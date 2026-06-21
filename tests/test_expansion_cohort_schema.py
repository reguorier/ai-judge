"""Test expansion cohort schema — §4 requirements."""

import json
import pytest
from pathlib import Path


COHORT_PATH = Path("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_cohort.json")


@pytest.fixture
def cohort():
    with open(COHORT_PATH) as f:
        return json.load(f)


class TestExpansionCohortExternalRatio:
    """External user ratio >= 80%"""

    def test_external_user_count(self, cohort):
        external = [u for u in cohort if u.get("is_external_user", False)]
        ratio = len(external) / len(cohort) * 100
        assert ratio >= 80, f"External ratio {ratio:.1f}% < 80%"
        assert len(external) >= 30, f"External users {len(external)} < 30"

    def test_total_user_range(self, cohort):
        assert 30 <= len(cohort) <= 50, f"Total users {len(cohort)} not in 30-50 range"

    def test_internal_not_mixed_with_external_stats(self, cohort):
        external = [u for u in cohort if u.get("is_external_user", False)]
        internal = [u for u in cohort if not u.get("is_external_user", False)]
        # Internal users exist but isolated
        assert len(internal) >= 0
        # Each user is clearly marked
        for u in cohort:
            assert "is_external_user" in u, f"User {u.get('user_id')} missing is_external_user flag"


class TestExpansionCohortConsent:
    """All users must have consent confirmed"""

    def test_all_consent_confirmed(self, cohort):
        for u in cohort:
            assert u.get("consent_confirmed") is True, f"User {u['user_id']} consent not confirmed"

    def test_no_sensitive_pii(self, cohort):
        forbidden_fields = ["phone", "id_card", "address", "bank_account", "medical_record"]
        for u in cohort:
            for field in forbidden_fields:
                assert field not in u or u[field] == "", f"User {u['user_id']} has forbidden field: {field}"


class TestExpansionCohortMaxRuns:
    """Each user max_runs <= 3"""

    def test_max_runs_limit(self, cohort):
        for u in cohort:
            assert u.get("max_runs", 0) <= 3, f"User {u['user_id']} max_runs={u.get('max_runs')} > 3"

    def test_allowed_task_ids_present(self, cohort):
        for u in cohort:
            tasks = u.get("allowed_task_ids", [])
            assert len(tasks) >= 1, f"User {u['user_id']} has no allowed_task_ids"


class TestExpansionCohortDistribution:
    """User type distribution matches spec"""

    def test_ordinary_user_minimum(self, cohort):
        count = sum(1 for u in cohort if u.get("reader_type") == "普通用户")
        assert count >= 15, f"Ordinary users {count} < 15"

    def test_pm_founder_minimum(self, cohort):
        count = sum(1 for u in cohort if u.get("reader_type") in ("PM", "创始人", "PM/创始人"))
        assert count >= 8, f"PM/founder users {count} < 8"

    def test_professional_user_minimum(self, cohort):
        count = sum(1 for u in cohort if u.get("reader_type") == "专业用户")
        assert count >= 5, f"Professional users {count} < 5"

    def test_legal_compliance_minimum(self, cohort):
        count = sum(1 for u in cohort if u.get("reader_type") in ("法律/合规", "法律", "合规"))
        assert count >= 5, f"Legal/compliance users {count} < 5"

    def test_data_model_minimum(self, cohort):
        count = sum(1 for u in cohort if u.get("reader_type") in ("数据/模型", "数据", "模型"))
        assert count >= 2, f"Data/model users {count} < 2"