"""test_beta_week2_user_roster_schema.py — 验证 user roster schema"""
import json
import os
import pytest

FIXTURE = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_week2_user_roster.json"


@pytest.fixture
def roster():
    with open(FIXTURE) as f:
        return json.load(f)


def test_roster_has_minimum_users(roster):
    assert len(roster) >= 5, f"Need >=5 users, got {len(roster)}"


def test_roster_all_users_external(roster):
    for user in roster:
        assert user.get("is_external_user") is True, f"{user['user_id']} must be external"


def test_roster_all_users_consented(roster):
    for user in roster:
        assert user.get("consent_confirmed") is True, f"{user['user_id']} must have confirmed consent"


def test_roster_reader_types_coverage(roster):
    types = {u["reader_type"] for u in roster}
    assert "普通用户" in types, "Missing 普通用户"
    assert any(t in types for t in ["PM", "专业用户"]), "Missing PM or 专业用户"
    assert "创始人" in types, "Missing 创始人"


def test_roster_tasks_per_user(roster):
    for user in roster:
        n = len(user.get("tasks_assigned", []))
        assert 2 <= n <= 3, f"{user['user_id']} has {n} tasks, expected 2-3"


def test_roster_required_fields(roster):
    required = ["user_id", "reader_type", "is_external_user", "recruitment_source",
                "tasks_assigned", "consent_confirmed", "notes"]
    for user in roster:
        for field in required:
            assert field in user, f"{user['user_id']} missing {field}"