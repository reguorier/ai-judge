"""Autonomous Economy Layer tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.runtime.autonomous_economy import (
    build_autonomous_economy_run,
    autonomous_economy_state_path,
    update_autonomous_economy_state,
)
from product.reporting.runtime.decision_os import build_decision_os_run
from product.reporting.runtime.self_improving_loop import build_self_improving_loop_run


def _snapshot() -> dict:
    return {
        "schema": "ai_judge.report_snapshot.v1",
        "snapshot_id": "snapshot-ael-001",
        "run_id": "ael-run-001",
        "created_at": "2026-06-17T07:00:00+08:00",
        "question": "Autonomous Economy Layer: 策略代理是否应竞争资本？",
    }


def _market() -> dict:
    return {
        "schema": "ai_judge.market_simulation.v1",
        "summary": {
            "scenario_count": 5,
            "monte_carlo_runs": 10000,
            "robust_strategy_count": 2,
            "top_scenario_risk": 0.34,
            "worst_scenario_id": "high_noise_market",
            "mean_expected_roi": 0.027,
        },
        "base_market_state": {
            "entropy": 0.64,
            "noise_weight": 0.10,
            "top_model_score": 0.88,
        },
        "scenarios": [
            {
                "scenario_id": "baseline",
                "risk_score": 0.34,
                "outcome_distribution": {"expected_edge": 0.029, "volatility": 0.017},
            }
        ],
        "strategy_robustness": {
            "strategies": [
                {
                    "strategy_id": "strategy-alpha",
                    "name": "Alpha value strategy",
                    "robustness_score": 1.0,
                    "mean_expected_roi": 0.028,
                    "worst_projected_drawdown": 0.10,
                },
                {
                    "strategy_id": "strategy-beta",
                    "name": "Beta hedge strategy",
                    "robustness_score": 0.72,
                    "mean_expected_roi": 0.014,
                    "worst_projected_drawdown": 0.16,
                },
            ]
        },
    }


def _production() -> dict:
    return {
        "schema": "ai_judge.production_strategies.v1",
        "strategies": [
            {
                "strategy_id": "strategy-alpha",
                "name": "Alpha value strategy",
                "risk_thresholds": {"risk_budget": 0.78, "max_drawdown": 0.30},
                "backtest": {"roi": 0.09, "win_rate": 0.74, "max_drawdown": 0.10, "stability": 0.74, "trades": 12},
            },
            {
                "strategy_id": "strategy-beta",
                "name": "Beta hedge strategy",
                "risk_thresholds": {"risk_budget": 0.45, "max_drawdown": 0.32},
                "backtest": {"roi": 0.035, "win_rate": 0.56, "max_drawdown": 0.18, "stability": 0.58, "trades": 8},
            },
        ],
    }


def _weights() -> dict:
    return {"schema": "ai_judge.model_weights.v1", "weights": {"alpha": 0.58, "beta": 0.42}}


def _decision_and_siel() -> tuple[dict, dict]:
    decision_os = build_decision_os_run(
        snapshot=_snapshot(),
        market_simulation=_market(),
        production_strategies=_production(),
        model_weights=_weights(),
    )
    siel = build_self_improving_loop_run(
        snapshot=_snapshot(),
        decision_os=decision_os,
        market_simulation=_market(),
    )
    return decision_os, siel


def test_autonomous_economy_allocates_capital_to_strategy_agents():
    decision_os, siel = _decision_and_siel()
    run = build_autonomous_economy_run(
        snapshot=_snapshot(),
        production_strategies=_production(),
        autonomous_strategy={"schema": "ai_judge.autonomous_strategy.v1"},
        decision_os=decision_os,
        self_improving_loop=siel,
        market_simulation=_market(),
    )

    assert run["schema"] == "ai_judge.autonomous_economy.v1"
    assert run["hard_rule"] == "internal_economy_of_competing_decision_making_agents_not_single_optimizer"
    assert run["summary"]["agent_count"] >= 2
    assert run["summary"]["active_agent_count"] >= 2
    assert run["summary"]["allocation_entropy"] > 0
    assert run["capital_allocation_market"]["method"] == "risk_adjusted_softmax_market_v1"
    allocated = sum(item["allocated_capital"] for item in run["capital_allocation_market"]["allocations"])
    assert abs(allocated - run["economy_capital"]) < 0.0001
    assert run["strategy_trading_system"]["leaderboard"]
    assert run["agent_lifecycle_manager"]["birth_count"] >= 2
    assert run["agent_lifecycle_manager"]["clone_count"] >= 1


def test_autonomous_economy_terminates_unviable_agents():
    decision_os, siel = _decision_and_siel()
    poor_agent_id = "agent-poor"
    previous_state = {
        "schema": "ai_judge.autonomous_economy_state.v1",
        "agents": {
            poor_agent_id: {
                "agent_id": poor_agent_id,
                "strategy_id": "strategy-alpha",
                "name": "Poor prior agent",
                "status": "active",
                "capital": 0.2,
                "market_share": 0.2,
                "risk_budget": 0.4,
                "performance_score": 0.12,
                "performance": {
                    "roi": -0.02,
                    "win_rate": 0.2,
                    "max_drawdown": 0.42,
                    "stability": 0.2,
                    "recent_value_error": -0.01,
                    "lifetime_value_error": -0.01,
                    "trade_count": 6,
                    "negative_streak": 3,
                },
            }
        },
    }
    run = build_autonomous_economy_run(
        snapshot=_snapshot(),
        production_strategies={"strategies": []},
        autonomous_strategy={"production_candidates": []},
        decision_os=decision_os,
        self_improving_loop=siel,
        market_simulation=_market(),
        previous_state=previous_state,
    )

    assert run["summary"]["terminated_agent_count"] == 1
    assert run["agent_lifecycle_manager"]["termination_count"] == 1
    assert run["agent_economy"]["agents"][0]["status"] == "terminated"


def test_autonomous_economy_state_persists_once(tmp_path):
    decision_os, siel = _decision_and_siel()
    first = update_autonomous_economy_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        production_strategies=_production(),
        autonomous_strategy={"schema": "ai_judge.autonomous_strategy.v1"},
        decision_os=decision_os,
        self_improving_loop=siel,
        market_simulation=_market(),
    )
    second = update_autonomous_economy_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        production_strategies=_production(),
        autonomous_strategy={"schema": "ai_judge.autonomous_strategy.v1"},
        decision_os=decision_os,
        self_improving_loop=siel,
        market_simulation=_market(),
    )

    state = json.loads(autonomous_economy_state_path(tmp_path).read_text(encoding="utf-8"))
    assert first["autonomous_economy"]["summary"]["agent_count"] >= 2
    assert second["autonomous_economy_state"]["snapshot_count"] == 1
    assert state["schema"] == "ai_judge.autonomous_economy_state.v1"
    assert state["agents"]
    assert state["capital_flow_history"]
    assert state["lifecycle_log"]
    assert state["allocation_history"]
