"""test_beta_week2_metrics_summary.py — 验证 metrics 计算"""
import json
import os
import pytest

METRICS = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_metrics.json"
RUNS = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_run_registry.json"
FEEDBACK = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_feedback.jsonl"


@pytest.fixture
def metrics():
    with open(METRICS) as f:
        return json.load(f)


@pytest.fixture
def runs():
    with open(RUNS) as f:
        return json.load(f)


def test_metrics_has_all_required_fields(metrics):
    required = [
        "week", "tasks_run", "tasks_completed", "tasks_degraded", "tasks_failed",
        "feedback_count", "external_user_count",
        "can_state_final_answer_rate", "can_state_next_step_rate", "can_explain_why_rate",
        "avg_trust_score", "avg_readability_score", "avg_actionability_score",
        "would_use_again_rate", "avg_latency_sec",
        "internal_proxy_week1", "external_user_week2", "delta_vs_week1"
    ]
    for field in required:
        assert field in metrics, f"Missing field: {field}"


def test_metrics_task_counts_sum(metrics, runs):
    assert metrics["tasks_completed"] + metrics["tasks_degraded"] + metrics["tasks_failed"] == len(runs)


def test_metrics_week1_baseline_correct(metrics):
    w1 = metrics["internal_proxy_week1"]
    assert w1["avg_trust_score"] == 4.26
    assert w1["avg_readability_score"] == 4.00
    assert w1["avg_actionability_score"] == 4.16
    assert w1["would_use_again_rate"] == 0.89


def test_delta_calculation_correct(metrics):
    w1 = metrics["internal_proxy_week1"]
    w2 = metrics["external_user_week2"]
    delta = metrics["delta_vs_week1"]

    assert abs(delta["trust_score"] - (w2["avg_trust_score"] - w1["avg_trust_score"])) < 0.01
    assert abs(delta["readability_score"] - (w2["avg_readability_score"] - w1["avg_readability_score"])) < 0.01
    assert abs(delta["actionability_score"] - (w2["avg_actionability_score"] - w1["avg_actionability_score"])) < 0.01


def test_external_week2_lower_than_week1(metrics):
    """External user scores should be systematically lower than internal proxy"""
    delta = metrics["delta_vs_week1"]
    assert delta["trust_score"] < 0, "External trust should be lower than internal"
    assert delta["readability_score"] < 0, "External readability should be lower than internal"
    assert delta["actionability_score"] < 0, "External actionability should be lower than internal"