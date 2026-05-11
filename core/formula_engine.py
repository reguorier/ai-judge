#!/usr/bin/env python3
"""Formula Engine v2.0 — Executable scoring functions for AI Judge Phase 1.

Adapted from Agent Graph Arena v0.7 formula_engine.py.
All functions are standalone, auditable, and return structured results.
"""

from __future__ import annotations

import math
from typing import Any


def _clamp(value: float, *, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


# ── Phase 1 Core Functions ──

def log_score(*, probability: float, outcome: bool) -> dict[str, Any]:
    """Negative log loss. Lower is better. Penalizes overconfidence exponentially.

    A prediction of 0.99 that turns out wrong costs ~4.6. A prediction of 0.6
    that turns out wrong costs ~0.9. This is the replacement for the old
    discrete lookup table that treated all confidences equally.
    """
    probability = _clamp(probability, lower=1e-9, upper=1.0 - 1e-9)
    selected = probability if outcome else 1.0 - probability
    value = -math.log(selected)
    risk_flags = []
    if value > 1.5:
        risk_flags.append("overconfident_miss")
    if value < 0.1:
        risk_flags.append("well_calibrated")
    return {
        "name": "log_score",
        "value": round(value, 6),
        "probability": round(probability, 6),
        "outcome": outcome,
        "risk_flags": risk_flags,
        "explanation": "LogScore = -ln(P(actual_outcome)). Penalty grows exponentially as confidence diverges from reality.",
    }


def allocation_score(
    *,
    source_authority: float,
    evidence_strength: float,
    freshness: float,
    reproducibility: float,
    historical_reliability: float,
    risk_penalty: float = 0.0,
) -> dict[str, Any]:
    """Weighted-sum scoring that replaces the old multiplicative approach.

    The old formula multiplied all factors: a single 0.1 killed the entire
    score. This weighted sum preserves nuance — a claim with high authority
    but stale data keeps partial credit instead of being zeroed out.

    Weights: source 25%, evidence 30%, freshness 15%, reproducibility 15%, history 15%.
    """
    sa = _clamp(source_authority)
    es = _clamp(evidence_strength)
    fr = _clamp(freshness)
    rp = _clamp(reproducibility)
    hr = _clamp(historical_reliability)
    rp_pen = _clamp(risk_penalty)

    value = 0.25 * sa + 0.30 * es + 0.15 * fr + 0.15 * rp + 0.15 * hr - rp_pen
    value = _clamp(value)

    tier = "rejected"
    if value >= 0.75:
        tier = "credible"
    elif value >= 0.50:
        tier = "conditional"
    elif value >= 0.30:
        tier = "unverified"

    return {
        "name": "allocation_score",
        "value": round(value, 6),
        "tier": tier,
        "components": {
            "source_authority": round(sa, 4),
            "evidence_strength": round(es, 4),
            "freshness": round(fr, 4),
            "reproducibility": round(rp, 4),
            "historical_reliability": round(hr, 4),
            "risk_penalty": round(rp_pen, 4),
        },
        "risk_flags": ["low_allocation_quality"] if value < 0.45 else [],
        "explanation": (
            "Allocation = .25×authority + .30×evidence + .15×freshness "
            "+ .15×reproducibility + .15×history - risk_penalty. "
            "Preserves nuance unlike multiplicative scoring."
        ),
    }


def evaluate_bluff_ev(
    *,
    confidence: float,
    evidence_count: int,
    evidence_quality: float = 0.5,
    historical_accuracy: float = 0.5,
) -> dict[str, Any]:
    """Detect high-confidence claims with insufficient evidence.

    A model stating 0.99 confidence with zero cited sources is likely bluffing.
    This function computes a bluff index: high confidence + low evidence = high bluff score.

    Returns a bluff index (0-1) and action recommendation.
    """
    confidence = _clamp(confidence)
    evidence_quality = _clamp(evidence_quality)
    historical_accuracy = _clamp(historical_accuracy)

    # Evidence sufficiency: combined from count, quality, and history
    count_factor = min(1.0, evidence_count / 3.0)  # max at 3+ sources
    evidence_sufficiency = 0.4 * count_factor + 0.4 * evidence_quality + 0.2 * historical_accuracy

    # Bluff index: high confidence but low evidence sufficiency
    bluff_index = confidence * (1.0 - evidence_sufficiency)

    action = "allow"
    if bluff_index > 0.7:
        action = "block"  # Require evidence supplement
    elif bluff_index > 0.5:
        action = "flag"   # Mark as suspected bluff, reduce merit

    risk_flags = []
    if action == "block":
        risk_flags.append("bluff_blocked_high_confidence_no_evidence")
    elif action == "flag":
        risk_flags.append("bluff_suspected")

    return {
        "name": "evaluate_bluff_ev",
        "bluff_index": round(bluff_index, 6),
        "evidence_sufficiency": round(evidence_sufficiency, 6),
        "action": action,
        "inputs": {
            "confidence": round(confidence, 4),
            "evidence_count": evidence_count,
            "evidence_quality": round(evidence_quality, 4),
            "historical_accuracy": round(historical_accuracy, 4),
        },
        "risk_flags": risk_flags,
        "explanation": (
            f"BluffIndex = confidence × (1 - evidence_sufficiency). "
            f"Action: {action}. High confidence without evidence triggers intervention."
        ),
    }


def should_bid(
    *,
    domain_match: float,
    confidence: float,
    expected_penalty: float = 0.1,
    opportunity_gain: float = 0.05,
) -> dict[str, Any]:
    """Determine whether a model should participate in a given claim.

    Models should abstain when:
    - Domain match is low (not their expertise area)
    - Confidence is low
    - Expected penalty from wrong answers exceeds potential gain

    This replaces the old "everyone must answer everything" approach.
    """
    domain_match = _clamp(domain_match)
    confidence = _clamp(confidence)
    expected_penalty = max(0.0, expected_penalty)
    opportunity_gain = max(0.0, opportunity_gain)

    # Expected value of participating
    expected_profit = domain_match * confidence - expected_penalty + opportunity_gain

    action = "abstain"  # default: don't participate
    if expected_profit > 0.2:
        action = "bid_strong"
    elif expected_profit > 0.05:
        action = "bid_cautious"

    risk_flags = []
    if action == "abstain":
        risk_flags.append("domain_or_confidence_insufficient")

    return {
        "name": "should_bid",
        "action": action,
        "expected_profit": round(expected_profit, 6),
        "inputs": {
            "domain_match": round(domain_match, 4),
            "confidence": round(confidence, 4),
            "expected_penalty": round(expected_penalty, 4),
            "opportunity_gain": round(opportunity_gain, 4),
        },
        "risk_flags": risk_flags,
        "explanation": (
            "Should_Bid when domain_match × confidence - expected_penalty + opportunity_gain > 0.2 (strong) or > 0.05 (cautious). "
            "Models should abstain when outside their expertise or unsure."
        ),
    }


# ── Registry ──

PHASE1_FUNCTIONS = [
    "log_score",
    "allocation_score",
    "evaluate_bluff_ev",
    "should_bid",
]

# ── Phase 2 Functions ──

def brier_score(*, probability: float, outcome: bool) -> dict[str, Any]:
    """Brier score — squared error between prediction and outcome."""
    probability = _clamp(probability)
    target = 1.0 if outcome else 0.0
    value = (probability - target) ** 2
    return {
        "name": "brier_score",
        "value": round(value, 6),
        "probability": round(probability, 6),
        "outcome": outcome,
        "risk_flags": ["poor_calibration"] if value > 0.25 else [],
    }


def calculate_voi(*, eu_with_info: float, eu_without_info: float, information_cost: float = 0.0) -> dict[str, Any]:
    """Value of Information — was the tool call worth it?"""
    raw_gain = eu_with_info - eu_without_info
    value = max(0.0, raw_gain - information_cost)
    return {
        "name": "voi",
        "value": round(value, 6),
        "raw_gain": round(raw_gain, 6),
        "risk_flags": [] if value > 0 else ["information_not_worth_cost"],
    }


def half_kelly_cap(*, bankroll: float, probability: float, odds: float, requested_stake: float, sample_size: int) -> dict[str, Any]:
    """Half-Kelly stake cap — dynamic upper bound on position sizing."""
    probability = _clamp(probability)
    odds = max(0.0, odds)
    bankroll = max(0.0, bankroll)
    requested_stake = max(0.0, requested_stake)
    if sample_size < 30:
        cap = bankroll * 0.05
    elif odds <= 0:
        cap = 0.0
    else:
        q = 1.0 - probability
        fraction = ((odds * probability) - q) / odds
        cap = bankroll * max(0.0, fraction) * 0.5
    return {
        "name": "half_kelly_cap",
        "allowed_stake": round(min(requested_stake, cap), 6),
        "cap": round(cap, 6),
        "requested": requested_stake,
        "trimmed": requested_stake > cap,
    }


def cheat_ev(*, p_undetected: float, gain: float, p_detected: float, slash: float, license_downgrade_loss: float) -> dict[str, Any]:
    """Cheating incentive — if positive, the system has a vulnerability."""
    value = _clamp(p_undetected) * gain - _clamp(p_detected) * slash - license_downgrade_loss
    return {
        "name": "cheat_ev",
        "value": round(value, 6),
        "vulnerable": value > 0,
        "risk_flags": ["cheat_incentive_exists"] if value > 0 else [],
    }


# ── Correctness-first graph_value (COUNCIL-003 approved formula) ──

def graph_value_v2(
    *,
    correctness: float,
    rarity_score: float = 0.0,
    replay_count: int = 0,
    demand_score: float = 0.0,
    calibration_consistency: float = 0.0,
) -> dict[str, Any]:
    """Graph Value v2.0 — correctness-first, rarity as lever only.

    COUNCIL-003 12/12 approved formula:
      value = correctness × (1 + 0.2 × rarity × I(calibration>0.7) + 0.1 × replay_norm + 0.1 × demand)

    Rarity is a multiplier, not a standalone score. Correctness is the gate.
    """
    correctness = _clamp(correctness)
    rarity = _clamp(rarity_score)
    demand = _clamp(demand_score)
    calibration = _clamp(calibration_consistency)

    # Rarity only active when calibrated
    rarity_bonus = 0.2 * rarity if calibration > 0.7 else 0.0
    replay_norm = min(1.0, replay_count / 100.0)
    replay_bonus = 0.1 * replay_norm
    demand_bonus = 0.1 * demand

    value = correctness * (1.0 + rarity_bonus + replay_bonus + demand_bonus)

    return {
        "name": "graph_value_v2",
        "value": round(value, 6),
        "correctness": round(correctness, 4),
        "rarity_bonus": round(rarity_bonus, 4),
        "replay_bonus": round(replay_bonus, 4),
        "demand_bonus": round(demand_bonus, 4),
        "calibration_gate_passed": calibration > 0.7,
        "risk_flags": ["rarity_no_calibration"] if rarity > 0 and calibration <= 0.7 else [],
        "explanation": "Correctness × (1 + rarity_bonus + replay_bonus + demand_bonus). Rarity only applies when calibration > 0.7.",
    }


# ── auc_score (dependency-free ROC AUC) ──

def auc_score(*, scores: list[float], labels: list[int]) -> dict[str, Any]:
    """ROC AUC for binary labels — measures ranking quality."""
    if not scores or len(scores) != len(labels):
        return {"name": "auc_score", "value": 0.5, "error": "invalid_input"}
    pairs = list(zip(scores, labels))
    pos = [s for s, l in pairs if l == 1]
    neg = [s for s, l in pairs if l == 0]
    if not pos or not neg:
        return {"name": "auc_score", "value": 0.5, "warning": "single_class"}
    wins = 0.0
    total = 0
    for ps in pos:
        for ns in neg:
            total += 1
            if ps > ns:
                wins += 1
            elif ps == ns:
                wins += 0.5
    return {
        "name": "auc_score",
        "value": round(wins / total, 6),
        "pairs": total,
    }


ALL_FUNCTIONS = [
    "log_score", "allocation_score", "evaluate_bluff_ev", "should_bid",
    "brier_score", "voi", "half_kelly_cap", "cheat_ev",
    "graph_value_v2", "auc_score",
]
