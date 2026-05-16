#!/usr/bin/env python3
"""Per-run execution trace for product-visible AI Judge runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunTrace:
    """Collect compact, user-visible execution events for one run."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: list[dict[str, Any]] = []

    def add(self, phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        self.events.append({
            "index": len(self.events) + 1,
            "at": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "action": action,
            "detail": detail,
            "data": _json_safe(data or {}),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "event_count": len(self.events),
            "events": self.events,
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_trace(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _json_safe(value: Any, limit: int = 1800) -> Any:
    """Keep trace payloads readable and bounded."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item, limit=limit) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item, limit=limit) for item in value[:80]]
    if isinstance(value, tuple):
        return [_json_safe(item, limit=limit) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and len(value) > limit:
            return value[: limit - 1].rstrip() + "..."
        return value
    return str(value)
