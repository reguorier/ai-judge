"""Autonomous Strategy Generator tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.runtime.autonomous_strategy import (
    build_autonomous_strategy_run,
    production_strategies_path,
    update_autonomous_strategy_state,
)


def _snapshot(run_id: str) -> dict:
    return {
        "schema": "ai_judge.report_snapshot.v1",
        "snapshot_id": f"snapshot-{run_id}",
        "run_id": run_id,
        "created_at": "2026-06-17T03:00:00Z",
        "title": "ASG sample",
        "question": "Product: generate strategies from historical runs",
        "mode": "deep_judge",
        "mode_label": "Deep Judge",
        "status": "completed",
        "judge_ir": {"schema": "ai_judge.judge_ir.v1", "sections": []},
        "noise_audit": {"seat_noise_rows": []},
    }


def _strategy(disagreement: str = "price_driven", dominant: str = "ARBITRAGE_SEEKING") -> dict:
    return {
        "schema": "ai_judge.strategy_intelligence.v1",
        "run_id": "asg-run",
        "created_at": "2026-06-17T03:00:00Z",
        "market_structure": {
            "disagreement_type": disagreement,
            "normalized_entropy": 0.62,
            "noise_weight": 0.0,
        },
        "summary": {
            "dominant_strategy": dominant,
            "disagreement_type": disagreement,
        },
    }


def _meta(top_score: float = 0.84, deprecated: int = 0) -> dict:
    return {
        "schema": "ai_judge.meta_judge.v1",
        "summary": {
            "top_model": "gemini",
            "top_score": top_score,
            "deprecated_model_count": deprecated,
        },
    }


def _weights() -> dict:
    return {
        "schema": "ai_judge.model_weights.v1",
        "weights": {"gemini": 0.42, "deepseek": 0.35, "claude": 0.23},
    }


def test_asg_generates_mutates_backtests_and_accepts_production_strategies(tmp_path):
    run = build_autonomous_strategy_run(
        reports_root=tmp_path,
        snapshot=_snapshot("asg-run-1"),
        strategy_intelligence=_strategy(),
        meta_judge=_meta(),
        model_weights=_weights(),
    )

    assert run["schema"] == "ai_judge.autonomous_strategy.v1"
    assert run["synthesized_templates"]
    assert run["generated_strategies"]
    assert run["mutated_strategies"]
    assert run["evaluated_strategies"]
    assert run["summary"]["accepted_count"] >= 1
    assert run["production_candidates"]
    assert all(item["status"] == "production" for item in run["production_candidates"])


def test_asg_state_only_promotes_backtest_passing_strategies(tmp_path):
    first = update_autonomous_strategy_state(
        reports_root=tmp_path,
        snapshot=_snapshot("asg-run-1"),
        strategy_intelligence=_strategy(),
        meta_judge=_meta(),
        model_weights=_weights(),
    )
    second = update_autonomous_strategy_state(
        reports_root=tmp_path,
        snapshot=_snapshot("asg-run-2"),
        strategy_intelligence=_strategy(),
        meta_judge=_meta(),
        model_weights=_weights(),
    )

    production = json.loads(production_strategies_path(tmp_path).read_text(encoding="utf-8"))

    assert first["autonomous_strategy"]["summary"]["accepted_count"] >= 1
    assert second["asg_state"]["snapshot_count"] == 2
    assert production["schema"] == "ai_judge.production_strategies.v1"
    assert production["strategy_count"] >= 1
    assert all(item["status"] == "production" for item in production["strategies"])
    assert production["admission_rule"] == "accepted_backtest_only_v1"


def test_asg_rejects_failing_backtests_from_production(tmp_path):
    run = build_autonomous_strategy_run(
        reports_root=tmp_path,
        snapshot=_snapshot("asg-noisy-run"),
        strategy_intelligence=_strategy(disagreement="noise_driven", dominant="NOISE_TRADING")
        | {"market_structure": {"disagreement_type": "noise_driven", "normalized_entropy": 0.95, "noise_weight": 1.0}},
        meta_judge=_meta(top_score=0.12, deprecated=4),
        model_weights={"schema": "ai_judge.model_weights.v1", "weights": {"xunfei": 0.0}},
    )

    assert run["evaluated_strategies"]
    assert all(item["lifecycle_status"] == "rejected" for item in run["evaluated_strategies"])
    assert run["summary"]["accepted_count"] == 0
    assert run["production_candidates"] == []
