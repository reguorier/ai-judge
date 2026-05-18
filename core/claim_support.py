#!/usr/bin/env python3
"""Claim-span/source support audit for AI Judge Citation Audit.

Citation verification answers whether a source can be matched in an isolated
evidence layer. This module answers a smaller follow-up question: whether the
claim near that citation is actually supported by the matched source.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


CLAIM_SUPPORT_STATUSES = (
    "supported",
    "partially_supported",
    "unsupported",
    "contradicted",
    "unknown",
)

SOURCE_RELEVANCE_STATUSES = (
    "relevant",
    "weakly_relevant",
    "irrelevant",
    "unknown",
)

SUPPORT_FAILURE_CODES = (
    "none",
    "overclaimed_causation",
    "missing_claim_evidence",
    "source_silent",
    "citation_unmatched",
    "source_contradicts_claim",
)

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]{2,}", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")
_CAUSAL_RE = re.compile(
    r"\b(cause|caused|causes|causing|lead to|led to|resulted in|results in|"
    r"because of|due to|drives|driven by|attributable to|responsible for)\b|"
    r"(导致|造成|引发|归因于|因为|由于|使得|带来)",
    re.IGNORECASE,
)
_ASSOCIATION_RE = re.compile(
    r"\b(correlation|correlated|association|associated|linked|relationship|"
    r"observational|cohort|risk factor|predictor)\b|"
    r"(相关|关联|观察性|相关性|关系|风险因素)",
    re.IGNORECASE,
)
_CAUSATION_DISCLAIMER_RE = re.compile(
    r"\b(does not establish causation|does not prove causality|cannot establish causation|"
    r"cannot infer causation|no causal conclusion|not causal|not causation|"
    r"correlation does not imply causation)\b|"
    r"(不能证明因果|不能推出因果|不代表因果|并不证明因果|未证明因果|非因果)",
    re.IGNORECASE,
)


def audit_claim_support(
    *,
    answer_text: str,
    citation_items: list[dict[str, Any]],
    external_evidence: list[dict[str, Any]] | dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Audit claim support separately from citation/source verification."""
    audited_at = generated_at or datetime.now(timezone.utc).isoformat()
    evidence_items = _normalize_evidence(external_evidence)
    items = [
        _audit_one_item(
            citation_item=item,
            answer_text=str(answer_text or ""),
            evidence_items=evidence_items,
            audited_at=audited_at,
        )
        for item in citation_items or []
    ]
    report = {
        "schema": "claim_support.v1",
        "status_schema": list(CLAIM_SUPPORT_STATUSES),
        "source_relevance_schema": list(SOURCE_RELEVANCE_STATUSES),
        "failure_code_schema": list(SUPPORT_FAILURE_CODES),
        "item_count": len(items),
        "claim_support_counts": _counts(items, "claim_support", CLAIM_SUPPORT_STATUSES),
        "source_relevance_counts": _counts(items, "source_relevance", SOURCE_RELEVANCE_STATUSES),
        "support_failure_counts": _failure_counts(items),
        "items": items,
        "explanation": (
            "Citation status, source relevance, and claim support are separate. "
            "A source can be real and relevant while failing to support the model's exact claim."
        ),
        "audited_at": audited_at,
    }
    report["overall_claim_support"] = _overall_claim_support(report["claim_support_counts"], len(items))
    report["claim_support_hash"] = _hash_payload(report)
    return report


def _audit_one_item(
    *,
    citation_item: dict[str, Any],
    answer_text: str,
    evidence_items: list[dict[str, Any]],
    audited_at: str,
) -> dict[str, Any]:
    citation_status = str(citation_item.get("status") or "unverifiable")
    claim_text = _claim_text(answer_text, citation_item)
    evidence = _matched_evidence(citation_item, evidence_items)
    evidence_text = _evidence_text(evidence)
    source_relevance = _source_relevance(citation_item, evidence, evidence_text)

    if citation_status == "contradicted":
        claim_support = "contradicted"
        failure_code = "source_contradicts_claim"
        reason = "Citation verification already found external evidence contradicting this source or related assertion."
    elif not evidence:
        claim_support = "unknown"
        failure_code = "citation_unmatched"
        reason = "No isolated evidence item is available for claim-level support scoring."
    elif _overclaimed_causation(claim_text, evidence_text):
        claim_support = "contradicted"
        failure_code = "overclaimed_causation"
        reason = "The claim uses causal language, while the matched source reports association or explicitly disclaims causation."
    elif citation_status == "verified":
        claim_support = "supported"
        failure_code = "none"
        reason = "The citation is strongly matched and no deterministic claim-support failure was detected."
    elif citation_status == "weakly_verified":
        claim_support = "partially_supported"
        failure_code = "none"
        reason = "The citation has partial support, but the source anchor is not strong enough for full claim support."
    elif citation_status == "irrelevant":
        claim_support = "unsupported"
        failure_code = "source_silent"
        reason = "The source can be matched, but it is not relevant enough to support the cited claim."
    else:
        claim_support = "unknown"
        failure_code = "missing_claim_evidence"
        reason = "The citation is currently unverifiable, so claim-level support cannot be upgraded."

    return {
        "claim_id": _claim_id(citation_item, claim_text),
        "citation_id": citation_item.get("citation_id"),
        "citation_status": citation_status,
        "raw_citation": citation_item.get("raw"),
        "claim_span": _compact(claim_text, 360),
        "source_id": (evidence or {}).get("id") or (evidence or {}).get("evidence_id"),
        "source_url": (evidence or {}).get("url"),
        "source_title": (evidence or {}).get("title"),
        "source_relevance": source_relevance,
        "claim_support": claim_support,
        "support_failure_code": failure_code,
        "support_reason": reason,
        "matched_evidence_hash": (citation_item.get("matched_evidence") or {}).get("evidence_hash")
        or (evidence or {}).get("evidence_hash"),
        "audited_at": audited_at,
    }


def _normalize_evidence(external_evidence: list[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
    if not external_evidence:
        return []
    if isinstance(external_evidence, dict):
        raw_items = external_evidence.get("items") or external_evidence.get("evidence") or [external_evidence]
    else:
        raw_items = external_evidence
    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items or [], 1):
        if not isinstance(item, dict):
            item = {"text": str(item)}
        url = str(item.get("url") or item.get("source_url") or "").strip()
        title = str(item.get("title") or item.get("source") or item.get("name") or "").strip()
        snippet = str(item.get("snippet") or item.get("summary") or item.get("quote") or "").strip()
        text = str(item.get("text") or item.get("content") or "").strip()
        evidence_id = str(item.get("id") or item.get("evidence_id") or f"EVID-{index:03d}")
        items.append({
            **item,
            "id": str(item.get("id") or evidence_id),
            "evidence_id": evidence_id,
            "url": url,
            "normalized_url": _normalize_url(url),
            "title": title,
            "snippet": snippet,
            "text": text,
            "_combined": " ".join([url, title, snippet, text]),
        })
    return items


def _matched_evidence(citation_item: dict[str, Any], evidence_items: list[dict[str, Any]]) -> dict[str, Any] | None:
    public = citation_item.get("matched_evidence") or {}
    public_id = str(public.get("evidence_id") or public.get("id") or "")
    public_url = _normalize_url(str(public.get("url") or ""))
    raw_url = _normalize_url(str(citation_item.get("raw") or "")) if citation_item.get("kind") == "url" else ""
    for evidence in evidence_items:
        evidence_id = str(evidence.get("id") or evidence.get("evidence_id") or "")
        if public_id and public_id == evidence_id:
            return evidence
        evidence_url = str(evidence.get("normalized_url") or _normalize_url(str(evidence.get("url") or "")))
        if public_url and public_url == evidence_url:
            return evidence
        if raw_url and raw_url == evidence_url:
            return evidence
    return None


def _claim_text(answer_text: str, citation_item: dict[str, Any]) -> str:
    context = str(citation_item.get("context") or "").strip()
    raw = str(citation_item.get("raw") or "").strip()
    if not context:
        context = answer_text
    sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_RE.split(context) if sentence.strip()]
    if raw:
        for index, sentence in enumerate(sentences):
            if raw in sentence:
                cleaned = _remove_citation(sentence, raw)
                if _tokens(cleaned):
                    return cleaned
                if index > 0:
                    return _remove_citation(sentences[index - 1], "")
    return _remove_citation(sentences[0] if sentences else context, raw)


def _remove_citation(text: str, raw: str) -> str:
    if raw:
        text = text.replace(raw, " ")
    text = re.sub(r"\b(Source|Sources|参考|来源)\s*[:：]\s*$", "", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _evidence_text(evidence: dict[str, Any] | None) -> str:
    if not evidence:
        return ""
    return " ".join([
        str(evidence.get("title") or ""),
        str(evidence.get("snippet") or ""),
        str(evidence.get("text") or ""),
        str(evidence.get("quote") or ""),
        str(evidence.get("summary") or ""),
    ])


def _source_relevance(citation_item: dict[str, Any], evidence: dict[str, Any] | None, evidence_text: str) -> str:
    if not evidence:
        return "unknown"
    status = str(citation_item.get("status") or "")
    if status in {"verified", "weakly_verified", "contradicted"}:
        return "relevant"
    if status == "irrelevant":
        return "irrelevant"
    score = _token_overlap(str(citation_item.get("context") or ""), evidence_text)
    if score >= 0.24:
        return "relevant"
    if score > 0:
        return "weakly_relevant"
    return "unknown"


def _overclaimed_causation(claim_text: str, evidence_text: str) -> bool:
    if not _CAUSAL_RE.search(claim_text):
        return False
    if _CAUSATION_DISCLAIMER_RE.search(evidence_text):
        return True
    return bool(_ASSOCIATION_RE.search(evidence_text) and not _CAUSAL_RE.search(evidence_text))


def _counts(items: list[dict[str, Any]], key: str, schema: tuple[str, ...]) -> dict[str, int]:
    counts = {status: 0 for status in schema}
    for item in items:
        status = str(item.get(key) or "")
        if status not in counts:
            counts[status] = 0
        counts[status] += 1
    return counts


def _failure_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {code: 0 for code in SUPPORT_FAILURE_CODES}
    for item in items:
        code = str(item.get("support_failure_code") or "none")
        if code not in counts:
            counts[code] = 0
        counts[code] += 1
    return counts


def _overall_claim_support(counts: dict[str, int], item_count: int) -> str:
    if item_count <= 0:
        return "unknown"
    if counts.get("contradicted", 0):
        return "contradicted"
    if counts.get("unsupported", 0):
        return "unsupported"
    if counts.get("supported", 0) and not any(counts.get(status, 0) for status in ("partially_supported", "unknown")):
        return "supported"
    if counts.get("supported", 0) or counts.get("partially_supported", 0):
        return "partially_supported"
    return "unknown"


def _claim_id(citation_item: dict[str, Any], claim_text: str) -> str:
    seed = {
        "citation_id": citation_item.get("citation_id"),
        "claim": claim_text,
        "raw": citation_item.get("raw"),
    }
    return f"CLAIM-{_hash_payload(seed)[:10].upper()}"


def _normalize_url(url: str) -> str:
    url = str(url or "").strip().rstrip(").,;:!?，。；：！？")
    if url.startswith("www."):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        return _normalize_text(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return f"{netloc}{parsed.path.rstrip('/')}".lower()


def _normalize_text(text: str) -> str:
    return " ".join(_TOKEN_RE.findall(str(text or "").lower()))


def _token_overlap(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, min(len(left_tokens), len(right_tokens)))


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(str(text or "").lower()))


def _compact(value: Any, limit: int = 300) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
