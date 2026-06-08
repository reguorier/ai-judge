"""P0-2: deep_judge must consume real LLM / search-agent / seat_outputs before returning success.

Integration tests for the deep_judge pipeline from create_client_run through report generation.
"""

import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.run_orchestrator import create_client_run, load_summary
from product.reporting.final_report_builder import (
    build_client_final_report,
    default_reports_root,
    write_report_bundle,
)
from product.reporting.report_schema import utc_now_iso


class TestDeepJudgeReasoningGate:
    """deep_judge MUST fail when no substantive reasoning sources are provided."""

    LEGAL_QUESTION = "迟延履行期间加倍支付的债务利息能否作为破产债权申报？（含多地法院观点）"

    def test_create_client_run_without_sources_fails(self):
        """P0-2: auto_complete deep_judge with no sources → status=failed, not completed."""
        result = create_client_run(
            question=self.LEGAL_QUESTION,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
        )
        assert result["status"] == "failed", (
            f"Expected 'failed', got '{result['status']}'. "
            f"Deep judge without LLM / search-agent / seat_outputs must fail."
        )
        assert result["reliability"] in ("none", "unknown")
        assert result["valid_seats"] == 0

    def test_deep_judge_with_search_agent_succeeds(self):
        """When search_agent_output is available, deep_judge should succeed."""
        report = build_client_final_report(
            run_id="test-dj-sa-001",
            question=self.LEGAL_QUESTION,
            mode="deep_judge",
            total_seats=5,
            valid_seats=5,
            failed_seats=0,
            search_agent_output={
                "result": (
                    "根据《破产法司法解释三》第3条，破产申请受理后债务人未履行生效法律文书"
                    "应当加倍支付的迟延利息，债权人作为破产债权申报的，人民法院不予确认。"
                    "但该利息属于惩罚性债权，在普通债权清偿完毕后的剩余财产中可按劣后债权处理。"
                    "各地法院（北京、上海、广东、江苏、浙江）主流观点趋于一致，"
                    "均不支持作为普通破产债权，但认可劣后债权地位。"
                ),
            },
        )
        assert report.get("status") != "failed"
        body = report.get("body_text", "") or report.get("core_conclusion", "")
        assert "破产" in body or "司法解释" in body


class TestDeepJudgeWithFullPipeline:
    """Full pipeline: create → report → bundle → verify."""

    LEGAL_QUESTION = "宅基地合作建房转售拆迁权益归属（甲乙丙丁案）"

    def test_full_pipeline_with_sources_produces_outputs(self):
        """Report with search_agent should write all artifacts."""
        report = build_client_final_report(
            run_id="test-full-001",
            question=self.LEGAL_QUESTION,
            mode="deep_judge",
            total_seats=5,
            valid_seats=5,
            failed_seats=0,
            search_agent_output={
                "result": (
                    "非本村村民宅基地房屋买卖合同无效。"
                    "丁可向甲主张不当得利返还（《民法典》第985条）。"
                    "案由为确认合同无效纠纷与不当得利纠纷。"
                    "被告为甲，第三人为拆迁方。诉讼请求：确认转售行为无效，"
                    "判令甲返还拆迁补偿款中房屋价值对应部分。"
                ),
            },
        )
        assert report.get("status") != "failed"

        bundle = write_report_bundle(report, default_reports_root())
        paths = bundle["paths"]
        for key in ["final_report", "html_report", "summary", "evidence_packet", "seat_matrix"]:
            assert Path(paths[key]).exists(), f"{key} not found at {paths[key]}"

        # Verify summary stats
        summary = bundle["summary"]
        assert "valid_seats" in summary
        assert "total_seats" in summary


class TestBackwardCompatibility:
    """Existing callers without new params should still work."""

    def test_product_eval_question_still_works(self):
        """Product evaluation questions that explicitly ask about the tool itself."""
        report = build_client_final_report(
            run_id="test-bc-001",
            question="product evaluation: 检查 dashboard 是否正常运行",
            mode="deep_judge",
            total_seats=3,
            valid_seats=3,
            failed_seats=0,
        )
        # Should NOT fail for product eval
        assert report.get("status") != "failed"