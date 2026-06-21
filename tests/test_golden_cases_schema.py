"""Tests for golden_cases.json schema validation."""

import json
import os
from pathlib import Path

import pytest


GOLDEN_CASES_PATH = Path(__file__).resolve().parent.parent / "runtime" / "product" / "golden_cases" / "golden_cases.json"


@pytest.fixture
def golden_cases() -> list:
    """Load golden cases from JSON."""
    with open(GOLDEN_CASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_golden_cases_minimum_count(golden_cases):
    """Golden cases must have at least 5 cases."""
    assert len(golden_cases) >= 5, f"Expected >= 5 golden cases, got {len(golden_cases)}"


def test_each_case_required_fields(golden_cases):
    """Each case must have id, mode, question, required_keywords, forbidden_keywords."""
    for case in golden_cases:
        assert "id" in case, f"Case missing 'id': {case}"
        assert "mode" in case, f"Case {case.get('id', '?')} missing 'mode'"
        assert "question" in case, f"Case {case['id']} missing 'question'"
        assert "required_keywords" in case, f"Case {case['id']} missing 'required_keywords'"
        assert "forbidden_keywords" in case, f"Case {case['id']} missing 'forbidden_keywords'"


def test_golden_cases_diverse_types(golden_cases):
    """Validate: at least 2 complex legal questions, at least 1 low-dispute fact question,
    not limited to single legal type."""
    complex_count = 0
    fact_count = 0
    types_seen = set()

    for case in golden_cases:
        q = case["question"]
        _id = case["id"]

        # Heuristic: complex if question ends with ? and uses legal terms
        if "?" in q or "如何" in q or "能否" in q:
            complex_count += 1
        # Fact-based: short, answer-based questions
        if "多少" in q or "共有" in q or "几条" in q:
            fact_count += 1

        # Track types
        types_seen.add(_id.split("-")[1] if "-" in _id else _id)

    assert complex_count >= 2, f"Expected >= 2 complex legal questions, got {complex_count}"
    assert fact_count >= 1, f"Expected >= 1 fact-based question, got {fact_count}"
    assert len(types_seen) >= 3, f"Expected diverse legal types (>=3), got {len(types_seen)}"


def test_case_ids_are_unique(golden_cases):
    """All case IDs must be unique."""
    ids = [case["id"] for case in golden_cases]
    assert len(ids) == len(set(ids)), f"Duplicate case IDs found: {ids}"


def test_forbidden_keywords_consistency(golden_cases):
    """Forbidden keywords should include common meta contamination terms."""
    meta_terms = {"B2B SaaS", "dashboard", "投资人"}
    for case in golden_cases:
        forbidden = set(case["forbidden_keywords"])
        common = meta_terms & forbidden
        assert len(common) >= 1, f"Case {case['id']} missing common meta contamination terms"