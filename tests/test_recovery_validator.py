#!/usr/bin/env python3
"""Tests for recovery_validator.py.

Validates that all 6 failure scenarios produce correct statuses
and that forbidden statuses are properly rejected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.product.observability.recovery_validator import (
    FAILURE_SCENARIOS,
    RecoveryValidator,
    RecoveryValidationReport,
)


class TestRecoveryValidator:
    """Test the recovery validator module."""

    def test_validator_importable(self):
        assert RecoveryValidator is not None

    def test_all_6_scenarios_defined(self):
        assert len(FAILURE_SCENARIOS) == 6

    def test_scenario_search_timeout(self):
        result = RecoveryValidator.validate_scenario(
            "search_timeout", actual_status="degraded"
        )
        assert result.passed is True
        assert result.retryable is True

    def test_scenario_search_timeout_forbidden_completed(self):
        result = RecoveryValidator.validate_scenario(
            "search_timeout", actual_status="completed"
        )
        assert result.passed is False

    def test_scenario_no_reasoning_source(self):
        result = RecoveryValidator.validate_scenario(
            "no_reasoning_source",
            actual_status="failed",
            actual_reason="deep_judge_no_substantive_reasoning",
        )
        assert result.passed is True

    def test_scenario_no_reasoning_source_forbidden_completed(self):
        result = RecoveryValidator.validate_scenario(
            "no_reasoning_source", actual_status="completed"
        )
        assert result.passed is False

    def test_scenario_no_reasoning_source_wrong_reason(self):
        result = RecoveryValidator.validate_scenario(
            "no_reasoning_source",
            actual_status="failed",
            actual_reason="wrong_reason",
        )
        assert result.passed is False

    def test_scenario_renderer_validation_fail(self):
        result = RecoveryValidator.validate_scenario(
            "renderer_validation_fail", actual_status="blocked"
        )
        assert result.passed is True

    def test_scenario_renderer_validation_fail_forbidden_completed(self):
        result = RecoveryValidator.validate_scenario(
            "renderer_validation_fail", actual_status="completed"
        )
        assert result.passed is False

    def test_scenario_artifact_write_fail(self):
        result = RecoveryValidator.validate_scenario(
            "artifact_write_fail", actual_status="failed"
        )
        assert result.passed is True
        assert result.retryable is True

    def test_scenario_artifact_write_fail_forbidden_completed(self):
        result = RecoveryValidator.validate_scenario(
            "artifact_write_fail", actual_status="completed"
        )
        assert result.passed is False

    def test_scenario_seat_partial_failure(self):
        result = RecoveryValidator.validate_scenario(
            "seat_partial_failure", actual_status="completed_with_warnings"
        )
        assert result.passed is True
        assert result.safe_to_show_partial is True

    def test_scenario_seat_partial_failure_forbidden_completed(self):
        result = RecoveryValidator.validate_scenario(
            "seat_partial_failure", actual_status="completed"
        )
        assert result.passed is False

    def test_scenario_followup_no_source(self):
        result = RecoveryValidator.validate_scenario(
            "followup_no_source", actual_status="not_generated"
        )
        assert result.passed is True
        assert result.retryable is False

    def test_scenario_followup_no_source_forbidden_completed(self):
        result = RecoveryValidator.validate_scenario(
            "followup_no_source", actual_status="completed"
        )
        assert result.passed is False

    def test_validate_all_passes_all(self):
        scenarios = {
            "search_timeout": {"status": "degraded"},
            "no_reasoning_source": {
                "status": "failed",
                "reason": "deep_judge_no_substantive_reasoning",
            },
            "renderer_validation_fail": {"status": "blocked"},
            "artifact_write_fail": {"status": "failed"},
            "seat_partial_failure": {"status": "completed_with_warnings"},
            "followup_no_source": {"status": "not_generated"},
        }
        report = RecoveryValidator.validate_all(scenarios, run_id="test-all-pass")
        assert report.overall_passed is True
        assert report.scenarios_passed == 6
        assert report.scenarios_failed == 0

    def test_validate_all_fails_some(self):
        scenarios = {
            "search_timeout": {"status": "completed"},  # wrong!
            "no_reasoning_source": {
                "status": "failed",
                "reason": "deep_judge_no_substantive_reasoning",
            },
            "renderer_validation_fail": {"status": "blocked"},
            "artifact_write_fail": {"status": "failed"},
            "seat_partial_failure": {"status": "completed_with_warnings"},
            "followup_no_source": {"status": "not_generated"},
        }
        report = RecoveryValidator.validate_all(scenarios, run_id="test-some-fail")
        assert report.overall_passed is False
        assert report.scenarios_failed >= 1

    def test_report_to_dict_serializable(self):
        scenarios = {
            "search_timeout": {"status": "degraded"},
        }
        report = RecoveryValidator.validate_all(scenarios, run_id="test-dict")
        d = report.to_dict()
        import json
        json.dumps(d)
        assert d["run_id"] == "test-dict"

    def test_user_visible_message_present(self):
        for name, definition in FAILURE_SCENARIOS.items():
            assert "user_visible_message" in definition
            assert len(definition["user_visible_message"]) > 0

    def test_retryable_flag_set(self):
        for name, definition in FAILURE_SCENARIOS.items():
            assert isinstance(definition["retryable"], bool)

    def test_safe_to_show_partial_flag_set(self):
        for name, definition in FAILURE_SCENARIOS.items():
            assert isinstance(definition["safe_to_show_partial"], bool)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-q"]))