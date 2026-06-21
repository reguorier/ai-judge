#!/usr/bin/env python3
"""Quality gate for returned model content before it enters report body."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from product.reporting.claim_card_normalizer import matched_slots_for_text


QUALITY_GATE_SCHEMA = "ai_judge.returned_content_quality_gate.v1"

RAW_FRAGMENT_MARKERS = [
    "...",
    "…",
    "摘要：",
    "代表性材料",
    "复制",
    "表格",
    "Claim/Evidence/Assumption",
    "Claim :",
    "Evidence :",
    "Assumption :",
    "revised_claims",
    "learned_from_others",
    "still_disagree",
    "final_delta",
    "网页席位",
    "答案总结",
    "二轮共振方案",
    "互评",
    "[my answer]",
]

RUNTIME_MARKERS = [
    "web_collection_process_timeout",
    "seat_timeout",
    "resonance_stall_degraded",
    "round2_late_evidence_deferred",
    "未完成",
    "subprocess exceeded",
    "parse_failed",
    "submit_failed",
]

JUDGMENT_DIRECTION_MARKERS = [
    "必须",
    "不得",
    "不能",
    "不应",
    "需要",
    "应当",
    "只能",
    "禁止",
    "允许",
    "可以",
    "可部署",
    "可上线",
    "触发",
    "导致",
    "构成",
    "风险",
]

EVIDENCE_MARKERS = [
    "因为",
    "依据",
    "证据",
    "来源",
    "可验证",
    "假设",
    "若",
    "如果",
    "监管",
    "规则",
    "责任",
    "路径",
    "要求",
]


def evaluate_returned_content_quality(
    *,
    domain: str,
    raw_claims: list[Any],
    raw_seat_outputs: list[Any] | None = None,
    missing_required_seats: list[Any] | None = None,
) -> dict[str, Any]:
    domain = str(domain or "").lower()
    claims = _normalize_raw_claims(raw_claims)
    usable: list[dict[str, Any]] = []
    discarded: list[dict[str, Any]] = []
    domain_matched = 0
    reason_counts: Counter[str] = Counter()

    for claim in claims:
        text = str(claim.get("claim") or "")
        matched_slots = matched_slots_for_text(domain, text)
        if matched_slots:
            domain_matched += 1
        reasons = _discard_reasons(domain, claim, matched_slots)
        if reasons:
            discarded.append({
                "claim_id": str(claim.get("claim_id") or ""),
                "seat": str(claim.get("seat") or ""),
                "reasons": reasons,
            })
            reason_counts.update(reasons)
            continue
        row = dict(claim)
        row["matched_slots"] = matched_slots
        usable.append(row)

    content_quality = _content_quality(len(usable), len(claims))
    return {
        "schema": QUALITY_GATE_SCHEMA,
        "domain": domain,
        "raw_claim_count": len(claims),
        "raw_seat_output_count": len(raw_seat_outputs or []),
        "domain_matched_claim_count": domain_matched,
        "content_quality": content_quality,
        "usable_claims": usable,
        "discarded_claims": discarded,
        "discard_reasons": dict(reason_counts),
        "quality_summary": _quality_summary(content_quality, len(claims), domain_matched, usable, discarded, reason_counts),
    }


def _normalize_raw_claims(raw_claims: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(raw_claims or []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("claim") or item.get("text") or "").strip()
        if not text:
            continue
        rows.append({
            "claim_id": str(item.get("claim_id") or f"claim-{index}"),
            "seat": str(item.get("seat") or item.get("_seat") or item.get("seat_id") or "").lower(),
            "claim": text,
            "score": item.get("score", item.get("_score")),
            "tier": item.get("tier", item.get("_tier")),
            "confidence": item.get("confidence"),
        })
    return rows


def _discard_reasons(domain: str, claim: dict[str, Any], matched_slots: list[str]) -> list[str]:
    text = str(claim.get("claim") or "")
    lower = text.lower()
    reasons: list[str] = []
    if any(marker.lower() in lower for marker in RUNTIME_MARKERS):
        reasons.append("runtime_or_failure_record")
    if any(marker.lower() in lower for marker in RAW_FRAGMENT_MARKERS):
        reasons.append("raw_template_or_truncation_residue")
    if _is_review_or_summary(claim):
        reasons.append("review_or_summary_not_domain_claim")
    if len(text) > 260:
        reasons.append("claim_too_long_for_report_body")
    if not _complete_sentence(text):
        reasons.append("not_complete_natural_language_sentence")
    if not matched_slots:
        reasons.append("not_directly_related_to_domain_core_slots")
    if not _has_judgment_object(domain, text):
        reasons.append("missing_clear_judgment_object")
    if not _has_judgment_direction(text):
        reasons.append("missing_clear_judgment_direction")
    if not _has_evidence_path(text):
        reasons.append("missing_evidence_or_verification_path")
    return list(dict.fromkeys(reasons))


def _is_review_or_summary(claim: dict[str, Any]) -> bool:
    claim_id = str(claim.get("claim_id") or "").lower()
    text = str(claim.get("claim") or "")
    return (
        "reviews-" in claim_id
        or "answer-summary" in claim_id
        or "mentor-resonance" in claim_id
        or "web-main" in claim_id
        or "互评" in text
        or "答案总结" in text
        or "网页席位" in text
        or "二轮共振方案" in text
    )


def _complete_sentence(text: str) -> bool:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) < 28:
        return False
    if clean.endswith((",", "，", "、", ":", "：", "-", "—")):
        return False
    return bool(re.search(r"[。.!！?？]$", clean))


def _has_judgment_object(domain: str, text: str) -> bool:
    lower = str(text or "").lower()
    domain_terms = {
        "finance": ["系统", "ai", "投顾", "投资", "交易", "客户", "ria", "sec", "fiduciary"],
        "medical": ["系统", "ai", "医院", "医生", "临床", "fda", "samd", "cds", "ehr", "患者"],
        "legal": ["系统", "ai", "律所", "律师", "客户", "法院", "privilege", "upl", "citation"],
    }.get(domain, ["系统", "ai"])
    return any(term in lower for term in domain_terms)


def _has_judgment_direction(text: str) -> bool:
    lower = str(text or "").lower()
    return any(marker.lower() in lower for marker in JUDGMENT_DIRECTION_MARKERS)


def _has_evidence_path(text: str) -> bool:
    lower = str(text or "").lower()
    return any(marker.lower() in lower for marker in EVIDENCE_MARKERS)


def _content_quality(usable_count: int, raw_count: int) -> str:
    if usable_count >= 6:
        return "USABLE"
    if usable_count >= 3:
        return "WEAK"
    return "UNREADABLE"


def _quality_summary(
    content_quality: str,
    raw_count: int,
    domain_matched: int,
    usable: list[dict[str, Any]],
    discarded: list[dict[str, Any]],
    reason_counts: Counter[str],
) -> str:
    top = ", ".join(f"{reason}:{count}" for reason, count in reason_counts.most_common(3)) or "none"
    return (
        f"raw claims {raw_count}, domain matched claims {domain_matched}, usable claims {len(usable)}, "
        f"discarded claims {len(discarded)}, content_quality {content_quality}; top discard reasons: {top}."
    )
