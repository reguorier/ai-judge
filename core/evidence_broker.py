#!/usr/bin/env python3
"""Evidence Broker for AI Judge Evidence OS.

The broker builds an isolated external-evidence layer. It may list candidate
sources mentioned by models, but candidate sources are not treated as verified
evidence until supplied or fetched as external evidence.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from core.evidence_trace import extract_explicit_refs, extract_implied_refs


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def build_evidence_broker_report(
    *,
    question: str,
    raw_answers: list[dict[str, Any]],
    mentor_supplements: list[dict[str, Any]] | None = None,
    user_evidence: list[dict[str, Any]] | dict[str, Any] | str | None = None,
    allow_network: bool = False,
    generated_at: str | None = None,
    max_fetches: int = 6,
) -> dict[str, Any]:
    """Create an external-evidence layer for citation validation."""
    created_at = generated_at or datetime.now(timezone.utc).isoformat()
    supplied = _normalize_user_evidence(user_evidence)
    candidates = _candidate_sources(raw_answers, mentor_supplements or [])

    fetched: list[dict[str, Any]] = []
    fetch_budget = max(0, int(max_fetches))
    if allow_network:
        for candidate in candidates:
            if fetch_budget <= 0:
                break
            url = str(candidate.get("url") or "")
            if not url.startswith(("http://", "https://")):
                continue
            fetched.append(_fetch_url_evidence(candidate, created_at))
            fetch_budget -= 1

    items = _dedupe_evidence(supplied + fetched + candidates)
    validation_items = [
        item for item in items
        if item.get("source_layer") in {"user_supplied", "network_fetch"}
        or item.get("trusted") is True
    ] + [
        item for item in items
        if item.get("source_layer") == "candidate_source"
    ]
    report = {
        "schema": "evidence_broker.v1",
        "created_at": created_at,
        "question": question,
        "allow_network": bool(allow_network),
        "source_policy": {
            "candidate_source": "模型答案中提到的来源，只能作为待检索候选，不能直接验证模型自己。",
            "user_supplied": "用户或外部系统提供的隔离证据，可进入 citation_validator。",
            "network_fetch": "Evidence Broker 实际抓取到的网页快照，可进入 citation_validator。",
        },
        "items": items,
        "items_for_validation": validation_items,
        "counts": {
            "user_supplied": sum(1 for item in items if item.get("source_layer") == "user_supplied"),
            "network_fetch": sum(1 for item in items if item.get("source_layer") == "network_fetch"),
            "candidate_source": sum(1 for item in items if item.get("source_layer") == "candidate_source"),
            "fetch_error": sum(1 for item in items if item.get("retrieval_state") == "fetch_error"),
        },
    }
    report["broker_hash"] = _hash_payload(report)
    return report


def _normalize_user_evidence(user_evidence: list[dict[str, Any]] | dict[str, Any] | str | None) -> list[dict[str, Any]]:
    if not user_evidence:
        return []
    if isinstance(user_evidence, str):
        raw_items: list[Any] = [{"text": user_evidence}]
    elif isinstance(user_evidence, dict):
        raw_items = user_evidence.get("items") or user_evidence.get("evidence") or [user_evidence]
    else:
        raw_items = user_evidence

    items: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items, 1):
        if not isinstance(raw, dict):
            raw = {"text": str(raw)}
        item = {
            **raw,
            "id": str(raw.get("id") or raw.get("evidence_id") or f"USR-EVID-{index:03d}"),
            "url": str(raw.get("url") or raw.get("source_url") or ""),
            "title": str(raw.get("title") or raw.get("source") or raw.get("name") or ""),
            "snippet": str(raw.get("snippet") or raw.get("summary") or raw.get("quote") or raw.get("text") or raw.get("content") or ""),
            "text": str(raw.get("text") or raw.get("content") or raw.get("snippet") or ""),
            "status": str(raw.get("status") or raw.get("verification_status") or "user_supplied"),
            "trusted": bool(raw.get("trusted", True)),
            "source_layer": "user_supplied",
            "retrieval_state": "provided",
        }
        item["evidence_hash"] = _hash_payload(item)
        items.append(item)
    return items


def _candidate_sources(raw_answers: list[dict[str, Any]], mentor_supplements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for layer, rows in (("raw_answer", raw_answers), ("mentor_supplement", mentor_supplements)):
        for row in rows:
            seat = str(row.get("seat") or "")
            text = str(row.get("response") or row.get("answer") or "")
            for ref in extract_explicit_refs(text):
                kind = str(ref.get("type") or "explicit")
                raw = str(ref.get("value") or "").strip()
                url = raw if kind == "url" and raw.startswith(("http://", "https://", "www.")) else ""
                candidates.append(_candidate_item(raw=raw, kind=kind, url=url, seat=seat, layer=layer))
            for ref in extract_implied_refs(text):
                raw = str(ref.get("source") or "").strip()
                candidates.append(_candidate_item(raw=raw, kind="implied", url="", seat=seat, layer=layer))
    return candidates


def _candidate_item(*, raw: str, kind: str, url: str, seat: str, layer: str) -> dict[str, Any]:
    if url.startswith("www."):
        url = "https://" + url
    item = {
        "id": f"CAND-{_hash_payload({'raw': raw, 'seat': seat, 'layer': layer})[:10].upper()}",
        "url": url,
        "title": raw if kind != "url" else "",
        "snippet": "",
        "text": "",
        "raw_source": raw,
        "kind": kind,
        "status": "candidate_unverified",
        "trusted": False,
        "source_layer": "candidate_source",
        "retrieval_state": "not_fetched",
        "origin_seat": seat,
        "origin_layer": layer,
    }
    item["evidence_hash"] = _hash_payload(item)
    return item


def _fetch_url_evidence(candidate: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    url = str(candidate.get("url") or "")
    request = urllib.request.Request(url, headers={"User-Agent": "AI-Judge-EvidenceBroker/3.5"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read(256_000)
            content_type = response.headers.get("content-type", "")
        text = raw.decode("utf-8", errors="replace")
        title = _extract_title(text) or url
        snippet = _compact(_TAG_RE.sub(" ", text), 480)
        item = {
            **candidate,
            "id": f"FETCH-{_hash_payload(url)[:10].upper()}",
            "title": title,
            "snippet": snippet,
            "text": snippet,
            "status": "fetched",
            "trusted": True,
            "source_layer": "network_fetch",
            "retrieval_state": "fetched",
            "content_type": content_type,
            "fetched_at": fetched_at,
        }
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        item = {
            **candidate,
            "status": "fetch_error",
            "trusted": False,
            "source_layer": "candidate_source",
            "retrieval_state": "fetch_error",
            "fetch_error": str(exc)[:240],
        }
    item["evidence_hash"] = _hash_payload(item)
    return item


def _dedupe_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for item in items:
        key = _evidence_key(item)
        existing = by_key.get(key)
        if not existing:
            by_key[key] = item
            continue
        if _rank(item) > _rank(existing):
            by_key[key] = item
    return list(by_key.values())


def _rank(item: dict[str, Any]) -> int:
    return {"user_supplied": 3, "network_fetch": 2, "candidate_source": 1}.get(str(item.get("source_layer")), 0)


def _evidence_key(item: dict[str, Any]) -> str:
    url = str(item.get("url") or "")
    if url:
        parsed = urlparse(url if not url.startswith("www.") else "https://" + url)
        host = parsed.netloc.lower().removeprefix("www.")
        return f"url:{host}{parsed.path.rstrip('/')}"
    raw = str(item.get("raw_source") or item.get("title") or item.get("snippet") or item.get("text") or "")
    return "text:" + re.sub(r"\s+", " ", raw.lower()).strip()


def _extract_title(text: str) -> str:
    match = _TITLE_RE.search(text)
    if not match:
        return ""
    return html.unescape(" ".join(match.group(1).split()))


def _compact(value: Any, limit: int = 300) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
