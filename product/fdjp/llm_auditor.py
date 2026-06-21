"""FDJP LLM Semantic Auditor – orchestrates provider call + parse + score.

Production-hardened version:
- Retry with provider metadata tracking
- Timeout handling with fallback
- Evidence ref validation (anti-hallucination)
- Unsupported evidence ratio tracking
- Provider metadata safe logging (no API key)
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from product.fdjp.constants import DIMENSION_LABELS, DIMENSIONS
from product.fdjp.llm_parser import LLMParseResult, build_valid_refs_set, parse_llm_response
from product.fdjp.llm_prompts import build_audit_prompt
from product.fdjp.provider import FDJPAuditProvider
from product.fdjp.provider_config import get_provider_config
from product.fdjp.provider_errors import (
    FDJPProviderAuthError,
    FDJPProviderCircuitBreakerOpen,
    FDJPProviderConfigError,
    FDJPProviderConnectionError,
    FDJPProviderRateLimitError,
    FDJPProviderServerError,
    FDJPProviderTimeoutError,
)
from product.fdjp.real_provider import build_provider_metadata
from product.fdjp.schemas import DimensionFinding


def run_llm_audit(
    provider: FDJPAuditProvider,
    task: dict[str, Any],
    seats: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    task_type: str = "general",
    timeout: int = 45,
) -> dict[str, Any]:
    """Run a full LLM semantic audit across all five dimensions.

    Args:
        provider: Configured FDJPAuditProvider instance.
        task: Task dict with 'question' and 'run_id' keys.
        seats: List of seat output dicts.
        evidence: List of evidence dicts.
        task_type: Task category for prompt tuning.
        timeout: LLM call timeout in seconds.

    Returns:
        Dict with:
            dimensions, insights, llm_metadata, findings,
            dimension_scores, provider_metadata, parse_metadata
    """
    meta = {
        "provider": provider.name,
        "model": "stub" if hasattr(provider, "_response") else (
            getattr(provider, "config", None) and provider.config.model or "unknown"
        ),
        "attempted": True,
        "success": False,
        "latency_ms": 0,
        "parse_success": False,
        "error_type": None,
        "error_message": None,
        "retry_count": 0,
        "fallback_used": False,
        "raw_response_saved": False,
    }

    provider_meta: dict[str, Any] = {
        "provider_kind": "stub",
        "model": "none",
        "base_url_hash": "none",
        "latency_ms": 0,
        "timeout_s": timeout,
        "retry_count": 0,
        "fallback_used": True,
        "error_type": None,
        "error_message": None,
        "request_id": None,
    }

    if not provider.is_available():
        meta["success"] = False
        meta["error_type"] = "FDJP_LLM_UNAVAILABLE"
        meta["error_message"] = "Provider is not available"
        provider_meta["error_type"] = "FDJP_LLM_UNAVAILABLE"
        provider_meta["error_message"] = "Provider is not available"
        return {
            "dimensions": _all_insufficient_dims(),
            "insights": [],
            "llm_metadata": meta,
            "findings": [],
            "dimension_scores": {d: 0.25 for d in DIMENSIONS},
            "provider_metadata": provider_meta,
            "parse_metadata": {
                "unsupported_ratio": 0.0,
                "unsupported_evidence_count": 0,
                "total_evidence_refs": 0,
                "parse_warnings": [],
            },
        }

    # Build prompt
    question = str(task.get("question", ""))
    verdict_summary = _build_verdict_summary(seats)
    prompt = build_audit_prompt(question, verdict_summary, seats, task_type)

    # Build valid refs set for evidence validation
    valid_refs = build_valid_refs_set(seats, evidence)

    # Call LLM
    t0 = time.perf_counter()
    parse_result: LLMParseResult
    raw = ""
    try:
        raw = provider.audit(prompt, timeout=timeout)
    except (FDJPProviderTimeoutError, FDJPProviderConfigError,
            FDJPProviderAuthError, FDJPProviderCircuitBreakerOpen,
            FDJPProviderConnectionError, FDJPProviderRateLimitError,
            FDJPProviderServerError) as exc:
        meta["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        meta["success"] = False
        meta["error_type"] = exc.error_type
        meta["error_message"] = str(exc)[:500]
        meta["fallback_used"] = True
        provider_meta.update({
            "latency_ms": meta["latency_ms"],
            "error_type": exc.error_type,
            "error_message": str(exc)[:500],
            "fallback_used": True,
            "retry_count": 0,
        })
        return {
            "dimensions": _all_insufficient_dims(),
            "insights": [],
            "llm_metadata": meta,
            "findings": [],
            "dimension_scores": {d: 0.25 for d in DIMENSIONS},
            "provider_metadata": provider_meta,
            "parse_metadata": {
                "unsupported_ratio": 0.0,
                "unsupported_evidence_count": 0,
                "total_evidence_refs": 0,
                "parse_warnings": [],
            },
        }
    except Exception as exc:
        meta["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        meta["success"] = False
        meta["error_type"] = type(exc).__name__
        meta["error_message"] = str(exc)[:500]
        meta["fallback_used"] = True
        provider_meta.update({
            "latency_ms": meta["latency_ms"],
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:500],
            "fallback_used": True,
        })
        return {
            "dimensions": _all_insufficient_dims(),
            "insights": [],
            "llm_metadata": meta,
            "findings": [],
            "dimension_scores": {d: 0.25 for d in DIMENSIONS},
            "provider_metadata": provider_meta,
            "parse_metadata": {
                "unsupported_ratio": 0.0,
                "unsupported_evidence_count": 0,
                "total_evidence_refs": 0,
                "parse_warnings": [],
            },
        }

    meta["latency_ms"] = round((time.perf_counter() - t0) * 1000)
    meta["success"] = True

    # Build provider metadata (safe, no key)
    if hasattr(provider, "config"):
        provider_meta = build_provider_metadata(
            provider.config,
            latency_ms=meta["latency_ms"],
            retry_count=meta.get("retry_count", 0),
            fallback_used=False,
            error_type=None,
            error_message=None,
        )
    else:
        provider_meta.update({
            "latency_ms": meta["latency_ms"],
            "fallback_used": False,
        })

    # Parse with evidence validation
    parse_result = parse_llm_response(raw, valid_refs=valid_refs)
    meta["parse_success"] = parse_result.success
    meta["raw_response_saved"] = False

    if not parse_result.success:
        meta["error_type"] = "FDJP_LLM_PARSE_FAILED"
        meta["error_message"] = "; ".join(parse_result.errors[:5])

    # Build dimensions dict from parse result
    dimensions: dict[str, dict[str, Any]] = {}
    dimension_scores: dict[str, float] = {}
    findings: list[DimensionFinding] = []

    for dim in DIMENSIONS:
        dim_data = parse_result.dimensions.get(dim, _default_insufficient_dim(dim))
        dimensions[dim] = dim_data

        score = _compute_dimension_score(dim_data)
        dimension_scores[dim] = score

        if dim_data.get("status") != "insufficient":
            finding = DimensionFinding(
                finding_id=f"fdjp-llm-{dim}-{uuid.uuid4().hex[:8]}",
                dimension=dim,
                claim=dim_data.get("claim", ""),
                claim_type="llm_semantic",
                basis=dim_data.get("evidence_refs", []),
                confidence=dim_data.get("confidence", 0.5),
                risk_if_wrong=dim_data.get("risk_if_wrong", ""),
                action_impact=dim_data.get("action_impact", ""),
                source_seats=[],
                evidence_ids=[],
                status=dim_data.get("status", "pass"),
                evidence_refs=dim_data.get("evidence_refs", []),
                reasoning_summary=dim_data.get("reasoning_summary", ""),
                source="llm",
                blocker_id=dim_data.get("blocker_id"),
                warning_id=dim_data.get("warning_id"),
            )
            findings.append(finding)

    return {
        "dimensions": dimensions,
        "insights": parse_result.insights,
        "llm_metadata": meta,
        "findings": findings,
        "dimension_scores": dimension_scores,
        "provider_metadata": provider_meta,
        "parse_metadata": {
            "unsupported_ratio": parse_result.unsupported_ratio,
            "unsupported_evidence_count": parse_result.unsupported_evidence_count,
            "total_evidence_refs": parse_result.total_evidence_refs,
            "parse_warnings": parse_result.parse_warnings,
        },
    }


def _compute_dimension_score(dim_data: dict[str, Any]) -> float:
    """Compute a 0-1 score for a dimension based on LLM findings."""
    status = dim_data.get("status", "insufficient")
    confidence = dim_data.get("confidence", 0.0)

    if status == "blocker":
        return 0.15
    if status == "insufficient":
        return max(0.15, min(confidence, 0.59))
    if status == "warning":
        return 0.55 + confidence * 0.20

    has_evidence = bool(dim_data.get("evidence_refs"))
    has_reasoning = bool(dim_data.get("reasoning_summary"))
    has_action = bool(dim_data.get("action_impact"))
    bonus = 0.05 * sum([has_evidence, has_reasoning, has_action])
    return min(0.70 + confidence * 0.25 + bonus, 0.99)


def _build_verdict_summary(seats: list[dict[str, Any]]) -> str:
    """Build a concise verdict summary from seat outputs."""
    parts: list[str] = []
    for seat in seats[:5]:
        seat_id = seat.get("seat_id", seat.get("seat", ""))
        output = seat.get("output", seat.get("text", ""))
        if output:
            parts.append(f"[{seat_id}]: {output[:500]}")
    return "\n\n".join(parts) if parts else "(no seat outputs)"


def _all_insufficient_dims() -> dict[str, dict[str, Any]]:
    """Return all dimensions as insufficient (LLM unavailable)."""
    return {d: _default_insufficient_dim(d) for d in DIMENSIONS}


def _default_insufficient_dim(dim: str) -> dict[str, Any]:
    return {
        "dimension": dim,
        "status": "insufficient",
        "claim": f"{DIMENSION_LABELS.get(dim, dim)}: LLM 审计不可用",
        "confidence": 0.25,
        "evidence_refs": [],
        "reasoning_summary": "LLM provider 不可用或返回为空",
        "risk_if_wrong": "无 LLM 审计意味着缺少语义层验证",
        "action_impact": "",
        "blocker_id": None,
        "warning_id": None,
        "source": "llm",
    }