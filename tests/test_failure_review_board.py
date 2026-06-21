#!/usr/bin/env python3
"""
test_failure_review_board.py

Tests for failure_review_board.py.
Verifies failure classification, record generation, and severity assignment.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.expanduser(
    "~/Library/Application Support/AI Judge/runtime/product"
))

from analytics.failure_review_board import (
    classify_from_feedback,
    build_failure_record,
    FAILURE_CLASSES,
    SEVERITY_LEVELS,
    process_feedback_to_failures,
    _auto_severity,
)


class TestClassifyFromFeedback:
    def test_low_readability_classifies_as_cannot_understand(self):
        """readability_score <= 2 → USER_CANNOT_UNDERSTAND."""
        fb = {
            "feedback_id": "FB-001", "task_id": "BETA-LEGAL-001", "run_id": "RUN-001",
            "readability_score_1_to_5": 1,
            "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": True,
            "confusing_part": "", "free_text": "",
        }
        classes = classify_from_feedback(fb)
        assert "USER_CANNOT_UNDERSTAND" in classes

    def test_cannot_explain_why_classifies_as_cannot_understand(self):
        """can_explain_why=False → USER_CANNOT_UNDERSTAND."""
        fb = {
            "feedback_id": "FB-002", "task_id": "BETA-LEGAL-002", "run_id": "RUN-002",
            "readability_score_1_to_5": 4,
            "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": False,
            "confusing_part": "", "free_text": "",
        }
        classes = classify_from_feedback(fb)
        assert "USER_CANNOT_UNDERSTAND" in classes

    def test_no_clear_verdict(self):
        """can_state_final_answer=False → NO_CLEAR_VERDICT."""
        fb = {
            "feedback_id": "FB-003", "task_id": "BETA-LEGAL-003", "run_id": "RUN-003",
            "readability_score_1_to_5": 4,
            "can_state_final_answer": False, "can_state_next_step": True, "can_explain_why": True,
            "confusing_part": "", "free_text": "",
        }
        classes = classify_from_feedback(fb)
        assert "NO_CLEAR_VERDICT" in classes

    def test_no_actionable_next_step(self):
        """can_state_next_step=False → NO_ACTIONABLE_NEXT_STEP."""
        fb = {
            "feedback_id": "FB-004", "task_id": "BETA-LEGAL-004", "run_id": "RUN-004",
            "readability_score_1_to_5": 4,
            "can_state_final_answer": True, "can_state_next_step": False, "can_explain_why": True,
            "confusing_part": "", "free_text": "",
        }
        classes = classify_from_feedback(fb)
        assert "NO_ACTIONABLE_NEXT_STEP" in classes

    def test_report_too_long_from_confusing_part(self):
        """confusing_part mentioning length → REPORT_TOO_LONG."""
        fb = {
            "feedback_id": "FB-005", "task_id": "BETA-LEGAL-005", "run_id": "RUN-005",
            "readability_score_1_to_5": 4,
            "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": True,
            "confusing_part": "报告太长了，读不完", "free_text": "",
        }
        classes = classify_from_feedback(fb)
        assert "REPORT_TOO_LONG" in classes

    def test_multiple_failure_classes(self):
        """One feedback can trigger multiple failure classes."""
        fb = {
            "feedback_id": "FB-006", "task_id": "BETA-LEGAL-006", "run_id": "RUN-006",
            "readability_score_1_to_5": 1,
            "can_state_final_answer": False, "can_state_next_step": False, "can_explain_why": False,
            "confusing_part": "太技术化，太多术语", "free_text": "完全看不懂",
        }
        classes = classify_from_feedback(fb)
        assert "USER_CANNOT_UNDERSTAND" in classes
        assert "NO_CLEAR_VERDICT" in classes
        assert "NO_ACTIONABLE_NEXT_STEP" in classes
        assert "REPORT_TOO_TECHNICAL" in classes


class TestBuildFailureRecord:
    def test_builds_complete_record(self):
        """build_failure_record produces a complete failure entry."""
        fb = {
            "feedback_id": "FB-001", "task_id": "BETA-LEGAL-001", "run_id": "RUN-001",
            "readability_score_1_to_5": 2,
            "can_state_final_answer": True, "can_state_next_step": True, "can_explain_why": True,
            "confusing_part": "", "free_text": "",
        }
        record = build_failure_record(fb, "USER_CANNOT_UNDERSTAND", severity="P1")
        assert record["failure_id"].startswith("FAIL-")
        assert record["task_id"] == "BETA-LEGAL-001"
        assert record["failure_class"] == "USER_CANNOT_UNDERSTAND"
        assert record["severity"] == "P1"
        assert len(record["root_cause"]) > 0
        assert len(record["recommended_fix"]) > 0

    def test_all_13_failure_classes_defined(self):
        """Verify all 13 failure classes are defined."""
        assert len(FAILURE_CLASSES) >= 13
        assert "USER_CANNOT_UNDERSTAND" in FAILURE_CLASSES
        assert "NO_CLEAR_VERDICT" in FAILURE_CLASSES
        assert "NO_ACTIONABLE_NEXT_STEP" in FAILURE_CLASSES
        assert "EVIDENCE_TOO_WEAK" in FAILURE_CLASSES
        assert "SEARCH_AGENT_NOISE" in FAILURE_CLASSES
        assert "REPORT_TOO_LONG" in FAILURE_CLASSES
        assert "REPORT_TOO_TECHNICAL" in FAILURE_CLASSES
        assert "WRONG_TASK_TYPE" in FAILURE_CLASSES
        assert "MISSING_CITATION" in FAILURE_CLASSES
        assert "RUNTIME_FAILURE" in FAILURE_CLASSES
        assert "VALIDATION_FAILURE" in FAILURE_CLASSES
        assert "SAFETY_OR_SCOPE_BOUNDARY" in FAILURE_CLASSES
        assert "UNKNOWN" in FAILURE_CLASSES


class TestAutoSeverity:
    def test_runtime_failure_is_p0(self):
        fb = {"feedback_id": "FB-001", "task_id": "X", "run_id": "X"}
        assert _auto_severity("RUNTIME_FAILURE", fb) == "P0"

    def test_user_cannot_understand_is_p1(self):
        fb = {"feedback_id": "FB-001", "task_id": "X", "run_id": "X"}
        assert _auto_severity("USER_CANNOT_UNDERSTAND", fb) == "P1"

    def test_report_too_long_is_p2(self):
        fb = {"feedback_id": "FB-001", "task_id": "X", "run_id": "X"}
        assert _auto_severity("REPORT_TOO_LONG", fb) == "P2"