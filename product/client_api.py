"""Minimal report-first client API for AI Judge.

P3.8.14-RC1: Added /runs/<id>/execute and /runs/<id>/poll endpoints to bridge
client runs to the real web jury engine.  Also added engine parameter to POST /runs.

Backend Client API Gap Closeout (2026-06-09):
- Added GET /api/client/capabilities
- Added GET /api/client/runs/:runId/events (SSE snapshot)
- Patched GET /api/client/runs/:runId to strip local absolute paths
- Patched GET /api/client/runs/:runId/report to return safe HTML or canonical contract JSON
- POST /api/client/runs rejects permission_mode: "admin"
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from flask import Blueprint, Response as FlaskResponse, jsonify, request, stream_with_context

from product.run_orchestrator import (
    archive_client_run,
    bridge_client_to_web_jury,
    create_client_run,
    followup_client_run,
    get_client_report,
    load_summary,
    pause_client_run,
    poll_client_jury_status,
    rerun_failed_client_run,
    resume_client_run,
    stop_client_run,
)
from product.fdjp.service import (
    build_fdjp_client_contract,
    load_dimension_audit,
    load_dimension_report_blocks,
    run_dimension_audit,
)
from product.search_agent import search_legal
from product.reporting.output_contract import normalize as _contract_normalize, render as _contract_render
from product.reporting.final_report_builder import default_reports_root
from core.model_stability import load_model_stability_profiles, model_stability_summary

client_blueprint = Blueprint("ai_judge_client", __name__, url_prefix="/api/client")


# ── Helpers ───────────────────────────────────────────────────────────

def _json_error(
    message: str,
    status: int = 400,
    *,
    reason: str | None = None,
    next_action: str | None = None,
    source: str = "client_api",
    run_id: str | None = None,
):
    payload = {
        "ok": False,
        "status": status,
        "error": message,
        "reason": reason or message,
        "next_action": next_action or "检查请求参数或稍后重试。",
        "trace_id": f"client-api-{int(time.time() * 1000)}",
        "source": source,
    }
    if run_id:
        payload["run_id"] = run_id
    return jsonify(payload), status


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


# ── Path sanitization ─────────────────────────────────────────────────

_LOCAL_PATH_PATTERN = re.compile(
    r"(/Users/|/home/|C:\\|\.ai-judge/runs/|file:///)",
    re.IGNORECASE,
)

_INTERNAL_PATH_FIELDS = frozenset({
    "final_report_path",
    "html_report_path",
    "evidence_packet_path",
    "seat_matrix_path",
    "noise_audit_path",
    "model_stability_path",
    "strategy_intelligence_path",
    "strategy_state_path",
    "meta_judge_path",
    "meta_judge_state_path",
    "model_weights_path",
    "autonomous_strategy_path",
    "asg_state_path",
    "production_strategies_path",
    "market_simulation_path",
    "market_simulation_state_path",
    "decision_os_path",
    "decision_os_state_path",
    "self_improving_loop_path",
    "self_improving_loop_state_path",
    "decision_policy_config_path",
    "autonomous_economy_path",
    "autonomous_economy_state_path",
    "recursive_civilization_path",
    "recursive_civilization_state_path",
    "fdjp_artifact_path",
})


def _has_local_path(value: str) -> bool:
    """Check if a string contains any local absolute path pattern."""
    if not isinstance(value, str):
        return False
    return bool(_LOCAL_PATH_PATTERN.search(value))


def _sanitize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Strip local absolute paths from a client run summary.

    Replaces internal disk paths with public route identifiers or empty strings.
    """
    clean = dict(summary)
    for field in _INTERNAL_PATH_FIELDS:
        if field in clean:
            del clean[field]

    # Strip any remaining string values that happen to be absolute paths
    for key, value in list(clean.items()):
        if isinstance(value, str) and _has_local_path(value):
            clean[key] = ""

    return clean


def _run_public_dto(run_id: str) -> dict[str, Any]:
    """Build a public-safe run DTO from the internal summary."""
    summary = load_summary(run_id)
    clean = _sanitize_summary(summary)

    status = str(clean.get("status", "unknown"))
    report_available = status in {"completed", "partial_completed"}

    # Build artifact list from route identifiers only
    artifacts: list[dict[str, Any]] = []

    # Report artifact
    if report_available:
        artifacts.append({
            "filename": "report",
            "route": f"/api/client/runs/{run_id}/report",
            "kind": "report",
            "contentType": "text/html",
        })

    # Seat matrix
    artifacts.append({
        "filename": "seat_matrix",
        "route": f"/api/client/runs/{run_id}/report-blocks",
        "kind": "report_blocks",
        "contentType": "application/json",
    })
    if clean.get("noise_score") is not None:
        artifacts.append({
            "filename": "noise_audit",
            "route": f"/api/client/runs/{run_id}/noise-audit",
            "kind": "noise_audit",
            "contentType": "application/json",
        })
    if clean.get("model_stability_profile_count") is not None:
        artifacts.append({
            "filename": "model_stability",
            "route": "/api/client/model-stability",
            "kind": "model_stability",
            "contentType": "application/json",
        })
    if clean.get("top_model") is not None:
        artifacts.append({
            "filename": "meta_judge",
            "route": f"/api/client/runs/{run_id}/meta-judge",
            "kind": "meta_judge",
            "contentType": "application/json",
        })
    if clean.get("asg_accepted_strategy_count") is not None:
        artifacts.append({
            "filename": "autonomous_strategy",
            "route": f"/api/client/runs/{run_id}/autonomous-strategy",
            "kind": "autonomous_strategy",
            "contentType": "application/json",
        })
        artifacts.append({
            "filename": "production_strategies",
            "route": "/api/client/production-strategies",
            "kind": "production_strategies",
            "contentType": "application/json",
        })
        artifacts.append({
            "filename": "model_weights",
            "route": "/api/client/model-weights",
            "kind": "model_weights",
            "contentType": "application/json",
        })
    if clean.get("msl_scenario_count") is not None:
        artifacts.append({
            "filename": "market_simulation",
            "route": f"/api/client/runs/{run_id}/market-simulation",
            "kind": "market_simulation",
            "contentType": "application/json",
        })
    if clean.get("decision_os_top_action") is not None:
        artifacts.append({
            "filename": "decision_os",
            "route": f"/api/client/runs/{run_id}/decision-os",
            "kind": "decision_os",
            "contentType": "application/json",
        })
    if clean.get("siel_outcome_signal_count") is not None:
        artifacts.append({
            "filename": "self_improving_loop",
            "route": f"/api/client/runs/{run_id}/self-improving-loop",
            "kind": "self_improving_loop",
            "contentType": "application/json",
        })
        artifacts.append({
            "filename": "decision_policy_config",
            "route": "/api/client/decision-policy-config",
            "kind": "decision_policy_config",
            "contentType": "application/json",
        })
    if clean.get("ael_agent_count") is not None:
        artifacts.append({
            "filename": "autonomous_economy",
            "route": f"/api/client/runs/{run_id}/autonomous-economy",
            "kind": "autonomous_economy",
            "contentType": "application/json",
        })
    if clean.get("rcl_civilization_count") is not None:
        artifacts.append({
            "filename": "recursive_civilization",
            "route": f"/api/client/runs/{run_id}/recursive-civilization",
            "kind": "recursive_civilization",
            "contentType": "application/json",
        })

    # Build seat list from valid_seats/total_seats
    seats: list[dict[str, Any]] = []
    valid = int(clean.get("valid_seats") or 0)
    failed = int(clean.get("failed_seats") or 0)
    total = int(clean.get("total_seats") or 0)
    for i in range(total):
        seat_status = (
            "answered" if i < valid
            else "failed" if i < valid + failed
            else "pending"
        )
        seats.append({
            "seatId": f"seat-{i}",
            "status": seat_status,
        })

    return {
        "runId": clean.get("run_id", run_id),
        "status": status,
        "mode": clean.get("mode", ""),
        "createdAt": clean.get("created_at", ""),
        "updatedAt": clean.get("completed_at", clean.get("created_at", "")),
        "seats": seats,
        "report": {
            "available": report_available,
            "route": f"/api/client/runs/{run_id}/report" if report_available else "",
            "contentType": "text/html",
        },
        "noise": {
            "score": clean.get("noise_score"),
            "level": clean.get("noise_level", ""),
            "recommendedAction": clean.get("noise_recommended_action", ""),
            "available": clean.get("noise_score") is not None,
        },
        "modelStability": {
            "available": clean.get("model_stability_profile_count") is not None,
            "profileCount": clean.get("model_stability_profile_count", 0),
            "route": "/api/client/model-stability",
        },
        "metaJudge": {
            "available": clean.get("top_model") is not None,
            "topModel": clean.get("top_model", ""),
            "topModelScore": clean.get("top_model_score", 0),
            "deprecatedModelCount": clean.get("deprecated_model_count", 0),
            "route": f"/api/client/runs/{run_id}/meta-judge",
            "weightsRoute": "/api/client/model-weights",
        },
        "autonomousStrategy": {
            "available": clean.get("asg_accepted_strategy_count") is not None,
            "acceptedCount": clean.get("asg_accepted_strategy_count", 0),
            "productionCount": clean.get("asg_production_strategy_count", 0),
            "topStrategyId": clean.get("asg_top_strategy_id", ""),
            "route": f"/api/client/runs/{run_id}/autonomous-strategy",
            "productionRoute": "/api/client/production-strategies",
        },
        "marketSimulation": {
            "available": clean.get("msl_scenario_count") is not None,
            "scenarioCount": clean.get("msl_scenario_count", 0),
            "monteCarloRuns": clean.get("msl_monte_carlo_runs", 0),
            "robustStrategyCount": clean.get("msl_robust_strategy_count", 0),
            "topScenarioRisk": clean.get("msl_top_scenario_risk", 0),
            "worstScenarioId": clean.get("msl_worst_scenario_id", ""),
            "route": f"/api/client/runs/{run_id}/market-simulation",
        },
        "decisionOS": {
            "available": clean.get("decision_os_top_action") is not None,
            "topAction": clean.get("decision_os_top_action", ""),
            "executedActionCount": clean.get("decision_os_executed_action_count", 0),
            "rejectedActionCount": clean.get("decision_os_rejected_action_count", 0),
            "portfolioExposure": clean.get("decision_os_portfolio_exposure", 0),
            "blockedDecisionCount": clean.get("decision_os_blocked_decision_count", 0),
            "route": f"/api/client/runs/{run_id}/decision-os",
        },
        "selfImprovingLoop": {
            "available": clean.get("siel_outcome_signal_count") is not None,
            "outcomeSignalCount": clean.get("siel_outcome_signal_count", 0),
            "meanValueError": clean.get("siel_mean_value_error", 0),
            "policyUpdateCount": clean.get("siel_policy_update_count", 0),
            "mutationCount": clean.get("siel_mutation_count", 0),
            "learningScore": clean.get("siel_learning_score", 0),
            "policyDirection": clean.get("siel_policy_direction", "stable"),
            "decisionPolicyConfigVersion": clean.get("decision_policy_config_version", 1),
            "route": f"/api/client/runs/{run_id}/self-improving-loop",
            "policyConfigRoute": "/api/client/decision-policy-config",
        },
        "autonomousEconomy": {
            "available": clean.get("ael_agent_count") is not None,
            "agentCount": clean.get("ael_agent_count", 0),
            "activeAgentCount": clean.get("ael_active_agent_count", 0),
            "terminatedAgentCount": clean.get("ael_terminated_agent_count", 0),
            "totalCapital": clean.get("ael_total_capital", 0),
            "topAgentId": clean.get("ael_top_agent_id", ""),
            "topStrategyId": clean.get("ael_top_strategy_id", ""),
            "topAgentCapital": clean.get("ael_top_agent_capital", 0),
            "allocationEntropy": clean.get("ael_allocation_entropy", 0),
            "lifecycleEventCount": clean.get("ael_lifecycle_event_count", 0),
            "cloneCount": clean.get("ael_clone_count", 0),
            "terminationCount": clean.get("ael_termination_count", 0),
            "totalCapitalReallocated": clean.get("ael_total_capital_reallocated", 0),
            "route": f"/api/client/runs/{run_id}/autonomous-economy",
        },
        "recursiveCivilization": {
            "available": clean.get("rcl_civilization_count") is not None,
            "civilizationCount": clean.get("rcl_civilization_count", 0),
            "activeCivilizationCount": clean.get("rcl_active_civilization_count", 0),
            "collapsedCivilizationCount": clean.get("rcl_collapsed_civilization_count", 0),
            "topCivilizationId": clean.get("rcl_top_civilization_id", ""),
            "topGovernanceArchetype": clean.get("rcl_top_governance_archetype", ""),
            "governanceMutationCount": clean.get("rcl_governance_mutation_count", 0),
            "interactionCount": clean.get("rcl_interaction_count", 0),
            "metaCivilizationCount": clean.get("rcl_meta_civilization_count", 0),
            "emergentBehaviorCount": clean.get("rcl_emergent_behavior_count", 0),
            "civilizationEntropy": clean.get("rcl_civilization_entropy", 0),
            "route": f"/api/client/runs/{run_id}/recursive-civilization",
        },
        "artifacts": artifacts,
    }


# ── Capabilities ──────────────────────────────────────────────────────

@client_blueprint.get("/capabilities")
def get_capabilities():
    """Public client capabilities endpoint.

    Returns a safe contract describing what the backend can do,
    without exposing local machine paths or secrets.
    """
    try:
        from bridges.web_seat_bridge import bridge_status
        bridge = bridge_status()
    except Exception:
        bridge = None

    backend_live = True
    bridge_ok = bridge is not None
    bridge_mode = None
    available_seats: list[str] = []
    missing_seats: list[str] = []

    if bridge:
        bridge_mode = str(bridge.get("mode") or "")
        seats_list = bridge.get("seats") or []
        if isinstance(seats_list, list):
            for s in seats_list:
                if isinstance(s, dict):
                    seat_id = s.get("id") or s.get("seat") or ""
                    if seat_id:
                        available_seats.append(str(seat_id))

    can_start = backend_live

    status = "ok" if (backend_live and bridge_ok) else "degraded" if backend_live else "unavailable"

    return jsonify({
        "status": status,
        "backendLive": backend_live,
        "canStartRun": can_start,
        "canRevealSecrets": False,
        "bridge": {
            "ok": bridge_ok,
            "mode": bridge_mode,
            "missingSeats": missing_seats,
            "availableSeats": available_seats,
        },
        "routes": {
            "health": "/api/health",
            "capabilities": "/api/client/capabilities",
            "runs": "/api/client/runs",
            "runDetail": "/api/client/runs/:id",
            "runEvents": "/api/client/runs/:id/events",
            "runReport": "/api/client/runs/:id/report",
            "noiseAudit": "/api/client/runs/:id/noise-audit",
            "modelStability": "/api/client/model-stability",
            "metaJudge": "/api/client/runs/:id/meta-judge",
            "modelWeights": "/api/client/model-weights",
            "autonomousStrategy": "/api/client/runs/:id/autonomous-strategy",
            "productionStrategies": "/api/client/production-strategies",
            "marketSimulation": "/api/client/runs/:id/market-simulation",
            "decisionOS": "/api/client/runs/:id/decision-os",
            "selfImprovingLoop": "/api/client/runs/:id/self-improving-loop",
            "decisionPolicyConfig": "/api/client/decision-policy-config",
            "autonomousEconomy": "/api/client/runs/:id/autonomous-economy",
            "recursiveCivilization": "/api/client/runs/:id/recursive-civilization",
        },
    })


@client_blueprint.get("/model-stability")
def get_model_stability():
    try:
        store = load_model_stability_profiles()
        return jsonify({"ok": True, "modelStability": model_stability_summary(store, limit=50)})
    except Exception as exc:
        return _json_error(f"model stability read failed: {exc}", 500)


@client_blueprint.get("/model-weights")
def get_model_weights():
    path = default_reports_root() / "runtime" / "model_weights.json"
    try:
        if path.exists() and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return jsonify({"ok": True, "modelWeights": payload})
    except Exception as exc:
        return _json_error(f"model weights read failed: {exc}", 500)
    return _json_error("MODEL_WEIGHTS_NOT_FOUND", 404)


@client_blueprint.get("/production-strategies")
def get_production_strategies():
    path = default_reports_root() / "runtime" / "production_strategies.json"
    try:
        if path.exists() and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return jsonify({"ok": True, "productionStrategies": payload})
    except Exception as exc:
        return _json_error(f"production strategies read failed: {exc}", 500)
    return _json_error("PRODUCTION_STRATEGIES_NOT_FOUND", 404)


@client_blueprint.get("/decision-policy-config")
def get_decision_policy_config():
    path = default_reports_root() / "runtime" / "decision_policy_config.json"
    try:
        if path.exists() and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return jsonify({"ok": True, "decisionPolicyConfig": payload})
    except Exception as exc:
        return _json_error(f"decision policy config read failed: {exc}", 500)
    return _json_error("DECISION_POLICY_CONFIG_NOT_FOUND", 404)


# ── POST /runs ────────────────────────────────────────────────────────

@client_blueprint.post("/runs")
def post_client_run():
    """Create a client run. Pass engine="web" for real web jury execution.

    Rejects permission_mode: "admin" — public client must not escalate.
    """
    data = _payload()

    # ── Reject admin permission_mode ──
    if str(data.get("permission_mode") or "").lower() == "admin":
        return _json_error("permission_mode 'admin' rejected on public client API", 403)

    question = str(data.get("question") or "")
    mode = str(data.get("mode") or "deep_judge")

    # ── inject search agent output for deep_judge ──
    search_agent_output = None
    if mode == "deep_judge":
        try:
            search_agent_output = search_legal(question)
        except Exception:
            search_agent_output = None  # graceful degradation

    try:
        summary = create_client_run(
            question=question,
            mode=mode,
            auto_complete=bool(data.get("auto_complete", True)),
            total_seats=int(data.get("total_seats") or 3),
            engine=str(data.get("engine") or "local"),
            search_agent_output=search_agent_output,
        )
    except ValueError as exc:
        return _json_error(str(exc), 400)
    return jsonify({
        "ok": True,
        "run": _sanitize_summary(summary),
        "human_status": summary.get("human_status"),
    }), 201


# ── GET /runs/:id ─────────────────────────────────────────────────────

@client_blueprint.get("/runs/<run_id>")
def get_client_run(run_id: str):
    """Return sanitized public run DTO — no local absolute paths."""
    try:
        dto = _run_public_dto(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    return jsonify(dto)


# ── POST /runs/:id/execute ────────────────────────────────────────────

@client_blueprint.post("/runs/<run_id>/execute")
def post_execute(run_id: str):
    """P3.8.14: Trigger real web jury execution for an existing client run.

    This bridges the client run to the full Chrome CDP pipeline:
    prompt_resonance → web_seat_bridge → 13 AI platforms → scoring → verdict.
    """
    data = _payload()
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)

    question = summary.get("question", "")
    mode = summary.get("mode", "deep_judge")
    seats = data.get("seats")

    try:
        result = bridge_client_to_web_jury(
            run_id=run_id,
            question=question,
            mode=mode,
            seats=seats if isinstance(seats, list) else None,
        )
    except Exception as exc:
        return _json_error(str(exc), 500)

    return jsonify(result)


# ── GET /runs/:id/poll ────────────────────────────────────────────────

@client_blueprint.get("/runs/<run_id>/poll")
def get_poll(run_id: str):
    """P3.8.14: Poll the status of a web-jury-backed client run.

    Returns the verdict when complete, or progress info while running.
    """
    result = poll_client_jury_status(run_id)
    if not result.get("ok"):
        return _json_error(result.get("error", "poll failed"), 404)
    return jsonify(result)


# ── Run control ───────────────────────────────────────────────────────

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


# ── Events (SSE snapshot) ─────────────────────────────────────────────

def _load_verdict_json(run_id: str) -> dict[str, Any] | None:
    """Try loading verdict.json from the real runs directory."""
    verdict_path = Path.home() / "Library" / "Application Support" / "AI Judge" / "runtime" / "runs" / run_id / "verdict.json"
    if verdict_path.exists():
        try:
            return json.loads(verdict_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


@client_blueprint.get("/runs/<run_id>/events")
def get_events(run_id: str):
    """SSE-compatible event stream for a client run.

    Returns a snapshot of run status, seat statuses, artifact pointers,
    and a terminal done/failed event. True live SSE is not yet wired
    to the worker's internal event bus, so this emits the current state
    as a complete event batch.
    """
    def generate():
        try:
            summary = load_summary(run_id)
        except FileNotFoundError:
            yield f"event: error\ndata: {json.dumps({'runId': run_id, 'error': 'RUN_NOT_FOUND'})}\n\n"
            return

        verdict = _load_verdict_json(run_id)
        status = str(summary.get("status", "unknown"))
        valid = int(summary.get("valid_seats") or 0)
        total = int(summary.get("total_seats") or 0)
        failed = int(summary.get("failed_seats") or 0)

        # 1) run_status
        yield f"event: run_status\ndata: {json.dumps({'runId': run_id, 'status': status})}\n\n"

        # 2) seat_status for each seat
        verdict_seats = verdict.get("seats", []) if verdict else []
        for i, seat in enumerate(verdict_seats):
            seat_id = str(seat.get("seat", f"seat-{i}"))
            seat_score = seat.get("score", 0)
            seat_status = "answered" if seat_score > 0 else "failed"
            yield f"event: seat_status\ndata: {json.dumps({'runId': run_id, 'seatId': seat_id, 'status': seat_status, 'score': seat_score})}\n\n"

        # 3) artifact events
        if status in {"completed", "partial_completed"}:
            yield f"event: artifact\ndata: {json.dumps({'runId': run_id, 'filename': 'report.html', 'route': f'/api/client/runs/{run_id}/report'})}\n\n"
        if summary.get("noise_score") is not None:
            yield f"event: noise_audit\ndata: {json.dumps({'runId': run_id, 'score': summary.get('noise_score'), 'level': summary.get('noise_level'), 'recommendedAction': summary.get('noise_recommended_action')})}\n\n"

        # 4) terminal
        terminal_status = "completed" if status in {"completed", "partial_completed"} else ("failed" if status == "failed" else "running")
        yield f"event: done\ndata: {json.dumps({'runId': run_id, 'status': terminal_status})}\n\n"

    return FlaskResponse(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Report ────────────────────────────────────────────────────────────

def _build_safe_report(run_id: str) -> dict[str, Any]:
    """Build a safe report: either canonical contract JSON or backend-rendered HTML.

    Accept header controls format:
    - Accept: application/json → canonical contract JSON
    - default → text/html backend-rendered using ReportContractSchema chain

    Returns a dict with: body (str), content_type, status_code
    """
    summary = load_summary(run_id)
    status = str(summary.get("status", "unknown"))

    # Try loading verdict.json for canonical contract
    verdict = None
    verdict_path = Path.home() / "Library" / "Application Support" / "AI Judge" / "runtime" / "runs" / run_id / "verdict.json"
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except Exception:
            verdict = None

    # Also check the summary's own report paths
    _html_raw = summary.get("html_report_path") or ""
    _final_raw = summary.get("final_report_path") or ""
    html_path = Path(_html_raw) if _html_raw else None
    final_path = Path(_final_raw) if _final_raw else None

    # Best source: verdict.json (canonical contract present)
    if verdict:
        contract = _contract_normalize(verdict)
        if contract and contract.get("verdict") not in {"unknown", ""}:
            return {
                "body": _contract_render(contract, "html"),
                "content_type": "text/html; charset=utf-8",
                "status_code": 200,
            }

    # Fallback: render from existing report files on disk
    if html_path and html_path.exists() and html_path.is_file():
        html_body = html_path.read_text(encoding="utf-8")
        # Path leak check
        if _has_local_path(html_body):
            cleaned = _LOCAL_PATH_PATTERN.sub("[sanitized]", html_body)
            return {
                "body": cleaned,
                "content_type": "text/html; charset=utf-8",
                "status_code": 200,
            }
        return {
            "body": html_body,
            "content_type": "text/html; charset=utf-8",
            "status_code": 200,
        }

    if final_path and final_path.exists() and final_path.is_file():
        md_body = final_path.read_text(encoding="utf-8")
        if _has_local_path(md_body):
            return {
                "body": json.dumps({
                    "error": "REPORT_CONTAINS_LOCAL_PATHS",
                    "runId": run_id,
                    "status": status,
                }),
                "content_type": "application/json",
                "status_code": 500,
            }
        return {
            "body": md_body,
            "content_type": "text/markdown; charset=utf-8",
            "status_code": 200,
        }

    # No report: return structured error
    if status in {"completed", "partial_completed"}:
        return {
            "body": json.dumps({
                "ok": False,
                "http_status": 409,
                "error": "REPORT_CONTRACT_NOT_AVAILABLE",
                "runId": run_id,
                "status": status,
                "reason": "No verdict.json and no report file found on disk.",
                "next_action": "Inspect run artifacts or regenerate the report.",
                "trace_id": f"client-report-{int(time.time() * 1000)}",
                "source": "client_report",
            }),
            "content_type": "application/json",
            "status_code": 409,
        }

    return {
        "body": json.dumps({
            "ok": False,
            "http_status": 404,
            "error": "REPORT_NOT_READY",
            "runId": run_id,
            "status": status,
            "reason": f"Run is in status '{status}'. Report not yet available.",
            "next_action": "Poll the run status again before opening the report.",
            "trace_id": f"client-report-{int(time.time() * 1000)}",
            "source": "client_report",
        }),
        "content_type": "application/json",
        "status_code": 404,
    }
@client_blueprint.get("/runs/<run_id>/report")
def get_report(run_id: str):
    """Return safe, backend-rendered HTML or canonical contract JSON.

    Accept: application/json → canonical contract
    Accept: text/html or default → safe HTML
    Never exposes local absolute paths.
    """
    try:
        report = _build_safe_report(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    except Exception as exc:
        return _json_error(f"report generation failed: {exc}", 500)

    return FlaskResponse(
        report["body"],
        status=report["status_code"],
        content_type=report["content_type"],
    )


# ── Dimension audit ───────────────────────────────────────────────────

@client_blueprint.post("/runs/<run_id>/dimension-audit")
def post_dimension_audit(run_id: str):
    data = _payload()
    try:
        audit = run_dimension_audit(
            run_id=run_id,
            task_type=str(data.get("task_type") or "general"),
            force=bool(data.get("force", False)),
            audit_mode=str(data.get("audit_mode") or "heuristic_only"),
        )
    except Exception as exc:
        return _json_error(str(exc), 500)
    return jsonify({"ok": True, "contract": build_fdjp_client_contract(audit)})


@client_blueprint.get("/runs/<run_id>/dimension-audit")
def get_dimension_audit(run_id: str):
    audit = load_dimension_audit(run_id=run_id)
    if not audit:
        return _json_error("FDJP_AUDIT_NOT_FOUND", 404)
    return jsonify({"ok": True, "contract": build_fdjp_client_contract(audit)})


@client_blueprint.get("/runs/<run_id>/report-blocks")
def get_dimension_report_blocks(run_id: str):
    return jsonify(load_dimension_report_blocks(run_id=run_id))


@client_blueprint.get("/runs/<run_id>/noise-audit")
def get_noise_audit(run_id: str):
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    candidates = []
    raw_path = str(summary.get("noise_audit_path") or "")
    if raw_path:
        candidates.append(Path(raw_path))
    candidates.append(default_reports_root() / "runs" / run_id / "noise_audit.json")
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"ok": True, "noise": payload})
        except Exception as exc:
            return _json_error(f"noise audit read failed: {exc}", 500, run_id=run_id)
    return _json_error("NOISE_AUDIT_NOT_FOUND", 404, run_id=run_id)


@client_blueprint.get("/runs/<run_id>/meta-judge")
def get_meta_judge(run_id: str):
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    candidates = []
    raw_path = str(summary.get("meta_judge_path") or "")
    if raw_path:
        candidates.append(Path(raw_path))
    candidates.append(default_reports_root() / "runs" / run_id / "meta_judge.json")
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"ok": True, "metaJudge": payload})
        except Exception as exc:
            return _json_error(f"meta judge read failed: {exc}", 500, run_id=run_id)
    return _json_error("META_JUDGE_NOT_FOUND", 404, run_id=run_id)


@client_blueprint.get("/runs/<run_id>/autonomous-strategy")
def get_autonomous_strategy(run_id: str):
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    candidates = []
    raw_path = str(summary.get("autonomous_strategy_path") or "")
    if raw_path:
        candidates.append(Path(raw_path))
    candidates.append(default_reports_root() / "runs" / run_id / "autonomous_strategy.json")
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"ok": True, "autonomousStrategy": payload})
        except Exception as exc:
            return _json_error(f"autonomous strategy read failed: {exc}", 500, run_id=run_id)
    return _json_error("AUTONOMOUS_STRATEGY_NOT_FOUND", 404, run_id=run_id)


@client_blueprint.get("/runs/<run_id>/market-simulation")
def get_market_simulation(run_id: str):
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    candidates = []
    raw_path = str(summary.get("market_simulation_path") or "")
    if raw_path:
        candidates.append(Path(raw_path))
    candidates.append(default_reports_root() / "runs" / run_id / "market_simulation.json")
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"ok": True, "marketSimulation": payload})
        except Exception as exc:
            return _json_error(f"market simulation read failed: {exc}", 500, run_id=run_id)
    return _json_error("MARKET_SIMULATION_NOT_FOUND", 404, run_id=run_id)


@client_blueprint.get("/runs/<run_id>/decision-os")
def get_decision_os(run_id: str):
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    candidates = []
    raw_path = str(summary.get("decision_os_path") or "")
    if raw_path:
        candidates.append(Path(raw_path))
    candidates.append(default_reports_root() / "runs" / run_id / "decision_os.json")
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"ok": True, "decisionOS": payload})
        except Exception as exc:
            return _json_error(f"decision OS read failed: {exc}", 500, run_id=run_id)
    return _json_error("DECISION_OS_NOT_FOUND", 404, run_id=run_id)


@client_blueprint.get("/runs/<run_id>/self-improving-loop")
def get_self_improving_loop(run_id: str):
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    candidates = []
    raw_path = str(summary.get("self_improving_loop_path") or "")
    if raw_path:
        candidates.append(Path(raw_path))
    candidates.append(default_reports_root() / "runs" / run_id / "self_improving_loop.json")
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"ok": True, "selfImprovingLoop": payload})
        except Exception as exc:
            return _json_error(f"self-improving loop read failed: {exc}", 500, run_id=run_id)
    return _json_error("SELF_IMPROVING_LOOP_NOT_FOUND", 404, run_id=run_id)


@client_blueprint.get("/runs/<run_id>/autonomous-economy")
def get_autonomous_economy(run_id: str):
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    candidates = []
    raw_path = str(summary.get("autonomous_economy_path") or "")
    if raw_path:
        candidates.append(Path(raw_path))
    candidates.append(default_reports_root() / "runs" / run_id / "autonomous_economy.json")
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"ok": True, "autonomousEconomy": payload})
        except Exception as exc:
            return _json_error(f"autonomous economy read failed: {exc}", 500, run_id=run_id)
    return _json_error("AUTONOMOUS_ECONOMY_NOT_FOUND", 404, run_id=run_id)


@client_blueprint.get("/runs/<run_id>/recursive-civilization")
def get_recursive_civilization(run_id: str):
    try:
        summary = load_summary(run_id)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    candidates = []
    raw_path = str(summary.get("recursive_civilization_path") or "")
    if raw_path:
        candidates.append(Path(raw_path))
    candidates.append(default_reports_root() / "runs" / run_id / "recursive_civilization.json")
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"ok": True, "recursiveCivilization": payload})
        except Exception as exc:
            return _json_error(f"recursive civilization read failed: {exc}", 500, run_id=run_id)
    return _json_error("RECURSIVE_CIVILIZATION_NOT_FOUND", 404, run_id=run_id)


# ── Followup / Archive ────────────────────────────────────────────────

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
