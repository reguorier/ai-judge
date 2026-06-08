"""P0-1: Seat matrix valid_seats must be computed from real seat states, not hardcoded."""

import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.evidence_summarizer import (
    compute_valid_seats,
    compute_failed_seats,
    build_seat_matrix,
    VALID_SEAT_STATUSES,
    INVALID_SEAT_STATUSES,
)


class TestComputeValidSeats:
    """valid_seats must reflect actual seat status, not total_seats."""

    def test_all_valid(self):
        seats = [
            {"status": "valid", "answer": "分析意见A"},
            {"status": "completed", "answer": "分析意见B"},
            {"status": "success", "answer": "分析意见C"},
        ]
        assert compute_valid_seats(seats) == 3

    def test_mixed_status(self):
        seats = [
            {"status": "valid", "answer": "有效分析"},
            {"status": "skipped", "answer": ""},
            {"status": "not_configured", "answer": ""},
            {"status": "failed", "answer": ""},
            {"status": "completed", "answer": "有效分析2"},
        ]
        assert compute_valid_seats(seats) == 2

    def test_all_skipped(self):
        seats = [
            {"status": "skipped", "answer": ""},
            {"status": "not_configured", "answer": ""},
        ]
        assert compute_valid_seats(seats) == 0

    def test_valid_status_but_empty_answer(self):
        """Seat with 'valid' status but empty answer should NOT count as valid."""
        seats = [
            {"status": "valid", "answer": ""},
            {"status": "completed", "answer": ""},
        ]
        assert compute_valid_seats(seats) == 0

    def test_score_bug_reproduction(self):
        """P0-1 bug: 5 total, seats 4+5 skipped → valid_seats should be 3, not 5."""
        seats = [
            {"status": "valid", "answer": "Report Builder 分析"},
            {"status": "valid", "answer": "Dissent Reviewer 分析"},
            {"status": "valid", "answer": "Human Gate 分析"},
            {"status": "skipped", "answer": ""},
            {"status": "not_configured", "answer": ""},
        ]
        assert compute_valid_seats(seats) == 3, (
            f"P0-1 BUG: 5 seats with 2 skipped should give valid_seats=3, "
            f"not 5. Got: {compute_valid_seats(seats)}"
        )


class TestComputeFailedSeats:
    """failed_seats counts error/timeout/failed states."""

    def test_some_failed(self):
        seats = [
            {"status": "valid", "answer": "ok"},
            {"status": "failed", "answer": ""},
            {"status": "error", "answer": ""},
            {"status": "timeout", "answer": ""},
        ]
        assert compute_failed_seats(seats) == 3

    def test_no_failed(self):
        seats = [
            {"status": "valid", "answer": "ok"},
            {"status": "skipped", "answer": ""},
        ]
        assert compute_failed_seats(seats) == 0


class TestBuildSeatMatrixConsistency:
    """build_seat_matrix output must be internally consistent."""

    def test_valid_count_does_not_exceed_valid_seats_param(self):
        """If valid_seats=3, only 3 seats should be valid, rest skipped."""
        sm = build_seat_matrix(
            run_id="test-sm-001",
            mode="deep_judge",
            valid_seats=3,
            total_seats=5,
            failed_seats=0,
        )
        seats = sm["seats"]
        valid_count = sum(
            1 for s in seats
            if s["status"] in {"valid", "completed", "answered", "success"}
        )
        assert valid_count <= 3, f"Expected ≤3 valid, got {valid_count}"

    def test_total_seats_matches(self):
        sm = build_seat_matrix(
            run_id="test-sm-002",
            mode="deep_judge",
            valid_seats=2,
            total_seats=7,
            failed_seats=1,
        )
        assert len(sm["seats"]) == 7

    def test_failed_seats_included(self):
        sm = build_seat_matrix(
            run_id="test-sm-003",
            mode="deep_judge",
            valid_seats=2,
            total_seats=5,
            failed_seats=2,
        )
        failed = [s for s in sm["seats"] if s["status"] == "failed"]
        assert len(failed) == 2