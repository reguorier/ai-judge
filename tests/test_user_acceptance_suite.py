#!/usr/bin/env python3
"""Tests for run_user_acceptance_suite.sh and summarize_user_acceptance_release.py.

Validates that the acceptance suite script and summary generator
work correctly with mock data.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.summarize_user_acceptance_release import build_summary


class TestUserAcceptanceSuite:
    """Test the user acceptance suite components."""

    def test_summary_generator_importable(self):
        from scripts.summarize_user_acceptance_release import build_summary
        assert callable(build_summary)

    def test_build_summary_all_pass(self):
        summary = build_summary(
            tasks_total=12,
            tasks_passed=12,
            tasks_failed=0,
            avg_decision_brief_score=88.5,
            avg_professional_review_score=82.1,
            avg_latency_sec=46.2,
            failure_recovery_passed=True,
            artifact_validation_passed=True,
            aj_report_v1_validation_passed=True,
        )
        assert summary["overall_pass"] is True
        assert summary["tasks_total"] == 12
        assert summary["tasks_passed"] == 12

    def test_build_summary_not_all_pass(self):
        summary = build_summary(
            tasks_total=12,
            tasks_passed=10,
            tasks_failed=2,
            avg_decision_brief_score=88.5,
            avg_professional_review_score=82.1,
        )
        assert summary["overall_pass"] is False

    def test_build_summary_low_scores(self):
        summary = build_summary(
            tasks_total=12,
            tasks_passed=12,
            avg_decision_brief_score=70.0,  # < 80
            avg_professional_review_score=70.0,  # < 75
        )
        assert summary["overall_pass"] is False

    def test_build_summary_too_few_tasks(self):
        summary = build_summary(
            tasks_total=10,  # < 12
            tasks_passed=10,
            avg_decision_brief_score=88.5,
            avg_professional_review_score=82.1,
        )
        assert summary["overall_pass"] is False

    def test_summary_json_serializable(self):
        summary = build_summary(
            tasks_total=12, tasks_passed=12,
            avg_decision_brief_score=88.5,
            avg_professional_review_score=82.1,
        )
        json.dumps(summary)

    def test_summary_has_required_fields(self):
        summary = build_summary(
            tasks_total=12, tasks_passed=12,
            avg_decision_brief_score=88.5,
            avg_professional_review_score=82.1,
        )
        required = {
            "release", "tasks_total", "tasks_passed",
            "avg_decision_brief_score", "avg_professional_review_score",
            "failure_recovery_passed", "overall_pass",
        }
        for field in required:
            assert field in summary, f"Missing field: {field}"

    def test_summary_pass_rate_calculation(self):
        summary = build_summary(tasks_total=12, tasks_passed=9)
        assert summary["pass_rate_pct"] == 75.0

    def test_summary_human_feedback_fields(self):
        summary = build_summary(
            tasks_total=12, tasks_passed=12,
            human_feedback_sample_size=5,
            human_feedback_avg_trust_score=4.2,
        )
        assert summary["human_feedback"]["sample_size"] == 5
        assert summary["human_feedback"]["avg_trust_score"] == 4.2

    def test_suite_script_exists(self):
        script = (
            Path(__file__).resolve().parent.parent
            / "scripts" / "run_user_acceptance_suite.sh"
        )
        assert script.exists(), f"Suite script not found: {script}"

    def test_failure_recovery_script_exists(self):
        script = (
            Path(__file__).resolve().parent.parent
            / "scripts" / "run_failure_recovery_suite.sh"
        )
        assert script.exists(), f"Failure recovery script not found: {script}"

    def test_suite_script_is_executable(self):
        script = (
            Path(__file__).resolve().parent.parent
            / "scripts" / "run_user_acceptance_suite.sh"
        )
        # Check if file has execute permission (best-effort on macOS)
        import os
        assert os.access(str(script), os.X_OK), f"Script not executable: {script}"

    def test_summary_script_exists(self):
        script = (
            Path(__file__).resolve().parent.parent
            / "scripts" / "summarize_user_acceptance_release.py"
        )
        assert script.exists(), f"Summary script not found: {script}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-q"]))