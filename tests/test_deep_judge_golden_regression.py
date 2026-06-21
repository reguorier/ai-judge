"""Tests for deep_judge golden regression end-to-end."""

import json
import os
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runtime" / "product"))

from observability.artifact_validator import validate_artifacts
from observability.run_metadata_observer import observe_run
from observability.failure_classifier import classify_failure
from observability.report_similarity import jaccard_similarity, compare_reports


GOLDEN_CASES_PATH = Path(__file__).resolve().parent.parent / "runtime" / "product" / "golden_cases" / "golden_cases.json"


@pytest.fixture
def golden_cases() -> list:
    with open(GOLDEN_CASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_golden_case_count(golden_cases):
    """Golden cases must have at least 5 cases."""
    assert len(golden_cases) >= 5


def test_full_validation_pipeline():
    """End-to-end: create artifacts, validate, observe, classify."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "test-run"
        run_dir.mkdir()

        # Write all artifacts
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
            ]
        }), encoding="utf-8")

        (run_dir / "evidence_pack.json").write_text(json.dumps({
            "sources": [
                {"id": "src-1", "content": "evidence"}
            ]
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

        # Validate artifacts
        val_result = validate_artifacts(str(run_dir))
        assert val_result["ok"] is True

        # Observe
        obs_result = observe_run(str(run_dir))
        assert obs_result["status"] == "completed"
        assert obs_result["artifact_ok"] is True
        assert obs_result["failure_class"] is None

        # Classify (should be no failure)
        fail_class = classify_failure(val_result["failures"])
        assert fail_class is None


def test_similarity_same_text():
    """Jaccard similarity of identical text should be 1.0."""
    text = "迟延履行期间加倍支付的债务利息能否作为破产债权申报"
    sim = jaccard_similarity(text, text)
    assert sim == 1.0


def test_similarity_different_texts():
    """Jaccard similarity of completely different texts should be 0.0."""
    text1 = "迟延履行期间加倍支付的债务利息作为破产债权申报"
    text2 = "完全不同的文本内容没有任何重叠词汇"
    sim = jaccard_similarity(text1, text2)
    # Should be very low since there's no overlap
    assert sim < 0.5