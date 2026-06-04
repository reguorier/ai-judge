"""Minimal notification abstraction for the local client."""

from __future__ import annotations


def notify(title: str, message: str) -> str:
    return f"{title}: {message}"
