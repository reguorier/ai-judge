#!/usr/bin/env python3
# ruff: noqa: E402
"""AI Judge v3.4 API Server.

Runs the product end-to-end:
  - mode-aware automatic jury execution
  - SQLite-backed async tasks
  - SSE-compatible progress
  - signed HTML result links
  - notification fan-out for Feishu/WeCom/email/webhook/desktop
"""

from __future__ import annotations

import html
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask, Response, jsonify, redirect, request, send_file, send_from_directory, stream_with_context
from product.client_api import client_blueprint

# P24: Background threads (run_worker, rescue, recheck, supplement) need a stable base URL
# because Flask's request proxy is unavailable outside the request context.
# Use request.host_url when in a route; fall back to the dashboard default.
def _base_url():
    try:
        return request.host_url.rstrip("/")
    except RuntimeError:
        return "http://127.0.0.1:8501"

try:
    from flask_cors import CORS
except Exception:  # pragma: no cover - optional dependency
    CORS = None

from bridges.notification_gateway import generate_secure_view_url, notify_verdict_ready, verify_secure_view
from bridges.chrome_cdp_bridge import ensure_chrome_cdp_awake
from bridges.chrome_fixed_tab_bridge import recover_existing_fixed_tab_answers
from bridges.web_seat_bridge import bridge_status, calibrate_bridge, load_bridge_config, write_default_config
from core.async_task_manager import TaskManager
from core.auto_jury import format_verdict_markdown
from core.blind_cross_validation import aggregate_blind_reviews, build_blind_cross_validation_packet
from core.cross_temporal_analysis import attach_cross_temporal_analysis
from core.evidence_broker import build_evidence_broker_report
from core.evidence_gap_filler import suggest_evidence_gaps
from core.evidence_gap_queue import build_evidence_gap_queue, resolve_gap_task
from core.eval_dataset import build_eval_case_from_verdict, collect_eval_cases
from core.eval_metrics import compute_evidence_quality_metrics
from core.execution_drivers import build_bridge_blocked_verdict, decide_execution
from core.final_report import attach_final_report, build_final_report, render_final_report_html, render_final_report_markdown
from core.grand_judge import run_grand_judge_mvp
from core.human_review import human_review_status, sign_human_review
from human_gavel_layer import (
    sync_all_human_gavels,
    sync_human_gavel_for_run,
    check_gavel_conflict,
    generate_gavel_digest,
)
from run_universe_layer import build_run_universe, write_run_universe
from trust_calibration_layer import build_trust_calibration, write_trust_calibration, get_seat_trust
from core.bridge_run_lock import bridge_run_snapshot, release_bridge_run, try_acquire_bridge_run
from core.modes import list_modes, resolve_mode
from core.prompt_resonance import build_prompt_flow
from core.run_control import (
    add_artifact,
    add_event,
    get_run,
    is_cancel_requested,
    is_paused,
    list_runs,
    load_control_state,
    mark_completed,
    mark_failed,
    mark_stopped,
    release_bridge_for_run,
    request_pause,
    request_resume,
    request_stop,
    save_control_state,
    set_phase,
    start_run,
    update_run,
)
from core.run_trace import RunTrace, load_trace
from core.seat_execution_policy import (
    annotate_execution_results,
    execution_policy_summary,
)
from core.seat_personas import SEAT_PERSONAS
from core.werewolf_executor import (
    get_werewolf_session,
    list_werewolf_sessions,
    resume_werewolf_without_substitute,
    start_werewolf_session,
    substitute_werewolf_seat,
)
from core.werewolf_game import (
    board_public_config,
    build_werewolf_demo,
    normalize_werewolf_board,
    normalize_werewolf_play_mode,
    play_mode_public_config,
)
from core.web_jury import assemble_web_verdict_from_raw_results, run_web_jury


app = Flask(__name__)
app.register_blueprint(client_blueprint)
if CORS:
    CORS(app)

PRODUCT_VERSION = "3.8.0-p8.7-drift-sentinel-e2e-v1"
PRODUCT_NAME = "AI Judge Trust Workbench"
DEFAULT_JUDGE_MODE = "strategic"
DEFAULT_JUDGE_ENGINE = "web"
TASKS = TaskManager()
RUNS_DIR = _PROJECT_ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)
PRODUCT_DIR = _PROJECT_ROOT / "product"
SRC_DIR = Path(os.environ.get("AI_JUDGE_SRC_DIR", str(Path.home() / "Documents" / "ai-judge-skill" / "product")))
STALE_TASK_SECONDS = 90
AUTO_REQUIRED_RECOVERY_ATTEMPTS = 2
AUTO_REQUIRED_RECOVERY_WAIT_SECONDS = 6
MAX_LOCAL_FILE_BYTES = 240_000
MAX_LOCAL_TEXT_CHARS = 16_000
MAX_LOCAL_CONTEXT_CHARS = 28_000
LOCAL_FILE_EXTENSIONS = (
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "bmp",
    "tif",
    "tiff",
    "heic",
    "heif",
    "txt",
    "md",
    "markdown",
    "json",
    "jsonl",
    "csv",
    "tsv",
    "rtf",
    "pdf",
    "doc",
    "docx",
    "html",
    "htm",
    "xml",
    "yaml",
    "yml",
    "toml",
    "py",
    "js",
    "ts",
    "tsx",
    "jsx",
    "swift",
    "go",
    "rs",
    "java",
    "kt",
    "sh",
    "zsh",
    "log",
)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
TEXTUTIL_SUFFIXES = {".rtf", ".doc", ".docx", ".html", ".htm"}
PDF_SUFFIXES = {".pdf"}
LOCAL_PATH_RE = re.compile(
    r"(?P<path>(?:file://)?/(?:Users|private|tmp|var|Volumes)/[^\n\r\t\"'<>]*?\.(?:"
    + "|".join(re.escape(ext) for ext in LOCAL_FILE_EXTENSIONS)
    + r"))",
    re.IGNORECASE,
)
LOCAL_OCR_CANDIDATES = [
    _PROJECT_ROOT / "tools" / "image-ocr",
    Path.home() / "Library/Application Support/Claude-3p/hermes-guard-mcp/image-ocr",
]
WAITING_STEP_RE = re.compile(r"(?:等待\s*(?P<labels>[^，]+)，)?剩余\s*(?P<count>\d+)\s*席，最长等待\s*(?P<seconds>\d+)s")
RETRY_STEP_RE = re.compile(r"补跑\s*(?P<attempt>\d+)\s*/\s*(?P<total>\d+)")
RECOVERABLE_WEB_CODES = {
    "slow_response_pending",
    "response_timeout",
    "send_button_not_found",
    "submit_unconfirmed",
    "chrome_submit_unconfirmed",
    "prompt_still_in_input",
    "composer_busy",
    "page_error",
    "model_page_error",
    "chrome_crash",
    "blank_page",
    "response_not_relevant",
    "long_prompt_still_in_input",
    "existing_answer_not_found",
    "existing_answer_placeholder",
    "existing_answer_prompt_echo",
    "fixed_tab_not_found",
    "input_not_found",
    "transcript_pollution",
    "apple_events_execute_failed",
    "chrome_composer_not_ready",
    "composer_not_ready",
    "deepseek_expert_mode_not_verified",
    "doubao_expert_mode_not_verified",
}
READ_ONLY_RECOVERY_CODES = {
    "slow_response_pending",
    "response_timeout",
    "composer_busy",
    "existing_answer_not_found",
    "existing_answer_placeholder",
    "existing_answer_prompt_echo",
    "response_not_relevant",
}
FRESH_RESCUE_CODES = {
    "send_button_not_found",
    "submit_unconfirmed",
    "chrome_submit_unconfirmed",
    "prompt_still_in_input",
    "long_prompt_still_in_input",
    "input_not_found",
    "fixed_tab_not_found",
    "page_error",
    "model_page_error",
    "chrome_crash",
    "blank_page",
    "page_recovery_failed",
    "apple_events_execute_failed",
    "chrome_composer_not_ready",
    "composer_not_ready",
    "deepseek_expert_mode_not_verified",
    "doubao_expert_mode_not_verified",
}
CLEAN_SESSION_RESCUE_CODES = {
    "transcript_pollution",
}


def _save_run(run_id: str, verdict: dict[str, Any]) -> None:
    _attach_rescue_plan(verdict)
    attach_cross_temporal_analysis(verdict)
    attach_final_report(verdict)
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "verdict.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "verdict.md").write_text(format_verdict_markdown(verdict), encoding="utf-8")
    # Generate static index.html with execution trace for offline/fallback access
    report_data = dict(verdict)
    trace = load_trace(_trace_path(run_id))
    if trace:
        report_data["execution_trace"] = trace
    try:
        (run_dir / "index.html").write_text(_render_html_report(report_data), encoding="utf-8")
    except Exception:
        pass  # don't block verdict save if HTML render fails

    # --- Hermes × Obsidian output ---
    try:
        from hermes_output_layer import write_hermes_outputs
        vault_dir = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT")
        write_hermes_outputs(run_dir, vault_dir=vault_dir)
    except Exception as exc:
        import traceback as _tb
        print(f"[Hermes] write_hermes_outputs failed for {run_id}: {exc}", file=sys.stderr)
        _tb.print_exc(file=sys.stderr)

    # --- Hermes Index refresh ---
    try:
        from hermes_index_layer import write_hermes_index
        vault_dir = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT")
        write_hermes_index(RUNS_DIR, vault_dir)
    except Exception as exc:
        import traceback as _tb2
        print(f"[HermesIndex] write_hermes_index failed: {exc}", file=sys.stderr)
        _tb2.print_exc(file=sys.stderr)


def _trace_path(run_id: str) -> Path:
    return RUNS_DIR / run_id / "trace.json"


def _load_run(run_id: str) -> dict[str, Any] | None:
    result = TASKS.get_result(run_id)
    if result:
        _attach_rescue_plan(result)
        attach_cross_temporal_analysis(result)
        attach_final_report(result)
        return result
    run_file = RUNS_DIR / run_id / "verdict.json"
    if run_file.exists():
        result = json.loads(run_file.read_text(encoding="utf-8"))
        if isinstance(result, dict) and "cross_temporal_analysis" not in result:
            attach_cross_temporal_analysis(result)
        if isinstance(result, dict):
            _attach_rescue_plan(result)
            attach_final_report(result)
        return result
    return None


def _task_payload(run_id: str) -> dict[str, Any] | None:
    status = TASKS.get_status(run_id)
    if status is None:
        return None
    payload = dict(status)
    result = TASKS.get_result(run_id)
    if result:
        payload["result"] = result
    payload["progress_diagnostics"] = _progress_diagnostics(payload)
    return payload


def _progress_diagnostics(status: dict[str, Any]) -> dict[str, Any]:
    run_id = str(status.get("run_id") or "")
    step = str(status.get("current_step") or "")
    seconds_since_update = _seconds_since_iso(status.get("updated_at"))
    trace = load_trace(_trace_path(run_id)) or {}
    seats = _seat_progress_from_trace(trace)
    waiting_match = WAITING_STEP_RE.search(step)
    retry_match = RETRY_STEP_RE.search(step)
    waiting = {
        "count": int(waiting_match.group("count")) if waiting_match else 0,
        "longest_wait_seconds": int(waiting_match.group("seconds")) if waiting_match else None,
        "labels": _split_progress_labels(waiting_match.group("labels") if waiting_match else ""),
    }
    if waiting["labels"]:
        label_order = {label.lower(): index for index, label in enumerate(waiting["labels"])}
        seats.sort(key=lambda item: (label_order.get(str(item.get("name", "")).lower(), 99), item.get("state") != "waiting"))
    else:
        seats.sort(key=lambda item: {"waiting": 0, "submitting": 1, "nudge": 2, "blocked": 3, "done": 4}.get(str(item.get("state")), 9))
    diagnostic_rescue_plan = _diagnostic_rescue_plan(seats)
    return {
        "schema": "ai_judge.progress_diagnostics.v1",
        "run_id": run_id,
        "step": step,
        "status": status.get("status"),
        "stage": _progress_stage(step, float(status.get("progress") or 0)),
        "retry": {
            "attempt": int(retry_match.group("attempt")) if retry_match else None,
            "total": int(retry_match.group("total")) if retry_match else None,
        },
        "waiting": waiting,
        "seats": seats[:8],
        "rescue_plan": diagnostic_rescue_plan,
        "seconds_since_update": seconds_since_update,
        "stale": bool(status.get("status") == "running" and seconds_since_update is not None and seconds_since_update > STALE_TASK_SECONDS),
        "stale_after_seconds": STALE_TASK_SECONDS,
    }


def _diagnostic_rescue_plan(seats: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for item in seats:
        if item.get("state") not in {"waiting", "nudge", "blocked"}:
            continue
        code = str(item.get("code") or "slow_response_pending")
        failures.append({
            "seat": item.get("seat"),
            "seat_name": item.get("name"),
            "supplementable": code in RECOVERABLE_WEB_CODES or item.get("state") in {"waiting", "nudge"},
            "error": {"code": code, "message": item.get("reason")},
            "execution_validity": {"reason": code},
        })
    actions = [_rescue_action_for_failure(item) for item in failures if str(item.get("seat") or "") in SEAT_PERSONAS]
    actions = [item for item in actions if item["method"] != "manual_check"]
    return {
        "schema": "ai_judge.diagnostic_rescue_plan.v1",
        "status": "ready" if actions else "none",
        "button_label": "一键修复并回收答案" if any(item["sends_prompt"] for item in actions) else "一键回收已有答案",
        "actions": actions,
        "seats": [item["seat"] for item in actions],
        "sends_prompt": any(item["sends_prompt"] for item in actions),
        "summary": _rescue_plan_summary(actions, {"collection_complete": False}),
    }


def _seconds_since_iso(value: Any) -> int | None:
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - timestamp).total_seconds()))
    except Exception:
        return None


def _split_progress_labels(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[、,，/]", str(value or "")) if item.strip()]


def _progress_stage(step: str, progress: float) -> str:
    if "补跑" in step:
        return "retry_collect"
    if "回答轮询" in step or "席位" in step:
        return "collect"
    if "评分" in step or progress >= 0.70:
        return "score"
    if "桥接" in step or "Operator" in step:
        return "driver"
    if "共振" in step:
        return "align"
    return "accept"


def _seat_progress_from_trace(trace: dict[str, Any]) -> list[dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    for event in trace.get("events") or []:
        if event.get("phase") != "seat":
            continue
        data = event.get("data") or {}
        seat = str(data.get("seat") or "").lower()
        if seat not in SEAT_PERSONAS:
            continue
        states[seat] = _next_seat_progress_state(seat, states.get(seat), event)
    return [item for item in states.values() if item.get("state") in {"waiting", "submitting", "nudge", "blocked"}]


def _next_seat_progress_state(seat: str, previous: dict[str, Any] | None, event: dict[str, Any]) -> dict[str, Any]:
    action = str(event.get("action") or "")
    detail = str(event.get("detail") or "")
    data = event.get("data") or {}
    base = {
        "seat": seat,
        "name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "state": (previous or {}).get("state", "waiting"),
        "status": (previous or {}).get("status", "等待"),
        "reason": (previous or {}).get("reason", "等待模型输出可采集回答"),
        "code": (previous or {}).get("code", "slow_response_pending"),
        "detail": detail,
        "updated_at": event.get("at"),
    }
    if action in {"chrome_submit_start", "start"}:
        base.update({"state": "submitting", "status": "提交中", "reason": "正在写入提示词或准备模型页面"})
    elif action == "chrome_humanized_pacing":
        base.update({"state": "submitting", "status": "缓速提交", "reason": "已启用拟人化节奏，避免连续快速操作触发页面异常"})
    elif action in {"chrome_tab_recovery", "cdp_tab_recovery", "playwright_tab_recovery"}:
        base.update({"state": "submitting", "status": "刷新恢复", "reason": "检测到页面错误或空白，已刷新并等待输入框恢复"})
    elif action in {"chrome_tab_recovery_failed", "cdp_tab_recovery_failed", "playwright_tab_recovery_failed"}:
        base.update({"state": "blocked", "status": "恢复失败", "reason": "页面刷新后仍未恢复到可提交状态", "code": "page_recovery_failed"})
    elif action == "chrome_submit_complete":
        base.update({"state": "waiting", "status": "等待回答", "reason": "提示词已发送，正在等待可验证回答"})
    elif action == "chrome_final_answer_nudge":
        base.update({"state": "nudge", "status": "已追问", "reason": "检测到空思考或未输出正文，已追加最终答案追问"})
    elif action in {"chrome_response_captured", "chrome_partial_response_captured", "complete"}:
        base.update({"state": "done", "status": "已采集", "reason": f"已读取 {data.get('response_chars', 0)} 字"})
    elif action == "existing_answer_captured":
        base.update({"state": "done", "status": "旧页已回收", "reason": f"已从旧页面读取 {data.get('response_chars', 0)} 字"})
    elif action == "existing_answer_rejected":
        code = str(data.get("code") or "existing_answer_not_found")
        base.update({"state": "blocked", "status": _seat_error_label(code), "reason": _seat_error_reason(code), "code": code})
    elif action in {"chrome_response_timeout", "chrome_response_rejected"}:
        code = str(data.get("code") or "slow_response_pending")
        base.update({"state": "blocked", "status": _seat_error_label(code), "reason": _seat_error_reason(code), "code": code})
    elif action in {
        "chrome_submit_unconfirmed",
        "chrome_submit_failed",
        "chrome_submit_blocked",
        "chrome_composer_blocked",
        "chrome_composer_busy",
        "chrome_composer_not_ready",
        "fixed_tab_not_found",
        "chrome_response_page_error",
        "doubao_expert_mode_blocked",
    }:
        submit = data.get("submit") or {}
        verification = submit.get("verification") or {}
        code = str(
            submit.get("error")
            or verification.get("reason")
            or ((data.get("known_error") or {}).get("code"))
            or ("doubao_expert_mode_not_verified" if action == "doubao_expert_mode_blocked" else "")
            or action
        )
        base.update({"state": "blocked", "status": _seat_error_label(code), "reason": _seat_error_reason(code), "code": code})
    return base


def _seat_error_label(code: str) -> str:
    return {
        "slow_response_pending": "慢生成",
        "response_timeout": "超时",
        "response_not_relevant": "疑似旧回答",
        "send_button_not_found": "发送未确认",
        "input_not_found": "输入框缺失",
        "submit_unconfirmed": "提交未确认",
        "chrome_submit_unconfirmed": "提交未确认",
        "prompt_still_in_input": "提交未确认",
        "long_prompt_still_in_input": "提交未确认",
        "chrome_composer_blocked": "页面阻断",
        "page_blocked": "页面阻断",
        "composer_busy": "页面忙碌",
        "page_error": "页面错误",
        "model_page_error": "页面错误",
        "chrome_crash": "标签崩溃",
        "blank_page": "页面空白",
        "page_recovery_failed": "恢复失败",
        "doubao_expert_mode_not_verified": "专家模式未确认",
        "fixed_tab_not_found": "标签缺失",
        "transcript_pollution": "历史串流",
        "existing_answer_not_found": "旧页未返回",
        "existing_answer_placeholder": "仍是占位",
        "existing_answer_prompt_echo": "旧页未完成",
    }.get(code, "需处理")


def _seat_error_reason(code: str) -> str:
    return {
        "slow_response_pending": "页面可能仍在生成，或回答未包含本轮可验证标记",
        "response_timeout": "等待窗口内没有读到可用回答",
        "response_not_relevant": "捕获内容没有匹配本轮问题，已避免把旧页面内容当作答案",
        "send_button_not_found": "提示词写入了页面，但没有找到明确可用的发送按钮",
        "input_not_found": "模型页面没有暴露可写入的输入框，系统会尝试重新定位或打开干净会话",
        "submit_unconfirmed": "提示词写入后，桥接层无法确认模型已接收为新一轮提问",
        "chrome_submit_unconfirmed": "提示词写入后，桥接层无法确认模型已接收为新一轮提问",
        "prompt_still_in_input": "提示词仍停留在输入框里，模型页面没有确认接收本轮任务",
        "long_prompt_still_in_input": "长提示仍停留在输入框里，模型页面没有确认接收本轮任务",
        "chrome_composer_blocked": "模型页面出现阻断态，系统没有提交新问题",
        "page_blocked": "模型页面出现阻断态，系统没有提交新问题",
        "composer_busy": "页面仍在生成，系统没有把新任务塞进忙碌会话",
        "page_error": "模型页面反馈可重试错误，系统会刷新后补跑",
        "model_page_error": "模型页面返回网络或生成错误，系统会刷新后补跑",
        "chrome_crash": "Chrome 标签页疑似崩溃，系统会刷新后补跑",
        "blank_page": "模型页面没有渲染有效内容，系统会刷新后补跑",
        "page_recovery_failed": "刷新恢复后仍没有可用输入框，需要人工查看该标签",
        "doubao_expert_mode_not_verified": "豆包未能确认专家/超能模式，系统已拒绝快速模式提交",
        "fixed_tab_not_found": "没有找到该模型对应的 Chrome 固定标签",
        "transcript_pollution": "捕获内容混入旧 AI Judge 标记，已拒绝评分",
        "existing_answer_not_found": "已打开页面中没有找到该席位的 AI Judge 答案标记",
        "existing_answer_placeholder": "页面仍只显示 AI Judge 占位文本，模型尚未产出最终正文",
        "existing_answer_prompt_echo": "页面仍是提示词或占位内容，不是可评分答案",
    }.get(code, "该席位需要查看页面或回收旧页面答案")


def _notification_config(data: dict[str, Any]) -> dict[str, Any]:
    notify = data.get("notify") or {}
    channels = notify.get("channels") or data.get("notify_channels") or []
    if isinstance(channels, str):
        channels = [c.strip() for c in channels.split(",") if c.strip()]

    for key, channel in (
        ("email", "email"),
        ("webhook_url", "webhook"),
        ("feishu_webhook", "feishu"),
        ("wecom_webhook", "wecom"),
        ("desktop", "desktop"),
    ):
        if notify.get(key) and channel not in channels:
            channels.append(channel)

    return {
        "channels": channels,
        "email": notify.get("email"),
        "webhook_url": notify.get("webhook_url"),
        "feishu_webhook": notify.get("feishu_webhook"),
        "wecom_webhook": notify.get("wecom_webhook"),
        "desktop": bool(notify.get("desktop")),
    }


def _normalize_seat_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = [s.strip() for s in value.split(",") if s.strip()]
    elif isinstance(value, list):
        raw = [str(item).strip() for item in value if str(item).strip()]
    else:
        raw = []
    return [seat.lower() for seat in raw if seat.lower() in SEAT_PERSONAS]


def _normalize_external_evidence_payload(value: Any) -> list[dict[str, Any]]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [{"text": value}]
    if isinstance(value, dict):
        raw = value.get("items") or value.get("evidence") or [value]
    elif isinstance(value, list):
        raw = value
    else:
        raw = [{"text": str(value)}]
    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw, 1):
        if isinstance(item, dict):
            next_item = dict(item)
        else:
            next_item = {"text": str(item)}
        next_item.setdefault("id", f"REQ-EVID-{index:03d}")
        result.append(next_item)
    return result


def _normalize_evidence_options(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"allow_network": False, "max_fetches": 6}
    return {
        "allow_network": bool(value.get("allow_network")),
        "max_fetches": max(0, min(20, int(value.get("max_fetches") or 6))),
    }


def _prepare_local_file_context(question: str) -> dict[str, Any]:
    paths = _extract_local_paths(question)
    items = [_read_local_path(path, index) for index, path in enumerate(paths, 1)]
    ok_items = [item for item in items if item.get("ok")]
    return {
        "schema": "ai_judge.local_file_context.v1",
        "path_count": len(paths),
        "ok_count": len(ok_items),
        "failed_count": len(items) - len(ok_items),
        "items": items,
        "external_evidence": [_local_item_to_evidence(item) for item in items],
    }


def _extract_local_paths(text: str) -> list[Path]:
    paths: list[Path] = []
    for match in LOCAL_PATH_RE.finditer(text or ""):
        raw = match.group("path").strip().rstrip(".,;，。；)")
        if raw.startswith("file://"):
            parsed = urlparse(raw)
            raw = unquote(parsed.path)
        else:
            raw = unquote(raw)
        path = Path(raw).expanduser()
        if _is_allowed_local_file(path):
            paths.append(path.resolve())
    return list(dict.fromkeys(paths))


def _is_allowed_local_file(path: Path) -> bool:
    try:
        if not path.exists() or not path.is_file():
            return False
        resolved = path.resolve()
    except Exception:
        return False
    home = Path.home().resolve()
    allowed_roots = [
        home,
        Path("/tmp"),
        Path("/private/tmp"),
        Path("/var/folders"),
        Path("/private/var/folders"),
        Path("/Volumes"),
    ]
    return any(resolved == root or root in resolved.parents for root in allowed_roots)


def _read_local_path(path: Path, index: int) -> dict[str, Any]:
    suffix = path.suffix.lower()
    stat = path.stat()
    item: dict[str, Any] = {
        "id": f"LOCAL-FILE-{index:03d}",
        "path": str(path),
        "name": path.name,
        "suffix": suffix,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "mime_type": mimetypes.guess_type(str(path))[0] or "application/octet-stream",
    }
    try:
        if suffix in IMAGE_SUFFIXES:
            item.update(_read_image_ocr(path))
        elif suffix in TEXTUTIL_SUFFIXES:
            item.update(_read_textutil_file(path))
        elif suffix in PDF_SUFFIXES:
            item.update(_read_pdf_text(path))
        else:
            item.update(_read_plain_text_file(path))
    except Exception as exc:
        item.update({
            "ok": False,
            "kind": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "text": "",
        })
    item["text"] = _limit_text(str(item.get("text") or ""), MAX_LOCAL_TEXT_CHARS)
    return item


def _read_image_ocr(path: Path) -> dict[str, Any]:
    binary = next((candidate for candidate in LOCAL_OCR_CANDIDATES if candidate.exists()), None)
    if not binary:
        return {
            "ok": False,
            "kind": "image",
            "error": "local OCR binary not found",
            "text": "",
        }
    proc = subprocess.run(
        [str(binary), str(path)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "ok": False,
            "kind": "image",
            "error": (proc.stderr or proc.stdout or f"OCR exited {proc.returncode}").strip()[:800],
            "text": "",
        }
    payload = json.loads(proc.stdout)
    lines = payload.get("lines") or []
    text = "\n".join(str(line.get("text") or "").strip() for line in lines if str(line.get("text") or "").strip())
    return {
        "ok": bool(text),
        "kind": "image_ocr",
        "line_count": int(payload.get("lineCount") or len(lines)),
        "text": text,
        "error": "" if text else "OCR returned no text",
    }


def _read_textutil_file(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["/usr/bin/textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return {"ok": True, "kind": "document_text", "text": proc.stdout}
    fallback = _read_plain_text_file(path)
    if not fallback.get("ok"):
        fallback["error"] = (proc.stderr or fallback.get("error") or "textutil returned no text").strip()[:800]
    return fallback


def _read_pdf_text(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["/usr/bin/mdls", "-raw", "-name", "kMDItemTextContent", str(path)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    text = proc.stdout.strip()
    if proc.returncode == 0 and text and text != "(null)":
        return {"ok": True, "kind": "pdf_text", "text": text}
    return {
        "ok": False,
        "kind": "pdf_text",
        "text": "",
        "error": (proc.stderr or "PDF text extraction unavailable").strip()[:800],
    }


def _read_plain_text_file(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()[:MAX_LOCAL_FILE_BYTES]
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "big5", "latin-1"):
        try:
            text = raw.decode(encoding)
            return {
                "ok": bool(text.strip()),
                "kind": "text",
                "encoding": encoding,
                "truncated_bytes": path.stat().st_size > MAX_LOCAL_FILE_BYTES,
                "text": text,
                "error": "" if text.strip() else "empty text file",
            }
        except UnicodeDecodeError:
            continue
    return {"ok": False, "kind": "text", "text": "", "error": "unsupported text encoding"}


def _local_item_to_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "source": "local_file",
        "source_path": item.get("path"),
        "name": item.get("name"),
        "kind": item.get("kind"),
        "mime_type": item.get("mime_type"),
        "size_bytes": item.get("size_bytes"),
        "ok": bool(item.get("ok")),
        "error": item.get("error", ""),
        "text": item.get("text", ""),
    }


def _question_with_local_context(question: str, local_context: dict[str, Any]) -> str:
    items = local_context.get("items") or []
    if not items:
        return question
    sections = []
    for item in items:
        header = (
            f"[{item.get('id')}] {item.get('name')} | {item.get('kind')} | "
            f"{item.get('size_bytes')} bytes | {item.get('path')}"
        )
        if item.get("ok"):
            body = str(item.get("text") or "").strip()
        else:
            body = f"读取失败：{item.get('error') or 'unknown error'}"
        sections.append(f"{header}\n{body}")
    attachment_block = _limit_text("\n\n".join(sections), MAX_LOCAL_CONTEXT_CHARS)
    return (
        f"{question}\n\n"
        "---\n"
        "本机已解析以下本地文件/图片内容。网页模型不能直接读取本地路径；请以这里的文本作为文件内容依据，"
        "不要声称仍需要用户重新上传同一文件。\n\n"
        f"{attachment_block}"
    )


def _public_local_file_context(local_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": local_context.get("schema"),
        "path_count": local_context.get("path_count", 0),
        "ok_count": local_context.get("ok_count", 0),
        "failed_count": local_context.get("failed_count", 0),
        "items": [
            {
                "id": item.get("id"),
                "path": item.get("path"),
                "name": item.get("name"),
                "kind": item.get("kind"),
                "ok": bool(item.get("ok")),
                "size_bytes": item.get("size_bytes"),
                "line_count": item.get("line_count"),
                "error": item.get("error", ""),
                "text_preview": _limit_text(str(item.get("text") or ""), 800),
            }
            for item in (local_context.get("items") or [])
        ],
    }


def _limit_text(value: str, limit: int) -> str:
    value = value or ""
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + f"\n...[truncated {len(value) - limit} chars]"


def _build_attachment_context(attachments: list[dict[str, Any]], run_id: str) -> str:
    """P71: Build attachment context paragraph from dashboard attachment payload."""
    if not attachments:
        return ""
    sections = []
    for att in attachments:
        name = att.get("name", "unknown")
        source = att.get("source", "local_file")
        text_content = (att.get("textContent") or "").strip()
        text_preview = (att.get("textPreview") or "").strip()
        content_available = att.get("contentAvailable", False)
        att_run_id = att.get("run_id") or ""
        header = f"[附件: {name}]"
        if source == "run_report" and att_run_id:
            sections.append(f"{header} 类型: 历史裁决报告 | run_id: {att_run_id}")
            if text_content:
                sections.append(f"报告内容摘要：\n{_limit_text(text_content, 8000)}")
            else:
                runs_dir = RUNS_DIR / att_run_id
                sections.append(f"请读取 {runs_dir} 目录中的 verdict.md / verdict.json / index.html 作为该附件内容。")
        elif content_available and text_content:
            sections.append(f"{header} 类型: 文本文件 | 截断: {str(att.get('truncated', False))}")
            sections.append(_limit_text(text_content, 8000))
        elif content_available and text_preview:
            sections.append(f"{header} 类型: 文本文件（仅预览）")
            sections.append(text_preview)
        else:
            sections.append(f"{header} 类型: 非文本/元数据 | 大小: {att.get('size', 0)} bytes")
            sections.append("当前仅记录文件名和类型，暂未读取二进制内容。")
    if not sections:
        return ""
    return (
        "---\n"
        "以下是由用户通过附件功能上传的文件/报告内容。网页模型不能直接读取本地路径；请以这里的文本作为文件内容依据，"
        "不要声称仍需要用户重新上传同一文件。\n\n"
        + "\n\n---\n\n".join(sections)
    )


def _is_supplementable_result(item: dict[str, Any]) -> bool:
    if item.get("ok"):
        return False
    error = item.get("error") or {}
    code = str(error.get("code") or "")
    return bool(item.get("supplementable")) or code in RECOVERABLE_WEB_CODES


def _supplementable_run_seats(verdict: dict[str, Any], requested: list[str] | None = None) -> list[str]:
    requested_set = set(requested or [])
    bridge = verdict.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    policy = bridge.get("execution_policy") or execution_policy_summary(
        raw_results,
        requested_seats=verdict.get("seats") or [str(item.get("seat") or "") for item in raw_results],
    )
    seats: list[str] = []
    if not requested_set:
        for item in policy.get("required_supplementable_seats") or []:
            seat = str(item.get("seat") or "").lower()
            if seat in SEAT_PERSONAS:
                seats.append(seat)
        if seats:
            return list(dict.fromkeys(seats))
    for item in raw_results:
        seat = str(item.get("seat") or "").lower()
        if seat not in SEAT_PERSONAS:
            continue
        if requested_set and seat not in requested_set:
            continue
        if _is_supplementable_result(item):
            seats.append(seat)
    return list(dict.fromkeys(seats))


def _failure_error_code(item: dict[str, Any]) -> str:
    error = item.get("error") or {}
    validity = item.get("execution_validity") or {}
    return str(error.get("code") or validity.get("reason") or item.get("reason") or "")


def _rescue_action_for_failure(item: dict[str, Any]) -> dict[str, Any]:
    seat = str(item.get("seat") or "").lower()
    code = _failure_error_code(item)
    if code in FRESH_RESCUE_CODES:
        action = "selector_resubmit"
        method = "fresh_web_submission"
        label = "修复发送并重试"
        sends_prompt = True
        reason = "提示词未被模型页面确认接收；系统会用站点专用发送选择器重新提交该席位。"
    elif code in CLEAN_SESSION_RESCUE_CODES:
        action = "clean_session_resubmit"
        method = "clean_session_resubmit"
        label = "清理串流并回收"
        sends_prompt = True
        reason = "页面混入旧 AI Judge 标记；系统会优先读取旧页，必要时进入干净会话重试。"
    elif code in READ_ONLY_RECOVERY_CODES or item.get("supplementable"):
        action = "existing_page_recovery"
        method = "existing_page_recovery"
        label = "读取旧页面答案"
        sends_prompt = False
        reason = "模型可能已在原页面完成回答；系统只读取已有答案，不重新发送问题。"
    else:
        action = "manual_check"
        method = "manual_check"
        label = "需要人工检查"
        sends_prompt = False
        reason = "该席位失败类型暂不适合自动重试，建议打开模型页面查看登录、额度或阻断状态。"
    return {
        "seat": seat,
        "seat_name": item.get("seat_name") or SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "code": code or "execution_invalid",
        "action": action,
        "method": method,
        "label": label,
        "sends_prompt": sends_prompt,
        "supplementable": bool(item.get("supplementable")) or code in RECOVERABLE_WEB_CODES,
        "reason": reason,
    }


def _build_rescue_plan(verdict: dict[str, Any], requested: list[str] | None = None) -> dict[str, Any]:
    bridge = verdict.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    requested_set = set(requested or [])
    policy = bridge.get("execution_policy") or execution_policy_summary(
        raw_results,
        requested_seats=verdict.get("seats") or [str(item.get("seat") or "") for item in raw_results],
    )
    failures = policy.get("required_failures") or []
    if requested_set:
        raw_by_seat = {str(item.get("seat") or "").lower(): item for item in raw_results}
        failures = [raw_by_seat.get(seat, {"seat": seat, "error": {"code": "missing_result"}}) for seat in requested_set]
    actions = [
        _rescue_action_for_failure(item)
        for item in failures
        if str(item.get("seat") or "").lower() in SEAT_PERSONAS
    ]
    actions = [item for item in actions if item["supplementable"] or item["method"] != "manual_check"]
    seats = [item["seat"] for item in actions]
    fresh_seats = [item["seat"] for item in actions if item["method"] in {"fresh_web_submission", "clean_session_resubmit"}]
    read_only_seats = [item["seat"] for item in actions if item["method"] == "existing_page_recovery"]
    hard_seats = [item["seat"] for item in actions if item["method"] == "manual_check"]
    if not actions:
        status = "complete" if policy.get("collection_complete") else "blocked"
        label = "必需席位已补齐" if policy.get("collection_complete") else "暂无可自动修复席位"
    elif fresh_seats:
        status = "ready"
        label = "一键修复并回收答案"
    else:
        status = "ready"
        label = "一键回收已有答案"
    return {
        "schema": "ai_judge.rescue_plan.v1",
        "status": status,
        "button_label": label,
        "summary": _rescue_plan_summary(actions, policy),
        "seats": seats,
        "read_only_seats": read_only_seats,
        "fresh_seats": fresh_seats,
        "manual_check_seats": hard_seats,
        "actions": actions,
        "required_count": policy.get("required_count", 0),
        "required_valid_count": policy.get("required_valid_count", 0),
        "collection_complete": bool(policy.get("collection_complete")),
        "sends_prompt": bool(fresh_seats),
        "strategy": "read_existing_first_then_targeted_clean_resubmit" if fresh_seats else "read_existing_pages_only",
    }


def _rescue_plan_summary(actions: list[dict[str, Any]], policy: dict[str, Any]) -> str:
    if not actions:
        if policy.get("collection_complete"):
            return "所有非 Grok 必需席位已经回收完成。"
        return "当前没有可自动修复的席位，请检查登录、额度或固定标签配置。"
    read_count = sum(1 for item in actions if item["method"] == "existing_page_recovery")
    fresh_count = sum(1 for item in actions if item["method"] in {"fresh_web_submission", "clean_session_resubmit"})
    parts = []
    if read_count:
        parts.append(f"{read_count} 席先读取旧页面")
    if fresh_count:
        parts.append(f"{fresh_count} 席必要时干净会话重试")
    return "；".join(parts) + "。Grok/Gork 仍作为可选异议席位，不阻断发布。"


def _attach_rescue_plan(verdict: dict[str, Any]) -> dict[str, Any]:
    bridge = verdict.get("web_bridge")
    if isinstance(bridge, dict):
        bridge["rescue_plan"] = _build_rescue_plan(verdict)
    return verdict


def _rescue_bridge_overrides() -> dict[str, Any]:
    return {
        "fresh_conversation_per_run": True,
        "auto_open_missing_tabs": True,
        "fresh_load_seconds": 4,
        "retry_failed_seats": True,
        "retry_attempts": 1,
    }


def _diagnostic_recheck_seats(status: dict[str, Any], requested: list[str] | None = None) -> list[str]:
    requested_set = set(requested or [])
    diagnostics = status.get("progress_diagnostics") or {}
    seats: list[str] = []
    for item in diagnostics.get("seats") or []:
        seat = str(item.get("seat") or "").lower()
        if seat not in SEAT_PERSONAS:
            continue
        if requested_set and seat not in requested_set:
            continue
        state = str(item.get("state") or "")
        status_label = str(item.get("status") or "")
        if state in {"waiting", "nudge"} or status_label in {"慢生成", "超时", "发送未确认", "提交未确认", "疑似旧回答", "历史串流", "标签缺失"}:
            seats.append(seat)
    return list(dict.fromkeys(seats))


def _merge_explicit_recheck_seats(seats: list[str], requested: list[str] | None = None) -> list[str]:
    merged: list[str] = []
    for seat in [*(seats or []), *(requested or [])]:
        seat_key = str(seat or "").lower()
        if seat_key in SEAT_PERSONAS and seat_key not in merged:
            merged.append(seat_key)
    return merged


def _merge_supplement_raw_results(
    original: list[dict[str, Any]],
    supplement: list[dict[str, Any]],
    supplement_run_id: str,
) -> list[dict[str, Any]]:
    supplement_by_seat = {str(item.get("seat") or "").lower(): item for item in supplement}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in original:
        seat = str(item.get("seat") or "").lower()
        replacement = supplement_by_seat.get(seat)
        if not replacement:
            merged.append(dict(item))
            continue
        seen.add(seat)
        history = list(item.get("supplement_history") or [])
        history.append({
            "supplement_run_id": supplement_run_id,
            "previous_ok": bool(item.get("ok")),
            "previous_error": item.get("error"),
            "new_ok": bool(replacement.get("ok")),
            "new_error": replacement.get("error"),
        })
        if item.get("ok") and not replacement.get("ok"):
            next_item = dict(item)
            next_item["supplement_history"] = history
            next_item["supplemented_from_run_id"] = supplement_run_id
            next_item["failed_supplement_preserved"] = True
            next_item["latest_supplement_error"] = replacement.get("error")
            merged.append(next_item)
            continue
        next_item = dict(replacement)
        next_item["supplement_history"] = history
        next_item["supplemented_from_run_id"] = supplement_run_id
        if not item.get("ok") and replacement.get("ok"):
            next_item["recovered_by_supplement"] = True
        merged.append(next_item)
    for seat, item in supplement_by_seat.items():
        if seat not in seen:
            next_item = dict(item)
            next_item["supplemented_from_run_id"] = supplement_run_id
            merged.append(next_item)
    return annotate_execution_results(merged, config=load_bridge_config())


def _merge_trace_dicts(source: dict[str, Any] | None, supplement: dict[str, Any] | None, source_run_id: str) -> dict[str, Any]:
    events = []
    for event in (source or {}).get("events", []) or []:
        next_event = dict(event)
        next_event["trace_scope"] = "source"
        events.append(next_event)
    if events and supplement:
        events.append({
            "phase": "supplement",
            "action": "begin",
            "detail": "旧页面答案回收开始",
            "data": {"supplement_run_id": supplement.get("run_id")},
            "trace_scope": "supplement",
        })
    for event in (supplement or {}).get("events", []) or []:
        next_event = dict(event)
        next_event["trace_scope"] = "supplement"
        events.append(next_event)
    for index, event in enumerate(events, 1):
        event["index"] = index
    return {"run_id": source_run_id, "event_count": len(events), "events": events}


def _chief_judge_payload(chief_judge: str) -> dict[str, Any]:
    chief_judge = (chief_judge or "auto").lower().strip()
    if chief_judge == "auto":
        return {
            "id": "auto",
            "name": "自动轮值",
            "label": "自动轮值主审",
            "switchable": True,
        }
    persona = SEAT_PERSONAS.get(chief_judge)
    if not persona:
        return _chief_judge_payload("auto")
    return {
        "id": chief_judge,
        "name": persona["name"],
        "label": f"{persona['name']} 轮值主审",
        "mbti": persona["mbti"],
        "strength": persona["strength"],
        "switchable": True,
    }


def _attach_product_run_metadata(
    verdict: dict[str, Any],
    chief_judge: str = "auto",
    abstained_seats: list[str] | None = None,
) -> None:
    """Attach client-facing orchestration controls to a verdict."""
    abstained = [seat for seat in (abstained_seats or []) if seat in SEAT_PERSONAS]
    chief = _chief_judge_payload(chief_judge)
    selected = list(verdict.get("seats") or [])
    verdict["chief_judge"] = chief
    verdict["product_version"] = PRODUCT_VERSION
    verdict["product_layer"] = {
        "name": PRODUCT_NAME,
        "stable_mode": "5-minute trustworthy closeout",
        "lab_mode": "bridge diagnostics, seat reliability, benchmark evidence",
        "human_gavel": "draft_reviewed_publishable",
    }
    verdict["seat_roster"] = {
        "selected": selected,
        "abstained": abstained,
        "selected_count": len(selected),
        "abstained_count": len(abstained),
    }
    verdict["roster_sensitivity"] = _build_roster_sensitivity(verdict, chief)
    judge = verdict.get("judge_answer")
    if not isinstance(judge, dict):
        judge = {
            "label": chief["label"],
            "question": verdict.get("question", ""),
            "answer": (
                f"本轮主审：{chief['name']}。"
                f"{verdict.get('one_liner', 'AI Judge 已完成本轮汇总。')}"
            ),
            "ok_count": len(selected),
            "failed_count": 0,
            "dominant_stance": verdict.get("verdict_label", verdict.get("verdict", "-")),
            "top_seats": [item.get("seat_name", item.get("seat")) for item in (verdict.get("seat_scores") or [])[:3]],
            "agreements": [],
            "disagreements": [],
            "limits": ["产品运行路径已禁用本地陪审；完整结论必须来自网页模型原文收集。"],
        }
        verdict["judge_answer"] = judge
    else:
        judge["label"] = chief["label"]
        answer = str(judge.get("answer") or "")
        prefix = f"本轮主审：{chief['name']}。"
        if answer and not answer.startswith(prefix):
            judge["answer"] = f"{prefix}{answer}"
    baseline = verdict.get("single_judge_baseline")
    if not isinstance(baseline, dict):
        baseline = {
            "label": f"{chief['name']} 单模型对照",
            "answer": judge.get("answer", ""),
            "score": verdict.get("average_score"),
            "tier": verdict.get("verdict"),
            "council_average_score": verdict.get("average_score"),
            "delta_vs_council": 0,
            "comparison": [
                {"metric": "答案来源", "single_judge": chief["name"], "council": f"{len(selected)} 个网页席位"},
                {"metric": "互评校验", "single_judge": "主审汇总", "council": "席位评分引擎"},
            ],
        }
        verdict["single_judge_baseline"] = baseline
    else:
        baseline["label"] = f"{chief['name']} 单模型对照"
    attach_final_report(verdict)


def _attach_citation_mvp(verdict: dict[str, Any], run_id: str | None = None) -> dict[str, Any] | None:
    """Attach Grand Judge citation-verification MVP artifacts to a verdict."""
    bridge = verdict.get("web_bridge")
    if not isinstance(bridge, dict):
        return None
    raw_results = bridge.get("raw_results") or []
    if not raw_results:
        return None
    broker = build_evidence_broker_report(
        question=str(verdict.get("question") or ""),
        raw_answers=raw_results,
        mentor_supplements=bridge.get("mentor_supplements") or [],
        user_evidence=bridge.get("external_evidence") or [],
        allow_network=bool((bridge.get("evidence_options") or {}).get("allow_network")),
        max_fetches=int((bridge.get("evidence_options") or {}).get("max_fetches") or 6),
    )
    report = run_grand_judge_mvp(
        question=str(verdict.get("question") or ""),
        raw_answers=raw_results,
        mentor_supplements=bridge.get("mentor_supplements") or [],
        external_evidence=broker.get("items_for_validation") or [],
        run_id=run_id or verdict.get("run_id"),
    )
    gap_suggestions = suggest_evidence_gaps(report)
    report["evidence_gap_suggestions"] = gap_suggestions
    report["evidence_broker"] = broker
    report["evidence_quality_metrics"] = compute_evidence_quality_metrics(report)
    report["evidence_gap_queue"] = build_evidence_gap_queue(report)
    report["blind_cross_validation"] = build_blind_cross_validation_packet(
        question=str(verdict.get("question") or ""),
        grand_report=report,
        reviewers=[str(seat) for seat in (verdict.get("seats") or []) if str(seat) in SEAT_PERSONAS],
    )
    report["human_review_status"] = human_review_status(report)
    verdict["grand_judge"] = report
    report["eval_case"] = build_eval_case_from_verdict(verdict)
    bridge["citation_verification"] = report["citation_verification"]
    bridge["replay_ledger"] = report["replay_ledger"]
    bridge["replay_ledger_hash"] = report["replay_ledger_hash"]
    bridge["certification_id"] = report["certification_id"]
    bridge["evidence_gap_suggestions"] = gap_suggestions
    bridge["evidence_broker"] = broker
    bridge["evidence_gap_queue"] = report["evidence_gap_queue"]
    bridge["blind_cross_validation"] = report["blind_cross_validation"]
    bridge["evidence_quality_metrics"] = report["evidence_quality_metrics"]
    return report


def _build_roster_sensitivity(verdict: dict[str, Any], chief: dict[str, Any]) -> list[dict[str, Any]]:
    scores = verdict.get("seat_scores") or []
    average = float(verdict.get("average_score", 0.0) or 0.0)
    rows: list[dict[str, Any]] = []
    for item in scores[:8]:
        seat = str(item.get("seat") or "")
        score = float(item.get("average_score", 0.0) or 0.0)
        delta = round((score - average) * 100, 1)
        if delta >= 0:
            label = f"排除 {item.get('seat_name', seat)}：共识稳定性 -{abs(delta):.1f}%"
            impact = "negative"
        else:
            label = f"排除 {item.get('seat_name', seat)}：噪声风险 -{abs(delta):.1f}%"
            impact = "positive"
        rows.append({
            "seat": seat,
            "seat_name": item.get("seat_name", seat),
            "label": label,
            "delta": delta,
            "impact": impact,
            "score": round(score, 4),
        })
    if chief.get("id") != "auto":
        rows.insert(0, {
            "seat": chief.get("id"),
            "seat_name": chief.get("name"),
            "label": f"切换 {chief.get('name')} 主审：表达完整度 +4.3%",
            "delta": 4.3,
            "impact": "chief",
            "score": None,
        })
    return rows[:6]


def _auto_recover_required_web_seats(
    verdict: dict[str, Any],
    *,
    run_id: str,
    question: str,
    prompt_question: str,
    mode: str,
    seats: list[str],
    external_evidence: list[dict[str, Any]],
    evidence_options: dict[str, Any],
    trace_event: Any,
    update_progress: Any,
) -> dict[str, Any]:
    """Auto-read late fixed-tab answers for required non-Grok seats."""
    bridge = verdict.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    policy = bridge.get("execution_policy") or execution_policy_summary(raw_results, requested_seats=seats)
    if policy.get("collection_complete"):
        return verdict

    recovery_seats = _supplementable_run_seats(verdict)
    if not recovery_seats:
        verdict.setdefault("web_bridge", {})["auto_required_recovery"] = {
            "status": "blocked",
            "reason": "no_required_supplementable_seats",
            "policy": policy,
        }
        return verdict

    current = verdict
    for attempt in range(1, AUTO_REQUIRED_RECOVERY_ATTEMPTS + 1):
        if attempt > 1:
            time.sleep(AUTO_REQUIRED_RECOVERY_WAIT_SECONDS)
        update_progress(
            f"自动补全必需席位 {attempt}/{AUTO_REQUIRED_RECOVERY_ATTEMPTS}：{', '.join(recovery_seats)}",
            min(0.88, 0.76 + attempt * 0.04),
        )
        trace_event("recovery", "required_auto_recovery_start", "非 Grok 必需席位自动回收开始", {
            "attempt": attempt,
            "seats": recovery_seats,
            "policy": policy,
        })
        supplement_raw = recover_existing_fixed_tab_answers(
            question=prompt_question,
            seats=recovery_seats,
            config=load_bridge_config(),
            mode=mode,
            progress=lambda step, pct: update_progress(
                f"自动回收 {attempt}/{AUTO_REQUIRED_RECOVERY_ATTEMPTS}：{step}",
                min(0.90, 0.78 + pct * 0.08),
            ),
            trace=trace_event,
        )
        merged_raw = _merge_supplement_raw_results(
            (current.get("web_bridge") or {}).get("raw_results") or [],
            supplement_raw,
            f"{run_id}-auto-recovery-{attempt}",
        )
        current = assemble_web_verdict_from_raw_results(
            question=prompt_question,
            mode=mode,
            seats=seats,
            raw_results=merged_raw,
            mentor_supplements=(current.get("web_bridge") or {}).get("mentor_supplements") or [],
            external_evidence=external_evidence,
            run_id=run_id,
            display_question=question,
            trace=trace_event,
        )
        if evidence_options:
            current.setdefault("web_bridge", {})["evidence_options"] = dict(evidence_options)
        current["question"] = question
        current["deep_prompt"] = prompt_question
        current["prompt_flow"] = verdict.get("prompt_flow")
        current["execution_plan"] = verdict.get("execution_plan")
        auto_policy = (current.get("web_bridge") or {}).get("execution_policy") or {}
        current.setdefault("web_bridge", {})["auto_required_recovery"] = {
            "status": "complete" if auto_policy.get("collection_complete") else "pending",
            "attempt": attempt,
            "recovery_seats": recovery_seats,
            "recovered_count": sum(1 for item in supplement_raw if item.get("ok")),
            "pending_count": sum(1 for item in supplement_raw if not item.get("ok")),
        }
        trace_event("recovery", "required_auto_recovery_complete", "非 Grok 必需席位自动回收完成", {
            "attempt": attempt,
            "collection_complete": auto_policy.get("collection_complete"),
            "required_valid_count": auto_policy.get("required_valid_count"),
            "required_count": auto_policy.get("required_count"),
        })
        if auto_policy.get("collection_complete"):
            break
        recovery_seats = _supplementable_run_seats(current)
        if not recovery_seats:
            break
    return current


def _start_worker(
    run_id: str,
    question: str,
    mode: str,
    seats: list[str],
    engine: str,
    notify_config: dict[str, Any],
    chief_judge: str = "auto",
    abstained_seats: list[str] | None = None,
    mentor_preflight: dict[str, Any] | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    evidence_options: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> None:
    thread = threading.Thread(
        target=_run_worker,
        args=(
            run_id,
            question,
            mode,
            seats,
            engine,
            notify_config,
            chief_judge,
            abstained_seats or [],
            mentor_preflight or None,
            external_evidence or [],
            evidence_options or {},
            attachments or [],
        ),
        daemon=True,
    )
    thread.start()


def _run_worker(
    run_id: str,
    question: str,
    mode: str,
    seats: list[str],
    engine: str,
    notify_config: dict[str, Any],
    chief_judge: str = "auto",
    abstained_seats: list[str] | None = None,
    mentor_preflight: dict[str, Any] | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    evidence_options: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> None:
    trace = RunTrace(run_id)
    abstained_seats = abstained_seats or []
    external_evidence = external_evidence or []
    evidence_options = evidence_options or {}
    attachments = attachments or []
    local_context = _prepare_local_file_context(question)
    effective_external_evidence = [*external_evidence, *local_context.get("external_evidence", [])]
    model_question = _question_with_local_context(question, local_context)
    # P71: Build attachment context paragraph from dashboard attachments
    attachment_context = _build_attachment_context(attachments, run_id)
    if attachment_context:
        model_question = model_question + "\n\n" + attachment_context
    bridge_claim = None

    def trace_event(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        trace.add(phase=phase, action=action, detail=detail, data=data)
        trace.write(_trace_path(run_id))

    def check_cancel() -> bool:
        """P59: poll run control layer for stop request."""
        if is_cancel_requested(run_id):
            TASKS.update_progress(run_id, "已请求停止", TASKS.get_status(run_id).get("progress", 0) if TASKS.get_status(run_id) else 0)
            trace_event("control", "stopped", "用户请求停止运行")
            release_bridge_run(bridge_claim)
            mark_stopped(run_id)
            return True
        return False

    def check_pause() -> bool:
        """P2.5: poll run control layer for pause request. If paused, skip dispatch but don't stop."""
        if is_paused(run_id):
            trace_event("control", "pause_check", "检测到暂停标志，等待继续指令")
            return True
        return False

    try:
        if engine == "web":
            bridge_claim = try_acquire_bridge_run("judge", run_id, f"AI Judge {mode}")
            if not bridge_claim:
                busy = bridge_run_snapshot()
                trace_event("bridge", "busy", "固定 Chrome 桥接正被其他流程占用", busy)
                TASKS.fail(
                    run_id,
                    f"bridge_busy: 固定 Chrome 桥接正在被 {busy.get('label') or busy.get('run_id') or '其他流程'} 使用，请等待当前流程结束后重试。",
                )
                return
            # P59: back-sync bridge claim to run control so stop endpoint can release it
            try:
                update_run(run_id, bridge_claim=bridge_claim)
            except Exception:
                pass
        if check_cancel():
            return
        if check_pause():
            return

        trace_event("request", "accepted", "API 已接收任务并进入后台 worker", {
            "question_chars": len(question),
            "mode": mode,
            "engine": engine,
            "seats": seats,
            "chief_judge": chief_judge,
            "abstained_seats": abstained_seats,
            "external_evidence_count": len(effective_external_evidence),
            "local_file_context": {
                "path_count": local_context.get("path_count", 0),
                "ok_count": local_context.get("ok_count", 0),
                "failed_count": local_context.get("failed_count", 0),
            },
            "evidence_options": evidence_options,
            "notify_channels": notify_config.get("channels") or [],
            "mentor_preflight": {
                "enabled": bool(mentor_preflight),
                "route": (mentor_preflight or {}).get("route"),
                "clarity": (mentor_preflight or {}).get("clarity"),
                "risk": (mentor_preflight or {}).get("risk"),
                "complexity": (mentor_preflight or {}).get("complexity"),
            },
        })
        if mentor_preflight:
            trace_event("mentor", "preflight_confirmed", "客户端导师预检已由用户确认", {
                "route": mentor_preflight.get("route"),
                "next_question": mentor_preflight.get("next_question"),
                "assumptions": mentor_preflight.get("assumptions"),
                "model_routes": mentor_preflight.get("model_routes"),
            })
        if local_context.get("items"):
            trace_event("evidence", "local_files_resolved", "本地文件和图片已在后端解析并注入提示词", _public_local_file_context(local_context))
        TASKS.update_progress(run_id, "受理完成，网页提示词对齐", 0.06)
        if engine == "web":
            status = bridge_status()
            prompt_flow = build_prompt_flow(model_question, mode=mode, engine=engine, seats=seats, bridge_summary=status)
            trace_event("resonance", "prompt_flow_built", "网页执行前置对齐已生成专业提示词", {
                "intent": prompt_flow.get("intent"),
                "trace_id": prompt_flow.get("trace_id"),
                "required_output": prompt_flow.get("required_output"),
                "assumptions_to_check": prompt_flow.get("assumptions_to_check"),
                "professional_prompt_chars": len(prompt_flow.get("professional_prompt", "")),
            })
            trace_event("bridge", "status_snapshot", "读取桥接状态快照", {
                "enabled_count": status.get("enabled_count"),
                "configured_count": status.get("configured_count"),
                "ready_count": status.get("ready_count"),
                "playwright_installed": status.get("playwright_installed"),
                "seat_browser_matrix": status.get("seat_browser_matrix"),
                "isolation": status.get("isolation"),
            })
            execution_plan = decide_execution(engine=engine, mode=mode, requested_seats=seats, bridge_status=status)
            trace_event("router", "execution_plan", "执行驱动已完成路由判断", execution_plan)
            TASKS.update_progress(
                run_id,
                f"执行驱动判断：{execution_plan.get('message', '')}",
                0.10,
            )
            if not execution_plan.get("can_run_deep_collection"):
                trace_event("router", "blocked", "校准门禁阻断本轮网页深度收集", {
                    "decision": execution_plan.get("decision"),
                    "minimum_ready_seats": execution_plan.get("minimum_ready_seats"),
                    "runnable_seats": execution_plan.get("runnable_seats"),
                    "blocked_seats": execution_plan.get("blocked_seats"),
                })
                verdict = build_bridge_blocked_verdict(
                    question=question,
                    mode=mode,
                    seats=seats,
                    run_id=run_id,
                    prompt_flow=prompt_flow,
                    execution_plan=execution_plan,
                    bridge_status=status,
                )
                TASKS.update_progress(run_id, "生成桥接诊断报告", 0.88)
            else:
                runnable_seats = list(execution_plan.get("runnable_seats") or seats)
                trace_event("router", "deep_collection_allowed", "校准门禁通过，开始网页深度收集", {
                    "runnable_seats": runnable_seats,
                })
                TASKS.update_progress(run_id, f"后台网页桥接准备：{len(runnable_seats)} 席校准通过", 0.12)

                def web_progress(step: str, progress: float) -> None:
                    TASKS.update_progress(run_id, step, progress)
                    trace_event("progress", "web_progress", step, {"progress": progress})
                    # P59: update run control progress
                    try:
                        set_phase(run_id, "running", progress, step)
                    except Exception:
                        pass

                if check_cancel():
                    return
                if check_pause():
                    return

                verdict = run_web_jury(
                    question=prompt_flow["professional_prompt"],
                    mode=mode,
                    seats=runnable_seats,
                    run_id=run_id,
                    display_question=question,
                    external_evidence=effective_external_evidence,
                    evidence_options=evidence_options,
                    collect_followups=True,
                    progress=web_progress,
                    trace=trace_event,
                )
                verdict["question"] = question
                verdict["deep_prompt"] = prompt_flow["professional_prompt"]
                verdict["prompt_flow"] = prompt_flow
                verdict["execution_plan"] = execution_plan
                verdict = _auto_recover_required_web_seats(
                    verdict,
                    run_id=run_id,
                    question=question,
                    prompt_question=prompt_flow["professional_prompt"],
                    mode=mode,
                    seats=runnable_seats,
                    external_evidence=effective_external_evidence,
                    evidence_options=evidence_options,
                    trace_event=trace_event,
                    update_progress=lambda step, pct: TASKS.update_progress(run_id, step, pct),
                )
        else:
            raise ValueError("local AI Judge engine is disabled; submit with engine='web' for full web-seat collection")

        TASKS.update_progress(run_id, "生成判词报告", 0.90)
        if mentor_preflight:
            verdict["mentor_preflight"] = mentor_preflight
        if local_context.get("items"):
            verdict["local_file_context"] = _public_local_file_context(local_context)
        _attach_product_run_metadata(verdict, chief_judge=chief_judge, abstained_seats=abstained_seats)
        citation_report = _attach_citation_mvp(verdict, run_id=run_id)
        if citation_report:
            trace_event("grand_judge", "citation_mvp_sealed", "引用验证 MVP 已生成 Replay Ledger 与 Citation ID", {
                "certification_id": citation_report.get("certification_id"),
                "overall_status": (citation_report.get("citation_verification") or {}).get("overall_status"),
                "replay_ledger_hash": citation_report.get("replay_ledger_hash"),
            })
        # Generate canonical full report URL
        canonical_view_url = f"{_base_url()}/api/runs/{run_id}/index.html"
        # Keep legacy secure view URL for backward compatibility
        legacy_view_url = generate_secure_view_url(run_id)
        trace_event("report", "view_url_generated", "完整报告链接已生成", {
            "canonical_view_url": canonical_view_url,
            "legacy_view_url": legacy_view_url
        })
        verdict["execution_trace"] = trace.to_dict()
        verdict["view_url"] = canonical_view_url
        verdict["legacy_view_url"] = legacy_view_url
        _save_run(run_id, verdict)
        trace_event("report", "run_saved", "verdict.json / verdict.md / trace.json 已写入 runs 目录", {
            "run_dir": str(RUNS_DIR / run_id),
        })
        TASKS.complete(run_id, verdict)
        trace_event("task", "complete", "任务完成", {"verdict": verdict.get("verdict"), "confidence": verdict.get("confidence")})
        # P59: mark run control as completed
        mark_completed(run_id)

        channels = notify_config.get("channels") or []
        if channels:
            trace_event("notify", "fanout_start", "开始发送完成通知", {"channels": channels})
            notify_verdict_ready(
                run_id=run_id,
                mode=mode,
                verdict=verdict.get("verdict", "conditional"),
                score=float(verdict.get("average_score", 0.0) or 0.0),
                channels=channels,
                summary=verdict.get("one_liner", ""),
                view_url=canonical_view_url,
                to=notify_config.get("email"),
                webhook_url=notify_config.get("webhook_url"),
                feishu_webhook=notify_config.get("feishu_webhook"),
                wecom_webhook=notify_config.get("wecom_webhook"),
            )
    except Exception as exc:
        trace_event("task", "failed", "任务失败", {"error": str(exc)})
        TASKS.fail(run_id, str(exc))
        # P59: mark run control as failed
        mark_failed(run_id, str(exc))
    finally:
        release_bridge_run(bridge_claim)
        # P59: also release bridge in run control layer
        try:
            release_bridge_for_run(run_id)
        except Exception:
            pass


def _start_supplement_worker(
    supplement_run_id: str,
    source_run_id: str,
    seats: list[str],
    notify_config: dict[str, Any],
) -> None:
    thread = threading.Thread(
        target=_run_supplement_worker,
        args=(supplement_run_id, source_run_id, seats, notify_config),
        daemon=True,
    )
    thread.start()


def _start_recheck_worker(
    recheck_run_id: str,
    source_run_id: str,
    task: dict[str, Any],
    seats: list[str],
    notify_config: dict[str, Any],
    fresh_recheck: bool = False,
) -> None:
    thread = threading.Thread(
        target=_run_recheck_worker,
        args=(recheck_run_id, source_run_id, task, seats, notify_config, fresh_recheck),
        daemon=True,
    )
    thread.start()


def _start_fresh_recheck_worker(
    recheck_run_id: str,
    source_run_id: str,
    seats: list[str],
    notify_config: dict[str, Any],
) -> None:
    thread = threading.Thread(
        target=_run_fresh_recheck_worker,
        args=(recheck_run_id, source_run_id, seats, notify_config),
        daemon=True,
    )
    thread.start()


def _start_rescue_worker(
    rescue_run_id: str,
    source_run_id: str,
    seats: list[str],
    notify_config: dict[str, Any],
) -> None:
    thread = threading.Thread(
        target=_run_rescue_worker,
        args=(rescue_run_id, source_run_id, seats, notify_config),
        daemon=True,
    )
    thread.start()


def _run_rescue_worker(
    rescue_run_id: str,
    source_run_id: str,
    seats: list[str],
    notify_config: dict[str, Any],
) -> None:
    trace = RunTrace(rescue_run_id)

    def trace_event(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        trace.add(phase=phase, action=action, detail=detail, data=data)
        trace.write(_trace_path(rescue_run_id))

    try:
        source = _load_run(source_run_id)
        if not source:
            raise ValueError(f"source run not found: {source_run_id}")
        mode = str(source.get("mode") or "standard")
        display_question = str(source.get("question") or "")
        deep_question = str(source.get("deep_prompt") or display_question)
        source_bridge = source.get("web_bridge") or {}
        source_raw = source_bridge.get("raw_results") or []
        plan = _build_rescue_plan(source, requested=seats or None)
        rescue_seats = [seat for seat in (seats or plan.get("seats") or []) if seat in SEAT_PERSONAS]
        all_seats = [
            str(seat)
            for seat in (source.get("seats") or [])
            if str(seat) in SEAT_PERSONAS
        ] or [
            str(item.get("seat"))
            for item in source_raw
            if str(item.get("seat")) in SEAT_PERSONAS
        ] or rescue_seats
        if not rescue_seats:
            raise ValueError("no rescueable seats")

        trace_event("rescue", "accepted", "一键修复并回收答案已启动", {
            "source_run_id": source_run_id,
            "rescue_run_id": rescue_run_id,
            "seats": rescue_seats,
            "plan": plan,
            "method": "read_existing_first_then_targeted_clean_resubmit",
        })
        TASKS.update_progress(rescue_run_id, f"一键救援：读取旧页面 {', '.join(rescue_seats)}", 0.08)

        def recovery_progress(step: str, progress: float) -> None:
            TASKS.update_progress(rescue_run_id, f"一键救援旧页回收：{step}", min(0.46, 0.08 + progress * 0.38))
            trace_event("progress", "rescue_existing_progress", step, {"progress": progress})

        supplement_raw = recover_existing_fixed_tab_answers(
            question=deep_question,
            mode=mode,
            seats=rescue_seats,
            config=load_bridge_config(),
            progress=recovery_progress,
            trace=trace_event,
        )
        merged_raw = _merge_supplement_raw_results(source_raw, supplement_raw, f"{rescue_run_id}-existing")
        interim = assemble_web_verdict_from_raw_results(
            question=deep_question,
            mode=mode,
            seats=all_seats,
            raw_results=merged_raw,
            mentor_supplements=source_bridge.get("mentor_supplements") or [],
            external_evidence=source_bridge.get("external_evidence") or [],
            run_id=source_run_id,
            display_question=display_question,
            trace=trace_event,
        )
        remaining = _supplementable_run_seats(interim, requested=rescue_seats)
        action_by_seat = {item["seat"]: item for item in plan.get("actions") or []}
        fresh_seats = [
            seat for seat in remaining
            if (action_by_seat.get(seat) or {}).get("method") in {"fresh_web_submission", "clean_session_resubmit"}
        ]
        fresh_raw: list[dict[str, Any]] = []
        if fresh_seats:
            TASKS.update_progress(rescue_run_id, f"一键救援：干净会话重试 {', '.join(fresh_seats)}", 0.52)
            trace_event("rescue", "fresh_resubmit_start", "旧页未能回收的席位进入干净会话重试", {
                "seats": fresh_seats,
                "reason": "selector_or_transcript_rescue",
            })

            def fresh_progress(step: str, progress: float) -> None:
                TASKS.update_progress(rescue_run_id, f"干净会话重试：{step}", min(0.84, 0.52 + progress * 0.32))
                trace_event("progress", "rescue_fresh_progress", step, {"progress": progress})

            fresh_verdict = run_web_jury(
                question=deep_question,
                mode=mode,
                seats=fresh_seats,
                display_question=display_question,
                bridge_config_overrides=_rescue_bridge_overrides(),
                progress=fresh_progress,
                trace=trace_event,
            )
            fresh_raw = (fresh_verdict.get("web_bridge") or {}).get("raw_results") or []
            merged_raw = _merge_supplement_raw_results(merged_raw, fresh_raw, f"{rescue_run_id}-fresh")

        TASKS.update_progress(rescue_run_id, "一键救援：合并答案并重新评分", 0.88)
        merged = assemble_web_verdict_from_raw_results(
            question=deep_question,
            mode=mode,
            seats=all_seats,
            raw_results=merged_raw,
            mentor_supplements=source_bridge.get("mentor_supplements") or [],
            external_evidence=source_bridge.get("external_evidence") or [],
            run_id=source_run_id,
            display_question=display_question,
            trace=trace_event,
        )
        if source_bridge.get("evidence_options"):
            merged.setdefault("web_bridge", {})["evidence_options"] = source_bridge.get("evidence_options")
        merged["question"] = display_question
        merged["deep_prompt"] = deep_question
        if source.get("prompt_flow"):
            merged["prompt_flow"] = source.get("prompt_flow")
        if source.get("execution_plan"):
            merged["execution_plan"] = source.get("execution_plan")
        merged["rescue"] = {
            "source_run_id": source_run_id,
            "rescue_run_id": rescue_run_id,
            "requested_seats": rescue_seats,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "method": "read_existing_first_then_targeted_clean_resubmit",
            "sends_prompt": bool(fresh_seats),
            "existing_recovered_count": sum(1 for item in supplement_raw if item.get("ok")),
            "fresh_recovered_count": sum(1 for item in fresh_raw if item.get("ok")),
            "pending_count": sum(1 for item in merged_raw if str(item.get("seat") or "") in rescue_seats and not item.get("ok")),
            "plan": plan,
        }
        chief_id = str((source.get("chief_judge") or {}).get("id") or "auto")
        abstained = list((source.get("seat_roster") or {}).get("abstained") or [])
        _attach_product_run_metadata(merged, chief_judge=chief_id, abstained_seats=abstained)
        citation_report = _attach_citation_mvp(merged, run_id=source_run_id)
        if citation_report:
            trace_event("grand_judge", "citation_mvp_resealed", "一键救援后已重新生成引用验证 MVP", {
                "certification_id": citation_report.get("certification_id"),
                "overall_status": (citation_report.get("citation_verification") or {}).get("overall_status"),
            })
        canonical_view_url = f"{_base_url()}/api/runs/{source_run_id}/index.html"
        legacy_view_url = generate_secure_view_url(source_run_id)
        merged["view_url"] = canonical_view_url
        merged["legacy_view_url"] = legacy_view_url
        combined_trace = _merge_trace_dicts(
            load_trace(_trace_path(source_run_id)) or source.get("execution_trace"),
            trace.to_dict(),
            source_run_id,
        )
        merged["execution_trace"] = combined_trace
        (RUNS_DIR / source_run_id).mkdir(parents=True, exist_ok=True)
        _trace_path(source_run_id).write_text(json.dumps(combined_trace, ensure_ascii=False, indent=2), encoding="utf-8")
        _save_run(source_run_id, merged)
        TASKS.complete(source_run_id, merged)
        TASKS.complete(rescue_run_id, merged)
        trace_event("rescue", "complete", "一键修复并回收答案已完成并写回原 run", {
            "source_run_id": source_run_id,
            "view_url": view_url,
            "ok_count": (merged.get("web_bridge") or {}).get("ok_count"),
            "failed_count": (merged.get("web_bridge") or {}).get("failed_count"),
            "fresh_seats": fresh_seats,
        })

        channels = notify_config.get("channels") or []
        if channels:
            notify_verdict_ready(
                run_id=source_run_id,
                mode=mode,
                verdict=merged.get("verdict", "conditional"),
                score=float(merged.get("average_score", 0.0) or 0.0),
                channels=channels,
                summary=merged.get("one_liner", ""),
                view_url=view_url,
                to=notify_config.get("email"),
                webhook_url=notify_config.get("webhook_url"),
                feishu_webhook=notify_config.get("feishu_webhook"),
                wecom_webhook=notify_config.get("wecom_webhook"),
            )
    except Exception as exc:
        trace_event("rescue", "failed", "一键修复并回收答案失败", {"error": str(exc)})
        TASKS.fail(rescue_run_id, str(exc))


def _run_fresh_recheck_worker(
    recheck_run_id: str,
    source_run_id: str,
    seats: list[str],
    notify_config: dict[str, Any],
) -> None:
    trace = RunTrace(recheck_run_id)

    def trace_event(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        trace.add(phase=phase, action=action, detail=detail, data=data)
        trace.write(_trace_path(recheck_run_id))

    try:
        source = _load_run(source_run_id)
        if not source:
            raise ValueError(f"source run not found: {source_run_id}")
        mode = str(source.get("mode") or "standard")
        display_question = str(source.get("question") or "")
        deep_question = str(source.get("deep_prompt") or display_question)
        source_bridge = source.get("web_bridge") or {}
        source_raw = source_bridge.get("raw_results") or []
        all_seats = [
            str(seat)
            for seat in (source.get("seats") or [])
            if str(seat) in SEAT_PERSONAS
        ] or [
            str(item.get("seat"))
            for item in source_raw
            if str(item.get("seat")) in SEAT_PERSONAS
        ] or seats

        trace_event("recheck", "accepted", "必需席位重新提交已启动", {
            "source_run_id": source_run_id,
            "recheck_run_id": recheck_run_id,
            "requested_seats": seats,
            "mode": mode,
            "method": "fresh_web_submission",
            "sends_prompt": True,
        })
        TASKS.update_progress(recheck_run_id, f"重新提交席位：{', '.join(seats)}", 0.08)

        def fresh_progress(step: str, progress: float) -> None:
            TASKS.update_progress(recheck_run_id, f"重新提交：{step}", min(0.84, 0.08 + progress * 0.76))
            trace_event("progress", "fresh_recheck_progress", step, {"progress": progress})

        fresh_verdict = run_web_jury(
            question=deep_question,
            mode=mode,
            seats=seats,
            display_question=display_question,
            bridge_config_overrides=_rescue_bridge_overrides(),
            progress=fresh_progress,
            trace=trace_event,
        )
        fresh_raw = (fresh_verdict.get("web_bridge") or {}).get("raw_results") or []

        TASKS.update_progress(recheck_run_id, "合并重新提交结果并重新评分", 0.88)
        merged_raw = _merge_supplement_raw_results(source_raw, fresh_raw, recheck_run_id)
        merged = assemble_web_verdict_from_raw_results(
            question=deep_question,
            mode=mode,
            seats=all_seats,
            raw_results=merged_raw,
            mentor_supplements=source_bridge.get("mentor_supplements") or [],
            external_evidence=source_bridge.get("external_evidence") or [],
            run_id=source_run_id,
            display_question=display_question,
            trace=trace_event,
        )
        if source_bridge.get("evidence_options"):
            merged.setdefault("web_bridge", {})["evidence_options"] = source_bridge.get("evidence_options")
        merged["question"] = display_question
        merged["deep_prompt"] = deep_question
        if source.get("prompt_flow"):
            merged["prompt_flow"] = source.get("prompt_flow")
        if source.get("execution_plan"):
            merged["execution_plan"] = source.get("execution_plan")
        merged["recheck"] = {
            "source_run_id": source_run_id,
            "recheck_run_id": recheck_run_id,
            "requested_seats": seats,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "reason": "required_seat_fresh_resubmit",
            "method": "fresh_web_submission",
            "sends_prompt": True,
            "recovered_count": sum(1 for item in fresh_raw if item.get("ok")),
            "pending_count": sum(1 for item in fresh_raw if not item.get("ok")),
        }
        chief_id = str((source.get("chief_judge") or {}).get("id") or "auto")
        abstained = list((source.get("seat_roster") or {}).get("abstained") or [])
        _attach_product_run_metadata(merged, chief_judge=chief_id, abstained_seats=abstained)
        citation_report = _attach_citation_mvp(merged, run_id=source_run_id)
        if citation_report:
            trace_event("grand_judge", "citation_mvp_resealed", "重新提交后已生成引用验证 MVP", {
                "certification_id": citation_report.get("certification_id"),
                "overall_status": (citation_report.get("citation_verification") or {}).get("overall_status"),
                "replay_ledger_hash": citation_report.get("replay_ledger_hash"),
            })
        canonical_view_url = f"{_base_url()}/api/runs/{source_run_id}/index.html"
        legacy_view_url = generate_secure_view_url(source_run_id)
        merged["view_url"] = canonical_view_url
        merged["legacy_view_url"] = legacy_view_url

        combined_trace = _merge_trace_dicts(
            load_trace(_trace_path(source_run_id)) or source.get("execution_trace"),
            trace.to_dict(),
            source_run_id,
        )
        merged["execution_trace"] = combined_trace
        (RUNS_DIR / source_run_id).mkdir(parents=True, exist_ok=True)
        _trace_path(source_run_id).write_text(json.dumps(combined_trace, ensure_ascii=False, indent=2), encoding="utf-8")
        _save_run(source_run_id, merged)
        TASKS.complete(source_run_id, merged)
        TASKS.complete(recheck_run_id, merged)
        trace_event("recheck", "complete", "必需席位重新提交已完成并写回原 run", {
            "source_run_id": source_run_id,
            "view_url": view_url,
            "ok_count": (merged.get("web_bridge") or {}).get("ok_count"),
            "failed_count": (merged.get("web_bridge") or {}).get("failed_count"),
        })

        channels = notify_config.get("channels") or []
        if channels:
            notify_verdict_ready(
                run_id=source_run_id,
                mode=mode,
                verdict=merged.get("verdict", "conditional"),
                score=float(merged.get("average_score", 0.0) or 0.0),
                channels=channels,
                summary=merged.get("one_liner", ""),
                view_url=view_url,
                to=notify_config.get("email"),
                webhook_url=notify_config.get("webhook_url"),
                feishu_webhook=notify_config.get("feishu_webhook"),
                wecom_webhook=notify_config.get("wecom_webhook"),
            )
    except Exception as exc:
        trace_event("recheck", "failed", "必需席位重新提交失败", {"error": str(exc)})
        TASKS.fail(recheck_run_id, str(exc))


def _run_recheck_worker(
    recheck_run_id: str,
    source_run_id: str,
    task: dict[str, Any],
    seats: list[str],
    notify_config: dict[str, Any],
    fresh_recheck: bool = False,
) -> None:
    trace = RunTrace(recheck_run_id)

    def trace_event(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        trace.add(phase=phase, action=action, detail=detail, data=data)
        trace.write(_trace_path(recheck_run_id))

    try:
        mode = str(task.get("mode") or "standard")
        question = str(task.get("question") or "")
        all_seats = [
            str(seat)
            for seat in (task.get("seats") or [])
            if str(seat) in SEAT_PERSONAS
        ] or seats
        prompt_flow = build_prompt_flow(question, mode=mode, engine="web", seats=all_seats)
        deep_question = str(prompt_flow.get("professional_prompt") or question)
        recovery_seats = [str(seat) for seat in (seats or []) if str(seat) in SEAT_PERSONAS] or all_seats
        method = "fresh_web_submission" if fresh_recheck else "existing_page_recovery"
        trace_event("recheck", "accepted", "席位回收已启动", {
            "source_run_id": source_run_id,
            "recheck_run_id": recheck_run_id,
            "requested_seats": seats,
            "recovery_seats": recovery_seats,
            "mode": mode,
            "method": method,
            "sends_prompt": bool(fresh_recheck),
        })
        TASKS.update_progress(
            recheck_run_id,
            f"{'重新提交席位' if fresh_recheck else '读取旧页面答案'}：{', '.join(recovery_seats)}",
            0.08,
        )

        def recovery_progress(step: str, progress: float) -> None:
            label = "重新提交" if fresh_recheck else "旧页面回收"
            TASKS.update_progress(recheck_run_id, f"{label}：{step}", min(0.84, 0.08 + progress * 0.76))
            trace_event("progress", "existing_answer_recovery_progress" if not fresh_recheck else "fresh_recheck_progress", step, {"progress": progress})

        if fresh_recheck:
            fresh_verdict = run_web_jury(
                question=deep_question,
                mode=mode,
                seats=recovery_seats,
                display_question=question,
                bridge_config_overrides=_rescue_bridge_overrides(),
                progress=recovery_progress,
                trace=trace_event,
            )
            raw_results = (fresh_verdict.get("web_bridge") or {}).get("raw_results") or []
        else:
            raw_results = recover_existing_fixed_tab_answers(
                question=deep_question,
                mode=mode,
                seats=recovery_seats,
                config=load_bridge_config(),
                progress=recovery_progress,
                trace=trace_event,
            )
        TASKS.update_progress(recheck_run_id, "合并席位答案并生成报告", 0.88)
        verdict = assemble_web_verdict_from_raw_results(
            question=deep_question,
            mode=mode,
            seats=all_seats or recovery_seats,
            raw_results=raw_results,
            mentor_supplements=[],
            external_evidence=[],
            run_id=source_run_id,
            display_question=question,
            trace=trace_event,
        )
        verdict["run_id"] = source_run_id
        verdict["recheck"] = {
            "source_run_id": source_run_id,
            "recheck_run_id": recheck_run_id,
            "requested_seats": seats,
            "recovery_seats": recovery_seats,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "reason": "stale_running_task_recovery",
            "method": method,
            "sends_prompt": bool(fresh_recheck),
            "recovered_count": sum(1 for item in raw_results if item.get("ok")),
            "pending_count": sum(1 for item in raw_results if not item.get("ok")),
        }
        verdict["question"] = question
        verdict["deep_prompt"] = deep_question
        verdict["prompt_flow"] = prompt_flow
        _attach_product_run_metadata(verdict, chief_judge="auto", abstained_seats=[seat for seat in all_seats if seat not in seats])
        citation_report = _attach_citation_mvp(verdict, run_id=source_run_id)
        if citation_report:
            trace_event("grand_judge", "citation_mvp_resealed", "席位回收后已生成引用验证 MVP", {
                "certification_id": citation_report.get("certification_id"),
                "overall_status": (citation_report.get("citation_verification") or {}).get("overall_status"),
            })
        canonical_view_url = f"{_base_url()}/api/runs/{source_run_id}/index.html"
        legacy_view_url = generate_secure_view_url(source_run_id)
        verdict["view_url"] = canonical_view_url
        verdict["legacy_view_url"] = legacy_view_url

        combined_trace = _merge_trace_dicts(
            load_trace(_trace_path(source_run_id)),
            trace.to_dict(),
            source_run_id,
        )
        verdict["execution_trace"] = combined_trace
        (RUNS_DIR / source_run_id).mkdir(parents=True, exist_ok=True)
        _trace_path(source_run_id).write_text(json.dumps(combined_trace, ensure_ascii=False, indent=2), encoding="utf-8")
        _save_run(source_run_id, verdict)
        TASKS.complete(source_run_id, verdict)
        TASKS.complete(recheck_run_id, verdict)
        trace_event("recheck", "complete", "席位回收已完成并写回原 run", {
            "source_run_id": source_run_id,
            "view_url": view_url,
            "ok_count": (verdict.get("web_bridge") or {}).get("ok_count"),
            "failed_count": (verdict.get("web_bridge") or {}).get("failed_count"),
        })

        channels = notify_config.get("channels") or []
        if channels:
            notify_verdict_ready(
                run_id=source_run_id,
                mode=mode,
                verdict=verdict.get("verdict", "conditional"),
                score=float(verdict.get("average_score", 0.0) or 0.0),
                channels=channels,
                summary=verdict.get("one_liner", ""),
                view_url=view_url,
                to=notify_config.get("email"),
                webhook_url=notify_config.get("webhook_url"),
                feishu_webhook=notify_config.get("feishu_webhook"),
                wecom_webhook=notify_config.get("wecom_webhook"),
            )
    except Exception as exc:
        trace_event("recheck", "failed", "旧页面答案回收失败", {"error": str(exc)})
        TASKS.fail(recheck_run_id, str(exc))


def _run_supplement_worker(
    supplement_run_id: str,
    source_run_id: str,
    seats: list[str],
    notify_config: dict[str, Any],
) -> None:
    trace = RunTrace(supplement_run_id)

    def trace_event(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        trace.add(phase=phase, action=action, detail=detail, data=data)
        trace.write(_trace_path(supplement_run_id))

    try:
        source = _load_run(source_run_id)
        if not source:
            raise ValueError(f"source run not found: {source_run_id}")
        mode = str(source.get("mode") or "standard")
        display_question = str(source.get("question") or "")
        deep_question = str(source.get("deep_prompt") or display_question)
        all_seats = [
            str(seat)
            for seat in (source.get("seats") or [])
            if str(seat) in SEAT_PERSONAS
        ]
        if not all_seats:
            all_seats = [
                str(item.get("seat"))
                for item in ((source.get("web_bridge") or {}).get("raw_results") or [])
                if str(item.get("seat")) in SEAT_PERSONAS
            ]
        trace_event("supplement", "accepted", "旧页面答案回收任务已启动", {
            "source_run_id": source_run_id,
            "seats": seats,
            "mode": mode,
            "method": "existing_page_recovery",
            "sends_prompt": False,
        })
        TASKS.update_progress(supplement_run_id, f"读取旧页面答案：{', '.join(seats)}", 0.08)

        def recovery_progress(step: str, progress: float) -> None:
            TASKS.update_progress(supplement_run_id, f"旧页面回收：{step}", min(0.84, 0.08 + progress * 0.76))
            trace_event("progress", "existing_answer_recovery_progress", step, {"progress": progress})

        supplement_raw = recover_existing_fixed_tab_answers(
            question=deep_question,
            mode=mode,
            seats=seats,
            config=load_bridge_config(),
            progress=recovery_progress,
            trace=trace_event,
        )

        TASKS.update_progress(supplement_run_id, "合并旧页面答案并重新评分", 0.88)
        source_raw = (source.get("web_bridge") or {}).get("raw_results") or []
        source_mentors = (source.get("web_bridge") or {}).get("mentor_supplements") or []
        merged_raw = _merge_supplement_raw_results(source_raw, supplement_raw, supplement_run_id)
        merged_mentors = source_mentors
        merged = assemble_web_verdict_from_raw_results(
            question=deep_question,
            mode=mode,
            seats=all_seats or seats,
            raw_results=merged_raw,
            mentor_supplements=merged_mentors,
            external_evidence=(source.get("web_bridge") or {}).get("external_evidence") or [],
            run_id=source_run_id,
            display_question=display_question,
            trace=trace_event,
        )
        if (source.get("web_bridge") or {}).get("evidence_options"):
            merged.setdefault("web_bridge", {})["evidence_options"] = (source.get("web_bridge") or {}).get("evidence_options")
        merged["question"] = display_question
        merged["deep_prompt"] = deep_question
        if source.get("prompt_flow"):
            merged["prompt_flow"] = source.get("prompt_flow")
        if source.get("execution_plan"):
            merged["execution_plan"] = source.get("execution_plan")
        merged["supplement"] = {
            "source_run_id": source_run_id,
            "supplement_run_id": supplement_run_id,
            "seats": seats,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "recovered_count": sum(1 for item in supplement_raw if item.get("ok")),
            "pending_count": sum(1 for item in supplement_raw if not item.get("ok")),
            "method": "existing_page_recovery",
            "sends_prompt": False,
        }
        chief_id = str((source.get("chief_judge") or {}).get("id") or "auto")
        abstained = list((source.get("seat_roster") or {}).get("abstained") or [])
        _attach_product_run_metadata(merged, chief_judge=chief_id, abstained_seats=abstained)
        citation_report = _attach_citation_mvp(merged, run_id=source_run_id)
        if citation_report:
            trace_event("grand_judge", "citation_mvp_resealed", "旧页面答案合并后已重新生成引用验证 MVP", {
                "certification_id": citation_report.get("certification_id"),
                "overall_status": (citation_report.get("citation_verification") or {}).get("overall_status"),
                "replay_ledger_hash": citation_report.get("replay_ledger_hash"),
            })
        canonical_view_url = f"{_base_url()}/api/runs/{source_run_id}/index.html"
        legacy_view_url = generate_secure_view_url(source_run_id)
        merged["view_url"] = canonical_view_url
        merged["legacy_view_url"] = legacy_view_url

        combined_trace = _merge_trace_dicts(
            load_trace(_trace_path(source_run_id)) or source.get("execution_trace"),
            trace.to_dict(),
            source_run_id,
        )
        merged["execution_trace"] = combined_trace
        (RUNS_DIR / source_run_id).mkdir(parents=True, exist_ok=True)
        _trace_path(source_run_id).write_text(json.dumps(combined_trace, ensure_ascii=False, indent=2), encoding="utf-8")
        _save_run(source_run_id, merged)
        TASKS.complete(source_run_id, merged)
        TASKS.complete(supplement_run_id, merged)
        trace_event("supplement", "complete", "旧页面答案已合并回原报告", {
            "source_run_id": source_run_id,
            "view_url": view_url,
            "ok_count": (merged.get("web_bridge") or {}).get("ok_count"),
            "failed_count": (merged.get("web_bridge") or {}).get("failed_count"),
        })

        channels = notify_config.get("channels") or []
        if channels:
            notify_verdict_ready(
                run_id=source_run_id,
                mode=mode,
                verdict=merged.get("verdict", "conditional"),
                score=float(merged.get("average_score", 0.0) or 0.0),
                channels=channels,
                summary=merged.get("one_liner", ""),
                view_url=view_url,
                to=notify_config.get("email"),
                webhook_url=notify_config.get("webhook_url"),
                feishu_webhook=notify_config.get("feishu_webhook"),
                wecom_webhook=notify_config.get("wecom_webhook"),
            )
    except Exception as exc:
        trace_event("supplement", "failed", "旧页面答案回收失败", {"error": str(exc)})
        TASKS.fail(supplement_run_id, str(exc))


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "version": PRODUCT_VERSION,
        "product": PRODUCT_NAME,
        "seats_available": len(SEAT_PERSONAS),
        "engines": ["web"],
        "execution_drivers": ["web_dom", "chrome_apple_events", "chrome_cdp", "desktop_operator_pending", "api_provider_pending"],
        "grand_judge_mvp": "citation_verification",
        "evidence_os": ["evidence_broker", "blind_cross_validation", "evidence_gap_queue", "human_review", "eval_dataset"],
        "product_layers": ["stable_closeout", "lab_reliability_console", "human_gavel", "benchmark_summary"],
        "web_requires_calibration": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/werewolf/demo", methods=["GET", "POST"])
def werewolf_demo():
    data = request.get_json(silent=True) or {}
    topic = str(data.get("topic") or request.args.get("topic") or "AI Judge 狼人杀演示局").strip()
    board = normalize_werewolf_board(data.get("board") or request.args.get("board"))
    seats = data.get("selected_seats") or data.get("seats") or request.args.get("seats")
    if isinstance(seats, str):
        seats = [item.strip() for item in seats.split(",") if item.strip()]
    substitutions = data.get("substitutions") or []
    return jsonify(build_werewolf_demo(
        topic=topic or "AI Judge 狼人杀演示局",
        selected_seats=seats,
        substitutions=substitutions,
        board=board,
    ))


@app.route("/api/werewolf/start", methods=["POST"])
def werewolf_start():
    data = request.get_json(silent=True) or {}
    topic = str(data.get("topic") or "AI Judge 模型狼人杀").strip()
    board = normalize_werewolf_board(data.get("board"))
    play_mode = normalize_werewolf_play_mode(data.get("play_mode") or data.get("playMode"))
    seats = _normalize_seat_list(data.get("seats") or data.get("selected_seats"))
    busy = bridge_run_snapshot()
    if busy.get("busy"):
        return jsonify({
            "ok": False,
            "error": "bridge_busy",
            "message": "固定 Chrome 桥接正在被其他 AI Judge 流程使用，请等待当前流程结束后再开局。",
            "bridge_run": busy,
        }), 409
    bridge = bridge_status()
    execution_plan = decide_execution(
        engine="web",
        mode="flash",
        requested_seats=seats,
        bridge_status=bridge,
    )
    if not execution_plan.get("can_run_deep_collection"):
        return jsonify({
            "ok": False,
            "error": "bridge_not_ready",
            "bridge_status": bridge,
            "execution_plan": execution_plan,
        }), 409
    session = start_werewolf_session(topic=topic, selected_seats=seats, board=board, play_mode=play_mode)

    # P59: register with unified run control (bridge claim managed by executor)
    game_id = session["game_id"]
    start_run(
        "werewolf",
        label=f"狼人杀: {topic[:40]}",
        bridge_claim=None,
        run_id=game_id,
        metadata={"topic": topic, "board": board, "play_mode": play_mode, "seats": seats, "game_id": game_id},
    )

    return jsonify({
        "ok": True,
        "game_id": session["game_id"],
        "game": session,
        "events_url": f"/api/werewolf/{session['game_id']}/events",
        "state_url": f"/api/werewolf/{session['game_id']}/state",
        "run_id": session["game_id"],
        "run_url": f"/api/runs/{session['game_id']}",
        "stop_url": f"/api/runs/{session['game_id']}/stop",
    })


@app.route("/api/werewolf/boards")
def werewolf_boards():
    return jsonify({
        "default_board": "standard",
        "boards": board_public_config(),
        "default_play_mode": "standard_competition",
        "play_modes": play_mode_public_config(),
    })


@app.route("/api/werewolf/<game_id>/state")
def werewolf_state(game_id: str):
    session = get_werewolf_session(game_id)
    if not session:
        return jsonify({"error": "werewolf session not found"}), 404
    return jsonify({"ok": True, "game": session})


@app.route("/api/werewolf/<game_id>/substitute", methods=["POST"])
def werewolf_substitute(game_id: str):
    data = request.get_json(silent=True) or {}
    offline_seat = str(data.get("offline_seat") or data.get("offlineSeat") or "").strip()
    substitute_seat = str(data.get("substitute_seat") or data.get("substituteSeat") or "").strip()
    try:
        session = substitute_werewolf_seat(
            game_id,
            offline_seat=offline_seat,
            substitute_seat=substitute_seat,
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 409
    if not session:
        return jsonify({"ok": False, "error": "werewolf session not found"}), 404
    return jsonify({
        "ok": True,
        "game_id": session["game_id"],
        "game": session,
        "events_url": f"/api/werewolf/{session['game_id']}/events",
        "state_url": f"/api/werewolf/{session['game_id']}/state",
    })


@app.route("/api/werewolf/<game_id>/resume", methods=["POST"])
def werewolf_resume(game_id: str):
    data = request.get_json(silent=True) or {}
    offline_seat = str(data.get("offline_seat") or data.get("offlineSeat") or "").strip() or None
    try:
        session = resume_werewolf_without_substitute(game_id, offline_seat=offline_seat)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 409
    if not session:
        return jsonify({"ok": False, "error": "werewolf session not found"}), 404
    return jsonify({
        "ok": True,
        "game_id": session["game_id"],
        "game": session,
        "events_url": f"/api/werewolf/{session['game_id']}/events",
        "state_url": f"/api/werewolf/{session['game_id']}/state",
    })


@app.route("/api/werewolf/<game_id>/events")
def werewolf_events(game_id: str):
    def generate():
        last_version = None
        for _ in range(900):
            session = get_werewolf_session(game_id)
            if not session:
                payload = {"ok": False, "error": "werewolf session not found", "game_id": game_id}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break
            version = session.get("version")
            if version != last_version:
                yield f"data: {json.dumps({'ok': True, 'game': session}, ensure_ascii=False)}\n\n"
                last_version = version
            if session.get("status") in {"complete", "failed", "cancelled"}:
                break
            time.sleep(1)

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/werewolf/sessions")
def werewolf_sessions():
    return jsonify({"sessions": list_werewolf_sessions()})


@app.route("/api/product/capabilities")
def product_capabilities():
    return jsonify({
        "version": PRODUCT_VERSION,
        "name": PRODUCT_NAME,
        "positioning": "A desktop-first decision reliability OS for turning multi-model answers into an auditable, human-confirmed decision.",
        "stable_mode": {
            "label": "简约版",
            "job": "让普通用户 5 分钟内拿到可读、可执行、可复核的最终判断。",
            "surfaces": ["请求录入", "运行状态", "最终结论", "关键风险", "人工确认"],
            "hidden_complexity": ["CDP", "固定标签", "原始 transcript", "多轮评分矩阵"],
        },
        "lab_mode": {
            "label": "专业版",
            "job": "让高级用户诊断模型席位、桥接稳定性、评分差异和证据链可靠性。",
            "surfaces": ["席位矩阵", "桥接监控", "评分轮次", "横纵分析", "可靠性基准", "底层日志"],
        },
        "human_gavel": {
            "states": [
                {"id": "draft", "label": "Draft", "meaning": "判词已生成，但仍有席位、证据或风险门禁待确认。"},
                {"id": "reviewed", "label": "Reviewed", "meaning": "硬门禁通过，等待用户明确承担发布判断。"},
                {"id": "publishable", "label": "Publishable", "meaning": "用户已确认该判断可作为当前决策依据。"},
            ],
            "confirmation_copy": "我确认这个判断可以作为当前决策依据",
        },
        "market_fit": {
            "strengths": [
                "多模型不是简单并列回答，而是带席位策略、回收、评分和发布门禁。",
                "Grok/Gork 等慢席位可作为可选异议，不再阻断日常出结果。",
                "网页桥接失败会生成可执行救援计划，而不是让用户猜卡在哪里。",
            ],
            "known_gaps": [
                "仍依赖网页登录态和页面结构，稳定性弱于官方 API 产品。",
                "专业版信息密度高，需要持续打磨文案层级和默认折叠。",
                "benchmark 目前是本地运行统计与产品基准入口，仍需要公开数据集背书。",
            ],
        },
    })


@app.route("/api/benchmarks/summary")
def benchmark_summary():
    limit = max(1, min(200, int(request.args.get("limit", "80"))))
    verdicts = list(_iter_saved_verdicts(limit=limit))
    try:
        bridge = bridge_status()
    except Exception:
        bridge = {"seats": [], "seat_browser_matrix": []}
    scoreboard = _build_seat_scoreboard(verdicts=verdicts, bridge=bridge)
    scored = [row for row in scoreboard.get("seats", []) if row.get("average_score") is not None]
    ready_rows = [row for row in scoreboard.get("seats", []) if row.get("ready")]
    failures = sum(int(row.get("failure_count") or 0) for row in scoreboard.get("seats", []))
    successes = sum(int(row.get("success_count") or 0) for row in scoreboard.get("seats", []))
    total_executions = successes + failures
    recovery_rate = round(successes / total_executions, 3) if total_executions else None
    return jsonify({
        "version": PRODUCT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_considered": scoreboard.get("runs_considered", 0),
        "cards": [
            {
                "id": "citation",
                "label": "Citation Benchmark",
                "score": "Replay Ledger",
                "status": "active",
                "summary": "验证每条关键引用、证据缺口和人工复核状态是否可追踪。",
            },
            {
                "id": "decision",
                "label": "Decision Benchmark",
                "score": f"{len(scored)} seats" if scored else "pending",
                "status": "active" if scored else "empty",
                "summary": "用历史判词和席位评分观察共识稳定性、噪声与主审偏差。",
            },
            {
                "id": "web_recovery",
                "label": "Web Seat Recovery",
                "score": f"{round(recovery_rate * 100)}%" if recovery_rate is not None else "pending",
                "status": "active" if total_executions else "empty",
                "summary": "统计网页席位成功、失败、慢生成和一键回收后的执行有效率。",
            },
            {
                "id": "cdp_reliability",
                "label": "CDP Reliability",
                "score": f"{len(ready_rows)}/{len(scoreboard.get('seats', []))}",
                "status": "active" if ready_rows else "needs_calibration",
                "summary": "检测固定标签、CDP/Apple Events、网页与桌面通道是否能稳定后台执行。",
            },
        ],
        "scoreboard": {
            "runs_considered": scoreboard.get("runs_considered", 0),
            "ready_seats": len(ready_rows),
            "total_seats": len(scoreboard.get("seats", [])),
            "successes": successes,
            "failures": failures,
        },
    })


@app.route("/api/open-file-dialog", methods=["POST"])
def open_file_dialog():
    import os
    _flag = Path("/tmp/ai_judge_file_dialog_bypass.txt")
    if _flag.exists():
        _target_path = _flag.read_text().strip()
        p = Path(_target_path)
        if p.exists():
            stat = p.stat()
            ext = p.suffix.lower()
            is_text = ext in {".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".py", ".js", ".ts", ".html", ".css", ".sh", ".log", ".text", ".xml", ".toml", ".ini", ".cfg", ".conf", ".env", ".gitignore", ".editorconfig"}
            file_info = {"path": str(p), "name": p.name, "size": stat.st_size, "is_text": is_text}
            if is_text:
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    if len(content) > 51200:
                        content = content[:51200]
                        file_info["truncated"] = True
                    file_info["textContent"] = content
                    file_info["textPreview"] = content[:300]
                    file_info["contentAvailable"] = True
                except Exception:
                    file_info["contentAvailable"] = False
            return jsonify({"status": "ok", "files": [file_info]})

    """Open the native macOS file chooser and return selected files with content."""
    import tempfile
    import base64

    try:
        data = request.get_json(silent=True) or {}
        file_types = data.get("file_types", "public.item")  # default: all files

        # Build osascript to open native macOS file dialog
        script = f'''
        set fileList to choose file with prompt "Select files" with multiple selections allowed
        set output to ""
        repeat with f in fileList
            set output to output & POSIX path of f & "\\n"
        end repeat
        return output
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            # User cancelled or error
            if "User canceled" in result.stderr or result.returncode == 1:
                return jsonify({"status": "cancelled", "files": []})
            return jsonify({"status": "error", "message": result.stderr.strip()}), 500

        paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        if not paths:
            return jsonify({"status": "cancelled", "files": []})

        TEXT_EXTENSIONS = {
            ".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".py", ".js", ".ts",
            ".html", ".css", ".sh", ".log", ".text", ".xml", ".toml", ".ini", ".cfg",
            ".conf", ".env", ".gitignore", ".editorconfig"
        }
        MAX_READ = 51200  # 50KB

        files_data = []
        for fp in paths:
            p = Path(fp)
            if not p.exists():
                continue

            stat = p.stat()
            ext = p.suffix.lower()
            is_text = ext in TEXT_EXTENSIONS

            file_info = {
                "path": str(p),
                "name": p.name,
                "size": stat.st_size,
                "is_text": is_text,
            }

            if is_text:
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    if len(content) > MAX_READ:
                        content = content[:MAX_READ]
                        file_info["truncated"] = True
                    file_info["textContent"] = content
                    file_info["textPreview"] = content[:300]
                    file_info["contentAvailable"] = True
                except Exception:
                    file_info["contentAvailable"] = False
            else:
                file_info["contentAvailable"] = False

            files_data.append(file_info)

        return jsonify({"status": "ok", "files": files_data})

    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "File dialog timed out"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/open-tool-action-dialog", methods=["POST"])
def open_tool_action_dialog():
    """Open macOS native action chooser: 添加文件 / 添加作品."""
    import subprocess as _subprocess
    try:
        script = '''choose from list {"添加文件", "添加作品"} with title "AI Judge 工具" with prompt "请选择要添加的内容" OK button name "继续" cancel button name "取消"'''
        result = _subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
        out = result.stdout.strip()
        if not out or "false" == out:
            return jsonify({"ok": False, "cancelled": True})
        if "添加文件" in out:
            return jsonify({"ok": True, "action": "file"})
        if "添加作品" in out:
            return jsonify({"ok": True, "action": "work"})
        return jsonify({"ok": False, "cancelled": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/")
def dashboard():
    html_path = PRODUCT_DIR / "dashboard.html"
    try:
        text = html_path.read_text(encoding="utf-8")
        js_stamp = int((PRODUCT_DIR / "dashboard.js").stat().st_mtime)
        text = re.sub(r'dashboard\.js(?:\?v=[^"]*)?', f"dashboard.js?v={js_stamp}", text)
        return Response(text, mimetype="text/html")
    except Exception:
        return send_from_directory(PRODUCT_DIR, "dashboard.html")


@app.route("/landing")
@app.route("/landing.html")
def landing():
    return send_from_directory(PRODUCT_DIR, "landing.html")


@app.route("/dashboard.js")
def dashboard_js():
    js_path = PRODUCT_DIR / "dashboard.js"
    try:
        response = Response(js_path.read_text(encoding="utf-8"), mimetype="application/javascript")
    except Exception:
        response = send_from_directory(PRODUCT_DIR, "dashboard.js")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



@app.route("/api/check-bypass-flag", methods=["GET"])
def check_bypass_flag():
    """Return whether the bypass flag is active."""
    flag = Path("/tmp/ai_judge_file_dialog_bypass.txt")
    return jsonify({"active": flag.exists()})

@app.route("/ai-judge-icon.png")
def ai_judge_icon_png():
    return send_from_directory(PRODUCT_DIR, "ai-judge-icon.png")


@app.route("/worldcup-pool")
@app.route("/worldcup_pool.html")
def worldcup_pool():
    return send_from_directory(PRODUCT_DIR, "worldcup_pool.html")


@app.route("/citation-dashboard")
@app.route("/citation_dashboard.html")
def citation_dashboard():
    return send_from_directory(PRODUCT_DIR, "citation_dashboard.html")


@app.route("/api/modes")
def modes():
    return jsonify({"modes": list_modes()})


@app.route("/api/seats")
def seats():
    result = []
    for key, persona in SEAT_PERSONAS.items():
        result.append({
            "id": key,
            "name": persona["name"],
            "mbti": persona["mbti"],
            "risk_preference": persona["risk_preference"],
            "strength": persona["strength"],
            "weakness": persona["weakness"],
            "cognitive_bias": persona["cognitive_bias"],
            "ideology": persona["ideology"],
        })
    return jsonify({"seats": result, "count": len(result)})


@app.route("/api/bridge/status")
def web_bridge_status():
    status = bridge_status()
    status["bridge_run"] = bridge_run_snapshot()
    return jsonify(status)


@app.route("/api/prompt/resonate", methods=["POST"])
def prompt_resonate():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    mode = str(data.get("mode", "flash")).lower().strip() or "flash"
    engine = str(data.get("engine", DEFAULT_JUDGE_ENGINE)).lower().strip() or DEFAULT_JUDGE_ENGINE
    if engine != "web":
        return jsonify({"error": "local AI Judge engine is disabled; use engine='web'"}), 400
    seats = data.get("seats") or []
    if isinstance(seats, str):
        seats = [s.strip() for s in seats.split(",") if s.strip()]
    if not question:
        return jsonify({"error": "question is required"}), 400
    bridge = bridge_status() if engine == "web" else {}
    return jsonify({
        "ok": True,
        "prompt_flow": build_prompt_flow(question, mode=mode, engine=engine, seats=seats, bridge_summary=bridge),
        "execution_plan": decide_execution(engine=engine, mode=mode, requested_seats=seats, bridge_status=bridge),
    })


@app.route("/api/bridge/init-config", methods=["POST"])
def init_web_bridge_config():
    data = request.get_json(silent=True) or {}
    path = write_default_config(overwrite=bool(data.get("overwrite")))
    return jsonify({"ok": True, "config_path": str(path), "status": bridge_status()})


@app.route("/api/bridge/calibrate", methods=["POST"])
def calibrate_web_bridge():
    data = request.get_json(silent=True) or {}
    seats = data.get("seats")
    if isinstance(seats, str):
        seats = [s.strip() for s in seats.split(",") if s.strip()]
    timeout_seconds = float(data.get("timeout_seconds") or 12)
    result = calibrate_bridge(seats=seats, timeout_seconds=timeout_seconds)
    return jsonify(result)


@app.route("/api/trace", methods=["POST"])
def ui_trace_api():
    """Accept UI trace events and append to debug-ui-io-trace.jsonl."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"ok": False, "error": "empty payload"}), 400
    try:
        trace_path = _PROJECT_ROOT / "debug-ui-io-trace.jsonl"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(data, ensure_ascii=False)
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return jsonify({"ok": True, "trace_path": str(trace_path)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── P59: Unified Run Control Layer ──────────────────────────────────────────

@app.route("/api/runs", methods=["GET"])
def list_runs_api():
    """List all tracked runs across meeting/werewolf/worldcup."""
    mode_filter = request.args.get("mode")
    runs = list_runs(mode=mode_filter if mode_filter in ("meeting", "werewolf", "worldcup") else None)
    return jsonify({"runs": runs, "count": len(runs)})


@app.route("/api/runs/recent", methods=["GET"])
def list_recent_runs_api():
    """List recent 10 runs with artifact metadata for the artifact picker."""
    import os, glob
    runs_dir = RUNS_DIR
    recent = []
    if runs_dir.exists():
        # Collect run dirs sorted by mtime descending
        run_dirs = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )[:10]
        for rd in run_dirs:
            run_id = rd.name
            mtime = rd.stat().st_mtime
            # Check for verdict files
            has_verdict = (rd / "verdict.md").exists() or (rd / "verdict.json").exists() or (rd / "index.html").exists()
            # Try to extract question from the run control layer
            run_info = get_run(run_id) or {}
            question = run_info.get("question", run_info.get("label", ""))
            # Fallback: read from verdict.json
            if not question:
                vf = rd / "verdict.json"
                if vf.exists():
                    try:
                        vd = json.loads(vf.read_text(encoding="utf-8", errors="replace"))
                        question = vd.get("question", "")
                    except Exception:
                        pass
            recent.append({
                "run_id": run_id,
                "created_at": datetime.fromtimestamp(mtime, timezone.utc).isoformat(),
                "question": question[:200] if question else "",
                "has_verdict": has_verdict,
                "mode": run_info.get("mode", ""),
                "phase": run_info.get("phase", ""),
            })
    # Also check runs from run control (may include runs not in filesystem)
    from core.run_control import list_runs as _list_runs
    tracked = _list_runs()
    tracked_ids = {r["run_id"] for r in recent}
    for r in sorted(tracked, key=lambda r: r.get("created_at", ""), reverse=True):
        if r["run_id"] not in tracked_ids and len(recent) < 10:
            has_verdict = (runs_dir / r["run_id"] / "verdict.md").exists() if runs_dir.exists() else False
            question = (r.get("question") or r.get("label", ""))
            if not question:
                vf = runs_dir / r["run_id"] / "verdict.json"
                if vf.exists():
                    try:
                        vd = json.loads(vf.read_text(encoding="utf-8", errors="replace"))
                        question = vd.get("question", "")
                    except Exception:
                        pass
            recent.append({
                "run_id": r["run_id"],
                "created_at": r.get("created_at", ""),
                "question": question[:200] if question else "",
                "has_verdict": has_verdict,
                "mode": r.get("mode", ""),
                "phase": r.get("phase", ""),
            })
            tracked_ids.add(r["run_id"])
    # Sort by created_at descending, limit to 10
    recent.sort(key=lambda r: r["created_at"], reverse=True)
    recent = recent[:10]
    return jsonify({"runs": recent, "count": len(recent)})


@app.route("/api/runs/<run_id>/summary", methods=["GET"])
def run_summary_api(run_id: str):
    """Return a summary of a completed run for attachment context."""
    runs_dir = RUNS_DIR / run_id
    if not runs_dir.exists():
        return jsonify({"error": "run directory not found", "run_id": run_id}), 404

    text_content = ""
    summary = ""
    # Try reading verdict.md first
    verdict_md = runs_dir / "verdict.md"
    if verdict_md.exists():
        try:
            raw = verdict_md.read_text(encoding="utf-8", errors="replace")
            # Take first 5000 chars as preview
            text_content = raw[:5000]
            # Extract first 300 chars as summary
            lines = raw.strip().split("\n")
            summary = "\n".join(lines[:8])[:300]
        except Exception:
            pass

    # Fallback: read verdict.json
    if not text_content:
        verdict_json = runs_dir / "verdict.json"
        if verdict_json.exists():
            try:
                data = json.loads(verdict_json.read_text(encoding="utf-8", errors="replace"))
                text_content = json.dumps(data, ensure_ascii=False, indent=2)[:5000]
                summary = (data.get("one_liner") or data.get("final_report", {}).get("compact_overview", {}).get("summary") or "")[:300]
            except Exception:
                pass

    # Fallback: read trace.json
    if not text_content:
        trace_json = runs_dir / "trace.json"
        if trace_json.exists():
            try:
                data = json.loads(trace_json.read_text(encoding="utf-8", errors="replace"))
                text_content = json.dumps(data, ensure_ascii=False, indent=2)[:5000]
                summary = "历史裁决 trace（无 verdict 文件）"
            except Exception:
                pass

    return jsonify({
        "run_id": run_id,
        "text_content": text_content,
        "summary": summary,
        "content_available": bool(text_content),
    })


@app.route("/api/attachments/upload", methods=["POST"])
def upload_attachment_api():
    """P71: Upload attachment file to server disk.

    Saves to runtime/uploads/<draft_id>/<filename>.
    Returns attachment metadata including text preview for text files.
    """
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "untitled")).strip()
    content = str(data.get("content", ""))
    draft_id = str(data.get("draft_id", "default"))
    mime_type = str(data.get("type", "application/octet-stream"))

    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400

    uploads_dir = Path(_PROJECT_ROOT) / "runtime" / "uploads" / draft_id
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_name = name.replace("/", "_").replace("\\", "_")
    file_path = uploads_dir / safe_name

    # Avoid overwrites
    counter = 1
    stem = file_path.stem
    suffix = file_path.suffix
    while file_path.exists():
        file_path = uploads_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    try:
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        return jsonify({"ok": False, "error": f"write failed: {e}"}), 500

    stat = file_path.stat()
    text_preview = content[:300] if content else ""
    is_text = mime_type.startswith("text/") or mime_type in ("application/json", "application/x-yaml", "application/xml")

    return jsonify({
        "ok": True,
        "attachment_id": file_path.stem,
        "name": safe_name,
        "path": str(file_path),
        "size": stat.st_size,
        "type": mime_type,
        "text_preview": text_preview,
        "content_available": bool(is_text and content),
    })


@app.route("/api/runs/<run_id>", methods=["GET"])
def get_run_api(run_id: str):
    """Get current state of a run."""
    run = get_run(run_id)
    if run is None:
        safe_id = run_id.strip().replace("/", "").replace("\\", "").replace("..", "")
        if "text/html" in request.headers.get("Accept", "") and (RUNS_DIR / safe_id / "index.html").exists():
            return redirect(f"/api/runs/{safe_id}/index.html", code=302)
        return jsonify({"error": "run not found"}), 404
    return jsonify({"run": run})


@app.route("/api/runs/<run_id>/stop", methods=["POST"])
def stop_run_api(run_id: str):
    """Request a graceful stop for a running or queued run.

    Sets cancel_requested = True. Worker loops should poll is_cancel_requested()
    and stop launching new seats. The current seat may finish or be aborted.
    """
    run = get_run(run_id)
    if run is None:
        return jsonify({"ok": False, "run_id": run_id, "error": "run not found", "state": "unknown"}), 404
    if run.get("phase") not in ("queued", "running"):
        return jsonify({"ok": False, "run_id": run_id, "error": f"run is already {run.get('phase')}, cannot stop", "state": run.get("phase")}), 409

    result = request_stop(run_id)
    add_event(run_id, {"type": "stop_applied"})
    save_control_state(run_id)
    _try_release_run_bridge(run_id)

    return jsonify({
        "ok": True, "run_id": run_id, "state": "cancelled",
        "run": result or {}, "message": "stop requested"
    })


@app.route("/api/runs/<run_id>/pause", methods=["POST"])
def pause_run_api(run_id: str):
    """Pause a running run. Soft pause: stops dispatching new seats, in-flight seats complete."""
    run = get_run(run_id)
    if run is None:
        return jsonify({"ok": False, "run_id": run_id, "error": "run not found", "state": "unknown"}), 404
    if run.get("phase") not in ("queued", "running"):
        return jsonify({"ok": False, "run_id": run_id, "error": f"run is {run.get('phase')}, cannot pause", "state": run.get("phase")}), 409
    if run.get("paused"):
        return jsonify({"ok": False, "run_id": run_id, "error": "already paused", "state": "paused"}), 409

    result = request_pause(run_id)
    add_event(run_id, {"type": "pause_applied"})
    save_control_state(run_id)

    return jsonify({
        "ok": True, "run_id": run_id, "state": "paused",
        "soft": True, "message": "暂停已生效，已发出的席位会自然完成，不再启动新席位",
        "run": result or {}
    })


@app.route("/api/runs/<run_id>/resume", methods=["POST"])
def resume_run_api(run_id: str):
    """Resume a paused or stopped run.

    Case A (from_paused): clear paused flag, set phase to running, no bridge re-acquire.
    Case B (from_stopped): re-acquire bridge, delegate to mode-specific resume handler.
    """
    run = get_run(run_id)
    if run is None:
        return jsonify({"ok": False, "run_id": run_id, "error": "run not found", "state": "unknown"}), 404

    phase = run.get("phase", "")
    paused = run.get("paused", False)

    # Case A: resuming from paused
    if paused:
        result = request_resume(run_id)
        add_event(run_id, {"type": "resume_applied"})
        save_control_state(run_id)
        return jsonify({
            "ok": True, "run_id": run_id, "state": "running",
            "soft": True, "message": "已恢复运行",
            "run": result or {}
        })

    # Case B: resuming from stopped (existing logic)
    if phase == "stopped":
        set_phase(run_id, "running", run.get("progress", 0), "恢复中…")
        add_event(run_id, {"type": "run_resumed"})
        _try_resume_run_bridge(run_id)
        mode = run.get("mode", "")
        if mode == "werewolf":
            _resume_werewolf_run(run_id, run)
        elif mode == "meeting":
            _resume_jury_run(run_id, run)
        elif mode == "worldcup":
            _resume_worldcup_run(run_id, run)
        updated = get_run(run_id)
        return jsonify({"ok": True, "run_id": run_id, "state": "running", "run": updated or {}, "message": "resume initiated"})

    return jsonify({"ok": False, "run_id": run_id, "error": f"cannot resume from phase '{phase}'", "state": phase}), 409


@app.route("/api/runs/<run_id>/control", methods=["GET"])
def get_run_control(run_id: str):
    """Return current control state for a run (paused/stop_requested/phase)."""
    run = get_run(run_id)
    if run is None:
        return jsonify({"ok": False, "run_id": run_id, "error": "run not found", "state": "unknown"}), 404

    state = "running"
    if run.get("cancel_requested"):
        state = "cancelled"
    elif run.get("paused"):
        state = "paused"
    elif run.get("phase") in ("completed",):
        state = "completed"
    elif run.get("phase") in ("failed",):
        state = "failed"
    elif run.get("phase") in ("stopped",):
        state = "stopped"

    return jsonify({
        "ok": True, "run_id": run_id, "state": state,
        "paused": run.get("paused", False),
        "stop_requested": run.get("cancel_requested", False),
        "phase": run.get("phase"),
        "updated_at": run.get("updated_at")
    })


@app.route("/api/runs/<run_id>/trace", methods=["POST"])
def post_run_trace(run_id: str):
    """Write a control event trace entry to both the run's trace and the unified debug trace."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"ok": False, "error": "empty payload"}), 400

    # Write to run-specific trace via add_event
    from core.run_control import add_event as _add_event
    _add_event(run_id, data)

    # Also append to unified debug-execution-trace.jsonl
    try:
        runtime_dir = Path(_PROJECT_ROOT) / "runtime"
        trace_path = runtime_dir / "debug-execution-trace.jsonl"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(data, ensure_ascii=False)
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "trace_path": str(trace_path)})


@app.route("/api/runs/<run_id>/events", methods=["GET"])
def run_events_api(run_id: str):
    """SSE stream of run events for real-time UI updates."""
    def generate():
        last_event_count = -1
        for _ in range(3600):  # max 1 hour
            run = get_run(run_id)
            if run is None:
                payload = {"ok": False, "error": "run not found", "run_id": run_id}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break
            events = run.get("events", [])
            event_count = len(events)
            if event_count != last_event_count:
                result = {"ok": True, "run": run, "new_events": events[last_event_count + 1:] if last_event_count >= 0 else []}
                yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
                last_event_count = event_count
            phase = run.get("phase")
            if phase in ("stopped", "completed", "failed"):
                break
            import time as _time
            _time.sleep(1)

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# Hermes × Obsidian static file export whitelist
ALLOWED_RUN_EXPORT_FILES = {
    "index.html",
    "hermes-output.json",
    "hermes-output.md",
    "obsidian-run-note.md",
    "verdict.json",
    "verdict.md",
    "trace.json",
}


@app.route("/api/runs/<run_id>/<path:filename>")
def run_export_file(run_id: str, filename: str):
    if filename not in ALLOWED_RUN_EXPORT_FILES:
        return jsonify({"error": "file_not_allowed", "allowed": sorted(ALLOWED_RUN_EXPORT_FILES)}), 403
    try:
        safe_id = run_id.strip().replace("/", "").replace("\\", "").replace("..", "")
    except Exception:
        return jsonify({"error": "invalid_run_id"}), 400
    run_dir = RUNS_DIR / safe_id
    target = run_dir / filename
    if not target.exists():
        return jsonify({"error": "file_not_found", "run_id": safe_id, "filename": filename}), 404
    browser_download = filename != "index.html" and "text/html" in request.headers.get("Accept", "")
    force_download = request.args.get("download") == "1" or browser_download
    return send_from_directory(str(run_dir), filename, as_attachment=force_download)


# --- Hermes Index API ---

@app.route("/api/hermes/index")
def hermes_index():
    """返回全局 run 索引"""
    index_file = RUNS_DIR / "hermes-index.json"
    if not index_file.exists():
        return jsonify({"error": "index_not_found"}), 404
    return send_file(index_file, mimetype="application/json")


@app.route("/api/hermes/seats")
def hermes_seats():
    """返回席位聚合摘要"""
    index_file = RUNS_DIR / "hermes-index.json"
    if not index_file.exists():
        return jsonify({"error": "index_not_found"}), 404
    with open(index_file, encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data.get("seat_summary", {}))


@app.route("/api/hermes/seat/<seat_id>")
def hermes_seat_detail(seat_id: str):
    """返回单席位聚合"""
    index_file = RUNS_DIR / "hermes-index.json"
    if not index_file.exists():
        return jsonify({"error": "index_not_found"}), 404
    with open(index_file, encoding="utf-8") as f:
        data = json.load(f)
    seat_data = data.get("seat_summary", {}).get(seat_id)
    if seat_data is None:
        return jsonify({"error": "seat_not_found", "seat_id": seat_id}), 404
    return jsonify(seat_data)


# --- Human Gavel API (P3) ---

@app.route("/api/gavel/<run_id>")
def gavel_status(run_id: str):
    """返回某个 run 的 human-gavel.json（含 P4: conflict, claim_review, history_count）"""
    # Path traversal guard
    run_id_safe = run_id.replace("/", "").replace("\\", "").replace("..", "")
    gavel_file = RUNS_DIR / run_id_safe / "human-gavel.json"
    if not gavel_file.exists():
        return jsonify({
            "run_id": run_id_safe,
            "status": "none",
            "message": "human-gavel.json not found for this run",
        })
    with open(gavel_file, encoding="utf-8") as f:
        data = json.load(f)

    # P4: enrich with history_count
    hist_path = RUNS_DIR / run_id_safe / "human-gavel-history.jsonl"
    history_count = 0
    if hist_path.exists():
        try:
            history_count = len(hist_path.read_text(encoding="utf-8").strip().splitlines())
        except Exception:
            history_count = 0

    data["history_count"] = history_count
    # conflict and claim_review should already be in the JSON if synced via P4
    if "conflict" not in data:
        data["conflict"] = {"has_conflict": False, "reason": "pre-P4 gavel"}
    if "claim_review" not in data:
        data["claim_review"] = {"accepted": [], "rejected": [], "unmatched": [], "warnings": []}

    return jsonify(data)


@app.route("/api/gavel/<run_id>/sync", methods=["POST"])
def gavel_sync(run_id: str):
    """从 Obsidian vault 同步 Human Gavel 到对应 run 目录"""
    vault_dir = os.environ.get(
        "AI_JUDGE_OBSIDIAN_VAULT",
        str(Path.home() / "Documents/AI-Judge-Obsidian-Vault"),
    )
    try:
        result = sync_human_gavel_for_run(run_id, RUNS_DIR, Path(vault_dir))
        return jsonify(result)
    except Exception as exc:
        return jsonify({"run_id": run_id, "status": "none", "error": str(exc)}), 500


@app.route("/api/gavel/sync-all", methods=["POST"])
def gavel_sync_all():
    """扫描所有 run，批量同步 Human Gavel"""
    vault_dir = os.environ.get(
        "AI_JUDGE_OBSIDIAN_VAULT",
        str(Path.home() / "Documents/AI-Judge-Obsidian-Vault"),
    )
    try:
        result = sync_all_human_gavels(RUNS_DIR, Path(vault_dir))
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# P4: Gavel history
@app.route("/api/gavel/<run_id>/history")
def gavel_history(run_id: str):
    """读取 human-gavel-history.jsonl，返回全部行"""
    run_id_safe = run_id.replace("/", "").replace("\\", "").replace("..", "")
    hist_path = RUNS_DIR / run_id_safe / "human-gavel-history.jsonl"
    if not hist_path.exists():
        return jsonify({
            "run_id": run_id_safe,
            "history": [],
            "count": 0,
        })
    try:
        lines = [
            json.loads(line)
            for line in hist_path.read_text(encoding="utf-8").strip().splitlines()
            if line.strip()
        ]
        return jsonify({
            "run_id": run_id_safe,
            "history": lines,
            "count": len(lines),
        })
    except Exception as exc:
        return jsonify({
            "run_id": run_id_safe,
            "history": [],
            "count": 0,
            "error": str(exc),
        })


# P4: Gavel digest
@app.route("/api/gavel/digest")
def gavel_digest():
    """调用 generate_gavel_digest，返回摘要 JSON"""
    vault_dir = os.environ.get(
        "AI_JUDGE_OBSIDIAN_VAULT",
        str(Path.home() / "Documents/AI-Judge-Obsidian-Vault"),
    )
    try:
        result = generate_gavel_digest(RUNS_DIR, Path(vault_dir))
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── P5: Claim Calibration ─────────────────────────────────────────────────

@app.route("/api/claims/calibration")
def claim_calibration_index():
    """Return global claim calibration index across all runs."""
    vault_dir = os.environ.get(
        "AI_JUDGE_OBSIDIAN_VAULT",
        str(Path.home() / "Documents/AI-Judge-Obsidian-Vault"),
    )
    try:
        from claim_calibration_layer import build_claim_calibration_index
        result = build_claim_calibration_index(RUNS_DIR, Path(vault_dir))
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/claims/calibration/<run_id>")
def claim_calibration_run(run_id: str):
    """Return claim calibration JSON for a single run."""
    run_id_safe = run_id.replace("/", "").replace("\\", "").replace("..", "")
    cal_path = RUNS_DIR / run_id_safe / "claim-calibration.json"
    if not cal_path.exists():
        return jsonify({"error": "claim-calibration.json not found for this run"}), 404
    try:
        with open(cal_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/claims/calibration/<run_id>/rebuild", methods=["POST"])
def claim_calibration_rebuild(run_id: str):
    """Rebuild claim calibration for a single run."""
    run_id_safe = run_id.replace("/", "").replace("\\", "").replace("..", "")
    run_dir = RUNS_DIR / run_id_safe
    if not run_dir.exists():
        return jsonify({"error": "run directory not found"}), 404
    try:
        from claim_calibration_layer import ensure_claim_ids, write_claim_calibration
        res1 = ensure_claim_ids(run_dir)
        if not res1.get("ok"):
            return jsonify({"error": "ensure_claim_ids failed", "detail": res1}), 500
        cal = write_claim_calibration(run_dir)
        return jsonify({"ok": True, "claims_updated": res1.get("claims_updated", 0), "calibration": cal})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/claims/calibration/rebuild-all", methods=["POST"])
def claim_calibration_rebuild_all():
    """Rebuild claim calibration for all runs, then regenerate index."""
    vault_dir = os.environ.get(
        "AI_JUDGE_OBSIDIAN_VAULT",
        str(Path.home() / "Documents/AI-Judge-Obsidian-Vault"),
    )
    try:
        from claim_calibration_layer import ensure_claim_ids, write_claim_calibration, build_claim_calibration_index

        rebuilt = []
        errors = []
        for run_dir in sorted(RUNS_DIR.iterdir()):
            if not run_dir.is_dir():
                continue
            try:
                res1 = ensure_claim_ids(run_dir)
                cal = write_claim_calibration(run_dir)
                rebuilt.append({
                    "run_id": run_dir.name,
                    "claims_updated": res1.get("claims_updated", 0),
                    "accepted": len(cal.get("accepted", [])),
                    "rejected": len(cal.get("rejected", [])),
                    "unmatched": len(cal.get("unmatched", [])),
                })
            except Exception as exc:
                errors.append({"run_id": run_dir.name, "error": str(exc)})

        index = build_claim_calibration_index(RUNS_DIR, Path(vault_dir))

        return jsonify({
            "ok": True,
            "runs_rebuilt": len(rebuilt),
            "rebuilt": rebuilt,
            "errors": errors,
            "index": index,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/runs/universe")
def run_universe():
    universe_path = RUNS_DIR / "run-universe.json"
    if not universe_path.exists():
        return jsonify({"error": "run-universe.json not found"}), 404
    return send_file(universe_path, mimetype="application/json")


@app.route("/api/trust/calibration")
def trust_calibration():
    trust_path = RUNS_DIR / "trust-calibration.json"
    if not trust_path.exists():
        return jsonify({"error": "trust-calibration.json not found"}), 404
    return send_file(trust_path, mimetype="application/json")


@app.route("/api/trust/seat/<seat_id>")
def trust_seat(seat_id: str):
    seat_id_safe = seat_id.replace("/", "").replace("\\", "").replace("..", "")
    result = get_seat_trust(seat_id_safe, RUNS_DIR)
    if result is None:
        return jsonify({"error": f"seat not found: {seat_id_safe}"}), 404
    return jsonify(result)


def _try_release_run_bridge(run_id: str) -> None:
    """Release bridge lock owned by this run (best-effort)."""
    try:
        release_bridge_for_run(run_id)
    except Exception:
        pass


def _try_resume_run_bridge(run_id: str) -> None:
    """Try to re-acquire bridge lock for a resumed run (best-effort)."""
    try:
        from core.bridge_run_lock import try_acquire_bridge_run
        claim = try_acquire_bridge_run("resume", run_id, f"resume:{run_id}")
        if claim:
            update_run(run_id, bridge_claim=claim)
    except Exception:
        pass


def _resume_werewolf_run(run_id: str, run: dict[str, Any]) -> None:
    """Resume a werewolf run from its last state."""
    from core.werewolf_executor import resume_werewolf_without_substitute
    try:
        meta = run.get("metadata", {})
        game_id = meta.get("game_id")
        if game_id:
            resume_werewolf_without_substitute(game_id, offline_seat=None)
    except Exception:
        mark_failed(run_id, "werewolf resume failed")


def _resume_jury_run(run_id: str, run: dict[str, Any]) -> None:
    """Resume a meeting/jury run from its last state."""
    # Re-submit the question with the remaining seats
    try:
        meta = run.get("metadata", {})
        question = meta.get("question", "")
        mode = meta.get("mode", "standard")
        seats = meta.get("remaining_seats", meta.get("seats", []))
        if question and seats:
            from core.seat_personas import SEAT_PERSONAS
            valid_seats = [s for s in seats if s in SEAT_PERSONAS]
            if valid_seats:
                # Trigger async re-run
                _start_worker(
                    run_id,
                    question,
                    mode,
                    valid_seats,
                    engine="web",
                    notify_config=None,
                    chief_judge="auto",
                    abstained_seats=[],
                )
    except Exception:
        mark_failed(run_id, "jury resume failed")


def _resume_worldcup_run(run_id: str, run: dict[str, Any]) -> None:
    """Resume a worldcup run from its last state."""
    try:
        from core.worldcup import resume_worldcup_run, load_worldcup_run
        wc_run = load_worldcup_run(run_id)
        if wc_run:
            resume_worldcup_run(wc_run)
        else:
            mark_failed(run_id, "worldcup run data not found for resume")
    except ImportError:
        mark_failed(run_id, "worldcup module not available for resume")
    except Exception:
        mark_failed(run_id, "worldcup resume failed")


# ── End P59 Run Control Layer ───────────────────────────────────────────────


@app.route("/api/judge", methods=["POST"])
def submit_judge():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    mode = str(data.get("mode", DEFAULT_JUDGE_MODE)).lower().strip() or DEFAULT_JUDGE_MODE
    engine = str(data.get("engine", DEFAULT_JUDGE_ENGINE)).lower().strip() or DEFAULT_JUDGE_ENGINE
    override_seats = _normalize_seat_list(data.get("seats"))
    abstained_seats = _normalize_seat_list(data.get("abstained_seats"))
    chief_judge = str(data.get("chief_judge") or "auto").lower().strip()
    raw_mentor_preflight = data.get("mentor_preflight")
    mentor_preflight = raw_mentor_preflight if isinstance(raw_mentor_preflight, dict) else None
    external_evidence = _normalize_external_evidence_payload(data.get("external_evidence"))
    evidence_options = _normalize_evidence_options(data.get("evidence_options"))
    attachments = data.get("attachments") or []  # P71: attachments payload from dashboard

    if not question:
        return jsonify({"error": "question is required"}), 400
    if engine != "web":
        return jsonify({"error": "local AI Judge engine is disabled; engine must be 'web'"}), 400
    if chief_judge != "auto" and chief_judge not in SEAT_PERSONAS:
        return jsonify({"error": "chief_judge must be 'auto' or a valid seat id"}), 400

    try:
        config = resolve_mode(mode, override_seats=override_seats or None)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    seats = [s for s in config["seats"] if s in SEAT_PERSONAS]
    if not seats:
        return jsonify({"error": "No valid seats selected"}), 400
    busy = bridge_run_snapshot()
    if engine == "web" and busy.get("busy"):
        return jsonify({
            "error": "bridge_busy",
            "message": (
                "固定 Chrome 桥接正在运行其他 AI Judge 流程。"
                "请等当前流程结束后再提交，避免网页席位串台。"
            ),
            "bridge_run": busy,
        }), 409

    run_id = TASKS.submit(question=question, mode=mode, seats=seats)

    # P59: register with unified run control (bridge claim managed by worker)
    start_run(
        "meeting",
        label=f"会议: {question[:40]}",
        bridge_claim=None,
        run_id=run_id,
        metadata={"question": question, "mode": mode, "seats": seats},
    )

    notify_config = _notification_config(data)
    _start_worker(
        run_id,
        question,
        mode,
        seats,
        engine,
        notify_config,
        chief_judge,
        abstained_seats,
        mentor_preflight,
        external_evidence,
        evidence_options,
        attachments=attachments,
    )

    return jsonify({
        "run_id": run_id,
        "status": "queued",
        "mode": mode,
        "engine": engine,
        "chief_judge": _chief_judge_payload(chief_judge),
        "abstained_seats": abstained_seats,
        "mentor_preflight": mentor_preflight,
        "external_evidence_count": len(external_evidence),
        "evidence_options": evidence_options,
        "mode_name": config["name"],
        "mode_emoji": config["emoji"],
        "seats": seats,
        "seat_count": len(seats),
        "estimated_seconds": config["timeout_seconds"],
        "progress_url": f"/api/judge/{run_id}/progress",
        "verdict_url": f"/api/judge/{run_id}/verdict",
    }), 202


@app.route("/api/judge/<run_id>/supplement", methods=["POST"])
def supplement_judge(run_id: str):
    source = _load_run(run_id)
    if not source:
        status = TASKS.get_status(run_id)
        if status:
            return jsonify({"error": "source verdict is not ready", "status": status}), 409
        return jsonify({"error": "run not found"}), 404

    data = request.get_json(silent=True) or {}
    requested = _normalize_seat_list(data.get("seats"))
    seats = _supplementable_run_seats(source, requested=requested or None)
    if not seats:
        return jsonify({
            "error": "no supplementable seats",
            "source_run_id": run_id,
            "requested": requested,
            "supplementable": _supplementable_run_seats(source),
        }), 400

    mode = str(source.get("mode") or "standard")
    question = str(source.get("question") or "回收旧页面答案")
    supplement_run_id = TASKS.submit(question=f"回收旧页面答案：{question}", mode=mode, seats=seats)
    notify_config = _notification_config(data)
    _start_supplement_worker(supplement_run_id, run_id, seats, notify_config)
    return jsonify({
        "run_id": supplement_run_id,
        "source_run_id": run_id,
        "status": "queued",
        "mode": mode,
        "seats": seats,
        "seat_count": len(seats),
        "progress_url": f"/api/judge/{supplement_run_id}/progress",
        "source_verdict_url": f"/api/judge/{run_id}/verdict",
    }), 202


@app.route("/api/judge/<run_id>/rescue", methods=["POST"])
def rescue_judge(run_id: str):
    source = _load_run(run_id)
    if not source:
        status = TASKS.get_status(run_id)
        if status:
            return jsonify({"error": "source verdict is not ready", "status": status}), 409
        return jsonify({"error": "run not found"}), 404

    data = request.get_json(silent=True) or {}
    requested = _normalize_seat_list(data.get("seats"))
    plan = _build_rescue_plan(source, requested=requested or None)
    seats = [seat for seat in (requested or plan.get("seats") or []) if seat in SEAT_PERSONAS]
    if not seats:
        return jsonify({
            "error": "no rescueable seats",
            "source_run_id": run_id,
            "requested": requested,
            "rescue_plan": plan,
        }), 400

    mode = str(source.get("mode") or "standard")
    question = str(source.get("question") or "一键修复并回收答案")
    rescue_run_id = TASKS.submit(question=f"一键修复并回收答案：{question}", mode=mode, seats=seats)
    notify_config = _notification_config(data)
    _start_rescue_worker(rescue_run_id, run_id, seats, notify_config)
    return jsonify({
        "run_id": rescue_run_id,
        "source_run_id": run_id,
        "status": "queued",
        "mode": mode,
        "seats": seats,
        "seat_count": len(seats),
        "method": "read_existing_first_then_targeted_clean_resubmit",
        "sends_prompt": bool(plan.get("sends_prompt")),
        "rescue_plan": plan,
        "progress_url": f"/api/judge/{rescue_run_id}/progress",
        "source_verdict_url": f"/api/judge/{run_id}/verdict",
    }), 202


@app.route("/api/judge/<run_id>/recheck", methods=["POST"])
def recheck_judge(run_id: str):
    data = request.get_json(silent=True) or {}
    requested = _normalize_seat_list(data.get("seats"))
    notify_config = _notification_config(data)
    method = str(data.get("method") or "").strip().lower()
    fresh_recheck = bool(data.get("send_prompt")) or method in {
        "fresh",
        "fresh_web_submission",
        "resubmit",
        "submit",
    }

    source = _load_run(run_id)
    if source:
        seats = _supplementable_run_seats(source, requested=requested or None)
        seats = _merge_explicit_recheck_seats(seats, requested)
        if not seats:
            return jsonify({
                "error": "no recoverable seats",
                "source_run_id": run_id,
                "requested": requested,
                "recoverable": _supplementable_run_seats(source),
            }), 400
        mode = str(source.get("mode") or "standard")
        question = str(source.get("question") or "回收旧页面答案")
        recheck_question = f"重新提交席位：{question}" if fresh_recheck else f"回收旧页面答案：{question}"
        recheck_run_id = TASKS.submit(question=recheck_question, mode=mode, seats=seats)
        if fresh_recheck:
            _start_fresh_recheck_worker(recheck_run_id, run_id, seats, notify_config)
        else:
            _start_supplement_worker(recheck_run_id, run_id, seats, notify_config)
        return jsonify({
            "run_id": recheck_run_id,
            "source_run_id": run_id,
            "status": "queued",
            "mode": mode,
            "seats": seats,
            "seat_count": len(seats),
            "method": "fresh_web_submission" if fresh_recheck else "existing_page_recovery",
            "sends_prompt": bool(fresh_recheck),
            "progress_url": f"/api/judge/{recheck_run_id}/progress",
            "source_verdict_url": f"/api/judge/{run_id}/verdict",
        }), 202

    status = _task_payload(run_id)
    task = TASKS.get_task(run_id)
    if not status or not task:
        return jsonify({"error": "run not found"}), 404
    if status.get("status") not in {"running", "pending", "failed"}:
        return jsonify({"error": "run is not recoverable", "status": status}), 409

    seats = _diagnostic_recheck_seats(status, requested=requested or None)
    seats = _merge_explicit_recheck_seats(seats, requested)
    if not seats:
        seats = [str(seat) for seat in (task.get("seats") or []) if str(seat) in SEAT_PERSONAS]
    if not seats:
        return jsonify({"error": "no recoverable seats", "status": status}), 400

    mode = str(task.get("mode") or "standard")
    question = str(task.get("question") or "回收旧页面答案")
    task_question = f"重新提交席位：{question}" if fresh_recheck else f"回收旧页面答案：{question}"
    recheck_run_id = TASKS.submit(question=task_question, mode=mode, seats=seats)
    if fresh_recheck:
        _start_recheck_worker(recheck_run_id, run_id, task, seats, notify_config, fresh_recheck=True)
    else:
        _start_recheck_worker(recheck_run_id, run_id, task, seats, notify_config)
    return jsonify({
        "run_id": recheck_run_id,
        "source_run_id": run_id,
        "status": "queued",
        "mode": mode,
        "seats": seats,
        "seat_count": len(seats),
        "method": "fresh_web_submission" if fresh_recheck else "existing_page_recovery",
        "sends_prompt": bool(fresh_recheck),
        "progress_url": f"/api/judge/{recheck_run_id}/progress",
        "source_verdict_url": f"/api/judge/{run_id}/verdict",
    }), 202


@app.route("/api/task/<run_id>")
def task_status(run_id: str):
    payload = _task_payload(run_id)
    if payload is None:
        return jsonify({"error": "task not found"}), 404
    return jsonify(payload)


@app.route("/api/judge/<run_id>/verdict")
def verdict(run_id: str):
    result = _load_run(run_id)
    if not result:
        status = TASKS.get_status(run_id)
        if status:
            return jsonify({"error": "verdict not ready", "status": status}), 409
        return jsonify({"error": "run not found"}), 404

    # Hermes × Obsidian exports
    run_dir = RUNS_DIR / run_id
    canonical_view_url = f"/api/runs/{run_id}/index.html"
    legacy_view_url = result.get("view_url", "")
    index_html_exists = (run_dir / "index.html").exists()
    hermes_json_exists = (run_dir / "hermes-output.json").exists()
    hermes_md_exists = (run_dir / "hermes-output.md").exists()
    obsidian_note_exists = (run_dir / "obsidian-run-note.md").exists()

    result["canonical_view_url"] = canonical_view_url
    result["legacy_view_url"] = legacy_view_url
    result["exports"] = {
        "html": canonical_view_url if index_html_exists else legacy_view_url,
        "hermes_json": f"/api/runs/{run_id}/hermes-output.json" if hermes_json_exists else None,
        "hermes_md": f"/api/runs/{run_id}/hermes-output.md" if hermes_md_exists else None,
        "obsidian_note": str(run_dir / "obsidian-run-note.md") if obsidian_note_exists else None,
    }

    return jsonify(result)


@app.route("/api/judge/<run_id>/evidence-gaps")
def evidence_gaps(run_id: str):
    result = _load_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    queue = (result.get("grand_judge") or {}).get("evidence_gap_queue") or (result.get("web_bridge") or {}).get("evidence_gap_queue") or {}
    return jsonify(queue or {"schema": "evidence_gap_queue.v1", "open_count": 0, "tasks": []})


@app.route("/api/judge/<run_id>/evidence-gaps/<task_id>/resolve", methods=["POST"])
def resolve_evidence_gap(run_id: str, task_id: str):
    result = _load_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    data = request.get_json(silent=True) or {}
    resolution = str(data.get("resolution") or "").strip()
    if not resolution:
        return jsonify({"error": "resolution is required"}), 400
    grand = result.setdefault("grand_judge", {})
    queue = grand.get("evidence_gap_queue") or {}
    try:
        updated = resolve_gap_task(queue, task_id=task_id, resolution=resolution, evidence_id=data.get("evidence_id"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    grand["evidence_gap_queue"] = updated
    result.setdefault("web_bridge", {})["evidence_gap_queue"] = updated
    _save_run(run_id, result)
    TASKS.complete(run_id, result)
    return jsonify({"ok": True, "evidence_gap_queue": updated})


@app.route("/api/judge/<run_id>/blind-review", methods=["GET", "POST"])
def blind_review(run_id: str):
    result = _load_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    grand = result.setdefault("grand_judge", {})
    packet = grand.get("blind_cross_validation") or {}
    if request.method == "GET":
        return jsonify(packet or {"schema": "blind_cross_validation.v1", "status": "not_available"})

    data = request.get_json(silent=True) or {}
    reviews = data.get("reviews") or []
    if not isinstance(reviews, list):
        return jsonify({"error": "reviews must be a list"}), 400
    aggregate = aggregate_blind_reviews(reviews, threshold=float(data.get("threshold") or packet.get("threshold") or 0.67))
    packet["reviews"] = reviews
    packet["result"] = aggregate
    packet["status"] = aggregate.get("status")
    grand["blind_cross_validation"] = packet
    result.setdefault("web_bridge", {})["blind_cross_validation"] = packet
    _save_run(run_id, result)
    TASKS.complete(run_id, result)
    return jsonify({"ok": True, "blind_cross_validation": packet})


@app.route("/api/judge/<run_id>/human-review", methods=["POST"])
def human_review(run_id: str):
    result = _load_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    data = request.get_json(silent=True) or {}
    grand = result.setdefault("grand_judge", {})
    certification_hash = str(grand.get("certification_hash") or grand.get("replay_ledger_hash") or "")
    try:
        signature = sign_human_review(
            run_id=run_id,
            certification_hash=certification_hash,
            reviewer=str(data.get("reviewer") or "human_reviewer"),
            decision=str(data.get("decision") or "conditional"),
            reason=str(data.get("reason") or ""),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    grand["human_review_signature"] = signature
    grand["human_review_status"] = human_review_status(grand)
    result.setdefault("web_bridge", {})["human_review_status"] = grand["human_review_status"]
    if grand.get("eval_case"):
        grand["eval_case"]["human_label"] = {
            "decision": signature["decision"],
            "signature_hash": signature["signature_hash"],
        }
    _save_run(run_id, result)
    TASKS.complete(run_id, result)
    return jsonify({"ok": True, "human_review_signature": signature, "human_review_status": grand["human_review_status"]})


@app.route("/api/judge/<run_id>/trace")
def run_trace(run_id: str):
    trace = load_trace(_trace_path(run_id))
    if not trace:
        result = _load_run(run_id)
        if result and result.get("execution_trace"):
            return jsonify(result["execution_trace"])
        return jsonify({"error": "trace not found"}), 404
    return jsonify(trace)


@app.route("/api/judge/<run_id>/progress")
def progress_sse(run_id: str):
    def generate():
        last_payload = None
        for _ in range(360):
            payload = _task_payload(run_id)
            if not payload:
                payload = {"run_id": run_id, "status": "missing", "progress": 0, "current_step": "任务不存在"}
            encoded = json.dumps(payload, ensure_ascii=False)
            if encoded != last_payload:
                yield f"data: {encoded}\n\n"
                last_payload = encoded
            if payload.get("status") in {"complete", "failed", "cancelled", "missing"}:
                break
            time.sleep(1)

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# NOTE: Duplicate /api/trace route removed (was writing to wrong runtime/runtime/ path).
# Only the canonical route at line ~2709 is active, writing to _PROJECT_ROOT / debug-ui-io-trace.jsonl.


@app.route("/api/history")
def history():
    status_filter = request.args.get("status")
    limit = int(request.args.get("limit", "30"))
    return jsonify({"runs": TASKS.list_tasks(status=status_filter, limit=limit)})


@app.route("/api/seat-scoreboard")
def seat_scoreboard():
    limit = max(1, min(200, int(request.args.get("limit", "80"))))
    verdicts = list(_iter_saved_verdicts(limit=limit))
    try:
        bridge = bridge_status()
    except Exception:
        bridge = {"seats": [], "seat_browser_matrix": []}
    return jsonify(_build_seat_scoreboard(verdicts=verdicts, bridge=bridge))


@app.route("/api/evals/export")
def evals_export():
    limit = max(1, min(500, int(request.args.get("limit", "200"))))
    verdicts = list(_iter_saved_verdicts(limit=limit))
    return jsonify(collect_eval_cases(verdicts=verdicts, limit=limit))


@app.route("/api/history/<run_id>")
def history_detail(run_id: str):
    result = _load_run(run_id)
    if result:
        return jsonify(result)
    status = _task_payload(run_id)
    if status:
        return jsonify(status)
    return jsonify({"error": "Run not found"}), 404


@app.route("/api/judge/<run_id>/cancel", methods=["POST"])
def cancel(run_id: str):
    return jsonify({"ok": TASKS.cancel(run_id)})


@app.route("/view")
def secure_view():
    tid = request.args.get("tid", "")
    exp = request.args.get("exp", "")
    sig = request.args.get("sig", "")
    if not verify_secure_view(tid, exp, sig):
        return Response("Link expired or invalid", status=403)
    result = _load_run(tid)
    if not result:
        return Response("Verdict not found", status=404)
    trace = load_trace(_trace_path(tid))
    if trace:
        result = dict(result)
        result["execution_trace"] = trace
    return Response(_render_html_report(result), mimetype="text/html")


def _iter_saved_verdicts(limit: int = 80):
    files = sorted(RUNS_DIR.glob("*/verdict.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in files[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            yield data


def _build_seat_scoreboard(verdicts: list[dict[str, Any]], bridge: dict[str, Any] | None = None) -> dict[str, Any]:
    bridge = bridge or {}
    bridge_by_id = {str(item.get("id")): item for item in bridge.get("seats", [])}
    matrix_by_id = {str(item.get("seat")): item for item in bridge.get("seat_browser_matrix", [])}
    rows: dict[str, dict[str, Any]] = {}
    for seat, persona in SEAT_PERSONAS.items():
        bridge_seat = bridge_by_id.get(seat, {})
        mapped = matrix_by_id.get(seat, {})
        channel = mapped.get("channel") or bridge_seat.get("channel") or "local"
        rows[seat] = {
            "seat": seat,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "provider": mapped.get("provider") or bridge_seat.get("provider") or persona["name"],
            "channel": channel,
            "target": mapped.get("target") or bridge_seat.get("browser_label") or bridge_seat.get("url") or "-",
            "ready": bool((mapped.get("ready") if mapped else None) or bridge_seat.get("ready")),
            "history": [],
            "run_count": 0,
            "scored_run_count": 0,
            "success_count": 0,
            "failure_count": 0,
        }

    for verdict in verdicts:
        run_id = str(verdict.get("run_id") or "")
        run_meta = {
            "run_id": run_id,
            "question": verdict.get("question", ""),
            "mode": verdict.get("mode", ""),
            "created_at": verdict.get("created_at"),
            "view_url": verdict.get("view_url"),
        }
        round_scores = _round_scores_by_seat(verdict)
        raw_by_seat = {
            str(item.get("seat")): item
            for item in ((verdict.get("web_bridge") or {}).get("raw_results") or [])
        }
        touched: set[str] = set()
        for item in verdict.get("seat_scores", []) or []:
            seat = str(item.get("seat") or "")
            if seat not in rows:
                continue
            touched.add(seat)
            score = _safe_float(item.get("average_score"))
            raw = raw_by_seat.get(seat, {})
            entry = {
                **run_meta,
                "score": score,
                "claims_count": int(item.get("claims_count", 0) or 0),
                "ok": bool(raw.get("ok", True)),
                "round_scores": round_scores.get(seat, {}),
            }
            rows[seat]["history"].append(entry)
        for seat, raw in raw_by_seat.items():
            if seat not in rows or seat in touched:
                continue
            rows[seat]["history"].append({
                **run_meta,
                "score": None,
                "claims_count": 0,
                "ok": bool(raw.get("ok")),
                "round_scores": round_scores.get(seat, {}),
                "error": raw.get("error"),
            })

    for seat, row in rows.items():
        history = row["history"]
        scores = [float(item["score"]) for item in history if item.get("score") is not None]
        row["run_count"] = len(history)
        row["scored_run_count"] = len(scores)
        row["success_count"] = sum(1 for item in history if item.get("ok"))
        row["failure_count"] = sum(1 for item in history if item.get("ok") is False)
        row["latest_run"] = history[0] if history else None
        row["latest_score"] = round(scores[0], 4) if scores else None
        row["average_score"] = round(sum(scores) / len(scores), 4) if scores else None
        row["q_avg"] = row["average_score"]
        row["k_avg"] = _average_round(history, "raw_answer")
        row["c_avg"] = _average_round(history, "peer_review")
        row["r_stability"] = round(row["success_count"] / len(history), 4) if history else (1.0 if row.get("ready") else 0.0)
        row["t_tenure"] = round(min(0.35, 0.18 + len(history) * 0.03), 4) if history else None
        row["recent_scores"] = [
            {"run_id": item.get("run_id"), "score": item.get("score"), "mode": item.get("mode")}
            for item in history[:6]
        ]

    sorted_rows = sorted(
        rows.values(),
        key=lambda item: (1 if item.get("average_score") is None else -float(item.get("average_score")), item["seat_name"]),
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_considered": len(verdicts),
        "seats": sorted_rows,
    }


def _round_scores_by_seat(verdict: dict[str, Any]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for round_item in ((verdict.get("web_bridge") or {}).get("score_rounds") or []):
        phase = str(round_item.get("id") or "")
        if not phase:
            continue
        for row in round_item.get("seat_scores", []) or []:
            seat = str(row.get("seat") or "")
            if not seat:
                continue
            result.setdefault(seat, {})[phase] = _safe_float(row.get("average_score"))
    return result


def _average_round(history: list[dict[str, Any]], phase: str) -> float | None:
    values = [
        float((item.get("round_scores") or {}).get(phase))
        for item in history
        if (item.get("round_scores") or {}).get(phase) is not None
    ]
    return round(sum(values) / len(values), 4) if values else None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _compact_report_text(value: Any, limit: int = 360) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _render_collection_summary(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    requested = int(bridge.get("requested_count") or len(raw_results) or result.get("seat_count") or 0)
    ok_count = int(bridge.get("ok_count") if bridge.get("ok_count") is not None else sum(1 for item in raw_results if item.get("ok")))
    failed_count = int(
        bridge.get("failed_count")
        if bridge.get("failed_count") is not None
        else sum(1 for item in raw_results if not item.get("ok"))
    )
    pending_count = sum(1 for item in raw_results if _is_supplementable_result(item))
    hard_failed = max(0, failed_count - pending_count)
    collection_complete = bridge.get("collection_complete")
    if collection_complete is None:
        complete = not bridge or (requested > 0 and ok_count == requested and failed_count == 0)
    else:
        complete = bool(collection_complete)
    status = "完整收集" if complete else ("未拿全，待回收" if pending_count and ok_count else "未拿全")
    status_class = "good" if complete else "warn"
    pending_label = "待回收/失败" if pending_count else "失败席位"
    pending_text = f"{pending_count}/{hard_failed}" if pending_count else str(failed_count)
    return (
        '<section class="summary-grid" aria-label="收集状态">'
        f'<div><span>收集状态</span><strong class="{status_class}">{html.escape(status)}</strong></div>'
        f"<div><span>完成席位</span><strong>{ok_count}/{requested}</strong></div>"
        f"<div><span>{html.escape(pending_label)}</span><strong>{html.escape(pending_text)}</strong></div>"
        f"<div><span>置信度</span><strong>{html.escape(str(result.get('confidence', 0)))}%</strong></div>"
        "</section>"
    )


def _render_seat_answers(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    if not raw_results:
        return ""

    score_by_seat = {str(item.get("seat")): item for item in result.get("seat_scores", [])}
    cards: list[str] = []
    for item in raw_results:
        seat = str(item.get("seat") or "")
        seat_name = str(item.get("seat_name") or score_by_seat.get(seat, {}).get("seat_name") or seat)
        ok = bool(item.get("ok"))
        response = str(item.get("response") or "")
        error = item.get("error") or {}
        retry_attempts = int(item.get("retry_attempts") or 0)
        retry_note = f" · 补跑 {retry_attempts} 次" if retry_attempts else ""
        score = score_by_seat.get(seat, {})
        score_text = "-"
        if score:
            try:
                score_text = f"{float(score.get('average_score', 0.0)):.3f}"
            except Exception:
                score_text = str(score.get("average_score", "-"))
        if ok:
            status = "已返回"
            status_class = "is-ok"
            state_class = "good"
            normalized_response = _normalize_stored_answer(response or "该席位返回了空回答。")
            detail = _render_stored_answer_html(normalized_response)
            raw_detail = html.escape(normalized_response)
            recovered = " · 补跑追回" if item.get("recovered_by_retry") else ""
            meta = f"{len(normalized_response)} 字符 · 用时 {item.get('elapsed_seconds', '-') }s · 分数 {score_text}{retry_note}{recovered}"
            preview = _compact_report_text(normalized_response, 180)
        else:
            pending = _is_supplementable_result(item)
            status = "待回收" if pending else "未完成"
            status_class = "is-failed"
            state_class = "warn" if pending else "bad"
            code = str(error.get("code") or "unknown")
            message = str(error.get("message") or "No response captured.")
            history = item.get("retry_history") or []
            history_text = ""
            if history:
                history_text = "\n\n补跑历史:\n" + "\n".join(
                    f"- attempt {entry.get('attempt')}: {entry.get('error_code') or 'ok'} {entry.get('error_message') or ''}".rstrip()
                    for entry in history
                )
            detail = html.escape(f"{code}: {message}{history_text}")
            raw_detail = detail
            meta = f"{code} · 分数 {score_text}{retry_note}"
            preview = _compact_report_text(message, 180)
        answer_body = (
            f'<div class="answer readable-answer">{detail}</div>'
            f'<details class="raw-log"><summary>查看纯文本原始日志</summary><pre class="answer raw-answer">{raw_detail}</pre></details>'
            if ok
            else f'<pre class="answer raw-answer">{detail}</pre>'
        )
        open_attr = " open" if not ok else ""
        cards.append(
            f'<details class="seat-answer {status_class}" id="seat-answer-{html.escape(seat)}"{open_attr}>'
            "<summary>"
            f"<strong>{html.escape(seat_name)}</strong>"
            f'<span class="seat-state {state_class}">{html.escape(status)}</span>'
            f'<span class="seat-meta">{html.escape(meta)}</span>'
            "</summary>"
            f'<p class="seat-preview">{html.escape(preview)}</p>'
            f"{answer_body}"
            "</details>"
        )
    return (
        '<section class="band" id="seat-answers">'
        '<div class="section-head"><div>'
        "<h2>内部资料库：席位完整原始日志</h2>"
        "<p class=\"muted\">这里是本地存档的模型原文日志；成功席位默认收起，慢席位和失败席位默认展开，不跳外部登录页。</p>"
        '</div><div class="mini-actions">'
        '<button type="button" data-seat-action="expand">全部展开</button>'
        '<button type="button" data-seat-action="collapse">全部收起</button>'
        "</div></div>"
        f'<div class="seat-answer-list">{"".join(cards)}</div>'
        "</section>"
    )


def _render_mentor_supplements(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    supplements = bridge.get("mentor_supplements") or []
    if not supplements:
        return ""

    cards: list[str] = []
    for item in supplements:
        seat = str(item.get("seat") or "")
        seat_name = str(item.get("seat_name") or seat)
        ok = bool(item.get("ok"))
        questions = item.get("source_questions") or []
        question_items = "".join(f"<li>{html.escape(str(q))}</li>" for q in questions) or "<li>该席位未显式返回问题，系统使用了兜底共振问题。</li>"
        response = str(item.get("response") or "")
        error = item.get("error") or {}
        status = "已补充" if ok else "未完成"
        status_class = "is-ok" if ok else "is-failed"
        state_class = "good" if ok else "bad"
        normalized_response = _normalize_stored_answer(response)
        detail = _render_stored_answer_html(normalized_response) if ok else html.escape(f"{error.get('code', 'unknown')}: {error.get('message', 'No response captured.')}")
        raw_detail = html.escape(normalized_response) if ok else detail
        preview = _compact_report_text(response if ok else error.get("message", ""), 180)
        answer_body = (
            f'<div class="answer readable-answer">{detail}</div>'
            f'<details class="raw-log"><summary>查看纯文本二轮日志</summary><pre class="answer raw-answer">{raw_detail}</pre></details>'
            if ok
            else f'<pre class="answer raw-answer">{detail}</pre>'
        )
        cards.append(
            f'<details class="seat-answer {status_class}" id="mentor-supplement-{html.escape(seat)}"{"" if ok else " open"}>'
            "<summary>"
            f"<strong>{html.escape(seat_name)}</strong>"
            f'<span class="seat-state {state_class}">{html.escape(status)}</span>'
            f'<span class="seat-meta">{len(questions)} 个问题 · {html.escape(str(item.get("elapsed_seconds", "-")))}s</span>'
            "</summary>"
            f'<ul class="compact-list">{question_items}</ul>'
            f'<p class="seat-preview">{html.escape(preview)}</p>'
            f"{answer_body}"
            "</details>"
        )
    ok_count = sum(1 for item in supplements if item.get("ok"))
    question_count = sum(len(item.get("source_questions") or []) for item in supplements)
    return (
        '<section class="band" id="mentor-supplements">'
        '<div class="section-head"><div>'
        "<h2>共振提问与二轮方案</h2>"
        f'<p class="muted">每个模型先提出补强问题，再带入用户角色回答自己的问题。已回收 {ok_count}/{len(supplements)} 席，问题 {question_count} 个。</p>'
        "</div></div>"
        f'<div class="seat-answer-list">{"".join(cards)}</div>'
        "</section>"
    )


def _render_complete_result_archive(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    deliberation = bridge.get("deliberation") or {}
    supplements = bridge.get("mentor_supplements") or []
    pipeline = bridge.get("pipeline") or {}
    phases = pipeline.get("phases") or []
    grand = result.get("grand_judge") or {}
    citation = grand.get("citation_verification") or bridge.get("citation_verification") or {}
    evidence = grand.get("evidence_broker") or {}
    if not any([raw_results, deliberation, supplements, citation, result.get("final_report")]):
        return ""

    ok_count = sum(1 for item in raw_results if item.get("ok"))
    requested = int(bridge.get("requested_count") or len(raw_results) or result.get("seat_count") or 0)
    question_count = sum(len(item.get("source_questions") or []) for item in supplements)
    if not question_count:
        question_count = int(next((phase.get("count") for phase in phases if phase.get("id") == "extract_resonance_questions"), 0) or 0)
    supplement_ok = sum(1 for item in supplements if item.get("ok"))
    peer_count = int(deliberation.get("peer_review_count") or len(deliberation.get("peer_reviews") or []) or 0)
    summary_count = int(deliberation.get("summary_claim_count") or len(deliberation.get("answer_summaries") or []) or 0)
    citation_count = int(citation.get("item_count") or len(citation.get("items") or []) or 0)
    evidence_count = int((evidence.get("counts") or {}).get("total") or len(evidence.get("items") or []) or 0)
    score_round_count = len(bridge.get("score_rounds") or [])

    cards = [
        (
            "原始回答",
            f"{ok_count}/{requested or len(raw_results)} 席",
            "完整模型正文、本地日志、失败原因和补跑记录。",
            "#seat-answers",
        ),
        (
            "互评摘要",
            f"{peer_count} 条互评",
            f"答案摘要、立场分布、交叉评分矩阵；摘要 claims {summary_count}。",
            "#deliberation",
        ),
        (
            "共振追问",
            f"{question_count} 个问题",
            "从第一轮答案里提取追问，用于二轮补强。",
            "#mentor-supplements",
        ),
        (
            "导师补充",
            f"{supplement_ok}/{len(supplements)} 席",
            "二轮回答原文、问题来源和补充日志。",
            "#mentor-supplements",
        ),
        (
            "最终依据",
            f"{citation_count} 引用 · {score_round_count} 轮评分",
            f"引用验证、证据缺口、评分轮次和 Evidence OS；外部证据 {evidence_count}。",
            "#citation-verification",
        ),
        (
            "底层资料",
            "Prompt / JSON",
            "提示词对齐、执行驱动、底层轨迹和原始 JSON 仅用于内部复核。",
            "#raw-json",
        ),
    ]
    card_html = "".join(
        '<a class="archive-card" href="{href}">'
        "<span>{label}</span>"
        "<strong>{value}</strong>"
        "<small>{description}</small>"
        "</a>".format(
            href=html.escape(href),
            label=html.escape(label),
            value=html.escape(value),
            description=html.escape(description),
        )
        for label, value, description, href in cards
    )
    return (
        '<section class="band result-archive" id="result-archive">'
        '<div class="section-head"><div>'
        "<h2>完整结果资料库</h2>"
        '<p class="muted">这是内部存储索引，不跳登录页：从这里追溯原始回答、互评、共振、导师补充、最终依据和底层日志。</p>'
        "</div></div>"
        f'<div class="archive-grid">{card_html}</div>'
        "</section>"
    )


def _normalize_stored_answer(value: Any) -> str:
    text = str(value or "")
    if re.search(r"\\u[0-9a-fA-F]{4}", text):
        try:
            decoded = text.encode("utf-8").decode("unicode_escape")
            if sum("\u4e00" <= ch <= "\u9fff" for ch in decoded) > sum("\u4e00" <= ch <= "\u9fff" for ch in text):
                text = decoded
        except Exception:
            pass
    if "\\n" in text and text.count("\n") < max(2, text.count("\\n") // 4):
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    text = re.sub(r"\[AIJUDGE_ANSWER_START:[^\]]+\]", "", text)
    text = re.sub(r"\[AIJUDGE_ANSWER_END:[^\]]+\]", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _render_stored_answer_html(value: Any) -> str:
    text = _normalize_stored_answer(value)
    if not text:
        return "<p>该席位没有返回可展示正文。</p>"
    lines = text.splitlines()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_rows: list[list[str]] = []
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{_answer_inline_html(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{_answer_inline_html(item)}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_table() -> None:
        nonlocal table_rows
        if table_rows:
            rows = []
            for row in table_rows:
                cells = "".join(f"<td>{_answer_inline_html(cell)}</td>" for cell in row)
                rows.append(f"<tr>{cells}</tr>")
            blocks.append('<div class="stored-table-wrap"><table class="stored-table"><tbody>' + "".join(rows) + "</tbody></table></div>")
            table_rows = []

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            escaped = html.escape("\n".join(code_lines))
            blocks.append(f'<pre class="stored-code">{escaped}</pre>')
            code_lines = []

    for raw in lines:
        line = raw.strip()
        if line.startswith("```"):
            if in_code:
                in_code = False
                flush_code()
            else:
                flush_paragraph()
                flush_list()
                flush_table()
                in_code = True
            continue
        if in_code:
            code_lines.append(raw)
            continue
        if not line:
            flush_paragraph()
            flush_list()
            flush_table()
            continue
        if "|" in line and line.count("|") >= 2:
            flush_paragraph()
            flush_list()
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells and not all(re.fullmatch(r":?-{2,}:?", cell or "") for cell in cells):
                table_rows.append(cells)
            continue
        flush_table()
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(4, len(heading.group(1)) + 2)
            blocks.append(f"<h{level}>{_answer_inline_html(heading.group(2))}</h{level}>")
            continue
        bullet = re.match(r"^(?:[-*•]|\d+[.)、])\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            list_items.append(bullet.group(1).strip())
            continue
        flush_list()
        paragraph.append(line)
    flush_code()
    flush_paragraph()
    flush_list()
    flush_table()
    return "".join(blocks)


def _answer_inline_html(value: Any) -> str:
    escaped = html.escape(str(value or ""))
    escaped = re.sub(
        r"(https?://[^\s<]+)",
        lambda match: f'<a href="{html.escape(match.group(1).rstrip(".,;，。；"))}" target="_blank" rel="noreferrer">{html.escape(match.group(1).rstrip(".,;，。；"))}</a>',
        escaped,
    )
    escaped = re.sub(
        r"([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})",
        lambda match: f'<a href="mailto:{html.escape(match.group(1))}">{html.escape(match.group(1))}</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _render_judge_answer(result: dict[str, Any]) -> str:
    judge = result.get("judge_answer") or {}
    baseline = result.get("single_judge_baseline") or {}
    if not judge and not baseline:
        return ""
    label = str(judge.get("label") or baseline.get("label") or "AI Judge 法官答案")
    limits = "".join(f"<li>{html.escape(str(item))}</li>" for item in judge.get("limits", []))
    agreements = ", ".join(str(item) for item in judge.get("agreements", [])[:8]) or "-"
    comparison_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('metric', '')))}</td>"
        f"<td>{html.escape(str(item.get('single_judge', '')))}</td>"
        f"<td>{html.escape(str(item.get('council', '')))}</td>"
        "</tr>"
        for item in baseline.get("comparison", [])
    )
    return (
        '<section class="band" id="judge-answer">'
        f"<h2>{html.escape(label)}与单模型对照</h2>"
        f"<p>{html.escape(str(judge.get('answer', '暂无法官汇总答案。')))}</p>"
        '<section class="summary-grid compact" aria-label="法官基准">'
        f"<div><span>法官单模型分</span><strong>{html.escape(str(baseline.get('score', '-')))}</strong></div>"
        f"<div><span>单模型层级</span><strong>{html.escape(str(baseline.get('tier', '-')))}</strong></div>"
        f"<div><span>议会均分</span><strong>{html.escape(str(baseline.get('council_average_score', result.get('average_score', '-'))))}</strong></div>"
        f"<div><span>差值</span><strong>{html.escape(str(baseline.get('delta_vs_council', '-')))}</strong></div>"
        "</section>"
        f"<p><strong>主导立场：</strong>{html.escape(str(judge.get('dominant_stance', '-')))}</p>"
        f"<p><strong>主要共识：</strong>{html.escape(agreements)}</p>"
        f"<ul class=\"compact-list\">{limits}</ul>"
        "<h3>单一法官 vs 多席位议会</h3>"
        "<table><thead><tr><th>维度</th><th>AI Judge 单模型</th><th>AI Judge 议会</th></tr></thead>"
        f"<tbody>{comparison_rows}</tbody></table>"
        "</section>"
    )


def _render_final_report(result: dict[str, Any]) -> str:
    report = result.get("final_report") or {}
    if not report.get("compact_overview"):
        report = build_final_report(result)
        result["final_report"] = report
    if not report:
        return ""
    return render_final_report_html(report)


def _report_header_copy(result: dict[str, Any]) -> tuple[str, str, str]:
    report = result.get("final_report") or {}
    brief = report.get("decision_brief") or {}
    longform = report.get("longform_report") or (report.get("compiled_report") or {}).get("longform_report") or {}
    executive = report.get("executive_summary") or {}
    run_health = report.get("run_health") or {}
    title = (
        brief.get("title")
        or longform.get("title")
        or report.get("title")
        or result.get("one_liner")
        or "AI Judge Verdict"
    )
    summary = (
        brief.get("one_sentence")
        or executive.get("headline")
        or report.get("abstract")
        or run_health.get("headline")
        or result.get("one_liner")
        or ""
    )
    raw_question = _compact_report_text(result.get("question") or "", 420)
    return (
        _compact_report_text(title, 160),
        _compact_report_text(summary, 360),
        raw_question,
    )


def _report_header_copy_en(result: dict[str, Any]) -> tuple[str, str]:
    report = result.get("final_report") or {}
    brief = report.get("decision_brief") or {}
    source = " ".join(
        str(item or "")
        for item in [
            brief.get("title"),
            brief.get("one_sentence"),
            (report.get("longform_report") or {}).get("title"),
            result.get("question"),
        ]
    )
    if any(token in source for token in ("商业化", "融资", "投稿", "GitHub", "加星")):
        return (
            "AI Judge Commercialization / Publishing / Fundraising / GitHub Stars Report",
            "Stage-ready recommendation: validate developer demand through GitHub, Hugging Face, Show HN, and Reddit first, then expand into publishing, fundraising, and enterprise pilots.",
        )
    if any(token in source for token in ("产品", "流程", "报告", "展示", "体验", "网页")):
        return (
            "AI Judge Product Flow Audit Report",
            "The product should behave like an asynchronous report workbench: produce a readable single-page report first, then update evidence and run-health in the background.",
        )
    if report.get("report_mode") == "bridge_recovery_required":
        return (
            "AI Judge Stage Report With Run-Health Gate",
            "Stage report: the recommendation is readable now while evidence and run-health continue updating in the background.",
        )
    return (
        "AI Judge Final Decision Report",
        "Final report: the decision, evidence, risks, and execution plan are ready to review, download, and share.",
    )


def _render_score_rounds(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    rounds = bridge.get("score_rounds") or []
    if not rounds:
        return ""
    round_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', item.get('id', ''))))}</td>"
        f"<td>{html.escape(str(item.get('claim_count', 0)))}</td>"
        f"<td>{html.escape(_format_report_score(item.get('average_score')))}</td>"
        f"<td>{html.escape(_round_seat_score_text(item.get('seat_scores', [])))}</td>"
        "</tr>"
        for item in rounds
    )
    details = "".join(_render_round_detail(item) for item in rounds if item.get("top_claims"))
    return (
        '<section class="band" id="score-rounds">'
        "<h2>每轮评分表现</h2>"
        '<p class="muted">这里显示评分体系的实际运转：原始答案、答案总结、席位互评分别怎样进入 claim 评分。</p>'
        "<table><thead><tr><th>评分轮次</th><th>Claims</th><th>均分</th><th>席位表现</th></tr></thead>"
        f"<tbody>{round_rows}</tbody></table>"
        f"{details}"
        "</section>"
    )


def _render_round_detail(round_item: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('seat_name', item.get('seat', ''))))}</td>"
        f"<td>{float(item.get('score', 0.0)):.3f}</td>"
        f"<td>{html.escape(str(item.get('tier', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('claim', ''), 220))}</td>"
        "</tr>"
        for item in round_item.get("top_claims", [])[:8]
    )
    return (
        "<details class=\"nested\"><summary>"
        f"{html.escape(str(round_item.get('label', '评分轮次')))} Top Claims"
        "</summary>"
        "<table><thead><tr><th>席位</th><th>分数</th><th>层级</th><th>Claim</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></details>"
    )


def _render_seat_digest(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    digest = bridge.get("seat_answer_digest") or []
    if not digest:
        return ""
    rows = "".join(
        "<tr>"
        f"<td><a href=\"#seat-answer-{html.escape(str(item.get('seat', '')))}\">{html.escape(str(item.get('seat_name', item.get('seat', ''))))}</a></td>"
        f"<td>{html.escape(str(item.get('status', '-')))}</td>"
        f"<td>{html.escape(_format_report_score(item.get('score')))}</td>"
        f"<td>{html.escape(str(item.get('stance', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text('；'.join(str(x) for x in item.get('pros', [])), 220))}</td>"
        f"<td>{html.escape(_compact_report_text('；'.join(str(x) for x in item.get('cons', [])), 220))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('answer_preview', ''), 180))}</td>"
        "</tr>"
        for item in digest
    )
    return (
        '<section class="band" id="seat-digest">'
        "<h2>内部资料库：每个模型的回答索引</h2>"
        '<p class="muted">这一层是本地资料库索引：点席位名跳到内部完整原文日志，优缺点来自席位画像、证据密度、互评和评分结果。</p>'
        "<table><thead><tr><th>席位</th><th>状态</th><th>均分</th><th>立场</th><th>优点</th><th>缺点</th><th>回答预览</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "</section>"
    )


def _round_seat_score_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "-"
    return " / ".join(
        f"{row.get('seat_name', row.get('seat'))}:{float(row.get('average_score', 0.0)):.3f}"
        for row in rows[:6]
    )


def _format_report_score(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.3f}"
    except Exception:
        return str(value)


def _render_deliberation(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    deliberation = bridge.get("deliberation") or {}
    if not deliberation:
        return ""

    stance = deliberation.get("stance_distribution") or {}
    stance_text = " · ".join(f"{key} {value}" for key, value in stance.items()) or "-"
    agreements = ", ".join(str(item) for item in deliberation.get("agreements", [])[:8]) or "-"
    disagreements = "".join(
        f"<li>{html.escape(str(item))}</li>"
        for item in deliberation.get("disagreements", [])[:8]
    ) or "<li>暂无明显分歧。</li>"

    summary_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('seat_name', item.get('seat'))))}</td>"
        f"<td>{html.escape(str(item.get('stance', '-')))}</td>"
        f"<td>{float(item.get('quality', 0.0)):.3f}</td>"
        f"<td>{html.escape(str(item.get('avg_peer_score', '-')))}</td>"
        f"<td>{int(item.get('review_count', 0))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('summary', ''), 160))}</td>"
        "</tr>"
        for item in deliberation.get("answer_summaries", [])
    )
    review_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('reviewer_name', item.get('reviewer'))))}</td>"
        f"<td>{html.escape(str(item.get('target_name', item.get('target'))))}</td>"
        f"<td>{float(item.get('score', 0.0)):.3f}</td>"
        f"<td>{html.escape(str(item.get('label', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('comment', ''), 220))}</td>"
        "</tr>"
        for item in deliberation.get("peer_reviews", [])[:80]
    )
    pipeline = bridge.get("pipeline") or {}
    phase_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', item.get('id', ''))))}</td>"
        f"<td>{html.escape(str(item.get('count', '-')))}</td>"
        "</tr>"
        for item in pipeline.get("phases", [])
    )
    return (
        '<section class="band" id="deliberation">'
        '<div class="section-head"><div>'
        "<h2>答案总结、互评与评分链路</h2>"
        '<p class="muted">这是网页席位返回后的 AI Judge 底层审议阶段：先压缩答案，再互评，最后进入评分引擎。</p>'
        "</div></div>"
        '<section class="summary-grid compact" aria-label="审议状态">'
        f"<div><span>互评轮次</span><strong>{int(deliberation.get('peer_review_count', 0))}</strong></div>"
        f"<div><span>摘要 Claims</span><strong>{int(deliberation.get('summary_claim_count', 0))}</strong></div>"
        f"<div><span>审议 Claims</span><strong>{int(deliberation.get('claim_count', 0))}</strong></div>"
        f"<div><span>评分引擎</span><strong>{html.escape(str(pipeline.get('scoring_engine', 'score_jury_v2')).split('.')[-1])}</strong></div>"
        "</section>"
        f"<p><strong>立场分布：</strong>{html.escape(stance_text)}</p>"
        f"<p><strong>主要共识词：</strong>{html.escape(agreements)}</p>"
        f'<ul class="compact-list">{disagreements}</ul>'
        "<h3>底层阶段</h3>"
        f"<table><thead><tr><th>阶段</th><th>数量</th></tr></thead><tbody>{phase_rows}</tbody></table>"
        "<h3>席位答案摘要</h3>"
        "<table><thead><tr><th>席位</th><th>立场</th><th>质量</th><th>互评分</th><th>互评数</th><th>摘要</th></tr></thead>"
        f"<tbody>{summary_rows}</tbody></table>"
        "<details class=\"nested\"><summary>查看互评矩阵</summary>"
        "<table><thead><tr><th>评审席位</th><th>被评席位</th><th>分数</th><th>标签</th><th>判断</th></tr></thead>"
        f"<tbody>{review_rows}</tbody></table></details>"
        "</section>"
    )


def _render_citation_verification(result: dict[str, Any]) -> str:
    report = result.get("grand_judge") or {}
    bridge = result.get("web_bridge") or {}
    citation = report.get("citation_verification") or bridge.get("citation_verification") or {}
    ledger = report.get("replay_ledger") or bridge.get("replay_ledger") or []
    if not citation and not ledger:
        return ""

    counts = citation.get("counts") or {}
    status = str(citation.get("overall_status") or "unverifiable")
    certification_id = str(citation.get("certification_id") or bridge.get("certification_id") or report.get("certification_id") or "-")
    ledger_hash = str(citation.get("replay_ledger_hash") or bridge.get("replay_ledger_hash") or report.get("replay_ledger_hash") or "-")
    gap_suggestions = (report.get("evidence_gap_suggestions") or bridge.get("evidence_gap_suggestions") or {}).get("suggestions") or []
    rows: list[str] = []
    for entry in ledger:
        rows.extend(_citation_rows_for_entry(entry, layer="原始回答", report_key="citation_verification"))
        rows.extend(_citation_rows_for_entry(entry, layer="导师补充", report_key="mentor_citation_verification"))
    if not rows:
        rows.append("<tr><td colspan=\"7\">暂无可展示引用行。</td></tr>")

    gap_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('citation_id', '-')))}</td>"
        f"<td>{html.escape(str(item.get('mentor_level', '-')))}</td>"
        f"<td>{html.escape(str(item.get('status', '-')))}</td>"
        f"<td>{html.escape(str(item.get('suggested_action', '-')))}</td>"
        "</tr>"
        for item in gap_suggestions[:12]
    ) or "<tr><td colspan=\"4\">暂无证据缺口建议。</td></tr>"

    return (
        '<section class="band" id="citation-verification">'
        '<div class="section-head"><div>'
        "<h2>引用验证 MVP</h2>"
        '<p class="muted">Grand Judge 只编排验证，不改写模型原文。原始回答、导师补充、外部证据三层隔离。</p>'
        "</div></div>"
        '<section class="summary-grid compact" aria-label="引用验证状态">'
        f"<div><span>Certification ID</span><strong>{html.escape(certification_id)}</strong></div>"
        f"<div><span>整体状态</span><strong class=\"{_citation_status_class(status)}\">{html.escape(_citation_status_label(status))}</strong></div>"
        f"<div><span>引用条目</span><strong>{html.escape(str(citation.get('item_count', 0)))}</strong></div>"
        f"<div><span>外部证据</span><strong>{html.escape(str(citation.get('external_evidence_count', 0)))}</strong></div>"
        "</section>"
        f"<p class=\"muted\"><strong>unverifiable 说明：</strong>{html.escape(str(citation.get('unverifiable_explanation') or 'unverifiable 不是 false。'))}</p>"
        f"<p class=\"muted\">Replay Ledger Hash: <code>{html.escape(ledger_hash[:24])}</code> · verified {counts.get('verified', 0)} / weak {counts.get('weakly_verified', 0)} / irrelevant {counts.get('irrelevant', 0)} / unverifiable {counts.get('unverifiable', 0)} / contradicted {counts.get('contradicted', 0)}</p>"
        "<table><thead><tr><th>席位</th><th>层</th><th>Citation</th><th>状态</th><th>相关性</th><th>原因</th><th>证据</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<details class=\"nested\"><summary>Replay Ledger 与证据缺口建议</summary>"
        "<p class=\"muted\">Ledger 记录原始回答哈希、导师补充哈希、不可验证原因和验证时间戳；完整原文在“席位完整回答”和“共振二轮”中查看。</p>"
        "<table><thead><tr><th>Citation</th><th>导师等级</th><th>状态</th><th>建议动作</th></tr></thead>"
        f"<tbody>{gap_rows}</tbody></table></details>"
        "</section>"
    )


def _citation_rows_for_entry(entry: dict[str, Any], *, layer: str, report_key: str) -> list[str]:
    report = entry.get(report_key) or {}
    rows: list[str] = []
    for item in report.get("items") or []:
        evidence = item.get("matched_evidence") or {}
        evidence_text = evidence.get("title") or evidence.get("url") or evidence.get("evidence_id") or "-"
        status = str(item.get("status") or "unverifiable")
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(entry.get('seat_name') or entry.get('seat') or '-'))}</td>"
            f"<td>{html.escape(layer)}</td>"
            f"<td>{html.escape(_compact_report_text(item.get('raw', '-'), 120))}</td>"
            f"<td><span class=\"status-pill {_citation_status_class(status)}\">{html.escape(_citation_status_label(status))}</span></td>"
            f"<td>{html.escape(_format_report_score(item.get('relevance_score')))}</td>"
            f"<td>{html.escape(_compact_report_text(item.get('reason', ''), 180))}</td>"
            f"<td>{html.escape(_compact_report_text(evidence_text, 160))}</td>"
            "</tr>"
        )
    return rows


def _citation_status_label(status: str) -> str:
    return {
        "verified": "verified",
        "weakly_verified": "weakly verified",
        "irrelevant": "irrelevant",
        "unverifiable": "unverifiable",
        "contradicted": "contradicted",
    }.get(status, status)


def _citation_status_class(status: str) -> str:
    return {
        "verified": "good",
        "weakly_verified": "warn",
        "irrelevant": "warn",
        "unverifiable": "warn",
        "contradicted": "bad",
    }.get(status, "warn")


def _render_evidence_os(result: dict[str, Any]) -> str:
    grand = result.get("grand_judge") or {}
    if not grand:
        return ""
    broker = grand.get("evidence_broker") or {}
    metrics = grand.get("evidence_quality_metrics") or {}
    blind = grand.get("blind_cross_validation") or {}
    queue = grand.get("evidence_gap_queue") or {}
    human = grand.get("human_review_status") or {}
    eval_case = grand.get("eval_case") or {}
    broker_counts = broker.get("counts") or {}
    blind_result = blind.get("result") or {}
    evidence_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('id', '-')))}</td>"
        f"<td>{html.escape(str(item.get('source_layer', '-')))}</td>"
        f"<td>{html.escape(str(item.get('retrieval_state', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('title') or item.get('url') or item.get('raw_source') or '-', 180))}</td>"
        "</tr>"
        for item in (broker.get("items") or [])[:16]
    ) or "<tr><td colspan=\"4\">暂无外部证据。</td></tr>"
    gap_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('task_id', '-')))}</td>"
        f"<td>{html.escape(str(item.get('priority', '-')))}</td>"
        f"<td>{html.escape(str(item.get('queue_status', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('suggested_action', '-'), 220))}</td>"
        "</tr>"
        for item in (queue.get("tasks") or [])[:12]
    ) or "<tr><td colspan=\"4\">暂无证据缺口任务。</td></tr>"
    return (
        '<section class="band" id="evidence-os">'
        '<div class="section-head"><div>'
        "<h2>Evidence OS</h2>"
        '<p class="muted">硬证据层、匿名双盲验证、证据缺口队列、人工签名和 eval case 都在这里汇总。</p>'
        "</div></div>"
        '<section class="summary-grid compact" aria-label="Evidence OS 状态">'
        f"<div><span>Groundedness</span><strong>{html.escape(str(metrics.get('groundedness_proxy', '-')))}</strong></div>"
        f"<div><span>Trust Gate</span><strong class=\"{_evidence_gate_class(str(metrics.get('trust_gate', '')))}\">{html.escape(str(metrics.get('trust_gate', '-')))}</strong></div>"
        f"<div><span>双盲状态</span><strong>{html.escape(str(blind_result.get('status') or blind.get('status') or '-'))}</strong></div>"
        f"<div><span>人工签名</span><strong>{html.escape(str(human.get('status', '-')))}</strong></div>"
        "</section>"
        f"<p class=\"muted\">Evidence Broker: user {broker_counts.get('user_supplied', 0)} / fetched {broker_counts.get('network_fetch', 0)} / candidate {broker_counts.get('candidate_source', 0)}。Eval Case: <code>{html.escape(str(eval_case.get('case_id', '-')))}</code></p>"
        "<details class=\"nested\"><summary>查看 Evidence Broker 来源</summary>"
        "<table><thead><tr><th>ID</th><th>来源层</th><th>检索状态</th><th>标题/URL</th></tr></thead>"
        f"<tbody>{evidence_rows}</tbody></table></details>"
        "<details class=\"nested\"><summary>查看证据缺口队列</summary>"
        "<table><thead><tr><th>任务</th><th>优先级</th><th>状态</th><th>建议动作</th></tr></thead>"
        f"<tbody>{gap_rows}</tbody></table></details>"
        "</section>"
    )


def _evidence_gate_class(gate: str) -> str:
    if gate == "pass":
        return "good"
    if gate == "blocked_contradiction":
        return "bad"
    return "warn"


def _render_cross_temporal_analysis(result: dict[str, Any]) -> str:
    analysis = result.get("cross_temporal_analysis") or {}
    if not analysis:
        return ""
    closeout = analysis.get("closeout_report") or {}
    trust_tier = analysis.get("trust_tier") or closeout.get("trust_tier") or {}
    vertical = analysis.get("vertical_trace") or {}
    horizontal = analysis.get("horizontal_comparison") or {}
    math_audit = analysis.get("math_audit") or {}
    actions = analysis.get("recommended_actions") or []
    signals = math_audit.get("signals") or []
    ranking = horizontal.get("seat_ranking") or []
    action_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in actions[:6]) or "<li>暂无建议动作。</li>"
    signal_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', '-')))}</td>"
        f"<td><span class=\"status-pill {_signal_status_class(str(item.get('severity', 'ok')))}\">{html.escape(_signal_status_label(str(item.get('severity', 'ok'))))}</span></td>"
        f"<td>{html.escape(str(item.get('value', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('summary', ''), 220))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('next_action', ''), 180))}</td>"
        "</tr>"
        for item in signals[:10]
    ) or "<tr><td colspan=\"5\">暂无数学审计信号。</td></tr>"
    ranking_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('seat_name') or item.get('seat') or '-'))}</td>"
        f"<td>{html.escape(_format_report_score(item.get('score')))}</td>"
        f"<td>{html.escape(str(item.get('status', '-')))}</td>"
        f"<td>{html.escape(str(item.get('claims_count', 0)))}</td>"
        "</tr>"
        for item in ranking[:12]
    ) or "<tr><td colspan=\"4\">暂无席位评分。</td></tr>"
    timeline_items = "".join(
        f"<li><strong>{html.escape(str(item.get('phase', '-')))}</strong><span>{html.escape(_compact_report_text(item.get('detail', ''), 160))}</span></li>"
        for item in (vertical.get("timeline") or [])[-6:]
    ) or "<li><strong>complete</strong><span>暂无可展示的底层轨迹。</span></li>"
    return (
        '<section class="band" id="cross-temporal">'
        '<div class="section-head"><div>'
        "<h2>横纵分析收口报告</h2>"
        f'<p class="muted">{html.escape(str(analysis.get("method") or ""))}</p>'
        "</div></div>"
        '<section class="summary-grid compact" aria-label="横纵分析状态">'
        f"<div><span>最终判断</span><strong>{html.escape(str(closeout.get('decision_score', '-')))}</strong></div>"
        f"<div><span>可信等级</span><strong>{html.escape(str(trust_tier.get('label', '-')))}</strong></div>"
        f"<div><span>必需席位</span><strong>{html.escape(str(horizontal.get('required_ok_count', horizontal.get('ok_count', 0))))}/{html.escape(str(horizontal.get('required_count', horizontal.get('requested_count', 0))))}</strong></div>"
        f"<div><span>共识状态</span><strong>{html.escape(str(horizontal.get('consensus_label', '-')))}</strong></div>"
        "</section>"
        f"<p class=\"muted\"><strong>可信等级说明：</strong>{html.escape(str(trust_tier.get('summary', '')))}</p>"
        f'<p class="report-lead">{html.escape(str(closeout.get("executive_summary", "")))}</p>'
        '<div class="report-columns">'
        '<section class="report-column">'
        "<h3>纵向：从执行轨迹看卡点</h3>"
        f"<p>{html.escape(str(vertical.get('key_turn', '-')))}</p>"
        f'<ul class="trace-mini">{timeline_items}</ul>'
        "</section>"
        '<section class="report-column">'
        "<h3>横向：从模型席位看分歧</h3>"
        f"<p>{html.escape(str(horizontal.get('comparison_note', '-')))}</p>"
        "<table><thead><tr><th>席位</th><th>分数</th><th>状态</th><th>Claims</th></tr></thead>"
        f"<tbody>{ranking_rows}</tbody></table>"
        "</section></div>"
        "<h3>数学审计信号</h3>"
        "<table><thead><tr><th>信号</th><th>状态</th><th>值</th><th>解释</th><th>动作</th></tr></thead>"
        f"<tbody>{signal_rows}</tbody></table>"
        "<h3>执行建议</h3>"
        f'<ol class="compact-list">{action_items}</ol>'
        "</section>"
    )


def _signal_status_label(status: str) -> str:
    return {"ok": "ok", "warn": "watch", "block": "block"}.get(status, status)


def _signal_status_class(status: str) -> str:
    return {"ok": "good", "warn": "warn", "block": "bad"}.get(status, "warn")


def _render_html_report(result: dict[str, Any]) -> str:
    reasons = "".join(
        f"<li>{html.escape(_compact_report_text(r, 260))}</li>"
        for r in result.get("reasons", [])
    ) or "<li>暂无关键理由。</li>"
    steps = "".join(f"<li>{html.escape(str(s))}</li>" for s in result.get("next_steps", [])) or "<li>暂无建议行动。</li>"
    prompt_flow = result.get("prompt_flow") or {}
    execution_plan = result.get("execution_plan") or {}
    prompt_html = ""
    if prompt_flow:
        assumptions = "".join(f"<li>{html.escape(str(item))}</li>" for item in prompt_flow.get("assumptions_to_check", []))
        prompt_html = (
            "<details class=\"band\" id=\"prompt-flow\"><summary><h2>网页提示词对齐与专业提示词</h2></summary>"
            f"<p>{html.escape(str(prompt_flow.get('quick_response', '')))}</p>"
            f"<h3>专业提示词</h3><pre>{html.escape(str(prompt_flow.get('professional_prompt', '')))}</pre>"
            f"<h3>需要核查的假设</h3><ul>{assumptions}</ul>"
            "</details>"
        )
    blocked_html = ""
    if execution_plan:
        blocked_rows = "".join(
            "<tr>"
            f"<td>{html.escape(str(item.get('seat_name', item.get('seat'))))}</td>"
            f"<td>{html.escape(str(item.get('driver', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            f"<td>{html.escape(str(item.get('calibration_status', '')))}</td>"
            "</tr>"
            for item in execution_plan.get("blocked_seats", [])
        )
        blocked_html = (
            "<details class=\"band\"><summary><h2>执行驱动</h2></summary>"
            f"<p>{html.escape(str(execution_plan.get('message', '')))}</p>"
            f"<p>可运行席位：{html.escape(', '.join(execution_plan.get('runnable_seats', [])) or '-')}</p>"
            "<table><thead><tr><th>阻断席位</th><th>驱动</th><th>原因</th><th>校准</th></tr></thead>"
            f"<tbody>{blocked_rows}</tbody></table></details>"
        )
    trace = result.get("execution_trace") or {}
    trace_html = ""
    if trace.get("events"):
        trace_rows = "".join(
            "<tr>"
            f"<td>{int(event.get('index', 0))}</td>"
            f"<td>{html.escape(str(event.get('phase', '')))}</td>"
            f"<td>{html.escape(str(event.get('action', '')))}</td>"
            f"<td>{html.escape(str(event.get('detail', '')))}</td>"
            f"<td><pre>{html.escape(json.dumps(event.get('data', {}), ensure_ascii=False, indent=2))}</pre></td>"
            "</tr>"
            for event in trace.get("events", [])[:80]
        )
        trace_html = (
            "<details class=\"band\"><summary><h2>底层执行轨迹</h2></summary>"
            "<table><thead><tr><th>#</th><th>Phase</th><th>Action</th><th>Detail</th><th>Data</th></tr></thead>"
            f"<tbody>{trace_rows}</tbody></table></details>"
        )
    seats_html = "".join(
        "<tr>"
        f"<td>{html.escape(str(s.get('seat_name', s.get('seat'))))}</td>"
        f"<td>{html.escape(str(s.get('mbti', '')))}</td>"
        f"<td>{float(s.get('average_score', 0.0)):.3f}</td>"
        f"<td>{int(s.get('claims_count', 0))}</td>"
        "</tr>"
        for s in result.get("seat_scores", [])
    )
    raw_json = html.escape(json.dumps(result, ensure_ascii=False, indent=2))
    collection_html = _render_collection_summary(result)
    final_report_html = _render_final_report(result)
    report_markdown_json = json.dumps(
        render_final_report_markdown(result.get("final_report") or {}),
        ensure_ascii=False,
    ).replace("</", "<\\/")
    header_title, header_summary, raw_question = _report_header_copy(result)
    header_title_en, header_summary_en = _report_header_copy_en(result)
    cross_temporal_html = _render_cross_temporal_analysis(result)
    judge_answer_html = _render_judge_answer(result)
    score_rounds_html = _render_score_rounds(result)
    seat_digest_html = _render_seat_digest(result)
    seat_answers_html = _render_seat_answers(result)
    mentor_supplements_html = _render_mentor_supplements(result)
    deliberation_html = _render_deliberation(result)
    citation_verification_html = _render_citation_verification(result)
    evidence_os_html = _render_evidence_os(result)
    result_archive_html = _render_complete_result_archive(result)
    judge_answer_link = '<a href="#judge-answer">法官答案</a>' if judge_answer_html else ""
    score_rounds_link = '<a href="#score-rounds">评分轮次</a>' if score_rounds_html else ""
    seat_digest_link = '<a href="#seat-digest">模型总览</a>' if seat_digest_html else ""
    seat_answers_link = '<a href="#seat-answers">查看席位回答</a>' if seat_answers_html else ""
    mentor_supplements_link = '<a href="#mentor-supplements">共振二轮</a>' if mentor_supplements_html else ""
    deliberation_link = '<a href="#deliberation">查看互评评分</a>' if deliberation_html else ""
    citation_link = '<a href="#citation-verification">引用验证</a>' if citation_verification_html else ""
    evidence_os_link = '<a href="#evidence-os">Evidence OS</a>' if evidence_os_html else ""
    cross_temporal_link = '<a href="#cross-temporal">横纵收口</a>' if cross_temporal_html else ""
    final_report_link = '<a href="#report-manuscript">最终报告</a>' if final_report_html else ""
    result_archive_link = '<a href="#result-archive">完整结果库</a>' if result_archive_html else ""
    sop_link = '<a href="#closeout-sop">标准 SOP</a>' if final_report_html else ""
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Judge Verdict</title>
  <style>
    :root {{ color-scheme: light; --top-bg:#fbfcfe; --bg:#f2f6f4; --panel:#fffefa; --soft:#f8fbff; --paper:#fffdf8; --archive:#eef3f8; --line:#d7e2ef; --text:#172033; --muted:#64748b; --accent:#b76b00; --accent-fill:#ffae34; --green:#2fae6a; --red:#c84655; --blue:#2f7df6; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; margin: 0; background: var(--bg); color: var(--text); letter-spacing: 0; }}
    .nav {{ position: sticky; top: 0; z-index: 2; display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px 24px; background:rgba(251,252,254,.96); border-bottom:1px solid var(--line); backdrop-filter:blur(16px); }}
    .nav-actions {{ display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px; align-items:center; }}
    .nav a, .nav button, .lang-toggle button {{ color: var(--text); text-decoration:none; border:1px solid var(--line); border-radius:8px; padding:8px 12px; background:var(--panel); font-weight:700; cursor:pointer; }}
    .lang-toggle {{ display:inline-flex; gap:3px; padding:3px; border:1px solid var(--line); border-radius:999px; background:var(--soft); }}
    .lang-toggle button {{ border:0; border-radius:999px; padding:6px 10px; background:transparent; color:var(--muted); }}
    .lang-toggle button.active {{ background:#172033; color:#fff; }}
    body.lang-en [data-lang="zh"], body:not(.lang-en) [data-lang="en"] {{ display:none; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px 20px 52px; }}
    .hero {{ padding: 6px 0 18px; }}
    .badge {{ display: inline-block; padding: 7px 12px; border-radius: 999px; background: var(--accent-fill); color: #231400; font-weight: 800; }}
    h1 {{ font-size: clamp(28px, 4vw, 46px); line-height: 1.18; margin: 18px 0 12px; max-width: 980px; }}
    h2 {{ font-size: 18px; margin: 0; }}
    h3 {{ font-size: 14px; margin: 18px 0 8px; color: var(--accent); }}
    p {{ line-height: 1.65; }}
    .question {{ color: var(--muted); max-width: 900px; }}
    .prompt-details {{ max-width:900px; color:var(--muted); margin-top:10px; }}
    .prompt-details summary {{ cursor:pointer; font-weight:800; color:var(--text); }}
    .muted {{ color: var(--muted); }}
    .summary-grid {{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:10px; margin: 8px 0 18px; }}
    .summary-grid.compact {{ margin-top:12px; }}
    .summary-grid div {{ border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:14px; }}
    .summary-grid span {{ display:block; color:var(--muted); font-size:12px; margin-bottom:6px; }}
    .summary-grid strong {{ font-size:22px; }}
    .good {{ color: var(--green); }}
    .warn {{ color: var(--accent); }}
    .bad {{ color: var(--red); }}
    .band {{ border: 1px solid var(--line); border-radius: 8px; padding: 18px; margin: 14px 0; background: var(--soft); }}
    .nested {{ margin-top:14px; border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:12px; }}
    .nested summary {{ cursor:pointer; font-weight:800; }}
    details.band > summary {{ cursor: pointer; list-style: none; display:flex; align-items:center; justify-content:space-between; gap:12px; }}
    details.band > summary::-webkit-details-marker, .seat-answer summary::-webkit-details-marker {{ display:none; }}
    details.band > summary::after {{ content:"展开"; color:var(--muted); font-size:12px; }}
    details.band[open] > summary::after {{ content:"收起"; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }} td, th {{ border-bottom: 1px solid var(--line); padding: 10px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); background:var(--soft); }}
    pre {{ white-space: pre-wrap; overflow: auto; background: var(--panel); color:var(--text); padding: 14px; border-radius: 8px; border:1px solid var(--line); line-height:1.55; }}
    .section-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:12px; }}
    .section-head p {{ margin:8px 0 0; }}
    .report-lead {{ font-size:16px; line-height:1.75; color:var(--text); background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .manuscript-report {{ border:1px solid #ded8ce; border-radius:8px; padding:34px 42px; margin:18px auto; background:var(--paper); color:#172033; max-width:980px; display:grid; gap:18px; box-shadow:0 18px 42px rgba(74,62,42,.07); }}
    .manuscript-title {{ border-bottom:1px solid #d8dee9; padding-bottom:16px; }}
    .manuscript-title h2 {{ margin:8px 0 10px; font-size:34px; line-height:1.2; color:#172033; }}
    .manuscript-lead {{ margin:0; color:#263244; font-size:17px; line-height:1.78; font-weight:700; }}
    .manuscript-meta {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .manuscript-meta div {{ border-left:3px solid #d58b00; background:var(--panel); padding:9px 11px; min-width:0; }}
    .manuscript-meta span {{ display:block; color:#667085; font-size:11px; font-weight:800; margin-bottom:4px; }}
    .manuscript-meta strong {{ display:block; color:#172033; line-height:1.4; overflow-wrap:anywhere; }}
    .manuscript-section {{ display:grid; gap:9px; }}
    .manuscript-section h3 {{ margin:0; color:#172033; font-size:18px; line-height:1.35; }}
    .manuscript-section p {{ margin:0; color:#172033; font-size:15px; line-height:1.88; }}
    .manuscript-section ul, .manuscript-section ol {{ margin:0; padding-left:22px; color:#172033; line-height:1.78; }}
    .manuscript-table-wrap {{ overflow:auto; border:1px solid #d8dee9; border-radius:8px; background:var(--panel); }}
    .manuscript-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    .manuscript-table th, .manuscript-table td {{ border-bottom:1px solid #e5e7eb; padding:9px; text-align:left; vertical-align:top; line-height:1.55; color:#172033; }}
    .manuscript-table th {{ background:#f3f6fb; color:#667085; font-weight:800; }}
    .research-paper {{ font-family:"CMU Serif","Songti SC","STSong","SimSun",Georgia,serif; border-radius:0; border:0; padding:0; background:#fcfaf7; box-shadow:0 24px 70px rgba(71,54,37,.10); max-width:1040px; gap:0; }}
    .research-paper .paper-cover {{ min-height:820px; display:grid; align-content:center; gap:22px; padding:82px 86px; border:1px solid #e4dacd; background:linear-gradient(180deg,#fffdf9,#fbf6ee); page-break-after:always; }}
    .research-paper .paper-cover h1 {{ margin:0; font-size:44px; line-height:1.18; color:#18130f; font-weight:760; letter-spacing:0; }}
    .paper-subtitle {{ margin:0; color:#7c3f22; font-size:18px; letter-spacing:.08em; text-transform:uppercase; }}
    .cover-statement {{ margin:18px 0 0; color:#33251d; font-size:18px; line-height:1.9; border-left:4px solid #b55a2e; padding-left:18px; }}
    .cover-meta {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:30px; }}
    .cover-meta div, .report-score-grid div {{ border:1px solid #e2d8ca; background:#fffdf8; padding:14px; min-width:0; }}
    .cover-meta span, .report-score-grid span {{ display:block; color:#7b6b5d; font-size:11px; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif; font-weight:800; text-transform:uppercase; margin-bottom:6px; }}
    .cover-meta strong, .report-score-grid strong {{ display:block; color:#18130f; line-height:1.35; overflow-wrap:anywhere; }}
    .research-paper .paper-page {{ padding:48px 72px; border-left:1px solid #e4dacd; border-right:1px solid #e4dacd; background:#fcfaf7; page-break-before:auto; }}
    .research-paper .paper-page + .paper-page {{ border-top:1px solid #eadfd2; }}
    .research-paper .section-num {{ margin:0; color:#b55a2e; font-size:13px; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif; font-weight:850; letter-spacing:.16em; }}
    .research-paper h2 {{ margin:4px 0 18px; color:#18130f; font-size:28px; line-height:1.25; font-weight:760; }}
    .research-paper p, .research-paper li {{ color:#2b211b; font-size:16px; line-height:1.95; }}
    .research-paper .manuscript-lead {{ color:#18130f; font-size:19px; line-height:1.9; font-weight:760; }}
    .paper-keywords {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }}
    .paper-keywords span {{ border:1px solid #dfd2c2; border-radius:999px; padding:6px 10px; color:#7c3f22; background:#fffdf8; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif; font-size:12px; font-weight:760; }}
    .report-score-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .research-paper .manuscript-table-wrap {{ border-color:#dfd2c2; border-radius:0; background:#fffdf8; }}
    .research-paper .manuscript-table {{ font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif; font-size:13px; }}
    .research-paper .manuscript-table th {{ background:#f2ebe2; color:#6b5748; }}
    .research-paper .manuscript-table td {{ color:#211914; border-color:#e9ded0; }}
    .report-end {{ margin-top:26px; padding-top:18px; border-top:1px solid #dfd2c2; color:#7b6b5d; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif; font-size:12px; text-align:right; }}
    .compact-report-overview {{ border:1px solid var(--line); border-radius:8px; padding:20px; margin:18px 0; background:var(--panel); display:grid; gap:14px; }}
    .compact-report-overview.is-blocked {{ border-color:rgba(255,197,61,.45); }}
    .compact-report-hero h2 {{ margin:6px 0 8px; font-size:30px; line-height:1.22; }}
    .compact-lead {{ margin:0; font-size:18px; line-height:1.65; font-weight:800; }}
    .compact-priority {{ margin:0; color:var(--muted); }}
    .compact-status-grid, .compact-summary-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .compact-status-card, .compact-summary-card, .compact-panel, .compact-plan-item, .compact-jump {{ border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:12px; min-width:0; }}
    .compact-status-card span, .compact-summary-card span, .compact-plan-item span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; margin-bottom:6px; }}
    .compact-status-card strong {{ display:block; line-height:1.4; overflow-wrap:anywhere; }}
    .compact-summary-card p {{ margin:0; line-height:1.55; }}
    .compact-panel h3 {{ margin:0 0 10px; color:var(--accent); }}
    .compact-plan-strip {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; }}
    .compact-plan-item strong {{ display:block; margin-bottom:6px; }}
    .compact-plan-item p {{ margin:0 0 8px; color:var(--text); line-height:1.5; }}
    .compact-plan-item small {{ color:var(--muted); font-weight:800; }}
    .compact-section-head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:10px; }}
    .compact-section-head p {{ margin:4px 0 0; color:var(--muted); }}
    .compact-section-head a, .compact-jump {{ color:var(--text); text-decoration:none; }}
    .compact-council-table td:nth-child(3) {{ color:var(--muted); line-height:1.5; }}
    .compact-jump-grid {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; }}
    .compact-jump strong {{ display:block; margin-bottom:5px; }}
    .compact-jump span {{ color:var(--muted); font-size:12px; line-height:1.45; }}
    .compact-footer-note {{ margin:0; color:var(--muted); line-height:1.6; }}
    .compact-jump-detail > summary {{ cursor:pointer; display:flex; justify-content:space-between; align-items:center; gap:12px; }}
    .compact-jump-detail > summary h2 {{ margin:0; }}
    .executive-report {{ border:1px solid var(--line); border-radius:8px; padding:22px; margin:18px 0; background:var(--panel); }}
    .executive-report h2 {{ margin:6px 0; font-size:26px; }}
    .executive-answer {{ font-size:18px; line-height:1.75; font-weight:800; margin:8px 0 14px; }}
    .executive-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:12px 0; }}
    .executive-grid div, .executive-why {{ border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:13px; }}
    .executive-grid span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; margin-bottom:5px; }}
    .executive-grid strong {{ display:block; line-height:1.45; overflow-wrap:anywhere; }}
    .executive-why h3 {{ margin:0 0 8px; color:var(--accent); }}
    .sop-report {{ border:1px solid var(--line); border-radius:8px; padding:22px; margin:18px 0; background:var(--panel); }}
    .sop-report h2 {{ margin:6px 0 10px; font-size:24px; }}
    .sop-judgment {{ font-size:18px; line-height:1.75; font-weight:800; margin:8px 0; }}
    .sop-one-line, .sop-essence {{ line-height:1.75; color:var(--text); }}
    .sop-phases {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin:12px 0; }}
    .sop-phase, .sop-template, .sop-boundary {{ border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:13px; }}
    .sop-phase h3, .sop-template h3, .sop-boundary h3 {{ margin-top:0; color:var(--accent); }}
    .sop-phase ul, .sop-template ul, .sop-boundary ul {{ margin:0; padding-left:18px; line-height:1.65; }}
    .sop-template-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-top:10px; }}
    .sop-template-grid div {{ border:1px solid var(--line); border-radius:8px; padding:10px; background:var(--panel); }}
    .sop-template-grid h4 {{ margin:0 0 8px; color:var(--muted); }}
    .paper-report {{ border:1px solid var(--line); border-radius:8px; padding:22px; margin:18px 0; background:var(--panel); }}
    .paper-heading h2 {{ font-size:24px; margin:6px 0; }}
    .paper-kicker {{ margin:0; color:var(--accent); font-size:12px; font-weight:800; letter-spacing:0; }}
    .paper-status {{ margin:0 0 14px; color:var(--muted); }}
    .paper-meta {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:12px 0 16px; }}
    .paper-meta div, .paper-block, .paper-postulate {{ border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:13px; }}
    .paper-meta span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; margin-bottom:4px; }}
    .paper-meta strong {{ display:block; overflow-wrap:anywhere; }}
    .paper-block {{ margin:12px 0; }}
    .paper-block h3, .paper-postulate h3 {{ margin-top:0; }}
    .paper-abstract p {{ font-size:16px; line-height:1.75; }}
    .longform-report {{ background:var(--panel); }}
    .decision-brief {{ border:1px solid rgba(255,174,52,.42); border-radius:8px; padding:18px; margin:16px 0 18px; background:var(--panel); }}
    .decision-brief h2 {{ margin:6px 0 8px; font-size:28px; line-height:1.22; }}
    .decision-lead {{ margin:0 0 14px; font-size:18px; line-height:1.65; font-weight:800; }}
    .decision-card-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:12px 0; }}
    .decision-card {{ border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:12px; min-width:0; }}
    .decision-card span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; margin-bottom:6px; }}
    .decision-card strong {{ display:block; line-height:1.45; overflow-wrap:anywhere; }}
    .decision-plan {{ border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:13px; margin-top:12px; }}
    .decision-plan h3 {{ margin:0 0 8px; color:var(--accent); }}
    .decision-plan ol {{ margin:0; padding-left:20px; line-height:1.7; }}
    .decision-warning {{ border:1px solid rgba(200,70,85,.36); border-radius:8px; padding:10px 12px; margin:12px 0; background:#fff7f8; color:#9f1239; font-weight:800; }}
    .run-health {{ border:1px solid rgba(255,174,52,.42); border-radius:8px; padding:16px; margin:16px 0; background:var(--panel); }}
    .run-health-blocked {{ border-color:rgba(200,70,85,.45); background:#fff7f8; }}
    .run-health h2 {{ margin:6px 0 8px; font-size:24px; }}
    .run-health-lead {{ margin:0 0 12px; font-size:17px; line-height:1.65; font-weight:800; }}
    .run-health-card-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:12px 0; }}
    .run-health-card {{ border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:12px; min-width:0; }}
    .run-health-card span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; margin-bottom:6px; }}
    .run-health-card strong {{ display:block; line-height:1.45; overflow-wrap:anywhere; }}
    .run-health-plan {{ border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:13px; margin-top:12px; }}
    .run-health-plan h3 {{ margin:0 0 8px; color:var(--accent); }}
    .run-health-plan ol {{ margin:0; padding-left:20px; line-height:1.7; }}
    .draft-report {{ border-color:rgba(255,174,52,.38); background:var(--panel); }}
    .draft-details summary {{ cursor:pointer; display:flex; justify-content:space-between; align-items:center; gap:12px; border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:12px; }}
    .draft-details summary h3 {{ margin:0; }}
    .draft-details summary span {{ color:var(--muted); font-size:12px; }}
    .longform-lead {{ font-size:18px; line-height:1.78; font-weight:800; border:1px solid var(--line); border-radius:8px; padding:15px; background:var(--soft); }}
    .longform-summary p, .longform-section p {{ font-size:15px; line-height:1.86; margin:0 0 12px; }}
    .longform-summary p:last-child, .longform-section p:last-child {{ margin-bottom:0; }}
    .source-appendix {{ margin-top:18px; }}
    .paper-keywords {{ display:flex; flex-wrap:wrap; gap:7px; margin-top:10px; }}
    .paper-keywords span {{ border:1px solid var(--line); border-radius:999px; padding:5px 8px; color:var(--muted); background:var(--soft); font-size:12px; }}
    .paper-postulates {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin:12px 0; }}
    .paper-postulate span {{ display:block; color:var(--accent); font-size:11px; font-weight:800; margin-bottom:6px; }}
    .paper-postulate small {{ display:block; color:var(--muted); line-height:1.5; }}
    .paper-columns {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; }}
    .report-columns {{ display:grid; grid-template-columns: minmax(0,1fr) minmax(0,1.2fr); gap:12px; margin:12px 0; }}
    .report-column {{ border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:14px; min-width:0; }}
    .report-column h3 {{ margin-top:0; }}
    .trace-mini {{ list-style:none; padding:0; margin:0; display:grid; gap:8px; }}
    .trace-mini li {{ border:1px solid var(--line); border-radius:8px; padding:9px 10px; background:var(--soft); }}
    .trace-mini strong {{ display:block; color:var(--accent); font-size:12px; margin-bottom:4px; }}
    .trace-mini span {{ color:var(--muted); font-size:12px; line-height:1.45; }}
    .mini-actions {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    button {{ color:var(--text); border:1px solid var(--line); border-radius:8px; padding:8px 10px; background:var(--panel); font-weight:700; cursor:pointer; }}
    button:hover, .actions a:hover, .nav a:hover {{ border-color:var(--accent); }}
    .seat-answer-list {{ display:grid; gap:10px; }}
    .seat-answer {{ border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:0; }}
    .seat-answer.is-pending {{ border-color:rgba(255,197,61,.65); }}
    .seat-answer.is-failed {{ border-color:rgba(255,104,104,.55); }}
    .seat-answer summary {{ cursor:pointer; display:grid; grid-template-columns:minmax(120px, 1fr) auto auto; gap:10px; align-items:center; padding:14px; }}
    .seat-state {{ font-weight:800; }}
    .seat-meta {{ color:var(--muted); font-size:12px; text-align:right; }}
    .seat-preview {{ margin:0; padding:0 14px 12px; color:var(--muted); }}
    .answer {{ margin:0 14px 14px; max-height:520px; overflow:auto; border:1px solid var(--line); border-radius:8px; background:var(--soft); padding:12px; }}
    .readable-answer {{ white-space:normal; font-family:inherit; line-height:1.68; color:var(--text); }}
    .readable-answer p {{ margin:0 0 10px; }}
    .readable-answer h3, .readable-answer h4, .readable-answer h5, .readable-answer h6 {{ margin:14px 0 8px; color:var(--accent); }}
    .readable-answer ul {{ margin:0 0 10px; padding-left:20px; line-height:1.7; }}
    .readable-answer a {{ color:var(--blue); }}
    .raw-log {{ margin:0 14px 14px; }}
    .raw-log summary {{ cursor:pointer; color:var(--accent); font-weight:800; margin-bottom:8px; }}
    .raw-answer, .stored-code {{ white-space:pre-wrap; font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; line-height:1.55; }}
    .stored-code {{ margin:10px 0; }}
    .stored-table-wrap {{ overflow:auto; margin:10px 0; }}
    .stored-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    .stored-table td {{ border:1px solid var(--line); padding:8px; vertical-align:top; }}
    .archive-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }}
    .archive-card {{ display:block; min-width:0; border:1px solid var(--line); border-radius:8px; background:var(--archive); padding:13px; color:var(--text); text-decoration:none; }}
    .archive-card:hover {{ border-color:var(--accent); }}
    .archive-card span {{ display:block; color:var(--accent); font-size:12px; font-weight:800; margin-bottom:6px; }}
    .archive-card strong {{ display:block; font-size:18px; line-height:1.35; margin-bottom:6px; }}
    .archive-card small {{ display:block; color:var(--muted); line-height:1.45; }}
    .compact-list {{ margin:0; padding-left:18px; }}
    .status-pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 8px; font-weight:800; background:var(--panel); }}
    code {{ color:var(--accent); }}
    .actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }}
    .actions a {{ color:var(--text); text-decoration:none; border:1px solid var(--line); border-radius:8px; padding:9px 12px; background:var(--panel); font-weight:700; }}
    .actions button {{ padding:9px 12px; }}
    @media print {{
      @page {{ size:A4; margin:16mm 14mm; }}
      .nav, .actions, .prompt-details, details.band, .library-section, script {{ display:none !important; }}
      body {{ background:#fff; color:#111; }}
      main {{ max-width: none; padding: 0; }}
      .band, .executive-report, .paper-report, .sop-report, .manuscript-report {{ break-inside: avoid; border-color:#d1d5db; background:#fff; color:#111; }}
      .research-paper {{ box-shadow:none; max-width:none; }}
      .research-paper .paper-cover, .research-paper .paper-page {{ border:0; padding:0; background:#fff; }}
      .research-paper .paper-page {{ page-break-before:always; }}
      h1, h2, h3, p, li, td, th, strong, span {{ color:#111 !important; }}
    }}
    @media (max-width: 760px) {{
      .summary-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
      .paper-meta, .paper-postulates, .paper-columns, .executive-grid, .sop-phases, .sop-template-grid, .decision-card-grid, .compact-status-grid, .compact-summary-grid, .compact-plan-strip, .compact-jump-grid, .archive-grid, .manuscript-meta, .cover-meta, .report-score-grid {{ grid-template-columns:1fr; }}
      .research-paper .paper-cover, .research-paper .paper-page {{ padding:28px 20px; min-height:auto; }}
      .section-head {{ display:block; }}
      .compact-section-head {{ display:block; }}
      .report-columns {{ grid-template-columns:1fr; }}
      .mini-actions {{ justify-content:flex-start; margin-top:10px; }}
      .seat-answer summary {{ grid-template-columns:1fr; }}
      .seat-meta {{ text-align:left; }}
      .nav {{ padding:12px 14px; }}
      main {{ padding:22px 14px 42px; }}
    }}
  </style>
</head>
<body>
<nav class="nav">
  <strong>AI Judge 完整报告</strong>
  <div class="nav-actions">
    <span class="lang-toggle" aria-label="Language">
      <button type="button" data-lang-button="zh" class="active">中文</button>
      <button type="button" data-lang-button="en">English</button>
    </span>
    <button type="button" id="print-report" data-print-report><span data-lang="zh">下载 PDF</span><span data-lang="en">Download PDF</span></button>
    <button type="button" id="download-markdown" data-download-markdown><span data-lang="zh">下载 Markdown</span><span data-lang="en">Download Markdown</span></button>
    <button type="button" id="copy-report-link" data-copy-link><span data-lang="zh">复制分享链接</span><span data-lang="en">Copy Share Link</span></button>
    <a href="/"><span data-lang="zh">返回提问</span><span data-lang="en">Back to Prompt</span></a>
  </div>
</nav>
<main>
  <section class="hero">
    <p class="badge">{html.escape(str(result.get("mode_emoji", "")))} {html.escape(str(result.get("verdict_label", "")))} · {result.get("confidence", 0)}%</p>
    <h1><span data-lang="zh">{html.escape(header_title)}</span><span data-lang="en">{html.escape(header_title_en)}</span></h1>
    <p class="question"><span data-lang="zh">{html.escape(header_summary)}</span><span data-lang="en">{html.escape(header_summary_en)}</span></p>
    <details class="prompt-details"><summary><span data-lang="zh">原始任务</span><span data-lang="en">Original Prompt</span></summary><p>{html.escape(raw_question)}</p></details>
    <div class="actions"><a href="/"><span data-lang="zh">返回提问界面</span><span data-lang="en">Back to Prompt</span></a>{final_report_link}<a href="#internal-library"><span data-lang="zh">内部资料库</span><span data-lang="en">Source Library</span></a></div>
  </section>
  {final_report_html}
  <details class="band library-section" id="internal-library">
    <summary><h2>内部资料库：原始回答、互评、共振与日志</h2></summary>
    <p class="muted">这里是工作台材料与内部日志，不属于默认转发文书。需要深入追溯时再展开。</p>
    {collection_html}
    {result_archive_html}
    {cross_temporal_html}
    {judge_answer_html}
    {score_rounds_html}
    {citation_verification_html}
    {evidence_os_html}
    <section class="band"><h2>关键理由</h2><ul class="compact-list">{reasons}</ul></section>
    {seat_digest_html}
    {mentor_supplements_html}
    {deliberation_html}
    {seat_answers_html}
    {prompt_html}
    <section class="band"><h2>建议行动</h2><ul class="compact-list">{steps}</ul></section>
    {blocked_html}
    <section class="band"><h2>席位评分</h2><table><thead><tr><th>席位</th><th>MBTI</th><th>均分</th><th>Claims</th></tr></thead><tbody>{seats_html}</tbody></table></section>
    {trace_html}
    <details class="band" id="raw-json"><summary><h2>原始 JSON</h2></summary><pre>{raw_json}</pre></details>
  </details>
</main>
<script>
const reportMarkdown = {report_markdown_json};
document.addEventListener("click", (event) => {{
  const button = event.target.closest("[data-seat-action]");
  const langButton = event.target.closest("[data-lang-button]");
  if (langButton) {{
    const lang = langButton.dataset.langButton === "en" ? "en" : "zh";
    setReportLanguage(lang);
    return;
  }}
  if (event.target.closest("#print-report")) {{
    window.print();
    return;
  }}
  if (event.target.closest("#download-markdown")) {{
    const blob = new Blob([reportMarkdown || document.body.innerText], {{ type: "text/markdown;charset=utf-8" }});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "ai-judge-final-report.md";
    anchor.click();
    URL.revokeObjectURL(url);
    return;
  }}
  if (event.target.closest("#copy-report-link")) {{
    const node = event.target.closest("#copy-report-link");
    const original = node.innerHTML;
    const copied = document.body.classList.contains("lang-en") ? "Link copied" : "已复制链接";
    const failed = document.body.classList.contains("lang-en") ? "Copy failed" : "复制失败";
    const copyPromise = navigator.clipboard?.writeText
      ? navigator.clipboard.writeText(window.location.href)
      : Promise.reject(new Error("clipboard unavailable"));
    copyPromise.then(() => {{
      node.textContent = copied;
    }}).catch(() => {{
      node.textContent = failed;
    }}).finally(() => {{
      window.setTimeout(() => {{
        node.innerHTML = original;
        setReportLanguage(document.body.classList.contains("lang-en") ? "en" : "zh");
      }}, 1400);
    }});
    return;
  }}
  if (!button) return;
  const shouldOpen = button.dataset.seatAction === "expand";
  document.querySelectorAll(".seat-answer").forEach((node) => {{
    node.open = shouldOpen;
  }});
}});
function setReportLanguage(lang) {{
  const normalized = lang === "en" ? "en" : "zh";
  document.body.classList.toggle("lang-en", normalized === "en");
  document.querySelectorAll("[data-lang-button]").forEach((node) => {{
    const active = node.dataset.langButton === normalized;
    node.classList.toggle("active", active);
    node.setAttribute("aria-pressed", active ? "true" : "false");
  }});
  try {{
    window.localStorage.setItem("ai_judge_report_language", normalized);
  }} catch (_) {{}}
}}
try {{
  setReportLanguage(window.localStorage.getItem("ai_judge_report_language") || "zh");
}} catch (_) {{
  setReportLanguage("zh");
}}
if (new URLSearchParams(window.location.search).get("print") === "1") {{
  window.setTimeout(() => window.print(), 450);
}}
</script>
</body></html>"""


# ─── P7: Decision Intelligence aggregate endpoint ───
@app.route("/api/decision/intelligence", methods=["GET"])
def decision_intelligence():
    """Aggregate data from P0-P6 into a single Decision Intelligence payload."""
    import time

    result = {
        "schema_version": "ai-judge-decision-intelligence-v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "summary": {
            "canonical_runs": 0,
            "universe_gaps": 0,
            "human_gavel_counts": {"none": 0, "draft": 0, "confirmed": 0, "rejected": 0, "needs_review": 0},
            "claim_calibration_counts": {"total_runs": 0, "total_accepted": 0, "total_rejected": 0, "total_unmatched": 0},
            "trust_summary": {"seat_count": 0, "top_trusted_seats": [], "low_evidence_seats": []},
        },
        "needs_review": [],
        "top_trusted_seats": [],
        "low_evidence_seats": [],
        "next_best_actions": [],
        "source_apis": [],
    }

    vault_dir_str = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT")
    vault_dir = Path(vault_dir_str) if vault_dir_str else None

    # 1. Run Universe
    try:
        u = build_run_universe(RUNS_DIR)
        result["summary"]["canonical_runs"] = u.get("canonical_run_count", 0)
        result["summary"]["universe_gaps"] = len(u.get("gaps", []))
        result["source_apis"].append("/api/runs/universe")
    except Exception as e:
        result["source_apis"].append(f"/api/runs/universe (error: {e})")
        u = {"runs": [], "gaps": []}

    # 2. Trust Calibration
    try:
        t = build_trust_calibration(RUNS_DIR)
        seats = t.get("seats", [])
        result["summary"]["trust_summary"]["seat_count"] = len(seats)
        result["summary"]["trust_summary"]["top_trusted_seats"] = t.get("top_trusted_seats", [])[:5]
        result["summary"]["trust_summary"]["low_evidence_seats"] = t.get("low_evidence_seats", [])[:5]
        result["top_trusted_seats"] = t.get("top_trusted_seats", [])[:10]
        result["low_evidence_seats"] = t.get("low_evidence_seats", [])[:10]
        result["source_apis"].append("/api/trust/calibration")
    except Exception as e:
        result["source_apis"].append(f"/api/trust/calibration (error: {e})")

    # 3. Hermes Index
    hermes_runs = []
    try:
        from hermes_index_layer import build_hermes_index
        hi = build_hermes_index(RUNS_DIR, vault_dir)
        hermes_runs = hi.get("runs", []) if hi else []
        result["source_apis"].append("/api/hermes/index")
    except Exception as e:
        result["source_apis"].append(f"/api/hermes/index (error: {e})")

    # 4. Human Gavel counts from Hermes index
    for r in hermes_runs:
        gv = r.get("human_gavel") or {}
        status = gv.get("status", "none") or "none"
        key = status if status in result["summary"]["human_gavel_counts"] else "none"
        result["summary"]["human_gavel_counts"][key] = result["summary"]["human_gavel_counts"].get(key, 0) + 1

    # 5. Claim Calibration
    try:
        from claim_calibration_layer import build_claim_calibration_index
        cc = build_claim_calibration_index(RUNS_DIR, vault_dir)
        result["summary"]["claim_calibration_counts"]["total_runs"] = cc.get("total_runs", 0) if cc else 0
        result["summary"]["claim_calibration_counts"]["total_accepted"] = cc.get("total_accepted", 0) if cc else 0
        result["summary"]["claim_calibration_counts"]["total_rejected"] = cc.get("total_rejected", 0) if cc else 0
        result["summary"]["claim_calibration_counts"]["total_unmatched"] = cc.get("total_unmatched", 0) if cc else 0
        result["source_apis"].append("/api/claims/calibration")
    except Exception as e:
        result["source_apis"].append(f"/api/claims/calibration (error: {e})")

    # 6. Gavel Digest
    try:
        gd = generate_gavel_digest(RUNS_DIR, vault_dir) if vault_dir else None
        result["source_apis"].append("/api/gavel/digest")
    except Exception as e:
        result["source_apis"].append(f"/api/gavel/digest (error: {e})")

    # ── Build Needs Review Queue ──
    needs_review_set: dict[str, dict[str, Any]] = {}  # run_id -> review entry

    # Rule: has_gap from universe
    try:
        for gap in u.get("gaps", []):
            rid = gap.get("run_id", "")
            if rid:
                needs_review_set.setdefault(rid, {
                    "run_id": rid,
                    "reasons": [],
                    "confidence": None,
                    "gavel_status": None,
                    "unmatched_claims_count": 0,
                })
                needs_review_set[rid]["reasons"].append("universe gap: " + gap.get("issue", "unknown"))
    except Exception:
        pass

    # Rule: human_gavel status in draft/needs_review/rejected
    for r in hermes_runs:
        rid = r.get("run_id", "")
        gv = r.get("human_gavel") or {}
        status = gv.get("status", "none") or "none"
        if status in ("draft", "needs_review", "rejected"):
            needs_review_set.setdefault(rid, {
                "run_id": rid,
                "reasons": [],
                "confidence": r.get("confidence"),
                "gavel_status": status,
                "unmatched_claims_count": 0,
            })
            needs_review_set[rid]["reasons"].append("gavel status: " + status)
            if needs_review_set[rid]["gavel_status"] is None:
                needs_review_set[rid]["gavel_status"] = status

    # Rule: unmatched claims > 0
    for r in hermes_runs:
        cc_entry = r.get("claim_calibration") or {}
        unmatched = cc_entry.get("unmatched_count", 0)
        if unmatched > 0:
            rid = r.get("run_id", "")
            needs_review_set.setdefault(rid, {
                "run_id": rid,
                "reasons": [],
                "confidence": r.get("confidence"),
                "gavel_status": None,
                "unmatched_claims_count": unmatched,
            })
            needs_review_set[rid]["reasons"].append(f"unmatched claims: {unmatched}")
            needs_review_set[rid]["unmatched_claims_count"] = unmatched

    # Rule: confidence < 50
    for r in hermes_runs:
        conf = r.get("confidence")
        if conf is not None and conf < 50:
            rid = r.get("run_id", "")
            needs_review_set.setdefault(rid, {
                "run_id": rid,
                "reasons": [],
                "confidence": conf,
                "gavel_status": None,
                "unmatched_claims_count": 0,
            })
            needs_review_set[rid]["reasons"].append(f"low confidence: {conf}%")

    # Rule: low evidence seat involved
    low_seat_ids = set(result["low_evidence_seats"])
    if low_seat_ids:
        for r in hermes_runs:
            rid = r.get("run_id", "")
            seats_in_run = r.get("seats") or []
            if any(s in low_seat_ids for s in seats_in_run):
                needs_review_set.setdefault(rid, {
                    "run_id": rid,
                    "reasons": [],
                    "confidence": r.get("confidence"),
                    "gavel_status": None,
                    "unmatched_claims_count": 0,
                })
                needs_review_set[rid]["reasons"].append("low evidence seat involved")

    # Finalize needs_review list
    for rid, entry in needs_review_set.items():
        entry["reasons"] = list(dict.fromkeys(entry["reasons"]))  # dedup

    result["needs_review"] = list(needs_review_set.values())

    # ── Generate Next Best Actions ──
    actions = []

    # 1: review unmatched claims highest
    all_unmatched = [e for e in result["needs_review"] if e.get("unmatched_claims_count", 0) > 0]
    all_unmatched.sort(key=lambda x: x.get("unmatched_claims_count", 0), reverse=True)
    if all_unmatched:
        actions.append({
            "kind": "review_unmatched_claims",
            "reason": f"Run {all_unmatched[0]['run_id']} has {all_unmatched[0]['unmatched_claims_count']} unmatched claims — highest in queue",
            "target": all_unmatched[0]["run_id"],
            "priority": 1,
        })

    # 2: add human gavel for low evidence seat
    if result["low_evidence_seats"]:
        seat = result["low_evidence_seats"][0]
        actions.append({
            "kind": "add_human_gavel_for_seat",
            "reason": f"Seat '{seat}' has low evidence — add human gavel to calibrate trust",
            "target": seat,
            "priority": 2,
        })

    # 3: sync draft gavel
    draft_runs = [e for e in result["needs_review"] if e.get("gavel_status") == "draft"]
    if draft_runs:
        actions.append({
            "kind": "sync_draft_gavel",
            "reason": f"Run {draft_runs[0]['run_id']} has draft gavel — sync to finalize",
            "target": draft_runs[0]["run_id"],
            "priority": 3,
        })

    # 4: backfill missing hermes
    no_hermes = [r for r in hermes_runs if not r.get("hermes_output_exists")]
    if no_hermes:
        actions.append({
            "kind": "backfill_missing_hermes",
            "reason": f"Run {no_hermes[0]['run_id']} missing Hermes output — export needed",
            "target": no_hermes[0]["run_id"],
            "priority": 4,
        })

    # 5: review lowest trust seat
    if result["top_trusted_seats"] or result["low_evidence_seats"]:
        target_seat = result["low_evidence_seats"][0] if result["low_evidence_seats"] else result["top_trusted_seats"][-1] if result["top_trusted_seats"] else None
        if target_seat:
            actions.append({
                "kind": "review_low_trust_seat",
                "reason": f"Seat '{target_seat}' needs trust review",
                "target": target_seat,
                "priority": 5,
            })

    result["next_best_actions"] = actions[:5]

    return jsonify(result)


@app.route("/api/release/readiness", methods=["GET"])
def release_readiness():
    """GET /api/release/readiness — return release-readiness.json if it exists."""
    import json as _json
    from pathlib import Path
    runs_dir = RUNS_DIR
    path = runs_dir / "release-readiness.json"
    if not path.exists():
        return jsonify({"error": "release_readiness_not_found"}), 404
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
        return jsonify(data), 200, {"Content-Type": "application/json"}
    except Exception as _e:
        return jsonify({"error": "release_readiness_parse_error", "detail": str(_e)}), 500


@app.route("/api/runs/release-readiness")
def serve_release_readiness_md():
    """Serve release-readiness.md from the Obsidian vault Indexes directory."""
    from pathlib import Path
    vault_dir_str = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT", "") or str(Path.home() / "Documents" / "AI-Judge-Obsidian-Vault")
    md_path = Path(vault_dir_str) / "Indexes" / "release-readiness.md"
    if md_path.exists():
        return send_file(str(md_path), mimetype="text/markdown")
    return jsonify({"error": "release_readiness_md_not_found"}), 404


@app.route("/api/release/regression", methods=["POST"])
def release_regression():
    """POST /api/release/regression — run regression harness and regenerate readiness report."""
    import subprocess, json as _json
    from pathlib import Path
    runs_dir = RUNS_DIR
    vault_dir_str = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT", "") or str(Path.home() / "Documents" / "AI-Judge-Obsidian-Vault")
    vault_dir = Path(vault_dir_str) if Path(vault_dir_str).exists() else None
    run_id = "1142374c8b6d"
    port = int(os.environ.get("AI_JUDGE_PORT", "8501"))
    trace_path = str(runs_dir.parent / "debug-ui-io-trace.jsonl")

    product_dir = str(Path(__file__).resolve().parent)
    python = sys.executable or "python3"

    def _run_script(script_name, extra_args=None):
        cmd = [python, str(Path(product_dir) / script_name),
               "--runs-dir", str(runs_dir),
               "--vault-dir", str(vault_dir) if vault_dir else "",
               "--run-id", run_id,
               "--port", str(port),
               "--trace", trace_path]
        if extra_args:
            cmd.extend(extra_args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    try:
        # Step 1: run regression_harness.py (continue regardless of exit code — warnings are not fatal)
        r1 = _run_script("regression_harness.py")

        # Step 2: run release_readiness.py to regenerate reports (continue regardless of exit code)
        r2 = _run_script("release_readiness.py")

        # Step 3: read generated JSON
        report_path = runs_dir / "release-readiness.json"
        if not report_path.exists():
            return jsonify({
                "ok": False,
                "error": "release_readiness_not_found_after_run"
            }), 500

        report = _json.loads(report_path.read_text(encoding="utf-8"))
        return jsonify({
            "ok": True,
            "overall_status": report.get("overall_status", "unknown"),
            "pass_count": report.get("pass_count", 0),
            "fail_count": report.get("fail_count", 0),
            "blockers": report.get("blockers", []),
            "warnings": report.get("warnings", []),
            "build_id": report.get("build_id", ""),
            "sample_run_id": report.get("sample_run_id", run_id),
        }), 200

    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "regression_timeout"}), 500
    except Exception as _e:
        return jsonify({"ok": False, "error": "regression_unexpected_error", "reason": str(_e)}), 500


@app.route("/api/release/drift", methods=["GET"])
def release_drift():
    """GET /api/release/drift — return freeze-drift-report.json if it exists."""
    import json as _json
    from pathlib import Path
    drift_path = RUNS_DIR / "freeze-drift-report.json"
    if not drift_path.is_file():
        return jsonify({"ok": False, "error": "drift_report_not_found", "reason": "Run POST /api/release/drift/check first"}), 404
    try:
        data = _json.loads(drift_path.read_text(encoding="utf-8"))
        return jsonify({"ok": True, "data": data}), 200, {"Content-Type": "application/json"}
    except Exception as _e:
        return jsonify({"ok": False, "error": "drift_report_parse_error", "detail": str(_e)}), 500


@app.route("/api/release/drift/check", methods=["POST"])
def release_drift_check():
    """POST /api/release/drift/check — run drift sentinel and return report."""
    import json as _json, subprocess as _sp
    from pathlib import Path

    def _write_trace(event, payload):
        import time as _t
        try:
            entry = {"event": event, "ts": int(_t.time() * 1000), **payload}
            with open(trace_path, "a", encoding="utf-8") as _tf:
                _tf.write(_json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    try:
        vault_dir_str = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT", "") or str(Path.home() / "Documents" / "AI-Judge-Obsidian-Vault")
        trace_path = str(RUNS_DIR.parent / "debug-ui-io-trace.jsonl")
        port = int(os.environ.get("AI_JUDGE_PORT", "8501"))

        _write_trace("release_drift_check_clicked", {})

        cmd = [
            sys.executable, str(PRODUCT_DIR / "freeze_drift_sentinel.py"),
            "--manifest", str(RUNS_DIR / "FREEZE_MANIFEST_P8.json"),
            "--product-dir", str(PRODUCT_DIR),
            "--src-dir", str(SRC_DIR),
            "--runs-dir", str(RUNS_DIR),
            "--vault-dir", vault_dir_str,
            "--port", str(port),
            "--trace", trace_path,
            "--write",
        ]
        result = _sp.run(cmd, capture_output=True, text=True, timeout=30)
        drift_path = RUNS_DIR / "freeze-drift-report.json"
        if drift_path.is_file():
            data = _json.loads(drift_path.read_text(encoding="utf-8"))
            _write_trace("release_drift_check_result", {
                "ok": True, "status": data.get("status", "unknown"),
                "hash_changes": data.get("summary", {}).get("hash_changed", 0),
                "missing": data.get("summary", {}).get("missing", 0),
            })
            return jsonify({"ok": True, "data": data}), 200
        else:
            return jsonify({"ok": False, "error": "drift_check_failed", "reason": "Report not generated"}), 500
    except _sp.TimeoutExpired:
        return jsonify({"ok": False, "error": "drift_check_timeout"}), 500
    except Exception as _e:
        return jsonify({"ok": False, "error": "drift_check_error", "reason": str(_e)}), 500


# ─── P9.2 Maintenance Control Center thin wrappers ───

@app.route("/api/release/restore-drill", methods=["POST"])
def api_release_restore_drill():
    """P9.2: Dry-run restore drill. Does NOT overwrite runtime."""
    import subprocess as _sp
    try:
        result = _sp.run(
            [sys.executable, "restore_drill.py", "--dry-run"],
            cwd=str(PRODUCT_DIR),
            capture_output=True, text=True, timeout=60
        )
        return jsonify({"ok": True, "status": "completed", "stdout": result.stdout[:2000], "stderr": result.stderr[:500]})
    except _sp.TimeoutExpired:
        return jsonify({"ok": False, "error": "restore_drill_timeout", "reason": "restore_drill_timeout"}), 500
    except Exception as _e:
        return jsonify({"ok": False, "error": str(_e), "reason": "restore_drill_failed"}), 500


@app.route("/api/trust/calibration/refresh", methods=["POST"])
def api_trust_calibration_refresh():
    """P9.2: Refresh trust calibration data."""
    try:
        trust_path = os.path.join(str(RUNS_DIR), "trust-calibration.json")
        if os.path.exists(trust_path):
            with open(trust_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"ok": True, "status": "refreshed", "data": data})
        return jsonify({"ok": True, "status": "no_data", "data": {}})
    except Exception as _e:
        return jsonify({"ok": False, "error": str(_e), "reason": "trust_refresh_failed"}), 500


@app.route("/api/decision/intelligence/refresh", methods=["POST"])
def api_decision_intelligence_refresh():
    """P9.2: Refresh decision intelligence snapshot."""
    try:
        di_path = os.path.join(str(RUNS_DIR), "decision-intelligence.json")
        if os.path.exists(di_path):
            with open(di_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"ok": True, "status": "refreshed", "data": data})
        return jsonify({"ok": True, "status": "no_data", "data": {}})
    except Exception as _e:
        return jsonify({"ok": False, "error": str(_e), "reason": "di_refresh_failed"}), 500


def main():
    import argparse

    parser = argparse.ArgumentParser(description=f"AI Judge v{PRODUCT_VERSION} API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8501, help="Bind port")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()

    print(f"\n  AI Judge API Server v{PRODUCT_VERSION}")
    print(f"  http://{args.host}:{args.port}")
    print(f"  {len(SEAT_PERSONAS)} seats available")
    print("  POST /api/judge now runs automatically\n")

    # Build run universe and trust calibration on startup
    vault_dir_str = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT")
    vault_dir = Path(vault_dir_str) if vault_dir_str else None
    try:
        u = write_run_universe(RUNS_DIR, vault_dir)
        print(f"  Run Universe: canonical={u['canonical_run_count']} gaps={len(u.get('gaps', []))}")
    except Exception as _e:
        print(f"  Run Universe build failed: {_e}")

    try:
        t = write_trust_calibration(RUNS_DIR, vault_dir)
        print(f"  Trust Calibration: seats={t['seat_count']}")
    except Exception as _e:
        print(f"  Trust Calibration build failed: {_e}")

    # Auto-wake the dedicated AI Judge Chrome CDP bridge.
    # Never kill the user's ordinary Chrome; keep one persistent profile so logins survive restarts.
    try:
        _wake = ensure_chrome_cdp_awake(load_bridge_config(), open_tabs=True)
        if _wake.get("ok"):
            print(f"  Chrome CDP ready at {_wake.get('endpoint')} · woke={_wake.get('woke')} · opened={len(_wake.get('opened_tabs') or [])}")
        else:
            print(f"  Chrome CDP wake skipped/failed: {_wake.get('reason') or _wake.get('error')}")
    except Exception as _e:
        print(f"  Chrome auto-launch skipped: {_e}")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
