#!/usr/bin/env python3
"""Human review signature layer for AI Judge certifications."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


VALID_DECISIONS = {"accept", "conditional", "reject", "escalate"}


def sign_human_review(
    *,
    run_id: str,
    certification_hash: str,
    reviewer: str,
    decision: str,
    reason: str,
    signed_at: str | None = None,
) -> dict[str, Any]:
    """Create a tamper-evident human review signature."""
    decision = str(decision or "").lower().strip()
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of {sorted(VALID_DECISIONS)}")
    reason = str(reason or "").strip()
    if len(reason) < 20:
        raise ValueError("human review reason must be at least 20 characters")
    signed_at = signed_at or datetime.now(timezone.utc).isoformat()
    payload = {
        "schema": "human_review_signature.v1",
        "run_id": run_id,
        "certification_hash": certification_hash,
        "reviewer": str(reviewer or "human_reviewer").strip() or "human_reviewer",
        "decision": decision,
        "reason": reason,
        "signed_at": signed_at,
    }
    payload["signature_hash"] = _hash_payload(payload)
    return payload


def human_review_status(grand_report: dict[str, Any]) -> dict[str, Any]:
    signature = grand_report.get("human_review_signature")
    if signature:
        return {
            "status": "signed",
            "decision": signature.get("decision"),
            "reviewer": signature.get("reviewer"),
            "signature_hash": signature.get("signature_hash"),
        }
    citation = grand_report.get("citation_verification") or {}
    counts = citation.get("counts") or {}
    required = bool(counts.get("contradicted") or counts.get("unverifiable"))
    return {
        "status": "required" if required else "optional",
        "reason": "存在 contradicted/unverifiable 引用，发布前建议人工签名。" if required else "引用状态较稳，可选人工签名。",
    }


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
