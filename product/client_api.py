"""Minimal report-first client API for AI Judge."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from flask import Blueprint, jsonify, request

from product.run_orchestrator import (
    archive_client_run,
    create_client_run,
    followup_client_run,
    get_client_report,
    load_summary,
    pause_client_run,
    rerun_failed_client_run,
    resume_client_run,
    stop_client_run,
)

client_blueprint = Blueprint("ai_judge_client", __name__, url_prefix="/api/client")


def _json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def _payload() -> dict:
    return request.get_json(silent=True) or {}


def _run_action(run_id: str, action: Callable):
    try:
        result = action(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    return jsonify(result)


@client_blueprint.post("/runs")
def post_client_run():
    data = _payload()
    try:
        summary = create_client_run(
            question=str(data.get("question") or ""),
            mode=str(data.get("mode") or "deep_judge"),
            auto_complete=bool(data.get("auto_complete", True)),
            total_seats=int(data.get("total_seats") or 3),
        )
    except ValueError as exc:
        return _json_error(str(exc), 400)
    return jsonify({"ok": True, "run": summary, "human_status": summary.get("human_status")}), 201


@client_blueprint.get("/runs/<run_id>")
def get_client_run(run_id: str):
    return _run_action(run_id, load_summary)


@client_blueprint.post("/runs/<run_id>/pause")
def post_pause(run_id: str):
    return _run_action(run_id, pause_client_run)


@client_blueprint.post("/runs/<run_id>/resume")
def post_resume(run_id: str):
    return _run_action(run_id, resume_client_run)


@client_blueprint.post("/runs/<run_id>/stop")
def post_stop(run_id: str):
    return _run_action(run_id, stop_client_run)


@client_blueprint.post("/runs/<run_id>/rerun-failed")
def post_rerun_failed(run_id: str):
    return _run_action(run_id, rerun_failed_client_run)


@client_blueprint.get("/runs/<run_id>/report")
def get_report(run_id: str):
    return _run_action(run_id, get_client_report)


@client_blueprint.post("/runs/<run_id>/followup")
def post_followup(run_id: str):
    data = _payload()
    prompt = str(data.get("prompt") or "")
    try:
        result = followup_client_run(run_id, prompt)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    return jsonify({"ok": True, **result})


@client_blueprint.post("/runs/<run_id>/archive")
def post_archive(run_id: str):
    data = _payload()
    vault = data.get("vault_dir")
    try:
        result = archive_client_run(run_id, vault_dir=Path(vault) if vault else None)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    return jsonify({"ok": True, **result})
