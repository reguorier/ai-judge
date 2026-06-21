"""P0: Final report builder must be grounded in issue outputs, not product meta."""

import json
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.final_report_builder import (
    build_client_final_report,
    collect_sources,
    fail_no_report,
    SourcePack,
    write_report_bundle,
)
from product.reporting.html_renderer import render_final_report_html


class TestReportGroundedInIssue:
    """final_report_builder: body driven by user issue, not AI Judge product meta."""

    def test_no_sources_returns_failure_for_legal_issue(self):
        """P0-2: deep_judge without LLM/search-agent/seat_outputs → failure, not fake meta report."""
        report = build_client_final_report(
            run_id="test-legal-001",
            question="迟延履行期间的债务利息能否作为破产债权申报？",
            mode="deep_judge",
            total_seats=3,
            valid_seats=3,
            failed_seats=0,
        )
        assert report.get("status") == "failed", "no-source deep_judge must fail"
        assert report.get("_failure") is not None
        fail = report["_failure"]
        assert fail["reason"] == "deep_judge_no_substantive_reasoning"

    def test_no_sources_passes_for_product_eval(self):
        """Product evaluation questions (explicitly about the tool) are allowed without sources."""
        report = build_client_final_report(
            run_id="test-product-001",
            question="product dashboard client 验证",  # product keyword
            mode="deep_judge",
            total_seats=3,
            valid_seats=3,
            failed_seats=0,
        )
        assert report.get("status") != "failed"

    def test_with_search_agent_output_is_accepted(self):
        """When search_agent_output is passed, report should succeed."""
        report = build_client_final_report(
            run_id="test-legal-002",
            question="宅基地合作建房拆迁补偿归属问题",
            mode="deep_judge",
            total_seats=5,
            valid_seats=5,
            failed_seats=0,
            search_agent_output={
                "result": "根据《土地管理法》第62条，非本村村民购买宅基地房屋的合同无效。"
                          "但在拆迁背景下，法院通常基于诚实信用原则酌定补偿款分配。"
                          "实际占有人可依据《民法典》第985条主张不当得利返还。"
                          "（详细分析见报告全文……以此填充至少100个字符以满足check）",
                "summary": "宅基地买卖无效，补偿款归属需平衡登记人与实际占有人利益。",
            },
        )
        assert report.get("status") != "failed"
        # Body should contain search agent text, not product meta
        body = report.get("body_text", "") or report.get("core_conclusion", "")
        assert "土地管理法" in body or "宅基地" in body or "补偿" in body

    def test_with_seat_outputs_is_accepted(self):
        """When seat_outputs with substantive answers are passed, report should succeed."""
        report = build_client_final_report(
            run_id="test-legal-003",
            question="迟延履行利息破产债权申报",
            mode="deep_judge",
            total_seats=3,
            valid_seats=3,
            failed_seats=0,
            seat_outputs=[
                {
                    "seat_id": "report_builder",
                    "display_name": "Report Builder",
                    "status": "completed",
                    "answer": "迟延履行期间的加倍利息属于惩罚性债权，"
                             "根据《破产法司法解释三》第3条不作为普通破产债权确认，"
                             "但可主张为劣后债权。各地法院主流观点趋于一致。"
                             "最高人民法院及北京、上海、广东、江苏、浙江等地的裁判"
                             "实践均支持劣后债权说，即破产债权清偿完毕后仍有剩余财产时"
                             "才予以清偿，若无剩余则无需清偿。",
                },
            ],
        )
        assert report.get("status") != "failed"

    def test_fail_no_report_structure(self):
        """fail_no_report returns expected structure."""
        result = fail_no_report(run_id="test-fail", reason="test_reason", failures=["f1", "f2"])
        assert result["status"] == "failed"
        assert result["_failure"]["reason"] == "test_reason"
        assert result["_failure"]["failures"] == ["f1", "f2"]

    def test_write_bundle_persists_noise_audit(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AI_JUDGE_MODEL_STABILITY_PATH", str(tmp_path / "model_stability_profiles.json"))
        report = build_client_final_report(
            run_id="test-noise-bundle",
            question="product noise audit bundle 验证",
            mode="deep_judge",
            total_seats=3,
            valid_seats=2,
            failed_seats=1,
        )

        bundle = write_report_bundle(report, reports_root=tmp_path)
        summary = bundle["summary"]
        noise_path = Path(bundle["paths"]["noise_audit"])
        judge_ir_path = Path(bundle["paths"]["judge_ir"])
        markdown = Path(bundle["paths"]["final_report"]).read_text(encoding="utf-8")
        noise = json.loads(noise_path.read_text(encoding="utf-8"))
        judge_ir = json.loads(judge_ir_path.read_text(encoding="utf-8"))

        assert noise_path.exists()
        assert judge_ir_path.exists()
        assert noise["schema"] == "ai_judge.noise_audit.v1"
        assert judge_ir["schema"] == "ai_judge.judge_ir.v1"
        assert [section["slot"] for section in judge_ir["sections"]] == [
            "summary",
            "metrics",
            "analysis",
            "comparison",
            "risk",
            "appendix",
        ]
        assert summary["noise_score"] == noise["noise_score"]
        assert summary["judge_ir_path"] == str(judge_ir_path)
        assert summary["noise_level"] == noise["noise_level"]
        assert summary["model_stability_profile_count"] >= 1
        assert "Noise Audit / 噪声审计" in markdown
        assert "Model Stability / 模型稳定性画像" in markdown

    def test_final_report_html_uses_judge_ir_component_renderer(self):
        report = build_client_final_report(
            run_id="test-schema-html",
            question="product schema-driven client renderer 验证",
            mode="deep_judge",
            total_seats=3,
            valid_seats=3,
            failed_seats=0,
        )

        html = render_final_report_html(report)

        assert 'content="judge-ir-component-renderer" name="ai-judge-renderer"' in html
        assert "审阅目录" in html
        assert "核心摘要" in html
        assert "风险矩阵" in html
        assert "MetricGrid" not in html
        assert "<script" not in html


class TestCollectSources:
    """SourcePack building from various input types."""

    def test_empty_inputs(self):
        sp = collect_sources(question="test")
        assert not sp.has_substantive_content

    def test_search_agent_only(self):
        sp = collect_sources(
            question="test",
            search_agent_output={"result": "详细分析内容，超过100字符的限制。" * 5},
        )
        assert sp.has_substantive_content
        assert "search_agent" in sp.source_labels

    def test_seat_outputs_only(self):
        sp = collect_sources(
            question="test",
            seat_outputs=[
                {"seat_id": "s1", "answer": "诉讼请求应确认合同无效并主张不当得利返还。" * 3},
            ],
        )
        assert sp.has_substantive_content
        assert "seat_outputs" in sp.source_labels

    def test_short_search_agent_ignored(self):
        """Search agent with too-short result doesn't count."""
        sp = collect_sources(
            question="test",
            search_agent_output={"result": "短"},
        )
        assert not sp.has_substantive_content

    def test_short_seat_outputs_ignored(self):
        sp = collect_sources(
            question="test",
            seat_outputs=[{"seat_id": "s1", "answer": ""}],
        )
        assert not sp.has_substantive_content
