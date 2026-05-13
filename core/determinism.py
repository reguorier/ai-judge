#!/usr/bin/env python3
"""Determinism Engine v3.1 — L1/L2 consistency, confidence lights, human tax, hard truth trigger.

AI Judge V3 core module. Implements:
  - L1: 3-sample strict consistency check (temperature=0, JSON Schema, seed=fixed)
  - L2: Multi-model jury with weighted median + 4-tier disagreement protocol
  - Confidence: 3-tier lights (稳/悬/猜) replacing raw probability numbers
  - Human Tax: mandatory 20-char human_final_reason before PDF export
  - V3: hard_truth mode determination from neuro-cognitive profile

Adopted from: DeepSeek 三重协议 + Kimi 四维置信度 + 豆包 MVP + Meta 取舍声明
"""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass, field
from typing import Any, Optional


# ── L1: Repeat Determinism (同一输入多次评审一致) ──

@dataclass
class L1ConsistencyResult:
    """Result of L1 consistency check with 3-sample strict match."""
    status: str  # "PASS" | "UNSTABLE"
    consensus_result: Optional[dict[str, Any]] = None
    all_samples: list[dict[str, Any]] = field(default_factory=list)
    match_rate: float = 0.0
    message: str = ""


def l1_consistency_check(
    results: list[dict[str, Any]],
    *,
    required_matches: int = 3,
    total_samples: int = 3,
    strict_mode: bool = True,
) -> L1ConsistencyResult:
    """Check L1 repeat determinism across multiple judge runs.

    In MVP strict mode: 3 samples, all 3 must produce the exact same score
    for the result to pass. If any sample differs, result is UNSTABLE.

    Args:
        results: List of judge result dicts, each containing at minimum {'score': float}
        required_matches: How many samples must match (default 3 = all must match)
        total_samples: Total samples taken (default 3)
        strict_mode: If True, compare JSON string-level; if False, compare score +- 0.1

    Returns:
        L1ConsistencyResult with status and message
    """
    if len(results) < 2:
        return L1ConsistencyResult(
            status="INSUFFICIENT_DATA",
            message="Need at least 2 samples for consistency check.",
        )

    scores = [r.get("score", r.get("value", 0)) for r in results]

    if strict_mode:
        # String-level: compare JSON serialization of full result
        serialized = [json.dumps(r, sort_keys=True, default=str) for r in results]
        matches = sum(1 for s in serialized if s == serialized[0])
    else:
        # Score-level: compare within 0.1 tolerance
        base = scores[0]
        matches = sum(1 for s in scores if abs(s - base) < 0.1)

    match_rate = matches / len(results)

    if matches >= required_matches:
        return L1ConsistencyResult(
            status="PASS",
            consensus_result=results[0],
            all_samples=results,
            match_rate=match_rate,
            message=f"L1 PASS: {matches}/{len(results)} samples agree ({match_rate:.0%}).",
        )
    else:
        return L1ConsistencyResult(
            status="UNSTABLE",
            all_samples=results,
            match_rate=match_rate,
            message=(
                f"L1 UNSTABLE: only {matches}/{len(results)} samples agree ({match_rate:.0%}). "
                f"Scores: {scores}. 建议换个问法后重试。"
            ),
        )


def generate_deterministic_seed(input_text: str, run_index: int = 0) -> int:
    """Generate a fixed seed from input text hash to ensure reproducibility."""
    hash_bytes = hashlib.sha256(f"{input_text}:{run_index}".encode()).digest()
    return int.from_bytes(hash_bytes[:4], "big")


# ── L2: Cross-Model Determinism ──

@dataclass
class L2JuryResult:
    """Result of L2 cross-model jury consensus."""
    weighted_median_score: float
    individual_scores: dict[str, float]
    disagreement_level: str  # "mild" | "moderate" | "severe" | "systematic"
    max_gap: float
    action: str  # "accept" | "show_both_sides" | "debate_protocol" | "human_review"
    message: str


# 4-tier disagreement thresholds (10-point scale)
DISAGREEMENT_TIERS = [
    ("mild", 0.5, 1.5, "accept"),
    ("moderate", 1.5, 2.5, "show_both_sides"),
    ("severe", 2.5, 4.0, "debate_protocol"),
    ("systematic", 4.0, float("inf"), "human_review"),
]


def l2_cross_model_consensus(
    model_scores: dict[str, float],
    *,
    model_weights: Optional[dict[str, float]] = None,
) -> L2JuryResult:
    """Compute cross-model consensus with weighted median and 4-tier disagreement.

    Args:
        model_scores: Dict mapping model_name -> score (0-10)
        model_weights: Dict mapping model_name -> weight (sums to 1.0).
                       If None, equal weights.

    Returns:
        L2JuryResult with consensus score and disagreement handling.
    """
    if len(model_scores) < 2:
        return L2JuryResult(
            weighted_median_score=list(model_scores.values())[0] if model_scores else 0,
            individual_scores=model_scores,
            disagreement_level="insufficient_data",
            max_gap=0.0,
            action="accept",
            message="Need at least 2 models for cross-model consensus.",
        )

    models = list(model_scores.keys())
    scores = list(model_scores.values())

    # Default equal weights
    if model_weights is None:
        model_weights = {m: 1.0 / len(models) for m in models}

    # Weighted median
    weighted_median = _weighted_median(scores, [model_weights[m] for m in models])

    # Max gap between any two models
    max_gap = max(scores) - min(scores)

    # Determine disagreement tier
    tier = "mild"
    action = "accept"
    for name, low, high, act in DISAGREEMENT_TIERS:
        if low <= max_gap < high:
            tier = name
            action = act
            break

    # Generate message
    action_messages = {
        "accept": f"跨模型一致性良好 (分歧度 {max_gap:.1f}/10)，取加权中位数 {weighted_median:.1f}。",
        "show_both_sides": f"模型间存在中等分歧 ({max_gap:.1f}/10)。展示各模型立场供你判断。",
        "debate_protocol": f"模型间存在重度分歧 ({max_gap:.1f}/10)。启动辩论协议：低分模型说明缺陷，高分模型回应。",
        "human_review": f"模型间存在系统性分歧 ({max_gap:.1f}/10)。降级为人工复核。",
    }

    return L2JuryResult(
        weighted_median_score=round(weighted_median, 2),
        individual_scores=model_scores,
        disagreement_level=tier,
        max_gap=round(max_gap, 2),
        action=action,
        message=action_messages.get(action, ""),
    )


def _weighted_median(values: list[float], weights: list[float]) -> float:
    """Compute weighted median."""
    pairs = sorted(zip(values, weights))
    total_weight = sum(weights)
    cumulative = 0.0
    for v, w in pairs:
        cumulative += w
        if cumulative >= total_weight / 2:
            return v
    return pairs[-1][0]


# ── Confidence Lights: 三档灯 ──

@dataclass
class ConfidenceLight:
    """3-tier confidence representation replacing raw probability numbers."""
    level: str  # "steady" | "uncertain" | "guess"
    emoji: str  # "🟢" | "🟡" | "🔴"
    label_cn: str  # "稳" | "悬" | "猜"
    numerical_range: str  # e.g., ">90%" | "60-90%" | "<60%"
    certain_judgments: list[str] = field(default_factory=list)
    uncertain_judgments: list[dict[str, str]] = field(default_factory=list)
    ai_blind_spots: list[str] = field(default_factory=list)


def compute_confidence_light(
    l1_result: L1ConsistencyResult,
    l2_result: Optional[L2JuryResult] = None,
    *,
    human_alignment: float = 0.8,
    domain_coverage: float = 0.8,
) -> ConfidenceLight:
    """Compute 3-tier confidence light from L1, L2, human alignment, and domain coverage.

    Combines:
      - L1 repeatability (weight 0.35)
      - L2 cross-model agreement (weight 0.35)
      - Human alignment (weight 0.15)
      - Domain coverage (weight 0.15)

    Outputs one of three lights: 稳 (steady), 悬 (uncertain), 猜 (guess).
    """
    # L1 contribution
    l1_score = l1_result.match_rate if l1_result.match_rate > 0 else 0.5

    # L2 contribution
    l2_score = 1.0
    if l2_result:
        tier_map = {"mild": 0.95, "moderate": 0.75, "severe": 0.50, "systematic": 0.30}
        l2_score = tier_map.get(l2_result.disagreement_level, 0.5)

    combined = (
        0.35 * l1_score
        + 0.35 * l2_score
        + 0.15 * human_alignment
        + 0.15 * domain_coverage
    )

    # Cap at 0.95 per "95% hard cap" design principle
    combined = min(combined, 0.95)

    if combined >= 0.85:
        level = "steady"
        emoji = "🟢"
        label = "稳"
        num_range = ">85%"
    elif combined >= 0.60:
        level = "uncertain"
        emoji = "🟡"
        label = "悬"
        num_range = "60-85%"
    else:
        level = "guess"
        emoji = "🔴"
        label = "猜"
        num_range = "<60%"

    # Populate certain/uncertain judgments
    certain = []
    uncertain = []

    if l1_result.match_rate >= 1.0:
        certain.append(f"评分重复一致性 {l1_result.match_rate:.0%}")
    elif l1_result.match_rate > 0:
        uncertain.append({
            "dimension": "评分重复性",
            "reason": f"多次采样存在差异，一致率 {l1_result.match_rate:.0%}",
        })

    if l2_result and l2_result.disagreement_level in ("mild",):
        certain.append(f"跨模型一致性良好 (分歧 {l2_result.max_gap:.1f})")
    elif l2_result:
        uncertain.append({
            "dimension": "跨模型一致性",
            "reason": f"模型间存在 {l2_result.disagreement_level} 分歧 (极差 {l2_result.max_gap:.1f})",
        })

    # AI Blind Spots (mandatory)
    blind_spots = [
        "我无法评估组织/政治可行性",
        "我的训练数据可能过时（截止日期前）",
        "创造性维度判断具有内在主观性",
    ]

    return ConfidenceLight(
        level=level,
        emoji=emoji,
        label_cn=label,
        numerical_range=num_range,
        certain_judgments=certain,
        uncertain_judgments=uncertain,
        ai_blind_spots=blind_spots,
    )


# ── Human Tax: 人肉税 ──

@dataclass
class HumanTaxResult:
    """Human tax verification for verdict signature."""
    passed: bool
    reason: str
    human_input: str = ""
    perfunctory_count: int = 0  # Consecutive perfunctory signatures


PERFUNCTORY_PATTERNS = [
    "同意", "没问题", "ok", "好的", "可以", "行",
    "无异议", "没有", "没问题", "好", "嗯",
]


def enforce_human_tax(
    human_reason: str,
    *,
    min_chars: int = 20,
    perfunctory_history: list[str] = None,
) -> HumanTaxResult:
    """Enforce human tax: must write >= 20 chars of substantive reason.

    Detects perfunctory (敷衍) signatures like "同意" or "没问题".
    After 3 consecutive perfunctory, triggers cognitive offload alert.

    Args:
        human_reason: User-provided reason text
        min_chars: Minimum characters required (default 20)
        perfunctory_history: Previous perfunctory detection results

    Returns:
        HumanTaxResult with pass/fail and alert level
    """
    perfunctory_history = perfunctory_history or []

    stripped = human_reason.strip()

    # Check minimum length
    if len(stripped) < min_chars:
        return HumanTaxResult(
            passed=False,
            reason=f"理由至少需要 {min_chars} 字。您当前输入了 {len(stripped)} 字。请展开您的判断。",
            human_input=stripped,
        )

    # Check for perfunctory content
    is_perfunctory = any(
        stripped.lower().startswith(p) and len(stripped) < 10
        for p in PERFUNCTORY_PATTERNS
    )

    if is_perfunctory:
        perfunctory_count = sum(1 for h in perfunctory_history if h) + 1
        alert = ""
        if perfunctory_count >= 3:
            alert = (
                "\n⚠️ 认知外包警报：您已连续 3 次敷衍签字。"
                "接下来 5 次评审需要先给出您的自评才能查看 AI 结果。"
            )

        return HumanTaxResult(
            passed=True,  # Still allow, but track
            reason=f"已记录。{alert}" if alert else "已记录。",
            human_input=stripped,
            perfunctory_count=perfunctory_count,
        )

    return HumanTaxResult(
        passed=True,
        reason="签字有效。您的判断已被记录并纳入成长分析。",
        human_input=stripped,
        perfunctory_count=0,  # Reset on genuine input
    )


# ── Full Determinism Pipeline ──

def run_determinism_pipeline(
    judge_samples: list[dict[str, Any]],
    *,
    model_scores: Optional[dict[str, float]] = None,
    model_weights: Optional[dict[str, float]] = None,
    human_reason: str = "",
    human_alignment: float = 0.8,
    domain_coverage: float = 0.8,
) -> dict[str, Any]:
    """Run the complete determinism pipeline: L1 → L2 → Confidence → Human Tax.

    This is the single entry point for the Phase 1 determinism engine.
    Call this after collecting 3 judge samples.

    Returns a comprehensive determinism report.
    """
    # Step 1: L1 Consistency
    l1 = l1_consistency_check(judge_samples, required_matches=3, total_samples=3)

    # Step 2: L2 Cross-Model (if multiple model scores available)
    l2 = None
    if model_scores and len(model_scores) >= 2:
        l2 = l2_cross_model_consensus(model_scores, model_weights=model_weights)

    # Step 3: Confidence Light
    light = compute_confidence_light(
        l1,
        l2,
        human_alignment=human_alignment,
        domain_coverage=domain_coverage,
    )

    # Step 4: Human Tax
    tax = enforce_human_tax(human_reason) if human_reason else None

    return {
        "determinism_version": "2.0.0",
        "l1_consistency": {
            "status": l1.status,
            "match_rate": l1.match_rate,
            "message": l1.message,
        },
        "l2_cross_model": {
            "status": l2.disagreement_level if l2 else "not_computed",
            "weighted_median": l2.weighted_median_score if l2 else None,
            "max_gap": l2.max_gap if l2 else None,
            "action": l2.action if l2 else None,
            "message": l2.message if l2 else "",
        } if l2 else None,
        "confidence_light": {
            "level": light.level,
            "emoji": light.emoji,
            "label": light.label_cn,
            "range": light.numerical_range,
            "certain": light.certain_judgments,
            "uncertain": light.uncertain_judgments,
            "ai_blind_spots": light.ai_blind_spots,
        },
        "human_tax": {
            "passed": tax.passed if tax else False,
            "reason": tax.reason if tax else "未提交签字",
            "perfunctory_count": tax.perfunctory_count if tax else 0,
        },
        "verdict_exportable": (
            l1.status == "PASS"
            and (tax.passed if tax else False)
            and light.level in ("steady", "uncertain")
        ),
    }


def run_full_v3_pipeline(
    judge_samples: list[dict[str, Any]],
    *,
    model_scores: Optional[dict[str, float]] = None,
    model_weights: Optional[dict[str, float]] = None,
    human_reason: str = "",
    human_alignment: float = 0.8,
    domain_coverage: float = 0.8,
    neuro_profile: Optional[dict[str, Any]] = None,
    session_history: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """V3 Full Pipeline: Determinism + Neuro Profile + Hard Truth mode.

    This is the complete V3 pipeline replacing run_determinism_pipeline.
    Adds cognitive risk detection and hard_truth mode determination.
    """
    # V2 pipeline
    v2_report = run_determinism_pipeline(
        judge_samples=judge_samples,
        model_scores=model_scores,
        model_weights=model_weights,
        human_reason=human_reason,
        human_alignment=human_alignment,
        domain_coverage=domain_coverage,
    )

    # V3 additions
    v3_additions = {}

    if neuro_profile:
        from core.hard_truth import determine_mode, check_heterogeneity_exemption

        mode = determine_mode(neuro_profile, session_history)
        exemption = check_heterogeneity_exemption(neuro_profile)

        v3_additions = {
            "v3_neuro_profile": neuro_profile,
            "dual_scores": {
                "smart_sounding": neuro_profile.get("smart_sounding_score"),
                "judgment_quality": neuro_profile.get("judgment_quality_score"),
                "gap": neuro_profile.get("smart_vs_judgment_gap"),
                "gap_label": neuro_profile.get("gap_label"),
            },
            "cognitive_risk_flags": neuro_profile.get("cognitive_risk_flags", []),
            "hard_truth_mode": {
                "level": mode["mode_level"],
                "name": mode["mode_name"],
                "active": mode["hard_truth_active"],
                "trigger_reason": mode["trigger_reason"],
            },
            "heterogeneity_exemption": exemption,
        }

    v2_report.update(v3_additions)
    v2_report["pipeline_version"] = "3.1.0"
    return v2_report
