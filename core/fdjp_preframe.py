"""Five-Dimension Pre-Frame — runs BEFORE seat distribution.

Enriches the professional prompt with five-dimensional analysis context.
Called by build_prompt_flow() in prompt_resonance.py.

This module adds structural, interest, power, strategy, and pattern
context to the prompt that seats will receive, so each seat's answer
is already informed by multi-dimensional thinking.
"""

from __future__ import annotations

from typing import Any


def build_fdjp_preframe(
    question: str,
    mode: str,
    intent: str,
    required_output: list[str],
    assumptions: list[str],
) -> dict[str, Any]:
    """Build five-dimensional pre-frame context for prompt enrichment.

    Returns a dict with:
    - preframe_lines: list of context lines to append to the professional prompt
    - dimensions: dict of dimension-specific analysis
    """
    dimensions = {}

    # 1. Structural — what's the real question?
    structural = _structural_preframe(question, intent)
    dimensions["structural"] = structural

    # 2. Interest — who gains, who loses?
    interest = _interest_preframe(question)
    dimensions["interest"] = interest

    # 3. Power — who controls the rules?
    power = _power_preframe(question)
    dimensions["power"] = power

    # 4. Strategy — optimal action sequence?
    strategy = _strategy_preframe(question, mode)
    dimensions["strategy"] = strategy

    # 5. Pattern — what does precedent tell us?
    pattern = _pattern_preframe(question)
    dimensions["pattern"] = pattern

    # Build preframe lines to append to professional prompt
    preframe_lines = []
    for dim_name, dim_data in dimensions.items():
        if dim_data.get("context_line"):
            preframe_lines.append(f"[{dim_name}] {dim_data['context_line']}")

    return {
        "preframe_lines": preframe_lines,
        "dimensions": dimensions,
    }


def _structural_preframe(question: str, intent: str) -> dict[str, Any]:
    """Analyze the logical structure of the question."""
    q = question.lower()
    framing_note = ""
    if any(kw in q for kw in ["能否", "是否", "可以", "应该", "对不对"]):
        framing_note = "这是一个二元判断问题，请注意区分'事实层面'和'价值层面'的判断。"
    elif any(kw in q for kw in ["如何", "怎么", "方案", "策略"]):
        framing_note = "这是一个方案设计问题，请注意区分'目标'、'约束条件'和'可行路径'。"
    return {"context_line": framing_note, "question_type": "binary" if framing_note else "open"}


def _interest_preframe(question: str) -> dict[str, Any]:
    """Analyze the interest structure."""
    q = question.lower()
    note = ""
    if any(kw in q for kw in ["赔偿", "补偿", "利息", "破产", "债权", "拆迁"]):
        note = "涉及利益分配，请分析各方的成本结构和收益预期。"
    return {"context_line": note}


def _power_preframe(question: str) -> dict[str, Any]:
    """Analyze the power structure."""
    q = question.lower()
    note = ""
    if any(kw in q for kw in ["法院", "仲裁", "行政", "政府", "管理", "审批"]):
        note = "涉及权力结构，请注意话语权分布和规则制定权。"
    return {"context_line": note}


def _strategy_preframe(question: str, mode: str) -> dict[str, Any]:
    """Analyze the strategic dimension."""
    note = ""
    if mode in ("strategic", "deep_judge"):
        note = "深度模式：请给出分阶段行动方案，注意时机和资源约束。"
    return {"context_line": note}


def _pattern_preframe(question: str) -> dict[str, Any]:
    """Analyze historical patterns."""
    q = question.lower()
    note = ""
    if any(kw in q for kw in ["法律", "法规", "判例", "案例", "司法"]):
        note = "请引用相关法条、司法解释和典型案例，注意裁判演进趋势。"
    return {"context_line": note}
