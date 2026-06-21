"""FDJP gates – blocker/warning detection and score evaluation."""

from __future__ import annotations

from typing import Any

from product.fdjp.constants import (
    DEFAULT_DIMENSION_WEIGHTS,
    DIMENSIONS,
    FDJP_P0_BLOCKERS,
    FDJP_P1_WARNINGS,
    FDJP_SCORE_THRESHOLD_FULL_PASS,
    FDJP_SCORE_THRESHOLD_PARTIAL,
    FDJP_SCORE_THRESHOLD_WARNINGS,
    TASK_TYPE_WEIGHTS,
)


def evaluate_fdjp_gates(audit: dict[str, Any]) -> dict[str, Any]:
    """Evaluate FDJP blocker/warning gates against an audit dict."""
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    dims = audit.get("dimensions", {})
    mode = audit.get("mode", "unknown")

    # Check each dimension for blockers
    for dim in DIMENSIONS:
        dim_data = dims.get(dim, {})
        summary = str(dim_data.get("summary", "")).strip()
        findings = dim_data.get("findings", [])
        score = dim_data.get("score", 0.0)

        if dim == "philosophy" and (not summary or score < 0.30):
            blockers.append({
                "blocker_id": "PHILOSOPHY_ESSENCE_MISSING",
                "severity": "P0",
                "reason": FDJP_P0_BLOCKERS["PHILOSOPHY_ESSENCE_MISSING"],
                "affected_dimension": dim,
            })

        if dim == "military" and (not findings or score < 0.30):
            blockers.append({
                "blocker_id": "MILITARY_ACTION_MISSING",
                "severity": "P0",
                "reason": FDJP_P0_BLOCKERS["MILITARY_ACTION_MISSING"],
                "affected_dimension": dim,
            })

        if dim == "economy" and (not findings or score < 0.30):
            blockers.append({
                "blocker_id": "ECONOMY_STAKEHOLDER_MISSING",
                "severity": "P0",
                "reason": FDJP_P0_BLOCKERS["ECONOMY_STAKEHOLDER_MISSING"],
                "affected_dimension": dim,
            })

        if dim == "politics" and (not findings or score < 0.30):
            blockers.append({
                "blocker_id": "POLITICS_AUTHORITY_MISSING",
                "severity": "P0",
                "reason": FDJP_P0_BLOCKERS["POLITICS_AUTHORITY_MISSING"],
                "affected_dimension": dim,
            })

        if dim == "history" and (not summary or score < 0.20):
            blockers.append({
                "blocker_id": "HISTORY_PRECEDENT_REQUIRED_MISSING",
                "severity": "P0",
                "reason": FDJP_P0_BLOCKERS["HISTORY_PRECEDENT_REQUIRED_MISSING"],
                "affected_dimension": dim,
            })

    # Check for P1 warnings
    for dim in DIMENSIONS:
        dim_data = dims.get(dim, {})
        score = dim_data.get("score", 0.0)
        findings = dim_data.get("findings", [])

        if dim == "economy" and 0.30 <= score < 0.55:
            warnings.append({
                "warning_id": "HIDDEN_COST_WEAK",
                "severity": "P1",
                "reason": FDJP_P1_WARNINGS["HIDDEN_COST_WEAK"],
                "affected_dimension": dim,
            })
        if dim == "politics" and 0.30 <= score < 0.55:
            warnings.append({
                "warning_id": "POWER_MAP_SHALLOW",
                "severity": "P1",
                "reason": FDJP_P1_WARNINGS["POWER_MAP_SHALLOW"],
                "affected_dimension": dim,
            })
        if dim == "history" and findings and score < 0.50:
            warnings.append({
                "warning_id": "BAD_ANALOGY_RISK",
                "severity": "P1",
                "reason": FDJP_P1_WARNINGS["BAD_ANALOGY_RISK"],
                "affected_dimension": dim,
            })
        if dim == "military" and score < 0.50:
            warnings.append({
                "warning_id": "NO_FALLBACK_PLAN",
                "severity": "P1",
                "reason": FDJP_P1_WARNINGS["NO_FALLBACK_PLAN"],
                "affected_dimension": dim,
            })

    if mode == "heuristic":
        warnings.append({
            "warning_id": "FDJP_LLM_UNAVAILABLE_HEURISTIC_ONLY",
            "severity": "P1",
            "reason": FDJP_P1_WARNINGS["FDJP_LLM_UNAVAILABLE_HEURISTIC_ONLY"],
            "affected_dimension": "global",
        })

    return {
        "blockers": blockers,
        "warnings": warnings,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
    }


def evaluate_dimension_scores(
    audit: dict[str, Any],
    task_type: str = "general",
) -> dict[str, Any]:
    """Compute weighted dimension scores and overall_score."""
    weights = TASK_TYPE_WEIGHTS.get(task_type, TASK_TYPE_WEIGHTS["general"])
    dim_scores = audit.get("dimension_scores", {})

    # Compute weighted overall
    weighted_sum = 0.0
    weight_total = 0.0
    for dim, score in dim_scores.items():
        w = weights.get(dim, DEFAULT_DIMENSION_WEIGHTS.get(dim, 0.20))
        weighted_sum += score * w
        weight_total += w

    overall = weighted_sum / max(weight_total, 0.01) if weight_total > 0 else 0.0
    if audit.get("mode", "heuristic") == "heuristic":
        overall = min(overall, 0.75)  # hard cap for heuristic

    audit["overall_score"] = round(overall, 4)
    audit["dimension_scores"] = {k: round(v, 4) for k, v in dim_scores.items()}

    # ── Gate Semantics Patch: fixed status determination ──
    gates = audit.get("gates", {})
    blocker_count = gates.get("blocker_count", 0)
    is_heuristic = audit.get("mode") == "heuristic"

    # Rule 1: Any P0 blocker → CONTENT_BLOCKED (absolute priority, never PASS_WITH_WARNINGS)
    if blocker_count > 0:
        audit["status"] = "FDJP_CONTENT_BLOCKED"
    else:
        # Rule 2: Score-based thresholds (no P0 blockers)
        # Rule 3: heuristic mode can never reach FULL_PASS
        if overall >= FDJP_SCORE_THRESHOLD_FULL_PASS and not is_heuristic:
            audit["status"] = "FDJP_FULL_PASS"
        elif overall >= FDJP_SCORE_THRESHOLD_WARNINGS:
            audit["status"] = "FDJP_PASS_WITH_WARNINGS"
        elif overall >= FDJP_SCORE_THRESHOLD_PARTIAL:
            audit["status"] = "FDJP_PARTIAL"
        else:
            audit["status"] = "FDJP_CONTENT_BLOCKED"

    return audit