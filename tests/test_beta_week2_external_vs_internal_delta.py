"""test_beta_week2_external_vs_internal_delta.py — 验证 delta 计算"""
import json
import os
import pytest

METRICS = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_metrics.json"
W1_METRICS = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week1_metrics.json"


@pytest.fixture
def w2_metrics():
    with open(METRICS) as f:
        return json.load(f)


@pytest.fixture
def w1_metrics():
    with open(W1_METRICS) as f:
        return json.load(f)


def test_delta_readability_is_largest_gap(w2_metrics):
    """Readability should show the largest gap between internal and external"""
    delta = w2_metrics["delta_vs_week1"]
    gaps = [delta["trust_score"], delta["readability_score"], delta["actionability_score"]]
    # readability should be the most negative (largest absolute gap)
    assert delta["readability_score"] <= delta["trust_score"], "Readability gap should be >= trust gap"
    assert delta["readability_score"] <= delta["actionability_score"], "Readability gap should be >= actionability gap"


def test_delta_within_expected_range(w2_metrics):
    """Gap should be in the 0.2-0.7 range for realistic simulation"""
    delta = w2_metrics["delta_vs_week1"]
    for key in ["trust_score", "readability_score", "actionability_score"]:
        assert -0.7 <= delta[key] <= -0.2, f"{key} delta {delta[key]} outside expected -0.7 to -0.2 range"


def test_w1_w2_metrics_coherence(w1_metrics, w2_metrics):
    """Week 1 and Week 2 metrics should be coherent (same schema)"""
    for key in ["avg_trust_score", "avg_readability_score", "avg_actionability_score", "would_use_again_rate"]:
        assert key in w1_metrics, f"W1 missing {key}"
        assert key in w2_metrics["internal_proxy_week1"], f"W2 missing {key} in internal_proxy_week1"


def test_external_vs_internal_user_type_difference(w2_metrics):
    """Verify the external user type distinction is meaningful"""
    w1 = w2_metrics["internal_proxy_week1"]
    w2 = w2_metrics["external_user_week2"]
    # w2 should differ from w1
    assert w2["avg_readability_score"] != w1["avg_readability_score"], "No meaningful difference detected"