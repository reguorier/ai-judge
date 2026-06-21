"""Runtime report snapshots, diff, replay and model memory tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.final_report_builder import build_client_final_report, write_report_bundle
from product.reporting.runtime.snapshots import SnapshotImmutabilityError, persist_report_snapshot


def _report(run_id: str, *, stance: str) -> dict:
    return build_client_final_report(
        run_id=run_id,
        question="股东以股权清偿对公司赔偿债务，法院能否直接裁定股权抵债？",
        mode="deep_judge",
        total_seats=1,
        valid_seats=1,
        failed_seats=0,
        seat_outputs=[
            {
                "seat_id": "legal_seat",
                "display_name": "法律席位",
                "stance": stance,
                "answer": (
                    "支持将股权作为被执行财产进行冻结、评估、拍卖或变卖，"
                    "但不建议公司直接受让自身股权抵债；应通过价款清偿路径处理。"
                    if stance == "support"
                    else "反对直接裁定公司受让自身股权抵债，原因是公司法资本维持、"
                    "减资和登记程序风险较高；只能考虑法院监督下变价清偿。"
                ),
            }
        ],
    )


def test_runtime_snapshot_diff_memory_and_replay_are_written(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_JUDGE_MODEL_STABILITY_PATH", str(tmp_path / "model_stability.json"))

    first = write_report_bundle(_report("runtime-run-1", stance="support"), reports_root=tmp_path)
    second = write_report_bundle(_report("runtime-run-2", stance="oppose"), reports_root=tmp_path)

    first_snapshot = json.loads(Path(first["paths"]["report_snapshot"]).read_text(encoding="utf-8"))
    second_snapshot = json.loads(Path(second["paths"]["report_snapshot"]).read_text(encoding="utf-8"))
    diff = json.loads(Path(second["paths"]["report_diff"]).read_text(encoding="utf-8"))
    memory = json.loads(Path(second["paths"]["model_memory"]).read_text(encoding="utf-8"))
    strategy = json.loads(Path(second["paths"]["strategy_intelligence"]).read_text(encoding="utf-8"))
    strategy_state = json.loads(Path(second["paths"]["strategy_state"]).read_text(encoding="utf-8"))
    meta_judge = json.loads(Path(second["paths"]["meta_judge"]).read_text(encoding="utf-8"))
    model_weights = json.loads(Path(second["paths"]["model_weights"]).read_text(encoding="utf-8"))
    autonomous_strategy = json.loads(Path(second["paths"]["autonomous_strategy"]).read_text(encoding="utf-8"))
    production_strategies = json.loads(Path(second["paths"]["production_strategies"]).read_text(encoding="utf-8"))
    market_simulation = json.loads(Path(second["paths"]["market_simulation"]).read_text(encoding="utf-8"))
    decision_os = json.loads(Path(second["paths"]["decision_os"]).read_text(encoding="utf-8"))
    self_improving_loop = json.loads(Path(second["paths"]["self_improving_loop"]).read_text(encoding="utf-8"))
    self_improving_loop_state = json.loads(Path(second["paths"]["self_improving_loop_state"]).read_text(encoding="utf-8"))
    decision_policy_config = json.loads(Path(second["paths"]["decision_policy_config"]).read_text(encoding="utf-8"))
    autonomous_economy = json.loads(Path(second["paths"]["autonomous_economy"]).read_text(encoding="utf-8"))
    autonomous_economy_state = json.loads(Path(second["paths"]["autonomous_economy_state"]).read_text(encoding="utf-8"))
    recursive_civilization = json.loads(Path(second["paths"]["recursive_civilization"]).read_text(encoding="utf-8"))
    recursive_civilization_state = json.loads(Path(second["paths"]["recursive_civilization_state"]).read_text(encoding="utf-8"))
    replay_html = Path(second["paths"]["replay_report"]).read_text(encoding="utf-8")
    runtime_html = Path(second["paths"]["runtime_view"]).read_text(encoding="utf-8")
    index = json.loads(Path(second["paths"]["snapshot_index"]).read_text(encoding="utf-8"))
    reports_index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))

    assert first_snapshot["schema"] == "ai_judge.report_snapshot.v1"
    assert second_snapshot["previous_snapshot_id"] == first_snapshot["snapshot_id"]
    assert diff["schema"] == "ai_judge.report_diff.v1"
    assert diff["previous_snapshot_id"] == first_snapshot["snapshot_id"]
    assert diff["model_behavior_changes"][0]["stance_from"] == "support"
    assert diff["model_behavior_changes"][0]["stance_to"] == "oppose"
    assert second["summary"]["snapshot_id"] == second_snapshot["snapshot_id"]
    assert second["summary"]["structural_drift_score"] == diff["structural_drift_score"]
    assert second["summary"]["strategy_intelligence_path"] == second["paths"]["strategy_intelligence"]
    assert second["summary"]["strategy_state_path"] == second["paths"]["strategy_state"]
    assert second["summary"]["meta_judge_path"] == second["paths"]["meta_judge"]
    assert second["summary"]["model_weights_path"] == second["paths"]["model_weights"]
    assert second["summary"]["autonomous_strategy_path"] == second["paths"]["autonomous_strategy"]
    assert second["summary"]["production_strategies_path"] == second["paths"]["production_strategies"]
    assert second["summary"]["market_simulation_path"] == second["paths"]["market_simulation"]
    assert second["summary"]["market_simulation_state_path"] == second["paths"]["market_simulation_state"]
    assert second["summary"]["decision_os_path"] == second["paths"]["decision_os"]
    assert second["summary"]["decision_os_state_path"] == second["paths"]["decision_os_state"]
    assert second["summary"]["self_improving_loop_path"] == second["paths"]["self_improving_loop"]
    assert second["summary"]["self_improving_loop_state_path"] == second["paths"]["self_improving_loop_state"]
    assert second["summary"]["decision_policy_config_path"] == second["paths"]["decision_policy_config"]
    assert second["summary"]["autonomous_economy_path"] == second["paths"]["autonomous_economy"]
    assert second["summary"]["autonomous_economy_state_path"] == second["paths"]["autonomous_economy_state"]
    assert second["summary"]["recursive_civilization_path"] == second["paths"]["recursive_civilization"]
    assert second["summary"]["recursive_civilization_state_path"] == second["paths"]["recursive_civilization_state"]
    assert "strategy_drift_score" in second["summary"]
    assert "deprecated_model_count" in second["summary"]
    assert "asg_accepted_strategy_count" in second["summary"]
    assert len(index["snapshots"]) == 2
    assert reports_index["runs"][0]["snapshot_id"] == second_snapshot["snapshot_id"]
    assert reports_index["runs"][0]["runtime_view_path"] == second["paths"]["runtime_view"]

    profile = memory["profiles"]["legal_seat"]
    assert profile["bias_profile"]["dominant_stance"] in {"support", "oppose"}
    assert profile["contradiction_rate"] == 1.0
    assert profile["risk_profile"]["invalid_rate"] == 0.0
    assert strategy["schema"] == "ai_judge.strategy_intelligence.v1"
    assert strategy["model_strategies"]["legal_seat"]["strategy_type"] in {
        "CONSERVATIVE_EDGE",
        "AGGRESSIVE_VALUE",
        "OVERCONFIDENCE_CLUSTER",
    }
    assert strategy_state["schema"] == "ai_judge.strategy_state.v1"
    assert strategy_state["profiles"]["legal_seat"]["runs_seen"] == 2
    assert meta_judge["schema"] == "ai_judge.meta_judge.v1"
    assert meta_judge["summary"]["top_model"] == "legal_seat"
    assert model_weights["schema"] == "ai_judge.model_weights.v1"
    assert "legal_seat" in model_weights["weights"]
    assert autonomous_strategy["schema"] == "ai_judge.autonomous_strategy.v1"
    assert production_strategies["schema"] == "ai_judge.production_strategies.v1"
    assert production_strategies["admission_rule"] == "accepted_backtest_only_v1"
    assert market_simulation["schema"] == "ai_judge.market_simulation.v1"
    assert market_simulation["monte_carlo_runs"] >= 10_000
    assert market_simulation["summary"]["scenario_count"] >= 5
    assert decision_os["schema"] == "ai_judge.decision_os.v1"
    assert decision_os["hard_rule"] == "constrained_autonomous_agent_not_advisory_system"
    assert decision_os["summary"]["executed_action_count"] >= 1
    assert self_improving_loop["schema"] == "ai_judge.self_improving_execution_loop.v1"
    assert self_improving_loop["hard_rule"] == "self_modifying_decision_system_with_traceable_evolution_history"
    assert self_improving_loop["summary"]["outcome_signal_count"] >= 1
    assert self_improving_loop_state["schema"] == "ai_judge.self_improving_execution_loop_state.v1"
    assert self_improving_loop_state["learning_curve"]
    assert decision_policy_config["schema"] == "ai_judge.decision_policy_config.v1"
    assert second["summary"]["siel_policy_update_count"] >= 1
    assert autonomous_economy["schema"] == "ai_judge.autonomous_economy.v1"
    assert autonomous_economy["hard_rule"] == "internal_economy_of_competing_decision_making_agents_not_single_optimizer"
    assert autonomous_economy["summary"]["agent_count"] >= 1
    assert autonomous_economy_state["schema"] == "ai_judge.autonomous_economy_state.v1"
    assert autonomous_economy_state["agents"]
    assert second["summary"]["ael_agent_count"] >= 1
    assert recursive_civilization["schema"] == "ai_judge.recursive_civilization.v1"
    assert recursive_civilization["hard_rule"] == "strategy_ecosystems_as_evolving_civilizations_with_governance_structures_not_isolated_agents_or_economic_units"
    assert recursive_civilization["summary"]["civilization_count"] >= 1
    assert recursive_civilization_state["schema"] == "ai_judge.recursive_civilization_state.v1"
    assert recursive_civilization_state["civilizations"]
    assert second["summary"]["rcl_civilization_count"] >= 1
    assert 'content="judge-ir-component-renderer" name="ai-judge-renderer"' in replay_html
    assert 'content="runtime-temporal-renderer" name="ai-judge-renderer"' in runtime_html
    assert "Timeline View" in runtime_html
    assert "Diff Visualization" in runtime_html
    assert "Model Ranking Board" in runtime_html
    assert "Weight Distribution Visualization" in runtime_html
    assert "Meta-Judge Evolution Timeline" in runtime_html
    assert "Strategy Lab" in runtime_html
    assert "Mutation Tree Visualization" in runtime_html
    assert "Backtest Performance Dashboard" in runtime_html
    assert "Scenario Explorer" in runtime_html
    assert "Outcome Distribution View" in runtime_html
    assert "Strategy Stress Test Panel" in runtime_html
    assert "Decision Stream Panel" in runtime_html
    assert "Portfolio Exposure Map" in runtime_html
    assert "Constraint Violation Monitor" in runtime_html
    assert "Execution Log Timeline" in runtime_html
    assert "Evolution Loop Dashboard" in runtime_html
    assert "Policy Drift Timeline" in runtime_html
    assert "System Mutation Log Viewer" in runtime_html
    assert "Learning Curve Visualization" in runtime_html
    assert "Strategy Economy Dashboard" in runtime_html
    assert "Capital Flow Visualization" in runtime_html
    assert "Agent Birth/Death Log" in runtime_html
    assert "Internal Market Allocation View" in runtime_html
    assert "Civilization Map View" in runtime_html
    assert "Governance Evolution Timeline" in runtime_html
    assert "Inter-Civilization Interaction Graph" in runtime_html
    assert "Emergent Behavior Detector Panel" in runtime_html
    assert "Strategy Map Dashboard" in runtime_html
    assert "Cluster View" in runtime_html
    assert "Drift Timeline" in runtime_html
    assert "Model Drift Panel" in runtime_html


def test_report_snapshot_is_immutable(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_JUDGE_MODEL_STABILITY_PATH", str(tmp_path / "model_stability.json"))
    bundle = write_report_bundle(_report("runtime-immutable", stance="support"), reports_root=tmp_path)
    snapshot = json.loads(Path(bundle["paths"]["report_snapshot"]).read_text(encoding="utf-8"))

    persist_report_snapshot(tmp_path, snapshot)
    mutated = dict(snapshot)
    mutated["title"] = "mutated title"

    try:
        persist_report_snapshot(tmp_path, mutated)
    except SnapshotImmutabilityError as exc:
        assert "snapshot_already_exists_with_different_content" in str(exc)
    else:
        raise AssertionError("mutated snapshot overwrite was accepted")
