"""Shared seat adapter result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SeatRunResult:
    seat_id: str
    status: str
    answer_path: str = ""
    evidence_path: str = ""
    screenshot_before_path: str = ""
    screenshot_after_path: str = ""
    trajectory_path: str = ""
    summary: str = ""
    failure_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seat_id": self.seat_id,
            "status": self.status,
            "answer_path": self.answer_path,
            "evidence_path": self.evidence_path,
            "screenshot_before_path": self.screenshot_before_path,
            "screenshot_after_path": self.screenshot_after_path,
            "trajectory_path": self.trajectory_path,
            "summary": self.summary,
            "failure_reason": self.failure_reason,
            "metadata": self.metadata,
        }
