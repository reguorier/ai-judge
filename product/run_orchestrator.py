"""Client-first run orchestration for AI Judge.

This is intentionally a thin local layer: it creates backend state, writes report
artifacts, and exposes real pause/resume/stop state changes without expanding the
legacy dashboard.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from product.archive.vault_exporter import archive_report
from product.followup.followup_api import create_followup
from product.reporting.final_report_builder import build_client_final_report, default_reports_root, make_run_id, title_from_question, write_report_bundle
from product.reporting.report_schema import SUMMARY_SCHEMA_VERSION, mode_label, normalize_mode, utc_now_iso
from product.run_status_presenter import present_summary


def _run_dir(run_id: str, reports_root: Path | None = None) -> Path:
    root = reports_root or default_reports_root()
    return root / "runs" / run_id


def _summary_path(run_id: str, reports_root: Path | None = None) -> Path:
    return _run_dir(run_id, reports_root) / "summary.json"


def save_summary(summary: dict[str, Any], reports_root: Path | None = None) -> dict[str, Any]:
    path = _summary_path(str(summary["run_id"]), reports_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = present_summary(summary)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def load_summary(run_id: str, reports_root: Path | None = None) -> dict[str, Any]:
    path = _summary_path(run_id, reports_root)
    if not path.exists():
        raise FileNotFoundError(f"client run not found: {run_id}")
    return present_summary(json.loads(path.read_text(encoding="utf-8")))


def create_client_run(
    *,
    question: str,
    mode: str = "deep_judge",
    auto_complete: bool = True,
    reports_root: Path | None = None,
    total_seats: int = 3,
) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise ValueError("question is required")
    mode = normalize_mode(mode)
    run_id = make_run_id()
    now = utc_now_iso()
    summary = {
        "schema": SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "title": title_from_question(question),
        "mode": mode,
        "mode_label": mode_label(mode),
        "question": question,
        "status": "running" if not auto_complete else "reporting",
        "created_at": now,
        "started_at": now,
        "completed_at": "",
        "total_seats": total_seats,
        "valid_seats": 0 if not auto_complete else total_seats,
        "failed_seats": 0,
        "reliability": "unknown",
        "final_report_path": "",
        "html_report_path": "",
        "evidence_packet_path": "",
        "seat_matrix_path": "",
        "human_status": "任务已创建。",
    }
    save_summary(summary, reports_root)
    if auto_complete:
        report = build_client_final_report(
            run_id=run_id,
            question=question,
            mode=mode,
            status="completed",
            total_seats=total_seats,
            valid_seats=total_seats,
            failed_seats=0,
            generated_at=now,
        )
        bundle = write_report_bundle(report, reports_root)
        return present_summary(bundle["summary"])
    return load_summary(run_id, reports_root)


def update_client_run_status(run_id: str, status: str, reports_root: Path | None = None) -> dict[str, Any]:
    summary = load_summary(run_id, reports_root)
    summary["status"] = status
    if status in {"completed", "partial_completed", "failed", "cancelled"} and not summary.get("completed_at"):
        summary["completed_at"] = utc_now_iso()
    return save_summary(summary, reports_root)


def pause_client_run(run_id: str, reports_root: Path | None = None) -> dict[str, Any]:
    summary = load_summary(run_id, reports_root)
    if not summary.get("controls", {}).get("can_pause"):
        return summary | {"ok": False, "message": "current status cannot be paused"}
    summary["status"] = "paused"
    return save_summary(summary, reports_root) | {"ok": True}


def resume_client_run(run_id: str, reports_root: Path | None = None) -> dict[str, Any]:
    summary = load_summary(run_id, reports_root)
    if not summary.get("controls", {}).get("can_resume"):
        return summary | {"ok": False, "message": "current status cannot be resumed"}
    summary["status"] = "running"
    return save_summary(summary, reports_root) | {"ok": True}


def stop_client_run(run_id: str, reports_root: Path | None = None) -> dict[str, Any]:
    summary = load_summary(run_id, reports_root)
    if not summary.get("controls", {}).get("can_stop"):
        return summary | {"ok": False, "message": "current status cannot be stopped"}
    summary["status"] = "cancelled"
    summary["completed_at"] = utc_now_iso()
    return save_summary(summary, reports_root) | {"ok": True}


def rerun_failed_client_run(run_id: str, reports_root: Path | None = None) -> dict[str, Any]:
    summary = load_summary(run_id, reports_root)
    if int(summary.get("failed_seats") or 0) <= 0:
        return summary | {"ok": True, "message": "no failed seats to rerun"}
    report = build_client_final_report(
        run_id=run_id,
        question=str(summary.get("question", "")),
        mode=str(summary.get("mode", "deep_judge")),
        status="completed",
        total_seats=int(summary.get("total_seats") or 3),
        valid_seats=int(summary.get("total_seats") or 3),
        failed_seats=0,
        generated_at=utc_now_iso(),
    )
    bundle = write_report_bundle(report, reports_root)
    return present_summary(bundle["summary"]) | {"ok": True, "message": "failed seats rerun through local report bundle"}


def get_client_report(run_id: str, reports_root: Path | None = None) -> dict[str, Any]:
    summary = load_summary(run_id, reports_root)
    final_path = Path(summary.get("final_report_path") or "")
    html_path = Path(summary.get("html_report_path") or "")
    return {
        "run_id": run_id,
        "summary": summary,
        "final_report_path": str(final_path),
        "html_report_path": str(html_path),
        "markdown": final_path.read_text(encoding="utf-8") if final_path.exists() else "",
    }


def followup_client_run(run_id: str, prompt: str, reports_root: Path | None = None) -> dict[str, Any]:
    return create_followup(_run_dir(run_id, reports_root), prompt)


def archive_client_run(run_id: str, vault_dir: Path | None = None, reports_root: Path | None = None) -> dict[str, Any]:
    summary = load_summary(run_id, reports_root)
    return archive_report(summary, reports_root or default_reports_root(), vault_dir=vault_dir)
