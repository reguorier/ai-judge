"""test_beta_week2_failure_review.py — 验证 failure review"""
import json
import os
import pytest

FIXTURE = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_failure_review.jsonl"

VALID_CLASSES = {
    "USER_CANNOT_UNDERSTAND", "NO_CLEAR_VERDICT", "NO_ACTIONABLE_NEXT_STEP",
    "EVIDENCE_TOO_WEAK", "SEARCH_AGENT_NOISE", "REPORT_TOO_LONG",
    "REPORT_TOO_TECHNICAL", "WRONG_TASK_TYPE", "MISSING_CITATION",
    "RUNTIME_FAILURE", "VALIDATION_FAILURE", "SAFETY_OR_SCOPE_BOUNDARY", "UNKNOWN"
}


@pytest.fixture
def failures():
    entries = []
    with open(FIXTURE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def test_failure_count_between_4_and_6(failures):
    assert 4 <= len(failures) <= 6, f"Expected 4-6 failures, got {len(failures)}"


def test_all_failures_use_valid_classification(failures):
    for fr in failures:
        assert fr["failure_class"] in VALID_CLASSES, \
            f"{fr['failure_id']}: invalid class '{fr['failure_class']}'"


def test_all_failures_have_required_fields(failures):
    required = ["failure_id", "task_id", "run_id", "failure_class", "severity",
                "root_cause", "recommended_fix", "owner", "regression_test_needed",
                "is_external", "user_id", "created_at"]
    for fr in failures:
        for field in required:
            assert field in fr, f"{fr.get('failure_id', '?')} missing {field}"


def test_at_least_one_p0_severity(failures):
    p0 = [fr for fr in failures if fr["severity"] == "P0"]
    assert len(p0) >= 1, "Need at least 1 P0 failure (RUNTIME_FAILURE from audit task)"


def test_covers_failed_and_low_score_categories(failures):
    classes = {fr["failure_class"] for fr in failures}
    assert len(classes) >= 3, f"Should cover >=3 distinct failure classes, got {len(classes)}"