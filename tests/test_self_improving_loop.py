"""Self-Improving Execution Loop tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.runtime.decision_os import build_decision_os_run, decision_policy_config_path
from product.reporting.runtime.self_improving_loop import (
    build_self_improving_loop_run,
    self_improving_loop_state_path,
    update_self_improving_loop_state,
)


def _snapshot() -> dict:
    return {
        "schema": "ai_judge.report_snapshot.v1",
        "snapshot_id": "snapshot-siel-001",
        "run_id": "siel-run-001",
        "created_at": "2026-06-17T06:00:00+08:00",
        "question": "Self Improving Loop: 是否应执行并学习策略？",
    }


def _market(*, risk: float = 0.36, robust: float = 1.0, roi: float = 0.026) -> dict:
    return {
        "schema": "ai_judge.market_simulation.v1",
        "summary": {
            "scenario_count": 5,
            "monte_carlo_runs": 10000,
            "robust_strategy_count": 1,
            "top_scenario_risk": risk,
            "worst_scenario_id": "high_noise_market",
            "mean_expected_roi": roi,
        },
        "base_market_state": {
            "entropy": 0.62,
            "noise_weight": 0.10,
            "top_model_score": 0.88,
        },
        "scenarios": [
            {
                "scenario_id": "baseline",
                "risk_score": risk,
                "outcome_distribution": {
                    "expected_edge": 0.027,
                    "volatility": 0.018,
                    "tail_risk_p05": -0.017,
                },
            }
        ],
        "strategy_robustness": {
            "strategies": [
                {
                    "strategy_id": "strategy-siel",
                    "name": "SIEL robust strategy",
                    "robustness_score": robust,
                    "mean_expected_roi": roi,
                    "worst_projected_drawdown": 0.10,
                    "lifecycle_status": "robust",
                }
            ]
        },
    }


def _production() -> dict:
    return {
        "schema": "ai_judge.production_strategies.v1",
        "strategies": [
            {
                "strategy_id": "strategy-siel",
                "name": "SIEL robust strategy",
                "status": "production",
                "risk_thresholds": {"risk_budget": 0.78, "max_drawdown": 0.30},
                "backtest": {"roi": 0.09, "win_rate": 0.74},
            }
        ],
    }


def _weights() -> dict:
    return {"schema": "ai_judge.model_weights.v1", "weights": {"alpha": 0.56, "beta": 0.44}}


def _decision_os() -> dict:
    return build_decision_os_run(
        snapshot=_snapshot(),
        market_simulation=_market(),
        production_strategies=_production(),
        model_weights=_weights(),
    )


def test_self_improving_loop_outputs_decision_outcome_policy_and_mutation():
    loop = build_self_improving_loop_run(
        snapshot=_snapshot(),
        decision_os=_decision_os(),
        market_simulation=_market(),
    )

    assert loop["schema"] == "ai_judge.self_improving_execution_loop.v1"
    assert loop["hard_rule"] == "self_modifying_decision_system_with_traceable_evolution_history"
    assert loop["decision_output"]["decision_count"] >= 1
    assert loop["outcome_evaluation"]["summary"]["signal_count"] >= 1
    assert "mean_value_error" in loop["outcome_evaluation"]["expected_vs_realized"]
    assert loop["policy_update"]["method"] == "bounded_policy_gradient_v1"
    assert loop["policy_update"]["gradient_steps"]
    assert loop["system_rewriter"]["untracked_self_modification_allowed"] is False
    assert loop["system_mutation_log"]
    assert all(item["tracked"] for item in loop["system_mutation_log"])
    assert loop["summary"]["policy_update_count"] >= 1


def test_self_improving_loop_persists_state_and_policy_config_once(tmp_path):
    first = update_self_improving_loop_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        decision_os=_decision_os(),
        market_simulation=_market(),
    )
    second = update_self_improving_loop_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        decision_os=_decision_os(),
        market_simulation=_market(),
    )

    state = json.loads(self_improving_loop_state_path(tmp_path).read_text(encoding="utf-8"))
    config = json.loads(decision_policy_config_path(tmp_path).read_text(encoding="utf-8"))

    assert first["self_improving_loop"]["summary"]["outcome_signal_count"] >= 1
    assert second["self_improving_loop_state"]["snapshot_count"] == 1
    assert state["schema"] == "ai_judge.self_improving_execution_loop_state.v1"
    assert state["runs"][0]["run_id"] == "siel-run-001"
    assert state["policy_history"]
    assert state["mutation_log"]
    assert state["learning_curve"]
    assert config["schema"] == "ai_judge.decision_policy_config.v1"
    assert config["version"] >= 2
