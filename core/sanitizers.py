#!/usr/bin/env python3
"""Central path sanitizer for AI Judge public/matrix outputs.

Transforms local machine paths into safe redacted forms for any output
that may leave the developer machine (reports, evidence packages, API
responses, logs destined for external consumption).
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Precompiled patterns
# ---------------------------------------------------------------------------

_SANITIZER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # macOS private user paths with explicit username
    (re.compile(r"/Users/audimacmini"), "<local-user-path>"),
    # macOS other private user paths (non-Shared, non-guest)
    (
        re.compile(
            r"/Users/(?!(Shared|Guest)/)([a-zA-Z0-9_.@-]+)"
        ),
        r"<local-user-path>/\2",
    ),
    # Linux home paths
    (re.compile(r"/home/([a-zA-Z0-9_.@-]+)"), r"<home-path>/\1"),
    # Windows local paths
    (
        re.compile(r"C:\\Users\\([a-zA-Z0-9_.@ -]+)"),
        r"<windows-local-path>\\\1",
    ),
    # .ai-judge/runs artifact paths
    (re.compile(r"[^\s]*\.ai-judge/runs[^\s]*"), "<run-artifact-path>"),
    # Runtime runs in Library/Application Support (private path)
    (
        re.compile(
            r"[^\s]*Library/Application Support/AI Judge/runtime/runs[^\s]*"
        ),
        "<runtime-run-path>",
    ),
    # Library/Application Support/AI Judge with private user prefix
    # (covers the common long paths used in this codebase)
    (
        re.compile(
            r"<local-user-path>/Library/Application Support/AI Judge[^\s]*"
        ),
        "<runtime-path>",
    ),
]

# Paths that start with /Users/Shared are intentionally kept in internal
# runtime context but redacted for public consumption.
_SHARED_PATH = re.compile(r"/Users/Shared/AI Judge(/[^\s]*)?")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sanitize_path(text: str, *, allow_shared: bool = False) -> str:
    """Redact all private local paths in *text*.

    Parameters
    ----------
    text : str
        The input string (a file path, JSON content, report body, etc.).
    allow_shared : bool
        If ``True``, ``/Users/Shared/AI Judge/...`` paths are preserved.
        Default ``False`` (redact them too).

    Returns
    -------
    str
        Sanitized string with private paths replaced by safe tokens.
    """
    result = text
    for pattern, replacement in _SANITIZER_PATTERNS:
        result = pattern.sub(replacement, result)
    if not allow_shared:
        result = _SHARED_PATH.sub("<shared-runtime-path>", result)
    return result


def sanitize_paths(texts: list[str], *, allow_shared: bool = False) -> list[str]:
    """Bulk-sanitize a list of strings."""
    return [sanitize_path(t, allow_shared=allow_shared) for t in texts]


def sanitize_value(value: Any, *, allow_shared: bool = False) -> Any:
    """Recursively sanitize all strings inside *value* (str/dict/list)."""
    if isinstance(value, str):
        return sanitize_path(value, allow_shared=allow_shared)
    if isinstance(value, dict):
        return {
            k: sanitize_value(v, allow_shared=allow_shared)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [sanitize_value(v, allow_shared=allow_shared) for v in value]
    return value


def sanitize_json_payload(
    payload: dict[str, Any], *, allow_shared: bool = False
) -> dict[str, Any]:
    """Deep-sanitize a JSON-serialisable dict meant for public/matrix output."""
    return sanitize_value(payload, allow_shared=allow_shared)


# ---------------------------------------------------------------------------
# Leak check (for tests / validation)
# ---------------------------------------------------------------------------

_PRIVATE_PATH_TESTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"/Users/audimacmini"), "audimacmini path"),
    (re.compile(r"/Users/(?!(Shared|Guest)/)[a-zA-Z0-9_.@-]+/"), "private user path"),
    (re.compile(r"/home/[a-zA-Z0-9_.@-]+/"), "linux home path"),
    (re.compile(r"C:\\Users\\"), "windows user path"),
    (re.compile(r"\.ai-judge/runs"), ".ai-judge/runs"),
    (
        re.compile(r"Library/Application Support/AI Judge/runtime/runs"),
        "private runtime runs",
    ),
]


def has_private_path_leak(text: str) -> list[str]:
    """Return list of leak descriptions found in *text*, empty if clean."""
    leaks: list[str] = []
    for pattern, desc in _PRIVATE_PATH_TESTS:
        if pattern.search(text):
            leaks.append(desc)
    return leaks


def assert_no_path_leak(text: str, *, label: str = "text") -> None:
    """Raise ``AssertionError`` if *text* contains a private path."""
    leaks = has_private_path_leak(text)
    if leaks:
        raise AssertionError(f"Path leak in {label}: {leaks}\nFirst 500 chars: {text[:500]}")
