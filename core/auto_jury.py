#!/usr/bin/env python3
"""Automatic local jury execution for AI Judge v3.4.

This module gives the product a complete end-to-end path even when no external
LLM provider is configured. It converts the fixed seat personas into structured
claims, scores those claims through the existing v2 scoring engine, and returns
a product-ready verdict.

The boundary is intentionally narrow: when live model providers are added, swap
`build_local_claims()` for provider-backed claim collection and keep the rest of
the product/API/notification surface unchanged.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from core.modes import resolve_mode
from core.scoring_v2 import score_jury_v2
from core.seat_personas import SEAT_PERSONAS


RISK_PENALTY = {
    "very_low": 0.02,
    "low": 0.03,
    "conservative": 0.035,
    "moderate_low": 0.04,
    "moderate": 0.05,
    "balanced": 0.05,
    "moderate_high": 0.065,
    "aggressive": 0.08,
    "aggressive_pragmatic": 0.075,
    "high": 0.09,
}

VERDICT_LABELS = {
    "credible": "可信",
    "conditional": "建议推进但需验证",
    "unverified": "证据不足",
    "rejected": "不建议采纳",
}


def run_auto_jury(
    question: str,
    mode: str = "flash",
    seats: list[str] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the automatic local jury and return a complete verdict object."""
    question = question.strip()
    if not question:
        raise ValueError("question is required")

    config = resolve_mode(mode, override_seats=seats)
    resolved_seats = _valid_seats(config["seats"])
    claims = build_local_claims(question=question, mode=mode, seats=resolved_seats)
    return assemble_verdict(
        question=question,
        mode=mode,
        seats=resolved_seats,
        claims=claims,
        run_id=run_id,
        engine="local-auto-jury-v3.4",
    )


def assemble_verdict(
    question: str,
    mode: str,
    seats: list[str],
    claims: list[dict[str, Any]],
    run_id: str | None = None,
    engine: str = "local-auto-jury-v3.4",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score structured claims and return the product-ready verdict object."""
    config = resolve_mode(mode, override_seats=seats)
    resolved_seats = _valid_seats(config["seats"])
    score_result = score_jury_v2(claims)
    scored_claims = _merge_scored_claims(claims, score_result.get("claims", []))
    verdict = _derive_verdict(score_result)
    average_score = float(score_result.get("average_score", 0.0) or 0.0)
    confidence = _derive_confidence(score_result, resolved_seats)
    seat_scores = _seat_scores(scored_claims)
    reasons = _top_reasons(scored_claims, verdict)

    result = {
        "run_id": run_id,
        "question": question,
        "mode": mode,
        "mode_name": config["name"],
        "mode_emoji": config["emoji"],
        "seats": resolved_seats,
        "seat_count": len(resolved_seats),
        "status": "complete",
        "verdict": verdict,
        "verdict_label": VERDICT_LABELS.get(verdict, verdict),
        "one_liner": _one_liner(verdict, question, confidence),
        "confidence": confidence,
        "average_score": round(average_score, 4),
        "tier_distribution": score_result.get("tier_distribution", {}),
        "total_claims": len(scored_claims),
        "seat_scores": seat_scores,
        "reasons": reasons,
        "next_steps": _next_steps(verdict, mode),
        "claims": scored_claims,
        "summary": _summary_text(question, mode, verdict, confidence, reasons),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "features": config.get("features", {}),
    }
    if extra:
        result.update(extra)
    return result


def build_local_claims(question: str, mode: str, seats: list[str]) -> list[dict[str, Any]]:
    """Generate deterministic structured claims from seat personas."""
    claims: list[dict[str, Any]] = []
    for idx, seat in enumerate(seats):
        persona = SEAT_PERSONAS[seat]
        base = _seat_base(question, seat, mode)
        risk_penalty = RISK_PENALTY.get(persona.get("risk_preference", "moderate"), 0.05)
        common = {
            "_seat": seat,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "source_authority": _clamp(base + 0.12),
            "evidence_strength": _clamp(base + (0.08 if mode != "flash" else 0.0)),
            "evidence_count": 2 + int(_stable_float(question, seat, "count") * 5),
            "evidence_quality": _clamp(base + 0.05),
            "freshness": _clamp(0.62 + _stable_float(question, seat, "freshness") * 0.25),
            "reproducibility": _clamp(0.58 + _stable_float(question, seat, "repro") * 0.28),
            "historical_reliability": _clamp(0.60 + _stable_float(seat, mode, "history") * 0.25),
            "confidence": _clamp(base + 0.10),
            "risk_penalty": risk_penalty,
        }

        claims.append({
            **common,
            "claim_id": f"{seat}-main",
            "claim": (
                f"{persona['name']} ({persona['mbti']}) sees the decision in '{question}' as "
                f"{_stance_word(base)} because {persona['strength']}."
            ),
        })

        if mode != "flash":
            claims.append({
                **common,
                "claim_id": f"{seat}-risk",
                "source_authority": _clamp(common["source_authority"] - 0.05),
                "evidence_strength": _clamp(common["evidence_strength"] - 0.04),
                "confidence": _clamp(common["confidence"] - 0.08),
                "risk_penalty": _clamp(risk_penalty + 0.025, 0.0, 0.2),
                "claim": (
                    f"{persona['name']} flags a blind spot for '{question}': "
                    f"{persona['weakness']} must be actively checked before execution."
                ),
            })

        if mode == "strategic":
            claims.append({
                **common,
                "claim_id": f"{seat}-audit",
                "source_authority": _clamp(common["source_authority"] + 0.03),
                "evidence_strength": _clamp(common["evidence_strength"] + 0.02),
                "confidence": _clamp(common["confidence"] - 0.03),
                "risk_penalty": _clamp(risk_penalty + 0.015, 0.0, 0.2),
                "claim": (
                    f"{persona['name']} recommends an audit checkpoint for '{question}' "
                    "before irreversible commitment."
                ),
            })

    return claims


def format_verdict_markdown(verdict: dict[str, Any]) -> str:
    """Render a verdict object as Markdown."""
    lines = [
        f"# AI Judge Verdict",
        "",
        f"**Run ID:** {verdict.get('run_id') or '-'}",
        f"**Mode:** {verdict.get('mode_emoji', '')} {verdict.get('mode_name', verdict.get('mode'))}",
        f"**Question:** {verdict.get('question', '')}",
        f"**Verdict:** {verdict.get('verdict_label', verdict.get('verdict'))}",
        f"**Confidence:** {verdict.get('confidence', 0)}%",
        "",
        f"## One Liner",
        "",
        verdict.get("one_liner", ""),
        "",
        "## Key Reasons",
        "",
    ]
    for reason in verdict.get("reasons", []):
        lines.append(f"- {reason}")

    judge = verdict.get("judge_answer") or {}
    baseline = verdict.get("single_judge_baseline") or {}
    if judge or baseline:
        lines.extend(["", f"## {judge.get('label') or baseline.get('label') or 'AI Judge Judge Answer'}", ""])
        if judge.get("answer"):
            lines.append(str(judge.get("answer")))
        if baseline:
            lines.extend([
                "",
                f"- Single-judge score: {baseline.get('score', '-')}",
                f"- Council average score: {baseline.get('council_average_score', '-')}",
                f"- Delta vs council: {baseline.get('delta_vs_council', '-')}",
            ])

    score_rounds = ((verdict.get("web_bridge") or {}).get("score_rounds") or [])
    if score_rounds:
        lines.extend(["", "## Score Rounds", "", "| Round | Claims | Avg |", "|---|---:|---:|"])
        for item in score_rounds:
            avg = item.get("average_score")
            avg_text = "-" if avg is None else f"{float(avg):.3f}"
            lines.append(f"| {item.get('label', item.get('id'))} | {item.get('claim_count', 0)} | {avg_text} |")

    lines.extend(["", "## Next Steps", ""])
    for step in verdict.get("next_steps", []):
        lines.append(f"- {step}")

    lines.extend(["", "## Seat Scores", "", "| Seat | MBTI | Avg | Claims |", "|---|---:|---:|---:|"])
    for seat in verdict.get("seat_scores", []):
        lines.append(
            f"| {seat.get('seat_name', seat.get('seat'))} | {seat.get('mbti', '')} | "
            f"{seat.get('average_score', 0):.3f} | {seat.get('claims_count', 0)} |"
        )

    lines.extend(["", "## Raw JSON", "", "```json", json.dumps(verdict, ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines)


def _valid_seats(seats: list[str]) -> list[str]:
    valid = [s.lower() for s in seats if s.lower() in SEAT_PERSONAS]
    if not valid:
        raise ValueError(f"No valid seats. Available: {list(SEAT_PERSONAS.keys())}")
    return valid


def _merge_scored_claims(source: list[dict[str, Any]], scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = []
    for original, score in zip(source, scored):
        item = dict(original)
        item["_score"] = float(score.get("score", 0.0) or 0.0)
        item["_tier"] = score.get("tier", "unverified")
        item["_explanation"] = score.get("explanation", "")
        item["bluff_gate"] = score.get("bluff_gate")
        item["bid_gate"] = score.get("bid_gate")
        merged.append(item)
    return merged


def _derive_verdict(score_result: dict[str, Any]) -> str:
    tiers = score_result.get("tier_distribution", {})
    avg = float(score_result.get("average_score", 0.0) or 0.0)
    credible = tiers.get("credible", 0)
    rejected = tiers.get("rejected", 0)
    unverified = tiers.get("unverified", 0)
    conditional = tiers.get("conditional", 0)

    if rejected > credible and avg < 0.45:
        return "rejected"
    if unverified > credible + conditional:
        return "unverified"
    if credible >= max(1, conditional + unverified + rejected) and avg >= 0.68:
        return "credible"
    return "conditional"


def _derive_confidence(score_result: dict[str, Any], seats: list[str]) -> int:
    avg = float(score_result.get("average_score", 0.0) or 0.0)
    tiers = score_result.get("tier_distribution", {})
    total = max(1, int(score_result.get("total_claims", 0) or 0))
    credible_ratio = tiers.get("credible", 0) / total
    seat_bonus = min(len(seats), 9) * 1.5
    confidence = 45 + avg * 35 + credible_ratio * 12 + seat_bonus
    return int(max(35, min(96, round(confidence))))


def _seat_scores(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        grouped.setdefault(claim["_seat"], []).append(claim)

    rows = []
    for seat, items in grouped.items():
        scores = [float(i.get("_score", 0.0) or 0.0) for i in items]
        tiers: dict[str, int] = {}
        for item in items:
            tiers[item.get("_tier", "unverified")] = tiers.get(item.get("_tier", "unverified"), 0) + 1
        persona = SEAT_PERSONAS[seat]
        rows.append({
            "seat": seat,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claims_count": len(items),
            "average_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "tiers": tiers,
            "strength": persona["strength"],
            "weakness": persona["weakness"],
        })
    rows.sort(key=lambda r: r["average_score"], reverse=True)
    return rows


def _top_reasons(claims: list[dict[str, Any]], verdict: str) -> list[str]:
    reverse = verdict == "rejected"
    ranked = sorted(claims, key=lambda c: float(c.get("_score", 0.0) or 0.0), reverse=not reverse)
    reasons = []
    for claim in ranked[:3]:
        reasons.append(f"{claim.get('seat_name', claim.get('_seat'))}: {claim.get('claim')}")
    return reasons


def _next_steps(verdict: str, mode: str) -> list[str]:
    if verdict == "credible":
        return [
            "Proceed, but keep one independent evidence check before irreversible action.",
            "Save this verdict and compare it with a future Standard or Strategic run if stakes increase.",
        ]
    if verdict == "rejected":
        return [
            "Do not act on the proposal in its current form.",
            "Rewrite the question with concrete constraints and rerun Standard mode.",
        ]
    if verdict == "unverified":
        return [
            "Collect missing facts, numbers, or source links before deciding.",
            "Rerun with Standard mode after evidence is available.",
        ]
    steps = [
        "Treat the result as usable direction, not final authorization.",
        "Validate the top risk before committing money, reputation, or irreversible effort.",
    ]
    if mode == "flash":
        steps.append("Upgrade to Standard or Strategic mode if the decision matters.")
    return steps


def _one_liner(verdict: str, question: str, confidence: int) -> str:
    label = VERDICT_LABELS.get(verdict, verdict)
    return f"{label}。当前对“{question[:60]}”的自动陪审置信度为 {confidence}%。"


def _summary_text(question: str, mode: str, verdict: str, confidence: int, reasons: list[str]) -> str:
    lines = [
        f"AI Judge v3.4 自动判词",
        f"问题：{question}",
        f"模式：{mode}",
        f"结论：{VERDICT_LABELS.get(verdict, verdict)}",
        f"置信度：{confidence}%",
        "",
        "关键理由：",
    ]
    lines.extend(f"- {r}" for r in reasons)
    return "\n".join(lines)


def _seat_base(question: str, seat: str, mode: str) -> float:
    q_len_bonus = min(len(question), 220) / 220 * 0.08
    mode_bonus = {"flash": 0.0, "standard": 0.045, "strategic": 0.075}.get(mode, 0.03)
    return _clamp(0.54 + q_len_bonus + mode_bonus + _stable_float(question, seat, mode) * 0.20)


def _stable_float(*parts: str) -> float:
    raw = "::".join(parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:12]
    return int(digest, 16) / float(0xFFFFFFFFFFFF)


def _stance_word(score: float) -> str:
    if score >= 0.72:
        return "directionally strong"
    if score >= 0.62:
        return "promising but conditional"
    if score >= 0.50:
        return "uncertain and evidence-dependent"
    return "weak"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


if __name__ == "__main__":
    sample = run_auto_jury("Should we ship AI Judge v3.4 this week?", mode="flash", run_id="demo")
    print(format_verdict_markdown(sample))
