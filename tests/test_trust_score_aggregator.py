#!/usr/bin/env python3
"""
test_trust_score_aggregator.py

Tests for trust_score_aggregator.py.
Verifies aggregation logic, pass/fail thresholds, and empty input handling.
"""

import json
import os
import sys
import tempfile
import pytest

# Add analytics to path
sys.path.insert(0, os.path.expanduser(
    "~/Library/Application Support/AI Judge/runtime/product"
))

from analytics.trust_score_aggregator import (
    aggregate,
    load_feedback,
    PASS_THRESHOLDS,
    _evaluate_pass,
    _empty_metrics,
)


class TestAggregate:
    def test_empty_feedback_returns_zero_metrics(self):
        """Empty feedback list returns zeroed metrics."""
        result = aggregate([])
        assert result["feedback_count"] == 0
        assert result["can_state_final_answer_rate"] == 0.0
        assert result["avg_trust_score"] == 0.0

    def test_all_perfect_feedback(self):
        """All scores maxed out -> all rates 100%, averages 5.0."""
        feedbacks = [
            {
                "feedback_id": f"FB-{i:03d}",
                "task_id": f"BETA-LEGAL-00{i}",
                "run_id": f"RUN-00{i}",
                "reader_type": "专业用户",
                "can_state_final_answer": True,
                "can_state_next_step": True,
                "can_explain_why": True,
                "trust_score_1_to_5": 5,
                "readability_score_1_to_5": 5,
                "actionability_score_1_to_5": 5,
                "confusing_part": "",
                "missing_information": "",
                "would_use_again": True,
                "free_text": "",
                "created_at": "2026-06-08T12:00:00Z",
            }
            for i in range(10)
        ]
        result = aggregate(feedbacks)
        assert result["feedback_count"] == 10
        assert result["can_state_final_answer_rate"] == 1.0
        assert result["can_state_next_step_rate"] == 1.0
        assert result["can_explain_why_rate"] == 1.0
        assert result["avg_trust_score"] == 5.0
        assert result["avg_readability_score"] == 5.0
        assert result["avg_actionability_score"] == 5.0
        assert result["would_use_again_rate"] == 1.0

    def test_mixed_feedback(self):
        """Mixed scores compute correct averages."""
        feedbacks = [
            {
                "feedback_id": "FB-001", "task_id": "BETA-LEGAL-001", "run_id": "RUN-001",
                "reader_type": "普通用户",
                "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": True,
                "trust_score_1_to_5": 5, "readability_score_1_to_5": 5, "actionability_score_1_to_5": 5,
                "confusing_part": "", "missing_information": "", "would_use_again": True, "free_text": "",
                "created_at": "2026-06-08T12:00:00Z",
            },
            {
                "feedback_id": "FB-002", "task_id": "BETA-LEGAL-002", "run_id": "RUN-002",
                "reader_type": "普通用户",
                "can_state_final_answer": False, "can_state_next_step": False, "can_explain_why": False,
                "trust_score_1_to_5": 1, "readability_score_1_to_5": 1, "actionability_score_1_to_5": 1,
                "confusing_part": "完全看不懂", "missing_information": "", "would_use_again": False,
                "free_text": "太差了", "created_at": "2026-06-08T12:30:00Z",
            },
        ]
        result = aggregate(feedbacks)
        assert result["can_state_final_answer_rate"] == 0.5
        assert result["can_state_next_step_rate"] == 0.5
        assert result["can_explain_why_rate"] == 0.5
        assert result["avg_trust_score"] == 3.0
        assert result["avg_readability_score"] == 3.0
        assert result["avg_actionability_score"] == 3.0
        assert result["would_use_again_rate"] == 0.5

    def test_confusing_part_top5(self):
        """Confusing parts are counted and top-5 returned."""
        feedbacks = []
        for i in range(5):
            feedbacks.append({
                "feedback_id": f"FB-{i:03d}", "task_id": "BETA-LEGAL-001", "run_id": f"RUN-{i}",
                "reader_type": "普通用户",
                "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": True,
                "trust_score_1_to_5": 4, "readability_score_1_to_5": 4, "actionability_score_1_to_5": 4,
                "confusing_part": "术语太多看不懂", "missing_information": "", "would_use_again": True,
                "free_text": "", "created_at": "2026-06-08T12:00:00Z",
            })
        for i in range(3):
            feedbacks.append({
                "feedback_id": f"FB-{5+i:03d}", "task_id": "BETA-LEGAL-002", "run_id": f"RUN-{5+i}",
                "reader_type": "普通用户",
                "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": True,
                "trust_score_1_to_5": 3, "readability_score_1_to_5": 3, "actionability_score_1_to_5": 3,
                "confusing_part": "结论不够明确", "missing_information": "", "would_use_again": True,
                "free_text": "", "created_at": "2026-06-08T12:00:00Z",
            })
        result = aggregate(feedbacks)
        top5 = result["confusing_part_top5"]
        assert len(top5) == 2
        # Most common should be first
        assert top5[0]["count"] == 5


class TestEvaluatePass:
    def test_all_pass_when_above_thresholds(self):
        """All metrics above thresholds → ALL_PASS=true."""
        metrics = {
            "can_state_final_answer_rate": 0.95,
            "can_state_next_step_rate": 0.90,
            "can_explain_why_rate": 0.85,
            "avg_trust_score": 4.5,
            "avg_readability_score": 4.2,
            "avg_actionability_score": 4.1,
            "would_use_again_rate": 0.80,
        }
        check = _evaluate_pass(metrics)
        assert check["ALL_PASS"] is True

    def test_fail_when_below_thresholds(self):
        """Metrics below thresholds → individual fails, ALL_PASS=false."""
        metrics = {
            "can_state_final_answer_rate": 0.60,
            "can_state_next_step_rate": 0.70,
            "can_explain_why_rate": 0.50,
            "avg_trust_score": 3.0,
            "avg_readability_score": 3.5,
            "avg_actionability_score": 2.5,
            "would_use_again_rate": 0.40,
        }
        check = _evaluate_pass(metrics)
        assert check["ALL_PASS"] is False
        for key in PASS_THRESHOLDS:
            assert check[key]["passed"] is False