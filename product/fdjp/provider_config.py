"""FDJP provider configuration – environment variable management.

Reads provider configuration from environment variables with sensible defaults.
Never logs or exposes the API key in metadata or logs.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any


class FDJPProviderConfig:
    """Provider configuration loaded from environment variables."""

    __slots__ = (
        "kind",
        "base_url",
        "api_key",
        "model",
        "timeout_s",
        "max_retries",
        "max_tokens",
        "temperature",
        "enable_real",
        "openrouter_http_referer",
        "openrouter_app_title",
        "openrouter_app_categories",
        "openrouter_force_fusion",
    )

    def __init__(self):
        explicit_kind = os.environ.get("FDJP_PROVIDER_KIND", "")
        openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.kind: str = explicit_kind or ("openrouter" if openrouter_api_key else "openai_compatible")
        openrouter_mode = self.kind == "openrouter"

        self.base_url: str = (
            os.environ.get("FDJP_PROVIDER_BASE_URL", "").strip()
            or (os.environ.get("OPENROUTER_BASE_URL", "").strip() if openrouter_mode else "")
            or ("https://openrouter.ai/api/v1" if openrouter_mode else "")
        )
        self.api_key: str = os.environ.get("FDJP_PROVIDER_API_KEY", "").strip() or (
            openrouter_api_key if openrouter_mode else ""
        )
        self.model: str = (
            os.environ.get("FDJP_PROVIDER_MODEL", "").strip()
            or (os.environ.get("OPENROUTER_MODEL", "").strip() if openrouter_mode else "")
            or ("~openai/gpt-latest" if openrouter_mode else "gpt-4o-mini")
        )
        self.timeout_s: int = int(os.environ.get("FDJP_PROVIDER_TIMEOUT_S", "20"))
        self.max_retries: int = int(os.environ.get("FDJP_PROVIDER_MAX_RETRIES", "2"))
        self.max_tokens: int = int(os.environ.get("FDJP_PROVIDER_MAX_TOKENS", "1800"))
        self.temperature: float = float(os.environ.get("FDJP_PROVIDER_TEMPERATURE", "0"))
        self.enable_real: bool = os.environ.get("FDJP_PROVIDER_ENABLE_REAL", "0") == "1"
        self.openrouter_http_referer: str = os.environ.get(
            "OPENROUTER_HTTP_REFERER",
            os.environ.get("OPENROUTER_APP_URL", "https://github.com/reguorier/ai-judge"),
        ).strip()
        self.openrouter_app_title: str = os.environ.get("OPENROUTER_APP_TITLE", "AI Judge").strip()
        self.openrouter_app_categories: str = os.environ.get("OPENROUTER_APP_CATEGORIES", "cli-agent").strip()
        self.openrouter_force_fusion: bool = os.environ.get("OPENROUTER_FORCE_FUSION", "0") == "1"

    def has_credentials(self) -> bool:
        """Check if we have a usable API key."""
        return bool(self.api_key and self.api_key.strip())

    def is_usable(self) -> bool:
        """Check if config is sufficient for real provider calls."""
        return self.enable_real and self.has_credentials() and bool(self.base_url)

    def is_openrouter(self) -> bool:
        """Return True when this config targets OpenRouter."""
        return self.kind == "openrouter" or "openrouter.ai" in self.base_url.lower()

    def base_url_hash(self) -> str:
        """Return a sha256 prefix hash of the base URL (for metadata)."""
        if not self.base_url:
            return "empty"
        h = hashlib.sha256(self.base_url.encode()).hexdigest()[:12]
        return f"sha256-{h}"

    def safe_metadata(self) -> dict[str, Any]:
        """Return provider metadata safe for logging (no API key)."""
        return {
            "provider_kind": self.kind,
            "model": self.model,
            "base_url_hash": self.base_url_hash(),
            "timeout_s": self.timeout_s,
            "max_retries": self.max_retries,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "enable_real": self.enable_real,
            "openrouter_attribution_enabled": self.is_openrouter() and bool(
                self.openrouter_http_referer or self.openrouter_app_title
            ),
            "openrouter_force_fusion": self.openrouter_force_fusion,
        }

    def to_dict(self) -> dict[str, Any]:
        """Return full config dict (used internally, never logged)."""
        return {
            "kind": self.kind,
            "base_url": self.base_url,
            "api_key": "***" if self.api_key else "",
            "model": self.model,
            "timeout_s": self.timeout_s,
            "max_retries": self.max_retries,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "enable_real": self.enable_real,
            "openrouter_attribution_enabled": self.is_openrouter() and bool(
                self.openrouter_http_referer or self.openrouter_app_title
            ),
            "openrouter_force_fusion": self.openrouter_force_fusion,
        }


# Singleton config
_provider_config: FDJPProviderConfig | None = None


def get_provider_config() -> FDJPProviderConfig:
    """Get the global provider config singleton."""
    global _provider_config
    if _provider_config is None:
        _provider_config = FDJPProviderConfig()
    return _provider_config


def reset_provider_config() -> None:
    """Reset the config singleton (for testing)."""
    global _provider_config
    _provider_config = None
