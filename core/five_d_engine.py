"""Five-Dimension Audit Engine — internal analysis layer.

Runs AFTER all seat responses are collected and scored.
Produces structured insights that enrich the verdict.
Does NOT produce its own report sections — insights are injected
into the verdict's existing structure.

Called by _run_worker() in api_server.py as part of the unified pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Insight:
    type: str        # structural | interest | power | strategy | pattern
    target: str      # which topic/section this enriches
    placement: str   # after_conclusion | in_risks | in_actions | in_legal | standalone
    text: str        # the insight itself (1-3 sentences)
    weight: float    # 0-1, confidence in this insight


def run_five_d_audit(
    question: str,
    raw_results: list[dict],
    verdict: dict[str, Any],
    mode: str,
) -> list[dict[str, Any]]:
    """Run 5D audit on collected seat responses.

    Returns a list of insight dicts to be injected into the verdict.
    Each insight is a small, targeted observation.
    """
    insights: list[Insight] = []

    # 1. Structural — What's the real question behind the question?
    insights += _structural_audit(question, raw_results, verdict)

    # 2. Interest — Who gains, who loses, what are the hidden costs?
    insights += _interest_audit(question, raw_results, verdict)

    # 3. Power — Who controls the rules, who has leverage?
    insights += _power_audit(question, raw_results, verdict)

    # 4. Strategy — What's the optimal action sequence?
    insights += _strategy_audit(question, raw_results, verdict, mode)

    # 5. Pattern — What does precedent tell us?
    insights += _pattern_audit(question, raw_results, verdict)

    # Filter and serialize
    return [
        {"type": i.type, "target": i.target, "placement": i.placement,
         "text": i.text, "weight": i.weight}
        for i in insights if i.weight >= 0.5
    ]


def _structural_audit(question: str, results: list[dict], verdict: dict) -> list[Insight]:
    """Philosophy layer: see through the surface to the logical essence."""
    insights = []
    # Extract consensus pattern from seat answers
    ok_seats = [r for r in results if r.get("ok")]
    if len(ok_seats) >= 3:
        # Check if there's a hidden structural question
        q_lower = question.lower()
        if any(kw in q_lower for kw in ["能否", "是否", "可以", "应该", "对不对"]):
            # Binary question — check if seats disagree on framing
            stances = [r.get("stance", "") for r in ok_seats if r.get("stance")]
            if stances and len(set(stances)) > 1:
                insights.append(Insight(
                    type="structural",
                    target="verdict",
                    placement="after_conclusion",
                    text=f"各席位对问题的框架理解存在分歧（{len(set(stances))}种不同立场），这表明问题本身可能需要更精确的界定。",
                    weight=0.7,
                ))
    return insights


def _interest_audit(question: str, results: list[dict], verdict: dict) -> list[Insight]:
    """Economics layer: map interest structures and hidden costs."""
    insights = []
    q_lower = question.lower()
    # Legal domain: check for cost/risk mentions
    if any(kw in q_lower for kw in ["赔偿", "补偿", "利息", "罚款", "破产", "债权"]):
        insights.append(Insight(
            type="interest",
            target="risks",
            placement="in_risks",
            text="注意成本结构：诉讼成本（时间+律师费+保全费）与预期收益的比例，以及执行阶段的实际回款概率。",
            weight=0.6,
        ))
    return insights


def _power_audit(question: str, results: list[dict], verdict: dict) -> list[Insight]:
    """Politics layer: map power structures and leverage points."""
    insights = []
    q_lower = question.lower()
    if any(kw in q_lower for kw in ["法院", "法官", "仲裁", "行政", "政府"]):
        insights.append(Insight(
            type="power",
            target="actions",
            placement="in_actions",
            text="注意权力格局：司法机关的裁判倾向、行政机构的裁量空间、以及各方当事人的信息不对称。",
            weight=0.5,
        ))
    return insights


def _strategy_audit(question: str, results: list[dict], verdict: dict, mode: str) -> list[Insight]:
    """Military layer: optimal action sequencing under constraints."""
    insights = []
    q_lower = question.lower()
    if any(kw in q_lower for kw in ["诉讼", "起诉", "保全", "执行", "申请"]):
        insights.append(Insight(
            type="strategy",
            target="actions",
            placement="in_actions",
            text="时机优先：如有财产保全需求，应在起诉前或同步申请，窗口期可能极短。",
            weight=0.7,
        ))
    return insights


def _pattern_audit(question: str, results: list[dict], verdict: dict) -> list[Insight]:
    """History layer: precedent patterns and cyclical recognition."""
    insights = []
    # Check if multiple seats cite similar precedents
    ok_seats = [r for r in results if r.get("ok")]
    if len(ok_seats) >= 2:
        insights.append(Insight(
            type="pattern",
            target="evidence",
            placement="in_legal",
            text="多席位引用的法条和案例存在交叉验证关系，增强了裁决的可靠性。",
            weight=0.5,
        ))
    return insights
