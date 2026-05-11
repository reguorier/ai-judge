#!/usr/bin/env python3
"""Consensus v2.0 — Diversity monitoring, cluster detection, and graph valuation.

Phase 2+ functions from COUNCIL-003:
  - normalized_graph_variance: diversity radar against consensus hallucination
  - cluster_strategy_vectors: detect implicit alignment between seats
  - graph_value_v2: correctness-first seat valuation
  - diversity_alert: threshold-based warning system
"""

from __future__ import annotations

import math
import statistics
from typing import Any

from core.formula_engine import graph_value_v2


def normalized_graph_variance(seat_vectors: dict[str, list[float]]) -> dict[str, Any]:
    """Compute normalized diversity across seat response vectors.

    A low value means seats are converging — potential consensus hallucination.
    A high value means seats are genuinely diverse.

    Returns a diversity_index in [0, 1] where:
      - < 0.3: CRITICAL — seats are echo chambers
      - 0.3-0.6: WARNING — diversity declining
      - > 0.6: HEALTHY
    """
    if len(seat_vectors) < 2:
        return {"diversity_index": 0.0, "status": "insufficient_data", "warning": "need at least 2 seats"}

    seats = list(seat_vectors.keys())
    vector_len = len(seat_vectors[seats[0]])
    if vector_len == 0:
        return {"diversity_index": 0.0, "status": "empty_vectors"}

    # Collect per-dimension variances
    columns = []
    for i in range(vector_len):
        col = [seat_vectors[seat][i] for seat in seats if i < len(seat_vectors[seat])]
        if len(col) >= 2:
            columns.append(statistics.pvariance(col))

    if not columns:
        return {"diversity_index": 0.0, "status": "no_variance_data"}

    avg_variance = sum(columns) / len(columns)
    # Maximum possible variance for [0,1] bounded values is 0.25
    diversity_index = round(min(1.0, avg_variance / 0.25), 6)

    # Determine status
    if diversity_index < 0.3:
        status = "critical_echo_chamber"
        alert = "9 seats are producing near-identical outputs. Consensus hallucination risk is HIGH."
    elif diversity_index < 0.6:
        status = "warning_diversity_low"
        alert = "Seat diversity is declining. Consider injecting adversarial prompts or raising temperature."
    else:
        status = "healthy"
        alert = None

    return {
        "diversity_index": diversity_index,
        "status": status,
        "alert": alert,
        "seat_count": len(seats),
        "dimensions_analyzed": len(columns),
    }


def cluster_strategy_vectors(
    seat_vectors: dict[str, list[float]],
    threshold: float = 0.45,
) -> dict[str, Any]:
    """Greedy cluster detection — find seats that are implicitly aligned.

    Seats whose response vectors are within Euclidean distance < threshold
    are clustered together. These clusters may represent:
      - Shared training data biases
      - Model family similarities (GPT family, Gemini family, etc.)
      - Strategic alignment

    Returns clusters for private reflection (not public punishment).
    """
    if len(seat_vectors) < 2:
        return {"clusters": [], "alignment_warnings": []}

    seats = list(seat_vectors.keys())

    # Euclidean distance helper
    def euclidean(a: list[float], b: list[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    # Greedy clustering
    clusters: list[list[str]] = []
    for seat in seats:
        vector = seat_vectors[seat]
        placed = False
        for cluster in clusters:
            centroid = [
                sum(seat_vectors[s][i] for s in cluster if i < len(seat_vectors[s])) / len(cluster)
                for i in range(len(vector))
            ]
            dist = euclidean(vector, centroid)
            if dist <= threshold:
                cluster.append(seat)
                placed = True
                break
        if not placed:
            clusters.append([seat])

    # Build alignment warnings for clusters > 1
    alignment_warnings = []
    for cluster in clusters:
        if len(cluster) > 1:
            alignment_warnings.append({
                "seats": cluster,
                "size": len(cluster),
                "warning": f"Seats {', '.join(cluster)} show high response similarity. Consider merging their scoring weights.",
            })

    return {
        "cluster_count": len(clusters),
        "largest_cluster_size": max(len(c) for c in clusters) if clusters else 0,
        "clusters": clusters,
        "alignment_warnings": alignment_warnings,
        "threshold": threshold,
    }


def build_seat_graph_values(
    seat_performance: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Build graph_value_v2 for all seats using COUNCIL-003 approved formula.

    Each seat gets a correctness-first valuation that can be used
    to replace the old single-dimensional historical_reliability.
    """
    results = {}
    for seat, perf in seat_performance.items():
        gv = graph_value_v2(
            correctness=perf.get("correctness", 0.5),
            rarity_score=perf.get("rarity_score", 0.0),
            replay_count=int(perf.get("replay_count", 0)),
            demand_score=perf.get("demand_score", 0.5),
            calibration_consistency=perf.get("calibration_consistency", 0.5),
        )
        results[seat] = gv

    return {
        "seat_values": results,
        "top_seat": max(results, key=lambda s: results[s]["value"]) if results else None,
        "average_value": round(
            sum(r["value"] for r in results.values()) / len(results), 6
        ) if results else 0.0,
    }


def diversity_alert_pipeline(
    seat_vectors: dict[str, list[float]],
    seat_performance: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Full pipeline: diversity check → cluster detection → graph valuation.

    This runs after each jury session to produce the consensus health report.
    """
    diversity = normalized_graph_variance(seat_vectors)
    clusters = cluster_strategy_vectors(seat_vectors)
    graph_vals = build_seat_graph_values(seat_performance)

    # Compose final health report
    health = "healthy"
    if diversity["status"] == "critical_echo_chamber":
        health = "critical"
    elif diversity["status"] == "warning_diversity_low":
        health = "warning"
    if clusters["largest_cluster_size"] >= 5:
        health = "critical"

    return {
        "version": "2.0.0",
        "health": health,
        "diversity": diversity,
        "clusters": clusters,
        "graph_values": graph_vals,
        "recommendation": (
            "Inject adversarial prompts to break consensus"
            if health == "critical" else
            "Monitor diversity trend" if health == "warning" else
            "System is healthy"
        ),
    }
