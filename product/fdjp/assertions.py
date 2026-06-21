"""Shared FDJP assertion extraction primitives.

All clients feed FDJP through this module so the five-dimension layer receives
one stable input shape regardless of artifact source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


FAILED_OUTPUT_MARKERS = (
    "existing_answer_placeholder",
    "provider_quota_limited",
    "prompt_still_in_input",
    "usage/message limit",
    "usage limit",
    "未完成",
    "慢生成待回收",
    "占位符",
)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])\s*|\n+")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class AssertionRecord:
    source_type: str
    seat_id: str
    display_name: str
    evidence_id: str
    text: str
    confidence: float
    answer_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "seat_id": self.seat_id,
            "display_name": self.display_name,
            "evidence_id": self.evidence_id,
            "text": self.text,
            "confidence": self.confidence,
            "answer_path": self.answer_path,
        }


def clean_text(text: Any) -> str:
    return WHITESPACE_RE.sub(" ", str(text or "")).strip()


def safe_float(value: Any, default: float = 0.55) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def looks_failed(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in FAILED_OUTPUT_MARKERS)


def seat_text(seat: dict[str, Any]) -> str:
    for key in ("output", "response", "answer", "content", "text", "summary"):
        value = seat.get(key)
        if isinstance(value, str) and value.strip():
            return clean_text(value)
    return ""


def normalise_seats(seats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalised: list[dict[str, Any]] = []
    for index, seat in enumerate(seats or [], start=1):
        if not isinstance(seat, dict):
            continue
        text = seat_text(seat)
        if not text or looks_failed(text):
            continue
        seat_id = clean_text(
            seat.get("seat_id")
            or seat.get("seat")
            or seat.get("name")
            or seat.get("provider_id")
            or f"seat_{index}"
        )
        normalised.append({
            "seat_id": seat_id,
            "display_name": clean_text(seat.get("display_name") or seat.get("seat_name") or seat_id),
            "text": text,
            "confidence": max(0.05, min(safe_float(seat.get("confidence", seat.get("score", 0.55))), 1.0)),
            "answer_path": clean_text(seat.get("answer_path") or seat.get("source") or ""),
        })
    return normalised


def normalise_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, ev in enumerate(evidence or [], start=1):
        if not isinstance(ev, dict):
            continue
        text = clean_text(ev.get("text") or ev.get("summary") or ev.get("description") or ev.get("claim"))
        if not text or looks_failed(text):
            continue
        ev_id = clean_text(ev.get("id") or ev.get("evidence_id") or f"evidence_{index}")
        items.append({
            "evidence_id": ev_id,
            "source_type": "evidence",
            "seat_id": "",
            "text": text,
            "confidence": max(0.05, min(safe_float(ev.get("confidence", ev.get("score", 0.50))), 1.0)),
        })
    return items


def split_assertions(text: str, *, max_items: int = 30) -> list[str]:
    parts: list[str] = []
    for chunk in SENTENCE_SPLIT_RE.split(text):
        chunk = clean_text(chunk)
        if len(chunk) < 12:
            continue
        if len(chunk) > 420:
            subparts = re.split(r"(?<=[，,：:])\s*", chunk)
            buffer = ""
            for sub in subparts:
                sub = clean_text(sub)
                if not sub:
                    continue
                if len(buffer) + len(sub) < 360:
                    buffer = (buffer + " " + sub).strip()
                else:
                    if len(buffer) >= 12:
                        parts.append(buffer)
                    buffer = sub
            if len(buffer) >= 12:
                parts.append(buffer)
        else:
            parts.append(chunk)
        if len(parts) >= max_items:
            break
    return parts[:max_items]


def extract_assertion_records(
    seats: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for seat in seats:
        for idx, assertion in enumerate(split_assertions(seat["text"]), start=1):
            records.append(AssertionRecord(
                source_type="seat",
                seat_id=seat["seat_id"],
                display_name=seat["display_name"],
                evidence_id=f"seat:{seat['seat_id']}:{idx:03d}",
                text=assertion,
                confidence=seat["confidence"],
                answer_path=seat["answer_path"],
            ).to_dict())
    for ev in evidence:
        for idx, assertion in enumerate(split_assertions(ev["text"], max_items=10), start=1):
            records.append(AssertionRecord(
                source_type="evidence",
                seat_id="",
                display_name="evidence",
                evidence_id=f"{ev['evidence_id']}:{idx:03d}",
                text=assertion,
                confidence=ev["confidence"],
            ).to_dict())
    return records


def build_assertion_packet(
    seats: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    normalised_seats = normalise_seats(seats)
    normalised_evidence = normalise_evidence(evidence)
    records = extract_assertion_records(normalised_seats, normalised_evidence)
    return {
        "schema": "ai_judge.fdjp.assertion_packet.v1",
        "seat_source_count": len(normalised_seats),
        "evidence_source_count": len(normalised_evidence),
        "assertion_count": len(records),
        "seats": normalised_seats,
        "evidence": normalised_evidence,
        "assertions": records,
    }
