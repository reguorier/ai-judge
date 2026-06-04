"""Client application state for the minimal AI Judge entrypoint."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClientAppState:
    question: str = ""
    mode: str = "deep_judge"
    run: dict[str, Any] = field(default_factory=dict)
    report: dict[str, Any] = field(default_factory=dict)

    @property
    def run_id(self) -> str:
        return str(self.run.get("run_id") or self.run.get("run", {}).get("run_id") or "")
