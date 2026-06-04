"""Build and persist the report-first AI Judge client output."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from product.archive.latest_pointer import update_latest
from product.archive.report_indexer import update_index
from product.reporting.evidence_summarizer import build_evidence_packet, build_seat_matrix
from product.reporting.html_renderer import render_final_report_html
from product.reporting.markdown_renderer import render_final_report_markdown
from product.reporting.reliability_scorer import reliability_sentence, score_reliability
from product.reporting.report_schema import REPORT_SCHEMA_VERSION, SUMMARY_SCHEMA_VERSION, mode_label, normalize_mode, utc_now_iso

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def default_reports_root() -> Path:
    return Path(os.environ.get("AI_JUDGE_REPORTS_ROOT", str(PROJECT_ROOT / "reports")))


def make_run_id(prefix: str = "client") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def title_from_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question).strip()
    return normalized[:72] or "AI Judge client run"


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
) -> dict[str, Any]:
    mode = normalize_mode(mode)
    generated_at = generated_at or utc_now_iso()
    reliability = score_reliability(valid_seats, total_seats, failed_seats)
    reliability_text = reliability_sentence(reliability, valid_seats, total_seats, failed_seats)
    title = title_from_question(question)
    stance = "可以继续执行本地 report-first 闭环；不要把 Dashboard 作为核心产品。" if "dashboard" in question.lower() or "仪表盘" in question else "应以最终报告作为主交付物，界面只保留提交、控制、追问和归档。"
    return {
        "schema": REPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "title": title,
        "mode": mode,
        "mode_label": mode_label(mode),
        "question": question,
        "status": status,
        "core_conclusion": f"{stance} {reliability_text}",
        "scope": "本报告用于把本地 AI Judge run 的问题、状态、席位摘要、证据强度、风险和下一步行动压缩为可审计结论；不替代人工最终判断，也不声称未生成的外部 Web seat 证据存在。",
        "verified_facts": [
            {"fact": f"run_id 已生成并贯穿报告 artifact：{run_id}", "source": "summary.json"},
            {"fact": f"本次模式为 {mode_label(mode)}。", "source": "summary.json"},
            {"fact": "报告 bundle 包含 Markdown、HTML、summary、evidence packet 和 seat matrix。", "source": "local files"},
        ],
        "inferences": [
            {"text": "用户价值应落在最终报告，而不是多页面 dashboard 控件。", "source": "product scope", "strength": "medium"},
            {"text": "薄客户端足够承载提交、状态感知、运行控制、报告查看、追问和归档。", "source": "client flow", "strength": "medium"},
        ],
        "seat_summaries": [
            {"summary": "Report Builder：把问题压缩成结构化最终报告。", "strength": "medium"},
            {"summary": "Dissent Reviewer：保留边界、分歧和失败条件。", "strength": "medium"},
            {"summary": "Human Final Gate：提醒最终裁决留在本地人工控制。", "strength": "medium"},
        ],
        "consensus": [
            "报告是主交付物。",
            "客户端只需要必要状态和运行控制。",
            "dashboard/workbench 只能作为内部 debug/operator aid。",
        ],
        "disagreements": [
            "若未来接入真实 Web seat，应先通过 evidence validator，不能用页面变化当作 answered。",
            "若证据不足，应输出 partial/low reliability，而不是强行给高置信结论。",
        ],
        "evidence_strength": {
            "overall": reliability,
            "items": [
                {"description": "本地 run summary 与报告 bundle 一致。", "strength": "medium"},
                {"description": "seat matrix 明确有效/失败/跳过状态。", "strength": "medium" if valid_seats else "weak"},
                {"description": "外部网页或模型席位证据未生成时不会被冒充。", "strength": "strong"},
            ],
        },
        "risks": [
            "当前最小闭环生成的是本地报告和控制 artifact，不等于真实多模型 Web seat 全量执行。",
            "若 Obsidian 路径未配置，归档会进入本地 pending 目录。",
            "若后续扩展客户端 UI，应继续限制在提交、控制、报告、追问、归档。",
        ],
        "failure_conditions": [
            "无法生成 final_report.md / final_report.html / summary.json / evidence_packet.json / seat_matrix.json。",
            "运行控制只改变前端显示而不改变后端 summary 状态。",
            "报告把推断写成事实，或伪造未执行的外部 seat 证据。",
        ],
        "recommended_actions": [
            "把日常入口固定为 AI Judge Client 或 /api/client/runs。",
            "优先改进最终报告质量和 evidence validator，不扩展 dashboard。",
            "真实 Web seat 接入前，先要求 answer.txt、answer.json、evidence.json 和 trajectory artifacts。",
        ],
        "audit": {
            "generated_at": generated_at,
            "valid_seats": valid_seats,
            "failed_seats": failed_seats,
            "total_seats": total_seats,
            "artifact_paths": [],
        },
    }


def write_report_bundle(report: dict[str, Any], reports_root: Path | None = None) -> dict[str, Any]:
    reports_root = reports_root or default_reports_root()
    run_id = str(report["run_id"])
    run_dir = reports_root / "runs" / run_id
    followups_dir = run_dir / "followups"
    followups_dir.mkdir(parents=True, exist_ok=True)
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
        generated_at=report.get("audit", {}).get("generated_at"),
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
    summary = {
        "schema": SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "title": report.get("title"),
        "mode": report.get("mode"),
        "mode_label": report.get("mode_label"),
        "question": report.get("question"),
        "status": report.get("status", "completed"),
        "created_at": report.get("audit", {}).get("generated_at"),
        "started_at": report.get("audit", {}).get("generated_at"),
        "completed_at": report.get("audit", {}).get("generated_at"),
        "total_seats": total_seats,
        "valid_seats": valid_seats,
        "failed_seats": failed_seats,
        "reliability": report.get("evidence_strength", {}).get("overall", "unknown"),
        "final_report_path": str(final_report_path),
        "html_report_path": str(html_report_path),
        "evidence_packet_path": str(evidence_path),
        "seat_matrix_path": str(seat_matrix_path),
        "human_status": "最终报告已生成，用户可以查看、追问或归档。",
        "controls": {"can_pause": False, "can_resume": False, "can_stop": False, "can_rerun_failed": failed_seats > 0},
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    operator_note_path.write_text(
        "# Operator Note\n\n"
        f"- run_id: {run_id}\n"
        f"- mode: {report.get('mode')}\n"
        f"- failed_seats: {failed_seats}\n"
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
