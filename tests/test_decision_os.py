"""Autonomous Decision OS tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.runtime.decision_os import (
    BET,
    NO_BET,
    build_decision_os_run,
    decision_os_state_path,
    update_decision_os_state,
)


def _snapshot() -> dict:
    return {
        "schema": "ai_judge.report_snapshot.v1",
        "snapshot_id": "snapshot-dos-001",
        "run_id": "dos-run-001",
        "created_at": "2026-06-17T05:00:00+08:00",
        "question": "Product Decision OS: 巴西 vs 德国是否执行受约束下注？",
    }


def _market(*, entropy: float = 0.62, risk: float = 0.52, robust: float = 1.0, roi: float = 0.026) -> dict:
    return {
        "schema": "ai_judge.market_simulation.v1",
        "summary": {
            "scenario_count": 5,
            "monte_carlo_runs": 10000,
            "robust_strategy_count": 1 if robust > 0 else 0,
            "top_scenario_risk": risk,
            "worst_scenario_id": "high_noise_market",
            "mean_expected_roi": roi,
        },
        "base_market_state": {
            "entropy": entropy,
            "noise_weight": 0.12,
            "top_model_score": 0.82,
        },
        "strategy_robustness": {
            "strategies": [
                {
                    "strategy_id": "strategy-robust",
                    "name": "Robust price strategy",
                    "robustness_score": robust,
                    "mean_expected_roi": roi,
                    "worst_projected_drawdown": 0.105,
                    "lifecycle_status": "robust" if robust >= 0.6 else "fragile",
                }
            ]
        },
    }


def _production() -> dict:
    return {
        "schema": "ai_judge.production_strategies.v1",
        "strategies": [
            {
                "strategy_id": "strategy-robust",
                "name": "Robust price strategy",
                "status": "production",
                "risk_thresholds": {"risk_budget": 0.78, "max_drawdown": 0.34},
                "backtest": {"roi": 0.08, "win_rate": 0.72},
            }
        ],
    }


def _weights() -> dict:
    return {"schema": "ai_judge.model_weights.v1", "weights": {"alpha": 0.48, "beta": 0.32}}


def test_decision_os_executes_bounded_bet_for_robust_strategy():
    result = build_decision_os_run(
        snapshot=_snapshot(),
        market_simulation=_market(),
        production_strategies=_production(),
        model_weights=_weights(),
    )

    assert result["schema"] == "ai_judge.decision_os.v1"
    assert result["hard_rule"] == "constrained_autonomous_agent_not_advisory_system"
    assert result["summary"]["top_action"] == BET
    assert result["summary"]["executed_action_count"] >= 1
    assert result["portfolio_allocation"]["projected_portfolio_exposure"] <= result["risk_limits"]["max_portfolio_exposure"]
    assert result["portfolio_allocation"]["positions"][0]["allocated_capital"] <= result["risk_limits"]["max_match_exposure"]
    assert result["execution_layer"]["logs"][0]["status"] == "executed"


def test_decision_os_blocks_high_risk_low_entropy_policy_action():
    result = build_decision_os_run(
        snapshot=_snapshot(),
        market_simulation=_market(entropy=0.12, risk=0.68, robust=1.0, roi=0.031),
        production_strategies=_production(),
        model_weights=_weights(),
    )

    decision = result["constraint_evaluation"]["decisions"][0]
    assert decision["policy_action"] == BET
    assert decision["constraint_status"] == "blocked"
    assert decision["executable_action"] == NO_BET
    assert "high_risk_low_entropy_block" in decision["constraint_violations"]
    assert result["summary"]["rejected_action_count"] == 1


def test_decision_os_reads_runtime_policy_config():
    result = build_decision_os_run(
        snapshot=_snapshot(),
        market_simulation=_market(robust=0.9, roi=0.026),
        production_strategies=_production(),
        model_weights=_weights(),
        policy_config={
            "decision_rules": {
                "bet_min_robustness": 0.95,
                "hedge_min_robustness": 0.95,
                "hedge_min_expected_roi": 0.03,
            }
        },
    )

    decision = result["constraint_evaluation"]["decisions"][0]
    assert decision["policy_action"] == NO_BET
    assert result["policy_config_version"] == 1


def test_decision_os_state_persists_execution_once(tmp_path):
    first = update_decision_os_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        market_simulation=_market(),
        production_strategies=_production(),
        model_weights=_weights(),
    )
    second = update_decision_os_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        market_simulation=_market(),
        production_strategies=_production(),
        model_weights=_weights(),
    )

    state = json.loads(decision_os_state_path(tmp_path).read_text(encoding="utf-8"))
    assert first["decision_os"]["summary"]["executed_action_count"] >= 1
    assert second["decision_os_state"]["snapshot_count"] == 1
    assert state["schema"] == "ai_judge.decision_os_state.v1"
    assert state["runs"][0]["top_action"] == BET
    assert len(state["execution_log"]) >= 1
    assert state["active_exposures"]
