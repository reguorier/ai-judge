#!/usr/bin/env python3
"""test_reader_type_adapter.py — 验证 ReaderTypeAdapter。

最低要求：
- ordinary_user 不出现技术术语
- ordinary_user 有最终结论和下一步
- professional_user 保留证据和不确定性
- appendix 不被 adapter 修改
"""

import json
import os
import sys
import pytest

# Insert readability module path
sys.path.insert(
    0,
    os.path.expanduser(
        "~/Library/Application Support/AI Judge/runtime/product"
    ),
)

from readability.reader_type_adapter import (
    ReaderTypeAdapter,
    adapt_report_for_reader,
    _remove_jargon,
    _add_so_what,
)


class TestReaderTypeAdapter:
    """ReaderTypeAdapter 行为验证"""

    def _make_report(self):
        return {
            "headline": "AI Judge 通过 JSON schema 和 hard gate 完成了最终验证",
            "subtitle": "renderer 渲染 validator 结果，含共识矩阵分析",
            "decision_cards": [
                {
                    "title": "数据隐私",
                    "verdict": "存在风险",
                    "explanation": "该方案涉及 embedding 和 RAG 的幻觉率偏高",
                    "action": "补充数据保护条款",
                }
            ],
            "what_if_no_ai_judge": "你可能需要数天查阅法规和判例",
            "blocking_problems": [
                {
                    "title": "缺少数据保护条款",
                    "what_it_is": "合同未约定数据保护措施，grounding 不足",
                    "why_it_matters": "可能导致合规风险",
                    "action": "补充数据保护附录",
                }
            ],
            "ai_judge_value": {
                "title": "AI Judge 在推理门控下完成",
                "explanation": "通过 token 级别校准层和语义审计",
            },
            "next_steps": [
                {"action": "补充条款后重新审查", "acceptance": "条款通过合规检查"}
            ],
            "appendix": {"full_evidence": "完整证据"},
            "hard_gates": [{"name": "gate_1", "passed": True}],
            "verdict_json": {"verdict": "risk"},
            "evidence_pack": {"sources": ["source1"]},
            "search_agent_output": {"results": []},
            "validation_result": {"ok": True},
        }

    def test_ordinary_user_removes_jargon(self):
        report = self._make_report()
        adapted = adapt_report_for_reader(report, "ordinary_user")

        main_text = json.dumps(adapted, ensure_ascii=False)
        forbidden = ["JSON", "schema", "hard gate", "renderer", "validator", "共识矩阵",
                     "embedding", "RAG", "幻觉率", "grounding", "推理门控", "token",
                     "校准层", "语义审计"]
        for term in forbidden:
            assert term not in adapted.get("headline", ""), f"'{term}' in headline"
            assert term not in adapted.get("subtitle", ""), f"'{term}' in subtitle"
            assert term not in str(adapted.get("decision_cards", [])), f"'{term}' in decision_cards"

        # 但 appendix 保留原始
        assert adapted["appendix"] == report["appendix"]

    def test_ordinary_user_has_so_what(self):
        report = self._make_report()
        adapted = adapt_report_for_reader(report, "ordinary_user")

        cards = adapted.get("decision_cards", [])
        assert len(cards) > 0
        for card in cards:
            assert "so_what" in card, f"so_what missing from card: {card.get('title')}"
            assert len(card["so_what"]) > 3, f"so_what too short: {card['so_what']}"

    def test_professional_preserves_evidence(self):
        report = self._make_report()
        # Add evidence_strength and uncertainty for professional test
        report["decision_cards"][0]["evidence_strength"] = "medium"
        report["decision_cards"][0]["uncertainty"] = "low"

        adapted = adapt_report_for_reader(report, "professional_user")
        card = adapted["decision_cards"][0]
        assert card.get("evidence_strength") == "medium", "evidence_strength lost"
        assert card.get("uncertainty") == "low", "uncertainty lost"

    def test_appendix_untouched(self):
        report = self._make_report()
        for rt in ["ordinary_user", "pm_founder", "professional_user", "legal_compliance_user"]:
            adapted = adapt_report_for_reader(report, rt)
            assert adapted["appendix"] == report["appendix"], f"appendix modified for {rt}"
            assert adapted["hard_gates"] == report["hard_gates"], f"hard_gates modified for {rt}"
            assert adapted["verdict_json"] == report["verdict_json"], f"verdict_json modified for {rt}"
            assert adapted["evidence_pack"] == report["evidence_pack"], f"evidence_pack modified for {rt}"

    def test_default_render_preserves_aj_report_v1(self):
        report = self._make_report()
        adapted = adapt_report_for_reader(report)  # default = ordinary_user

        # 所有 AJ_REPORT_V1 关键字段存在
        for key in ["headline", "decision_cards", "appendix", "hard_gates", "verdict_json"]:
            assert key in adapted, f"Missing AJ_REPORT_V1 key: {key}"

    def test_fallback_on_unknown_reader_type(self):
        report = self._make_report()
        adapted = adapt_report_for_reader(report, "nonexistent_type")
        # 应该 fallback 到 default (ordinary_user)
        assert adapted is not None
        assert "headline" in adapted