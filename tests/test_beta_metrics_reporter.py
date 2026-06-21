#!/usr/bin/env python3
"""
test_beta_metrics_reporter.py

Tests for beta_metrics_reporter.py.
Verifies metrics computation, Markdown generation, and output correctness.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.expanduser(
    "~/Library/Application Support/AI Judge/runtime/product"
))

from analytics.beta_metrics_reporter import (
    compute_metrics,
    generate_markdown,
)


class TestComputeMetrics:
    def test_empty_feedback_and_registry(self):
        """Empty inputs produce zeroed metrics."""
        metrics = compute_metrics([], [])
        assert metrics["feedback_count"] == 0  # tracks via feedbacks
        assert metrics["avg_trust_score"] == 0.0
        assert metrics["avg_readability_score"] == 0.0
        assert metrics["avg_actionability_score"] == 0.0
        assert metrics["would_use_again_rate"] == 0.0

    def test_feedback_only_computes_scores(self):
        """Metrics from feedback without registry compute scores correctly."""
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
                "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": True,
                "trust_score_1_to_5": 3, "readability_score_1_to_5": 3, "actionability_score_1_to_5": 3,
                "confusing_part": "", "missing_information": "", "would_use_again": False, "free_text": "",
                "created_at": "2026-06-08T12:00:00Z",
            },
        ]
        metrics = compute_metrics(feedbacks, [])
        assert metrics["avg_trust_score"] == 4.0
        assert metrics["avg_readability_score"] == 4.0
        assert metrics["avg_actionability_score"] == 4.0
        assert metrics["would_use_again_rate"] == 0.5

    def test_registry_counts_tasks(self):
        """Registry provides tasks_run/completed/failed counts."""
        registry = [
            {"task_id": "BETA-LEGAL-001", "run_id": "RUN-001", "status": "completed", "latency_sec": 45.0},
            {"task_id": "BETA-LEGAL-002", "run_id": "RUN-002", "status": "completed", "latency_sec": 32.0},
            {"task_id": "BETA-LEGAL-003", "run_id": "RUN-003", "status": "failed", "latency_sec": 0},
            {"task_id": "BETA-LEGAL-004", "run_id": "RUN-004", "status": "completed", "latency_sec": 28.0},
        ]
        metrics = compute_metrics([], registry)
        assert metrics["tasks_run"] == 4
        assert metrics["tasks_completed"] == 3
        assert metrics["tasks_failed"] == 1
        assert metrics["avg_latency_sec"] == 35.0  # (45+32+28)/3

    def test_mixed_inputs(self):
        """Full integration: feedback + registry."""
        feedbacks = [
            {
                "feedback_id": "FB-001", "task_id": "BETA-LEGAL-001", "run_id": "RUN-001",
                "reader_type": "普通用户",
                "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": True,
                "trust_score_1_to_5": 5, "readability_score_1_to_5": 4, "actionability_score_1_to_5": 5,
                "confusing_part": "术语有点多", "missing_information": "", "would_use_again": True,
                "free_text": "很好", "created_at": "2026-06-08T12:00:00Z",
            },
            {
                "feedback_id": "FB-002", "task_id": "BETA-LEGAL-002", "run_id": "RUN-002",
                "reader_type": "普通用户",
                "can_state_final_answer": False, "can_state_next_step": False, "can_explain_why": False,
                "trust_score_1_to_5": 1, "readability_score_1_to_5": 1, "actionability_score_1_to_5": 1,
                "confusing_part": "完全看不懂在说什么", "missing_information": "需要更多法律条文引用",
                "would_use_again": False, "free_text": "太差了", "created_at": "2026-06-08T12:00:00Z",
            },
        ]
        registry = [
            {"task_id": "BETA-LEGAL-001", "run_id": "RUN-001", "status": "completed", "latency_sec": 60},
            {"task_id": "BETA-LEGAL-002", "run_id": "RUN-002", "status": "completed", "latency_sec": 45},
        ]
        metrics = compute_metrics(feedbacks, registry)
        assert metrics["tasks_run"] == 2
        assert metrics["avg_trust_score"] == 3.0
        assert metrics["would_use_again_rate"] == 0.5

        # Failure classes should be auto-inferred
        assert len(metrics["top_failure_classes"]) >= 2  # NO_CLEAR_VERDICT and USER_CANNOT_UNDERSTAND
        # Confusing parts
        assert len(metrics["top_confusing_parts"]) >= 2


class TestGenerateMarkdown:
    def test_generates_structured_report(self):
        """Markdown output contains expected sections."""
        metrics = {
            "week": "2026-W23",
            "generated_at": "2026-06-08T12:00:00Z",
            "tasks_run": 10,
            "tasks_completed": 8,
            "tasks_failed": 2,
            "avg_latency_sec": 45.5,
            "avg_trust_score": 4.2,
            "avg_readability_score": 4.0,
            "avg_actionability_score": 3.8,
            "would_use_again_rate": 0.75,
            "top_failure_classes": [{"class": "NO_CLEAR_VERDICT", "count": 3}],
            "top_confusing_parts": [{"text": "术语太多", "count": 5}],
            "recommended_next_fixes": ["优化可读性", "增强证据展示"],
        }
        md = generate_markdown(metrics)
        assert "Deep Judge Beta" in md
        assert "2026-W23" in md
        assert "概览" in md
        assert "4.2" in md
        assert "75.0%" in md
        assert "主要失败类型" in md
        assert "NO_CLEAR_VERDICT" in md
        assert "优化可读性" in md

    def test_empty_metrics_still_generates_valid_markdown(self):
        """Even empty metrics produce valid markdown."""
        metrics = {
            "week": "N/A",
            "generated_at": "",
            "tasks_run": 0, "tasks_completed": 0, "tasks_failed": 0,
            "avg_latency_sec": 0, "avg_trust_score": 0, "avg_readability_score": 0,
            "avg_actionability_score": 0, "would_use_again_rate": 0,
            "top_failure_classes": [], "top_confusing_parts": [], "recommended_next_fixes": [],
        }
        md = generate_markdown(metrics)
        assert "Deep Judge Beta" in md
        assert "（无失败记录）" in md
        assert "（无困惑反馈）" in md