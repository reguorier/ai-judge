#!/usr/bin/env python3
"""AI Judge Scoring v2.0 — Phase 1 Immediate Implementation.

Replaces:
  - Multiplicative claim scoring → allocation_score (weighted sum + risk penalty)
  - Discrete confidence lookup → log_score (continuous probability penalty)
  - No bluff detection → evaluate_bluff_ev (intercept high-confidence-no-evidence)
  - Forced participation → should_bid (allow abstain without penalty)

Usage:
  from core.scoring_v2 import score_claim_v2, score_jury_v2
"""

from __future__ import annotations

import json
from typing import Any

from core.formula_engine import (
    allocation_score,
    evaluate_bluff_ev,
    log_score,
    should_bid,
)


def score_claim_v2(
    *,
    claim: str,
    source_authority: float = 0.5,
    evidence_strength: float = 0.5,
    evidence_count: int = 0,
    evidence_quality: float = 0.5,
    freshness: float = 0.5,
    reproducibility: float = 0.5,
    historical_reliability: float = 0.5,
    confidence: float = 0.5,
    risk_penalty: float = 0.0,
    known_outcome: bool | None = None,
) -> dict[str, Any]:
    """Score a single claim using v2.0 Phase 1 formulas.

    This is the drop-in replacement for the old multiplicative `score_claim()`.
    It runs through three gates:

    1. BLUFF GATE: evaluate_bluff_ev — if confidence is high but evidence is
       missing, the claim is blocked or flagged before scoring.

    2. BID GATE: should_bid — if the model should abstain from this claim
       (low domain match or low confidence), it's flagged.

    3. SCORE GATE: allocation_score — weighted sum of five factors, replacing
       the old multiplication.

    If known_outcome is provided, log_score is computed as a calibration metric.
    """
    result: dict[str, Any] = {
        "claim": claim[:200],
        "scoring_version": "2.0.0-phase1",
    }

    # ── Gate 1: Bluff Detection ──
    bluff = evaluate_bluff_ev(
        confidence=confidence,
        evidence_count=evidence_count,
        evidence_quality=evidence_quality,
        historical_accuracy=historical_reliability,
    )
    result["bluff_gate"] = bluff

    if bluff["action"] == "block":
        result["score"] = 0.0
        result["tier"] = "rejected"
        result["blocked_by"] = "bluff_gate"
        result["explanation"] = "Claim blocked: high confidence with insufficient evidence."
        return result

    # ── Gate 2: Bid Decision ──
    bid = should_bid(
        domain_match=evidence_strength,  # proxy: stronger evidence = better domain match
        confidence=confidence,
        expected_penalty=0.1,
        opportunity_gain=0.05,
    )
    result["bid_gate"] = bid

    # ── Gate 3: Allocation Score ──
    alloc = allocation_score(
        source_authority=source_authority,
        evidence_strength=evidence_strength,
        freshness=freshness,
        reproducibility=reproducibility,
        historical_reliability=historical_reliability,
        risk_penalty=risk_penalty,
    )
    result.update({
        "score": alloc["value"],
        "tier": alloc["tier"],
        "components": alloc["components"],
        "explanation": alloc["explanation"],
    })

    # ── Calibration: log_score if outcome known ──
    if known_outcome is not None:
        ls = log_score(probability=confidence, outcome=known_outcome)
        result["log_score"] = ls

    # ── Bluff penalty: if flagged, reduce score ──
    if bluff["action"] == "flag":
        penalty = 0.7  # 30% reduction
        result["score"] = round(result["score"] * penalty, 6)
        result["bluff_penalty_applied"] = penalty

    # ── Bid flag ──
    if bid["action"] == "abstain":
        result["abstain_recommended"] = True

    return result


def score_jury_v2(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Score an entire jury run with v2.0 formulas.

    Input: list of claim dicts, each containing:
      - claim (str)
      - source_authority, evidence_strength, evidence_count, evidence_quality
      - freshness, reproducibility, historical_reliability
      - confidence, risk_penalty
      - known_outcome (optional bool)

    Output: jury-level summary with per-claim breakdown and aggregate metrics.
    """
    scored = []
    tiers = {"credible": 0, "conditional": 0, "unverified": 0, "rejected": 0}
    blocked = 0
    abstains = 0
    log_scores = []

    for c in claims:
        result = score_claim_v2(
            claim=c.get("claim", ""),
            source_authority=float(c.get("source_authority", 0.5)),
            evidence_strength=float(c.get("evidence_strength", 0.5)),
            evidence_count=int(c.get("evidence_count", 0)),
            evidence_quality=float(c.get("evidence_quality", 0.5)),
            freshness=float(c.get("freshness", 0.5)),
            reproducibility=float(c.get("reproducibility", 0.5)),
            historical_reliability=float(c.get("historical_reliability", 0.5)),
            confidence=float(c.get("confidence", 0.5)),
            risk_penalty=float(c.get("risk_penalty", 0.0)),
            known_outcome=c.get("known_outcome"),
        )
        scored.append(result)

        if result.get("blocked_by") == "bluff_gate":
            blocked += 1
        if result.get("abstain_recommended"):
            abstains += 1
        if "log_score" in result:
            log_scores.append(result["log_score"]["value"])
        tiers[result.get("tier", "rejected")] += 1

    # Aggregate
    scores = [r["score"] for r in scored]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    avg_log = sum(log_scores) / len(log_scores) if log_scores else None

    return {
        "scoring_version": "2.0.0-final",
        "total_claims": len(claims),
        "average_score": round(avg_score, 4),
        "average_log_score": round(avg_log, 4) if avg_log is not None else None,
        "tier_distribution": tiers,
        "bluff_blocked": blocked,
        "abstain_recommended": abstains,
        "claims": scored,
    }


def compute_v3_dual_scores(
    claims: list[dict[str, Any]],
    neuro_profile: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """V3: Compute smart_sounding_score and judgment_quality_score.

    This is the bridge between V2 scoring and V3 neuro-cognitive profiling.
    Called after score_jury_v2 to add cognitive quality dimensions.

    Returns dual scores plus cognitive risk flags for hard_truth mode triggering.
    """
    from core.neuro_profiler import compute_neuro_profile

    # If no neuro profile provided, compute from combined claim text
    if neuro_profile is None:
        combined_text = " ".join(
            c.get("claim", "") for c in claims if isinstance(c, dict)
        )
        neuro_profile = compute_neuro_profile(combined_text)

    return {
        "scoring_version": "3.1.0",
        "phase1_scoring_v2": score_jury_v2(claims),
        "v3_neuro_profile": neuro_profile,
        "dual_scores": {
            "smart_sounding_score": neuro_profile.get("smart_sounding_score", 0.5),
            "judgment_quality_score": neuro_profile.get("judgment_quality_score", 0.5),
            "gap": neuro_profile.get("smart_vs_judgment_gap", 0),
            "gap_label": neuro_profile.get("gap_label", "normal"),
        },
        "cognitive_risk_flags": neuro_profile.get("cognitive_risk_flags", []),
    }


def score_jury_full_pipeline(
    claims: list[dict[str, Any]],
    seat_vectors: dict[str, list[float]] | None = None,
    seat_performance: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Full v2.0 pipeline: Phase 1 scoring + Phase 2 diversity + Phase 3 graph value.

    This is the complete COUNCIL-003 final scoring pipeline.
    """
    # Phase 1: Claim-level scoring
    phase1 = score_jury_v2(claims)

    # Phase 2: Diversity monitoring (if seat vectors provided)
    phase2 = None
    if seat_vectors:
        from core.consensus_v2 import diversity_alert_pipeline

        perf = seat_performance or {}
        phase2 = diversity_alert_pipeline(seat_vectors, perf)

    # Phase 3: Peach projection (if we have scored seats)
    phase3 = None
    if phase2 and phase2.get("graph_values", {}).get("seat_values"):
        from core.peach_projection import peach_projection

        sv = phase2["graph_values"]["seat_values"]
        seat_scores = {s: v["value"] for s, v in sv.items()}
        seat_conf = {s: v.get("correctness", 0.5) for s, v in sv.items()}
        seat_stake = {s: 0.05 for s in sv}
        seat_acc = {s: v.get("correctness", 0.5) for s, v in sv.items()}

        phase3 = peach_projection(
            seat_scores=seat_scores,
            seat_confidence=seat_conf,
            seat_stake=seat_stake,
            seat_accuracy=seat_acc,
            k=2,
        )

    return {
        "scoring_version": "2.0.0-final",
        "phase1_scoring": phase1,
        "phase2_diversity": phase2,
        "phase3_peach_projection": phase3,
        "summary": {
            "total_claims": len(claims),
            "bluff_blocked": phase1.get("bluff_blocked", 0),
            "abstain_recommended": phase1.get("abstain_recommended", 0),
            "diversity_health": phase2["health"] if phase2 else "not_computed",
            "peach_winners": phase3["winners"] if phase3 else [],
        } if phase2 else {
            "total_claims": len(claims),
            "bluff_blocked": phase1.get("bluff_blocked", 0),
            "abstain_recommended": phase1.get("abstain_recommended", 0),
        },
    }
