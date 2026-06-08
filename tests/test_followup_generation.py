"""P1: followup_api must not generate when reasoning source is unavailable."""

import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.followup.followup_api import create_followup, _has_reasoning_source


class TestHasReasoningSource:
    """Detection of substantive reasoning sources in run directories."""

    def test_empty_dir_no_source(self, tmp_path):
        run_dir = tmp_path / "empty_run"
        run_dir.mkdir()
        assert not _has_reasoning_source(run_dir)

    def test_seat_matrix_with_valid_answer(self, tmp_path):
        run_dir = tmp_path / "run_with_seat"
        run_dir.mkdir()
        sm = {
            "seats": [
                {"status": "valid", "answer": "根据破产法司法解释三第3条..."},
                {"status": "skipped", "answer": ""},
            ]
        }
        (run_dir / "seat_matrix.json").write_text(json.dumps(sm, ensure_ascii=False))
        assert _has_reasoning_source(run_dir)

    def test_seat_matrix_all_skipped_no_source(self, tmp_path):
        run_dir = tmp_path / "run_all_skipped"
        run_dir.mkdir()
        sm = {
            "seats": [
                {"status": "skipped", "answer": ""},
                {"status": "not_configured", "answer": ""},
            ]
        }
        (run_dir / "seat_matrix.json").write_text(json.dumps(sm, ensure_ascii=False))
        assert not _has_reasoning_source(run_dir)

    def test_evidence_packet_external_search(self, tmp_path):
        run_dir = tmp_path / "run_with_evidence"
        run_dir.mkdir()
        ep = {
            "evidence_items": [
                {"type": "external_search", "description": "联网检索结果"},
            ]
        }
        (run_dir / "evidence_packet.json").write_text(json.dumps(ep, ensure_ascii=False))
        assert _has_reasoning_source(run_dir)


class TestCreateFollowupGating:
    """create_followup must gate on reasoning source availability."""

    def test_no_reasoning_source_returns_not_generated(self, tmp_path):
        run_dir = tmp_path / "empty_followup"
        run_dir.mkdir()
        result = create_followup(run_dir, "深入分析一下")
        assert result["status"] == "not_generated"
        assert result["reason"] == "followup_reasoning_unavailable"

    def test_with_reasoning_source_returns_success(self, tmp_path):
        run_dir = tmp_path / "run_with_source"
        run_dir.mkdir()
        sm = {
            "seats": [
                {"status": "valid", "answer": "宅基地合作建房转售中，非本村村民合同无效，"
                 "实际占有人丁可依据民法典第985条主张不当得利返还。"},
            ]
        }
        (run_dir / "seat_matrix.json").write_text(json.dumps(sm, ensure_ascii=False))
        # Also need summary.json for write_followup_note
        summary = {"run_id": "test-fu-001"}
        (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False))
        # And final_report.md
        (run_dir / "final_report.md").write_text("## 核心结论\n\n宅基地案例详细分析报告...")
        # And evidence_packet.json (required by load_followup_context)
        (run_dir / "evidence_packet.json").write_text(json.dumps(
            {"evidence_items": [{"type": "seat_output", "description": "席位输出"}]},
            ensure_ascii=False,
        ))
        result = create_followup(run_dir, "甲是否构成恶意串通？")
        assert "generated" in result.get("type", "") or result.get("followup_id")

    def test_empty_prompt_raises(self, tmp_path):
        run_dir = tmp_path / "run_empty_prompt"
        run_dir.mkdir()
        sm = {
            "seats": [
                {"status": "valid", "answer": "有实质内容" * 20},
            ]
        }
        (run_dir / "seat_matrix.json").write_text(json.dumps(sm, ensure_ascii=False))
        with pytest.raises(ValueError, match="follow-up prompt is required"):
            create_followup(run_dir, "   ")