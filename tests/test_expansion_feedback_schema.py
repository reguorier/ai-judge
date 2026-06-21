"""Test expansion feedback schema — §7 requirements."""

import json
import pytest
from pathlib import Path


FEEDBACK_PATH = Path("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_feedback.jsonl")
REGISTRY_PATH = Path("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_run_registry.json")


REQUIRED_FIELDS = [
    "feedback_id", "assignment_id", "user_id", "run_id", "task_id",
    "reader_type", "is_external_user", "can_state_final_answer",
    "can_state_next_step", "can_explain_why",
    "trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5",
    "would_use_again", "would_recommend", "would_join_waitlist",
    "confusing_part", "missing_information", "free_text", "created_at",
]


@pytest.fixture
def feedbacks():
    with open(FEEDBACK_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.fixture
def registry():
    with open(REGISTRY_PATH) as f:
        return json.load(f)


class TestExpansionFeedbackCoverage:
    """Feedback coverage >= 75% of completed runs"""

    def test_coverage_rate(self, feedbacks, registry):
        completed_runs = [r["run_id"] for r in registry if r["status"] in ("completed", "degraded")]
        feedbacked_runs = {f["run_id"] for f in feedbacks}
        missing = set(completed_runs) - feedbacked_runs
        coverage = len(feedbacked_runs) / len(completed_runs) * 100
        assert coverage >= 75, f"Feedback coverage {coverage:.1f}% < 75%. Missing: {missing}"

    def test_feedback_count_minimum(self, feedbacks):
        assert len(feedbacks) >= 48, f"Feedback count {len(feedbacks)} < 48"


class TestExpansionFeedbackFieldCompleteness:
    """All required fields present"""

    def test_all_required_fields(self, feedbacks):
        for fb in feedbacks:
            for field in REQUIRED_FIELDS:
                assert field in fb, f"Feedback {fb.get('feedback_id')} missing field: {field}"

    def test_score_ranges(self, feedbacks):
        for fb in feedbacks:
            assert 1 <= fb["trust_score_1_to_5"] <= 5, f"trust_score out of range: {fb['trust_score_1_to_5']}"
            assert 1 <= fb["readability_score_1_to_5"] <= 5, f"readability_score out of range"
            assert 1 <= fb["actionability_score_1_to_5"] <= 5, f"actionability_score out of range"

    def test_no_anomalous_low_scores(self, feedbacks):
        """Scores should not be uniformly too low (suggesting fabrication)"""
        avg_trust = sum(f["trust_score_1_to_5"] for f in feedbacks) / len(feedbacks)
        avg_read = sum(f["readability_score_1_to_5"] for f in feedbacks) / len(feedbacks)
        avg_act = sum(f["actionability_score_1_to_5"] for f in feedbacks) / len(feedbacks)
        assert avg_trust >= 3.6, f"Avg trust {avg_trust:.2f} too low"
        assert avg_read >= 3.6, f"Avg readability {avg_read:.2f} too low"
        assert avg_act >= 3.6, f"Avg actionability {avg_act:.2f} too low"


class TestExpansionFeedbackExternalFlag:
    """External user flag correctly set"""

    def test_external_flag_present(self, feedbacks):
        for fb in feedbacks:
            assert "is_external_user" in fb, f"Feedback {fb['feedback_id']} missing is_external_user"

    def test_external_ratio(self, feedbacks):
        external = sum(1 for f in feedbacks if f["is_external_user"])
        ratio = external / len(feedbacks) * 100
        assert ratio >= 80, f"External feedback ratio {ratio:.1f}% < 80%"


class TestExpansionFeedbackTimestamps:
    """Created_at field is valid ISO-8601"""

    def test_valid_timestamps(self, feedbacks):
        from datetime import datetime
        for fb in feedbacks:
            try:
                datetime.fromisoformat(fb["created_at"].replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(f"Invalid timestamp in feedback {fb['feedback_id']}: {fb['created_at']}")