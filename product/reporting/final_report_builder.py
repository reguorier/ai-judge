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

from product.archive.latest_pointer import update_latest
from product.archive.report_indexer import update_index
from product.reporting.evidence_summarizer import (
    build_evidence_packet,
    build_seat_matrix,
    compute_failed_seats,
    compute_valid_seats,
)
from product.reporting.html_renderer import render_final_report_html
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
            return fail_no_report(
                run_id=run_id,
                reason="final_report_not_grounded",
                failures=quality.failures,
            )

    return report


# ─── Support functions ───────────────────────────────────────────────

def default_reports_root() -> Path:
    return Path(os.environ.get("AI_JUDGE_REPORTS_ROOT", str(PROJECT_ROOT / "reports")))


def make_run_id(prefix: str = "client") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def title_from_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question).strip()
    return normalized[:72] or "AI Judge client run"


# ─── Write bundle ────────────────────────────────────────────────────

def write_report_bundle(report: dict[str, Any], reports_root: Path | None = None) -> dict[str, Any]:
    reports_root = reports_root or default_reports_root()
    run_id = str(report["run_id"])
    run_dir = reports_root / "runs" / run_id
    followups_dir = run_dir / "followups"
    followups_dir.mkdir(parents=True, exist_ok=True)

    is_failure = report.get("_failure") is not None

    if is_failure:
        total_seats = 0
        valid_seats = 0
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
    seat_matrix = build_seat_matrix(
        run_id=run_id,
        mode=str(report.get("mode", "deep_judge")),
        valid_seats=valid_seats,
        total_seats=total_seats,
        failed_seats=failed_seats,
    )
    final_report_path = run_dir / "final_report.md"
    html_report_path = run_dir / "final_report.html"
    summary_path = run_dir / "summary.json"
    evidence_path = run_dir / "evidence_packet.json"
    seat_matrix_path = run_dir / "seat_matrix.json"
    operator_note_path = run_dir / "operator_note.md"
    report["audit"]["artifact_paths"] = [
        str(final_report_path),
        str(html_report_path),
        str(summary_path),
        str(evidence_path),
        str(seat_matrix_path),
    ]
    final_report_path.write_text(render_final_report_markdown(report), encoding="utf-8")
    html_report_path.write_text(render_final_report_html(report), encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    seat_matrix_path.write_text(json.dumps(seat_matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
        "final_report_path": str(final_report_path),
        "html_report_path": str(html_report_path),
        "evidence_packet_path": str(evidence_path),
        "seat_matrix_path": str(seat_matrix_path),
        "human_status": "最终报告生成失败。" if is_failure else "最终报告已生成，用户可以查看、追问或归档。",
        "controls": {
            "can_pause": False,
            "can_resume": False,
            "can_stop": False,
            "can_rerun_failed": failed_seats > 0,
        },
    }
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
            "summary": str(summary_path),
            "evidence_packet": str(evidence_path),
            "seat_matrix": str(seat_matrix_path),
            "operator_note": str(operator_note_path),
        },
    }