#!/usr/bin/env python3
"""Neuro Profiler v3.0 — Neural cognitive signal extraction from text.

AI Judge V3 core module. Extracts 4 cognitive proxy signals from text:
  1. detect_self_closure()       — "自我视角闭环" (DMN proxy)
  2. detect_ambiguity_flexibility() — "模糊性处理能力" (ACC proxy)
  3. detect_recovery_after_negative() — "反馈恢复模式" (Vagal proxy)
  4. detect_experience_grounding() — "经验锚定度" (Semantic vs Procedural)

IMPORTANT: These are TEXTUAL PROXY SIGNALS, not neuroscientific diagnoses.
User-facing labels never use brain-region names (DMN, ACC, Vagal).
"""

from __future__ import annotations

import re
from typing import Any, Optional


def _sigmoid(x: float) -> float:
    import math
    return 1.0 / (1.0 + math.exp(-max(-10, min(10, x))))


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _tokenize(text: str) -> list[str]:
    return re.findall(r'[一-鿿]+|[a-zA-Z]+|\d+', text)


def _count_patterns(text: str, patterns: list[str]) -> int:
    return sum(text.count(p) for p in patterns)


# ── Signal 1: Self-Reference Closure (自我视角闭环) ──

def detect_self_closure(
    text: str,
    task_context: str = "general",
) -> dict[str, Any]:
    """Detect self-reference closure in text.

    Not counting "I" words — analyzing whether "I" dominates
    at points where perspective switching is needed.
    """
    clauses = re.split(r'[。！？；\n]', text)
    clauses = [c.strip() for c in clauses if c.strip()]
    tokens = _tokenize(text)
    token_count = len(tokens)

    # Self-reference clauses
    self_markers = ["我", "我的", "我们"]
    self_clauses = [c for c in clauses if any(m in c for m in self_markers)]

    # Other-agent mentions
    other_markers = ["用户", "客户", "对手", "竞品", "监管", "团队",
                     "他们", "对方", "第三方", "市场", "行业"]
    other_clauses = [c for c in clauses if any(m in c for m in other_markers)]

    # Context classification for each self-clause
    context_weights = {
        "neutral_opinion": 0.0,      # "我认为"
        "experience_grounded": -0.2,  # "我的经验是"
        "closure_signal": 0.7,        # "我一直觉得"
        "status_defense": 0.8,        # "你没理解我"
        "perspective_take": -0.6,     # "如果我是用户"
    }

    context_scores = []
    for clause in self_clauses[:20]:  # Cap at 20 for performance
        ctx = "neutral_opinion"
        if any(p in clause for p in ["我一直", "我从来", "我早就", "我就是"]):
            ctx = "closure_signal"
        elif any(p in clause for p in ["我的经验", "我做过", "我遇到过", "我上次"]):
            ctx = "experience_grounded"
        elif any(p in clause for p in ["你没理解", "你不懂", "我早就知道", "我已经说过"]):
            ctx = "status_defense"
        elif any(p in clause for p in ["如果我是", "站在.*角度", "从.*视角"]):
            ctx = "perspective_take"
        context_scores.append(context_weights.get(ctx, 0))

    # Closure markers (non-self words that signal closed thinking)
    closure_markers = _count_patterns(text, [
        "不用说", "肯定是", "本来就", "显然", "毫无疑问",
        "没必要讨论", "一定", "绝对"
    ])

    # Missed perspective slots
    required_perspectives = {
        "strategy": ["对手", "市场", "用户", "风险"],
        "product": ["用户", "技术", "竞品", "监管"],
        "general": ["对立面", "第三方", "数据"],
    }
    required = required_perspectives.get(task_context, required_perspectives["general"])
    filled = sum(1 for r in required if r in text)
    missed = max(0, len(required) - filled)

    avg_context = _mean(context_scores) if context_scores else 0.0
    other_ratio = len(other_clauses) / max(1, len(clauses))

    score = _sigmoid(
        avg_context
        + 0.18 * missed
        + 0.12 * min(closure_markers, 10)
        - 0.15 * other_ratio * 10
    )

    return {
        "self_closure_score": round(score, 4),
        "label": "high_self_closure" if score > 0.6 else "low_self_closure" if score < 0.3 else "moderate",
        "missed_perspective_slots": missed,
        "closure_markers": closure_markers,
        "other_agent_ratio": round(other_ratio, 4),
        "risk_flag": "self_reference_closure" if score > 0.6 else None,
    }


# ── Signal 2: Ambiguity Flexibility (模糊性处理能力) ──

def detect_ambiguity_flexibility(
    text: str,
    conflict_context: Optional[dict] = None,
) -> dict[str, Any]:
    """Detect how the user handles ambiguity and contradiction.

    This is the single most valuable V3 signal.
    If conflict_context is provided (a hard-coded dilemma),
    classification is more precise.
    """
    # Contradiction markers (facing complexity)
    contradiction = _count_patterns(text, [
        "但是", "然而", "另一方面", "矛盾", "冲突",
        "不确定", "反过来", "如果", "取决于"
    ])

    # Closure markers (avoiding complexity)
    closure = _count_patterns(text, [
        "肯定", "一定", "毫无疑问", "不用讨论",
        "本质上就是", "只能", "绝对"
    ])

    # Synthesis markers (integrating complexity)
    synthesis = _count_patterns(text, [
        "可以同时成立", "取决于", "边界是", "在什么条件下",
        "分别适用于", "需要区分", "在某些情况下"
    ])

    # "I don't know" follow-up quality — the most diagnostic
    unknown_triggers = ["我不知道", "不确定", "还不能判断", "还不清楚"]
    exploration_after = 0
    negative_after = 0
    for trigger in unknown_triggers:
        idx = text.find(trigger)
        if idx >= 0:
            after = text[idx + len(trigger):idx + len(trigger) + 80]
            if any(p in after for p in ["需要验证", "下一步", "数据", "实验", "拆成", "假设", "试试"]):
                exploration_after += 1
            if any(p in after for p in ["所以算了", "那就", "没办法"]):
                negative_after += 1

    exploration_quality = (exploration_after - negative_after) / max(1, exploration_after + negative_after + 1)

    # If conflict context provided, classify response type
    response_type = None
    if conflict_context:
        if _count_patterns(text, ["只能", "一定", "肯定", "绝对"]) > closure:
            response_type = "choose_side"
        elif _count_patterns(text, ["综合", "融合", "同时成立", "取决于"]) > 0:
            response_type = "synthesize"
        elif _count_patterns(text, ["需要验证", "不确定", "证据", "数据"]) > 0:
            response_type = "suspend_explore"
        else:
            response_type = "ambiguous"

    score = _sigmoid(
        0.25 * min(contradiction, 15)
        + 0.45 * min(synthesis, 10)
        + 0.55 * exploration_quality * 5
        - 0.50 * min(closure, 10)
    )

    if score < 0.35:
        label = "low_flexibility_choose_side"
    elif score < 0.70:
        label = "medium_flexibility_synthesis"
    else:
        label = "high_flexibility_suspend_and_probe"

    return {
        "ambiguity_flexibility_score": round(score, 4),
        "label": label,
        "response_type": response_type,
        "unknown_followup_quality": round(exploration_quality, 4),
        "contradiction_markers": contradiction,
        "closure_markers": closure,
        "synthesis_markers": synthesis,
        "risk_flag": "low_ambiguity_tolerance" if score < 0.35 else None,
    }


# ── Signal 3: Recovery After Negative Feedback (反馈恢复模式) ──

def detect_recovery_after_negative(
    immediate_response: str,
    pre_quality_score: float,
    post_quality_scores: list[float],
) -> dict[str, Any]:
    """Detect recovery pattern after negative feedback.

    Requires cross-session data — cannot reliably detect from single text.
    pre_quality = judgment quality before the negative feedback.
    post_quality_scores = judgment quality scores from 1-3 sessions after.
    """
    if not immediate_response:
        return {"label": "insufficient_data", "recovery_score": 0.5}

    # Defensive markers
    defense = _count_patterns(immediate_response, [
        "你没理解", "不是这个意思", "你错了",
        "我早就", "我已经说过", "这不成立",
    ])

    # Exploratory markers
    explore = _count_patterns(immediate_response, [
        "哪一点", "为什么", "重写", "换个角度",
        "试试", "反证", "如果你是对的",
        "证据", "需要验证", "让我想想",
    ])

    # Quality delta
    post_quality = _mean(post_quality_scores) if post_quality_scores else pre_quality_score
    quality_delta = post_quality - pre_quality_score

    # Defensive ratio
    total = defense + explore + 1
    defense_ratio = defense / total
    explore_ratio = explore / total

    recovery = _sigmoid(
        -0.6 * defense_ratio * 10
        + 0.5 * explore_ratio * 10
        + 0.8 * quality_delta * 5
    )

    if recovery < 0.3:
        label = "defensive_collapse"
    elif recovery < 0.6:
        label = "surface_acceptance"
    else:
        label = "exploratory_repair"

    return {
        "recovery_score": round(recovery, 4),
        "label": label,
        "quality_delta": round(quality_delta, 4),
        "defensiveness_ratio": round(defense_ratio, 4),
        "exploration_ratio": round(explore_ratio, 4),
        "risk_flag": "defensive_recovery_pattern" if recovery < 0.3 else None,
    }


# ── Signal 4: Experience Grounding (经验锚定度) ──

def detect_experience_grounding(text: str) -> dict[str, Any]:
    """Distinguish concept-driven (semantic memory) from experience-driven
    (procedural memory) language.

    User-facing: "经验锚定度"
    """
    tokens = _tokenize(text)
    n = max(1, len(tokens))

    # Procedural features
    action_verbs = _count_patterns(text, [
        "做了", "试了", "改了", "跑了", "测了", "写了",
        "上线", "发布", "部署", "回滚", "修了"
    ])
    sensory_words = _count_patterns(text, [
        "看到", "听到", "感觉到", "发现", "注意到",
    ])
    specific_entities = _count_patterns(text, [
        "上周", "昨天", "3月", "202", "第.*次", "客户说",
        "数据显示", "日志", "截图", "报错",
    ])
    failure_details = _count_patterns(text, [
        "失败", "错了", "卡在", "挂了", "失误", "踩坑",
        "后来发现", "当时以为", "结果并不是",
    ])
    correction_markers = _count_patterns(text, [
        "后来发现", "当时", "改了三次", "实际做的时候",
        "用户没点", "数据不支持", "我以为但",
    ])

    # Semantic features (penalty)
    abstract_nouns = _count_patterns(text, [
        "认知", "架构", "范式", "底层逻辑", "闭环",
        "赋能", "颗粒度", "护城河", "飞轮", "网络效应",
        "系统", "框架", "模型", "方法论",
    ])

    grounding = _sigmoid(
        0.35 * min(action_verbs / n * 100, 10)
        + 0.25 * min(sensory_words / n * 100, 10)
        + 0.30 * min(specific_entities / n * 100, 10)
        + 0.40 * min(failure_details, 5)
        + 0.30 * min(correction_markers, 5)
        - 0.25 * min(abstract_nouns / n * 100, 10)
    )

    if grounding < 0.3:
        label = "concept_driven"
    elif grounding < 0.6:
        label = "mixed"
    else:
        label = "experience_grounded"

    return {
        "experience_grounding_score": round(grounding, 4),
        "label": label,
        "semantic_fluency_risk": round(1 - grounding, 4),
        "action_verb_count": action_verbs,
        "failure_detail_count": failure_details,
        "abstract_noun_ratio": round(abstract_nouns / n, 4),
        "risk_flag": "conceptual_fluency_without_grounding" if grounding < 0.3 else None,
    }


# ── Full Neuro Profile ──

def compute_neuro_profile(
    text: str,
    task_context: str = "general",
    conflict_context: Optional[dict] = None,
    recovery_data: Optional[dict] = None,
) -> dict[str, Any]:
    """Compute the full neuro-cognitive profile for a text.

    Returns all 4 signals plus composite smart_sounding and judgment_quality scores.
    """
    # Signal 1: Self Closure
    self_closure = detect_self_closure(text, task_context)

    # Signal 2: Ambiguity Flexibility
    ambiguity = detect_ambiguity_flexibility(text, conflict_context)

    # Signal 3: Recovery (skip if no cross-session data)
    recovery = None
    if recovery_data:
        recovery = detect_recovery_after_negative(
            recovery_data.get("immediate_response", ""),
            recovery_data.get("pre_quality", 0.5),
            recovery_data.get("post_qualities", []),
        )

    # Signal 4: Experience Grounding
    grounding = detect_experience_grounding(text)

    # ── Compute dual scores ──
    # smart_sounding: how confident/fluent/structured it sounds (NOT how good it is)
    # High self-closure, low grounding, high closure-markers → sounds smart
    transition_words = _count_patterns(text, ["因此", "所以", "首先", "综上", "第一", "总之"])
    transition_density = transition_words / max(1, len(_tokenize(text))) * 100

    smart_sounding = _sigmoid(
        +0.4 * self_closure.get("self_closure_score", 0.5) * 4   # Confident self-reference sounds smart
        + 0.2 * transition_density * 0.5                         # Structured transitions
        + 0.4 * grounding.get("semantic_fluency_risk", 0.5) * 4  # Abstract = sounds smart
    )

    # judgment_quality: how reliable the actual thinking is
    # Low self-closure, high ambiguity tolerance, high grounding → good judgment
    judgment_quality = _sigmoid(
        +0.30 * (1 - self_closure.get("self_closure_score", 0.5)) * 4
        + 0.35 * ambiguity.get("ambiguity_flexibility_score", 0.5) * 5
        + 0.25 * grounding.get("experience_grounding_score", 0.5) * 4
        + 0.10 * (recovery.get("recovery_score", 0.5) * 3 if recovery else 1.5)
    )

    # Cognitive risk flags
    risk_flags = []
    if s := self_closure.get("risk_flag"):
        risk_flags.append(s)
    if a := ambiguity.get("risk_flag"):
        risk_flags.append(a)
    if recovery and (r := recovery.get("risk_flag")):
        risk_flags.append(r)
    if g := grounding.get("risk_flag"):
        risk_flags.append(g)

    # Gap: big gap between sounding smart and actually being smart
    gap = smart_sounding - judgment_quality
    gap_label = "normal"
    if gap > 0.30:
        gap_label = "sounds_smarter_than_is"
    elif gap < -0.10:
        gap_label = "judgment_exceeds_expression"

    return {
        "profile_version": "3.0.0",
        "smart_sounding_score": round(smart_sounding, 4),
        "judgment_quality_score": round(judgment_quality, 4),
        "smart_vs_judgment_gap": round(gap, 4),
        "gap_label": gap_label,
        "cognitive_risk_flags": risk_flags,
        "signals": {
            "self_closure": self_closure,
            "ambiguity_flexibility": ambiguity,
            "recovery_after_negative": recovery,
            "experience_grounding": grounding,
        },
    }
