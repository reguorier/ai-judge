"""Tests for run_metadata_observer.py."""

import json
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runtime" / "product"))

from observability.run_metadata_observer import observe_run, observe_all_runs


@pytest.fixture
def complete_run_dir():
    """Create a temporary directory with a complete run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        (run_dir / "run_metadata.json").write_text(json.dumps({
            "mode": "deep_judge",
            "deep_judge": {
                "substantive_sources": ["search-agent"],
                "search_agent_status": "completed",
                "search_agent_result_count": 5,
                "search_agent_cache_hit": False,
            }
        }), encoding="utf-8")

        (run_dir / "seat_matrix.json").write_text(json.dumps({
            "summary": {"valid_seats": 3},
            "seats": [
                {"id": "s1", "status": "valid"},
                {"id": "s2", "status": "valid"},
                {"id": "s3", "status": "valid"},
                {"id": "s4", "status": "skipped"},
                {"id": "s5", "status": "skipped"},
            ]
        }), encoding="utf-8")

        (run_dir / "evidence_pack.json").write_text(json.dumps({
            "sources": [{"id": "src-1"}]
        }), encoding="utf-8")

        (run_dir / "final_report_contract.json").write_text(json.dumps({
            "citations": [{"source_id": "src-1"}]
        }), encoding="utf-8")

        (run_dir / "final_report.html").write_text(
            "<html><h1>AJ_REPORT_V1 Decision Brief</h1></html>",
            encoding="utf-8"
        )

        (run_dir / "validation_result.json").write_text(json.dumps({
            "status": "ok"
        }), encoding="utf-8")

        yield tmpdir


def test_observe_complete_run(complete_run_dir):
    """A complete valid run should have status=completed and all fields populated."""
    result = observe_run(complete_run_dir)

    assert result["run_id"] == Path(complete_run_dir).name
    assert result["mode"] == "deep_judge"
    assert result["status"] == "completed"
    assert result["substantive_sources"] == ["search-agent"]
    assert result["search_agent_status"] == "completed"
    assert result["search_agent_result_count"] == 5
    assert result["search_agent_cache_hit"] is False
    assert result["valid_seats"] == 3
    assert result["skipped_seats"] == 2
    assert result["artifact_ok"] is True
    assert result["report_validation_ok"] is True
    assert result["failure_class"] is None


def test_observe_failed_run():
    """A run with validation failure should have status=failed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        (run_dir / "run_metadata.json").write_text(json.dumps({
            "deep_judge": {"substantive_sources": []},
        }), encoding="utf-8")

        (run_dir / "seat_matrix.json").write_text(json.dumps({
            "summary": {"valid_seats": 0}, "seats": []
        }), encoding="utf-8")

        (run_dir / "evidence_pack.json").write_text(json.dumps({"sources": []}), encoding="utf-8")

        (run_dir / "final_report_contract.json").write_text(json.dumps({"citations": []}), encoding="utf-8")

        (run_dir / "final_report.html").write_text("AJ_REPORT_V1", encoding="utf-8")

        (run_dir / "validation_result.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")

        result = observe_run(str(run_dir))
        assert result["status"] == "failed"
        assert result["artifact_ok"] is False
        assert result["failure_class"] is not None


def test_observe_all_runs():
    """observe_all_runs should return results for all run directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runs_root = Path(tmpdir)

        for i in range(3):
            run_dir = runs_root / f"run_{i}"
            run_dir.mkdir()
            (run_dir / "run_metadata.json").write_text(json.dumps({
                "deep_judge": {"substantive_sources": ["search-agent"]},
            }), encoding="utf-8")
            (run_dir / "seat_matrix.json").write_text(json.dumps({
                "summary": {"valid_seats": 0}, "seats": []
            }), encoding="utf-8")
            (run_dir / "evidence_pack.json").write_text(json.dumps({"sources": []}), encoding="utf-8")
            (run_dir / "final_report_contract.json").write_text(json.dumps({"citations": []}), encoding="utf-8")
            (run_dir / "final_report.html").write_text("AJ_REPORT_V1", encoding="utf-8")
            (run_dir / "validation_result.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")

        results = observe_all_runs(str(runs_root))
        assert len(results) == 3
        for r in results:
            assert "run_id" in r
            assert "mode" in r
            assert "status" in r