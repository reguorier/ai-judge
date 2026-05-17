#!/usr/bin/env python3
# ruff: noqa: E402
"""Web-seat backed AI Judge execution."""

from __future__ import annotations

import hashlib
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from bridges.web_seat_bridge import run_web_seats
from core.auto_jury import assemble_verdict
from core.modes import resolve_mode
from core.scoring_v2 import score_claim_v2
from core.seat_personas import SEAT_PERSONAS


def run_web_jury(
    question: str,
    mode: str = "flash",
    seats: list[str] | None = None,
    run_id: str | None = None,
    display_question: str | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    evidence_options: dict[str, Any] | None = None,
    collect_followups: bool = False,
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Collect live web-seat responses and score them into a verdict."""
    question = question.strip()
    if not question:
        raise ValueError("question is required")

    config = resolve_mode(mode, override_seats=seats)
    resolved_seats = [seat for seat in config["seats"] if seat in SEAT_PERSONAS]
    if trace:
        trace("jury", "web_jury_start", "进入网页陪审收集", {"mode": mode, "seats": resolved_seats})
    raw_results = run_web_seats(question=question, seats=resolved_seats, mode=mode, progress=progress, trace=trace)
    mentor_supplements: list[dict[str, Any]] = []
    if collect_followups:
        mentor_supplements = collect_resonance_followups(
            question=question,
            mode=mode,
            raw_results=raw_results,
            progress=progress,
            trace=trace,
        )
    elif trace:
        trace("resonance", "followups_deferred", "二轮共振不自动重新发题，保留给显式采补动作", {
            "successful_seats": sum(1 for item in raw_results if item.get("ok")),
            "method": "manual_or_existing_page_recovery_only",
        })
    verdict = assemble_web_verdict_from_raw_results(
        question=question,
        mode=mode,
        seats=resolved_seats,
        raw_results=raw_results,
        mentor_supplements=mentor_supplements,
        external_evidence=external_evidence,
        run_id=run_id,
        display_question=display_question,
        trace=trace,
    )
    if evidence_options:
        verdict.setdefault("web_bridge", {})["evidence_options"] = dict(evidence_options)
    return verdict


def assemble_web_verdict_from_raw_results(
    question: str,
    mode: str,
    seats: list[str],
    raw_results: list[dict[str, Any]],
    mentor_supplements: list[dict[str, Any]] | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    run_id: str | None = None,
    display_question: str | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Score already-collected web-seat responses into a verdict."""
    resolved_seats = [seat for seat in seats if seat in SEAT_PERSONAS]
    mentor_supplements = mentor_supplements or []
    external_evidence = external_evidence or []
    primary_claims = build_web_claims(question=question, mode=mode, results=raw_results)
    mentor_claims = build_mentor_supplement_claims(question=question, mode=mode, supplements=mentor_supplements)
    deliberation = build_web_deliberation(question=question, mode=mode, results=raw_results)
    claims = primary_claims + mentor_claims + deliberation["claims"]
    ok_count = sum(1 for item in raw_results if item.get("ok"))
    failed_count = sum(1 for item in raw_results if not item.get("ok"))
    mentor_ok_count = sum(1 for item in mentor_supplements if item.get("ok"))
    if trace:
        trace("jury", "web_jury_collected", "网页席位收集完成，进入答案总结与互评", {
            "ok_count": ok_count,
            "failed_count": failed_count,
            "primary_claim_count": len(primary_claims),
            "mentor_supplement_count": len(mentor_supplements),
            "mentor_ok_count": mentor_ok_count,
        })
        trace("jury", "web_deliberation_built", "答案总结、交叉互评与评分 claims 已生成", {
            "summary_claim_count": deliberation.get("summary_claim_count"),
            "peer_review_count": deliberation.get("peer_review_count"),
            "total_claim_count": len(claims),
        })
    report_question = (display_question or question).strip()
    verdict = assemble_verdict(
        question=report_question,
        mode=mode,
        seats=resolved_seats,
        claims=claims,
        run_id=run_id,
        engine="isolated-web-seat-bridge-v3.4",
        extra={
            "web_bridge": {
                "raw_results": raw_results,
                "ok_count": ok_count,
                "failed_count": failed_count,
                "requested_count": len(raw_results),
                "collection_complete": failed_count == 0 and ok_count == len(raw_results),
                "supplementable_seats": _supplementable_seats(raw_results),
                "mentor_supplements": _public_mentor_supplements(mentor_supplements),
                "external_evidence": external_evidence,
                "deliberation": _public_deliberation(deliberation),
                "isolation": {
                    "uses_system_mouse": False,
                    "uses_system_keyboard": False,
                    "uses_system_clipboard": False,
                    "raw_model_answers": "web_bridge.raw_results[].response",
                    "mentor_supplements": "web_bridge.mentor_supplements",
                    "external_evidence": "web_bridge.external_evidence",
                    "rule": "原文、导师补充、外部证据三层隔离；任何层的内容不得覆盖另一层原文。",
                },
                "governance": {
                    "judge_role": "summarize_stat_score_only",
                    "model_role": "participant_and_peer_supervisor",
                    "trust_gate": "majority_confirmation_after_blind_cross_validation",
                    "blind_review": {
                        "status": "contract_recorded",
                        "rule": "最终可信源必须先保留席位原文，再进入不记名交叉验证；多数席位确认后才提升为可信共识。",
                    },
                },
                "pipeline": {
                    "version": "web-jury-v3.4-full",
                    "phases": [
                        {"id": "collect_web_answers", "label": "网页席位收集", "count": len(raw_results)},
                        {"id": "extract_resonance_questions", "label": "席位共振提问", "count": _mentor_question_count(mentor_supplements)},
                        {"id": "collect_mentor_supplements", "label": "二轮共振方案", "count": mentor_ok_count},
                        {"id": "summarize_answers", "label": "答案总结", "count": deliberation.get("summary_claim_count", 0)},
                        {"id": "peer_review", "label": "席位互评", "count": deliberation.get("peer_review_count", 0)},
                        {"id": "score_claims_v2", "label": "评分引擎 v2", "count": len(claims)},
                    ],
                    "scoring_engine": "core.scoring_v2.score_jury_v2",
                },
            }
        },
    )
    if _bridge_collection_insufficient(raw_results, ok_count, failed_count, len(raw_results)):
        verdict.update(_bridge_incomplete_fields(raw_results, ok_count, failed_count))
    _attach_web_judge_explainability(verdict, report_question, raw_results, deliberation)
    return verdict


def collect_resonance_followups(
    question: str,
    mode: str,
    raw_results: list[dict[str, Any]],
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    """Ask each successful seat to answer its own resonance questions."""
    prompts = build_resonance_followup_prompts(question, raw_results)
    if not prompts:
        if trace:
            trace("resonance", "no_followup_prompts", "没有可进入二轮共振的席位", {})
        return []

    supplements: list[dict[str, Any]] = []
    total = max(1, len(prompts))
    for index, prompt in enumerate(prompts, 1):
        seat = str(prompt.get("seat") or "")
        if progress:
            progress(f"二轮共振追问：{seat} ({index}/{total})", 0.72 + 0.02 * index / total)
        if trace:
            trace("resonance", "followup_start", f"{seat} 开始二轮共振追问", {
                "seat": seat,
                "question_count": len(prompt.get("questions") or []),
            })

        def followup_progress(step: str, pct: float) -> None:
            if not progress:
                return
            pct = max(0.0, min(1.0, pct))
            mapped = 0.74 + 0.14 * ((index - 1) + pct) / total
            progress(f"二轮共振 {index}/{total}：{step}", min(0.90, mapped))

        try:
            results = run_web_seats(
                question=str(prompt.get("prompt") or ""),
                seats=[seat],
                mode=mode,
                progress=followup_progress,
                trace=trace,
            )
            item = dict(results[0]) if results else _empty_mentor_result(seat, "empty_followup_result")
        except Exception as exc:
            item = _empty_mentor_result(seat, "followup_collection_error", str(exc))

        item["round"] = "mentor_resonance_followup"
        item["source_round"] = "raw_answer"
        item["source_questions"] = prompt.get("questions") or []
        item["source_answer_preview"] = prompt.get("source_answer_preview")
        item["prompt"] = prompt.get("prompt")
        supplements.append(item)
        if trace:
            trace("resonance", "followup_complete", f"{seat} 二轮共振追问完成", {
                "seat": seat,
                "ok": item.get("ok"),
                "response_chars": len(str(item.get("response") or "")),
                "error": item.get("error"),
            })
    if progress:
        progress("二轮共振补充完成，进入评分", 0.90)
    return supplements


def build_resonance_followup_prompts(question: str, raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompts: list[dict[str, Any]] = []
    for item in raw_results:
        if not item.get("ok"):
            continue
        seat = str(item.get("seat") or "").lower()
        if seat not in SEAT_PERSONAS:
            continue
        response = str(item.get("response") or "")
        questions = extract_resonance_questions(response)
        if not questions:
            questions = _fallback_resonance_questions(question, response)
        prompt = _build_resonance_followup_prompt(question, seat, response, questions)
        prompts.append({
            "seat": seat,
            "seat_name": item.get("seat_name") or SEAT_PERSONAS[seat]["name"],
            "questions": questions,
            "source_answer_preview": _compact(response, 420),
            "prompt": prompt,
        })
    return prompts


def extract_resonance_questions(response: str, limit: int = 5) -> list[str]:
    """Extract explicit resonance questions from a model answer."""
    text = response.strip()
    if not text:
        return []
    lines = [line.strip(" \t-•*#0123456789.、)") for line in text.splitlines()]
    questions: list[str] = []
    in_resonance = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if re.search(r"共振提问|反问|关键问题|追问|需要澄清", line):
            in_resonance = True
            question_part = re.sub(r"^(共振提问|反问|关键问题|追问|需要澄清)[:：]?", "", line).strip()
            if question_part and _looks_like_question(question_part):
                questions.append(question_part)
            continue
        if in_resonance and _looks_like_question(line):
            questions.append(line)
        elif in_resonance and len(questions) >= 1 and re.match(r"^(结论|方案|风险|下一步|理由)[:：]", line):
            break
        if len(questions) >= limit:
            break
    if len(questions) < 3:
        for match in re.findall(r"[^。！？?\n]{6,120}[？?]", text):
            candidate = match.strip()
            if candidate not in questions:
                questions.append(candidate)
            if len(questions) >= limit:
                break
    return list(dict.fromkeys(questions))[:limit]


def build_mentor_supplement_claims(
    question: str,
    mode: str,
    supplements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for item in supplements:
        seat = str(item.get("seat", "")).lower()
        if seat not in SEAT_PERSONAS:
            continue
        persona = SEAT_PERSONAS[seat]
        ok = bool(item.get("ok"))
        response = str(item.get("response") or "")
        questions = item.get("source_questions") or []
        base = _response_base(question, mode, seat, response, ok)
        if ok:
            claim_text = (
                f"{persona['name']} 二轮共振方案：基于 {len(questions)} 个自提问题补充，"
                f"{_compact(response)}"
            )
        else:
            error = item.get("error") or {}
            claim_text = (
                f"{persona['name']} 二轮共振方案未完成：{error.get('code', 'unknown')} - "
                f"{error.get('message', 'No response captured.')}"
            )
        claims.append({
            "_seat": seat,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claim_id": f"{seat}-mentor-resonance-followup",
            "claim": claim_text,
            "source_authority": _clamp(base + (0.04 if ok else 0.0)),
            "evidence_strength": max(0.12, base - (0.06 if ok else 0.20)),
            "evidence_count": min(6, max(1 if ok else 0, len(questions) + (2 if len(response) > 600 else 0))),
            "evidence_quality": max(0.10, base - 0.04),
            "freshness": 0.84 if ok else 0.20,
            "reproducibility": 0.66 if ok else 0.15,
            "historical_reliability": 0.62 if ok else 0.25,
            "confidence": max(0.10, base - (0.00 if ok else 0.22)),
            "risk_penalty": _risk_penalty(persona.get("risk_preference", "moderate"), ok),
            "web_ok": ok,
            "deliberation_phase": "mentor_supplement",
            "source_questions": questions,
        })
    return claims


def build_web_claims(question: str, mode: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw web responses into scoring-engine claims."""
    claims: list[dict[str, Any]] = []
    for item in results:
        seat = str(item.get("seat", "")).lower()
        if seat not in SEAT_PERSONAS:
            continue
        persona = SEAT_PERSONAS[seat]
        ok = bool(item.get("ok"))
        response = str(item.get("response") or "")
        base = _response_base(question, mode, seat, response, ok)
        risk_penalty = _risk_penalty(persona.get("risk_preference", "moderate"), ok)
        if ok:
            claim_text = f"{persona['name']} 网页席位：{_compact(response)}"
        else:
            error = item.get("error") or {}
            status = "慢生成待回收" if _is_slow_supplementable(item) else "未完成"
            claim_text = (
                f"{persona['name']} 网页席位{status}：{error.get('code', 'unknown')} - "
                f"{error.get('message', 'No response captured.')}"
            )

        claims.append({
            "_seat": seat,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claim_id": f"{seat}-web-main",
            "claim": claim_text,
            "source_authority": base,
            "evidence_strength": max(0.12, base - (0.10 if ok else 0.20)),
            "evidence_count": 3 if ok and len(response) > 600 else (1 if ok else 0),
            "evidence_quality": max(0.10, base - 0.08),
            "freshness": 0.86 if ok else 0.20,
            "reproducibility": 0.62 if ok else 0.15,
            "historical_reliability": 0.64 if ok else 0.25,
            "confidence": max(0.10, base - (0.02 if ok else 0.22)),
            "risk_penalty": risk_penalty,
            "web_ok": ok,
        })
    return claims


def build_web_deliberation(question: str, mode: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the answer-summary and peer-review layer before final scoring."""
    ok_cards = [
        _answer_card(question, item)
        for item in results
        if item.get("ok") and str(item.get("seat", "")).lower() in SEAT_PERSONAS
    ]
    failed = [item for item in results if not item.get("ok")]
    peer_reviews: list[dict[str, Any]] = []
    for reviewer in ok_cards:
        for target in ok_cards:
            if reviewer["seat"] == target["seat"]:
                continue
            peer_reviews.append(_peer_review(question, reviewer, target))

    grouped_reviews: dict[str, list[dict[str, Any]]] = {}
    for review in peer_reviews:
        grouped_reviews.setdefault(review["target"], []).append(review)

    answer_summaries: list[dict[str, Any]] = []
    for card in ok_cards:
        reviews = grouped_reviews.get(card["seat"], [])
        avg_peer_score = round(sum(float(r["score"]) for r in reviews) / len(reviews), 4) if reviews else None
        answer_summaries.append({
            "seat": card["seat"],
            "seat_name": card["seat_name"],
            "stance": card["stance"],
            "quality": card["quality"],
            "evidence_count": card["evidence_count"],
            "risk_count": card["risk_count"],
            "review_count": len(reviews),
            "avg_peer_score": avg_peer_score,
            "summary": card["summary"],
        })

    claims = _deliberation_claims(question=question, mode=mode, answer_cards=ok_cards, peer_reviews=peer_reviews)
    stance_counts = Counter(card["stance"] for card in ok_cards)
    agreements = _shared_terms(ok_cards, limit=8)
    disagreements = _disagreement_notes(answer_summaries)
    return {
        "version": "web-deliberation-v1",
        "ok_count": len(ok_cards),
        "failed_count": len(failed),
        "stance_distribution": dict(stance_counts),
        "agreements": agreements,
        "disagreements": disagreements,
        "answer_summaries": answer_summaries,
        "peer_reviews": peer_reviews,
        "peer_review_count": len(peer_reviews),
        "summary_claim_count": len(ok_cards),
        "claims": claims,
        "claim_count": len(claims),
    }


def _public_deliberation(deliberation: dict[str, Any]) -> dict[str, Any]:
    """Keep report JSON useful without duplicating every scoring claim twice."""
    return {
        "version": deliberation.get("version"),
        "ok_count": deliberation.get("ok_count", 0),
        "failed_count": deliberation.get("failed_count", 0),
        "stance_distribution": deliberation.get("stance_distribution", {}),
        "agreements": deliberation.get("agreements", []),
        "disagreements": deliberation.get("disagreements", []),
        "answer_summaries": deliberation.get("answer_summaries", []),
        "peer_reviews": deliberation.get("peer_reviews", []),
        "peer_review_count": deliberation.get("peer_review_count", 0),
        "summary_claim_count": deliberation.get("summary_claim_count", 0),
        "claim_count": deliberation.get("claim_count", 0),
    }


def _attach_web_judge_explainability(
    verdict: dict[str, Any],
    question: str,
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any],
) -> None:
    """Attach product-level explainability artifacts to a web verdict."""
    bridge = verdict.setdefault("web_bridge", {})
    scored_claims = list(verdict.get("claims") or [])
    score_rounds = build_score_rounds(scored_claims)
    seat_digest = build_seat_answer_digest(raw_results, deliberation, verdict.get("seat_scores", []))
    mentor_supplements = bridge.get("mentor_supplements") or []
    judge_answer = build_judge_answer(question, verdict, raw_results, deliberation, seat_digest, mentor_supplements=mentor_supplements)
    single_baseline = build_single_judge_baseline(question, judge_answer, deliberation, raw_results, verdict)

    bridge["score_rounds"] = score_rounds
    bridge["seat_answer_digest"] = seat_digest
    verdict["judge_answer"] = judge_answer
    verdict["single_judge_baseline"] = single_baseline


def build_score_rounds(scored_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group scored claims by AI Judge round so the report can show score movement."""
    phases = [
        ("raw_answer", "第一轮：网页原始回答评分", lambda claim: not claim.get("deliberation_phase")),
        ("mentor_supplement", "第二轮：共振追问方案评分", lambda claim: claim.get("deliberation_phase") == "mentor_supplement"),
        ("answer_summary", "第三轮：答案总结评分", lambda claim: claim.get("deliberation_phase") == "answer_summary"),
        ("peer_review", "第四轮：席位互评评分", lambda claim: claim.get("deliberation_phase") == "peer_review"),
    ]
    rounds: list[dict[str, Any]] = []
    for phase_id, label, predicate in phases:
        claims = [claim for claim in scored_claims if predicate(claim)]
        if not claims:
            rounds.append({
                "id": phase_id,
                "label": label,
                "claim_count": 0,
                "average_score": None,
                "seat_scores": [],
                "top_claims": [],
            })
            continue
        scores = [float(claim.get("_score", 0.0) or 0.0) for claim in claims]
        rounds.append({
            "id": phase_id,
            "label": label,
            "claim_count": len(claims),
            "average_score": round(sum(scores) / len(scores), 4),
            "seat_scores": _round_seat_scores(claims),
            "top_claims": _round_top_claims(claims),
        })
    return rounds


def build_seat_answer_digest(
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any],
    seat_scores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create a compact, linkable digest for every model's answer, pros, and cons."""
    summaries = {str(item.get("seat")): item for item in deliberation.get("answer_summaries", [])}
    score_by_seat = {str(item.get("seat")): item for item in seat_scores}
    digest: list[dict[str, Any]] = []
    for item in raw_results:
        seat = str(item.get("seat") or "")
        persona = SEAT_PERSONAS.get(seat, {})
        summary = summaries.get(seat, {})
        score = score_by_seat.get(seat, {})
        response = str(item.get("response") or "")
        ok = bool(item.get("ok"))
        digest.append({
            "seat": seat,
            "seat_name": item.get("seat_name") or persona.get("name", seat),
            "ok": ok,
            "status": "已返回" if ok else ("待回收" if _is_slow_supplementable(item) else "未完成"),
            "score": score.get("average_score"),
            "claims_count": score.get("claims_count", 0),
            "stance": summary.get("stance") or ("慢生成待回收" if _is_slow_supplementable(item) else ("未返回" if not ok else "待归类")),
            "quality": summary.get("quality"),
            "avg_peer_score": summary.get("avg_peer_score"),
            "answer_preview": _compact(response, 260) if ok else _error_summary(item),
            "response": response,
            "pros": _seat_pros(item, summary, score, persona),
            "cons": _seat_cons(item, summary, score, persona),
            "strength": persona.get("strength", ""),
            "weakness": persona.get("weakness", ""),
            "error": item.get("error"),
        })
    return digest


def build_judge_answer(
    question: str,
    verdict: dict[str, Any],
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any],
    seat_digest: list[dict[str, Any]],
    mentor_supplements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate AI Judge's own synthesized judge answer from collected seats."""
    ok_count = sum(1 for item in raw_results if item.get("ok"))
    total = len(raw_results)
    failed_count = total - ok_count
    pending_count = sum(1 for item in raw_results if _is_slow_supplementable(item))
    stance_distribution = deliberation.get("stance_distribution") or {}
    dominant_stance = _dominant_stance(stance_distribution)
    ranked = sorted(
        [item for item in seat_digest if item.get("ok")],
        key=lambda item: float(item.get("score") or item.get("quality") or 0.0),
        reverse=True,
    )
    top_names = [str(item.get("seat_name")) for item in ranked[:3]]
    agreements = deliberation.get("agreements") or []
    disagreements = deliberation.get("disagreements") or []
    mentor_supplements = mentor_supplements or []
    mentor_ok_count = sum(1 for item in mentor_supplements if item.get("ok"))
    if ok_count <= 0:
        final_answer = "AI Judge 法官答案：信息不足。网页席位没有返回可用答案，因此不能给出问题本身的实质判决。"
    else:
        if failed_count == 0:
            completeness = "完整收集"
        elif pending_count == failed_count:
            completeness = f"已先完成 {ok_count}/{total} 席，另有 {pending_count} 席慢生成待回收"
        else:
            completeness = f"只完成 {ok_count}/{total} 席"
        final_answer = (
            f"AI Judge 法官答案：当前为{verdict.get('verdict_label', verdict.get('verdict'))}。"
            f"本轮{completeness}，主导立场是“{dominant_stance}”。"
            f"我会优先采纳 {', '.join(top_names) or '已返回席位'} 的共同部分，"
            f"把“{', '.join(agreements[:5]) or '共识不足'}”作为初步共识；"
            f"二轮共振补充已回收 {mentor_ok_count}/{len(mentor_supplements)} 席，"
            f"若存在未返回席位或低证据回答，则最终结论只作为阶段性判断。"
        )
    return {
        "label": "AI Judge 法官综合答案",
        "question": question,
        "answer": final_answer,
        "ok_count": ok_count,
        "failed_count": failed_count,
        "dominant_stance": dominant_stance,
        "top_seats": top_names,
        "agreements": agreements[:8],
        "disagreements": disagreements[:8],
        "mentor_supplement_count": len(mentor_supplements),
        "mentor_supplement_ok_count": mentor_ok_count,
        "limits": _judge_limits(failed_count, total, ranked, pending_count=pending_count),
    }


def build_single_judge_baseline(
    question: str,
    judge_answer: dict[str, Any],
    deliberation: dict[str, Any],
    raw_results: list[dict[str, Any]],
    verdict: dict[str, Any],
) -> dict[str, Any]:
    """Score the same run as if AI Judge were a single summarizing model."""
    answer_text = str(judge_answer.get("answer") or "")
    answer_summaries = deliberation.get("answer_summaries") or []
    avg_quality = (
        sum(float(item.get("quality", 0.0) or 0.0) for item in answer_summaries) / len(answer_summaries)
        if answer_summaries else 0.25
    )
    ok_count = sum(1 for item in raw_results if item.get("ok"))
    total = max(1, len(raw_results))
    completeness = ok_count / total
    evidence_count = min(8, sum(int(item.get("evidence_count", 0) or 0) for item in answer_summaries))
    scored = score_claim_v2(
        claim=f"AI Judge 单模型基准：{answer_text}",
        source_authority=_clamp(0.46 + 0.24 * completeness + 0.16 * avg_quality),
        evidence_strength=_clamp(0.36 + 0.30 * avg_quality + 0.16 * completeness),
        evidence_count=evidence_count,
        evidence_quality=_clamp(0.34 + 0.42 * avg_quality),
        freshness=0.80,
        reproducibility=_clamp(0.38 + 0.28 * completeness),
        historical_reliability=0.58,
        confidence=_clamp(0.40 + 0.34 * avg_quality + 0.12 * completeness),
        risk_penalty=0.06 if completeness >= 0.9 else 0.11,
    )
    council_score = float(verdict.get("average_score", 0.0) or 0.0)
    single_score = float(scored.get("score", 0.0) or 0.0)
    return {
        "label": "AI Judge 单模型基准",
        "answer": answer_text,
        "score": round(single_score, 4),
        "tier": scored.get("tier"),
        "explanation": scored.get("explanation"),
        "council_average_score": round(council_score, 4),
        "delta_vs_council": round(council_score - single_score, 4),
        "comparison": [
            {"metric": "答案来源", "single_judge": "法官汇总后的单一答案", "council": f"{ok_count}/{total} 个网页席位原始答案"},
            {"metric": "互评校验", "single_judge": "无模型间互评", "council": f"{int(deliberation.get('peer_review_count', 0))} 条席位互评"},
            {"metric": "可追溯性", "single_judge": "只能追到汇总文本", "council": "可追到每个席位原文、摘要、互评和 claim 分数"},
        ],
    }


def _round_seat_scores(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        grouped.setdefault(str(claim.get("_seat") or ""), []).append(claim)
    rows: list[dict[str, Any]] = []
    for seat, items in grouped.items():
        scores = [float(item.get("_score", 0.0) or 0.0) for item in items]
        tiers: dict[str, int] = {}
        for item in items:
            tier = str(item.get("_tier") or "unverified")
            tiers[tier] = tiers.get(tier, 0) + 1
        rows.append({
            "seat": seat,
            "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
            "claim_count": len(items),
            "average_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "tiers": tiers,
        })
    rows.sort(key=lambda row: float(row.get("average_score", 0.0) or 0.0), reverse=True)
    return rows


def _round_top_claims(claims: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    ranked = sorted(claims, key=lambda claim: float(claim.get("_score", 0.0) or 0.0), reverse=True)
    return [
        {
            "claim_id": claim.get("claim_id"),
            "seat": claim.get("_seat"),
            "seat_name": claim.get("seat_name"),
            "score": round(float(claim.get("_score", 0.0) or 0.0), 4),
            "tier": claim.get("_tier"),
            "phase": claim.get("deliberation_phase") or "raw_answer",
            "review_target": claim.get("review_target"),
            "claim": _compact(str(claim.get("claim") or ""), 260),
        }
        for claim in ranked[:limit]
    ]


def _error_summary(item: dict[str, Any]) -> str:
    error = item.get("error") or {}
    if _is_slow_supplementable(item):
        return f"慢席待回收: {error.get('message', '仍在生成或等待旧页面答案回收。')}"
    return f"{error.get('code', 'unknown')}: {error.get('message', 'No response captured.')}"


def _seat_pros(
    item: dict[str, Any],
    summary: dict[str, Any],
    score: dict[str, Any],
    persona: dict[str, Any],
) -> list[str]:
    if not item.get("ok"):
        if _is_slow_supplementable(item):
            return ["该席位被标记为慢生成，可通过旧页面答案回收按钮读取，不会污染当前结论。"]
        return ["失败原因被保留，未混入最终结论。"]
    pros = [str(persona.get("strength") or "该席位提供了独立回答。")]
    quality = float(summary.get("quality", 0.0) or 0.0)
    evidence_count = int(summary.get("evidence_count", 0) or 0)
    peer_score = summary.get("avg_peer_score")
    final_score = float(score.get("average_score", 0.0) or 0.0)
    if quality >= 0.62:
        pros.append("答案结构、相关性和证据密度较好。")
    if evidence_count >= 3:
        pros.append("包含较多可核查依据或明确假设。")
    if peer_score is not None and float(peer_score) >= 0.62:
        pros.append("在席位互评中获得较高认可。")
    if final_score >= 0.62:
        pros.append("综合评分进入可采纳区间。")
    return list(dict.fromkeys(pros))[:4]


def _seat_cons(
    item: dict[str, Any],
    summary: dict[str, Any],
    score: dict[str, Any],
    persona: dict[str, Any],
) -> list[str]:
    if not item.get("ok"):
        if _is_slow_supplementable(item):
            return [_error_summary(item), "该席位尚未进入实质互评，旧页面答案回收成功后会回填评分与共识。"]
        return [_error_summary(item), "该席位没有进入实质互评，只作为基础设施失败记录。"]
    cons = [str(persona.get("weakness") or "仍需人工复核关键假设。")]
    evidence_count = int(summary.get("evidence_count", 0) or 0)
    risk_count = int(summary.get("risk_count", 0) or 0)
    peer_score = summary.get("avg_peer_score")
    final_score = float(score.get("average_score", 0.0) or 0.0)
    if evidence_count <= 1:
        cons.append("证据密度偏低，可能是流畅但不可验证的回答。")
    if risk_count == 0:
        cons.append("缺少风险、前提或边界条件提示。")
    if peer_score is not None and float(peer_score) < 0.50:
        cons.append("互评认可度偏低，需要二次追问。")
    if final_score < 0.45:
        cons.append("综合评分偏低，不宜单独采纳。")
    return list(dict.fromkeys(cons))[:4]


def _dominant_stance(stance_distribution: dict[str, Any]) -> str:
    if not stance_distribution:
        return "信息不足"
    return max(stance_distribution.items(), key=lambda item: int(item[1] or 0))[0]


def _judge_limits(
    failed_count: int,
    total: int,
    ranked_digest: list[dict[str, Any]],
    pending_count: int = 0,
) -> list[str]:
    limits: list[str] = []
    hard_failed = max(0, failed_count - pending_count)
    if pending_count:
        limits.append(f"{pending_count}/{total} 个席位仍在慢生成待回收，当前结论先按已返回席位给出。")
    if hard_failed:
        limits.append(f"{hard_failed}/{total} 个席位未返回完整答案，最终结论必须标记为阶段性。")
    if len(ranked_digest) <= 1:
        limits.append("可用席位不足，互评和分歧检测的价值有限。")
    if ranked_digest and all(float(item.get("score") or 0.0) < 0.55 for item in ranked_digest):
        limits.append("返回席位的综合分都不高，应补充事实或改写问题后重跑。")
    return limits or ["本轮仍需人工核查关键事实、日期、金额、规则和不可逆决策点。"]


def _is_slow_supplementable(item: dict[str, Any]) -> bool:
    if item.get("ok"):
        return False
    error = item.get("error") or {}
    return bool(item.get("supplementable")) or str(error.get("code") or "") == "slow_response_pending"


def _looks_like_question(text: str) -> bool:
    lowered = text.lower()
    return (
        text.endswith(("?", "？"))
        or any(token in text for token in ("是否", "如何", "怎样", "什么", "哪些", "为何", "为什么", "能否", "要不要"))
        or any(token in lowered for token in ("how", "what", "why", "whether", "which"))
    )


def _fallback_resonance_questions(question: str, response: str) -> list[str]:
    topic = _compact(question, 80)
    response_has_code = bool(re.search(r"代码|接口|API|模块|架构|测试|部署|数据流|schema|endpoint", response, flags=re.I))
    questions = [
        f"如果我是用户，{topic} 的最小可验收交付物是什么？",
        "这个方案最容易被忽略的底层风险、桥接风险或验证盲点是什么？",
        "哪些原始模型回答、导师补充和外部证据必须隔离保存，才能避免用幻觉验证幻觉？",
    ]
    if response_has_code:
        questions.append("落地到代码时，应该新增或修改哪些模块、状态字段、接口和测试？")
    else:
        questions.append("如果要把这轮判断转成可执行路线图，第一周应该先做哪三个动作？")
    return questions[:5]


def _build_resonance_followup_prompt(question: str, seat: str, response: str, questions: list[str]) -> str:
    question_lines = "\n".join(f"{index}. {item}" for index, item in enumerate(questions, 1))
    persona = SEAT_PERSONAS.get(seat, {})
    return (
        "[AIJUDGE_RESONANCE_FOLLOWUP]\n"
        "你刚才作为 AI Judge 独立席位提出了共振提问。现在请你反问自己并回答。\n\n"
        f"用户原始任务：\n{question}\n\n"
        f"你的席位身份：{persona.get('name', seat)} / {persona.get('mbti', '')}\n"
        f"你的第一轮方案摘要：\n{_compact(response, 1800)}\n\n"
        "你提出的共振提问：\n"
        f"{question_lines}\n\n"
        "请针对以上问题，带入用户角色，给出你的二轮思考和详细技术方案。必须包含：\n"
        "- 对每个共振提问的回答\n"
        "- 你认为用户真正要达成的目标和验收标准\n"
        "- 详细技术方案：模块、数据结构、状态字段、接口、流程、异常处理\n"
        "- 执行路线：先做什么、后做什么、如何验证\n"
        "- 最大风险、反方意见、需要外部证据验证的点\n"
        "请明确标注事实、假设、建议，不要覆盖或改写第一轮原文。"
    )


def _empty_mentor_result(seat: str, code: str, message: str = "No resonance follow-up response was captured.") -> dict[str, Any]:
    return {
        "seat": seat,
        "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "ok": False,
        "url": "",
        "profile_dir": "",
        "elapsed_seconds": 0,
        "response": "",
        "error": {"code": code, "message": message},
    }


def _public_mentor_supplements(supplements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public: list[dict[str, Any]] = []
    for item in supplements:
        public.append({
            "seat": item.get("seat"),
            "seat_name": item.get("seat_name"),
            "ok": bool(item.get("ok")),
            "round": item.get("round"),
            "source_round": item.get("source_round"),
            "source_questions": item.get("source_questions") or [],
            "source_answer_preview": item.get("source_answer_preview"),
            "response": item.get("response") or "",
            "elapsed_seconds": item.get("elapsed_seconds"),
            "error": item.get("error"),
        })
    return public


def _mentor_question_count(supplements: list[dict[str, Any]]) -> int:
    return sum(len(item.get("source_questions") or []) for item in supplements)


def _supplementable_seats(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seats: list[dict[str, Any]] = []
    for item in results:
        if not _is_slow_supplementable(item):
            continue
        seats.append({
            "seat": item.get("seat"),
            "seat_name": item.get("seat_name"),
            "error": item.get("error"),
            "submitted_at": item.get("submitted_at"),
        })
    return seats


def _bridge_collection_insufficient(
    results: list[dict[str, Any]],
    ok_count: int,
    failed_count: int,
    total: int,
) -> bool:
    """Return whether the web run is an infrastructure failure, not a verdict."""
    if total <= 0:
        return True
    if failed_count <= 0:
        return False
    hard_failed = [item for item in results if not item.get("ok") and not _is_slow_supplementable(item)]
    if ok_count > 0 and not hard_failed:
        return False
    return ok_count < total or failed_count > 0


def _bridge_incomplete_fields(results: list[dict[str, Any]], ok_count: int, failed_count: int) -> dict[str, Any]:
    reasons: list[str] = []
    for item in results:
        if item.get("ok"):
            continue
        error = item.get("error") or {}
        seat_name = item.get("seat_name") or item.get("seat")
        code = error.get("code", "unknown")
        message = error.get("message", "No response captured.")
        prefix = "慢席待回收" if _is_slow_supplementable(item) else "未完成"
        reasons.append(f"{seat_name}: {prefix} / {code} - {message}")
        if len(reasons) >= 5:
            break
    if not reasons:
        reasons = ["网页桥接没有收集到足够独立答案。"]
    return {
        "verdict": "unverified",
        "verdict_label": "网页桥接未完成",
        "one_liner": f"网页桥接只拿到 {ok_count}/{len(results)} 个席位完整回答，{failed_count} 个席位未完成；这不是问题本身的判决。",
        "confidence": 0,
        "reasons": reasons,
        "next_steps": [
            "对慢生成席位使用旧页面答案回收按钮，只读取已打开页面的答案，成功后回填原始回答、互评和评分。",
            "逐席修复失败 adapter，直到本轮要求的所有网页席位都返回完整回答。",
            "对 send_button_not_found 的站点补充站点专用发送按钮选择器。",
            "对 transcript_pollution 的站点新建干净会话或强制使用答案包裹标记读取。",
        ],
    }


def _response_base(question: str, mode: str, seat: str, response: str, ok: bool) -> float:
    if not ok:
        return 0.26
    length_bonus = min(len(response), 2400) / 2400 * 0.16
    mode_bonus = {"flash": 0.0, "standard": 0.035, "strategic": 0.055}.get(mode, 0.02)
    stability = _stable_float(question, seat, response[:300]) * 0.08
    return min(0.88, 0.54 + length_bonus + mode_bonus + stability)


def _answer_card(question: str, item: dict[str, Any]) -> dict[str, Any]:
    seat = str(item.get("seat", "")).lower()
    persona = SEAT_PERSONAS[seat]
    response = str(item.get("response") or "")
    terms = _extract_terms(response)
    question_terms = set(_extract_terms(question))
    shared_question_terms = question_terms.intersection(terms)
    evidence_count = _evidence_count(response)
    risk_count = _risk_count(response)
    quality = _answer_quality(response, evidence_count, risk_count, len(shared_question_terms), len(question_terms))
    return {
        "seat": seat,
        "seat_name": persona["name"],
        "mbti": persona["mbti"],
        "response": response,
        "terms": terms,
        "quality": quality,
        "evidence_count": evidence_count,
        "risk_count": risk_count,
        "stance": _stance_label(response),
        "summary": _compact(response, 300),
    }


def _peer_review(question: str, reviewer: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    reviewer_terms = set(reviewer["terms"])
    target_terms = set(target["terms"])
    overlap = len(reviewer_terms.intersection(target_terms)) / max(1, min(len(reviewer_terms), len(target_terms)))
    evidence_bonus = min(0.18, float(target["evidence_count"]) * 0.035)
    risk_bonus = min(0.08, float(target["risk_count"]) * 0.02)
    overclaim_penalty = 0.10 if target["evidence_count"] == 0 and _overconfident(target["response"]) else 0.0
    diversity_bonus = 0.04 if reviewer["stance"] != target["stance"] else 0.0
    score = _clamp(0.30 + 0.42 * float(target["quality"]) + 0.16 * overlap + evidence_bonus + risk_bonus + diversity_bonus - overclaim_penalty)
    label = "强支持" if score >= 0.78 else "可采纳" if score >= 0.62 else "需复核" if score >= 0.46 else "低可信"
    comment = _peer_comment(reviewer, target, score, overlap, overclaim_penalty)
    return {
        "reviewer": reviewer["seat"],
        "reviewer_name": reviewer["seat_name"],
        "target": target["seat"],
        "target_name": target["seat_name"],
        "score": round(score, 4),
        "label": label,
        "overlap": round(overlap, 4),
        "comment": comment,
    }


def _deliberation_claims(
    question: str,
    mode: str,
    answer_cards: list[dict[str, Any]],
    peer_reviews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    mode_bonus = {"flash": 0.0, "standard": 0.035, "strategic": 0.055}.get(mode, 0.02)
    for card in answer_cards:
        persona = SEAT_PERSONAS[card["seat"]]
        quality = float(card["quality"])
        claims.append({
            "_seat": card["seat"],
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claim_id": f"{card['seat']}-answer-summary",
            "claim": f"{persona['name']} 答案总结：立场={card['stance']}；质量={quality:.2f}；摘要：{card['summary']}",
            "source_authority": _clamp(0.50 + quality * 0.32 + mode_bonus),
            "evidence_strength": _clamp(0.40 + quality * 0.35),
            "evidence_count": int(card["evidence_count"]),
            "evidence_quality": _clamp(0.38 + quality * 0.40),
            "freshness": 0.82,
            "reproducibility": _clamp(0.45 + min(0.25, len(card["terms"]) / 60)),
            "historical_reliability": _clamp(0.54 + _stable_float(question, card["seat"], "summary") * 0.24),
            "confidence": _clamp(0.45 + quality * 0.36),
            "risk_penalty": _risk_penalty(persona.get("risk_preference", "moderate"), True),
            "deliberation_phase": "answer_summary",
        })

    for review in peer_reviews:
        reviewer = str(review["reviewer"])
        persona = SEAT_PERSONAS[reviewer]
        score = float(review["score"])
        claims.append({
            "_seat": reviewer,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claim_id": f"{reviewer}-reviews-{review['target']}",
            "claim": f"{review['reviewer_name']} 互评 {review['target_name']}：{review['label']}，{review['comment']}",
            "source_authority": _clamp(0.46 + score * 0.34 + mode_bonus),
            "evidence_strength": _clamp(0.35 + score * 0.42),
            "evidence_count": 2 if score >= 0.62 else 1,
            "evidence_quality": _clamp(0.36 + score * 0.40),
            "freshness": 0.80,
            "reproducibility": _clamp(0.42 + float(review["overlap"]) * 0.35),
            "historical_reliability": _clamp(0.52 + _stable_float(question, reviewer, str(review["target"])) * 0.24),
            "confidence": _clamp(0.42 + score * 0.38),
            "risk_penalty": _risk_penalty(persona.get("risk_preference", "moderate"), True),
            "deliberation_phase": "peer_review",
            "review_target": review["target"],
        })
    return claims


def _extract_terms(text: str) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_+-]{2,}", text.lower())
    stop = {"以及", "但是", "如果", "因为", "所以", "这个", "一个", "the", "and", "for", "with", "that", "this"}
    return [token for token in tokens if token not in stop][:160]


def _evidence_count(text: str) -> int:
    patterns = [
        r"https?://",
        r"\d+(?:\.\d+)?\s*(?:%|年|月|日|美元|亿|万|场|次|分|kg|km)?",
        r"来源|依据|数据|报告|研究|统计|历史|规则|赛程|排名|赔率|假设|证据",
    ]
    return min(8, sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns))


def _risk_count(text: str) -> int:
    return min(6, len(re.findall(r"风险|不确定|假设|前提|限制|反例|可能|除非|需要验证|误差", text)))


def _answer_quality(response: str, evidence_count: int, risk_count: int, shared_terms: int, question_terms: int) -> float:
    length_score = min(len(response), 1800) / 1800
    evidence_score = min(evidence_count, 6) / 6
    risk_score = min(risk_count, 4) / 4
    relevance = shared_terms / max(1, min(question_terms, 18))
    structure = min(1.0, len(re.findall(r"(?:^|\n)\s*(?:[-*•]|\d+[.、]|[一二三四五六七八九十][、.])", response)) / 6)
    return round(_clamp(0.18 + 0.20 * length_score + 0.24 * evidence_score + 0.14 * risk_score + 0.16 * relevance + 0.08 * structure), 4)


def _stance_label(text: str) -> str:
    lowered = text.lower()
    if re.search(r"不建议|反对|不可行|失败|不要|低可信|unlikely|not likely", lowered):
        return "反对/谨慎"
    if re.search(r"建议|支持|可行|优先|看好|会|likely|should|recommend", lowered):
        return "支持/推进"
    if re.search(r"取决于|条件|如果|可能|不确定|需要验证|depends|conditional", lowered):
        return "条件/待验证"
    return "中性/信息型"


def _overconfident(text: str) -> bool:
    return bool(re.search(r"一定|必然|毫无疑问|绝对|肯定|guaranteed|certainly", text, flags=re.IGNORECASE))


def _peer_comment(reviewer: dict[str, Any], target: dict[str, Any], score: float, overlap: float, penalty: float) -> str:
    parts = []
    if overlap >= 0.42:
        parts.append("与自身答案有较高语义重合")
    elif overlap <= 0.16:
        parts.append("提供了明显不同视角")
    else:
        parts.append("与自身答案部分重合")
    if target["evidence_count"] >= 3:
        parts.append("证据/细节密度较高")
    else:
        parts.append("证据密度偏低")
    if target["risk_count"] >= 2:
        parts.append("有显式风险或前提检查")
    if penalty:
        parts.append("存在高确定性但低证据的过度断言风险")
    if score < 0.46:
        parts.append("建议进入人工复核或二次追问")
    return "；".join(parts) + "。"


def _shared_terms(cards: list[dict[str, Any]], limit: int = 8) -> list[str]:
    counts: Counter[str] = Counter()
    for card in cards:
        counts.update(set(card["terms"]))
    threshold = 2 if len(cards) >= 2 else 1
    return [term for term, count in counts.most_common(40) if count >= threshold][:limit]


def _disagreement_notes(answer_summaries: list[dict[str, Any]]) -> list[str]:
    if not answer_summaries:
        return []
    stance_groups: dict[str, list[str]] = {}
    for item in answer_summaries:
        stance_groups.setdefault(str(item["stance"]), []).append(str(item["seat_name"]))
    if len(stance_groups) <= 1:
        return ["席位立场整体同向，主要差异在证据密度和风险提示。"]
    return [
        f"{stance}: {', '.join(names)}"
        for stance, names in stance_groups.items()
    ]


def _risk_penalty(risk_preference: str, ok: bool) -> float:
    if not ok:
        return 0.16
    return {
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
    }.get(risk_preference, 0.05)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _compact(text: str, limit: int = 520) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."


def _stable_float(*parts: str) -> float:
    raw = "::".join(parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:12]
    return int(digest, 16) / float(0xFFFFFFFFFFFF)
