"""Public license shim for the open-core AI Judge package.

The production validator is distributed in the paid ai-judge-core package.
This shim keeps the public CLI importable without exposing the entitlement
protocol, offline cache rules, or license server internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LicenseStatus:
    valid: bool
    key_hash: str = ""
    plan: str = "community"
    machines_bound: int = 0
    max_machines: int = 0
    expires_at: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "key_hash": self.key_hash,
            "plan": self.plan,
            "machines_bound": self.machines_bound,
            "max_machines": self.max_machines,
            "expires_at": self.expires_at,
            "message": self.message,
        }


def _private_validator():
    try:
        from ai_judge_license.validator import (  # type: ignore[import-untyped]
            activate_license as _activate,
            clear_license as _clear,
            validate_license as _validate,
        )
    except ImportError:
        return None
    return _activate, _clear, _validate


def validate_license(key: str | None = None) -> LicenseStatus:
    private = _private_validator()
    if private is None:
        return LicenseStatus(
            valid=False,
            message=(
                "Paid AI Judge core is not installed. Install the subscriber "
                "package to run production jury, collect, verdict, and reflect commands."
            ),
        )
    _, _, private_validate = private
    return private_validate(key)


def activate_license(key: str) -> LicenseStatus:
    private = _private_validator()
    if private is None:
        return LicenseStatus(
            valid=False,
            message="Paid license package not installed. Subscribe to activate."
        )
    private_activate, _, _ = private
    return private_activate(key)


def clear_license() -> None:
    private = _private_validator()
    if private is None:
        return
    _, private_clear, _ = private
    private_clear()
