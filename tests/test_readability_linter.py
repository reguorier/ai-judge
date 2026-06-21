#!/usr/bin/env python3
"""test_readability_linter.py — 验证 ReadabilityLinter。

最低要求：
- 普通用户报告 score >=85
- jargon 检测正确
- 结构检查 (has_final_verdict / has_next_action / has_so_what / appendix_separated) 正确
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

from readability.readability_linter import ReadabilityLinter, lint_report


class TestReadabilityLinter:
    """ReadabilityLinter 功能验证"""

    def _make_good_ordinary_report(self):
        return {
            "headline": "AI Judge 评估结论：该方案存在中等法律风险",
            "subtitle": "综合分析合同与法规后得出的结论",
            "decision_cards": [
                {
                    "title": "数据隐私合规",
                    "verdict": "存在风险",
                    "explanation": "该方案涉及用户数据跨境传输，需要获得用户同意",
                    "action": "建议在签署前补充数据保护条款",
                    "so_what": "所以你应该：在签署前补充数据保护条款",
                }
            ],
            "what_if_no_ai_judge": "如果没有 AI Judge，你可能需要数天查阅法规",
            "blocking_problems": [
                {
                    "title": "缺少数据保护条款",
                    "what_it_is": "合同没有约定数据保护措施",
                    "why_it_matters": "可能导致合规风险",
                    "action": "补充数据保护附录",
                }
            ],
            "ai_judge_value": {
                "title": "AI Judge 价值",
                "explanation": "AI Judge 在短时间内完成了对合同和法规的分析",
            },
            "next_steps": [
                {"action": "补充数据保护条款后重新审查", "acceptance": "条款通过合规检查"}
            ],
            "appendix": {"full_evidence": "完整证据"},
        }

    def _make_jargon_report(self):
        return {
            "headline": "AI Judge JSON schema 验证 hard gate 通过 共识矩阵确认",
            "subtitle": "renderer 和 validator 已校准",
            "decision_cards": [
                {
                    "title": "问题",
                    "verdict": "通过",
                    "explanation": "embedding RAG 幻觉率在可接受范围",
                    "so_what": "所以你可以放心",
                }
            ],
            "next_steps": [{"action": "完成"}],
            "appendix": {},
        }

    def test_linter_score_good_ordinary_report(self):
        report = self._make_good_ordinary_report()
        result = lint_report(report, "ordinary_user")
        assert result["score"] >= 85, f"Expected score >= 85, got {result['score']}"
        assert result["has_final_verdict"], "Missing final_verdict"
        assert result["has_next_action"], "Missing next_action"
        assert result["has_so_what"], "Missing so_what"
        assert result["appendix_separated"], "Missing appendix"

    def test_linter_detects_jargon(self):
        report = self._make_jargon_report()
        linter = ReadabilityLinter("ordinary_user")
        main_text = linter._extract_main_text(report)
        jargon = linter.count_jargon(main_text)
        assert jargon > 0, f"Expected jargon > 0, got {jargon}"

        result = linter.lint(report)
        # 含有大量术语的报告应得分较低
        assert result["jargon_count"] > 0
        assert len(result["avoid_terms_found"]) > 0

    def test_linter_structural_checks_complete(self):
        report = self._make_good_ordinary_report()
        linter = ReadabilityLinter("ordinary_user")
        result = linter.lint(report)

        assert "avg_sentence_chars" in result
        assert "max_sentence_chars" in result
        assert "jargon_count" in result
        assert "has_final_verdict" in result
        assert "has_next_action" in result
        assert "has_so_what" in result
        assert "appendix_separated" in result
        assert "score" in result
        assert "pass_thresholds" in result

    def test_missing_so_what_detected(self):
        report = {
            "headline": "结论",
            "decision_cards": [{"title": "Q", "verdict": "OK"}],
            "next_steps": [{"action": "done"}],
            "appendix": {},
        }
        result = lint_report(report, "ordinary_user")
        assert not result["has_so_what"], "Should not have so_what"
        assert result["score"] < 100, "Score should be penalized"

    def test_missing_appendix_detected(self):
        report = {
            "headline": "结论",
            "decision_cards": [{"title": "Q", "verdict": "OK", "so_what": "可以"}],
            "next_steps": [{"action": "done"}],
        }
        result = lint_report(report, "ordinary_user")
        assert not result["appendix_separated"], "Should not have appendix"