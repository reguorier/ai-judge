"""FDJP hybrid synthesis – combines LLM and heuristic audit results.

Hardened rules:
- hybrid_score = 0.70 * llm_score + 0.30 * heuristic_score
- LLM unsupported_ratio >= 0.50 → hybrid_score capped at 0.59 (P0: FDJP_LLM_EVIDENCE_UNSUPPORTED)
- LLM unsupported_ratio >= 0.25 → hybrid_score capped at 0.59 (P1: FDJP_LLM_EVIDENCE_WEAK)
- LLM unavailable → effective_mode = heuristic_only
- P0 union: final_blockers = llm_blockers ∪ heuristic_blockers ∪ parser_blockers
- Conflict detection: LLM pass + heuristic P0 → P0 preserved
"""

from __future__ import annotations

from typing import Any

from product.fdjp.constants import (
    DIMENSIONS,
    HYBRID_HEURISTIC_WEIGHT,
    HYBRID_LLM_WEIGHT,
    LLM_INSUFFICIENT_DIM_CAP,
)
from product.fdjp.gates import evaluate_fdjp_gates


def _add_gate_compat_fields(dims: dict[str, Any]) -> dict[str, Any]:
    """Ensure dimensions dict has score/findings/summary for evaluate_fdjp_gates."""
    result: dict[str, Any] = {}
    for dim_key, dim_data in dims.items():
        if not isinstance(dim_data, dict):
            continue
        new_dim = dict(dim_data)
        if "score" not in new_dim:
            new_dim["score"] = new_dim.get("confidence", new_dim.get("hybrid_score", 0.5))
        if "findings" not in new_dim:
            new_dim["findings"] = []
        if "summary" not in new_dim:
            new_dim["summary"] = new_dim.get("claim", new_dim.get("reasoning_summary", ""))
        result[dim_key] = new_dim
    return result


def synthesize_hybrid_audit(
    heuristic_audit: dict[str, Any],
    llm_audit: dict[str, Any] | None,
    provider_metadata: dict[str, Any] | None = None,
    llm_unsupported_ratio: float = 0.0,
) -> dict[str, Any]:
    """Synthesize a hybrid audit from heuristic and LLM results.

    Args:
        heuristic_audit: Heuristic dimension audit dict.
        llm_audit: LLM dimension audit dict (may be None if LLM unavailable).
        provider_metadata: Optional provider metadata dict.
        llm_unsupported_ratio: Fraction of LLM evidence_refs that are unsupported.

    Returns:
        Hybrid audit dict with dimensions, scores, conflicts, blockers.
    """
    heuristic_audit, llm_audit, provider_metadata = _normalize_call_order(
        heuristic_audit,
        llm_audit,
        provider_metadata,
    )
    hybrid: dict[str, Any] = {
        "audit_mode": "hybrid",
        "effective_mode": "hybrid",
        "mode": "hybrid",
        "dimensions": {},
        "dimension_scores": {},
        "overall_score": 0.0,
        "status": "PASS_WITH_WARNINGS",
        "blockers": [],
        "warnings": [],
        "conflicts": [],
        "hybrid_conflicts": [],
        "parser_blockers": [],
        "provider_metadata": provider_metadata if isinstance(provider_metadata, dict) else {},
        "llm_metadata": (llm_audit or {}).get("llm_metadata", {}) if isinstance(llm_audit, dict) else {},
        "heuristic_metadata": heuristic_audit.get("heuristic_metadata", {}) if isinstance(heuristic_audit, dict) else {},
        "insights": [],
        "llm_unsupported_ratio": llm_unsupported_ratio,
    }
    hybrid["insights"] = _combine_lists(
        (llm_audit or {}).get("insights", []) if isinstance(llm_audit, dict) else [],
        heuristic_audit.get("insights", []) if isinstance(heuristic_audit, dict) else [],
    )

    # ── Handle LLM unavailable ──
    if llm_audit is None or not isinstance(llm_audit, dict):
        hybrid["effective_mode"] = "heuristic_only"
        hybrid["mode"] = "heuristic"
        hybrid["status"] = _heuristic_only_status(heuristic_audit)
        hybrid["overall_score"] = heuristic_audit.get("overall_score", 0.0)
        hybrid["dimension_scores"] = heuristic_audit.get("dimension_scores", {})
        hybrid["blockers"] = heuristic_audit.get("blockers", [])
        hybrid["warnings"] = heuristic_audit.get("warnings", [])
        hybrid["dimensions"] = _add_gate_compat_fields(heuristic_audit.get("dimensions", {}))
        hybrid["conflicts"] = heuristic_audit.get("cross_dimension_conflicts", [])
        hybrid["heuristic_metadata"] = {
            **(hybrid.get("heuristic_metadata") or {}),
            "reason": "LLM unavailable, hybrid degraded to heuristic_only",
        }
        return hybrid

    llm_success = (llm_audit.get("llm_metadata") or {}).get("success")
    if llm_success is False:
        hybrid["effective_mode"] = "heuristic_only"
        hybrid["mode"] = "heuristic"
        hybrid["status"] = _heuristic_only_status(heuristic_audit)
        hybrid["overall_score"] = heuristic_audit.get("overall_score", 0.0)
        hybrid["dimension_scores"] = heuristic_audit.get("dimension_scores", {})
        hybrid["blockers"] = heuristic_audit.get("blockers", [])
        hybrid["warnings"] = heuristic_audit.get("warnings", [])
        hybrid["dimensions"] = _add_gate_compat_fields(heuristic_audit.get("dimensions", {}))
        hybrid["conflicts"] = heuristic_audit.get("cross_dimension_conflicts", [])
        hybrid["heuristic_metadata"] = {
            **(hybrid.get("heuristic_metadata") or {}),
            "reason": "LLM failed, hybrid degraded to heuristic_only",
        }
        return hybrid

    # ── Handle empty LLM result ──
    llm_dims = llm_audit.get("dimensions", {})
    if not llm_dims or not isinstance(llm_dims, dict):
        hybrid["effective_mode"] = "heuristic_only"
        hybrid["mode"] = "heuristic"
        hybrid["status"] = _heuristic_only_status(heuristic_audit)
        hybrid["overall_score"] = heuristic_audit.get("overall_score", 0.0)
        hybrid["dimension_scores"] = heuristic_audit.get("dimension_scores", {})
        hybrid["blockers"] = heuristic_audit.get("blockers", [])
        hybrid["warnings"] = heuristic_audit.get("warnings", [])
        hybrid["dimensions"] = _add_gate_compat_fields(heuristic_audit.get("dimensions", {}))
        hybrid["conflicts"] = heuristic_audit.get("cross_dimension_conflicts", [])
        hybrid["heuristic_metadata"] = {
            **(hybrid.get("heuristic_metadata") or {}),
            "reason": "LLM returned no dimensions, hybrid degraded to heuristic_only",
        }
        return hybrid

    he_dims = heuristic_audit.get("dimensions", {})
    he_scores = heuristic_audit.get("dimension_scores", {}) if isinstance(heuristic_audit.get("dimension_scores"), dict) else {}
    llm_scores = llm_audit.get("dimension_scores", {}) if isinstance(llm_audit.get("dimension_scores"), dict) else {}

    # ── Synthesize each dimension ──
    dimension_scores: dict[str, Any] = {}
    for dim in DIMENSIONS:
        he_dim = he_dims.get(dim, {})
        llm_dim = llm_dims.get(dim, {})

        he_score = _safe_score(he_scores.get(dim, he_dim.get("score", he_dim.get("confidence", 0.0))))
        llm_score = _safe_score(llm_scores.get(dim, llm_dim.get("confidence", llm_dim.get("score", 0.0))))

        # LLM insufficient dim cap
        if llm_dim.get("status") == "insufficient":
            llm_score = min(llm_score, LLM_INSUFFICIENT_DIM_CAP)

        # Hybrid weighted score
        hybrid_score = HYBRID_LLM_WEIGHT * llm_score + HYBRID_HEURISTIC_WEIGHT * he_score

        # ── Conflict detection ──
        he_status = he_dim.get("status", "pass")
        llm_status = llm_dim.get("status", "pass")
        conflict = _detect_conflict(dim, he_status, llm_status)

        # ── P0 union ──
        he_blocker = he_status == "blocker"
        llm_blocker = llm_status == "blocker"
        is_blocker = he_blocker or llm_blocker

        # Record dimension result
        dimension_scores[dim] = {
            "llm_score": round(llm_score, 4),
            "heuristic_score": round(he_score, 4),
            "hybrid_score": round(hybrid_score, 4),
            "heuristic_status": he_status,
            "llm_status": llm_status,
            "hybrid_status": "blocker" if is_blocker else (
                "warning" if (he_status == "warning" or llm_status == "warning") else "pass"
            ),
            "conflict": conflict,
            "llm_evidence_refs": llm_dim.get("evidence_refs", []),
            "heuristic_keywords": he_dim.get("keywords", []),
            # Compatibility fields for evaluate_fdjp_gates
            "score": round(hybrid_score, 4),
            "findings": llm_dim.get("findings", he_dim.get("findings", [])),
            "summary": llm_dim.get("reasoning_summary", he_dim.get("summary", "")),
        }
        hybrid["dimensions"][dim] = dimension_scores[dim]

    # ── Aggregate cross-dimension conflicts ──
    for dim, dim_data in dimension_scores.items():
        conflict = dim_data.get("conflict")
        if conflict is not None:
            hybrid.setdefault("cross_dimension_conflicts", []).append(conflict)
            # Also add to hybrid_conflicts for API compatibility
            hybrid.setdefault("hybrid_conflicts", []).append(conflict)

    # ── Compute overall hybrid score ──
    if dimension_scores:
        raw_score = sum(d["hybrid_score"] for d in dimension_scores.values()) / len(dimension_scores)
    else:
        raw_score = 0.0

    # ── Cap score based on LLM unsupported ratio ──
    if llm_unsupported_ratio >= 0.50:
        raw_score = min(raw_score, 0.59)
        hybrid["parser_blockers"].append("FDJP_LLM_EVIDENCE_UNSUPPORTED")
    elif llm_unsupported_ratio >= 0.25:
        raw_score = min(raw_score, 0.59)
        hybrid["warnings"].append("FDJP_LLM_EVIDENCE_WEAK")

    hybrid["overall_score"] = round(raw_score, 4)
    hybrid["dimension_scores"] = {
        dim: data["hybrid_score"] for dim, data in dimension_scores.items()
    }

    # ── Gate evaluation ──
    # Save parser-level state before gate evaluation overwrites them
    pre_gate_warnings = list(hybrid.get("warnings", []))
    pre_gate_blockers = list(hybrid.get("parser_blockers", []))
    pre_gate_conflicts = list(hybrid.get("cross_dimension_conflicts", []))
    gates = evaluate_fdjp_gates(hybrid)
    hybrid.update(gates)
    # Merge back parser-level state
    for w in pre_gate_warnings:
        if w not in hybrid["warnings"]:
            hybrid["warnings"].append(w)
    for b in pre_gate_blockers:
        if b not in hybrid["parser_blockers"]:
            hybrid["parser_blockers"].append(b)
    # Merge back conflicts (gate evaluation may return empty conflicts)
    if pre_gate_conflicts and not hybrid.get("cross_dimension_conflicts"):
        hybrid["cross_dimension_conflicts"] = pre_gate_conflicts
    hybrid["conflicts"] = hybrid.get("cross_dimension_conflicts", [])

    # ── Collect blockers (P0 union) ──
    all_blockers: set[str] = set()
    # Extract blocker_ids from gate evaluation (blockers are dicts with blocker_id)
    for b in hybrid.get("blockers", []):
        if isinstance(b, dict):
            all_blockers.add(b.get("blocker_id", ""))
        elif isinstance(b, str):
            all_blockers.add(b)
    all_blockers.update(b for b in hybrid.get("parser_blockers", []) if isinstance(b, str))
    for dim_data in dimension_scores.values():
        if dim_data.get("heuristic_status") == "blocker":
            all_blockers.add(f"heuristic_block:{dim_data.get('heuristic_status', '')}")
        if dim_data.get("llm_status") == "blocker":
            all_blockers.add(f"llm_block:{dim_data.get('llm_status', '')}")
    hybrid["final_blockers"] = sorted(all_blockers)

    # ── P0 absolute priority ──
    if hybrid["final_blockers"]:
        hybrid["status"] = "FDJP_CONTENT_BLOCKED"
        hybrid["overall_score"] = min(hybrid["overall_score"], 0.34)

    return hybrid


def _normalize_call_order(
    first: dict[str, Any],
    second: dict[str, Any] | None,
    provider_metadata: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    """Accept both legacy (llm, heuristic, task_type) and current (heuristic, llm) calls."""
    if isinstance(first, dict) and "llm_metadata" in first and (
        second is None
        or (isinstance(second, dict) and "heuristic_metadata" in second)
        or (isinstance(second, dict) and "llm_metadata" not in second)
    ):
        heuristic = second if isinstance(second, dict) else {}
        llm = first
        return heuristic, llm, provider_metadata if isinstance(provider_metadata, dict) else {}
    return first if isinstance(first, dict) else {}, second, provider_metadata if isinstance(provider_metadata, dict) else {}


def _combine_lists(*values: Any) -> list[Any]:
    rows: list[Any] = []
    for value in values:
        if isinstance(value, list):
            rows.extend(value)
    return rows


def _detect_conflict(
    dim: str,
    he_status: str,
    llm_status: str,
) -> dict[str, Any] | None:
    """Detect conflicts between heuristic and LLM for a dimension.

    Only records conflict when heuristic says blocker/warning and LLM says
    pass (or vice versa) in a way that matters for the final outcome.
    """
    if he_status == "blocker" and llm_status == "pass":
        return {
            "dimension": dim,
            "llm_status": llm_status,
            "heuristic_status": he_status,
            "resolution": "P0 preserved from heuristic",
        }
    if he_status == "pass" and llm_status == "blocker":
        return {
            "dimension": dim,
            "llm_status": llm_status,
            "heuristic_status": he_status,
            "resolution": "P0 preserved from LLM",
        }
    return None


def _heuristic_only_status(heuristic_audit: dict[str, Any]) -> str:
    """Determine status when mode is heuristic_only.

    heuristic_only can never be FDJP_FULL_PASS.
    """
    score = heuristic_audit.get("overall_score", 0.0)
    blockers = heuristic_audit.get("blockers", [])

    if blockers:
        return "FDJP_CONTENT_BLOCKED"

    if score >= 0.80:
        return "FDJP_PASS_WITH_WARNINGS"  # heuristic_only max
    if score >= 0.60:
        return "FDJP_PASS_WITH_WARNINGS"
    if score >= 0.35:
        return "FDJP_PARTIAL"
    return "FDJP_CONTENT_BLOCKED"


def _safe_score(val: Any) -> float:
    """Coerce a value to [0, 1] float."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return max(0.0, min(1.0, v))
