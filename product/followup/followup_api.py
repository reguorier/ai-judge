"""Thin function API for creating follow-up notes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from product.followup.followup_reporter import write_followup_note


def create_followup(run_dir: Path, prompt: str) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("follow-up prompt is required")
    return write_followup_note(run_dir, prompt.strip())
