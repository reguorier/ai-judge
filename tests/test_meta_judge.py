"""Meta-Judge scoring, weighting, pruning and aggregation tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.auto_jury import assemble_verdict
from product.reporting.runtime.meta_judge import (
    build_meta_judge_evaluation,
    update_meta_judge_state,
)


def _snapshot(snapshot_id: str, run_id: str) -> dict:
    return {
        "schema": "ai_judge.report_snapshot.v1",
        "snapshot_id": snapshot_id,
        "run_id": run_id,
        "created_at": "2026-06-17T02:00:00Z",
        "title": "Meta Judge evaluation sample",
        "question": "Product: compare model influence after noisy and clean outputs.",
        "mode": "deep_judge",
        "mode_label": "Deep Judge",
        "status": "completed",
        "judge_ir": {"schema": "ai_judge.judge_ir.v1", "sections": []},
        "noise_audit": {
            "schema": "ai_judge.noise_audit.v1",
            "question_hash": "meta-question",
            "seat_noise_rows": [
                {
                    "seat": "alpha",
                    "seat_name": "Alpha",
                    "stance": "support",
                    "confidence": 0.78,
                    "valid": True,
                    "noise_flags": [],
                },
                {
                    "seat": "beta",
                    "seat_name": "Beta",
                    "stance": "support",
                    "confidence": 0.94,
                    "valid": False,
                    "noise_flags": ["format_noise", "hallucination_risk"],
                },
            ],
        },
    }


def _memory() -> dict:
    return {
        "schema": "ai_judge.model_memory.v1",
        "profiles": {
            "alpha": {
                "runs_seen": 3,
                "contradiction_rate": 0.0,
                "risk_profile": {
                    "invalid_rate": 0.0,
                    "format_noise_rate": 0.0,
                    "context_pollution_rate": 0.0,
                    "hallucination_risk_rate": 0.0,
                },
            },
            "beta": {
                "runs_seen": 3,
                "contradiction_rate": 0.9,
                "risk_profile": {
                    "invalid_rate": 0.7,
                    "format_noise_rate": 0.7,
                    "context_pollution_rate": 0.2,
                    "hallucination_risk_rate": 0.6,
                },
            },
        },
    }


def _strategy() -> dict:
    return {
        "schema": "ai_judge.strategy_intelligence.v1",
        "model_strategies": {
            "alpha": {"seat_name": "Alpha", "strategy_type": "AGGRESSIVE_VALUE"},
            "beta": {"seat_name": "Beta", "strategy_type": "NOISE_TRADING"},
        },
    }


def test_meta_judge_scores_weights_and_prunes_models():
    result = build_meta_judge_evaluation(
        snapshot=_snapshot("snapshot-meta-1", "meta-1"),
        model_memory=_memory(),
        strategy_intelligence=_strategy(),
    )

    alpha = result["model_scores"]["alpha"]
    beta = result["model_scores"]["beta"]
    weights = result["weight_allocation"]["weights"]

    assert result["schema"] == "ai_judge.meta_judge.v1"
    assert alpha["score"] > beta["score"]
    assert alpha["lifecycle_status"] == "active"
    assert beta["lifecycle_status"] == "deprecated"
    assert weights["alpha"] == 1.0
    assert weights["beta"] == 0.0
    assert result["summary"]["top_model"] == "alpha"
    assert result["summary"]["deprecated_model_count"] == 1


def test_meta_judge_state_persists_scores_and_weights(tmp_path):
    first = update_meta_judge_state(
        reports_root=tmp_path,
        snapshot=_snapshot("snapshot-meta-1", "meta-1"),
        model_memory=_memory(),
        strategy_intelligence=_strategy(),
    )
    second = update_meta_judge_state(
        reports_root=tmp_path,
        snapshot=_snapshot("snapshot-meta-2", "meta-2"),
        model_memory=_memory(),
        strategy_intelligence=_strategy(),
    )

    state = json.loads((tmp_path / "runtime" / "meta_judge_state.json").read_text(encoding="utf-8"))
    weights = json.loads((tmp_path / "runtime" / "model_weights.json").read_text(encoding="utf-8"))

    assert first["model_weights"]["weights"]["alpha"] == 1.0
    assert second["meta_judge_state"]["snapshot_count"] == 2
    assert state["profiles"]["alpha"]["runs_seen"] == 2
    assert state["profiles"]["beta"]["deprecated_events"] == 2
    assert weights["schema"] == "ai_judge.model_weights.v1"
    assert weights["deprecated_models"] == ["beta"]


def test_auto_jury_consumes_meta_judge_weights(tmp_path, monkeypatch):
    weights_path = tmp_path / "model_weights.json"
    weights_path.write_text(
        json.dumps(
            {
                "schema": "ai_judge.model_weights.v1",
                "weights": {"gemini": 0.9, "claude": 0.1},
                "models": {
                    "gemini": {"score": 0.9, "lifecycle_status": "active"},
                    "claude": {"score": 0.2, "lifecycle_status": "watch"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_JUDGE_MODEL_WEIGHTS_PATH", str(weights_path))

    claims = [
        {"_seat": "gemini", "claim": "Gemini strong claim", "confidence": 0.9},
        {"_seat": "claude", "claim": "Claude weak claim", "confidence": 0.4},
    ]
    verdict = assemble_verdict(
        question="Product: test weighted aggregation",
        mode="flash",
        seats=["gemini", "claude"],
        claims=claims,
        engine="test",
    )

    assert verdict["model_weights"]["weights"]["gemini"] == 0.9
    assert "average_score_meta_weighted" in verdict
    assert all("meta_judge_weight" in row for row in verdict["seat_scores"])
