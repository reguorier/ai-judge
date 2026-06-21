#!/usr/bin/env python3
"""test_beta_week3_readability_metrics.py — 验证 Week 3 readability 指标。

最低要求：
- 指标 JSON 结构完整
- delta vs Week 2 计算正确
- reader_type 分解完整
- 通过阈值判断正确
"""

import json
import os
import sys
import pytest

sys.path.insert(
    0,
    os.path.expanduser(
        "~/Library/Application Support/AI Judge/runtime/product"
    ),
)

from readability.readability_metrics import ReadabilityMetrics, compute_readability_metrics

BETA_OPS_DIR = os.path.expanduser(
    "~/Library/Application Support/AI Judge/runtime/product/beta_ops"
)


class TestBetaWeek3ReadabilityMetrics:
    """Week 3 Readability Metrics 验证"""

    def test_metrics_json_structure_complete(self):
        metrics_path = os.path.join(BETA_OPS_DIR, "beta_week3_metrics.json")
        if not os.path.exists(metrics_path):
            pytest.skip("beta_week3_metrics.json not found")

        with open(metrics_path, "r") as f:
            data = json.load(f)

        assert data["week"] == 3
        assert "baseline_week2" in data
        assert "week3_results" in data
        assert "reader_type_breakdown" in data
        assert "delta_vs_week2" in data
        assert "pass_thresholds" in data

    def test_week3_readability_above_threshold(self):
        metrics_path = os.path.join(BETA_OPS_DIR, "beta_week3_metrics.json")
        if not os.path.exists(metrics_path):
            pytest.skip("beta_week3_metrics.json not found")

        with open(metrics_path, "r") as f:
            data = json.load(f)

        readability = data["week3_results"]["avg_readability_score"]
        assert readability >= 3.8, f"Week 3 readability {readability} < 3.8"

    def test_delta_vs_week2_positive(self):
        metrics_path = os.path.join(BETA_OPS_DIR, "beta_week3_metrics.json")
        if not os.path.exists(metrics_path):
            pytest.skip("beta_week3_metrics.json not found")

        with open(metrics_path, "r") as f:
            data = json.load(f)

        delta = data["delta_vs_week2"]["readability_delta"]
        assert delta > 0, f"Delta should be positive, got {delta}"

    def test_ordinary_user_delta_sufficient(self):
        metrics_path = os.path.join(BETA_OPS_DIR, "beta_week3_metrics.json")
        if not os.path.exists(metrics_path):
            pytest.skip("beta_week3_metrics.json not found")

        with open(metrics_path, "r") as f:
            data = json.load(f)

        ou_delta = data["delta_vs_week2"]["ordinary_user_readability_delta"]
        assert ou_delta >= 0.35, f"ordinary_user delta {ou_delta} < 0.35"

    def test_all_reader_types_present_in_breakdown(self):
        metrics_path = os.path.join(BETA_OPS_DIR, "beta_week3_metrics.json")
        if not os.path.exists(metrics_path):
            pytest.skip("beta_week3_metrics.json not found")

        with open(metrics_path, "r") as f:
            data = json.load(f)

        breakdown = data["reader_type_breakdown"]
        for rt in ["ordinary_user", "pm_founder", "professional_user", "legal_compliance_user"]:
            assert rt in breakdown, f"Missing {rt} in reader_type_breakdown"

    def test_compute_delta_logic(self):
        rm = ReadabilityMetrics()
        w2 = {"avg_readability_score": 3.42, "avg_trust_score": 3.95}
        w3 = {"avg_readability_score": 3.95, "avg_trust_score": 3.92}

        delta = rm.compute_delta(w2, w3)
        assert delta["delta"] == 0.53, f"Expected 0.53, got {delta['delta']}"
        assert delta["trust_delta"] == -0.03, f"Expected -0.03, got {delta['trust_delta']}"

    def test_feedback_jsonl_structure(self):
        feedback_path = os.path.join(BETA_OPS_DIR, "beta_week3_feedback.jsonl")
        if not os.path.exists(feedback_path):
            pytest.skip("beta_week3_feedback.jsonl not found")

        with open(feedback_path, "r") as f:
            lines = [l.strip() for l in f if l.strip()]

        assert len(lines) == 12, f"Expected 12 feedback entries, got {len(lines)}"

        for line in lines:
            entry = json.loads(line)
            assert "feedback_id" in entry
            assert "task_id" in entry
            assert "reader_type" in entry
            assert "readability_score_1_to_5" in entry
            assert 1 <= entry["readability_score_1_to_5"] <= 5
            assert "is_external_user" in entry
            assert entry["is_external_user"]  # Week 3 external