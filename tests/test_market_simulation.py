"""Market Simulation Layer tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.runtime.market_simulation import (
    build_market_simulation_run,
    market_simulation_state_path,
    update_market_simulation_state,
)


def _snapshot() -> dict:
    return {
        "schema": "ai_judge.report_snapshot.v1",
        "snapshot_id": "snapshot-msl-001",
        "run_id": "msl-run-001",
        "created_at": "2026-06-17T02:40:00Z",
        "question": "2026 世界杯预测池：巴西 vs 德国，是否下注主胜？",
        "noise_audit": {
            "seat_noise_rows": [
                {"seat": "alpha", "seat_name": "Alpha", "stance": "support", "confidence": 0.78, "valid": True},
                {"seat": "beta", "seat_name": "Beta", "stance": "support value bet", "confidence": 0.72, "valid": True},
                {"seat": "gamma", "seat_name": "Gamma", "stance": "no bet", "confidence": 0.46, "valid": True},
            ]
        },
    }


def _strategy_intelligence() -> dict:
    return {
        "schema": "ai_judge.strategy_intelligence.v1",
        "snapshot_id": "snapshot-msl-001",
        "run_id": "msl-run-001",
        "model_strategies": {
            "alpha": {"seat": "alpha", "seat_name": "Alpha", "strategy_type": "CONSERVATIVE_EDGE", "confidence": 0.78, "stance": "support"},
            "beta": {"seat": "beta", "seat_name": "Beta", "strategy_type": "AGGRESSIVE_VALUE", "confidence": 0.72, "stance": "support value bet"},
            "gamma": {"seat": "gamma", "seat_name": "Gamma", "strategy_type": "NO_BET_RATIONAL", "confidence": 0.46, "stance": "no bet"},
        },
        "market_structure": {
            "normalized_entropy": 0.31,
            "noise_weight": 0.08,
            "disagreement_type": "price_driven",
        },
        "summary": {"dominant_strategy": "AGGRESSIVE_VALUE"},
    }


def _meta_judge() -> dict:
    return {
        "schema": "ai_judge.meta_judge.v1",
        "summary": {"top_model": "alpha", "top_score": 0.82, "deprecated_model_count": 0},
        "model_scores": {
            "alpha": {"seat": "alpha", "seat_name": "Alpha", "score": 0.82, "confidence": 0.78, "strategy_type": "CONSERVATIVE_EDGE", "lifecycle_status": "active"},
            "beta": {"seat": "beta", "seat_name": "Beta", "score": 0.76, "confidence": 0.72, "strategy_type": "AGGRESSIVE_VALUE", "lifecycle_status": "active"},
            "gamma": {"seat": "gamma", "seat_name": "Gamma", "score": 0.52, "confidence": 0.46, "strategy_type": "NO_BET_RATIONAL", "lifecycle_status": "watch"},
        },
    }


def _weights() -> dict:
    return {
        "schema": "ai_judge.model_weights.v1",
        "weights": {"alpha": 0.48, "beta": 0.39, "gamma": 0.13},
        "models": {},
    }


def _production_strategies() -> dict:
    return {
        "schema": "ai_judge.production_strategies.v1",
        "admission_rule": "accepted_backtest_only_v1",
        "strategies": [
            {
                "strategy_id": "strategy-robust",
                "name": "Robust price signal",
                "status": "production",
                "risk_thresholds": {"risk_budget": 0.76, "max_drawdown": 0.34},
                "backtest": {"roi": 0.092, "max_drawdown": 0.035, "win_rate": 0.71, "stability": 0.83},
            },
            {
                "strategy_id": "strategy-fragile",
                "name": "Fragile late value",
                "status": "production",
                "risk_thresholds": {"risk_budget": 0.32, "max_drawdown": 0.12},
                "backtest": {"roi": 0.018, "max_drawdown": 0.095, "win_rate": 0.53, "stability": 0.48},
            },
        ],
    }


def test_market_simulation_outputs_counterfactual_worlds_and_distributions():
    result = build_market_simulation_run(
        snapshot=_snapshot(),
        strategy_intelligence=_strategy_intelligence(),
        meta_judge=_meta_judge(),
        model_weights=_weights(),
        autonomous_strategy={"schema": "ai_judge.autonomous_strategy.v1"},
        production_strategies=_production_strategies(),
    )

    assert result["schema"] == "ai_judge.market_simulation.v1"
    assert result["hard_rule"] == "predictions_are_distributions_over_possible_worlds"
    assert result["monte_carlo_runs"] >= 10_000
    assert result["scenario_count"] >= 5
    assert result["summary"]["robust_strategy_count"] >= 1
    assert result["summary"]["top_scenario_risk"] >= result["scenarios"][0]["risk_score"]

    scenario = result["scenarios"][0]
    distribution = scenario["outcome_distribution"]
    assert distribution["monte_carlo_runs"] >= 10_000
    assert sum(distribution["counts"].values()) == distribution["monte_carlo_runs"]
    assert set(distribution["probabilities"]) == {"primary", "neutral", "counter"}
    assert "roi_delta" in scenario["counterfactual_impact"]
    assert scenario["model_behavior_simulation"][0]["predicted_action"] in {
        "BACK_PRIMARY",
        "BACK_COUNTER",
        "NO_BET",
        "SEEK_ARBITRAGE",
        "WAIT_FOR_PRICE",
    }
    assert len(scenario["market_feedback_loop"]["adjustment_rounds"]) == 3
    assert scenario["strategy_stress_tests"][0]["stress_status"] in {"robust", "stressed"}


def test_market_simulation_state_is_persisted_once(tmp_path):
    first = update_market_simulation_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        strategy_intelligence=_strategy_intelligence(),
        meta_judge=_meta_judge(),
        model_weights=_weights(),
        autonomous_strategy={"schema": "ai_judge.autonomous_strategy.v1"},
        production_strategies=_production_strategies(),
    )
    second = update_market_simulation_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        strategy_intelligence=_strategy_intelligence(),
        meta_judge=_meta_judge(),
        model_weights=_weights(),
        autonomous_strategy={"schema": "ai_judge.autonomous_strategy.v1"},
        production_strategies=_production_strategies(),
    )

    state = json.loads(market_simulation_state_path(tmp_path).read_text(encoding="utf-8"))
    assert first["market_simulation"]["summary"]["scenario_count"] >= 5
    assert second["market_simulation_state"]["snapshot_count"] == 1
    assert state["schema"] == "ai_judge.market_simulation_state.v1"
    assert state["runs"][0]["run_id"] == "msl-run-001"
    assert "baseline" in state["scenario_history"]
