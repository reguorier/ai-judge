"""P0-3: End-to-end legal issue flow verification.

Tests the complete pipeline:
create_client_run → build_client_final_report → write_report_bundle → artifact validation.
"""

import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.run_orchestrator import create_client_run, get_client_report
from product.reporting.final_report_builder import (
    build_client_final_report,
    default_reports_root,
    write_report_bundle,
)
from product.reporting.report_quality_gate import validate_final_report_relevance


# ─── Legal issue test cases ──────────────────────────────────────────

BANKRUPTCY_QUESTION = (
    "迟延履行期间加倍支付的债务利息能否作为破产债权申报。"
    "请分析不同地区的法院是否有不同观点。"
    "（需涵盖最高人民法院、北京、上海、广东、江苏、浙江等地区）"
)

FARMHOUSE_QUESTION = (
    "案例：甲乙丙丁都不是本村村民。1989年，甲与乙在农村宅基地合作开发共建房屋，"
    "甲作为宅基地登记的权利人。1993年，乙将房屋转售给丙。"
    "2009年，丙将房屋转售给丁。现2026年宅基地房屋被纳入拆迁，"
    "甲私自与拆迁主体签订合同（尚未实际取得拆迁补偿款）。"
    "问：1、丁得以向谁主张何种权利，请求权基础是什么？"
    "2、本案案由、被告、诉讼请求如何确定？"
)

SEARCH_AGENT_BANKRUPTCY = {
    "result": (
        "## 核心结论\n\n"
        "迟延履行期间的加倍部分债务利息在破产程序中**不能作为普通破产债权申报**。\n\n"
        "## 法律依据\n\n"
        "1. 《破产法司法解释三》第3条明确规定：破产申请受理后，债务人未履行生效法律文书"
        "应当加倍支付的迟延利息，债权人作为破产债权申报的，人民法院不予确认。\n"
        "2. 《全国法院破产审判工作会议纪要》第28条确立了补偿性债权优先于惩罚性债权的原则。\n\n"
        "## 各地法院观点\n\n"
        "| 地区 | 观点 | 裁判逻辑 |\n"
        "|------|------|----------|\n"
        "| 最高人民法院 | 劣后债权 | 不确认为普通债权，可在普通债权清偿后处理 |\n"
        "| 北京 | 劣后债权 | 惩罚性债权，劣后受偿 |\n"
        "| 上海 | 劣后债权 | 与北京一致 |\n"
        "| 广东 | 劣后（近期统一）| 早期直接拒绝，近期趋同 |\n"
        "| 江苏 | 劣后债权 | 统一指导意见 |\n"
        "| 浙江 | 劣后债权 | 与江苏一致 |\n\n"
        "## 实务建议\n"
        "一般债务利息可作为普通债权申报；加倍部分利息只能主张劣后债权。"
    ),
}

SEARCH_AGENT_FARMHOUSE = {
    "result": (
        "## 核心结论\n\n"
        "非本村村民之间的宅基地房屋买卖合同**无效**。\n\n"
        "## 丁的权利救济\n\n"
        "丁可向甲主张：\n"
        "1. **不当得利返还**（《民法典》第985条）：甲无法律根据取得拆迁补偿利益\n"
        "2. **合同无效后财产返还**（《民法典》第157条）\n\n"
        "## 案由、被告、诉讼请求\n\n"
        "| 项目 | 内容 |\n"
        "|------|------|\n"
        "| 案由 | 确认合同无效纠纷 + 不当得利纠纷 |\n"
        "| 被告 | 甲 |\n"
        "| 第三人 | 拆迁方（征收主体）|\n"
        "| 诉讼请求1 | 确认1989-2009年系列转售行为无效 |\n"
        "| 诉讼请求2 | 确认补偿款中房屋价值部分归丁所有 |\n"
        "| 诉讼请求3 | 判令甲返还对应补偿款 |\n\n"
        "## 类似判例\n"
        "浙江省高院再审案：买受人居住多年并出资翻建，酌定70%-80%补偿款归实际占有人。"
    ),
}


class TestFullLegalFlow:
    """End-to-end test: legal question → report → artifact validation."""

    def test_bankruptcy_issue_full_pipeline(self):
        """议题1: 迟延履行利息 → 报告 → 验证产物"""
        report = build_client_final_report(
            run_id="e2e-bankruptcy-001",
            question=BANKRUPTCY_QUESTION,
            mode="deep_judge",
            total_seats=5,
            valid_seats=5,
            failed_seats=0,
            search_agent_output=SEARCH_AGENT_BANKRUPTCY,
        )
        assert report.get("status") != "failed", "search_agent_output should pass reasoning gate"

        bundle = write_report_bundle(report, default_reports_root())
        # Verify all 6 artifacts exist
        paths = bundle["paths"]
        for key in ["final_report", "html_report", "summary", "evidence_packet", "seat_matrix", "operator_note"]:
            assert Path(paths[key]).exists(), f"Missing artifact: {key}"

        # Verify content is about bankruptcy, not product meta
        md = Path(paths["final_report"]).read_text(encoding="utf-8")
        assert "破产" in md or "司法解释" in md, (
            f"Report must discuss bankruptcy law, not product meta. "
            f"First 500 chars: {md[:500]}"
        )

        # Quality gate check
        quality = validate_final_report_relevance(
            question=BANKRUPTCY_QUESTION,
            report_text=md,
            source_pack={"has_substantive_content": True, "search_agent_output": SEARCH_AGENT_BANKRUPTCY},
        )
        assert quality.ok, f"Quality gate failed: {quality.failures}"

    def test_farmhouse_issue_full_pipeline(self):
        """议题2: 宅基地案例 → 报告 → 验证产物"""
        report = build_client_final_report(
            run_id="e2e-farmhouse-001",
            question=FARMHOUSE_QUESTION,
            mode="deep_judge",
            total_seats=5,
            valid_seats=5,
            failed_seats=0,
            search_agent_output=SEARCH_AGENT_FARMHOUSE,
        )
        assert report.get("status") != "failed"

        bundle = write_report_bundle(report, default_reports_root())
        md = Path(bundle["paths"]["final_report"]).read_text(encoding="utf-8")
        assert "宅基地" in md or "不当得利" in md or "合同无效" in md, (
            f"Report must discuss farmhouse case, not product meta. "
            f"First 500 chars: {md[:500]}"
        )

    def test_create_client_run_integration(self):
        """create_client_run with legal issue + search_agent → full flow integration."""
        # This tests the orchestrator's deep_judge gate
        result = create_client_run(
            question=BANKRUPTCY_QUESTION,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
        )
        # Without search_agent passed through, should fail via reasoning gate
        assert result["status"] == "failed", (
            "create_client_run without reasoning sources should now fail "
            "due to deep_judge reasoning gate"
        )

    def test_both_issues_artifact_completeness(self):
        """Both legal issues: every artifact must exist and non-empty."""
        for rid, question, sa in [
            ("both-001", BANKRUPTCY_QUESTION, SEARCH_AGENT_BANKRUPTCY),
            ("both-002", FARMHOUSE_QUESTION, SEARCH_AGENT_FARMHOUSE),
        ]:
            report = build_client_final_report(
                run_id=rid, question=question, mode="deep_judge",
                total_seats=5, valid_seats=5, failed_seats=0,
                search_agent_output=sa,
            )
            assert report.get("status") != "failed", f"{rid} should succeed"

            bundle = write_report_bundle(report, default_reports_root())
            for key, path in bundle["paths"].items():
                if key == "run_dir":
                    continue
                p = Path(path)
                assert p.exists(), f"{rid}: {key} missing"
                assert p.stat().st_size > 0, f"{rid}: {key} is empty"