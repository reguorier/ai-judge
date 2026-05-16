#!/usr/bin/env python3
"""Anonymous blind cross-validation contracts for Grand Judge."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def build_blind_cross_validation_packet(
    *,
    question: str,
    grand_report: dict[str, Any],
    reviewers: list[str],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build anonymized third-round prompts without seat names."""
    created_at = generated_at or datetime.now(timezone.utc).isoformat()
    anonymized = _anonymized_claims(grand_report)
    prompts = [
        {
            "reviewer": reviewer,
            "prompt": _review_prompt(question, reviewer, anonymized),
        }
        for reviewer in reviewers
    ]
    packet = {
        "schema": "blind_cross_validation.v1",
        "status": "pending_model_reviews",
        "created_at": created_at,
        "reviewer_count": len(reviewers),
        "threshold": 0.67,
        "anonymization": {
            "seat_names_removed": True,
            "raw_text_truncated": True,
            "source_hashes_preserved": True,
        },
        "anonymized_claims": anonymized,
        "review_prompts": prompts,
        "rule": "多数模型不记名确认后，引用或 claim 才能从模型共识升级为可信共识。",
    }
    packet["packet_hash"] = _hash_payload(packet)
    return packet


def aggregate_blind_reviews(reviews: list[dict[str, Any]], *, threshold: float = 0.67) -> dict[str, Any]:
    """Aggregate model blind-review decisions."""
    by_citation: dict[str, list[dict[str, Any]]] = {}
    for review in reviews:
        citation_id = str(review.get("citation_id") or review.get("target_id") or "")
        if not citation_id:
            continue
        by_citation.setdefault(citation_id, []).append(review)

    rows: list[dict[str, Any]] = []
    for citation_id, citation_reviews in sorted(by_citation.items()):
        counts = {"confirm": 0, "dispute": 0, "abstain": 0}
        for review in citation_reviews:
            decision = str(review.get("decision") or "abstain").lower()
            if decision not in counts:
                decision = "abstain"
            counts[decision] += 1
        decisive = counts["confirm"] + counts["dispute"]
        confirm_ratio = counts["confirm"] / decisive if decisive else 0.0
        rows.append({
            "citation_id": citation_id,
            "review_count": len(citation_reviews),
            "counts": counts,
            "confirm_ratio": round(confirm_ratio, 4),
            "majority_confirmed": decisive >= 2 and confirm_ratio >= threshold,
            "needs_human_review": counts["dispute"] > 0 or decisive < 2,
        })

    result = {
        "schema": "blind_cross_validation.result.v1",
        "status": "completed" if rows else "no_reviews",
        "threshold": threshold,
        "citation_results": rows,
        "confirmed_count": sum(1 for row in rows if row["majority_confirmed"]),
        "human_review_count": sum(1 for row in rows if row["needs_human_review"]),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    result["result_hash"] = _hash_payload(result)
    return result


def _anonymized_claims(grand_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(grand_report.get("replay_ledger") or [], 1):
        answer_id = f"ANSWER-{index:03d}"
        for layer, report_key in (("raw_answer", "citation_verification"), ("mentor_supplement", "mentor_citation_verification")):
            report = entry.get(report_key) or {}
            for item in report.get("items") or []:
                rows.append({
                    "answer_id": answer_id,
                    "layer": layer,
                    "citation_id": item.get("citation_id"),
                    "citation": item.get("raw"),
                    "status": item.get("status"),
                    "reason": item.get("reason"),
                    "context_preview": _compact(item.get("context"), 220),
                    "answer_hash": entry.get("raw_answer_hash") if layer == "raw_answer" else entry.get("mentor_supplement_hash"),
                })
    return rows


def _review_prompt(question: str, reviewer: str, anonymized: list[dict[str, Any]]) -> str:
    payload = json.dumps(anonymized[:40], ensure_ascii=False, indent=2)
    return (
        "[AIJUDGE_BLIND_CROSS_VALIDATION]\n"
        f"Reviewer: {reviewer}\n"
        f"Original question: {question}\n\n"
        "你将看到匿名答案的引用验证条目。不要猜测作者是谁；只判断每条 citation/claim 是否应 confirm、dispute 或 abstain。\n"
        "输出 JSON 数组：[{\"citation_id\":\"CITE-001\",\"decision\":\"confirm|dispute|abstain\",\"reason\":\"...\",\"confidence\":0.0-1.0}]\n\n"
        f"Anonymized packet:\n{payload}"
    )


def _compact(value: Any, limit: int = 300) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
