"""test_controlled_demo_cohort_schema.py — 测试受控演示用户名单 schema"""

import json
import os
import pytest

HOME = os.path.expanduser("~")
COHORT_PATH = os.path.join(
    HOME, "Library", "Application Support", "AI Judge", "runtime", "product",
    "demo_launch", "controlled_demo_cohort.json"
)


def _resolve_path():
    if os.path.exists(COHORT_PATH):
        return COHORT_PATH
    return None


def _load_cohort():
    path = _resolve_path()
    if path is None:
        pytest.skip("cohort file not found in any known location")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestCohortSchema:

    def test_cohort_is_list(self):
        cohort = _load_cohort()
        assert isinstance(cohort, list), "cohort should be a JSON array"

    def test_cohort_size_between_5_and_20(self):
        cohort = _load_cohort()
        assert 5 <= len(cohort) <= 20, f"cohort size {len(cohort)} not in [5, 20]"

    def test_all_users_have_required_fields(self):
        cohort = _load_cohort()
        required = ["user_id", "reader_type", "is_external_user", "allowed_task_ids",
                     "max_runs", "consent_confirmed"]
        for user in cohort:
            for field in required:
                assert field in user, f"{user.get('user_id', '?')} missing field: {field}"

    def test_all_users_consent_confirmed(self):
        cohort = _load_cohort()
        for user in cohort:
            assert user["consent_confirmed"] is True, f"{user['user_id']} consent not confirmed"

    def test_all_users_is_external(self):
        cohort = _load_cohort()
        for user in cohort:
            assert user["is_external_user"] is True, f"{user['user_id']} not marked external"

    def test_max_runs_not_exceeded(self):
        cohort = _load_cohort()
        for user in cohort:
            assert user["max_runs"] <= 3, f"{user['user_id']} max_runs={user['max_runs']} > 3"

    def test_all_users_have_allowed_tasks(self):
        cohort = _load_cohort()
        for user in cohort:
            assert len(user["allowed_task_ids"]) > 0, f"{user['user_id']} has no allowed tasks"

    def test_no_sensitive_personal_info(self):
        cohort = _load_cohort()
        sensitive_keys = ["phone", "id_card", "address", "email_personal"]
        for user in cohort:
            for key in sensitive_keys:
                assert key not in user, f"{user['user_id']} contains sensitive key: {key}"