#!/usr/bin/env python3
"""Tests for acceptance_tasks.json schema validation.

Validates that acceptance_tasks.json meets all requirements:
- At least 12 tasks
- Each category has correct count
- Each task has required fields
- No all-legal tasks
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


TASKS_FILE = (
    Path(__file__).resolve().parent.parent
    / "runtime" / "product" / "user_acceptance" / "acceptance_tasks.json"
)


@pytest.fixture(scope="module")
def tasks_data():
    with open(TASKS_FILE, encoding="utf-8") as f:
        return json.load(f)


class TestAcceptanceTasksSchema:
    """Validate acceptance_tasks.json schema compliance."""

    def test_tasks_file_exists(self):
        assert TASKS_FILE.exists(), f"Tasks file not found: {TASKS_FILE}"

    def test_at_least_12_tasks(self, tasks_data):
        tasks = tasks_data["tasks"]
        assert len(tasks) >= 12, f"Expected >= 12 tasks, got {len(tasks)}"

    def test_legal_tasks_count(self, tasks_data):
        legal = [t for t in tasks_data["tasks"] if t["category"] == "legal"]
        assert len(legal) == 5, f"Expected 5 legal tasks, got {len(legal)}"

    def test_product_tasks_count(self, tasks_data):
        product = [t for t in tasks_data["tasks"] if t["category"] == "product"]
        assert len(product) == 3, f"Expected 3 product tasks, got {len(product)}"

    def test_audit_tasks_count(self, tasks_data):
        audit = [t for t in tasks_data["tasks"] if t["category"] == "data_audit"]
        assert len(audit) == 2, f"Expected 2 audit tasks, got {len(audit)}"

    def test_decision_tasks_count(self, tasks_data):
        decision = [t for t in tasks_data["tasks"] if t["category"] == "decision"]
        assert len(decision) == 2, f"Expected 2 decision tasks, got {len(decision)}"

    def test_not_all_legal(self, tasks_data):
        legal = [t for t in tasks_data["tasks"] if t["category"] == "legal"]
        assert len(legal) < len(tasks_data["tasks"]), "All tasks are legal — not allowed"

    def test_each_task_has_required_fields(self, tasks_data):
        required = {
            "id", "category", "mode", "question",
            "expected_user_takeaway", "required_keywords",
            "forbidden_keywords", "target_reader",
            "max_expected_latency_sec", "must_generate_artifacts",
        }
        for task in tasks_data["tasks"]:
            missing = required - set(task.keys())
            assert not missing, f"Task {task.get('id', '?')} missing fields: {missing}"

    def test_each_task_has_expected_user_takeaway(self, tasks_data):
        for task in tasks_data["tasks"]:
            takeaway = task.get("expected_user_takeaway", "")
            assert takeaway, f"Task {task['id']} has empty expected_user_takeaway"
            assert len(takeaway) > 20, f"Task {task['id']} takeaway too short"

    def test_each_task_has_target_reader(self, tasks_data):
        valid_readers = {"普通用户", "专业用户", "PM", "创始人"}
        for task in tasks_data["tasks"]:
            reader = task.get("target_reader", "")
            assert reader in valid_readers, (
                f"Task {task['id']} has invalid target_reader: {reader}"
            )

    def test_task_ids_unique(self, tasks_data):
        ids = [t["id"] for t in tasks_data["tasks"]]
        assert len(ids) == len(set(ids)), "Duplicate task IDs found"

    def test_task_id_format(self, tasks_data):
        import re
        for task in tasks_data["tasks"]:
            assert re.match(
                r"^UA-(LEGAL|PRODUCT|AUDIT|DECISION)-\d{3}$", task["id"]
            ), f"Task {task['id']} has invalid ID format"

    def test_questions_are_non_trivial(self, tasks_data):
        for task in tasks_data["tasks"]:
            q = task.get("question", "")
            assert len(q) > 50, f"Task {task['id']} question too short: {len(q)} chars"

    def test_mode_is_deep_judge(self, tasks_data):
        for task in tasks_data["tasks"]:
            assert task.get("mode") == "deep_judge", (
                f"Task {task['id']} mode should be 'deep_judge'"
            )

    def test_valid_json_schema(self, tasks_data):
        """Verify the JSON has the expected top-level structure."""
        assert "tasks" in tasks_data
        assert isinstance(tasks_data["tasks"], list)
        assert "$schema" in tasks_data or "version" in tasks_data


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-q"]))