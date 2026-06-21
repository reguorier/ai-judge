"""Test expansion waitlist interest — §11 requirements."""

import json
import pytest
from pathlib import Path


WAITLIST_PATH = Path("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_waitlist_interest.jsonl")
FEEDBACK_PATH = Path("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_feedback.jsonl")


REQUIRED_FIELDS = [
    "user_id", "would_join_waitlist", "use_case", "team_size",
    "willing_to_pay_signal", "preferred_contact", "created_at",
]


@pytest.fixture
def waitlist():
    with open(WAITLIST_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.fixture
def feedbacks():
    with open(FEEDBACK_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


class TestExpansionWaitlistSourceConsistency:
    """Waitlist entries must come from feedback with would_join_waitlist=true"""

    def test_count_matches_feedback(self, waitlist, feedbacks):
        fb_waitlist = [f for f in feedbacks if f.get("would_join_waitlist")]
        assert len(waitlist) == len(fb_waitlist), \
            f"Waitlist {len(waitlist)} != feedback would_join {len(fb_waitlist)}"

    def test_user_ids_match_feedback(self, waitlist, feedbacks):
        fb_waitlist_ids = {f["user_id"] for f in feedbacks if f.get("would_join_waitlist")}
        waitlist_ids = {w["user_id"] for w in waitlist}
        assert waitlist_ids == fb_waitlist_ids, \
            f"ID mismatch: waitlist {waitlist_ids - fb_waitlist_ids}, feedback {fb_waitlist_ids - waitlist_ids}"


class TestExpansionWaitlistFieldCompleteness:
    """All required fields present"""

    def test_all_required_fields(self, waitlist):
        for w in waitlist:
            for field in REQUIRED_FIELDS:
                assert field in w, f"Waitlist entry missing field: {field}"

    def test_use_case_valid(self, waitlist):
        valid = {"legal", "product", "data", "decision", "other"}
        for w in waitlist:
            assert w["use_case"] in valid, f"Invalid use_case: {w['use_case']}"

    def test_team_size_valid(self, waitlist):
        valid = {"solo", "2-5", "6-20", "20+"}
        for w in waitlist:
            assert w["team_size"] in valid, f"Invalid team_size: {w['team_size']}"

    def test_willing_to_pay_valid(self, waitlist):
        valid = {"none", "low", "medium", "high"}
        for w in waitlist:
            assert w["willing_to_pay_signal"] in valid, f"Invalid pay signal: {w['willing_to_pay_signal']}"


class TestExpansionWaitlistNoForcedContact:
    """Must not force contact info collection"""

    def test_preferred_contact_distribution(self, waitlist):
        none_count = sum(1 for w in waitlist if w["preferred_contact"] == "none")
        assert none_count > 0, "No entries with preferred_contact=none — mandatory collection suspected"

    def test_no_plaintext_sensitive_info(self, waitlist):
        forbidden = ["@gmail.com", "@qq.com", "138", "139", "身份证"]
        for w in waitlist:
            entry_str = json.dumps(w)
            for keyword in forbidden:
                assert keyword not in entry_str, f"Waitlist entry contains forbidden keyword: {keyword}"