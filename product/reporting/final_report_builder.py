"""Build and persist the issue-grounded report-first AI Judge client output.

P0 fix: reports MUST be grounded in the user's legal issue, not AI Judge product meta.
Reports built without LLM / search-agent / seat_outputs fail with no_substantive_reasoning.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.sanitizers import sanitize_json_payload
from core.noise_audit import build_noise_audit, noise_summary
from core.model_stability import (
    default_model_stability_path,
    model_stability_summary,
    update_model_stability_profiles,
)

from product.archive.latest_pointer import update_latest
from product.archive.report_indexer import update_index
from product.reporting.evidence_summarizer import (
    build_evidence_packet,
    build_seat_matrix,
    compute_failed_seats,
    compute_valid_seats,
)
from product.reporting.html_renderer import build_final_report_judge_ir, render_final_report_html
from product.reporting.markdown_renderer import render_final_report_markdown
from product.reporting.reliability_scorer import reliability_sentence, score_reliability
from product.reporting.report_quality_gate import validate_final_report_relevance
from product.reporting.report_schema import (
    REPORT_SCHEMA_VERSION,
    SUMMARY_SCHEMA_VERSION,
    mode_label,
    normalize_mode,
    utc_now_iso,
)
from product.reporting.runtime.autonomous_strategy import (
    asg_state_path,
    production_strategies_path,
    update_autonomous_strategy_state,
)
from product.reporting.runtime.autonomous_economy import (
    autonomous_economy_state_path,
    update_autonomous_economy_state,
)
from product.reporting.runtime.recursive_civilization import (
    recursive_civilization_state_path,
    update_recursive_civilization_state,
)
from product.reporting.runtime.decision_os import (
    decision_policy_config_path,
    decision_os_state_path,
    update_decision_os_state,
)
from product.reporting.runtime.diff_engine import diff_snapshots
from product.reporting.runtime.meta_judge import (
    meta_judge_state_path,
    model_weights_path,
    update_meta_judge_state,
)
from product.reporting.runtime.market_simulation import (
    market_simulation_state_path,
    update_market_simulation_state,
)
from product.reporting.runtime.model_memory import update_model_memory
from product.reporting.runtime.replay import replay_snapshot_html
from product.reporting.runtime.runtime_view import render_runtime_view_html
from product.reporting.runtime.self_improving_loop import (
    self_improving_loop_state_path,
    update_self_improving_loop_state,
)
from product.reporting.runtime.snapshots import (
    build_report_snapshot,
    latest_snapshot,
    load_snapshot_index,
    persist_report_snapshot,
)
from product.reporting.runtime.strategy_intelligence import (
    strategy_state_path,
    update_strategy_state,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ─── Input model ─────────────────────────────────────────────────────

@dataclass
class FinalReportInput:
    """Structured input for building an issue-grounded final report."""

    run_id: str
    mode: str
    question: str
    normalized_task: dict[str, Any] = field(default_factory=dict)
    seat_outputs: list[dict[str, Any]] = field(default_factory=list)
    search_agent_output: dict[str, Any] | None = None
    legal_analysis: dict[str, Any] | None = None
    evidence_pack: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    seat_matrix_raw: dict[str, Any] | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)


# ─── Source collection ───────────────────────────────────────────────

@dataclass
class SourcePack:
    has_substantive_content: bool = False
    search_agent: dict[str, Any] | None = None
    legal_analysis: dict[str, Any] | None = None
    seat_outputs: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    source_labels: list[str] = field(default_factory=list)


def collect_sources(
    *,
    question: str,
    search_agent_output: dict[str, Any] | None = None,
    legal_analysis: dict[str, Any] | None = None,
    seat_outputs: list[dict[str, Any]] | None = None,
    evidence_pack: list[dict[str, Any]] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> SourcePack:
    sp = SourcePack()

    if search_agent_output and isinstance(search_agent_output, dict):
        result = search_agent_output.get("result") or search_agent_output.get("markdown") or ""
        if result and len(str(result).strip()) > 50:
            sp.search_agent = search_agent_output
            sp.source_labels.append("search_agent")
            sp.has_substantive_content = True

    if legal_analysis and isinstance(legal_analysis, dict):
        body = legal_analysis.get("analysis") or legal_analysis.get("body") or ""
        if body and len(str(body).strip()) > 50:
            sp.legal_analysis = legal_analysis
            sp.source_labels.append("legal_analysis")
            sp.has_substantive_content = True

    outputs = seat_outputs or []
    substantive_outputs = [
        o for o in outputs
        if isinstance(o, dict)
        and bool((o.get("answer") or o.get("text") or o.get("summary") or "").strip())
    ]
    if substantive_outputs:
        sp.seat_outputs = substantive_outputs
        sp.source_labels.append("seat_outputs")
        sp.has_substantive_content = True

    sp.evidence = evidence_pack or []
    sp.citations = citations or []

    return sp


# ─── Issue-grounded report composer ──────────────────────────────────

REQUIRED_SECTIONS = [
    "议题摘要",
    "明确裁决结论",
    "法律依据 / 检索依据",
    "多席位观点",
    "共识与分歧",
    "风险与不确定性",
    "下一步行动",
    "引用 / 证据附录",
]


def compose_issue_grounded_report(
    *,
    question: str,
    source_pack: SourcePack,
    seat_matrix: dict[str, Any],
    mode: str,
    run_id: str,
    generated_at: str,
) -> dict[str, Any]:
    """Build a final report whose body is driven by the user's issue, not product meta."""

    # ── Extract body text from sources ──
    body_parts: list[str] = []

    # Search agent output
    if source_pack.search_agent:
        sa = source_pack.search_agent
        sa_text = sa.get("result") or sa.get("markdown") or sa.get("summary") or ""
        if sa_text:
            body_parts.append(str(sa_text))

    # Legal analysis
    if source_pack.legal_analysis:
        la = source_pack.legal_analysis
        la_text = la.get("analysis") or la.get("body") or la.get("conclusion") or ""
        if la_text:
            body_parts.append(str(la_text))

    # Seat outputs
    for i, seat in enumerate(source_pack.seat_outputs):
        answer = seat.get("answer") or seat.get("text") or seat.get("summary") or ""
        if answer:
            body_parts.append(f"## 席位 {i + 1}: {seat.get('display_name', seat.get('seat_id', ''))}\n\n{answer}")

    body_text = "\n\n".join(body_parts) if body_parts else ""

    # ── Extract evidence refs from search-agent (§8) ──
    evidence_refs: list[str] = []
    if source_pack.search_agent:
        sa = source_pack.search_agent
        # New schema: results list with ids
        results = sa.get("results") or []
        if results:
            evidence_refs = [r.get("id", "") for r in results if r.get("id")]
        # Backward compatibility: fallback to snippet count
        if not evidence_refs:
            snippet_count = sa.get("snippet_count", 0)
            evidence_refs = [f"S{i}" for i in range(1, snippet_count + 1)]

    # ── Build core conclusion from available sources ──
    if source_pack.search_agent:
        sa = source_pack.search_agent
        core = (sa.get("result") or sa.get("summary") or sa.get("markdown") or "")
        if isinstance(core, str):
            core = core[:300]
    elif source_pack.legal_analysis:
        la = source_pack.legal_analysis
        core = (la.get("conclusion") or la.get("analysis") or "")[:300]
    else:
        core = f"针对议题「{question[:80]}」，本报告基于 {', '.join(source_pack.source_labels)} 进行分析。"

    # ── Assemble report ──
    total_seats = len(seat_matrix.get("seats", []))
    seats_list = seat_matrix.get("seats", [])
    valid_count = compute_valid_seats(seats_list)
    failed_count = compute_failed_seats(seats_list)

    reliability = score_reliability(valid_count, total_seats, failed_count)
    reliability_text = reliability_sentence(reliability, valid_count, total_seats, failed_count)

    # Extract seat summaries
    seat_summaries: list[dict[str, Any]] = []
    for s in seats_list:
        if s.get("status") in {"valid", "completed", "answered", "success"}:
            seat_summaries.append({
                "summary": f"{s.get('display_name', s.get('seat_id', ''))}: {s.get('summary', '')}",
                "strength": "medium",
            })

    return {
        "schema": REPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "title": title_from_question(question),
        "mode": mode,
        "mode_label": mode_label(mode),
        "question": question,
        "status": "completed",
        "core_conclusion": core,
        "scope": "本报告基于多源分析生成，用于把议题分析、席位观点、证据强度和风险压缩为可审计结论；不替代人工最终判断。",
        "body_text": body_text,
        "verified_facts": [
            {"fact": f"run_id 已生成：{run_id}", "source": "summary.json"},
            {"fact": f"本次模式为 {mode_label(mode)}。", "source": "summary.json"},
            {
                "fact": f"分析来源：{', '.join(source_pack.source_labels) if source_pack.source_labels else '无实质性推理来源'}",
                "source": "source_pack",
            },
        ],
        "inferences": [
            {
                "text": f"报告围绕用户议题「{question[:60]}」展开分析。",
                "source": "source_pack" if source_pack.has_substantive_content else "template",
                "strength": "medium" if source_pack.has_substantive_content else "weak",
            },
        ],
        "seat_summaries": seat_summaries if seat_summaries else [
            {"summary": "当前无有效席位产生实质性分析内容。", "strength": "weak"},
        ],
        "consensus": [
            "报告基于可用的分析来源生成。",
            "若分析来源不足，结论应标记为低置信度。",
        ],
        "disagreements": [
            "当分析来源不充分时，不应伪造未执行的席位或检索结果。",
        ],
        "evidence_strength": {
            "overall": reliability,
            "items": [
                {
                    "description": f"实质性分析来源：{', '.join(source_pack.source_labels) if source_pack.source_labels else '无'}",
                    "strength": "medium" if source_pack.has_substantive_content else "weak",
                },
                {
                    "description": f"席位有效性：{valid_count}/{total_seats}",
                    "strength": "medium" if valid_count else "weak",
                },
            ],
        },
        "risks": [
            "当前分析可能未覆盖全部司法辖区的观点差异。",
            "法律议题的时效性可能影响结论的准确性。",
        ],
        "failure_conditions": [
            "无 LLM / search-agent / seat_outputs 等实质性推理来源。",
            "最终报告未经 report_quality_gate 验证通过。",
            "席位矩阵与实际执行状态不一致。",
        ],
        "recommended_actions": [
            "若结论置信度不足，建议补充联网检索或专业法律数据库查询。",
            "重要法律决策应咨询持证律师。",
        ],
        "audit": {
            "generated_at": generated_at,
            "valid_seats": valid_count,
            "failed_seats": failed_count,
            "total_seats": total_seats,
            "artifact_paths": [],
            "source_pack_labels": source_pack.source_labels,
            "evidence_refs": evidence_refs,
        },
        "_source_pack": source_pack,
    }


# ─── Fail report ─────────────────────────────────────────────────────

def fail_no_report(
    *,
    run_id: str,
    reason: str,
    failures: list[str] | None = None,
) -> dict[str, Any]:
    """Return a structured failure report when no grounded report can be produced."""
    return {
        "schema": REPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "title": "最终报告生成失败",
        "mode": "deep_judge",
        "mode_label": "深度裁决",
        "question": "",
        "status": "failed",
        "core_conclusion": f"无法生成议题驱动的最终报告：{reason}",
        "scope": "报告生成因缺乏实质性推理来源而失败。",
        "body_text": "",
        "verified_facts": [],
        "inferences": [],
        "seat_summaries": [],
        "consensus": [],
        "disagreements": [],
        "evidence_strength": {"overall": "none", "items": []},
        "risks": [],
        "failure_conditions": [reason],
        "recommended_actions": [
            "确保 deep_judge 运行前至少接入 LLM、search-agent 或 seat_outputs 中的一种推理来源。",
        ],
        "audit": {
            "generated_at": utc_now_iso(),
            "valid_seats": 0,
            "failed_seats": 0,
            "total_seats": 0,
            "artifact_paths": [],
        },
        "_failure": {"reason": reason, "failures": failures or []},
    }


# ─── Main builder ────────────────────────────────────────────────────

def build_client_final_report(
    *,
    run_id: str,
    question: str,
    mode: str = "deep_judge",
    status: str = "completed",
    total_seats: int = 3,
    valid_seats: int = 3,
    failed_seats: int = 0,
    generated_at: str | None = None,
    # ── New: external analysis inputs ──
    search_agent_output: dict[str, Any] | None = None,
    legal_analysis: dict[str, Any] | None = None,
    seat_outputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a client final report grounded in the user's legal issue.

    When no substantive analysis sources are provided (no LLM / search-agent / seat_outputs),
    the report is built as a failure rather than a fake product-meta report.

    Backward-compatible: existing callers that don't pass the new params will get
    a failure report unless question contains product-eval keywords.
    """
    mode = normalize_mode(mode)
    generated_at = generated_at or utc_now_iso()

    # ── Collect sources ──
    source_pack = collect_sources(
        question=question,
        search_agent_output=search_agent_output,
        legal_analysis=legal_analysis,
        seat_outputs=seat_outputs,
    )

    # ── P0-2: deep_judge must have substantive reasoning sources ──
    if mode == "deep_judge" and not source_pack.has_substantive_content and "product" not in question.lower()[:50]:
        return fail_no_report(
            run_id=run_id,
            reason="deep_judge_no_substantive_reasoning",
            failures=["no_llm_output", "no_search_agent_output", "no_seat_outputs"],
        )

    # ── Build seat matrix ──
    seat_matrix = build_seat_matrix(
        run_id=run_id,
        mode=mode,
        valid_seats=valid_seats,
        total_seats=total_seats,
        failed_seats=failed_seats,
    )

    # ── Compose report ──
    report = compose_issue_grounded_report(
        question=question,
        source_pack=source_pack,
        seat_matrix=seat_matrix,
        mode=mode,
        run_id=run_id,
        generated_at=generated_at,
    )

    # ── Quality gate ──
    # Skip quality gate for product evaluation questions (explicitly about the tool)
    # Only deep_judge mode requires strict relevance validation
    is_product_eval = "product" in question.lower()[:50]
    if not is_product_eval and mode == "deep_judge":
        quality = validate_final_report_relevance(
            question=question,
            report_text=report.get("body_text", "") or report.get("core_conclusion", ""),
            source_pack={
                "has_substantive_content": source_pack.has_substantive_content,
                "legal_analysis": source_pack.legal_analysis,
                "search_agent_output": source_pack.search_agent,
            },
        )
        if not quality.ok:
            failed_report = fail_no_report(
                run_id=run_id,
                reason="final_report_not_grounded",
                failures=quality.failures,
            )
            failed_report["question"] = question
            failed_report["mode"] = mode
            failed_report["mode_label"] = mode_label(mode)
            failed_report["_source_pack"] = source_pack
            return failed_report

    return report


# ─── Support functions ───────────────────────────────────────────────

def default_reports_root() -> Path:
    return Path(os.environ.get("AI_JUDGE_REPORTS_ROOT", str(PROJECT_ROOT / "reports")))


def make_run_id(prefix: str = "client") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def title_from_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question).strip()
    return normalized[:72] or "AI Judge client run"


def _extract_source_pack_seat_outputs(source_pack: Any) -> list[dict[str, Any]]:
    if not source_pack or not hasattr(source_pack, "seat_outputs"):
        return []
    outputs = getattr(source_pack, "seat_outputs", []) or []
    return [item for item in outputs if isinstance(item, dict)]


def _seat_output_text(seat: dict[str, Any]) -> str:
    for key in ("answer", "output", "response", "text", "summary"):
        value = seat.get(key)
        if isinstance(value, str) and value.strip():
            return re.sub(r"\s+", " ", value).strip()
    return ""


def _attach_source_outputs_to_seat_matrix(
    seat_matrix: dict[str, Any],
    source_pack: Any,
) -> dict[str, Any]:
    """Prefer real client seat outputs over generated placeholder seats."""
    outputs = _extract_source_pack_seat_outputs(source_pack)
    real_seats: list[dict[str, Any]] = []
    for index, seat in enumerate(outputs, start=1):
        text = _seat_output_text(seat)
        if not text:
            continue
        seat_id = str(seat.get("seat_id") or seat.get("seat") or seat.get("name") or f"client_seat_{index}")
        display_name = str(seat.get("display_name") or seat.get("seat_name") or seat_id)
        real_seats.append({
            "seat_id": seat_id,
            "display_name": display_name,
            "status": "valid",
            "run_marker_found": True,
            "structured_answer_found": True,
            "answer_path": "source_pack.seat_outputs",
            "evidence_path": "evidence_packet.json",
            "summary": text[:280],
            "output": text,
            "text": text,
            "stance": seat.get("stance") or seat.get("final_position") or seat.get("position") or "",
            "confidence": seat.get("confidence", seat.get("score", 0.65)),
            "failure_reason": None,
        })
    if real_seats:
        enriched = dict(seat_matrix)
        enriched["seats"] = real_seats
        enriched["source"] = "source_pack.seat_outputs"
        return enriched
    return seat_matrix


def _fdjp_task_type_from_report(report: dict[str, Any]) -> str:
    mode = str(report.get("mode") or "")
    question = str(report.get("question") or "")
    if "法律" in question or "合同" in question or "法院" in question or mode == "deep_judge":
        return "legal"
    if "产品" in question or "代码" in question or "系统" in question or "架构" in question:
        return "product"
    return "general"


# ─── Write bundle ────────────────────────────────────────────────────

def write_report_bundle(report: dict[str, Any], reports_root: Path | None = None) -> dict[str, Any]:
    reports_root = reports_root or default_reports_root()
    run_id = str(report["run_id"])
    run_dir = reports_root / "runs" / run_id
    followups_dir = run_dir / "followups"
    followups_dir.mkdir(parents=True, exist_ok=True)

    is_failure = report.get("_failure") is not None

    source_pack = report.get("_source_pack")
    source_outputs = _extract_source_pack_seat_outputs(source_pack)

    if is_failure and not source_outputs:
        total_seats = 0
        valid_seats = 0
        failed_seats = 0
    elif source_outputs:
        total_seats = len(source_outputs)
        valid_seats = len([item for item in source_outputs if _seat_output_text(item)])
        failed_seats = 0
    else:
        total_seats = int(report.get("audit", {}).get("total_seats", 3))
        valid_seats = int(report.get("audit", {}).get("valid_seats", 0))
        failed_seats = int(report.get("audit", {}).get("failed_seats", 0))

    evidence = build_evidence_packet(
        run_id=run_id,
        question=str(report.get("question", "")),
        mode=str(report.get("mode", "deep_judge")),
        valid_seats=valid_seats,
        total_seats=total_seats,
        failed_seats=failed_seats,
    )
    # §8: Inject search-agent source items into evidence packet for traceability
    source_pack = report.get("_source_pack")
    if source_pack and hasattr(source_pack, "search_agent") and source_pack.search_agent:
        sa = source_pack.search_agent
        results = sa.get("results") or []
        if results:
            evidence["search_agent_sources"] = [
                {
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                    "source_type": r.get("source_type", "unknown"),
                    "relevance_score": r.get("relevance_score", 0.0),
                }
                for r in results
            ]
            evidence["evidence_items"].append({
                "id": "search_agent_evidence",
                "type": "search_agent",
                "strength": "medium",
                "description": f"联网检索证据：{len(results)} 条法律相关片段。",
                "refs": [r.get("id", "") for r in results],
            })
    seat_matrix = build_seat_matrix(
        run_id=run_id,
        mode=str(report.get("mode", "deep_judge")),
        valid_seats=valid_seats,
        total_seats=total_seats,
        failed_seats=failed_seats,
    )
    seat_matrix = _attach_source_outputs_to_seat_matrix(seat_matrix, source_pack)
    if seat_matrix.get("source") == "source_pack.seat_outputs":
        valid_seats = compute_valid_seats(seat_matrix.get("seats", []))
        failed_seats = compute_failed_seats(seat_matrix.get("seats", []))
        total_seats = len(seat_matrix.get("seats", []))
    final_report_path = run_dir / "final_report.md"
    html_report_path = run_dir / "final_report.html"
    judge_ir_path = run_dir / "final_report.judge_ir.json"
    report_snapshot_path = run_dir / "report_snapshot.json"
    report_diff_path = run_dir / "report_diff.json"
    replay_report_path = run_dir / "replay_report.html"
    runtime_view_path = run_dir / "runtime_view.html"
    strategy_intelligence_path = run_dir / "strategy_intelligence.json"
    meta_judge_path = run_dir / "meta_judge.json"
    autonomous_strategy_path = run_dir / "autonomous_strategy.json"
    market_simulation_path = run_dir / "market_simulation.json"
    decision_os_path = run_dir / "decision_os.json"
    self_improving_loop_path = run_dir / "self_improving_loop.json"
    autonomous_economy_path = run_dir / "autonomous_economy.json"
    recursive_civilization_path = run_dir / "recursive_civilization.json"
    summary_path = run_dir / "summary.json"
    evidence_path = run_dir / "evidence_packet.json"
    seat_matrix_path = run_dir / "seat_matrix.json"
    noise_audit_path = run_dir / "noise_audit.json"
    operator_note_path = run_dir / "operator_note.md"

    noise_audit = build_noise_audit(
        run_id=run_id,
        question=str(report.get("question", "")),
        mode=str(report.get("mode", "deep_judge")),
        verdict=report,
        seat_matrix=seat_matrix,
        evidence_packet=evidence,
        generated_at=str(report.get("audit", {}).get("generated_at") or ""),
    )
    report["noise_audit"] = noise_audit
    report.setdefault("audit", {})["noise_audit"] = noise_summary(noise_audit)
    stability_store = update_model_stability_profiles(
        run_id=run_id,
        question=str(report.get("question", "")),
        mode=str(report.get("mode", "deep_judge")),
        noise_audit=noise_audit,
        verdict=report,
        generated_at=str(report.get("audit", {}).get("generated_at") or ""),
    )
    current_seats = [
        str(row.get("seat") or "").lower()
        for row in noise_audit.get("seat_noise_rows", [])
        if isinstance(row, dict) and row.get("seat")
    ]
    report["model_stability"] = model_stability_summary(stability_store, seats=current_seats)
    report["audit"]["model_stability"] = {
        "schema": "ai_judge.model_stability_profiles.v1",
        "profile_count": report["model_stability"].get("profile_count", 0),
        "path": str(default_model_stability_path()),
    }

    report["audit"]["artifact_paths"] = [
        str(final_report_path),
        str(html_report_path),
        str(summary_path),
        str(evidence_path),
        str(seat_matrix_path),
        str(noise_audit_path),
    ]
    evidence = sanitize_json_payload(evidence)
    seat_matrix = sanitize_json_payload(seat_matrix)
    noise_audit = sanitize_json_payload(noise_audit)

    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    seat_matrix_path.write_text(json.dumps(seat_matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    noise_audit_path.write_text(json.dumps(noise_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fdjp_audit: dict[str, Any] | None = None
    try:
        from product.fdjp.service import run_dimension_audit
        fdjp_audit = run_dimension_audit(
            run_id=run_id,
            task_type=_fdjp_task_type_from_report(report),
            force=True,
            reports_root=reports_root,
            audit_mode="heuristic_only",
        )
        report["fdjp_audit"] = fdjp_audit
    except Exception as exc:
        report["fdjp_audit"] = {
            "run_id": run_id,
            "status": "FDJP_AUDIT_UNAVAILABLE",
            "mode": "unavailable",
            "overall_score": 0.0,
            "dimension_scores": {},
            "dimensions": {},
            "gates": {"blockers": [], "warnings": [], "blocker_count": 0, "warning_count": 0},
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    report = sanitize_json_payload(report)
    judge_ir = build_final_report_judge_ir(report)
    judge_ir_path.write_text(
        json.dumps(judge_ir.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    final_report_path.write_text(render_final_report_markdown(report), encoding="utf-8")
    html_report_path.write_text(render_final_report_html(report), encoding="utf-8")
    previous_snapshot = latest_snapshot(reports_root, exclude_run_id=run_id)
    snapshot = build_report_snapshot(
        run_id=run_id,
        report=report,
        judge_ir=judge_ir.to_dict(),
        generated_at=str(report.get("audit", {}).get("generated_at") or ""),
        paths={
            "final_report": str(final_report_path),
            "html_report": str(html_report_path),
            "judge_ir": str(judge_ir_path),
        },
        noise_audit=noise_audit,
        model_stability=report.get("model_stability") if isinstance(report.get("model_stability"), dict) else {},
        previous_snapshot_id=str((previous_snapshot or {}).get("snapshot_id") or ""),
    )
    snapshot_paths = persist_report_snapshot(reports_root, snapshot)
    report_snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_diff = diff_snapshots(previous_snapshot, snapshot)
    report_diff_path.write_text(json.dumps(report_diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    model_memory = update_model_memory(
        reports_root=reports_root,
        snapshot=snapshot,
        previous_snapshot=previous_snapshot,
    )
    strategy_runtime = update_strategy_state(
        reports_root=reports_root,
        snapshot=snapshot,
        previous_snapshot=previous_snapshot,
    )
    strategy_intelligence = strategy_runtime["strategy_intelligence"]
    strategy_state = strategy_runtime["strategy_state"]
    strategy_intelligence_path.write_text(
        json.dumps(strategy_intelligence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    meta_runtime = update_meta_judge_state(
        reports_root=reports_root,
        snapshot=snapshot,
        model_memory=model_memory,
        strategy_intelligence=strategy_intelligence,
    )
    meta_judge = meta_runtime["meta_judge"]
    meta_judge_state = meta_runtime["meta_judge_state"]
    model_weights = meta_runtime["model_weights"]
    meta_judge_path.write_text(
        json.dumps(meta_judge, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    asg_runtime = update_autonomous_strategy_state(
        reports_root=reports_root,
        snapshot=snapshot,
        strategy_intelligence=strategy_intelligence,
        meta_judge=meta_judge,
        model_weights=model_weights,
    )
    autonomous_strategy = asg_runtime["autonomous_strategy"]
    asg_state = asg_runtime["asg_state"]
    production_strategies = asg_runtime["production_strategies"]
    autonomous_strategy_path.write_text(
        json.dumps(autonomous_strategy, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    msl_runtime = update_market_simulation_state(
        reports_root=reports_root,
        snapshot=snapshot,
        strategy_intelligence=strategy_intelligence,
        meta_judge=meta_judge,
        model_weights=model_weights,
        autonomous_strategy=autonomous_strategy,
        production_strategies=production_strategies,
    )
    market_simulation = msl_runtime["market_simulation"]
    market_simulation_state = msl_runtime["market_simulation_state"]
    market_simulation_path.write_text(
        json.dumps(market_simulation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    decision_runtime = update_decision_os_state(
        reports_root=reports_root,
        snapshot=snapshot,
        market_simulation=market_simulation,
        production_strategies=production_strategies,
        model_weights=model_weights,
    )
    decision_os = decision_runtime["decision_os"]
    decision_os_state = decision_runtime["decision_os_state"]
    decision_os_path.write_text(
        json.dumps(decision_os, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    siel_runtime = update_self_improving_loop_state(
        reports_root=reports_root,
        snapshot=snapshot,
        decision_os=decision_os,
        market_simulation=market_simulation,
    )
    self_improving_loop = siel_runtime["self_improving_loop"]
    self_improving_loop_state = siel_runtime["self_improving_loop_state"]
    decision_policy_config = siel_runtime["decision_policy_config"]
    self_improving_loop_path.write_text(
        json.dumps(self_improving_loop, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    economy_runtime = update_autonomous_economy_state(
        reports_root=reports_root,
        snapshot=snapshot,
        production_strategies=production_strategies,
        autonomous_strategy=autonomous_strategy,
        decision_os=decision_os,
        self_improving_loop=self_improving_loop,
        market_simulation=market_simulation,
    )
    autonomous_economy = economy_runtime["autonomous_economy"]
    autonomous_economy_state = economy_runtime["autonomous_economy_state"]
    autonomous_economy_path.write_text(
        json.dumps(autonomous_economy, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    civilization_runtime = update_recursive_civilization_state(
        reports_root=reports_root,
        snapshot=snapshot,
        autonomous_economy=autonomous_economy,
        autonomous_economy_state=autonomous_economy_state,
        strategy_intelligence=strategy_intelligence,
    )
    recursive_civilization = civilization_runtime["recursive_civilization"]
    recursive_civilization_state = civilization_runtime["recursive_civilization_state"]
    recursive_civilization_path.write_text(
        json.dumps(recursive_civilization, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    replay_report_path.write_text(replay_snapshot_html(snapshot), encoding="utf-8")
    runtime_view_path.write_text(
        render_runtime_view_html(
            snapshot_index=load_snapshot_index(reports_root),
            current_snapshot=snapshot,
            report_diff=report_diff,
            model_memory=model_memory,
            strategy_intelligence=strategy_intelligence,
            strategy_state=strategy_state,
            meta_judge=meta_judge,
            meta_judge_state=meta_judge_state,
            model_weights=model_weights,
            autonomous_strategy=autonomous_strategy,
            asg_state=asg_state,
            production_strategies=production_strategies,
            market_simulation=market_simulation,
            market_simulation_state=market_simulation_state,
            decision_os=decision_os,
            decision_os_state=decision_os_state,
            self_improving_loop=self_improving_loop,
            self_improving_loop_state=self_improving_loop_state,
            decision_policy_config=decision_policy_config,
            autonomous_economy=autonomous_economy,
            autonomous_economy_state=autonomous_economy_state,
            recursive_civilization=recursive_civilization,
            recursive_civilization_state=recursive_civilization_state,
        ),
        encoding="utf-8",
    )

    status = "failed" if is_failure else report.get("status", "completed")
    summary = {
        "schema": SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "title": report.get("title"),
        "mode": report.get("mode"),
        "mode_label": report.get("mode_label"),
        "question": report.get("question"),
        "status": status,
        "created_at": report.get("audit", {}).get("generated_at"),
        "started_at": report.get("audit", {}).get("generated_at"),
        "completed_at": report.get("audit", {}).get("generated_at"),
        "total_seats": total_seats,
        "valid_seats": valid_seats,
        "failed_seats": failed_seats,
        "reliability": report.get("evidence_strength", {}).get("overall", "none"),
        "noise_score": noise_audit.get("noise_score"),
        "noise_level": noise_audit.get("noise_level"),
        "noise_recommended_action": noise_audit.get("recommended_action"),
        "model_stability_profile_count": report.get("model_stability", {}).get("profile_count", 0),
        "final_report_path": str(final_report_path),
        "html_report_path": str(html_report_path),
        "judge_ir_path": str(judge_ir_path),
        "report_snapshot_path": str(report_snapshot_path),
        "runtime_snapshot_path": snapshot_paths["snapshot_path"],
        "snapshot_index_path": snapshot_paths["snapshot_index_path"],
        "report_diff_path": str(report_diff_path),
        "replay_report_path": str(replay_report_path),
        "runtime_view_path": str(runtime_view_path),
        "model_memory_path": str(reports_root / "runtime" / "model_memory.json"),
        "strategy_intelligence_path": str(strategy_intelligence_path),
        "strategy_state_path": str(strategy_state_path(reports_root)),
        "meta_judge_path": str(meta_judge_path),
        "meta_judge_state_path": str(meta_judge_state_path(reports_root)),
        "model_weights_path": str(model_weights_path(reports_root)),
        "autonomous_strategy_path": str(autonomous_strategy_path),
        "asg_state_path": str(asg_state_path(reports_root)),
        "production_strategies_path": str(production_strategies_path(reports_root)),
        "market_simulation_path": str(market_simulation_path),
        "market_simulation_state_path": str(market_simulation_state_path(reports_root)),
        "decision_os_path": str(decision_os_path),
        "decision_os_state_path": str(decision_os_state_path(reports_root)),
        "self_improving_loop_path": str(self_improving_loop_path),
        "self_improving_loop_state_path": str(self_improving_loop_state_path(reports_root)),
        "decision_policy_config_path": str(decision_policy_config_path(reports_root)),
        "autonomous_economy_path": str(autonomous_economy_path),
        "autonomous_economy_state_path": str(autonomous_economy_state_path(reports_root)),
        "recursive_civilization_path": str(recursive_civilization_path),
        "recursive_civilization_state_path": str(recursive_civilization_state_path(reports_root)),
        "snapshot_id": snapshot["snapshot_id"],
        "previous_snapshot_id": snapshot.get("previous_snapshot_id", ""),
        "structural_drift_score": report_diff.get("structural_drift_score", 0),
        "strategy_drift_score": strategy_intelligence.get("strategy_drift", {}).get("aggregate_drift_score", 0),
        "strategy_disagreement_type": strategy_intelligence.get("market_structure", {}).get("disagreement_type"),
        "dominant_strategy": strategy_intelligence.get("summary", {}).get("dominant_strategy"),
        "top_model": meta_judge.get("summary", {}).get("top_model"),
        "top_model_score": meta_judge.get("summary", {}).get("top_score"),
        "deprecated_model_count": meta_judge.get("summary", {}).get("deprecated_model_count", 0),
        "asg_accepted_strategy_count": autonomous_strategy.get("summary", {}).get("accepted_count", 0),
        "asg_production_strategy_count": autonomous_strategy.get("summary", {}).get("production_strategy_count", 0),
        "asg_top_strategy_id": autonomous_strategy.get("summary", {}).get("top_strategy_id", ""),
        "msl_scenario_count": market_simulation.get("summary", {}).get("scenario_count", 0),
        "msl_monte_carlo_runs": market_simulation.get("summary", {}).get("monte_carlo_runs", 0),
        "msl_robust_strategy_count": market_simulation.get("summary", {}).get("robust_strategy_count", 0),
        "msl_top_scenario_risk": market_simulation.get("summary", {}).get("top_scenario_risk", 0),
        "msl_worst_scenario_id": market_simulation.get("summary", {}).get("worst_scenario_id", ""),
        "decision_os_top_action": decision_os.get("summary", {}).get("top_action", ""),
        "decision_os_executed_action_count": decision_os.get("summary", {}).get("executed_action_count", 0),
        "decision_os_rejected_action_count": decision_os.get("summary", {}).get("rejected_action_count", 0),
        "decision_os_portfolio_exposure": decision_os.get("summary", {}).get("portfolio_exposure", 0),
        "decision_os_blocked_decision_count": decision_os.get("summary", {}).get("blocked_decision_count", 0),
        "siel_outcome_signal_count": self_improving_loop.get("summary", {}).get("outcome_signal_count", 0),
        "siel_mean_value_error": self_improving_loop.get("summary", {}).get("mean_value_error", 0),
        "siel_policy_update_count": self_improving_loop.get("summary", {}).get("policy_update_count", 0),
        "siel_mutation_count": self_improving_loop.get("summary", {}).get("mutation_count", 0),
        "siel_learning_score": self_improving_loop.get("summary", {}).get("learning_score", 0),
        "siel_policy_direction": self_improving_loop.get("summary", {}).get("policy_direction", "stable"),
        "decision_policy_config_version": decision_policy_config.get("version", 1),
        "ael_agent_count": autonomous_economy.get("summary", {}).get("agent_count", 0),
        "ael_active_agent_count": autonomous_economy.get("summary", {}).get("active_agent_count", 0),
        "ael_terminated_agent_count": autonomous_economy.get("summary", {}).get("terminated_agent_count", 0),
        "ael_total_capital": autonomous_economy.get("summary", {}).get("total_capital", 0),
        "ael_top_agent_id": autonomous_economy.get("summary", {}).get("top_agent_id", ""),
        "ael_top_strategy_id": autonomous_economy.get("summary", {}).get("top_strategy_id", ""),
        "ael_top_agent_capital": autonomous_economy.get("summary", {}).get("top_agent_capital", 0),
        "ael_allocation_entropy": autonomous_economy.get("summary", {}).get("allocation_entropy", 0),
        "ael_lifecycle_event_count": autonomous_economy.get("summary", {}).get("lifecycle_event_count", 0),
        "ael_clone_count": autonomous_economy.get("summary", {}).get("clone_count", 0),
        "ael_termination_count": autonomous_economy.get("summary", {}).get("termination_count", 0),
        "ael_total_capital_reallocated": autonomous_economy.get("summary", {}).get("total_capital_reallocated", 0),
        "rcl_civilization_count": recursive_civilization.get("summary", {}).get("civilization_count", 0),
        "rcl_active_civilization_count": recursive_civilization.get("summary", {}).get("active_civilization_count", 0),
        "rcl_collapsed_civilization_count": recursive_civilization.get("summary", {}).get("collapsed_civilization_count", 0),
        "rcl_top_civilization_id": recursive_civilization.get("summary", {}).get("top_civilization_id", ""),
        "rcl_top_governance_archetype": recursive_civilization.get("summary", {}).get("top_governance_archetype", ""),
        "rcl_governance_mutation_count": recursive_civilization.get("summary", {}).get("governance_mutation_count", 0),
        "rcl_interaction_count": recursive_civilization.get("summary", {}).get("interaction_count", 0),
        "rcl_meta_civilization_count": recursive_civilization.get("summary", {}).get("meta_civilization_count", 0),
        "rcl_emergent_behavior_count": recursive_civilization.get("summary", {}).get("emergent_behavior_count", 0),
        "rcl_civilization_entropy": recursive_civilization.get("summary", {}).get("civilization_entropy", 0),
        "evidence_packet_path": str(evidence_path),
        "seat_matrix_path": str(seat_matrix_path),
        "noise_audit_path": str(noise_audit_path),
        "model_stability_path": str(default_model_stability_path()),
        "human_status": "最终报告生成失败。" if is_failure else "最终报告已生成，用户可以查看、追问或归档。",
        "fdjp_status": (fdjp_audit or report.get("fdjp_audit", {})).get("status"),
        "fdjp_overall_score": (fdjp_audit or report.get("fdjp_audit", {})).get("overall_score"),
        "fdjp_artifact_path": str(run_dir / "fdjp"),
        "controls": {
            "can_pause": False,
            "can_resume": False,
            "can_stop": False,
            "can_rerun_failed": failed_seats > 0,
        },
        "evidence_refs": report.get("audit", {}).get("evidence_refs", []),
    }
    summary = sanitize_json_payload(summary)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    operator_note_path.write_text(
        "# Operator Note\n\n"
        f"- run_id: {run_id}\n"
        f"- mode: {report.get('mode')}\n"
        f"- failed_seats: {failed_seats}\n"
        f"- is_failure: {is_failure}\n"
        "- dashboard: legacy/debug only; not required for this client flow\n"
        "- rollback: remove this run directory and restore code changes from git\n",
        encoding="utf-8",
    )
    update_latest(reports_root, final_report_path, html_report_path)
    update_index(reports_root, summary)
    return {
        "summary": summary,
        "report": report,
        "paths": {
            "run_dir": str(run_dir),
            "final_report": str(final_report_path),
            "html_report": str(html_report_path),
            "judge_ir": str(judge_ir_path),
            "report_snapshot": str(report_snapshot_path),
            "runtime_snapshot": snapshot_paths["snapshot_path"],
            "snapshot_index": snapshot_paths["snapshot_index_path"],
            "report_diff": str(report_diff_path),
            "replay_report": str(replay_report_path),
            "runtime_view": str(runtime_view_path),
            "model_memory": str(reports_root / "runtime" / "model_memory.json"),
            "strategy_intelligence": str(strategy_intelligence_path),
            "strategy_state": str(strategy_state_path(reports_root)),
            "meta_judge": str(meta_judge_path),
            "meta_judge_state": str(meta_judge_state_path(reports_root)),
            "model_weights": str(model_weights_path(reports_root)),
            "autonomous_strategy": str(autonomous_strategy_path),
            "asg_state": str(asg_state_path(reports_root)),
            "production_strategies": str(production_strategies_path(reports_root)),
            "market_simulation": str(market_simulation_path),
            "market_simulation_state": str(market_simulation_state_path(reports_root)),
            "decision_os": str(decision_os_path),
            "decision_os_state": str(decision_os_state_path(reports_root)),
            "self_improving_loop": str(self_improving_loop_path),
            "self_improving_loop_state": str(self_improving_loop_state_path(reports_root)),
            "decision_policy_config": str(decision_policy_config_path(reports_root)),
            "autonomous_economy": str(autonomous_economy_path),
            "autonomous_economy_state": str(autonomous_economy_state_path(reports_root)),
            "recursive_civilization": str(recursive_civilization_path),
            "recursive_civilization_state": str(recursive_civilization_state_path(reports_root)),
            "summary": str(summary_path),
            "evidence_packet": str(evidence_path),
            "seat_matrix": str(seat_matrix_path),
            "noise_audit": str(noise_audit_path),
            "operator_note": str(operator_note_path),
        },
    }
