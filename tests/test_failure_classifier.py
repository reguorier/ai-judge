"""Tests for failure_classifier.py."""

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runtime" / "product"))

from observability.failure_classifier import (
    classify_failure,
    FailureClass,
)


def test_classify_meta_contamination():
    """Meta contamination failures should classify as META_CONTAMINATION."""
    failures = [
        {"code": "missing_artifact", "file": "x.json"},
        {"code": "meta_contamination", "keyword": "dashboard"},
    ]
    result = classify_failure(failures)
    assert result == FailureClass.META_CONTAMINATION


def test_classify_seat_matrix_inconsistent():
    """Seat matrix inconsistency should classify correctly."""
    failures = [
        {"code": "seat_matrix_inconsistent", "reported_valid": 5, "actual_valid": 2},
    ]
    result = classify_failure(failures)
    assert result == FailureClass.SEAT_MATRIX_INCONSISTENT


def test_classify_artifact_missing():
    """Missing artifact should classify as ARTIFACT_MISSING."""
    failures = [
        {"code": "missing_artifact", "file": "evidence_pack.json"},
    ]
    result = classify_failure(failures)
    assert result == FailureClass.ARTIFACT_MISSING


def test_classify_report_validation_failed():
    """Validation not passed should classify as REPORT_VALIDATION_FAILED."""
    failures = [
        {"code": "validation_not_passed", "status": "failed"},
    ]
    result = classify_failure(failures)
    assert result == FailureClass.REPORT_VALIDATION_FAILED


def test_classify_no_reasoning_source():
    """Empty substantive_sources should classify as NO_REASONING_SOURCE."""
    failures = [
        {"code": "empty_substantive_sources"},
    ]
    result = classify_failure(failures)
    assert result == FailureClass.NO_REASONING_SOURCE


def test_classify_no_failures():
    """No failures should return None."""
    result = classify_failure([])
    assert result is None


def test_classify_all_nine_classes():
    """Verify all 9 failure classes are accessible."""
    classes = [
        FailureClass.NO_REASONING_SOURCE,
        FailureClass.SEARCH_AGENT_TIMEOUT,
        FailureClass.SEARCH_AGENT_NO_RESULTS,
        FailureClass.REPORT_RELEVANCE_FAILED,
        FailureClass.REPORT_VALIDATION_FAILED,
        FailureClass.ARTIFACT_MISSING,
        FailureClass.SEAT_MATRIX_INCONSISTENT,
        FailureClass.META_CONTAMINATION,
        FailureClass.UNKNOWN,
    ]
    assert len(classes) == 9
    unique = set(classes)
    assert len(unique) == 9