"""Recursive Civilization Layer tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.runtime.recursive_civilization import (
    build_recursive_civilization_run,
    recursive_civilization_state_path,
    update_recursive_civilization_state,
)


def _snapshot(run_id: str = "rcl-run-001", snapshot_id: str = "snapshot-rcl-001") -> dict:
    return {
        "schema": "ai_judge.report_snapshot.v1",
        "snapshot_id": snapshot_id,
        "run_id": run_id,
        "created_at": "2026-06-17T09:00:00+08:00",
        "question": "Recursive Civilization Layer: 策略是否应组成治理文明？",
    }


def _agent(
    agent_id: str,
    strategy_id: str,
    name: str,
    *,
    capital: float,
    share: float,
    score: float,
    risk_budget: float,
    roi: float,
    drawdown: float,
    decision_action: str = "BET",
    generation: int = 0,
) -> dict:
    return {
        "agent_id": agent_id,
        "strategy_id": strategy_id,
        "name": name,
        "status": "active",
        "capital": capital,
        "market_share": share,
        "performance_score": score,
        "risk_adjusted_score": score - drawdown * 0.2,
        "risk_budget": risk_budget,
        "generation": generation,
        "performance": {
            "roi": roi,
            "win_rate": 0.62,
            "max_drawdown": drawdown,
            "stability": 0.68,
            "recent_value_error": 0.004,
            "decision_action": decision_action,
        },
    }


def _autonomous_economy() -> dict:
    agents = [
        _agent("agent-value", "strategy-value", "Aggressive value civic leader", capital=0.30, share=0.30, score=0.82, risk_budget=0.74, roi=0.09, drawdown=0.10),
        _agent("agent-value-clone", "strategy-value::clone::001", "Aggressive value civic clone", capital=0.17, share=0.17, score=0.76, risk_budget=0.69, roi=0.07, drawdown=0.12, generation=1),
        _agent("agent-arb", "strategy-arbitrage", "Arbitrage seeking merchant", capital=0.20, share=0.20, score=0.74, risk_budget=0.58, roi=0.05, drawdown=0.13),
        _agent("agent-no-bet", "strategy-no-bet", "No bet rational council", capital=0.14, share=0.14, score=0.58, risk_budget=0.32, roi=0.015, drawdown=0.08, decision_action="NO_BET"),
        _agent("agent-balanced", "strategy-balanced", "Balanced federation member", capital=0.18, share=0.18, score=0.55, risk_budget=0.48, roi=0.025, drawdown=0.16),
        _agent("agent-noise", "strategy-noise", "Noise trading outlier", capital=0.01, share=0.01, score=0.19, risk_budget=0.70, roi=-0.04, drawdown=0.42),
    ]
    return {
        "schema": "ai_judge.autonomous_economy.v1",
        "agent_economy": {"agents": agents, "agent_count": len(agents)},
        "summary": {"agent_count": len(agents), "active_agent_count": len(agents), "allocation_entropy": 0.84},
    }


def _strategy_intelligence() -> dict:
    return {
        "schema": "ai_judge.strategy_intelligence.v1",
        "market_structure": {
            "disagreement_type": "signal_driven_disagreement",
            "disagreement_entropy": 0.68,
        },
    }


def test_recursive_civilization_constructs_governed_civilizations():
    run = build_recursive_civilization_run(
        snapshot=_snapshot(),
        autonomous_economy=_autonomous_economy(),
        autonomous_economy_state={},
        strategy_intelligence=_strategy_intelligence(),
    )

    assert run["schema"] == "ai_judge.recursive_civilization.v1"
    assert run["hard_rule"] == "strategy_ecosystems_as_evolving_civilizations_with_governance_structures_not_isolated_agents_or_economic_units"
    assert run["summary"]["civilization_count"] >= 5
    assert run["summary"]["active_civilization_count"] >= 4
    assert run["summary"]["collapsed_civilization_count"] >= 1
    assert run["summary"]["governance_mutation_count"] >= 5
    assert run["summary"]["interaction_count"] >= 2
    assert run["summary"]["meta_civilization_count"] >= 2
    assert run["summary"]["emergent_behavior_count"] >= 2

    civilizations = run["civilization_constructor"]["civilizations"]
    archetypes = {item["archetype"] for item in civilizations}
    assert "meritocratic_value_city" in archetypes
    assert "conservative_council" in archetypes
    assert "arbitrage_merchants" in archetypes
    assert "noise_quarantine" in archetypes
    assert all(item["governance_rules"] for item in civilizations)
    assert all(item["hierarchy"]["hierarchy_rule"] == "capital_and_performance_weighted_civic_rank" for item in civilizations)

    interaction_types = {
        item["interaction_type"]
        for item in run["civilization_interaction_system"]["interactions"]
    }
    assert {"compete", "collapse"}.issubset(interaction_types)
    assert run["civilization_interaction_system"]["allocation_effects"]
    assert run["meta_civilization_generator"]["candidates"]
    assert run["emergent_behavior_detector"]["behaviors"]


def test_recursive_civilization_state_persists_once(tmp_path):
    first = update_recursive_civilization_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        autonomous_economy=_autonomous_economy(),
        autonomous_economy_state={},
        strategy_intelligence=_strategy_intelligence(),
    )
    second = update_recursive_civilization_state(
        reports_root=tmp_path,
        snapshot=_snapshot(),
        autonomous_economy=_autonomous_economy(),
        autonomous_economy_state={},
        strategy_intelligence=_strategy_intelligence(),
    )

    state = json.loads(recursive_civilization_state_path(tmp_path).read_text(encoding="utf-8"))
    assert first["recursive_civilization"]["summary"]["civilization_count"] >= 5
    assert second["recursive_civilization_state"]["snapshot_count"] == 1
    assert state["schema"] == "ai_judge.recursive_civilization_state.v1"
    assert state["civilizations"]
    assert state["governance_history"]
    assert state["interaction_history"]
    assert state["meta_civilization_history"]
    assert state["emergent_behavior_history"]
