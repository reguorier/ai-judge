#!/usr/bin/env python3
"""Peach Projection — Two Peaches Kill Three Warriors applied to AI Judge.

Implements COUNCIL-003: per-claim scarcity-based weight allocation.
Only the top k seats per claim get primary influence; the rest get floor.

Ported from the Two Peaches mechanism design proposed in COUNCIL-003.
"""

from __future__ import annotations

from typing import Any


def peach_projection(
    *,
    seat_scores: dict[str, float],
    seat_confidence: dict[str, float],
    seat_stake: dict[str, float],
    seat_accuracy: dict[str, float],
    k: int = 2,
    floor: float = 0.05,
) -> dict[str, Any]:
    """Allocate per-claim influence weights using scarcity competition.

    Only top-k seats get primary weight. Remaining seats get floor.
    Merit formula: confidence × accuracy × (1 + stake_bonus)

    Args:
        seat_scores: raw allocation_score per seat
        seat_confidence: confidence per seat
        seat_stake: staked T-credit per seat
        seat_accuracy: historical accuracy per seat
        k: number of "peach winners" (default 2)
        floor: minimum weight for non-winning seats (default 0.05)
    """
    if k <= 0:
        raise ValueError("k must be positive")
    if floor < 0 or floor > 0.10:
        raise ValueError("floor should be in [0, 0.10]")

    seats = list(seat_scores.keys())
    n = len(seats)
    if n == 0:
        return {"winners": [], "weights": {}, "distribution": "no_seats"}

    # Compute merit for each seat
    merit: dict[str, float] = {}
    for seat in seats:
        conf = float(seat_confidence.get(seat, 0.5))
        acc = float(seat_accuracy.get(seat, 0.5))
        stake = float(seat_stake.get(seat, 0.0))
        # stake_bonus: up to 20% boost for those who put skin in the game
        stake_bonus = min(0.2, stake * 0.1)
        merit[seat] = round(conf * acc * (1.0 + stake_bonus), 6)

    # Sort by merit descending
    ranked = sorted(merit.items(), key=lambda x: x[1], reverse=True)

    # Determine winners
    k_actual = min(k, n)
    winners = [seat for seat, _ in ranked[:k_actual]]
    losers = [seat for seat, _ in ranked[k_actual:]]

    # Allocate weights
    winner_pool = 1.0 - (len(losers) * floor)
    if winner_pool < 0:
        winner_pool = 0.0

    weights: dict[str, float] = {}
    total_merit_winners = sum(merit[w] for w in winners) or 1.0

    for seat in seats:
        if seat in winners:
            frac = merit[seat] / total_merit_winners
            weights[seat] = round(frac * winner_pool, 6)
        else:
            weights[seat] = round(floor, 6)

    # Handle edge case: fix rounding drift
    drift = 1.0 - sum(weights.values())
    if abs(drift) > 1e-9 and winners:
        weights[winners[-1]] = round(weights[winners[-1]] + drift, 6)

    return {
        "k": k,
        "floor": floor,
        "winners": winners,
        "weights": weights,
        "merits": merit,
        "distribution": {
            "winner_pool": round(winner_pool, 6),
            "loser_pool": round(len(losers) * floor, 6),
            "winner_count": len(winners),
            "loser_count": len(losers),
        },
        "explanation": (
            f"Top {k_actual} seats (of {n}) awarded primary influence. "
            f"Winners: {', '.join(winners)}. "
            f"Losers get floor={floor} each. "
            f"Merit = confidence × accuracy × (1 + stake_bonus)."
        ),
    }


def consensus_penalty(
    agree_count: int,
    total_seats: int,
    has_tier0_evidence: bool = False,
) -> float:
    """If all seats agree without hard evidence, penalize consensus weight.

    Prevents the "9 echos" problem where all models agree but are collectively wrong.
    """
    if agree_count == total_seats and not has_tier0_evidence:
        return 0.5  # Halve weights
    return 1.0


def stake_settlement(
    *,
    was_correct: bool,
    staked_amount: float,
    confidence: float,
) -> dict[str, Any]:
    """Settle a staked claim. Correct = return stake + bonus. Wrong = forfeit.

    Bonus is proportional to confidence: higher confidence correct answers
    get bigger rewards, but higher confidence wrong answers lose everything.
    """
    if was_correct:
        bonus = staked_amount * confidence * 0.1
        net = staked_amount + bonus
        action = "reward"
    else:
        net = -staked_amount
        action = "forfeit"

    return {
        "action": action,
        "staked": staked_amount,
        "net_change": round(net, 6),
        "explanation": (
            f"Stake {'returned + bonus' if was_correct else 'forfeited'}. "
            f"Net: {net:+.4f}"
        ),
    }
