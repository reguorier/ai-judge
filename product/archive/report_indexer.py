"""Maintain reports/index.json for client-first report runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_index(reports_root: Path) -> dict[str, Any]:
    path = reports_root / "index.json"
    if not path.exists():
        return {"schema": "ai_judge.reports_index.v1", "runs": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema": "ai_judge.reports_index.v1", "runs": [], "warnings": ["previous index was invalid JSON"]}


def update_index(reports_root: Path, summary: dict[str, Any]) -> Path:
    reports_root.mkdir(parents=True, exist_ok=True)
    path = reports_root / "index.json"
    index = load_index(reports_root)
    runs = [item for item in index.get("runs", []) if item.get("run_id") != summary.get("run_id")]
    runs.insert(0, {
        "run_id": summary.get("run_id"),
        "title": summary.get("title"),
        "mode": summary.get("mode"),
        "status": summary.get("status"),
        "reliability": summary.get("reliability"),
        "created_at": summary.get("created_at"),
        "completed_at": summary.get("completed_at"),
        "final_report_path": summary.get("final_report_path"),
        "html_report_path": summary.get("html_report_path"),
        "snapshot_id": summary.get("snapshot_id"),
        "report_snapshot_path": summary.get("report_snapshot_path"),
        "runtime_view_path": summary.get("runtime_view_path"),
        "structural_drift_score": summary.get("structural_drift_score"),
        "top_model": summary.get("top_model"),
        "deprecated_model_count": summary.get("deprecated_model_count"),
        "model_weights_path": summary.get("model_weights_path"),
        "asg_accepted_strategy_count": summary.get("asg_accepted_strategy_count"),
        "asg_production_strategy_count": summary.get("asg_production_strategy_count"),
        "production_strategies_path": summary.get("production_strategies_path"),
        "market_simulation_path": summary.get("market_simulation_path"),
        "msl_scenario_count": summary.get("msl_scenario_count"),
        "msl_monte_carlo_runs": summary.get("msl_monte_carlo_runs"),
        "msl_robust_strategy_count": summary.get("msl_robust_strategy_count"),
        "msl_top_scenario_risk": summary.get("msl_top_scenario_risk"),
        "msl_worst_scenario_id": summary.get("msl_worst_scenario_id"),
        "decision_os_path": summary.get("decision_os_path"),
        "decision_os_top_action": summary.get("decision_os_top_action"),
        "decision_os_executed_action_count": summary.get("decision_os_executed_action_count"),
        "decision_os_rejected_action_count": summary.get("decision_os_rejected_action_count"),
        "decision_os_portfolio_exposure": summary.get("decision_os_portfolio_exposure"),
        "self_improving_loop_path": summary.get("self_improving_loop_path"),
        "siel_outcome_signal_count": summary.get("siel_outcome_signal_count"),
        "siel_mean_value_error": summary.get("siel_mean_value_error"),
        "siel_policy_update_count": summary.get("siel_policy_update_count"),
        "siel_mutation_count": summary.get("siel_mutation_count"),
        "siel_learning_score": summary.get("siel_learning_score"),
        "siel_policy_direction": summary.get("siel_policy_direction"),
        "decision_policy_config_version": summary.get("decision_policy_config_version"),
        "autonomous_economy_path": summary.get("autonomous_economy_path"),
        "ael_agent_count": summary.get("ael_agent_count"),
        "ael_active_agent_count": summary.get("ael_active_agent_count"),
        "ael_terminated_agent_count": summary.get("ael_terminated_agent_count"),
        "ael_total_capital": summary.get("ael_total_capital"),
        "ael_top_agent_id": summary.get("ael_top_agent_id"),
        "ael_top_strategy_id": summary.get("ael_top_strategy_id"),
        "ael_allocation_entropy": summary.get("ael_allocation_entropy"),
        "ael_lifecycle_event_count": summary.get("ael_lifecycle_event_count"),
        "ael_clone_count": summary.get("ael_clone_count"),
        "ael_termination_count": summary.get("ael_termination_count"),
        "recursive_civilization_path": summary.get("recursive_civilization_path"),
        "rcl_civilization_count": summary.get("rcl_civilization_count"),
        "rcl_active_civilization_count": summary.get("rcl_active_civilization_count"),
        "rcl_collapsed_civilization_count": summary.get("rcl_collapsed_civilization_count"),
        "rcl_top_civilization_id": summary.get("rcl_top_civilization_id"),
        "rcl_top_governance_archetype": summary.get("rcl_top_governance_archetype"),
        "rcl_governance_mutation_count": summary.get("rcl_governance_mutation_count"),
        "rcl_interaction_count": summary.get("rcl_interaction_count"),
        "rcl_meta_civilization_count": summary.get("rcl_meta_civilization_count"),
        "rcl_emergent_behavior_count": summary.get("rcl_emergent_behavior_count"),
        "rcl_civilization_entropy": summary.get("rcl_civilization_entropy"),
    })
    index["runs"] = runs[:100]
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
