"""FDJP service – high-level orchestration for five-dimension audit runs.

Production-hardened with real provider support:
- Provider kind selection (stub/null/real)
- Force refresh support
- Provider metadata in audit output
- Hybrid conflicts, unsupported evidence tracking
- Extended return format for API
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product.fdjp.constants import (
    DEFAULT_AUDIT_MODE,
    FDJP_VERSION,
    VALID_AUDIT_MODES,
)
from product.fdjp.extractor import run_heuristic_dimension_audit
from product.fdjp.gates import evaluate_dimension_scores, evaluate_fdjp_gates
from product.fdjp.hybrid import synthesize_hybrid_audit
from product.fdjp.llm_auditor import run_llm_audit
from product.fdjp.provider import FDJPAuditProvider, StubProvider, create_provider
from product.fdjp.report_blocks import build_fdjp_report_blocks


FDJP_CLIENT_CONTRACT_SCHEMA = "ai_judge.fdjp.client_contract.v1"


def _default_reports_root() -> Path:
    return Path(
        os.environ.get(
            "AI_JUDGE_REPORTS_ROOT",
            str(Path.home() / "Library" / "Application Support" / "AI Judge" / "runtime" / "reports"),
        )
    )


def _default_runtime_runs_root() -> Path:
    return Path(
        os.environ.get(
            "AI_JUDGE_RUNS_ROOT",
            str(Path.home() / "Library" / "Application Support" / "AI Judge" / "runtime" / "runs"),
        )
    )


def locate_run_dir(run_id: str, reports_root: Path | None = None) -> Path:
    """Locate the artifact directory for a given run_id."""
    if reports_root is not None:
        candidates = [
            reports_root / "runs" / run_id,
            reports_root / run_id,
        ]
    else:
        candidates = [
            _default_runtime_runs_root() / run_id,
            _default_reports_root() / "runs" / run_id,
        ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_existing_audit(run_dir: Path) -> dict[str, Any] | None:
    """Load an existing dimension_audit.json if present."""
    audit_path = run_dir / "fdjp" / "dimension_audit.json"
    if audit_path.exists():
        try:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if isinstance(audit, dict):
                audit.setdefault("artifact_dir", str(run_dir / "fdjp"))
            return audit
        except Exception:
            return None
    return None


def load_task(run_dir: Path) -> dict[str, Any]:
    """Load task data from run directory."""
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            return {
                "run_id": summary.get("run_id", ""),
                "task_id": summary.get("run_id", ""),
                "question": summary.get("question", ""),
                "mode": summary.get("mode", "unknown"),
            }
        except Exception:
            pass
    hermes_path = run_dir / "hermes-output.json"
    if hermes_path.exists():
        try:
            hermes = json.loads(hermes_path.read_text(encoding="utf-8"))
            return {
                "run_id": hermes.get("run_id", run_dir.name),
                "task_id": hermes.get("run_id", run_dir.name),
                "question": hermes.get("question", ""),
                "mode": hermes.get("mode", "unknown"),
            }
        except Exception:
            pass
    verdict_path = run_dir / "verdict.json"
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
            return {
                "run_id": verdict.get("run_id", run_dir.name),
                "task_id": verdict.get("run_id", run_dir.name),
                "question": verdict.get("question", ""),
                "mode": verdict.get("mode", "unknown"),
            }
        except Exception:
            pass
    return {"run_id": run_dir.name, "question": "", "mode": "unknown"}


_FAILED_HERMES_MARKERS = (
    "existing_answer_placeholder",
    "provider_quota_limited",
    "prompt_still_in_input",
    "usage limit",
    "usage/message limit",
    "未完成",
    "慢生成待回收",
)


def _looks_failed_hermes_claim(text: str, tier: str = "") -> bool:
    lowered = str(text or "").lower()
    if str(tier or "").lower() == "rejected":
        return True
    return any(marker.lower() in lowered for marker in _FAILED_HERMES_MARKERS)


def _seat_answers_from_hermes(hermes: dict[str, Any]) -> list[dict[str, Any]]:
    seats: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for index, claim in enumerate(hermes.get("top_claims", []) or [], start=1):
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("text") or claim.get("claim") or "").strip()
        seat_id = str(claim.get("seat") or claim.get("seat_id") or f"seat_{index}").strip()
        if not text or _looks_failed_hermes_claim(text):
            continue
        key = (seat_id, text[:160])
        if key in seen:
            continue
        seen.add(key)
        seats.append({
            "seat_id": seat_id,
            "display_name": seat_id,
            "output": text,
            "text": text,
            "score": claim.get("score", claim.get("confidence", 0.55)),
            "confidence": claim.get("confidence", claim.get("score", 0.55)),
            "answer_path": "hermes-output.json:top_claims",
        })

    for index, claim in enumerate(hermes.get("claims", []) or [], start=1):
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("claim") or claim.get("text") or "").strip()
        seat_id = str(claim.get("seat") or claim.get("seat_id") or f"claim_{index}").strip()
        tier = str(claim.get("tier") or "")
        if not text or _looks_failed_hermes_claim(text, tier):
            continue
        key = (seat_id, text[:160])
        if key in seen:
            continue
        seen.add(key)
        seats.append({
            "seat_id": seat_id,
            "display_name": seat_id,
            "output": text,
            "text": text,
            "score": claim.get("score", claim.get("confidence", 0.55)),
            "confidence": claim.get("confidence", claim.get("score", 0.55)),
            "answer_path": "hermes-output.json:claims",
        })

    return seats


def load_seat_answers(run_dir: Path) -> list[dict[str, Any]]:
    """Load seat outputs from run directory artifacts."""
    sm_path = run_dir / "seat_matrix.json"
    if sm_path.exists():
        try:
            sm = json.loads(sm_path.read_text(encoding="utf-8"))
            seats_data = sm.get("seats", [])
            if seats_data:
                return seats_data
        except Exception:
            pass

    ep_path = run_dir / "evidence_packet.json"
    if ep_path.exists():
        try:
            ep = json.loads(ep_path.read_text(encoding="utf-8"))
            seats_data = ep.get("seats", [])
            if seats_data:
                return seats_data
        except Exception:
            pass

    collected_runtime_seats: list[dict[str, Any]] = []
    seen_runtime_claims: set[tuple[str, str]] = set()

    def _extend_runtime_seats(items: list[dict[str, Any]]) -> None:
        for item in items:
            key = (str(item.get("seat_id") or ""), str(item.get("output") or "")[:180])
            if key in seen_runtime_claims:
                continue
            seen_runtime_claims.add(key)
            collected_runtime_seats.append(item)

    hermes_path = run_dir / "hermes-output.json"
    if hermes_path.exists():
        try:
            hermes = json.loads(hermes_path.read_text(encoding="utf-8"))
            _extend_runtime_seats(_seat_answers_from_hermes(hermes))
        except Exception:
            pass

    verdict_path = run_dir / "verdict.json"
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
            _extend_runtime_seats(_seat_answers_from_hermes(verdict))
        except Exception:
            pass

    if collected_runtime_seats:
        return collected_runtime_seats

    fr_path = run_dir / "final_report.md"
    if fr_path.exists():
        try:
            text = fr_path.read_text(encoding="utf-8")
            return [{"seat_id": "report_content", "output": text, "text": text}]
        except Exception:
            pass

    return []


def load_evidence(run_dir: Path) -> list[dict[str, Any]]:
    """Load evidence from run directory."""
    ep_path = run_dir / "evidence_packet.json"
    if ep_path.exists():
        try:
            ep = json.loads(ep_path.read_text(encoding="utf-8"))
            return ep.get("evidence_items", ep.get("items", []))
        except Exception:
            pass
    return []


def save_dimension_audit(run_dir: Path, audit: dict[str, Any]) -> tuple[Path, Path, Path]:
    """Persist FDJP audit artifacts to disk."""
    fdjp_dir = run_dir / "fdjp"
    fdjp_dir.mkdir(parents=True, exist_ok=True)

    audit_path = fdjp_dir / "dimension_audit.json"
    gates_path = fdjp_dir / "gates.json"
    blocks_path = fdjp_dir / "report_blocks.json"

    audit["updated_at"] = datetime.now(timezone.utc).isoformat()

    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    gates_path.write_text(
        json.dumps(audit.get("gates", {}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    blocks_path.write_text(
        json.dumps(audit.get("report_blocks", []), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Write findings as JSONL
    findings_path = fdjp_dir / "dimension_findings.jsonl"
    with findings_path.open("w", encoding="utf-8") as f:
        for dim_data in audit.get("dimensions", {}).values():
            for finding in dim_data.get("findings", []):
                f.write(json.dumps(finding, ensure_ascii=False) + "\n")

    # Write provider metadata
    pm_path = fdjp_dir / "provider_metadata.json"
    pm = audit.get("provider_metadata", {})
    if pm:
        pm_path.write_text(
            json.dumps(pm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return audit_path, gates_path, blocks_path


def build_fdjp_client_contract(audit: dict[str, Any] | None) -> dict[str, Any]:
    """Build the stable FDJP payload all clients should consume."""
    audit = audit if isinstance(audit, dict) else {}
    dims = audit.get("dimensions", {}) if isinstance(audit.get("dimensions"), dict) else {}
    findings = audit.get("findings", [])
    if not findings:
        findings = [
            finding
            for dim_data in dims.values()
            if isinstance(dim_data, dict)
            for finding in dim_data.get("findings", [])
            if isinstance(finding, dict)
        ]

    structured_findings = [
        f for f in findings
        if isinstance(f, dict)
        and str(f.get("claim_type", "")).startswith(("seat_assertion_", "evidence_assertion_"))
    ]
    sourced_findings = [
        f for f in structured_findings
        if f.get("evidence_ids") and (f.get("source_seats") or str(f.get("claim_type", "")).startswith("evidence_"))
    ]
    constraint_ready = [
        f for f in sourced_findings
        if f.get("assumptions") and f.get("verifiable") and f.get("constraint")
    ]

    dimension_findings = {
        dim: len((dims.get(dim) or {}).get("findings", []))
        for dim in dims.keys()
    }

    return {
        "schema": FDJP_CLIENT_CONTRACT_SCHEMA,
        "run_id": audit.get("run_id", ""),
        "status": audit.get("status", "FDJP_AUDIT_UNAVAILABLE"),
        "mode": audit.get("mode", ""),
        "audit_mode": audit.get("audit_mode", audit.get("mode", "")),
        "effective_mode": audit.get("effective_mode", audit.get("mode", "")),
        "overall_score": audit.get("overall_score", 0.0),
        "dimension_scores": audit.get("dimension_scores", {}),
        "dimension_findings": dimension_findings,
        "assertion_summary": {
            "total_findings": len(findings),
            "structured_findings": len(structured_findings),
            "sourced_findings": len(sourced_findings),
            "constraint_ready_findings": len(constraint_ready),
            "heuristic_metadata": audit.get("heuristic_metadata", {}),
        },
        "gates": audit.get("gates", {}),
        "cross_dimension_conflicts": audit.get("cross_dimension_conflicts", []),
        "artifact_dir": audit.get("artifact_dir", ""),
        "value_delta": {
            "mode": "multi_seat_constraint_audit",
            "compared_to_single_model": [
                "不是只给一个模型的一段答案，而是保留多席位来源和分歧。",
                "不是散文结论，而是每条判断绑定 source_seats、evidence_ids、assumptions、verifiable、constraint。",
                "不是一次性输出，而是经过五维约束、交叉冲突和发布门控。",
            ],
        },
        "audit": audit,
    }


def run_dimension_audit(
    run_id: str,
    task_type: str = "general",
    force: bool = False,
    reports_root: Path | None = None,
    audit_mode: str = "heuristic_only",
    provider_kind: str = "stub",
    force_refresh: bool = False,
    provider: FDJPAuditProvider | None = None,
    timeout_sec: int = 45,
) -> dict[str, Any]:
    """Run the full FDJP five-dimension audit for a run.

    Args:
        run_id: The run identifier.
        task_type: Task category for weighting.
        force: If True, re-run even if cached audit exists.
        reports_root: Override default reports root path.
        audit_mode: One of 'llm', 'hybrid', 'heuristic_only', 'unavailable'.
        provider_kind: Provider type - 'stub', 'null', or 'real'.
        force_refresh: If True, force re-run (alias for force).
        provider: FDJPAuditProvider instance (overrides provider_kind if given).
        timeout_sec: LLM call timeout in seconds.

    Returns:
        Audit dict with extended fields:
        run_id, status, audit_mode, effective_mode, overall_score,
        dimension_scores, findings, gates, llm_metadata, provider_metadata,
        hybrid_conflicts, warnings, blockers, parse_metadata
    """
    run_dir = locate_run_dir(run_id, reports_root)

    # Resolve force_refresh
    should_force = force or force_refresh

    # Validate audit_mode
    requested_mode = audit_mode
    if audit_mode not in VALID_AUDIT_MODES:
        audit_mode = DEFAULT_AUDIT_MODE

    # Check existing
    if not should_force:
        existing = load_existing_audit(run_dir)
        if existing:
            existing["_cached"] = True
            return existing

    # Load inputs
    task = load_task(run_dir)
    seats = load_seat_answers(run_dir)
    evidence = load_evidence(run_dir)

    # ── Create provider if not given ──
    if provider is None:
        provider = create_provider(provider_kind)

    # ── Select audit path based on requested mode ──
    effective_mode: str
    llm_metadata: dict[str, Any] = {}
    provider_metadata: dict[str, Any] = {}
    parse_metadata: dict[str, Any] = {
        "unsupported_ratio": 0.0,
        "unsupported_evidence_count": 0,
        "total_evidence_refs": 0,
        "parse_warnings": [],
    }
    hybrid_conflicts: list[dict[str, Any]] = []

    if audit_mode == "unavailable":
        effective_mode = "unavailable"
        audit = _build_unavailable_audit(task, task_type)

    elif audit_mode == "heuristic_only":
        effective_mode = "heuristic_only"
        audit = run_heuristic_dimension_audit(task, seats, evidence, task_type)
        audit["audit_mode"] = "heuristic_only"
        audit["requested_mode"] = requested_mode
        audit["effective_mode"] = effective_mode

    elif audit_mode == "llm":
        llm_result = run_llm_audit(provider, task, seats, evidence, task_type, timeout_sec)
        llm_metadata = llm_result.get("llm_metadata", {})
        provider_metadata = llm_result.get("provider_metadata", {})
        parse_metadata = llm_result.get("parse_metadata", parse_metadata)

        if not llm_metadata.get("success", False):
            effective_mode = "heuristic_only"
            audit = run_heuristic_dimension_audit(task, seats, evidence, task_type)
            audit["audit_mode"] = requested_mode
            audit["requested_mode"] = requested_mode
            audit["effective_mode"] = effective_mode
            audit["llm_metadata"] = llm_metadata
            audit["provider_metadata"] = provider_metadata
            audit["parse_metadata"] = parse_metadata
            audit["heuristic_metadata"] = {"reason": "LLM failed, fallback to heuristic"}
        else:
            effective_mode = "llm"
            audit = run_heuristic_dimension_audit(task, seats, evidence, task_type)
            audit["dimensions"] = llm_result.get("dimensions", audit.get("dimensions", {}))
            audit["dimension_scores"] = llm_result.get("dimension_scores", audit.get("dimension_scores", {}))
            audit["insights"] = llm_result.get("insights", [])
            audit["findings"] = llm_result.get("findings", [])
            audit["audit_mode"] = requested_mode
            audit["requested_mode"] = requested_mode
            audit["effective_mode"] = effective_mode
            audit["llm_metadata"] = llm_metadata
            audit["provider_metadata"] = provider_metadata
            audit["parse_metadata"] = parse_metadata
            audit["mode"] = "llm"

    elif audit_mode == "hybrid":
        llm_result = run_llm_audit(provider, task, seats, evidence, task_type, timeout_sec)
        llm_metadata = llm_result.get("llm_metadata", {})
        provider_metadata = llm_result.get("provider_metadata", {})
        parse_metadata = llm_result.get("parse_metadata", parse_metadata)
        heuristic_result = run_heuristic_dimension_audit(task, seats, evidence, task_type)

        unsupported_ratio = parse_metadata.get("unsupported_ratio", 0.0)
        hybrid = synthesize_hybrid_audit(
            heuristic_result,
            llm_result if llm_metadata.get("success") else None,
            provider_metadata=provider_metadata,
            llm_unsupported_ratio=unsupported_ratio,
        )

        if not llm_metadata.get("success", False):
            effective_mode = "heuristic_only"
            audit = heuristic_result
            audit["llm_metadata"] = llm_metadata
            audit["provider_metadata"] = provider_metadata
            audit["parse_metadata"] = parse_metadata
            audit["heuristic_metadata"] = {"reason": "LLM failed, hybrid degraded to heuristic_only"}
        else:
            effective_mode = "hybrid"
            audit = heuristic_result
            audit["dimensions"] = hybrid.get("dimensions", audit.get("dimensions", {}))
            audit["overall_score"] = hybrid.get("overall_score", audit.get("overall_score", 0.0))
            audit["dimension_scores"] = hybrid.get("dimension_scores", audit.get("dimension_scores", {}))
            audit["findings"] = hybrid.get("findings", [])
            audit["cross_dimension_conflicts"] = hybrid.get("hybrid_conflicts", [])
            audit["llm_metadata"] = llm_metadata
            audit["provider_metadata"] = provider_metadata
            audit["parse_metadata"] = parse_metadata
            audit["mode"] = "hybrid"

            # Collect hybrid conflicts
            for dim_name, dim_data in hybrid.get("dimensions", {}).items():
                if dim_data.get("conflict"):
                    hybrid_conflicts.append(dim_data["conflict"])

            audit["hybrid_conflicts"] = hybrid_conflicts
            audit["_hybrid_blockers"] = hybrid.get("blockers", [])
            audit["_hybrid_warnings"] = hybrid.get("warnings", [])
            audit["_parser_blockers"] = hybrid.get("parser_blockers", [])

        audit["audit_mode"] = requested_mode
        audit["requested_mode"] = requested_mode
        audit["effective_mode"] = effective_mode

    else:
        effective_mode = "heuristic_only"
        audit = run_heuristic_dimension_audit(task, seats, evidence, task_type)
        audit["audit_mode"] = requested_mode
        audit["requested_mode"] = requested_mode
        audit["effective_mode"] = effective_mode

    # ── Evaluate scores and gates ──
    audit = evaluate_dimension_scores(audit, task_type)

    # Hybrid gates: merge LLM + heuristic blockers/warnings
    if audit_mode == "hybrid" and effective_mode == "hybrid":
        gates = evaluate_fdjp_gates(audit)
        for b in audit.pop("_hybrid_blockers", []):
            if isinstance(b, str):
                gates["blockers"].append({"blocker_id": b, "severity": "P0", "reason": b})
            elif isinstance(b, dict) and not any(
                existing.get("blocker_id") == b.get("blocker_id") for existing in gates["blockers"]
            ):
                gates["blockers"].append(b)

        for w in audit.pop("_hybrid_warnings", []):
            if isinstance(w, str):
                gates["warnings"].append({"warning_id": w, "severity": "P1", "reason": w})
            elif isinstance(w, dict) and not any(
                existing.get("warning_id") == w.get("warning_id") for existing in gates["warnings"]
            ):
                gates["warnings"].append(w)

        for pb in audit.pop("_parser_blockers", []):
            if isinstance(pb, str):
                gates["blockers"].append({"blocker_id": pb, "severity": "P0", "reason": pb})

        gates["blocker_count"] = len(gates["blockers"])
        gates["warning_count"] = len(gates["warnings"])
        audit["gates"] = gates
        audit = evaluate_dimension_scores(audit, task_type)
    else:
        audit["gates"] = evaluate_fdjp_gates(audit)

    audit["report_blocks"] = build_fdjp_report_blocks(audit)
    audit["created_at"] = datetime.now(timezone.utc).isoformat()

    # ── Gate Semantics Patch: heuristic mode cannot claim FULL_PASS ──
    if effective_mode in ("heuristic_only", "unavailable") and audit.get("status") == "FDJP_FULL_PASS":
        audit["status"] = "FDJP_PASS_WITH_WARNINGS"

    # ── Heuristic-only warning ──
    if effective_mode in ("heuristic_only", "unavailable"):
        existing_warnings = audit["gates"].get("warnings", [])
        has_heuristic_warning = any(
            w.get("warning_id") == "FDJP_LLM_UNAVAILABLE_HEURISTIC_ONLY"
            for w in existing_warnings
        )
        if not has_heuristic_warning:
            existing_warnings.append({
                "warning_id": "FDJP_LLM_UNAVAILABLE_HEURISTIC_ONLY",
                "severity": "P1",
                "reason": "仅启用启发式审计，不能标 FULL_PASS",
                "affected_dimension": "global",
            })
            audit["gates"]["warnings"] = existing_warnings
            audit["gates"]["warning_count"] = len(existing_warnings)

    # Ensure provider_metadata always present
    if "provider_metadata" not in audit:
        audit["provider_metadata"] = provider_metadata

    # Persist
    audit["artifact_dir"] = str(run_dir / "fdjp")
    save_dimension_audit(run_dir, audit)
    audit["_cached"] = False

    return audit


def _build_unavailable_audit(
    task: dict[str, Any],
    task_type: str = "general",
) -> dict[str, Any]:
    """Build an audit dict representing FDJP_AUDIT_UNAVAILABLE state."""
    return {
        "run_id": task.get("run_id", ""),
        "task_id": task.get("task_id", ""),
        "task_type": task_type,
        "status": "FDJP_AUDIT_UNAVAILABLE",
        "mode": "unavailable",
        "audit_mode": "unavailable",
        "requested_mode": "unavailable",
        "effective_mode": "unavailable",
        "overall_score": 0.0,
        "dimension_scores": {},
        "dimensions": {},
        "findings": [],
        "insights": [],
        "cross_dimension_conflicts": [],
        "hybrid_conflicts": [],
        "gates": {"blockers": [], "warnings": [], "blocker_count": 0, "warning_count": 0},
        "report_blocks": [],
        "llm_metadata": {},
        "provider_metadata": {},
        "parse_metadata": {},
        "heuristic_metadata": {},
        "created_at": "",
        "version": FDJP_VERSION,
    }


def load_dimension_audit(
    run_id: str,
    reports_root: Path | None = None,
) -> dict[str, Any] | None:
    """Load dimension audit for a run. Returns None if not found."""
    run_dir = locate_run_dir(run_id, reports_root)
    return load_existing_audit(run_dir)


def load_dimension_report_blocks(
    run_id: str,
    reports_root: Path | None = None,
) -> dict[str, Any]:
    """Load report blocks for a run."""
    run_dir = locate_run_dir(run_id, reports_root)
    blocks_path = run_dir / "fdjp" / "report_blocks.json"
    if blocks_path.exists():
        try:
            blocks = json.loads(blocks_path.read_text(encoding="utf-8"))
            return {"ok": True, "run_id": run_id, "blocks": blocks}
        except Exception as e:
            return {"ok": False, "run_id": run_id, "error": str(e), "blocks": []}
    return {"ok": False, "run_id": run_id, "error": "FDJP_REPORT_BLOCKS_NOT_FOUND", "blocks": []}
