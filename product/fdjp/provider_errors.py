"""FDJP provider error types for real provider operations."""

from __future__ import annotations


class FDJPProviderError(Exception):
    """Base exception for FDJP provider errors."""

    def __init__(self, message: str, error_type: str = "FDJPProviderError"):
        super().__init__(message)
        self.error_type = error_type


class FDJPProviderTimeoutError(FDJPProviderError):
    """Provider request timed out."""

    def __init__(self, message: str = "Provider request timed out"):
        super().__init__(message, "FDJPProviderTimeoutError")


class FDJPProviderAuthError(FDJPProviderError):
    """Authentication/authorization failed (401/403)."""

    def __init__(self, message: str = "Provider authentication failed"):
        super().__init__(message, "FDJPProviderAuthError")


class FDJPProviderRateLimitError(FDJPProviderError):
    """Provider rate limited (429)."""

    def __init__(self, message: str = "Provider rate limited"):
        super().__init__(message, "FDJPProviderRateLimitError")


class FDJPProviderServerError(FDJPProviderError):
    """Provider server error (5xx)."""

    def __init__(self, message: str = "Provider server error"):
        super().__init__(message, "FDJPProviderServerError")


class FDJPProviderConnectionError(FDJPProviderError):
    """Connection reset or network failure."""

    def __init__(self, message: str = "Provider connection error"):
        super().__init__(message, "FDJPProviderConnectionError")


class FDJPProviderConfigError(FDJPProviderError):
    """Provider configuration error (missing env vars, invalid values)."""

    def __init__(self, message: str = "Provider configuration error"):
        super().__init__(message, "FDJPProviderConfigError")


class FDJPProviderCircuitBreakerOpen(FDJPProviderError):
    """Circuit breaker is open, provider calls blocked."""

    def __init__(self, message: str = "Circuit breaker open"):
        super().__init__(message, "FDJPProviderCircuitBreakerOpen")


# Retryable error types (for timeout, connectivity, rate-limit, 5xx)
RETRYABLE_ERROR_TYPES = {
    "FDJPProviderTimeoutError",
    "FDJPProviderRateLimitError",
    "FDJPProviderServerError",
    "FDJPProviderConnectionError",
}

# Non-retryable error types (auth, config, circuit breaker)
NON_RETRYABLE_ERROR_TYPES = {
    "FDJPProviderAuthError",
    "FDJPProviderConfigError",
    "FDJPProviderCircuitBreakerOpen",
}