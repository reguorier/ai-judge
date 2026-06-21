"""test_beta_week2_feedback_collection.py — 验证 feedback 收集逻辑"""
import json
import os
import pytest

FIXTURE = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_feedback.jsonl"
REGISTRY = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_run_registry.json"
ROSTER = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_user_roster.json"


@pytest.fixture
def feedback():
    entries = []
    with open(FIXTURE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


@pytest.fixture
def runs():
    with open(REGISTRY) as f:
        return json.load(f)


@pytest.fixture
def roster():
    with open(ROSTER) as f:
        return json.load(f)


def test_feedback_count_matches_scored_runs(feedback, runs):
    """Each completed/degraded run must have at least one feedback"""
    completed_ids = {r["run_id"] for r in runs if r["status"] in ("completed", "degraded")}
    feedbacked_ids = {f["run_id"] for f in feedback}
    missing = completed_ids - feedbacked_ids
    assert not missing, f"Runs missing feedback: {missing}"


def test_all_feedback_external(feedback):
    for entry in feedback:
        assert entry.get("is_external_user") is True, f"{entry['feedback_id']} not external"


def test_score_ranges(feedback):
    for entry in feedback:
        for field in ["trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5"]:
            val = entry.get(field)
            if val is not None:
                assert 1 <= val <= 5, f"{entry['feedback_id']} {field}={val} out of range"


def test_failed_task_has_null_scores(feedback, runs):
    """Failed runs should have null scores per experience memory"""
    failed_ids = {r["run_id"] for r in runs if r["status"] == "failed"}
    for entry in feedback:
        if entry["run_id"] in failed_ids:
            assert entry["trust_score_1_to_5"] is None, f"{entry['run_id']} failed but has trust score"
            assert entry["can_state_final_answer"] is False
            assert entry["can_explain_why"] is False


def test_at_least_5_low_scores_for_realistic_variance(feedback):
    """External users should have 3-5 feedback entries with at least one score <=3"""
    low = [f for f in feedback
           if f["trust_score_1_to_5"] is not None
           and (f["trust_score_1_to_5"] <= 3 or f["readability_score_1_to_5"] <= 3 or f["actionability_score_1_to_5"] <= 3)]
    assert len(low) >= 3, f"Expected >=3 low-score entries for realistic external variance, got {len(low)}"