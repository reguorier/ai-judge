"""test_controlled_demo_feedback_schema.py — 测试反馈 JSONL schema"""

import json
import os
import pytest

FEEDBACK_PATH = os.path.join(
    os.path.expanduser("~"), "Library", "Application Support", "AI Judge",
    "runtime", "product", "demo_launch", "controlled_demo_feedback.jsonl"
)

REQUIRED_FIELDS = [
    "feedback_id", "user_id", "run_id", "task_id", "reader_type",
    "is_external_user", "can_state_final_answer", "can_state_next_step",
    "can_explain_why", "trust_score_1_to_5", "readability_score_1_to_5",
    "actionability_score_1_to_5", "would_use_again", "confusing_part",
    "free_text", "created_at"
]


def _load_feedback():
    if not os.path.exists(FEEDBACK_PATH):
        pytest.skip(f"feedback file not found: {FEEDBACK_PATH}")
    entries = []
    with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


class TestFeedbackSchema:

    def test_feedback_is_not_empty(self):
        entries = _load_feedback()
        assert len(entries) > 0, "feedback file is empty"

    def test_all_entries_have_required_fields(self):
        entries = _load_feedback()
        for entry in entries:
            for field in REQUIRED_FIELDS:
                assert field in entry, f"{entry.get('feedback_id', '?')} missing field: {field}"

    def test_score_range_when_not_null(self):
        entries = _load_feedback()
        score_fields = ["trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5"]
        for entry in entries:
            for field in score_fields:
                val = entry.get(field)
                if val is not None:
                    assert 1 <= val <= 5, f"{entry['feedback_id']} {field}={val} out of [1,5]"

    def test_external_users_marked_correctly(self):
        entries = _load_feedback()
        for entry in entries:
            assert entry["is_external_user"] is True, f"{entry['feedback_id']} not marked external"

    def test_no_low_scores(self):
        """All scored entries should be ≥ 3.8"""
        entries = _load_feedback()
        for entry in entries:
            trust = entry.get("trust_score_1_to_5")
            if trust is not None:
                assert trust >= 3.8, f"{entry['feedback_id']} trust score {trust} too low"

    def test_feedback_coverage(self):
        """At least 80% of entries should have scores"""
        entries = _load_feedback()
        scored = [e for e in entries if e["trust_score_1_to_5"] is not None]
        coverage = len(scored) / len(entries)
        assert coverage >= 0.80, f"coverage {coverage:.1%} below 80%"