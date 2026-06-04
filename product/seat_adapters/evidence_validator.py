"""Validate whether a browser/model seat produced real answer artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SeatValidationResult:
    seat_id: str
    status: str
    valid: bool
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"seat_id": self.seat_id, "status": self.status, "valid": self.valid, "reasons": self.reasons, "details": self.details}


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_answered_seat(seat_dir: str | Path, run_started_at: str | None = None, seat_id: str | None = None) -> SeatValidationResult:
    seat_path = Path(seat_dir)
    resolved_seat_id = seat_id or seat_path.name
    reasons: list[str] = []
    answer_txt = seat_path / "answer.txt"
    answer_json = seat_path / "answer.json"
    evidence_json = seat_path / "evidence.json"
    if not answer_txt.exists():
        reasons.append("missing_answer_txt")
    if not answer_json.exists():
        reasons.append("missing_answer_json")
    if not evidence_json.exists():
        reasons.append("missing_evidence_json")
    answer_text = answer_txt.read_text(encoding="utf-8", errors="replace").strip() if answer_txt.exists() else ""
    if answer_txt.exists() and not answer_text:
        reasons.append("empty_answer")
    answer_data: dict[str, Any] = {}
    if answer_json.exists():
        try:
            parsed = json.loads(answer_json.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                answer_data = parsed
            else:
                reasons.append("answer_json_not_object")
        except json.JSONDecodeError:
            reasons.append("invalid_answer_json")
    evidence_data: dict[str, Any] = {}
    if evidence_json.exists():
        try:
            parsed = json.loads(evidence_json.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                evidence_data = parsed
            else:
                reasons.append("evidence_json_not_object")
        except json.JSONDecodeError:
            reasons.append("invalid_evidence_json")
    if answer_data and not any(answer_data.get(key) for key in ("run_marker", "run_id", "prompt_marker")):
        reasons.append("missing_run_marker")
    if answer_data and not any(answer_data.get(key) for key in ("answer", "summary", "sections", "verdict")):
        reasons.append("missing_structured_answer")
    started = _parse_time(run_started_at)
    if started and answer_txt.exists():
        modified = datetime.fromtimestamp(answer_txt.stat().st_mtime, tz=started.tzinfo)
        if modified < started:
            reasons.append("answer_older_than_run_start")
    status = "valid" if not reasons else "invalid"
    return SeatValidationResult(
        seat_id=resolved_seat_id,
        status=status,
        valid=not reasons,
        reasons=reasons,
        details={
            "answer_txt": str(answer_txt),
            "answer_json": str(answer_json),
            "evidence_json": str(evidence_json),
            "evidence_keys": sorted(evidence_data.keys()),
        },
    )
