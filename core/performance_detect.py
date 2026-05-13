#!/usr/bin/env python3
"""Performance Detection v2.0 — Detect performative thinking via process friction.

AI Judge V2 risk protection module. Implements:
  - 5-dimension performance scoring (edit friction, terminology surge, style drift, A/B gap, perfection line)
  - Dual-track recording (A: public submission, B: private log)
  - Non-confrontational intervention (switch to curiosity mode, never accuse)
  - "Waste draft reward" mechanism — reward abandoned but interesting paths

Adopted from: DeepSeek 过程摩擦 + Meta 双轨 + 多数模型"不揭穿"共识
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PerformanceScore:
    """Result of performance detection analysis."""
    score: float  # 0-1, higher = more likely performing
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH"
    signals: dict[str, Any]
    recommended_action: str
    intervention_message: str


# ── Core Detection Functions ──

def detect_performance(
    *,
    edit_history: Optional[list[dict[str, Any]]] = None,
    formal_submissions: Optional[list[str]] = None,
    casual_logs: Optional[list[str]] = None,
    historical_style: Optional[dict[str, float]] = None,
    recent_scores: Optional[list[float]] = None,
) -> PerformanceScore:
    """5-dimension performance detection.

    Args:
        edit_history: List of edit actions with timestamps
        formal_submissions: Recent formal ("A track") submitted texts
        casual_logs: Recent casual ("B track") fragment logs
        historical_style: Baseline style metrics from user history
        recent_scores: Recent evaluation scores for linearity check
    """
    signals = {}

    # Signal 1: Edit Friction Rate (< 5% is suspicious)
    if edit_history:
        signals["edit_friction"] = _compute_edit_friction(edit_history)
    else:
        signals["edit_friction"] = {"rate": 0.15, "flag": False}

    # Signal 2: A/B Track Gap (formal vs casual complexity difference)
    if formal_submissions and casual_logs:
        signals["ab_gap"] = _compute_ab_gap(formal_submissions, casual_logs)
    else:
        signals["ab_gap"] = {"gap_ratio": 1.0, "flag": False}

    # Signal 3: Style Drift (embedding shift from baseline)
    if historical_style:
        signals["style_drift"] = _compute_style_drift(formal_submissions or [], historical_style)
    else:
        signals["style_drift"] = {"drift_score": 0.0, "flag": False}

    # Signal 4: Terminology Surge (buzzword inflation)
    if formal_submissions:
        signals["terminology_surge"] = _detect_terminology_surge(formal_submissions)
    else:
        signals["terminology_surge"] = {"surge_score": 0.0, "flag": False}

    # Signal 5: Perfection Line (too smooth, no uncertainty markers)
    if formal_submissions and recent_scores:
        signals["perfection_line"] = _detect_perfection_line(formal_submissions, recent_scores)
    else:
        signals["perfection_line"] = {"is_perfect_line": False, "flag": False}

    # Weighted aggregate
    weights = {
        "edit_friction": 0.15,
        "ab_gap": 0.30,         # Most reliable — compares private vs public
        "style_drift": 0.20,
        "terminology_surge": 0.15,
        "perfection_line": 0.20,
    }

    scores_parts = {
        "edit_friction": _flag_to_score(signals["edit_friction"].get("flag", False)),
        "ab_gap": min(1.0, signals["ab_gap"].get("gap_ratio", 1.0) - 1.0)
        if signals["ab_gap"].get("gap_ratio", 1.0) > 1.4 else 0.0,
        "style_drift": _flag_to_score(signals["style_drift"].get("flag", False)),
        "terminology_surge": signals["terminology_surge"].get("surge_score", 0.0),
        "perfection_line": _flag_to_score(signals["perfection_line"].get("flag", False)),
    }

    combined = sum(weights[k] * scores_parts[k] for k in weights)

    risk = "LOW"
    if combined > 0.7:
        risk = "HIGH"
    elif combined > 0.4:
        risk = "MEDIUM"

    action, message = _get_intervention(risk, signals)

    return PerformanceScore(
        score=round(combined, 4),
        risk_level=risk,
        signals=signals,
        recommended_action=action,
        intervention_message=message,
    )


def _flag_to_score(flag: bool) -> float:
    return 1.0 if flag else 0.0


# ── Signal Computation ──

def _compute_edit_friction(edit_history: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute edit friction rate.

    Real thinking has trial-and-error. One-shot perfection = potential performance.
    Friction < 5% is a red flag.
    """
    if not edit_history:
        return {"rate": 0.0, "flag": False}

    total_chars = sum(e.get("text_length", 0) for e in edit_history)
    edit_chars = sum(
        e.get("delete_chars", 0) + e.get("insert_chars", 0)
        for e in edit_history
    )

    rate = edit_chars / max(total_chars, 1)
    return {
        "rate": round(rate, 4),
        "flag": rate < 0.05,
        "interpretation": "编辑摩擦率极低，可能一气呵成未经历试错" if rate < 0.05 else "正常",
    }


def _compute_ab_gap(
    formal_texts: list[str],
    casual_texts: list[str],
) -> dict[str, Any]:
    """Compare A-track (formal submission) vs B-track (casual log) complexity.

    If formal is >40% more complex than casual, that's a signal.
    """
    # Simplified: use average sentence length and word diversity as proxies
    formal_complexity = _text_complexity(formal_texts)
    casual_complexity = _text_complexity(casual_texts)

    if casual_complexity == 0:
        return {"gap_ratio": 1.0, "flag": False}

    gap = formal_complexity / casual_complexity
    return {
        "gap_ratio": round(gap, 2),
        "flag": gap > 1.4,
        "formal_complexity": round(formal_complexity, 2),
        "casual_complexity": round(casual_complexity, 2),
        "interpretation": (
            f"正式提交比随手记复杂 {gap:.0%}，可能刻意优化了正式输出"
            if gap > 1.4 else "正式与随手记复杂度一致"
        ),
    }


def _text_complexity(texts: list[str]) -> float:
    """Simple text complexity proxy: avg sentence length × unique word ratio."""
    if not texts:
        return 0.0
    combined = " ".join(texts)
    words = combined.split()
    if not words:
        return 0.0
    sentences = [s for s in combined.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    avg_sent_len = len(words) / max(len(sentences), 1)
    unique_ratio = len(set(w.lower() for w in words)) / len(words)
    return avg_sent_len * unique_ratio


def _compute_style_drift(
    formal_texts: list[str],
    historical_style: dict[str, float],
) -> dict[str, Any]:
    """Check if current style has drifted significantly from historical baseline.

    Simplified: compare text length and sentence complexity against historical mean.
    """
    if not formal_texts:
        return {"drift_score": 0.0, "flag": False}

    current_complexity = _text_complexity(formal_texts)
    historical_mean = historical_style.get("avg_complexity", current_complexity)
    historical_std = historical_style.get("std_complexity", current_complexity * 0.2)

    if historical_std == 0:
        return {"drift_score": 0.0, "flag": False}

    z_score = abs(current_complexity - historical_mean) / historical_std

    return {
        "drift_score": round(z_score, 2),
        "flag": z_score > 2.0,
        "interpretation": f"风格偏离历史基线 {z_score:.1f}σ" if z_score > 2.0 else "风格稳定",
    }


def _detect_terminology_surge(formal_texts: list[str]) -> dict[str, Any]:
    """Detect if the user has started stacking buzzwords.

    High buzzword density + low unique word ratio = potential performance.
    """
    buzzwords = [
        "底层逻辑", "范式转移", "熵增", "第一性原理", "降维打击",
        "赋能", "闭环", "抓手", "对齐", "颗粒度", "护城河",
        "飞轮", "引爆点", "网络效应", "幂律分布", "涌现",
    ]

    combined = " ".join(formal_texts)
    words = combined.split()
    if not words:
        return {"surge_score": 0.0, "flag": False}

    buzzword_count = sum(1 for bw in buzzwords if bw in combined)
    density = buzzword_count / len(words)

    return {
        "surge_score": round(min(1.0, density * 20), 2),  # Normalize
        "buzzword_density": round(density, 4),
        "flag": density > 0.03,  # >3% buzzwords
    }


def _detect_perfection_line(
    formal_texts: list[str],
    recent_scores: list[float],
) -> dict[str, Any]:
    """Detect if recent outputs form a suspiciously perfect line.

    Real progress is bumpy. A perfectly linear improvement is suspicious.
    Also check if uncertainty markers have disappeared.
    """
    combined = " ".join(formal_texts)
    uncertainty_markers = ["可能", "也许", "不确定", "需要验证", "我怀疑", "?",
                           "maybe", "perhaps", "uncertain", "有待", "暂时"]
    has_uncertainty = any(m in combined.lower() for m in uncertainty_markers)

    if len(recent_scores) < 3:
        return {"is_perfect_line": False, "flag": False}

    # Check score smoothness
    score_diffs = [abs(recent_scores[i] - recent_scores[i - 1]) for i in range(1, len(recent_scores))]
    avg_diff = sum(score_diffs) / len(score_diffs)

    # Extremely smooth = all diffs within 0.3 of each other
    is_smooth = all(abs(d - score_diffs[0]) < 0.3 for d in score_diffs) if score_diffs else False

    flag = is_smooth and not has_uncertainty

    return {
        "is_perfect_line": flag,
        "flag": flag,
        "score_smoothness": round(avg_diff, 2) if score_diffs else 0,
        "has_uncertainty_markers": has_uncertainty,
        "interpretation": (
            "连续高分 + 无不确定标记 + 线性平滑 → 高表演概率"
            if flag else "正常"
        ),
    }


# ── Intervention ──

def _get_intervention(risk: str, signals: dict) -> tuple[str, str]:
    """Get the appropriate intervention for detected performance risk.

    KEY DESIGN: Never accuse. Switch mode, don't punish.
    """
    if risk == "LOW":
        return "none", ""

    if risk == "MEDIUM":
        return "switch_to_curiosity", (
            "我注意到你最近的思考非常流畅和完整。"
            "有时候最流畅的表达跳过了探索的乐趣。"
            "你有没有在写这些之前尝试过其他论证方向？"
            "如果有被放弃的想法，它们可能比最终版本更有趣。"
        )

    # HIGH risk
    ab_gap = signals.get("ab_gap", {})
    if ab_gap.get("flag"):
        return "private_reminder", (
            "你最近的正式思考比随手记严谨很多。"
            "要不要把随手记也纳入评审？真实的混乱也有价值。"
        )

    return "switch_to_curiosity", (
        "我注意到你最近几次的表现异常出色和稳定。"
        "但有时候，最有趣的东西藏在那些不完美的、被放弃的想法里。"
        "下次要不要试试提交一个'未完成版'？我保证不扣分。"
    )


# ── Waste Draft Reward ──

def evaluate_waste_draft(
    abandoned_draft: str,
    final_output: str,
) -> dict[str, Any]:
    """Evaluate the value of an abandoned draft.

    This implements the "废稿奖励" mechanism — rewarding exploration
    paths that weren't used in the final output.
    """
    # In production, this would use LLM to compare and extract value
    # For now, structural analysis
    draft_words = len(abandoned_draft.split())
    final_words = len(final_output.split())

    reward = {
        "has_value": draft_words > 20,  # Non-trivial draft
        "reward_type": "exploration_bonus",
        "note": "被放弃的探索路径也构成思考足迹的一部分",
        "added_to_footprint": True,
    }

    return reward
