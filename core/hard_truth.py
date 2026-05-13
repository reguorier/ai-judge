#!/usr/bin/env python3
"""Hard Truth Mode v3.0 — L0-L4 judgment-first feedback.

AI Judge V3 core module. Implements:
  - L0-L4 escalation based on cognitive risk signals
  - "Hard Truth" output template (when smart_sounding >> judgment_quality)
  - Heterogeneity exemption (protect neurodiversity)
  - Performative acceptance detection

User-facing: "判断优先模式" (not "自私模式")
"""

from __future__ import annotations

from typing import Any, Optional


# ── L0-L4 Trigger Logic ──

def determine_mode(
    profile: dict[str, Any],
    history: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Determine which feedback mode to use based on neuro-cognitive profile.

    Args:
        profile: Full neuro_profile output from neuro_profiler.py
        history: Recent session history for pattern detection

    Returns:
        Mode determination with level, label, and action
    """
    history = history or []

    signals = profile.get("signals", {})
    sc = signals.get("self_closure", {})
    af = signals.get("ambiguity_flexibility", {})
    eg = signals.get("experience_grounding", {})
    rec = signals.get("recovery_after_negative", {})

    gap = profile.get("smart_vs_judgment_gap", 0)
    flags = profile.get("cognitive_risk_flags", [])
    jq = profile.get("judgment_quality_score", 0.5)

    # ── L4: Safety downgrade ──
    if _detect_high_risk_topic(profile):
        return _mode_response(4, "安全降级", "高风险话题，转为安全建议模式。")

    # ── L3: Forced evidence ──
    if len(flags) >= 3 and jq < 0.4:
        consecutive_defensive = sum(
            1 for h in history[-5:]
            if h.get("recovery_label") == "defensive_collapse"
        )
        if consecutive_defensive >= 3:
            return _mode_response(3, "强制证据",
                "多次防御性反应 + 质量不升。停止扩展，只接受可验证证据。")

    # ── L2: Judgment-first ──
    if (
        (gap > 0.30 and jq < 0.5)
        or (sc.get("self_closure_score", 0) > 0.7 and af.get("ambiguity_flexibility_score", 0.5) < 0.3)
        or (eg.get("semantic_fluency_risk", 0) > 0.7 and af.get("ambiguity_flexibility_score", 0.5) < 0.4)
    ):
        return _mode_response(2, "判断优先",
            "smart_sounding高但judgment_quality低，切换判断优先模式。")

    # ── L1: Calibration ──
    if gap > 0.15 or len(flags) >= 1:
        return _mode_response(1, "校准反馈",
            "检测到轻度认知偏差，提供校准建议。")

    # ── L0: Normal ──
    return _mode_response(0, "普通反馈", "正常模式。")


def _mode_response(level: int, label: str, reason: str) -> dict[str, Any]:
    names = ["普通反馈", "校准反馈", "判断优先", "强制证据", "安全降级"]
    return {
        "mode_level": level,
        "mode_name": names[level] if level < len(names) else label,
        "trigger_reason": reason,
        "hard_truth_active": level >= 2,
    }


def _detect_high_risk_topic(profile: dict) -> bool:
    """Simplified high-risk topic detection. Full version uses topic classifier."""
    # Placeholder — in production, check against risk topic list
    return False


# ── L2 Hard Truth Output Template ──

def generate_hard_truth_output(
    profile: dict[str, Any],
    original_text: str,
    snippets: Optional[list[str]] = None,
) -> str:
    """Generate the L2 '判断优先' output.

    Structured: Current verdict → Cognitive blind spots → Evidence → Fix action → Pause.
    """
    signals = profile.get("signals", {})
    sc = signals.get("self_closure", {})
    af = signals.get("ambiguity_flexibility", {})
    eg = signals.get("experience_grounding", {})

    ss = profile.get("smart_sounding_score", 0)
    jq = profile.get("judgment_quality_score", 0)
    gap = profile.get("smart_vs_judgment_gap", 0)

    lines = ["═══ 判断优先模式 ═══", ""]
    lines.append(f"smart_sounding: {ss:.2f}  |  judgment_quality: {jq:.2f}")
    lines.append(f'差距: {gap:.0%} — 这段输出「听起来聪明」，但不应被直接采信。')
    lines.append("")

    # Blind spots
    lines.append("认知盲区：")
    idx = 1
    if sc.get("label") == "high_self_closure":
        lines.append(f'  {idx}. 自我视角闭环：在应引入外部视角处仍以「我」主导。')
        lines.append(f"     缺失视角: {sc.get('missed_perspective_slots', 0)} 个")
        idx += 1
    if af.get("label") == "low_flexibility_choose_side":
        lines.append(f"  {idx}. 模糊性回避：面对矛盾时直接选边，未进行悬置探索。")
        lines.append(f"     闭合标记: {af.get('closure_markers', 0)} 处")
        idx += 1
    if eg.get("label") == "concept_driven":
        lines.append(f"  {idx}. 概念漂浮：大量抽象词汇缺乏经验锚定。")
        lines.append(f"     抽象词比例: {eg.get('abstract_noun_ratio', 0):.0%}")
        idx += 1

    lines.append("")

    # Evidence snippets
    if snippets:
        lines.append("原文证据：")
        for i, s in enumerate(snippets[:3]):
            lines.append(f"  [{i + 1}] {s[:120]}...")
        lines.append("")

    # Minimum fix action
    lines.append("最小修复动作（请回答以下三个问题）：")
    lines.append("  a. 你的哪个主张可以被证伪？给出可验证条件。")
    lines.append("  b. 哪个反方观点可能是真的？为什么？")
    lines.append("  c. 你下一步用什么数据或实验来验证？")
    lines.append("")

    # Pause
    lines.append("暂停项：在完成上述修复前，不建议继续扩展概念、增加术语或设计新方案。")

    return "\n".join(lines)


# ── Heterogeneity Exemption ──

def check_heterogeneity_exemption(
    profile: dict[str, Any],
    novelty_signals: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Check if user qualifies for heterogeneity exemption.

    When cognitive patterns are extremely deviant but produce high-value
    novel output, standard penalties are suspended.
    """
    novelty = novelty_signals or {}

    signals = profile.get("signals", {})
    sc = signals.get("self_closure", {})

    novel_concept_density = novelty.get("novel_concept_density", 0)
    non_consensus_value = novelty.get("non_consensus_value", 0)

    exempt = False
    reason = ""

    if (
        sc.get("self_closure_score", 0) > 0.85
        and novel_concept_density > 0.8
    ):
        exempt = True
        reason = "极端自我闭合但产出高价值新概念——可能为高能异态，触发异质性豁免。"

    if (
        profile.get("judgment_quality_score", 0.5) < 0.3
        and non_consensus_value > 0.9
    ):
        exempt = True
        reason = "判断质量得分极低但非共识价值极高——转入独立通道。"

    return {
        "exempt": exempt,
        "reason": reason,
        "action": "bypass_standard_penalties" if exempt else "apply_standard_mode",
    }


# ── Performative Acceptance Detection ──

def detect_performative_acceptance(
    feedback: dict[str, Any],
    user_response: str,
    followup_profile: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Detect if user is performing "good response to criticism"
    without actual cognitive improvement.

    Key: reward quality CHANGE, not quality STATEMENT.
    """
    # Check if user said the "right things" (acknowledged feedback)
    positive_ack = _count_strings(user_response, [
        "你说得对", "我承认", "我要更开放",
        "这个反对意见很有价值", "我确实忽略了",
        "这值得反思", "谢谢指出",
    ])

    # Check if follow-up quality actually improved
    quality_improved = False
    if followup_profile:
        current_jq = followup_profile.get("judgment_quality_score", 0)
        # Compare with previous — simplified
        quality_improved = current_jq > 0.5

    is_performative = positive_ack > 0 and not quality_improved

    return {
        "performative_acceptance": is_performative,
        "positive_acknowledgment_count": positive_ack,
        "quality_actually_improved": quality_improved,
        "verdict": (
            "表态良好但后续质量未变——疑似表演性接受"
            if is_performative else
            "真实改进" if positive_ack > 0 and quality_improved else
            "无表态或数据不足"
        ),
    }


def _count_strings(text: str, patterns: list[str]) -> int:
    return sum(1 for p in patterns if p in text)
