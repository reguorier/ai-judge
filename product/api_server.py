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
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

try:
    from flask_cors import CORS
except Exception:  # pragma: no cover - optional dependency
    CORS = None

from bridges.notification_gateway import generate_secure_view_url, notify_verdict_ready, verify_secure_view
from bridges.chrome_fixed_tab_bridge import recover_existing_fixed_tab_answers
from bridges.web_seat_bridge import bridge_status, calibrate_bridge, load_bridge_config, write_default_config
from core.async_task_manager import TaskManager
from core.auto_jury import format_verdict_markdown, run_auto_jury
from core.blind_cross_validation import aggregate_blind_reviews, build_blind_cross_validation_packet
from core.cross_temporal_analysis import attach_cross_temporal_analysis
from core.evidence_broker import build_evidence_broker_report
from core.evidence_gap_filler import suggest_evidence_gaps
from core.evidence_gap_queue import build_evidence_gap_queue, resolve_gap_task
from core.eval_dataset import build_eval_case_from_verdict, collect_eval_cases
from core.eval_metrics import compute_evidence_quality_metrics
from core.execution_drivers import build_bridge_blocked_verdict, decide_execution
from core.final_report import attach_final_report, build_final_report, render_final_report_html
from core.grand_judge import run_grand_judge_mvp
from core.human_review import human_review_status, sign_human_review
from core.modes import list_modes, resolve_mode
from core.prompt_resonance import build_prompt_flow
from core.run_trace import RunTrace, load_trace
from core.seat_execution_policy import (
    annotate_execution_results,
    execution_policy_summary,
)
from core.seat_personas import SEAT_PERSONAS
from core.web_jury import assemble_web_verdict_from_raw_results, run_web_jury


app = Flask(__name__)
if CORS:
    CORS(app)

PRODUCT_VERSION = "3.8.0"
PRODUCT_NAME = "AI Judge Trust Workbench"
TASKS = TaskManager()
RUNS_DIR = _PROJECT_ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)
PRODUCT_DIR = _PROJECT_ROOT / "product"
STALE_TASK_SECONDS = 90
AUTO_REQUIRED_RECOVERY_ATTEMPTS = 2
AUTO_REQUIRED_RECOVERY_WAIT_SECONDS = 6
WAITING_STEP_RE = re.compile(r"(?:等待\s*(?P<labels>[^，]+)，)?剩余\s*(?P<count>\d+)\s*席，最长等待\s*(?P<seconds>\d+)s")
RETRY_STEP_RE = re.compile(r"补跑\s*(?P<attempt>\d+)\s*/\s*(?P<total>\d+)")
RECOVERABLE_WEB_CODES = {
    "slow_response_pending",
    "response_timeout",
    "send_button_not_found",
    "submit_unconfirmed",
    "chrome_submit_unconfirmed",
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
    "long_prompt_still_in_input",
    "input_not_found",
    "fixed_tab_not_found",
    "page_error",
    "model_page_error",
    "chrome_crash",
    "blank_page",
    "page_recovery_failed",
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
            "limits": ["本地快答使用结构化席位画像模拟，不等同于网页模型原文收集。"],
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
                {"metric": "答案来源", "single_judge": chief["name"], "council": f"{len(selected)} 个本地席位"},
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
) -> None:
    trace = RunTrace(run_id)
    abstained_seats = abstained_seats or []
    external_evidence = external_evidence or []
    evidence_options = evidence_options or {}

    def trace_event(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        trace.add(phase=phase, action=action, detail=detail, data=data)
        trace.write(_trace_path(run_id))

    try:
        trace_event("request", "accepted", "API 已接收任务并进入后台 worker", {
            "question_chars": len(question),
            "mode": mode,
            "engine": engine,
            "seats": seats,
            "chief_judge": chief_judge,
            "abstained_seats": abstained_seats,
            "external_evidence_count": len(external_evidence),
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
        TASKS.update_progress(run_id, "受理完成，本地共振对齐", 0.06)
        if engine == "web":
            status = bridge_status()
            prompt_flow = build_prompt_flow(question, mode=mode, engine=engine, seats=seats, bridge_summary=status)
            trace_event("resonance", "prompt_flow_built", "本地共振已生成专业提示词", {
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

                verdict = run_web_jury(
                    question=prompt_flow["professional_prompt"],
                    mode=mode,
                    seats=runnable_seats,
                    run_id=run_id,
                    display_question=question,
                    external_evidence=external_evidence,
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
                    external_evidence=external_evidence,
                    evidence_options=evidence_options,
                    trace_event=trace_event,
                    update_progress=lambda step, pct: TASKS.update_progress(run_id, step, pct),
                )
        else:
            prompt_flow = build_prompt_flow(question, mode=mode, engine=engine, seats=seats)
            execution_plan = decide_execution(engine=engine, mode=mode, requested_seats=seats)
            trace_event("resonance", "prompt_flow_built", "本地共振已生成专业提示词", {
                "intent": prompt_flow.get("intent"),
                "trace_id": prompt_flow.get("trace_id"),
                "professional_prompt_chars": len(prompt_flow.get("professional_prompt", "")),
            })
            trace_event("router", "execution_plan", "本地执行驱动已确认", execution_plan)
            total = max(1, len(seats))
            for index, seat in enumerate(seats, 1):
                trace_event("seat", "local_infer", f"本地席位推理：{seat}", {"seat": seat, "index": index, "total": total})
                TASKS.update_progress(run_id, f"本地席位推理：{seat} ({index}/{total})", 0.10 + 0.55 * index / total)
                time.sleep(0.04)
            TASKS.update_progress(run_id, "汇总评分与异议", 0.72)
            trace_event("jury", "local_scoring", "本地席位 claims 汇总评分", {"seat_count": len(seats)})
            verdict = run_auto_jury(question=question, mode=mode, seats=seats, run_id=run_id)
            verdict["prompt_flow"] = prompt_flow
            verdict["execution_plan"] = execution_plan

        TASKS.update_progress(run_id, "生成判词报告", 0.90)
        if mentor_preflight:
            verdict["mentor_preflight"] = mentor_preflight
        _attach_product_run_metadata(verdict, chief_judge=chief_judge, abstained_seats=abstained_seats)
        citation_report = _attach_citation_mvp(verdict, run_id=run_id)
        if citation_report:
            trace_event("grand_judge", "citation_mvp_sealed", "引用验证 MVP 已生成 Replay Ledger 与 Citation ID", {
                "certification_id": citation_report.get("certification_id"),
                "overall_status": (citation_report.get("citation_verification") or {}).get("overall_status"),
                "replay_ledger_hash": citation_report.get("replay_ledger_hash"),
            })
        view_url = generate_secure_view_url(run_id)
        trace_event("report", "view_url_generated", "安全完整报告链接已生成", {"view_url": view_url})
        verdict["execution_trace"] = trace.to_dict()
        verdict["view_url"] = view_url
        _save_run(run_id, verdict)
        trace_event("report", "run_saved", "verdict.json / verdict.md / trace.json 已写入 runs 目录", {
            "run_dir": str(RUNS_DIR / run_id),
        })
        TASKS.complete(run_id, verdict)
        trace_event("task", "complete", "任务完成", {"verdict": verdict.get("verdict"), "confidence": verdict.get("confidence")})

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
                view_url=view_url,
                to=notify_config.get("email"),
                webhook_url=notify_config.get("webhook_url"),
                feishu_webhook=notify_config.get("feishu_webhook"),
                wecom_webhook=notify_config.get("wecom_webhook"),
            )
    except Exception as exc:
        trace_event("task", "failed", "任务失败", {"error": str(exc)})
        TASKS.fail(run_id, str(exc))


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
        view_url = generate_secure_view_url(source_run_id)
        merged["view_url"] = view_url
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
        view_url = generate_secure_view_url(source_run_id)
        merged["view_url"] = view_url

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
        view_url = generate_secure_view_url(source_run_id)
        verdict["view_url"] = view_url

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
        view_url = generate_secure_view_url(source_run_id)
        merged["view_url"] = view_url

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


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "version": PRODUCT_VERSION,
        "product": PRODUCT_NAME,
        "seats_available": len(SEAT_PERSONAS),
        "engines": ["local", "web"],
        "execution_drivers": ["local_synthetic", "web_dom", "chrome_apple_events", "chrome_cdp", "desktop_operator_pending", "api_provider_pending"],
        "grand_judge_mvp": "citation_verification",
        "evidence_os": ["evidence_broker", "blind_cross_validation", "evidence_gap_queue", "human_review", "eval_dataset"],
        "product_layers": ["stable_closeout", "lab_reliability_console", "human_gavel", "benchmark_summary"],
        "web_requires_calibration": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


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


@app.route("/")
def dashboard():
    return send_from_directory(PRODUCT_DIR, "dashboard.html")


@app.route("/landing")
@app.route("/landing.html")
def landing():
    return send_from_directory(PRODUCT_DIR, "landing.html")


@app.route("/dashboard.js")
def dashboard_js():
    return send_from_directory(PRODUCT_DIR, "dashboard.js")


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
    return jsonify(bridge_status())


@app.route("/api/prompt/resonate", methods=["POST"])
def prompt_resonate():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    mode = str(data.get("mode", "flash")).lower().strip() or "flash"
    engine = str(data.get("engine", "local")).lower().strip() or "local"
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


@app.route("/api/judge", methods=["POST"])
def submit_judge():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    mode = str(data.get("mode", "flash")).lower().strip() or "flash"
    engine = str(data.get("engine", "local")).lower().strip() or "local"
    override_seats = _normalize_seat_list(data.get("seats"))
    abstained_seats = _normalize_seat_list(data.get("abstained_seats"))
    chief_judge = str(data.get("chief_judge") or "auto").lower().strip()
    raw_mentor_preflight = data.get("mentor_preflight")
    mentor_preflight = raw_mentor_preflight if isinstance(raw_mentor_preflight, dict) else None
    external_evidence = _normalize_external_evidence_payload(data.get("external_evidence"))
    evidence_options = _normalize_evidence_options(data.get("evidence_options"))

    if not question:
        return jsonify({"error": "question is required"}), 400
    if engine not in {"local", "web"}:
        return jsonify({"error": "engine must be 'local' or 'web'"}), 400
    if chief_judge != "auto" and chief_judge not in SEAT_PERSONAS:
        return jsonify({"error": "chief_judge must be 'auto' or a valid seat id"}), 400

    try:
        config = resolve_mode(mode, override_seats=override_seats or None)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    seats = [s for s in config["seats"] if s in SEAT_PERSONAS]
    if not seats:
        return jsonify({"error": "No valid seats selected"}), 400

    run_id = TASKS.submit(question=question, mode=mode, seats=seats)
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
    if not seats and requested:
        seats = requested
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
            detail = html.escape(response or "该席位返回了空回答。")
            recovered = " · 补跑追回" if item.get("recovered_by_retry") else ""
            meta = f"{len(response)} 字符 · 用时 {item.get('elapsed_seconds', '-') }s · 分数 {score_text}{retry_note}{recovered}"
            preview = _compact_report_text(response, 180)
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
            meta = f"{code} · 分数 {score_text}{retry_note}"
            preview = _compact_report_text(message, 180)
        open_attr = " open" if not ok else ""
        cards.append(
            f'<details class="seat-answer {status_class}" id="seat-answer-{html.escape(seat)}"{open_attr}>'
            "<summary>"
            f"<strong>{html.escape(seat_name)}</strong>"
            f'<span class="seat-state {state_class}">{html.escape(status)}</span>'
            f'<span class="seat-meta">{html.escape(meta)}</span>'
            "</summary>"
            f'<p class="seat-preview">{html.escape(preview)}</p>'
            f'<pre class="answer">{detail}</pre>'
            "</details>"
        )
    return (
        '<section class="band" id="seat-answers">'
        '<div class="section-head"><div>'
        "<h2>席位完整回答</h2>"
        "<p class=\"muted\">成功席位默认收起，慢席位和失败席位默认展开；底层状态会保留，但不会混入最终判词。</p>"
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
        detail = html.escape(response) if ok else html.escape(f"{error.get('code', 'unknown')}: {error.get('message', 'No response captured.')}")
        preview = _compact_report_text(response if ok else error.get("message", ""), 180)
        cards.append(
            f'<details class="seat-answer {status_class}" id="mentor-supplement-{html.escape(seat)}"{"" if ok else " open"}>'
            "<summary>"
            f"<strong>{html.escape(seat_name)}</strong>"
            f'<span class="seat-state {state_class}">{html.escape(status)}</span>'
            f'<span class="seat-meta">{len(questions)} 个问题 · {html.escape(str(item.get("elapsed_seconds", "-")))}s</span>'
            "</summary>"
            f'<ul class="compact-list">{question_items}</ul>'
            f'<p class="seat-preview">{html.escape(preview)}</p>'
            f'<pre class="answer">{detail}</pre>'
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
    report = result.get("final_report") or build_final_report(result)
    if not report:
        return ""
    return render_final_report_html(report)


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
        "<h2>每个模型的回答入口、优缺点</h2>"
        '<p class="muted">这一层是索引：点席位名可跳到完整原文，优缺点来自席位画像、证据密度、互评和评分结果。</p>'
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
            "<details class=\"band\"><summary><h2>本地共振与专业提示词</h2></summary>"
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
    cross_temporal_html = _render_cross_temporal_analysis(result)
    judge_answer_html = _render_judge_answer(result)
    score_rounds_html = _render_score_rounds(result)
    seat_digest_html = _render_seat_digest(result)
    seat_answers_html = _render_seat_answers(result)
    mentor_supplements_html = _render_mentor_supplements(result)
    deliberation_html = _render_deliberation(result)
    citation_verification_html = _render_citation_verification(result)
    evidence_os_html = _render_evidence_os(result)
    judge_answer_link = '<a href="#judge-answer">法官答案</a>' if judge_answer_html else ""
    score_rounds_link = '<a href="#score-rounds">评分轮次</a>' if score_rounds_html else ""
    seat_digest_link = '<a href="#seat-digest">模型总览</a>' if seat_digest_html else ""
    seat_answers_link = '<a href="#seat-answers">查看席位回答</a>' if seat_answers_html else ""
    mentor_supplements_link = '<a href="#mentor-supplements">共振二轮</a>' if mentor_supplements_html else ""
    deliberation_link = '<a href="#deliberation">查看互评评分</a>' if deliberation_html else ""
    citation_link = '<a href="#citation-verification">引用验证</a>' if citation_verification_html else ""
    evidence_os_link = '<a href="#evidence-os">Evidence OS</a>' if evidence_os_html else ""
    cross_temporal_link = '<a href="#cross-temporal">横纵收口</a>' if cross_temporal_html else ""
    final_report_link = '<a href="#final-report">最终方案</a>' if final_report_html else ""
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Judge Verdict</title>
  <style>
    :root {{ color-scheme: dark; --bg:#080b14; --panel:#111827; --soft:#151d2c; --line:#263149; --text:#f4f6fb; --muted:#9aa4b5; --accent:#ffc53d; --green:#36d06f; --red:#ff6868; --blue:#65a8ff; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; margin: 0; background: var(--bg); color: var(--text); letter-spacing: 0; }}
    .nav {{ position: sticky; top: 0; z-index: 2; display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px 24px; background:#0d1425; border-bottom:1px solid var(--line); }}
    .nav a {{ color: var(--text); text-decoration:none; border:1px solid var(--line); border-radius:8px; padding:8px 12px; background:#101622; font-weight:700; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px 20px 52px; }}
    .hero {{ padding: 6px 0 18px; }}
    .badge {{ display: inline-block; padding: 7px 12px; border-radius: 999px; background: var(--accent); color: #111; font-weight: 800; }}
    h1 {{ font-size: clamp(28px, 4vw, 46px); line-height: 1.18; margin: 18px 0 12px; max-width: 980px; }}
    h2 {{ font-size: 18px; margin: 0; }}
    h3 {{ font-size: 14px; margin: 18px 0 8px; color: var(--accent); }}
    p {{ line-height: 1.65; }}
    .question {{ color: var(--muted); max-width: 900px; }}
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
    .nested {{ margin-top:14px; border:1px solid var(--line); border-radius:8px; background:#101622; padding:12px; }}
    .nested summary {{ cursor:pointer; font-weight:800; }}
    details.band > summary {{ cursor: pointer; list-style: none; display:flex; align-items:center; justify-content:space-between; gap:12px; }}
    details.band > summary::-webkit-details-marker, .seat-answer summary::-webkit-details-marker {{ display:none; }}
    details.band > summary::after {{ content:"展开"; color:var(--muted); font-size:12px; }}
    details.band[open] > summary::after {{ content:"收起"; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }} td, th {{ border-bottom: 1px solid var(--line); padding: 10px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); background:#111827; }}
    pre {{ white-space: pre-wrap; overflow: auto; background: #070b14; padding: 14px; border-radius: 8px; border:1px solid #1f2937; line-height:1.55; }}
    .section-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:12px; }}
    .section-head p {{ margin:8px 0 0; }}
    .report-lead {{ font-size:16px; line-height:1.75; color:var(--text); background:#0f172a; border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .paper-report {{ border:1px solid var(--line); border-radius:8px; padding:22px; margin:18px 0; background:#101827; }}
    .paper-heading h2 {{ font-size:24px; margin:6px 0; }}
    .paper-kicker {{ margin:0; color:var(--accent); font-size:12px; font-weight:800; letter-spacing:0; }}
    .paper-status {{ margin:0 0 14px; color:var(--muted); }}
    .paper-meta {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:12px 0 16px; }}
    .paper-meta div, .paper-block, .paper-postulate {{ border:1px solid var(--line); border-radius:8px; background:#0d1424; padding:13px; }}
    .paper-meta span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; margin-bottom:4px; }}
    .paper-meta strong {{ display:block; overflow-wrap:anywhere; }}
    .paper-block {{ margin:12px 0; }}
    .paper-block h3, .paper-postulate h3 {{ margin-top:0; }}
    .paper-abstract p {{ font-size:16px; line-height:1.75; }}
    .paper-keywords {{ display:flex; flex-wrap:wrap; gap:7px; margin-top:10px; }}
    .paper-keywords span {{ border:1px solid var(--line); border-radius:999px; padding:5px 8px; color:var(--muted); background:#0b1020; font-size:12px; }}
    .paper-postulates {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin:12px 0; }}
    .paper-postulate span {{ display:block; color:var(--accent); font-size:11px; font-weight:800; margin-bottom:6px; }}
    .paper-postulate small {{ display:block; color:var(--muted); line-height:1.5; }}
    .paper-columns {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; }}
    .report-columns {{ display:grid; grid-template-columns: minmax(0,1fr) minmax(0,1.2fr); gap:12px; margin:12px 0; }}
    .report-column {{ border:1px solid var(--line); border-radius:8px; background:#101622; padding:14px; min-width:0; }}
    .report-column h3 {{ margin-top:0; }}
    .trace-mini {{ list-style:none; padding:0; margin:0; display:grid; gap:8px; }}
    .trace-mini li {{ border:1px solid var(--line); border-radius:8px; padding:9px 10px; background:#0b1020; }}
    .trace-mini strong {{ display:block; color:var(--accent); font-size:12px; margin-bottom:4px; }}
    .trace-mini span {{ color:var(--muted); font-size:12px; line-height:1.45; }}
    .mini-actions {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    button {{ color:var(--text); border:1px solid var(--line); border-radius:8px; padding:8px 10px; background:#101622; font-weight:700; cursor:pointer; }}
    button:hover, .actions a:hover, .nav a:hover {{ border-color:var(--accent); }}
    .seat-answer-list {{ display:grid; gap:10px; }}
    .seat-answer {{ border:1px solid var(--line); border-radius:8px; background:#101622; padding:0; }}
    .seat-answer.is-pending {{ border-color:rgba(255,197,61,.65); }}
    .seat-answer.is-failed {{ border-color:rgba(255,104,104,.55); }}
    .seat-answer summary {{ cursor:pointer; display:grid; grid-template-columns:minmax(120px, 1fr) auto auto; gap:10px; align-items:center; padding:14px; }}
    .seat-state {{ font-weight:800; }}
    .seat-meta {{ color:var(--muted); font-size:12px; text-align:right; }}
    .seat-preview {{ margin:0; padding:0 14px 12px; color:var(--muted); }}
    .answer {{ margin:0 14px 14px; max-height:420px; }}
    .compact-list {{ margin:0; padding-left:18px; }}
    .status-pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 8px; font-weight:800; background:#0b1020; }}
    code {{ color:var(--accent); }}
    .actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }}
    .actions a {{ color:var(--text); text-decoration:none; border:1px solid var(--line); border-radius:8px; padding:9px 12px; background:#101622; font-weight:700; }}
    @media (max-width: 760px) {{
      .summary-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
      .paper-meta, .paper-postulates, .paper-columns {{ grid-template-columns:1fr; }}
      .section-head {{ display:block; }}
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
  <a href="/">返回提问</a>
</nav>
<main>
  <section class="hero">
    <p class="badge">{html.escape(str(result.get("mode_emoji", "")))} {html.escape(str(result.get("verdict_label", "")))} · {result.get("confidence", 0)}%</p>
    <h1>{html.escape(str(result.get("one_liner", "AI Judge Verdict")))}</h1>
    <p class="question">{html.escape(str(result.get("question", "")))}</p>
    <div class="actions"><a href="/">返回提问界面</a>{final_report_link}{cross_temporal_link}{judge_answer_link}{score_rounds_link}{citation_link}{evidence_os_link}{seat_digest_link}{seat_answers_link}{mentor_supplements_link}{deliberation_link}</div>
  </section>
  {collection_html}
  {final_report_html}
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
  <details class="band"><summary><h2>原始 JSON</h2></summary><pre>{raw_json}</pre></details>
</main>
<script>
document.addEventListener("click", (event) => {{
  const button = event.target.closest("[data-seat-action]");
  if (!button) return;
  const shouldOpen = button.dataset.seatAction === "expand";
  document.querySelectorAll(".seat-answer").forEach((node) => {{
    node.open = shouldOpen;
  }});
}});
</script>
</body></html>"""


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
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
