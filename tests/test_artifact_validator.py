"""Tests for artifact_validator.py."""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Path to artifact_validator
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runtime" / "product"))

from observability.artifact_validator import validate_artifacts


@pytest.fixture
def valid_artifacts_dir():
    """Create a temporary directory with all valid artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        # run_metadata.json with substantive_sources
        (run_dir / "run_metadata.json").write_text(json.dumps({
            "mode": "deep_judge",
            "deep_judge": {
                "substantive_sources": ["search-agent"]
            }
        }), encoding="utf-8")

        # seat_matrix.json with consistent valid_seats
        (run_dir / "seat_matrix.json").write_text(json.dumps({
            "summary": {"valid_seats": 3},
            "seats": [
                {"id": "seat1", "status": "valid"},
                {"id": "seat2", "status": "valid"},
                {"id": "seat3", "status": "valid"},
                {"id": "seat4", "status": "skipped"},
            ]
        }), encoding="utf-8")

        # evidence_pack.json with sources
        (run_dir / "evidence_pack.json").write_text(json.dumps({
            "sources": [
                {"id": "src-1", "content": "Evidence 1"},
                {"id": "src-2", "content": "Evidence 2"},
            ]
        }), encoding="utf-8")

        # final_report_contract.json with citations
        (run_dir / "final_report_contract.json").write_text(json.dumps({
            "citations": [
                {"source_id": "src-1", "text": "ref 1"},
                {"source_id": "src-2", "text": "ref 2"},
            ]
        }), encoding="utf-8")

        # final_report.html with AJ_REPORT_V1 marker
        (run_dir / "final_report.html").write_text(
            "<html><h1>AJ_REPORT_V1 Decision Brief</h1></html>",
            encoding="utf-8"
        )

        # validation_result.json with ok status
        (run_dir / "validation_result.json").write_text(json.dumps({
            "status": "ok"
        }), encoding="utf-8")

        yield tmpdir


def test_all_artifacts_valid(valid_artifacts_dir):
    """All valid artifacts should pass validation."""
    result = validate_artifacts(valid_artifacts_dir)
    assert result["ok"] is True
    assert len(result["failures"]) == 0


def test_missing_artifact():
    """Missing artifact should be detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        # Only create some artifacts
        (run_dir / "run_metadata.json").write_text(json.dumps({
            "deep_judge": {"substantive_sources": ["search-agent"]}
        }), encoding="utf-8")

        result = validate_artifacts(str(run_dir))
        assert result["ok"] is False
        failure_codes = {f["code"] for f in result["failures"]}
        assert "missing_artifact" in failure_codes


def test_empty_substantive_sources():
    """Empty substantive_sources should be flagged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        for name in ["run_metadata.json", "seat_matrix.json", "evidence_pack.json",
                      "final_report_contract.json", "final_report.html", "validation_result.json"]:
            (run_dir / name).write_text("{}", encoding="utf-8")

        (run_dir / "run_metadata.json").write_text(json.dumps({
            "deep_judge": {"substantive_sources": []}
        }), encoding="utf-8")

        (run_dir / "seat_matrix.json").write_text(json.dumps({
            "summary": {"valid_seats": 0}, "seats": []
        }), encoding="utf-8")

        (run_dir / "evidence_pack.json").write_text(json.dumps({"sources": []}), encoding="utf-8")

        (run_dir / "final_report_contract.json").write_text(json.dumps({"citations": []}), encoding="utf-8")

        (run_dir / "final_report.html").write_text("AJ_REPORT_V1 test", encoding="utf-8")

        (run_dir / "validation_result.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")

        result = validate_artifacts(str(run_dir))
        assert result["ok"] is False
        failure_codes = {f["code"] for f in result["failures"]}
        assert "empty_substantive_sources" in failure_codes


def test_meta_contamination():
    """Meta contamination keywords should be detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        (run_dir / "run_metadata.json").write_text(json.dumps({
            "deep_judge": {"substantive_sources": ["search-agent"]}
        }), encoding="utf-8")
        (run_dir / "seat_matrix.json").write_text(json.dumps({
            "summary": {"valid_seats": 0}, "seats": []
        }), encoding="utf-8")
        (run_dir / "evidence_pack.json").write_text(json.dumps({"sources": []}), encoding="utf-8")
        (run_dir / "final_report_contract.json").write_text(json.dumps({"citations": []}), encoding="utf-8")
        (run_dir / "final_report.html").write_text(
            "AJ_REPORT_V1 dashboard B2B SaaS",
            encoding="utf-8"
        )
        (run_dir / "validation_result.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")

        result = validate_artifacts(str(run_dir))
        assert result["ok"] is False
        failure_codes = {f["code"] for f in result["failures"]}
        assert "meta_contamination" in failure_codes


def test_seat_matrix_inconsistent():
    """Inconsistent seat_matrix should be detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        (run_dir / "run_metadata.json").write_text(json.dumps({
            "deep_judge": {"substantive_sources": ["search-agent"]}
        }), encoding="utf-8")
        (run_dir / "seat_matrix.json").write_text(json.dumps({
            "summary": {"valid_seats": 5},
            "seats": [
                {"id": "s1", "status": "valid"},
                {"id": "s2", "status": "skipped"},
            ]
        }), encoding="utf-8")
        (run_dir / "evidence_pack.json").write_text(json.dumps({"sources": []}), encoding="utf-8")
        (run_dir / "final_report_contract.json").write_text(json.dumps({"citations": []}), encoding="utf-8")
        (run_dir / "final_report.html").write_text("AJ_REPORT_V1 test", encoding="utf-8")
        (run_dir / "validation_result.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")

        result = validate_artifacts(str(run_dir))
        assert result["ok"] is False
        failure_codes = {f["code"] for f in result["failures"]}
        assert "seat_matrix_inconsistent" in failure_codes