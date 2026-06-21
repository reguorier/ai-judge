"""Runtime model influence weights for AI Judge aggregation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


MODEL_WEIGHTS_SCHEMA = "ai_judge.model_weights.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def default_model_weights_path() -> Path:
    return Path(
        os.environ.get(
            "AI_JUDGE_MODEL_WEIGHTS_PATH",
            str(PROJECT_ROOT / "reports" / "runtime" / "model_weights.json"),
        )
    )


def load_runtime_model_weights(path: Path | None = None) -> dict[str, Any]:
    target = path or default_model_weights_path()
    if not target.exists():
        return {"schema": MODEL_WEIGHTS_SCHEMA, "weights": {}, "models": {}, "source_path": str(target)}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "schema": MODEL_WEIGHTS_SCHEMA,
            "weights": {},
            "models": {},
            "source_path": str(target),
            "warnings": ["model weights file was invalid JSON"],
        }
    payload.setdefault("schema", MODEL_WEIGHTS_SCHEMA)
    payload.setdefault("weights", {})
    payload.setdefault("models", {})
    payload["source_path"] = str(target)
    return payload


def apply_runtime_model_weights(
    seat_scores: list[dict[str, Any]],
    weights_payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    payload = weights_payload or load_runtime_model_weights()
    weights = payload.get("weights") if isinstance(payload.get("weights"), dict) else {}
    if not weights:
        return seat_scores
    rows = []
    for row in seat_scores:
        seat = str(row.get("seat") or "").lower()
        item = dict(row)
        item["meta_judge_weight"] = round(float(weights.get(seat, 0.0) or 0.0), 6)
        model_info = payload.get("models", {}).get(seat, {}) if isinstance(payload.get("models"), dict) else {}
        if isinstance(model_info, dict):
            item["meta_judge_score"] = round(float(model_info.get("score") or 0.0), 4)
            item["meta_judge_lifecycle"] = str(model_info.get("lifecycle_status") or "unknown")
        rows.append(item)
    rows.sort(
        key=lambda item: (
            float(item.get("meta_judge_weight") or 0.0),
            float(item.get("average_score") or 0.0),
        ),
        reverse=True,
    )
    return rows


def meta_weighted_average(
    seat_scores: list[dict[str, Any]],
    weights_payload: dict[str, Any] | None = None,
) -> float | None:
    payload = weights_payload or load_runtime_model_weights()
    weights = payload.get("weights") if isinstance(payload.get("weights"), dict) else {}
    if not weights:
        return None
    total_weight = 0.0
    weighted_score = 0.0
    for row in seat_scores:
        seat = str(row.get("seat") or "").lower()
        if seat not in weights:
            continue
        weight = float(weights.get(seat) or 0.0)
        if weight <= 0:
            continue
        total_weight += weight
        weighted_score += float(row.get("average_score") or 0.0) * weight
    if total_weight <= 0:
        return None
    return round(weighted_score / total_weight, 4)
