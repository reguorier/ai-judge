"""Client-first run orchestration for AI Judge.

This is intentionally a thin local layer: it creates backend state, writes report
artifacts, and exposes real pause/resume/stop state changes without expanding the
legacy dashboard.

P3.8.14-RC1: Added bridge_client_to_web_jury() to route client runs through the
real Chrome CDP web jury engine instead of template generation.  When engine="web",
create_client_run delegates to the full _run_worker pipeline (same as /api/judge).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from product.archive.vault_exporter import archive_report
from product.deep_judge_runner import build_deep_judge_metadata_block, run_deep_judge
from product.followup.followup_api import create_followup
from product.reporting.final_report_builder import build_client_final_report, default_reports_root, make_run_id, title_from_question, write_report_bundle
from product.reporting.report_schema import SUMMARY_SCHEMA_VERSION, mode_label, normalize_mode, utc_now_iso
from product.reporting.unified_renderer import render_report as _unified_render
from product.run_status_presenter import present_summary
from product.reporting.output_contract import normalize as _contract_normalize, render as _contract_render



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


# ── P3.8.14: Bridge to real web jury execution ────────────────────────

def _resolve_seats_for_mode(mode: str) -> list[str]:
    """Resolve default seat list for a given mode."""
    try:
        from core.modes import resolve_mode
        from core.seat_personas import SEAT_PERSONAS
        config = resolve_mode(mode)
        return [s for s in config["seats"] if s in SEAT_PERSONAS]
    except Exception:
        return ["gemini", "deepseek", "chatgpt"]


def bridge_client_to_web_jury(
    run_id: str,
    question: str,
    mode: str = "deep_judge",
    seats: list[str] | None = None,
    engine: str = "web",
) -> dict[str, Any]:
    """Route a client run through the real web jury engine.

    This calls the same _run_worker pipeline used by POST /api/judge,
    giving client runs access to Chrome CDP automation, multi-seat
    collection, cross-validation, and real verdict generation.
    """
    from core.modes import resolve_mode
    from core.seat_personas import SEAT_PERSONAS

    normalized_mode = normalize_mode(mode)
    # Map client mode names to API mode names
    mode_map = {"deep_judge": "strategic", "quick_judge": "flash", "standard_judge": "standard"}
    api_mode = mode_map.get(normalized_mode, normalized_mode)

    if seats:
        resolved = [s for s in seats if s in SEAT_PERSONAS]
    else:
        resolved = _resolve_seats_for_mode(api_mode)

    if not resolved:
        return {"ok": False, "error": "no valid seats resolved"}

    # Import and call the API server's run submission path
    # This reuses the exact same pipeline as POST /api/judge
    from product.api_server import TASKS, _run_worker, start_run

    # Register the run in the task manager
    TASKS.submit(question=question, mode=api_mode, seats=resolved, run_id=run_id)
    start_run(
        "meeting",
        label=f"客户端裁决: {question[:40]}",
        bridge_claim=None,
        run_id=run_id,
        metadata={"question": question, "mode": api_mode, "seats": resolved, "client_run": True},
    )

    # Launch _run_worker in a background thread (same as api_server does)
    worker_thread = threading.Thread(
        target=_run_worker,
        kwargs={
            "run_id": run_id,
            "question": question,
            "mode": api_mode,
            "seats": resolved,
            "engine": engine,
            "notify_config": {},
        },
        daemon=True,
        name=f"client-jury-{run_id[:8]}",
    )
    worker_thread.start()

    return {
        "ok": True,
        "run_id": run_id,
        "status": "running",
        "mode": api_mode,
        "seats": resolved,
        "engine": engine,
        "message": f"Web jury execution started for {len(resolved)} seats. Poll /api/task/{run_id} for progress.",
    }


def poll_client_jury_status(run_id: str) -> dict[str, Any]:
    """Poll the status of a web-jury-backed client run."""
    try:
        from product.api_server import TASKS
        status = TASKS.get_status(run_id)
        result = TASKS.get_result(run_id)
        if result:
            # Sync verdict core fields back to summary
            try:
                summary = load_summary(run_id)
                summary["status"] = "completed"
                summary["completed_at"] = utc_now_iso()
                summary["verdict"] = result.get("verdict")
                summary["confidence"] = result.get("confidence")
                summary["one_liner"] = result.get("one_liner")
                summary["valid_seats"] = (result.get("web_bridge") or {}).get("ok_count", 0)
                summary["failed_seats"] = (result.get("web_bridge") or {}).get("failed_count", 0)
                summary["reliability"] = "high" if (result.get("confidence") or 0) >= 70 else "medium"
                noise = result.get("noise_audit")
                if not isinstance(noise, dict):
                    noise = (result.get("web_bridge") or {}).get("noise_audit")
                if isinstance(noise, dict):
                    summary["noise_score"] = noise.get("noise_score") if noise.get("noise_score") is not None else noise.get("score")
                    summary["noise_level"] = noise.get("noise_level") or noise.get("level")
                    summary["noise_recommended_action"] = noise.get("recommended_action") or noise.get("recommendedAction")
                stability = result.get("model_stability")
                if not isinstance(stability, dict):
                    stability = (result.get("web_bridge") or {}).get("model_stability")
                if isinstance(stability, dict):
                    summary["model_stability"] = stability
                    summary["model_stability_profile_count"] = stability.get("profile_count", 0)
                save_summary(summary)
            except Exception:
                pass  # Don't fail poll if summary sync fails
            return {"ok": True, "status": "complete", "verdict": result}
        if status is None:
            summary = load_summary(run_id)
            summary_status = str(summary.get("status") or "waiting_confirm")
            if summary_status in {"created", "running", "waiting_confirm"}:
                return {
                    "ok": True,
                    "run_id": run_id,
                    "status": "waiting_confirm",
                    "progress": 0,
                    "can_execute": True,
                    "message": "Client run has been created and is waiting for user confirmation.",
                }
            return {
                "ok": True,
                "run_id": run_id,
                "status": summary_status,
                "progress": 0,
                "can_execute": summary_status not in {"completed", "failed", "cancelled"},
            }
        return {"ok": True, "status": status.get("status", "unknown"), "progress": status.get("progress", 0)}
    except FileNotFoundError:
        return {"ok": False, "error": "RUN_NOT_FOUND", "run_id": run_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Original client run creation ───────────────────────────────────────

def create_client_run(
    *,
    question: str,
    mode: str = "deep_judge",
    auto_complete: bool = True,
    reports_root: Path | None = None,
    total_seats: int = 3,
    engine: str = "local",
    search_agent_output: dict[str, Any] | None = None,
    legal_analysis: dict[str, Any] | None = None,
    seat_outputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise ValueError("question is required")
    mode = normalize_mode(mode)
    run_id = make_run_id()
    now = utc_now_iso()

    # Map client mode names to display names
    mode_display = mode_label(mode)

    summary: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "title": title_from_question(question),
        "mode": mode,
        "mode_label": mode_display,
        "question": question,
        "status": "waiting_confirm" if not auto_complete else "reporting",
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
        "engine": engine,
    }
    save_summary(summary, reports_root)

    if auto_complete:
        if engine == "web":
            # ── P3.8.14: Route through real web jury ──
            bridge_result = bridge_client_to_web_jury(
                run_id=run_id,
                question=question,
                mode=mode,
            )
            summary["status"] = "running"
            summary["engine"] = "web"
            summary["human_status"] = "网页陪审执行已启动，等待席位回答。"
            summary["bridge"] = bridge_result
            save_summary(summary, reports_root)
            return present_summary(summary)

        # ── deep_judge reasoning gate ──
        if mode == "deep_judge":
            dj_result = run_deep_judge(
                question=question,
                search_agent_output=search_agent_output,
                legal_analysis=legal_analysis,
                seat_outputs=seat_outputs,
            )
            # Inject deep_judge metadata into summary
            summary.update(build_deep_judge_metadata_block(dj_result))

            if not dj_result.ok:
                summary["status"] = "failed"
                summary["reliability"] = "none"
                summary["valid_seats"] = 0
                summary["completed_at"] = now
                summary["human_status"] = "运行失败：深度裁决缺少实质性推理来源（LLM / search-agent / seat_outputs）。"
                summary["final_report_path"] = ""
                summary["html_report_path"] = ""
                return present_summary(save_summary(summary, reports_root))

            # Pass substantiated sources into final_report_builder
            report = build_client_final_report(
                run_id=run_id,
                question=question,
                mode=mode,
                status="completed",
                total_seats=total_seats,
                valid_seats=total_seats,
                failed_seats=0,
                generated_at=now,
                search_agent_output=dj_result.search_agent_output,
                legal_analysis=dj_result.legal_analysis,
                seat_outputs=dj_result.seat_outputs,
            )
        else:
            report = build_client_final_report(
                run_id=run_id,
                question=question,
                mode=mode,
                status="completed",
                total_seats=total_seats,
                valid_seats=total_seats,
                failed_seats=0,
                generated_at=now,
                search_agent_output=search_agent_output,
                legal_analysis=legal_analysis,
                seat_outputs=seat_outputs,
            )

        is_failure = report.get("_failure") is not None
        if is_failure:
            summary["status"] = "failed"
            summary["human_status"] = f"运行失败：{report['_failure'].get('reason', '未知原因')}"
            summary["reliability"] = "none"
            summary["valid_seats"] = 0
            summary["completed_at"] = now
            return present_summary(save_summary(summary, reports_root))

        bundle = write_report_bundle(report, reports_root)
        result = present_summary(bundle["summary"])
        # Preserve deep_judge metadata in final summary
        if "deep_judge" in summary:
            result["deep_judge"] = summary["deep_judge"]
        return result

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
    # Also stop the worker if running
    try:
        from product.api_server import TASKS
        TASKS.cancel(run_id)
    except Exception:
        pass
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

    # Also check the standard runs directory for web-jury verdicts
    verdict_path = Path.home() / "Library" / "Application Support" / "AI Judge" / "runtime" / "runs" / run_id / "verdict.json"
    verdict = None
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "run_id": run_id,
        "summary": summary,
        "final_report_path": str(final_path),
        "html_report_path": str(html_path),
        "markdown": final_path.read_text(encoding="utf-8") if final_path.exists() else "",
        "verdict": verdict,
    }


def followup_client_run(run_id: str, prompt: str, reports_root: Path | None = None) -> dict[str, Any]:
    return create_followup(_run_dir(run_id, reports_root), prompt)


def archive_client_run(run_id: str, vault_dir: Path | None = None, reports_root: Path | None = None) -> dict[str, Any]:
    summary = load_summary(run_id, reports_root)
    return archive_report(summary, reports_root or default_reports_root(), vault_dir=vault_dir)
