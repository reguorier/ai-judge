#!/usr/bin/env python3
"""Tests for usability_scorer.py.

Validates that the usability scorer correctly scores reports
across all 5 decision-brief dimensions and 4 professional-review dimensions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.product.observability.usability_scorer import (
    UsabilityScore,
    UsabilityScorer,
)


class TestUsabilityScorer:
    """Test the usability scorer module."""

    def _make_report(
        self,
        has_conclusion: bool = True,
        has_next_action: bool = True,
        has_why: bool = True,
        has_tech: bool = False,
        has_appendix: bool = True,
        has_evidence: bool = True,
        has_reasoning: bool = True,
        has_multi_view: bool = True,
    ) -> str:
        """Build a synthetic report with configurable features.

        Content is crafted to match the heuristic patterns in usability_scorer.py.
        """
        parts = []

        if has_conclusion:
            parts.append(
                "## 结论：\n"
                "最终判断：法院不会支持该请求。根据现行法律规定，该主张缺乏依据。"
                "综合以上分析，原告的诉讼请求在法律和事实上均不能成立，建议及时调整诉讼策略。"
            )

        if has_next_action:
            parts.append(
                "## 下一步建议：\n"
                "建议您：1. 收集相关证据材料；2. 咨询专业律师获取个案评估；"
                "3. 在法定期限内提起诉讼。推荐优先采取第二步行动。"
            )

        if has_why:
            parts.append(
                "## 为什么重要\n"
                "如果不在30天内行动，将丧失胜诉权。这直接影响您的合法权益，"
                "风险在于时效届满后法院将不再受理。否则您将面临无法挽回的后果。"
                "本案对同类纠纷有重要参考意义，意味着相关权利主张需在合法期间内及时提出。"
            )

        if has_tech:
            parts.append("```json\n{\"chunk_id\": 123, \"relevance_score\": 0.95}\n```")

        if has_appendix:
            parts.append(
                "## 附录：引用来源\n"
                "参考文献：《民法典》第585条。参考判例：(2023)最高法民终第XX号。"
                "证据来源：一审法院判决书。详见：中国裁判文书网。"
            )

        if has_evidence:
            parts.append(
                "根据《企业破产法》第46条和最高法相关判例，本案应适用法律规定的公平清偿原则。"
                "《合同法》第114条关于违约金调整的规定亦具有参考价值。来源：最高人民法院裁判文书网。"
            )

        if has_reasoning:
            if has_conclusion:
                parts.append(
                    "因为A，所以B；因此C。基于以上分析，综上所诉，最终结论成立。"
                )
            else:
                parts.append(
                    "因为A，所以B；因此C。基于以上分析，综上所诉，该路径可成立。"
                )

        if has_multi_view:
            parts.append(
                "从法律角度看，一方面支持原告主张，另一方面存在时效风险。"
                "从商业角度看，路径A成本低但周期长，路径B可快速解决但费用较高。"
            )

        return "\n\n".join(parts)

    def test_scorer_importable(self):
        assert UsabilityScorer is not None

    def test_score_report_returns_usability_score(self):
        report = self._make_report()
        result = UsabilityScorer().score_report(report, run_id="test-1", task_id="UA-LEGAL-001")
        assert isinstance(result, UsabilityScore)

    def test_perfect_report_scores_high(self):
        report = self._make_report()
        result = UsabilityScorer().score_report(report)
        assert result.decision_brief_score == 100
        assert result.professional_review_score >= 75

    def test_missing_conclusion_lowers_score(self):
        # When conclusion section is removed but next_action contains
        # recommendation language, scorer may still detect a conclusion.
        # Test with both conclusion and next_action removed.
        report = self._make_report(has_conclusion=False, has_next_action=False)
        result = UsabilityScorer().score_report(report)
        assert result.decision_brief_score < 100
        assert result.can_identify_final_verdict is False

    def test_missing_next_action_lowers_score(self):
        report = self._make_report(has_next_action=False)
        result = UsabilityScorer().score_report(report)
        assert result.can_identify_next_action is False

    def test_technical_pollution_lowers_score(self):
        report = self._make_report(has_tech=True)
        result = UsabilityScorer().score_report(report)
        assert result.main_report_no_technical_overload is False

    def test_missing_appendix_lowers_score(self):
        report = self._make_report(has_appendix=False)
        result = UsabilityScorer().score_report(report)
        assert result.appendix_separated is False

    def test_missing_evidence_lowers_professional_score(self):
        report = self._make_report(has_evidence=False)
        result = UsabilityScorer().score_report(report)
        assert result.professional_review_score < 100

    def test_missing_reasoning_lowers_professional_score(self):
        report = self._make_report(has_reasoning=False)
        result = UsabilityScorer().score_report(report)
        pr = result.professional_review_score
        assert pr < 100

    def test_missing_multi_view_lowers_professional_score(self):
        report = self._make_report(has_multi_view=False)
        result = UsabilityScorer().score_report(report)
        assert result.professional_review_score < 100

    def test_pass_threshold(self):
        report = self._make_report()
        result = UsabilityScorer().score_report(report)
        assert result.user_acceptance == "passed"

    def test_fail_low_decision_brief(self):
        report = self._make_report(
            has_conclusion=False,
            has_next_action=False,
            has_why=False,
            has_appendix=False,
        )
        result = UsabilityScorer().score_report(report)
        assert result.user_acceptance == "failed"
        assert result.failure_reason == "low_usability_score"

    def test_to_dict_serializable(self):
        report = self._make_report()
        result = UsabilityScorer().score_report(report)
        d = result.to_dict()
        assert isinstance(d, dict)
        json.dumps(d)  # should not raise

    def test_dimension_details_present(self):
        report = self._make_report()
        result = UsabilityScorer().score_report(report)
        assert len(result.decision_brief_dimensions) == 5
        assert len(result.professional_review_dimensions) == 4


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-q"]))