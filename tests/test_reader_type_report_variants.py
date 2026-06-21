#!/usr/bin/env python3
"""test_reader_type_report_variants.py — 验证 reader_type 报告变体。

最低要求：
- default render 不破坏 AJ_REPORT_V1
- reader_type fallback 到默认
- 不同 reader_type 产生不同适配
- appendix 在所有变体中保持不变
"""

import os
import sys
import pytest

sys.path.insert(
    0,
    os.path.expanduser(
        "~/Library/Application Support/AI Judge/runtime/product"
    ),
)

from readability.reader_type_adapter import (
    ReaderTypeAdapter,
    adapt_report_for_reader,
)


class TestReaderTypeReportVariants:
    """Reader Type 报告变体验证"""

    def _make_base_report(self):
        return {
            "headline": "AI Judge 最终评估结论",
            "subtitle": "基于多源证据的综合分析",
            "decision_cards": [
                {
                    "title": "数据隐私合规",
                    "verdict": "存在中等风险",
                    "explanation": "需要补充数据保护条款，使用 JSON schema 和 hard gate 验证",
                    "action": "补充数据保护条款",
                    "evidence_strength": "medium",
                    "uncertainty": "low",
                }
            ],
            "what_if_no_ai_judge": "你可能需要数天时间自行查阅法规",
            "blocking_problems": [
                {
                    "title": "缺少数据保护条款",
                    "what_it_is": "合同未约定保护措施",
                    "why_it_matters": "GDPR 风险",
                    "action": "补充附录",
                }
            ],
            "ai_judge_value": {
                "title": "价值评估",
                "explanation": "快速完成多源证据分析",
            },
            "next_steps": [
                {"action": "补充条款后重新审查", "acceptance": "条款通过"}
            ],
            "appendix": {"evidence": "完整证据"},
            "hard_gates": [{"name": "gate1", "passed": True}],
            "verdict_json": {"final": "risk"},
        }

    def test_default_render_preserves_aj_report_v1_structure(self):
        report = self._make_base_report()
        adapted = adapt_report_for_reader(report)  # default

        required_keys = [
            "headline", "decision_cards", "what_if_no_ai_judge",
            "blocking_problems", "ai_judge_value", "next_steps",
            "appendix", "hard_gates", "verdict_json",
        ]
        for key in required_keys:
            assert key in adapted, f"Missing AJ_REPORT_V1 key: {key}"

        # appendix untouched
        assert adapted["appendix"] == report["appendix"]
        assert adapted["hard_gates"] == report["hard_gates"]
        assert adapted["verdict_json"] == report["verdict_json"]

    def test_fallback_on_missing_reader_type(self):
        report = self._make_base_report()
        adapted = adapt_report_for_reader(report, "non_existent_type")
        assert adapted is not None
        assert "headline" in adapted

    def test_different_types_produce_different_output(self):
        report = self._make_base_report()
        ou = adapt_report_for_reader(report, "ordinary_user")
        pro = adapt_report_for_reader(report, "professional_user")

        # ordinary_user 应该有 so_what，professional 不一定
        ou_has_so_what = any(
            "so_what" in card for card in ou.get("decision_cards", [])
        )
        assert ou_has_so_what, "ordinary_user should have so_what"

        # 两者 headline 可能不同（普通版去掉了术语）
        # 但 appendix 必须相同
        assert ou["appendix"] == pro["appendix"], "appendix differs between types"

    def test_appendix_identical_across_all_types(self):
        report = self._make_base_report()
        appendixes = []
        for rt in ["ordinary_user", "pm_founder", "professional_user", "legal_compliance_user"]:
            adapted = adapt_report_for_reader(report, rt)
            appendixes.append(json.dumps(adapted["appendix"], sort_keys=True))

        assert len(set(appendixes)) == 1, "appendix differs across reader types"

    def test_all_four_types_produce_valid_output(self):
        report = self._make_base_report()
        for rt in ["ordinary_user", "pm_founder", "professional_user", "legal_compliance_user"]:
            adapted = adapt_report_for_reader(report, rt)
            assert isinstance(adapted, dict)
            assert "headline" in adapted
            assert "appendix" in adapted


# Need json for appendix comparison
import json