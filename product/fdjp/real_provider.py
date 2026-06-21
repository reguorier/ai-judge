"""FDJP Real Provider Adapter – OpenAI-compatible endpoint with production hardening.

Implements:
- OpenAI-compatible HTTP client
- Timeout, retry (2 attempts), circuit breaker (3 consecutive failures → 5min cooldown)
- Provider metadata (no API key leakage)
- Automatic fallback when unavailable
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from product.fdjp.provider import FDJPAuditProvider
from product.fdjp.provider_config import FDJPProviderConfig, get_provider_config
from product.fdjp.provider_errors import (
    FDJPProviderAuthError,
    FDJPProviderCircuitBreakerOpen,
    FDJPProviderConfigError,
    FDJPProviderConnectionError,
    FDJPProviderError,
    FDJPProviderRateLimitError,
    FDJPProviderServerError,
    FDJPProviderTimeoutError,
    NON_RETRYABLE_ERROR_TYPES,
    RETRYABLE_ERROR_TYPES,
)

# ── Circuit breaker state (process-level, lightweight) ──
_cb_failure_count: int = 0
_cb_last_failure_ts: float = 0.0
_cb_cooldown_s: float = 300.0  # 5 minutes
_cb_threshold: int = 3  # 3 consecutive failures


def _circuit_breaker_allows() -> bool:
    """Check if circuit breaker is closed (allows calls)."""
    global _cb_failure_count, _cb_last_failure_ts
    if _cb_failure_count < _cb_threshold:
        return True
    elapsed = time.monotonic() - _cb_last_failure_ts
    if elapsed >= _cb_cooldown_s:
        _cb_failure_count = 0
        return True
    return False


def _circuit_breaker_record_failure() -> None:
    """Record a failure for the circuit breaker."""
    global _cb_failure_count, _cb_last_failure_ts
    _cb_failure_count += 1
    _cb_last_failure_ts = time.monotonic()


def _circuit_breaker_record_success() -> None:
    """Reset circuit breaker on success."""
    global _cb_failure_count
    _cb_failure_count = 0


def _classify_http_error(status_code: int, body: str) -> FDJPProviderError:
    """Classify an HTTP error status into a provider error."""
    if status_code == 401 or status_code == 403:
        return FDJPProviderAuthError(f"HTTP {status_code}: {body[:200]}")
    if status_code == 429:
        return FDJPProviderRateLimitError(f"HTTP 429: {body[:200]}")
    if 500 <= status_code < 600:
        return FDJPProviderServerError(f"HTTP {status_code}: {body[:200]}")
    return FDJPProviderError(f"HTTP {status_code}: {body[:200]}", "FDJPProviderError")


class FDJPRealProvider(FDJPAuditProvider):
    """Real LLM provider using OpenAI-compatible HTTP endpoint."""

    def __init__(self, config: FDJPProviderConfig | None = None):
        self._config = config or get_provider_config()

    @property
    def name(self) -> str:
        return "FDJPRealProvider"

    @property
    def config(self) -> FDJPProviderConfig:
        return self._config

    def is_available(self) -> bool:
        """Check provider availability without making an expensive call.

        Returns False if:
        - Real provider is not enabled
        - No credentials configured
        - Circuit breaker is open
        """
        if not self._config.enable_real:
            return False
        if not self._config.has_credentials():
            return False
        if not _circuit_breaker_allows():
            return False
        return True

    def audit(self, prompt: str, *, timeout: int = 45) -> str:
        """Send prompt to the real LLM provider with retry and circuit breaker.

        Args:
            prompt: Full audit prompt text.
            timeout: Maximum seconds to wait (overrides config timeout_s).

        Returns:
            Raw LLM response string.

        Raises:
            FDJPProviderError: On any provider failure.
        """
        if not self._config.enable_real:
            raise FDJPProviderConfigError("Real provider not enabled (FDJP_PROVIDER_ENABLE_REAL=0)")

        if not self._config.has_credentials():
            raise FDJPProviderConfigError("No API key configured (FDJP_PROVIDER_API_KEY missing)")

        if not _circuit_breaker_allows():
            raise FDJPProviderCircuitBreakerOpen(
                f"Circuit breaker open: {_cb_failure_count} consecutive failures"
            )

        effective_timeout = timeout if timeout > 0 else self._config.timeout_s
        max_retries = self._config.max_retries

        last_error: FDJPProviderError | None = None

        for attempt in range(max_retries + 1):
            try:
                raw = self._call_endpoint(prompt, effective_timeout)
                _circuit_breaker_record_success()
                return raw
            except FDJPProviderError as exc:
                last_error = exc
                # Don't retry non-retryable errors
                if exc.error_type in NON_RETRYABLE_ERROR_TYPES:
                    break
                # Don't retry on last attempt
                if attempt >= max_retries:
                    break
                # Brief backoff before retry
                time.sleep(0.5 * (attempt + 1))
                continue
            except Exception as exc:
                last_error = FDJPProviderError(str(exc)[:500], type(exc).__name__)
                break

        # Record failure for circuit breaker
        _circuit_breaker_record_failure()
        if last_error:
            raise last_error
        raise FDJPProviderError("Unknown provider failure", "FDJPProviderError")

    def _call_endpoint(self, prompt: str, timeout_s: int) -> str:
        """Make a single HTTP call to the OpenAI-compatible endpoint."""
        url = self._config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": "You are a structured audit JSON generator. Output only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
        }
        if self._config.is_openrouter() and self._config.openrouter_force_fusion:
            payload["tool_choice"] = "required"

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }
        if self._config.is_openrouter():
            if self._config.openrouter_http_referer:
                headers["HTTP-Referer"] = self._config.openrouter_http_referer
            if self._config.openrouter_app_title:
                headers["X-Title"] = self._config.openrouter_app_title
            if self._config.openrouter_app_categories:
                headers["X-OpenRouter-Categories"] = self._config.openrouter_app_categories

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_json = json.loads(resp_body)
                # Extract content from OpenAI-compatible response
                choices = resp_json.get("choices", [])
                if not choices:
                    raise FDJPProviderError(
                        "Empty choices in provider response", "FDJPProviderError"
                    )
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if not content:
                    raise FDJPProviderError(
                        "Empty content in provider response", "FDJPProviderError"
                    )
                return content
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise _classify_http_error(exc.code, body)
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if "time" in reason.lower() or "timed out" in reason.lower():
                raise FDJPProviderTimeoutError(f"Provider timeout: {reason[:200]}")
            if "reset" in reason.lower() or "refused" in reason.lower():
                raise FDJPProviderConnectionError(f"Connection error: {reason[:200]}")
            raise FDJPProviderConnectionError(f"URL error: {reason[:200]}")
        except socket_timeout_error():
            raise FDJPProviderTimeoutError("Provider socket timeout")
        except json.JSONDecodeError:
            raise FDJPProviderError(
                "Invalid JSON in provider response", "FDJPProviderError"
            )


def socket_timeout_error() -> type:
    """Return socket.timeout for isinstance checks."""
    import socket
    return socket.timeout


def build_provider_metadata(
    config: FDJPProviderConfig,
    latency_ms: float,
    retry_count: int,
    fallback_used: bool = False,
    error_type: str | None = None,
    error_message: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build safe provider metadata dict (no API key)."""
    meta = config.safe_metadata()
    meta.update({
        "latency_ms": round(latency_ms),
        "retry_count": retry_count,
        "fallback_used": fallback_used,
        "error_type": error_type,
        "error_message": error_message[:500] if error_message else None,
        "request_id": request_id,
    })
    return meta


def reset_circuit_breaker() -> None:
    """Reset circuit breaker state (for testing)."""
    global _cb_failure_count, _cb_last_failure_ts
    _cb_failure_count = 0
    _cb_last_failure_ts = 0.0


def get_circuit_breaker_state() -> dict[str, Any]:
    """Get current circuit breaker state (for testing/metadata)."""
    return {
        "failure_count": _cb_failure_count,
        "last_failure_ts": _cb_last_failure_ts,
        "cooldown_s": _cb_cooldown_s,
        "threshold": _cb_threshold,
        "is_open": not _circuit_breaker_allows(),
    }
