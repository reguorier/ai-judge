#!/usr/bin/env python3
"""Eval case export helpers for AI Judge runs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def build_eval_case_from_verdict(verdict: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    grand = verdict.get("grand_judge") or {}
    citation = grand.get("citation_verification") or (verdict.get("web_bridge") or {}).get("citation_verification") or {}
    metrics = grand.get("evidence_quality_metrics") or {}
    case = {
        "schema": "ai_judge_eval_case.v1",
        "case_id": f"EVAL-{_hash_payload({'run_id': verdict.get('run_id'), 'question': verdict.get('question')})[:12].upper()}",
        "run_id": verdict.get("run_id"),
        "question": verdict.get("question"),
        "mode": verdict.get("mode"),
        "engine": verdict.get("engine"),
        "verdict": verdict.get("verdict"),
        "confidence": verdict.get("confidence"),
        "average_score": verdict.get("average_score"),
        "citation_overall_status": citation.get("overall_status"),
        "citation_counts": citation.get("counts") or {},
        "evidence_quality_metrics": metrics,
        "certification_id": citation.get("certification_id") or grand.get("certification_id"),
        "certification_hash": grand.get("certification_hash"),
        "replay_ledger_hash": grand.get("replay_ledger_hash"),
        "human_label": None,
        "created_at": generated_at or datetime.now(timezone.utc).isoformat(),
    }
    case["case_hash"] = _hash_payload(case)
    return case


def collect_eval_cases(verdicts: list[dict[str, Any]], *, limit: int = 200) -> dict[str, Any]:
    cases = [build_eval_case_from_verdict(verdict) for verdict in verdicts[:limit]]
    return {
        "schema": "ai_judge_eval_dataset.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "cases": cases,
    }


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
