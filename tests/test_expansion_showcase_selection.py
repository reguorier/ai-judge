"""Test expansion showcase selection — §10 criteria."""

import json
import pytest
from pathlib import Path


SHOWCASE_PATH = Path("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_showcase_candidates.json")


@pytest.fixture
def showcase():
    with open(SHOWCASE_PATH) as f:
        return json.load(f)


class TestExpansionShowcaseCount:
    """Showcase 3-5 candidates"""

    def test_minimum_count(self, showcase):
        assert len(showcase) >= 3, f"Showcase count {len(showcase)} < 3"

    def test_maximum_count(self, showcase):
        assert len(showcase) <= 5, f"Showcase count {len(showcase)} > 5"


class TestExpansionShowcaseAuthorization:
    """All must have user_permission=true"""

    def test_all_user_permission(self, showcase):
        for case in showcase:
            assert case.get("user_permission") is True, f"Case {case['case_id']} lacks user permission"

    def test_all_approved_for_public_false(self, showcase):
        """All must be approved_for_public=false (pending review)"""
        for case in showcase:
            assert case.get("approved_for_public") is False, f"Case {case['case_id']} prematurely approved"


class TestExpansionShowcasePii:
    """All pii_free=true"""

    def test_all_pii_free(self, showcase):
        for case in showcase:
            assert case.get("pii_free") is True, f"Case {case['case_id']} not PII free"


class TestExpansionShowcaseScores:
    """All trust/readability/actionability >= 4"""

    def test_all_scores_minimum(self, showcase):
        for case in showcase:
            scores = case.get("scores", {})
            assert scores.get("trust", 0) >= 4.0, f"Case {case['case_id']} trust {scores.get('trust')} < 4"
            assert scores.get("readability", 0) >= 4.0, f"Case {case['case_id']} readability {scores.get('readability')} < 4"
            assert scores.get("actionability", 0) >= 4.0, f"Case {case['case_id']} actionability {scores.get('actionability')} < 4"


class TestExpansionShowcaseFields:
    """Required fields present"""

    def test_required_fields(self, showcase):
        required = ["case_id", "source_run_id", "task_id", "category", "headline",
                     "why_it_shows_value", "user_permission", "pii_free", "approved_for_public"]
        for case in showcase:
            for field in required:
                assert field in case, f"Case {case.get('case_id')} missing field: {field}"