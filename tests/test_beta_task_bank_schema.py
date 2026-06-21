#!/usr/bin/env python3
"""
test_beta_task_bank_schema.py

Tests for beta_task_bank.json schema validation.
Verifies task count, category distribution, required fields,
and correctness of risk level + human review configuration.
"""

import json
import os
import pytest

TASK_BANK_PATH = os.path.expanduser(
    "~/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_task_bank.json"
)

REQUIRED_FIELDS = [
    "id", "category", "mode", "question", "target_reader",
    "expected_takeaway", "success_criteria", "risk_level",
    "requires_search_agent", "requires_human_review",
]

VALID_CATEGORIES = ["legal", "product", "data_audit", "life_decision", "report_review", "safety_boundary"]
VALID_MODES = ["deep_judge"]
VALID_READERS = ["普通用户", "专业用户", "PM", "创始人"]
VALID_RISK_LEVELS = ["low", "medium", "high"]


@pytest.fixture(scope="module")
def task_bank():
    """Load the task bank JSON."""
    with open(TASK_BANK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestTaskBankSchema:
    def test_at_least_30_tasks(self, task_bank):
        """Verify task bank has 30+ tasks."""
        assert len(task_bank) >= 30, f"Expected >= 30 tasks, got {len(task_bank)}"

    def test_all_required_fields_present(self, task_bank):
        """Verify every task has all required fields."""
        for task in task_bank:
            for field in REQUIRED_FIELDS:
                assert field in task, f"Task {task.get('id', '?')} missing field: {field}"

    def test_valid_categories(self, task_bank):
        """Verify all categories are valid and category counts match spec."""
        cats = {}
        for task in task_bank:
            cat = task["category"]
            assert cat in VALID_CATEGORIES, f"Invalid category: {cat}"
            cats[cat] = cats.get(cat, 0) + 1

        # Category count requirements
        assert cats.get("legal", 0) >= 8, f"Legal: expected >=8, got {cats.get('legal', 0)}"
        assert cats.get("product", 0) >= 6, f"Product: expected >=6, got {cats.get('product', 0)}"
        assert cats.get("data_audit", 0) >= 5, f"Data audit: expected >=5, got {cats.get('data_audit', 0)}"
        assert cats.get("life_decision", 0) >= 4, f"Life decision: expected >=4, got {cats.get('life_decision', 0)}"
        assert cats.get("report_review", 0) >= 4, f"Report review: expected >=4, got {cats.get('report_review', 0)}"
        assert cats.get("safety_boundary", 0) >= 3, f"Safety boundary: expected >=3, got {cats.get('safety_boundary', 0)}"


class TestTaskBankContent:
    def test_high_risk_tasks_have_human_review(self, task_bank):
        """Verify high-risk tasks require human review or have explicit boundary."""
        high_risk = [t for t in task_bank if t["risk_level"] == "high"]
        assert len(high_risk) > 0, "No high-risk tasks found"
        for task in high_risk:
            has_review = task.get("requires_human_review", False)
            is_boundary = task["category"] == "safety_boundary"
            assert has_review or is_boundary, (
                f"High-risk task {task['id']} must have requires_human_review=true "
                f"or be in safety_boundary category"
            )

    def test_every_task_has_expected_takeaway(self, task_bank):
        """Verify every task has a non-empty expected_takeaway."""
        for task in task_bank:
            takeaway = task.get("expected_takeaway", "")
            assert len(takeaway.strip()) > 10, (
                f"Task {task['id']}: expected_takeaway too short or empty"
            )

    def test_success_criteria_complete(self, task_bank):
        """Verify success_criteria sub-fields are present."""
        required_criteria = [
            "must_answer_core_question",
            "must_have_next_step",
            "must_have_evidence_or_reason",
            "must_not_have_meta_contamination",
        ]
        for task in task_bank:
            sc = task.get("success_criteria", {})
            for field in required_criteria:
                assert field in sc, f"Task {task['id']}: success_criteria missing {field}"

    def test_not_all_legal_tasks(self, task_bank):
        """Verify tasks are not exclusively legal — at least 4 other categories."""
        legal_count = sum(1 for t in task_bank if t["category"] == "legal")
        assert len(task_bank) - legal_count >= 22, (
            f"Too many legal tasks: {legal_count}/{len(task_bank)}. "
            f"Need diversity across categories."
        )

    def test_valid_risk_levels(self, task_bank):
        """Verify all risk levels are valid."""
        for task in task_bank:
            assert task["risk_level"] in VALID_RISK_LEVELS, (
                f"Task {task['id']}: invalid risk_level: {task['risk_level']}"
            )

    def test_valid_target_readers(self, task_bank):
        """Verify all target readers are valid."""
        for task in task_bank:
            assert task["target_reader"] in VALID_READERS, (
                f"Task {task['id']}: invalid target_reader: {task['target_reader']}"
            )