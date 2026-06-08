"""P0: Test deep_judge reasoning gate via run_orchestrator.create_client_run.

Covers:
- test_api_deep_judge_bankruptcy_uses_search_or_llm
- test_api_deep_judge_homestead_uses_search_or_llm
- test_api_deep_judge_fails_without_reasoning_source
- test_api_final_report_not_meta_template
- test_two_legal_api_reports_are_distinct
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
from product.reporting.report_schema import utc_now_iso


# ─── Shared test data ─────────────────────────────────────────────────

BANKRUPTCY_Q = (
    "迟延履行期间加倍支付的债务利息能否作为破产债权申报？"
)

FARMHOUSE_Q = (
    "宅基地房屋拆迁补偿纠纷中实际买受人如何主张权利？"
)

SEARCH_AGENT_BANKRUPTCY = {
    "result": (
        "## 核心结论\n\n"
        "根据《破产法司法解释三》第3条，破产申请受理后债务人未履行生效法律文书"
        "应当加倍支付的迟延利息，债权人作为破产债权申报的，人民法院不予确认。"
        "加倍利息属于惩罚性债权，在普通债权清偿完毕后可按劣后债权处理。"
        "各地法院（北京、上海、广东、江苏、浙江）主流观点趋于一致，"
        "均不支持作为普通破产债权，但认可劣后债权地位。\n\n"
        "关键时间节点：受理前产生的利息与受理后加倍利息应区分处理。"
    ),
}

SEARCH_AGENT_FARMHOUSE = {
    "result": (
        "## 核心结论\n\n"
        "非本村村民之间的宅基地房屋买卖合同无效。\n\n"
        "## 权利救济\n\n"
        "1. 实际买受人可依据《民法典》第985条主张不当得利返还。\n"
        "2. 合同无效后财产返还依据《民法典》第157条。\n"
        "3. 实际占有人可主张折价补偿和信赖利益赔偿。\n"
        "4. 部分判例支持实际占有人取得拆迁安置资格。\n\n"
        "## 类似判例\n"
        "浙江省高院再审案：买受人居住多年并出资翻建，酌定70%-80%补偿款归实际占有人。"
    ),
}

META_TEMPLATE_BLACKLIST = [
    "AI Judge 产品价值",
    "B2B SaaS",
    "报告视觉",
    "dashboard",
    "投资人",
    "产品评估",
    "薄客户端",
    "meta 模板",
]


# ─── Tests ────────────────────────────────────────────────────────────

class TestDeepJudgeWithoutSourcesFails:
    """Requirements: iii — no sources → status=failed, final_report_generated=false."""

    def test_api_deep_judge_fails_without_reasoning_source(self):
        """deep_judge with no sources must return status=failed."""
        result = create_client_run(
            question=BANKRUPTCY_Q,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
        )
        assert result["status"] == "failed", (
            f"Expected 'failed', got '{result['status']}'"
        )
        assert "reason" in result.get("deep_judge", {}) or result.get("reliability") in ("none", "unknown")
        # final_report_path must be empty or absent
        fp = result.get("final_report_path", "")
        assert fp == "" or fp is None, (
            f"Should not generate a report when sources are absent, got: {fp}"
        )


class TestBankruptcyDeepJudgeWithSource:
    """Requirement: v — bankruptcy API E2E with required keywords."""

    def test_api_deep_judge_bankruptcy_uses_search_or_llm(self):
        """Bankruptcy deep_judge with search_agent must produce relevant report."""
        result = create_client_run(
            question=BANKRUPTCY_Q,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
            search_agent_output=SEARCH_AGENT_BANKRUPTCY,
        )
        assert result["status"] in ("completed", "reporting"), (
            f"Expected completed/reporting, got '{result['status']}'"
        )

        # Verify deep_judge metadata
        dj = result.get("deep_judge", {})
        assert dj.get("search_agent_calls", 0) >= 1, (
            f"search_agent_calls should be >= 1, got {dj}"
        )
        assert "search-agent" in dj.get("substantive_sources", [])

        # Read the generated report
        fp = result.get("final_report_path", "")
        assert Path(fp).exists(), f"Final report not found at {fp}"
        md = Path(fp).read_text(encoding="utf-8")

        # Must contain bankruptcy-related keywords
        for kw in ["破产债权", "迟延履行", "加倍利息"]:
            assert kw in md, f"Required keyword '{kw}' not found in report"

        # Time-split expression (受理前/受理后 or similar)
        has_time_split = any(kw in md for kw in ["受理前", "受理后", "时间切分", "区分"])
        assert has_time_split, (
            f"Report must discuss time-based distinction. "
            f"First 500 chars: {md[:500]}"
        )

        # Must NOT contain product meta talk
        for black in META_TEMPLATE_BLACKLIST:
            assert black not in md, (
                f"Forbidden meta phrase '{black}' found in bankruptcy report"
            )

    def test_api_final_report_not_meta_template(self):
        """Requirement: iv — final report must NOT be a meta template."""
        result = create_client_run(
            question=BANKRUPTCY_Q,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
            search_agent_output=SEARCH_AGENT_BANKRUPTCY,
        )
        assert result["status"] in ("completed", "reporting")

        fp = result.get("final_report_path", "")
        md = Path(fp).read_text(encoding="utf-8")

        # The blacklist is the "must not appear" set
        for phrase in META_TEMPLATE_BLACKLIST:
            assert phrase not in md, f"Meta template phrase '{phrase}' found in report"


class TestFarmhouseDeepJudgeWithSource:
    """Requirement: vi — farmhouse API E2E with required keywords."""

    def test_api_deep_judge_homestead_uses_search_or_llm(self):
        """Farmhouse deep_judge with search_agent must produce relevant report."""
        result = create_client_run(
            question=FARMHOUSE_Q,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
            search_agent_output=SEARCH_AGENT_FARMHOUSE,
        )
        assert result["status"] in ("completed", "reporting"), (
            f"Expected completed/reporting, got '{result['status']}'"
        )

        # Verify deep_judge metadata
        dj = result.get("deep_judge", {})
        assert dj.get("search_agent_calls", 0) >= 1

        fp = result.get("final_report_path", "")
        assert Path(fp).exists()
        md = Path(fp).read_text(encoding="utf-8")

        # Must contain farmhouse-related keywords
        for kw in ["宅基地", "拆迁补偿"]:
            assert kw in md, f"Required keyword '{kw}' not found in report"

        #  农村房屋 / 宅基地房屋 至少其一
        assert ("农村房屋" in md or "宅基地房屋" in md), (
            "Neither '农村房屋' nor '宅基地房屋' found in report"
        )

        # Must contain at least one of: 合同效力 / 合同无效
        has_contract = any(kw in md for kw in ["合同效力", "合同无效"])
        assert has_contract, f"Contract validity keywords not found in report"

        # Must contain at least two of: 返还 / 折价 / 信赖利益 / 安置资格
        relief_keywords = ["返还", "折价", "信赖利益", "安置资格"]
        found = sum(1 for kw in relief_keywords if kw in md)
        assert found >= 2, (
            f"Need at least 2 relief keywords, found {found}. "
            f"First 500 chars: {md[:500]}"
        )


class TestTwoReportsDistinct:
    """Requirement: vii — two legal reports body similarity < 0.70."""

    def test_two_legal_api_reports_are_distinct(self):
        """Bankruptcy and farmhouse reports must be substantially distinct."""
        r1 = create_client_run(
            question=BANKRUPTCY_Q,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
            search_agent_output=SEARCH_AGENT_BANKRUPTCY,
        )
        r2 = create_client_run(
            question=FARMHOUSE_Q,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
            search_agent_output=SEARCH_AGENT_FARMHOUSE,
        )

        fp1 = r1.get("final_report_path", "")
        fp2 = r2.get("final_report_path", "")

        assert Path(fp1).exists()
        assert Path(fp2).exists()

        md1 = Path(fp1).read_text(encoding="utf-8")
        md2 = Path(fp2).read_text(encoding="utf-8")

        # Simple Jaccard-style word overlap
        def tokenize(text: str) -> set[str]:
            # Split on whitespace + punctuation, filter short tokens
            import re
            tokens = re.split(r"\s+|[,.;:!?()，。；：！？（）\n]", text)
            return {t.strip() for t in tokens if len(t.strip()) >= 2}

        t1 = tokenize(md1)
        t2 = tokenize(md2)

        if not t1 or not t2:
            pytest.skip("One or both reports have no tokens to compare")

        intersection = t1 & t2
        union = t1 | t2
        similarity = len(intersection) / len(union) if union else 1.0

        assert similarity < 0.70, (
            f"Reports too similar: Jaccard={similarity:.3f}. "
            f"Must be < 0.70 to confirm distinct legal analyses."
        )


class TestDeepJudgeMetadata:
    """Requirement: iii — run metadata must include deep_judge block."""

    def test_metadata_written_on_success(self):
        """Successful run must have deep_judge metadata."""
        result = create_client_run(
            question=BANKRUPTCY_Q,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
            search_agent_output=SEARCH_AGENT_BANKRUPTCY,
        )
        dj = result.get("deep_judge", {})
        required_keys = ["llm_calls", "search_agent_calls", "seat_outputs_consumed", "substantive_sources", "degraded"]
        for key in required_keys:
            assert key in dj, f"deep_judge metadata missing key: {key}"

    def test_metadata_written_on_failure(self):
        """Failed run must also have deep_judge metadata with degraded=true."""
        result = create_client_run(
            question=BANKRUPTCY_Q,
            mode="deep_judge",
            auto_complete=True,
            total_seats=5,
        )
        dj = result.get("deep_judge", {})
        assert dj.get("degraded") is True, (
            f"Failed run should have degraded=True, got: {dj}"
        )


class TestNonDeepJudgeModesUnaffected:
    """Other modes must still work."""

    def test_quick_judge_still_works(self):
        """quick_judge should not go through deep_judge gate."""
        result = create_client_run(
            question="Is this software secure?",
            mode="quick_judge",
            auto_complete=True,
            total_seats=3,
            search_agent_output=SEARCH_AGENT_BANKRUPTCY,
        )
        # quick_judge is not deep_judge, so it should complete
        assert result["status"] in ("completed", "reporting"), (
            f"quick_judge should still work, got {result['status']}"
        )

    def test_ops_check_still_works(self):
        """ops_check should not go through deep_judge gate."""
        result = create_client_run(
            question="Check system health",
            mode="ops_check",
            auto_complete=True,
            total_seats=3,
        )
        assert result["status"] in ("completed", "reporting")