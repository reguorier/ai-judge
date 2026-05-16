#!/usr/bin/env python3
"""Citation verification MVP for AI Judge Grand Judge.

The validator is deliberately deterministic and evidence-bounded. It does not
rewrite model answers and does not pretend that an absent match is false. A
citation can only be upgraded when external evidence is supplied and matched.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from core.evidence_trace import extract_explicit_refs, extract_implied_refs


CITATION_STATUSES = (
    "verified",
    "weakly_verified",
    "irrelevant",
    "unverifiable",
    "contradicted",
)

UNVERIFIABLE_EXPLANATION = (
    "unverifiable 表示当前外部证据不足，无法确认该引用真实性或相关性；"
    "它不是 false，也不等于 contradicted。"
)

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]{2,}", re.IGNORECASE)
_URL_TRAIL_RE = re.compile(r"[)\].,;:!?，。；：！？]+$")


def validate_citations(
    answer_text: str,
    *,
    question: str = "",
    external_evidence: list[dict[str, Any]] | dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Validate citations in one answer against supplied external evidence.

    Status meanings:
      - verified: exact or strong match, and relevant to the question/context.
      - weakly_verified: partial evidence match, still useful but not complete.
      - irrelevant: citation exists but matched evidence is off-topic.
      - unverifiable: no supplied external evidence can validate it.
      - contradicted: supplied external evidence explicitly refutes it.
    """
    verified_at = generated_at or datetime.now(timezone.utc).isoformat()
    answer_text = str(answer_text or "")
    question = str(question or "")
    evidence_items = _normalize_external_evidence(external_evidence)
    citations = _extract_citations(answer_text)

    if not citations:
        items = [{
            "citation_id": "CITE-000",
            "raw": "无显式引用",
            "kind": "none",
            "normalized": "",
            "context": _compact(answer_text, 240),
            "status": "unverifiable",
            "reason": "该回答未提供可核查引用；需要外部证据或明确来源后才能升级。",
            "matched_evidence": None,
            "relevance_score": 0.0,
            "verified_at": verified_at,
        }]
    else:
        items = [
            _validate_one_citation(
                citation,
                index=index,
                question=question,
                answer_text=answer_text,
                evidence_items=evidence_items,
                verified_at=verified_at,
            )
            for index, citation in enumerate(citations, 1)
        ]

    counts = _status_counts(items)
    overall_status = _overall_status(counts, len(items))
    report = {
        "schema": "citation_validator.v1",
        "status_schema": list(CITATION_STATUSES),
        "overall_status": overall_status,
        "citation_count": len(citations),
        "item_count": len(items),
        "counts": counts,
        "items": items,
        "external_evidence_used": len(evidence_items),
        "unverifiable_explanation": UNVERIFIABLE_EXPLANATION,
        "verified_at": verified_at,
    }
    report["verification_hash"] = _hash_payload(report)
    return report


def summarize_citation_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate several validator reports into one citation-level summary."""
    counts = {status: 0 for status in CITATION_STATUSES}
    item_count = 0
    citation_count = 0
    for report in reports:
        item_count += int(report.get("item_count") or len(report.get("items") or []))
        citation_count += int(report.get("citation_count") or 0)
        for status, value in (report.get("counts") or {}).items():
            if status in counts:
                counts[status] += int(value or 0)
    return {
        "schema": "citation_validator.summary.v1",
        "status_schema": list(CITATION_STATUSES),
        "overall_status": _overall_status(counts, item_count),
        "citation_count": citation_count,
        "item_count": item_count,
        "counts": counts,
        "unverifiable_explanation": UNVERIFIABLE_EXPLANATION,
        "verification_hash": _hash_payload({"counts": counts, "item_count": item_count, "citation_count": citation_count}),
    }


def _extract_citations(answer_text: str) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for ref in extract_explicit_refs(answer_text):
        raw = _clean_raw_ref(ref.get("value", ""))
        if not raw:
            continue
        kind = str(ref.get("type") or "explicit")
        key = (kind, _normalize_ref(raw, kind))
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "raw": raw,
            "kind": kind,
            "normalized": key[1],
            "context": _context_window(answer_text, raw),
        })
    for ref in extract_implied_refs(answer_text):
        raw = _clean_raw_ref(ref.get("source", ""))
        if not raw:
            continue
        kind = "implied"
        key = (kind, _normalize_ref(raw, kind))
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "raw": raw,
            "kind": kind,
            "normalized": key[1],
            "context": _context_window(answer_text, raw),
        })
    return citations


def _validate_one_citation(
    citation: dict[str, Any],
    *,
    index: int,
    question: str,
    answer_text: str,
    evidence_items: list[dict[str, Any]],
    verified_at: str,
) -> dict[str, Any]:
    best = _best_evidence_match(citation, evidence_items)
    citation_id = f"CITE-{index:03d}"
    if not best:
        return {
            "citation_id": citation_id,
            **citation,
            "status": "unverifiable",
            "reason": "未在隔离的外部证据层找到可匹配来源；这不是 false，只是当前不可验证。",
            "matched_evidence": None,
            "relevance_score": 0.0,
            "verified_at": verified_at,
        }

    evidence, match_score = best
    relevance = _relevance_score(
        " ".join([question, citation.get("context", ""), citation.get("raw", "")]),
        " ".join([evidence.get("title", ""), evidence.get("snippet", ""), evidence.get("text", "")]),
    )
    evidence_status = str(evidence.get("status") or evidence.get("verification_status") or "").lower()
    retrieval_state = str(evidence.get("retrieval_state") or "").lower()
    contradicted = bool(evidence.get("contradicts")) or evidence_status in {"contradicted", "contradicts", "refuted", "false"}
    if contradicted:
        status = "contradicted"
        reason = "外部证据层明确标记该引用或相关断言被反驳。"
    elif evidence_status in {"candidate_unverified", "retrieval_required", "not_fetched", "fetch_error"} or retrieval_state in {"not_fetched", "fetch_error", "blocked"}:
        status = "unverifiable"
        reason = "该来源只是模型答案中的候选来源，尚未进入隔离外部证据层；当前不可验证，不代表为假。"
    elif relevance < 0.24 and question:
        status = "irrelevant"
        reason = "引用来源可以匹配，但与当前问题或上下文相关性不足。"
    elif citation.get("kind") == "implied":
        status = "weakly_verified"
        reason = "间接引用可匹配到外部证据，但未给出 URL/DOI/页码等可复核锚点。"
    elif match_score >= 0.80 and relevance >= 0.12:
        status = "verified"
        reason = "引用与外部证据强匹配，且与当前问题/上下文相关。"
    elif match_score >= 0.48:
        status = "weakly_verified"
        reason = "引用与外部证据存在部分匹配，但仍需要更强证据或更精确来源。"
    else:
        status = "unverifiable"
        reason = "外部证据匹配强度不足；当前不可验证，不代表引用为假。"

    return {
        "citation_id": citation_id,
        **citation,
        "status": status,
        "reason": reason,
        "matched_evidence": _public_evidence(evidence, match_score),
        "relevance_score": round(relevance, 4),
        "verified_at": verified_at,
    }


def _normalize_external_evidence(external_evidence: list[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
    if not external_evidence:
        return []
    raw_items: list[Any]
    if isinstance(external_evidence, dict):
        raw_items = external_evidence.get("items") or external_evidence.get("evidence") or [external_evidence]
    else:
        raw_items = external_evidence
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items, 1):
        if not isinstance(item, dict):
            item = {"text": str(item)}
        url = str(item.get("url") or item.get("source_url") or "").strip()
        title = str(item.get("title") or item.get("source") or item.get("name") or "").strip()
        snippet = str(item.get("snippet") or item.get("summary") or item.get("quote") or "").strip()
        text = str(item.get("text") or item.get("content") or "").strip()
        evidence_id = str(item.get("id") or item.get("evidence_id") or f"EVID-{index:03d}")
        combined = " ".join([url, title, snippet, text])
        normalized.append({
            **item,
            "evidence_id": evidence_id,
            "url": url,
            "normalized_url": _normalize_url(url),
            "host": _host(url),
            "title": title,
            "snippet": snippet,
            "text": text,
            "_combined": combined,
            "_combined_norm": _normalize_text(combined),
        })
    return normalized


def _best_evidence_match(citation: dict[str, Any], evidence_items: list[dict[str, Any]]) -> tuple[dict[str, Any], float] | None:
    best: tuple[dict[str, Any], float] | None = None
    raw = str(citation.get("raw") or "")
    kind = str(citation.get("kind") or "")
    normalized = str(citation.get("normalized") or _normalize_ref(raw, kind))
    citation_host = _host(raw) if kind == "url" else ""
    for evidence in evidence_items:
        score = 0.0
        combined_norm = str(evidence.get("_combined_norm") or "")
        if kind == "url" and normalized and normalized == evidence.get("normalized_url"):
            score = 1.0
        elif kind == "url" and citation_host and citation_host == evidence.get("host"):
            score = max(score, 0.62 + 0.24 * _token_overlap(citation.get("context", ""), evidence.get("_combined", "")))
        elif kind in {"doi", "arxiv"} and normalized and normalized in combined_norm:
            score = 1.0
        elif normalized and normalized in combined_norm:
            score = 0.86
        else:
            score = max(score, 0.72 * _token_overlap(raw, evidence.get("_combined", "")))
            score = max(score, 0.64 * _token_overlap(citation.get("context", ""), evidence.get("_combined", "")))
        if score <= 0:
            continue
        if best is None or score > best[1]:
            best = (evidence, round(score, 4))
    return best


def _public_evidence(evidence: dict[str, Any], match_score: float) -> dict[str, Any]:
    return {
        "evidence_id": evidence.get("evidence_id"),
        "url": evidence.get("url"),
        "title": evidence.get("title"),
        "snippet": _compact(evidence.get("snippet") or evidence.get("text"), 220),
        "status": evidence.get("status") or evidence.get("verification_status"),
        "match_score": round(float(match_score), 4),
        "evidence_hash": _hash_payload({
            "url": evidence.get("url"),
            "title": evidence.get("title"),
            "snippet": evidence.get("snippet"),
            "text": evidence.get("text"),
            "status": evidence.get("status") or evidence.get("verification_status"),
        }),
    }


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in CITATION_STATUSES}
    for item in items:
        status = str(item.get("status") or "unverifiable")
        if status in counts:
            counts[status] += 1
    return counts


def _overall_status(counts: dict[str, int], item_count: int) -> str:
    if item_count <= 0:
        return "unverifiable"
    if counts.get("contradicted", 0):
        return "contradicted"
    if counts.get("verified", 0) and not any(counts.get(s, 0) for s in ("weakly_verified", "irrelevant", "unverifiable")):
        return "verified"
    if counts.get("verified", 0) or counts.get("weakly_verified", 0):
        return "weakly_verified"
    if counts.get("irrelevant", 0) and not counts.get("unverifiable", 0):
        return "irrelevant"
    return "unverifiable"


def _normalize_ref(raw: str, kind: str) -> str:
    raw = _clean_raw_ref(raw)
    if kind == "url":
        return _normalize_url(raw)
    return _normalize_text(raw)


def _normalize_url(url: str) -> str:
    url = _clean_raw_ref(url)
    if url.startswith("www."):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        return _normalize_text(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/")
    return f"{netloc}{path}".lower()


def _host(url: str) -> str:
    url = _clean_raw_ref(url)
    if url.startswith("www."):
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _normalize_text(text: str) -> str:
    return " ".join(_TOKEN_RE.findall(str(text or "").lower()))


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(str(text or "").lower()))


def _token_overlap(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, min(len(left_tokens), len(right_tokens)))


def _relevance_score(left: str, right: str) -> float:
    return _token_overlap(left, right)


def _context_window(text: str, needle: str, radius: int = 110) -> str:
    if not needle:
        return _compact(text, radius * 2)
    index = text.find(needle)
    if index < 0:
        return _compact(text, radius * 2)
    start = max(0, index - radius)
    end = min(len(text), index + len(needle) + radius)
    return text[start:end].strip()


def _clean_raw_ref(value: str) -> str:
    return _URL_TRAIL_RE.sub("", str(value or "").strip())


def _compact(value: Any, limit: int = 300) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
