#!/usr/bin/env python3
"""Lightweight evidence-quality metrics inspired by eval platforms."""

from __future__ import annotations

from typing import Any


def compute_evidence_quality_metrics(grand_report: dict[str, Any]) -> dict[str, Any]:
    citation = grand_report.get("citation_verification") or {}
    counts = citation.get("counts") or {}
    total = max(1, int(citation.get("item_count") or sum(int(v or 0) for v in counts.values()) or 0))
    verified = int(counts.get("verified", 0) or 0)
    weak = int(counts.get("weakly_verified", 0) or 0)
    unverifiable = int(counts.get("unverifiable", 0) or 0)
    contradicted = int(counts.get("contradicted", 0) or 0)
    irrelevant = int(counts.get("irrelevant", 0) or 0)
    groundedness_proxy = (verified + 0.5 * weak) / total
    risk_rate = (unverifiable + contradicted + irrelevant) / total
    return {
        "schema": "evidence_quality_metrics.v1",
        "groundedness_proxy": round(groundedness_proxy, 4),
        "verified_ratio": round(verified / total, 4),
        "weakly_verified_ratio": round(weak / total, 4),
        "unverifiable_rate": round(unverifiable / total, 4),
        "contradiction_rate": round(contradicted / total, 4),
        "irrelevant_rate": round(irrelevant / total, 4),
        "hard_evidence_count": int(citation.get("external_evidence_count", 0) or 0),
        "trust_gate": _trust_gate(groundedness_proxy, contradicted, citation),
    }


def _trust_gate(groundedness_proxy: float, contradicted: int, citation: dict[str, Any]) -> str:
    if contradicted:
        return "blocked_contradiction"
    if int(citation.get("external_evidence_count", 0) or 0) <= 0:
        return "needs_external_evidence"
    if groundedness_proxy >= 0.67:
        return "pass"
    return "needs_more_evidence"
