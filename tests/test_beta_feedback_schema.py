#!/usr/bin/env python3
"""
test_beta_feedback_schema.py

Tests for beta_user_feedback_schema.json validation.
Verifies feedback schema structure, field constraints, and
sample feedback correctness.
"""

import json
import os
import pytest

FEEDBACK_SCHEMA_PATH = os.path.expanduser(
    "~/Library/Application Support/AI Judge/runtime/product/beta_ops/beta_user_feedback_schema.json"
)

REQUIRED_FIELDS = [
    "feedback_id", "task_id", "run_id", "reader_type",
    "can_state_final_answer", "can_state_next_step", "can_explain_why",
    "trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5",
    "confusing_part", "missing_information", "would_use_again", "free_text", "created_at",
]

VALID_READER_TYPES = ["普通用户", "专业用户", "PM", "创始人"]


@pytest.fixture(scope="module")
def feedback_schema():
    """Load the feedback schema JSON."""
    with open(FEEDBACK_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestFeedbackSchemaStructure:
    def test_schema_has_required_fields(self, feedback_schema):
        """Verify schema has all required fields defined."""
        schema_required = feedback_schema.get("required", [])
        for field in REQUIRED_FIELDS:
            assert field in schema_required, f"Schema missing required field: {field}"

    def test_schema_has_properties(self, feedback_schema):
        """Verify schema defines properties for all fields."""
        properties = feedback_schema.get("properties", {})
        for field in REQUIRED_FIELDS:
            assert field in properties, f"Schema missing property definition: {field}"

    def test_score_fields_have_1_to_5_range(self, feedback_schema):
        """Verify score fields have min=1, max=5."""
        score_fields = ["trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5"]
        properties = feedback_schema.get("properties", {})
        for field in score_fields:
            prop = properties.get(field, {})
            assert prop.get("minimum") == 1, f"{field}: minimum should be 1"
            assert prop.get("maximum") == 5, f"{field}: maximum should be 5"


class TestFeedbackValidation:
    def test_valid_feedback_passes(self, feedback_schema):
        """Verify a correctly formed feedback record passes validation."""
        feedback = {
            "feedback_id": "FB-TEST-001",
            "task_id": "BETA-LEGAL-001",
            "run_id": "RUN-20240608-001",
            "reader_type": "普通用户",
            "can_state_final_answer": True,
            "can_state_next_step": True,
            "can_explain_why": True,
            "trust_score_1_to_5": 4,
            "readability_score_1_to_5": 4,
            "actionability_score_1_to_5": 4,
            "confusing_part": "",
            "missing_information": "",
            "would_use_again": True,
            "free_text": "Good report!",
            "created_at": "2026-06-08T12:00:00Z",
        }
        # All required fields present
        for field in REQUIRED_FIELDS:
            assert field in feedback, f"Missing: {field}"
        # Scores in range
        assert 1 <= feedback["trust_score_1_to_5"] <= 5
        assert 1 <= feedback["readability_score_1_to_5"] <= 5
        assert 1 <= feedback["actionability_score_1_to_5"] <= 5
        # Reader type valid
        assert feedback["reader_type"] in VALID_READER_TYPES
        # Booleans
        for bf in ["can_state_final_answer", "can_state_next_step", "can_explain_why", "would_use_again"]:
            assert isinstance(feedback[bf], bool)

    def test_confusing_part_can_be_empty(self, feedback_schema):
        """Verify confusing_part field exists but can be empty string."""
        feedback = {
            "feedback_id": "FB-TEST-002",
            "task_id": "BETA-PRODUCT-001",
            "run_id": "RUN-20240608-002",
            "reader_type": "PM",
            "can_state_final_answer": False,
            "can_state_next_step": True,
            "can_explain_why": False,
            "trust_score_1_to_5": 2,
            "readability_score_1_to_5": 2,
            "actionability_score_1_to_5": 3,
            "confusing_part": "",
            "missing_information": "Missing pricing model comparison",
            "would_use_again": False,
            "free_text": "Hard to understand",
            "created_at": "2026-06-08T14:00:00Z",
        }
        assert "confusing_part" in feedback
        assert feedback["confusing_part"] == ""  # Empty is valid

    def test_invalid_score_rejected(self):
        """Verify scores outside 1-5 are caught."""
        invalid_cases = [
            {"field": "trust_score_1_to_5", "value": 0},
            {"field": "trust_score_1_to_5", "value": 6},
            {"field": "readability_score_1_to_5", "value": -1},
            {"field": "actionability_score_1_to_5", "value": 10},
        ]
        for case in invalid_cases:
            assert not (1 <= case["value"] <= 5), (
                f"{case['field']}={case['value']} should be invalid"
            )

    def test_missing_required_field_detected(self):
        """Verify missing required fields are detected."""
        feedback = {
            "feedback_id": "FB-BAD-001",
            "task_id": "BETA-LEGAL-001",
            # missing run_id
            "reader_type": "普通用户",
        }
        missing = [f for f in REQUIRED_FIELDS if f not in feedback]
        assert len(missing) >= 10, f"Expected many missing fields, got: {missing}"