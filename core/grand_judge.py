#!/usr/bin/env python3
"""Grand Judge citation-verification MVP.

This is intentionally not a full Grand Judge. It only orchestrates citation
verification and replay sealing. Raw model answers remain immutable records.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from core.citation_validator import UNVERIFIABLE_EXPLANATION, summarize_citation_reports, validate_citations


def run_grand_judge_mvp(
    *,
    question: str,
    raw_answers: list[dict[str, Any]] | dict[str, Any],
    mentor_supplements: list[dict[str, Any]] | dict[str, Any] | None = None,
    external_evidence: list[dict[str, Any]] | dict[str, Any] | None = None,
    run_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Run the minimal citation-verification Grand Judge workflow."""
    verified_at = generated_at or datetime.now(timezone.utc).isoformat()
    answers = _normalize_answer_items(raw_answers)
    supplements_by_seat = _supplements_by_seat(mentor_supplements)

    ledger: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for index, answer in enumerate(answers, 1):
        seat = str(answer.get("seat") or f"seat-{index}").lower()
        raw_answer = str(answer.get("response") or answer.get("answer") or "")
        raw_report = validate_citations(
            raw_answer,
            question=question,
            external_evidence=external_evidence,
            generated_at=verified_at,
        )
        reports.append(raw_report)

        mentor = supplements_by_seat.get(seat)
        mentor_response = str((mentor or {}).get("response") or (mentor or {}).get("answer") or "")
        mentor_report = None
        if mentor_response:
            mentor_report = validate_citations(
                mentor_response,
                question=question,
                external_evidence=external_evidence,
                generated_at=verified_at,
            )
            reports.append(mentor_report)

        ledger.append({
            "ledger_id": f"LEDGER-{index:03d}",
            "seat": seat,
            "seat_name": answer.get("seat_name") or (mentor or {}).get("seat_name") or seat,
            "ok": bool(answer.get("ok")),
            "raw_answer": raw_answer,
            "raw_answer_hash": _hash_payload(raw_answer),
            "mentor_supplement": mentor_response,
            "mentor_supplement_hash": _hash_payload(mentor_response) if mentor_response else None,
            "citation_verification": raw_report,
            "mentor_citation_verification": mentor_report,
            "unverifiable_reasons": _unverifiable_reasons(raw_report, mentor_report),
            "verification_timestamp": verified_at,
            "source_isolation": {
                "raw_answer": "replay_ledger[].raw_answer",
                "mentor_supplement": "replay_ledger[].mentor_supplement",
                "external_evidence": "external_evidence_index",
                "rule": "Grand Judge 只汇总、统计、打分；不得改写模型原文。",
            },
        })

    summary = summarize_citation_reports(reports)
    evidence_index = _external_evidence_index(external_evidence)
    replay_ledger_hash = _hash_payload(ledger)
    certification_seed = {
        "run_id": run_id,
        "question": question,
        "summary": summary,
        "replay_ledger_hash": replay_ledger_hash,
        "external_evidence_hash": _hash_payload(evidence_index),
    }
    suffix = _hash_payload(certification_seed)[:10].upper()
    certification_id = f"CITE-{verified_at[:10].replace('-', '')}-{suffix}"
    report = {
        "schema": "grand_judge.citation_mvp.v1",
        "phase": "citation_verification_mvp",
        "run_id": run_id,
        "question": question,
        "certification_id": certification_id,
        "citation_verification": {
            **summary,
            "certification_id": certification_id,
            "replay_ledger_hash": replay_ledger_hash,
            "external_evidence_count": len(evidence_index),
        },
        "replay_ledger": ledger,
        "replay_ledger_hash": replay_ledger_hash,
        "external_evidence_index": evidence_index,
        "source_isolation": {
            "raw_model_answers": "replay_ledger[].raw_answer",
            "mentor_supplements": "replay_ledger[].mentor_supplement",
            "external_evidence": "external_evidence_index",
            "principle": "原文、导师补充、外部证据三者隔离；引用升级只能来自外部证据层。",
        },
        "judge_contract": {
            "role": "summarize_stat_score_only",
            "does_not_rewrite_model_originals": True,
            "anti_hallucination_rule": "不要用模型共识直接验证模型引用；只用隔离外部证据升级引用状态。",
            "unverifiable_explanation": UNVERIFIABLE_EXPLANATION,
        },
        "roadmap": [
            {
                "phase": "Phase 1",
                "name": "引用真实性 + 相关性验证",
                "status": "implemented_mvp",
                "scope": "verified / weakly_verified / irrelevant / unverifiable / contradicted",
            },
            {
                "phase": "Phase 2",
                "name": "证据缺口建议 + L1/L2/L3 导师反馈",
                "status": "suggestion_only",
                "scope": "evidence_gap_filler.py 只输出建议，不代写正文。",
            },
            {
                "phase": "Phase 3",
                "name": "Agent Graph Arena 对接",
                "status": "contract_recorded",
                "scope": "Graph Lab 印章、AgentFi 认证资产、Arena Casino 对抗验证、Forecast Market 可结算预测。",
            },
        ],
        "known_bottom_limits": [
            "Grok provider quota 不能由桥接层绕过。",
            "统计认证引擎可认证评分质量；事实真实性需 citation-level 外部证据验证。",
            "unverifiable 不是 false，UI 必须解释清楚。",
        ],
        "created_at": verified_at,
    }
    report["certification_hash"] = _hash_payload(report)
    return report


def build_replay_ledger(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    """Convenience helper for callers that only need the sealed ledger."""
    return run_grand_judge_mvp(*args, **kwargs)["replay_ledger"]


def _normalize_answer_items(raw_answers: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(raw_answers, dict):
        if "raw_results" in raw_answers:
            raw_answers = raw_answers.get("raw_results") or []
        else:
            raw_answers = [
                {"seat": seat, "ok": True, "response": answer}
                for seat, answer in raw_answers.items()
            ]
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(raw_answers or [], 1):
        if isinstance(item, dict):
            normalized.append(dict(item))
        else:
            normalized.append({"seat": f"seat-{index}", "ok": True, "response": str(item)})
    return normalized


def _supplements_by_seat(mentor_supplements: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not mentor_supplements:
        return {}
    if isinstance(mentor_supplements, dict):
        iterable = mentor_supplements.get("mentor_supplements") or mentor_supplements.values()
    else:
        iterable = mentor_supplements
    result: dict[str, dict[str, Any]] = {}
    for item in iterable:
        if not isinstance(item, dict):
            continue
        seat = str(item.get("seat") or "").lower()
        if seat:
            result[seat] = dict(item)
    return result


def _unverifiable_reasons(*reports: dict[str, Any] | None) -> list[dict[str, str]]:
    reasons: list[dict[str, str]] = []
    for report in reports:
        if not report:
            continue
        for item in report.get("items") or []:
            if item.get("status") == "unverifiable":
                reasons.append({
                    "citation_id": str(item.get("citation_id") or ""),
                    "raw": str(item.get("raw") or ""),
                    "reason": str(item.get("reason") or UNVERIFIABLE_EXPLANATION),
                })
    return reasons


def _external_evidence_index(external_evidence: list[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
    if not external_evidence:
        return []
    items = external_evidence.get("items") if isinstance(external_evidence, dict) else external_evidence
    result: list[dict[str, Any]] = []
    for index, item in enumerate(items or [], 1):
        if not isinstance(item, dict):
            item = {"text": str(item)}
        public = {
            "evidence_id": str(item.get("id") or item.get("evidence_id") or f"EVID-{index:03d}"),
            "url": item.get("url") or item.get("source_url"),
            "title": item.get("title") or item.get("source") or item.get("name"),
            "status": item.get("status") or item.get("verification_status"),
        }
        public["evidence_hash"] = _hash_payload(item)
        result.append(public)
    return result


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
