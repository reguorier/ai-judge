#!/usr/bin/env python3
# ruff: noqa: E402
"""Isolated browser bridge for live web-model seats.

This bridge is deliberately different from desktop GUI control:
  - it uses Playwright browser contexts, not macOS mouse events
  - it types into page DOMs, not the user's active keyboard focus
  - it never reads or writes the system clipboard
  - every seat gets its own persistent profile directory

The default product stays on the deterministic local engine. Enable this bridge
only after Playwright is installed and target model web apps are logged in or
configured with working selectors.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.execution_drivers import driver_for_bridge_seat
from core.seat_execution_policy import annotate_execution_results
from core.seat_personas import SEAT_PERSONAS, render_jury_prompt
from bridges.chrome_fixed_tab_bridge import (
    _build_prepare_submission_ui_js,
    _humanized_sleep,
    _quality_mode_failure,
    _quality_mode_policy_snapshot,
    _quality_mode_prepare_required,
    _quality_mode_prepare_verified,
    _quality_mode_required_mode,
    _quality_mode_trace_action,
    _quality_mode_trace_message,
    chrome_apple_events_status,
    list_chrome_tabs,
    run_chrome_fixed_tabs,
)
from bridges.chrome_cdp_bridge import chrome_cdp_status, ensure_chrome_cdp_awake, list_cdp_tabs, run_chrome_cdp_tabs


DATA_DIR = _PROJECT_ROOT / "data"
DEFAULT_CONFIG_PATH = DATA_DIR / "web_seats.json"
PROFILE_ROOT = DATA_DIR / "web_profiles"
CALIBRATION_PATH = DATA_DIR / "seat_calibration.json"
CALIBRATION_MAX_AGE_HOURS = 72
RETRYABLE_WEB_ERROR_CODES = {
    "cdp_unavailable",
    "response_timeout",
    "slow_response_pending",
    "response_below_minimum",
    "response_not_relevant",
    "model_page_error",
    "page_error",
    "chrome_crash",
    "fixed_tab_not_found",
    "deepseek_expert_mode_not_verified",
    "doubao_expert_mode_not_verified",
    "meta_quality_mode_not_verified",
    "wenxin_quality_mode_not_verified",
    "minimax_quality_mode_not_verified",
    "yuanbao_quality_mode_not_verified",
    "kimi_quality_mode_not_verified",
    "qwen_quality_mode_not_verified",
    "gemini_quality_mode_not_verified",
    "stepfun_quality_mode_not_verified",
    "xunfei_quality_mode_not_verified",
    "xunfei_desk_bounced_to_home",
    "xunfei_desk_input_not_ready",
    "xunfei_desk_ready_failed",
    "submit_unconfirmed",
    "send_button_not_found",
    "composer_busy",
}

BLOCKING_LOGIN_STATES = {
    "missing",
    "login_required",
    "challenge_required",
    "page_error",
    "provider_account_restricted",
}

LONG_PROMPT_FRAGILE_SEATS = {"gemini", "deepseek", "qwen", "wenxin", "yuanbao", "meta", "grok", "stepfun", "xunfei"}
A_SHARE_REDUCTION_PROMPT_MARKERS = (
    "董事减持",
    "upper_bound_ret_to_first2_high",
    "core_stats_summary",
    "event_study_rows",
    "2026Q2",
)

DEFAULT_URLS = {
    "chatgpt": "https://chatgpt.com/",
    "claude": "https://claude.ai/new",
    "gemini": "https://gemini.google.com/app?hl=zh",
    "deepseek": "https://chat.deepseek.com/",
    "qwen": "https://chat.qwen.ai/",
    "kimi": "https://www.kimi.com/",
    "grok": "https://grok.com/",
    "yuanbao": "https://yuanbao.tencent.com/chat/",
    "doubao": "https://www.doubao.com/chat/",
    "minimax": "https://agent.minimax.io",
    "zhipu": "https://bigmodel.cn/trialcenter/modeltrial/text",
    "wenxin": "https://wenxin.baidu.com/new-chat",
    "mimo": "https://aistudio.xiaomimimo.com/#/chat",
    "meta": "https://www.meta.ai/",
    "stepfun": "https://chat.stepfun.com/chats/new",
    "xunfei": "https://xinghuo.xfyun.cn/desk",
}

DEFAULT_TARGETS = {
    "chatgpt": {"provider": "ChatGPT", "channel": "web", "browser_label": "ChatGPT Atlas / chatgpt.com"},
    "claude": {"provider": "Claude", "channel": "web", "browser_label": "Claude / claude.ai"},
    "gemini": {"provider": "Gemini", "channel": "web", "browser_label": "Gemini / gemini.google.com"},
    "deepseek": {"provider": "DeepSeek", "channel": "web", "browser_label": "DeepSeek / chat.deepseek.com"},
    "qwen": {"provider": "Qwen Studio", "channel": "web", "browser_label": "Qwen Studio / chat.qwen.ai"},
    "kimi": {"provider": "Kimi", "channel": "web", "browser_label": "Kimi / kimi.com"},
    "grok": {"provider": "Grok", "channel": "web", "browser_label": "Grok / grok.com"},
    "yuanbao": {"provider": "Yuanbao", "channel": "web", "browser_label": "腾讯元宝 / yuanbao.tencent.com"},
    "mimo": {"provider": "MiMo", "channel": "web", "browser_label": "MiMo / custom"},
    "minimax": {
        "provider": "MiniMax",
        "channel": "web",
        "browser_label": "MiniMax Agent / agent.minimax.io",
        "allow_label_fallback": False,
    },
    "zhipu": {"provider": "智谱 AI", "channel": "web", "browser_label": "智谱AI开放平台 / bigmodel.cn"},
    "wenxin": {"provider": "Wenxin", "channel": "web", "browser_label": "文心一言 / wenxin.baidu.com"},
    "doubao": {
        "provider": "Doubao",
        "channel": "web",
        "browser_label": "Doubao / doubao.com",
        "app_name": "豆包",
        "bundle_id": "com.bot.neotix.doubao",
        "app_path": "/Applications/豆包.app",
        "fallback_url": "https://www.doubao.com/chat/",
    },
    "meta": {
        "provider": "Meta AI",
        "channel": "web",
        "browser_label": "Meta AI / meta.ai",
    },
    "stepfun": {
        "provider": "StepFun",
        "channel": "web",
        "browser_label": "阶跃星辰 / chat.stepfun.com",
    },
    "xunfei": {
        "provider": "科大讯飞",
        "channel": "web",
        "browser_label": "讯飞星火 / xinghuo.xfyun.cn",
    },
}

DEFAULT_INPUT_SELECTORS = [
    "textarea[data-testid='prompt-textarea']",
    "div[contenteditable='true'][role='textbox']",
    "div[role='textbox']",
    "textarea",
    "[contenteditable='true']",
]

DEFAULT_SUBMIT_SELECTORS = [
    "button[data-testid='send-button']",
    "button[aria-label*='Send']",
    "button[aria-label*='发送']",
    "button[type='submit']",
]

DEFAULT_RESPONSE_SELECTORS = [
    "[data-message-author-role='assistant']",
    "[data-testid*='conversation-turn']",
    ".ds-markdown",
    ".ds-markdown--block",
    ".bubble-content",
    "[class*='assistant-message']",
    ".model-response-text",
    ".response-content",
    "[class*='bot-message']",
    "[class*='ai-answer']",
    "[class*='answer-content']",
    ".chat-message-content",
    "[class*='message-content']",
    ".markdown-body",
    "[class*='answer-text']",
    "[class*='receive-message']",
    "[class*='assistant-content']",
    "[class*='message-text']",
    "[class*='chat-content']",
    "[class*='robot-msg']",
    "article",
    ".markdown",
    "main",
]

WORLDCUP_PROMPT_MARKERS = (
    "世界杯预测池",
    "赛事预测",
    "下注表",
    "贷款",
    "GP",
    "bet_ledger",
)

WORLDCUP_FRAGILE_SHORT_PROMPT_SEATS = {
    "claude",
    "qwen",
    "kimi",
    "doubao",
    "mimo",
    "meta",
    "grok",
    "minimax",
    "zhipu",
    "wenxin",
    "stepfun",
    "xunfei",
}


class SeatBridgeError(RuntimeError):
    """Raised when the web bridge cannot run."""


def playwright_installed() -> bool:
    """Return whether Playwright's Python package is installed."""
    return importlib.util.find_spec("playwright") is not None


def default_config() -> dict[str, Any]:
    """Return a conservative editable bridge config template."""
    quality_mode_policy = _quality_mode_policy_snapshot()
    return {
        "headless": True,
        "timeout_seconds": 120,
        "settle_seconds": 3,
        "retry_failed_seats": True,
        "retry_attempts": 2,
        "retry_timeout_seconds": 600,
        "required_timeout_seconds": 420,
        "required_retry_timeout_seconds": 600,
        "required_final_nudge_timeout_seconds": 120,
        "required_post_timeout_grace_seconds": 120,
        "auto_open_missing_tabs": False,
        "auto_wake_cdp": True,
        "auto_wake_open_tabs": True,
        "auto_wake_cooldown_seconds": 20,
        "auto_wake_wait_seconds": 25,
        "chrome_cdp_endpoint": "http://127.0.0.1:9333",
        "chrome_cdp_profile_dir": str(Path.home() / "Documents/Playground/.omx/ai-judge/chrome-profile"),
        "chrome_cdp_state_path": str(DATA_DIR / "chrome_cdp_bridge_state.json"),
        "chrome_launch_strategy": "open_app",
        "strict_chrome_profile_guard": True,
        "auto_terminate_wrong_cdp_profile": True,
        "chrome_profile_marker_required": False,
        "chrome_profile_marker_path": str(Path.home() / "Documents/Playground/.omx/ai-judge/chrome-profile/AI_JUDGE_DEDICATED_PROFILE.txt"),
        "login_state_path": str(DATA_DIR / "seat_login_state.json"),
        "login_state_audit": True,
        "humanized_pacing": True,
        "human_pacing": {
            "base_delay_seconds": 1.2,
            "jitter_seconds": 1.4,
            "fragile_base_delay_seconds": 2.4,
            "fragile_jitter_seconds": 2.6,
            "between_seats_seconds": 2.0,
            "after_write_seconds": 0.8,
            "after_click_seconds": 1.1,
            "after_reload_seconds": 4.0,
        },
        "page_recovery_attempts": 1,
        "page_recovery_wait_seconds": 12,
        "profile_root": str(PROFILE_ROOT),
        "input_selectors": DEFAULT_INPUT_SELECTORS,
        "submit_selectors": DEFAULT_SUBMIT_SELECTORS,
        "response_selectors": DEFAULT_RESPONSE_SELECTORS,
        "quality_mode_policy": quality_mode_policy,
        "seats": {
            seat: {
                "enabled": False,
                "url": DEFAULT_URLS.get(seat, ""),
                "fresh_url": DEFAULT_URLS.get(seat, ""),
                "fallback_url": DEFAULT_TARGETS.get(seat, {}).get("fallback_url", ""),
                "match_domains": [_domain(DEFAULT_URLS.get(seat, ""))] if DEFAULT_URLS.get(seat) else [],
                "channel": DEFAULT_TARGETS.get(seat, {}).get("channel", "web"),
                "provider": DEFAULT_TARGETS.get(seat, {}).get("provider", SEAT_PERSONAS[seat]["name"]),
                "browser_label": DEFAULT_TARGETS.get(seat, {}).get("browser_label", DEFAULT_URLS.get(seat, "")),
                "allow_label_fallback": DEFAULT_TARGETS.get(seat, {}).get("allow_label_fallback", True),
                "desktop_app": {
                    "name": DEFAULT_TARGETS.get(seat, {}).get("app_name"),
                    "bundle_id": DEFAULT_TARGETS.get(seat, {}).get("bundle_id"),
                    "path": DEFAULT_TARGETS.get(seat, {}).get("app_path"),
                } if DEFAULT_TARGETS.get(seat, {}).get("channel") == "desktop" else None,
                "headless": None,
                "execution_required": seat != "grok",
                "best_effort": seat == "grok",
                "exclude_from_publish_gate": seat == "grok",
                "required_quality_mode": _quality_mode_required_mode(seat),
                "fragile_page": seat in WORLDCUP_FRAGILE_SHORT_PROMPT_SEATS or seat in {"chatgpt", "deepseek"},
                "notes": "Set enabled=true after logging into this model in its isolated profile.",
            }
            for seat in SEAT_PERSONAS
        },
    }


def write_default_config(path: Path | None = None, overwrite: bool = False) -> Path:
    """Write an editable bridge config file."""
    target = path or DEFAULT_CONFIG_PATH
    if target.exists() and not overwrite:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(default_config(), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_bridge_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load config and merge it with defaults."""
    config = default_config()
    target = Path(path or os.environ.get("AI_JUDGE_WEB_SEATS_CONFIG", DEFAULT_CONFIG_PATH))
    if not target.exists():
        config["_config_path"] = str(target)
        config["_config_exists"] = False
        return config

    user_config = json.loads(target.read_text(encoding="utf-8"))
    for key, value in user_config.items():
        if key == "seats":
            continue
        config[key] = value

    seats = config["seats"]
    for seat, seat_config in (user_config.get("seats") or {}).items():
        if seat not in seats:
            seats[seat] = {}
        seats[seat].update(seat_config)
    config["quality_mode_policy"] = _quality_mode_policy_snapshot()
    for seat, seat_config in seats.items():
        seat_config["required_quality_mode"] = _quality_mode_required_mode(seat)

    config["_config_path"] = str(target)
    config["_config_exists"] = True
    return config


def merge_bridge_config_overrides(config: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return config with a shallow/deep merge suitable for rescue runs."""
    if not overrides:
        return config
    merged = dict(config)
    for key, value in overrides.items():
        if key == "seats" and isinstance(value, dict):
            merged_seats = {seat: dict(seat_config) for seat, seat_config in (merged.get("seats") or {}).items()}
            for seat, seat_overrides in value.items():
                if not isinstance(seat_overrides, dict):
                    continue
                merged_seats.setdefault(seat, {})
                merged_seats[seat].update(seat_overrides)
            merged["seats"] = merged_seats
        else:
            merged[key] = value
    return merged


def load_calibration(path: str | Path | None = None) -> dict[str, Any]:
    """Load persisted seat calibration results."""
    target = Path(path or CALIBRATION_PATH)
    if not target.exists():
        return {"version": 1, "updated_at": None, "seats": {}}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "updated_at": None, "seats": {}}
    if not isinstance(data, dict):
        return {"version": 1, "updated_at": None, "seats": {}}
    data.setdefault("version", 1)
    data.setdefault("seats", {})
    return data


def save_calibration(data: dict[str, Any], path: str | Path | None = None) -> Path:
    """Persist seat calibration results."""
    target = Path(path or CALIBRATION_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _prefer_wake_cdp_status(cdp_status: dict[str, Any] | None, cdp_wake: dict[str, Any] | None) -> dict[str, Any] | None:
    """Use the successful wake probe if the immediate follow-up probe races and times out."""
    if not isinstance(cdp_status, dict) or not isinstance(cdp_wake, dict):
        return cdp_status
    wake_status = cdp_wake.get("status")
    if isinstance(wake_status, dict) and wake_status.get("available") and not cdp_status.get("available"):
        failed_probe = dict(cdp_status)
        adopted = dict(wake_status)
        adopted["wake"] = cdp_wake
        adopted["pre_wake_probe"] = failed_probe
        adopted["adopted_from_wake"] = True
        return adopted
    cdp_status["wake"] = cdp_wake
    return cdp_status


def bridge_status(
    path: str | Path | None = None,
    *,
    allow_wake: bool = False,
    open_tabs: bool = False,
) -> dict[str, Any]:
    """Return product-facing readiness for the isolated web bridge.

    Status reads must be side-effect free by default.  Older versions used this
    route as a light self-heal point and woke Chrome CDP/opened tabs whenever
    dashboards polled readiness.  That made passive status polling look like an
    endless bridge launch loop.  Only explicit run execution or the dedicated
    wake endpoint should pass allow_wake=True.
    """
    config = load_bridge_config(path)
    calibration = load_calibration()
    installed = playwright_installed()
    automation_driver = str(config.get("automation_driver") or "playwright").strip().lower()
    chrome_status = chrome_apple_events_status() if automation_driver == "chrome_apple_events" else None
    cdp_status = chrome_cdp_status(config) if automation_driver == "chrome_cdp" else None
    cdp_wake = None
    if automation_driver == "chrome_cdp" and cdp_status and not cdp_status.get("available") and allow_wake and config.get("auto_wake_cdp", True):
        cdp_wake = ensure_chrome_cdp_awake(config, open_tabs=bool(open_tabs and config.get("auto_wake_open_tabs", True)))
        cdp_status = chrome_cdp_status(config)
        cdp_status = _prefer_wake_cdp_status(cdp_status, cdp_wake)
    elif automation_driver == "chrome_cdp" and cdp_status and cdp_status.get("available") and allow_wake and open_tabs and config.get("auto_wake_open_tabs", True):
        # A CDP endpoint can survive with zero useful tabs after a crash/restart.
        # Explicit wake/run checks may self-heal so the executor does not report
        # a connected but empty bridge.
        cdp_wake = ensure_chrome_cdp_awake(config, open_tabs=True)
        cdp_status = chrome_cdp_status(config)
        cdp_status = _prefer_wake_cdp_status(cdp_status, cdp_wake)
    chrome_tabs = []
    if chrome_status and chrome_status.get("available"):
        try:
            chrome_tabs = list_chrome_tabs()
        except Exception:
            chrome_tabs = []
    if cdp_status and cdp_status.get("available"):
        try:
            chrome_tabs = list_cdp_tabs(config)
        except Exception:
            chrome_tabs = []
    seat_rows = []
    enabled_count = 0
    configured_count = 0
    for seat, persona in SEAT_PERSONAS.items():
        seat_config = _seat_config(config, seat)
        enabled = bool(seat_config.get("enabled"))
        if enabled:
            enabled_count += 1
        profile_dir = _profile_dir(config, seat)
        channel = str(seat_config.get("channel") or "web")
        desktop_app = seat_config.get("desktop_app") or {}
        desktop_path = desktop_app.get("path")
        desktop_installed = bool(desktop_path and Path(desktop_path).exists())
        configured = enabled and bool(seat_config.get("url")) and installed
        if channel == "desktop":
            configured = enabled and desktop_installed
        elif automation_driver == "chrome_apple_events":
            configured = enabled and bool(seat_config.get("url")) and bool(chrome_status and chrome_status.get("available"))
        elif automation_driver == "chrome_cdp":
            configured = enabled and bool(seat_config.get("url")) and bool(cdp_status and cdp_status.get("available"))
        if configured:
            configured_count += 1

        calibration_entry = _calibration_entry(calibration, seat)
        driver_input = {"channel": channel}
        if channel == "web" and automation_driver == "chrome_apple_events":
            driver_input["driver"] = "chrome_apple_events"
        if channel == "web" and automation_driver == "chrome_cdp":
            driver_input["driver"] = "chrome_cdp"
        driver = driver_for_bridge_seat(driver_input)
        fixed_tab_ready = bool(
            channel == "web"
            and automation_driver in {"chrome_apple_events", "chrome_cdp"}
            and configured
            and _fixed_chrome_tab_available(seat_config, chrome_tabs)
        )
        fixed_tab_driver = channel == "web" and automation_driver in {"chrome_apple_events", "chrome_cdp"}
        login_state = _seat_login_state(seat_config, chrome_tabs) if fixed_tab_driver else {"state": "not_applicable"}
        login_blocked = login_state.get("state") in BLOCKING_LOGIN_STATES
        if fixed_tab_driver:
            ready = bool(
                configured
                and driver["safe_background"]
                and fixed_tab_ready
                and not login_blocked
            )
        else:
            ready = bool(
                configured
                and driver["safe_background"]
                and calibration_entry["fresh"]
                and calibration_entry["status"] == "pass"
            )
        reason = _readiness_reason(
            channel=channel,
            enabled=enabled,
            installed=installed,
            configured=configured,
            desktop_installed=desktop_installed,
            seat_config=seat_config,
            calibration_entry=calibration_entry,
            driver=driver,
        )
        if channel == "web" and automation_driver == "chrome_apple_events":
            if not (chrome_status and chrome_status.get("available")):
                reason = str((chrome_status or {}).get("reason") or "apple_events_js_disabled")
            elif not _fixed_chrome_tab_available(seat_config, chrome_tabs):
                reason = "fixed_tab_not_found"
            elif login_state.get("state") in BLOCKING_LOGIN_STATES:
                reason = str(login_state.get("state"))
            else:
                reason = "ready"
        if channel == "web" and automation_driver == "chrome_cdp":
            if not (cdp_status and cdp_status.get("available")):
                reason = str((cdp_status or {}).get("reason") or "cdp_unavailable")
            elif not _fixed_chrome_tab_available(seat_config, chrome_tabs):
                reason = "fixed_tab_not_found"
            elif login_state.get("state") in BLOCKING_LOGIN_STATES:
                reason = str(login_state.get("state"))
            else:
                reason = "ready"
        row = {
            "id": seat,
            "name": persona["name"],
            "enabled": enabled,
            "configured": configured,
            "ready": ready,
            "reason": reason,
            "channel": channel,
            "driver": driver["driver"],
            "driver_label": driver["driver_label"],
            "safe_background": driver["safe_background"],
            "operator_required": driver["operator_required"],
            "execution_required": bool(seat_config.get("execution_required", seat != "grok")),
            "required_quality_mode": seat_config.get("required_quality_mode", _quality_mode_required_mode(seat)),
            "best_effort": bool(seat_config.get("best_effort") or seat_config.get("exclude_from_publish_gate")),
            "exclude_from_publish_gate": bool(seat_config.get("exclude_from_publish_gate")),
            "provider": seat_config.get("provider", persona["name"]),
            "browser_label": seat_config.get("browser_label", seat_config.get("url", "")),
            "url": seat_config.get("url", ""),
            "fresh_url": seat_config.get("fresh_url", ""),
            "match_domains": seat_config.get("match_domains", []),
            "login_state": login_state,
            "display_url": seat_config.get("display_url") or seat_config.get("fresh_url") or seat_config.get("url", ""),
            "profile_dir": str(profile_dir),
            "calibration": calibration_entry,
            "desktop_app": {
                "name": desktop_app.get("name"),
                "bundle_id": desktop_app.get("bundle_id"),
                "path": desktop_path,
                "installed": desktop_installed,
                "running": _desktop_app_running(desktop_app.get("name")),
            } if channel == "desktop" else None,
        }
        seat_rows.append(row)

    status_payload = {
        "available": installed and any(seat["ready"] for seat in seat_rows),
        "playwright_installed": installed,
        "config_exists": bool(config.get("_config_exists")),
        "config_path": config.get("_config_path", str(DEFAULT_CONFIG_PATH)),
        "calibration_path": str(CALIBRATION_PATH),
        "calibration_max_age_hours": CALIBRATION_MAX_AGE_HOURS,
        "enabled_count": enabled_count,
        "configured_count": configured_count,
        "ready_count": sum(1 for seat in seat_rows if seat["ready"]),
        "seats": seat_rows,
        "seat_browser_matrix": [
            {
                "seat": seat["id"],
                "seat_name": seat["name"],
                "provider": seat.get("provider"),
                "channel": seat.get("channel"),
                "driver": seat.get("driver"),
                "driver_label": seat.get("driver_label"),
                "target": seat.get("browser_label") or seat.get("display_url") or seat.get("url") or (seat.get("desktop_app") or {}).get("name"),
                "url": seat.get("url"),
                "fresh_url": seat.get("fresh_url"),
                "match_domains": seat.get("match_domains"),
                "login_state": seat.get("login_state"),
                "configured": seat.get("configured"),
                "ready": seat.get("ready"),
                "reason": seat.get("reason"),
                "safe_background": seat.get("safe_background"),
                "execution_required": seat.get("execution_required"),
                "required_quality_mode": seat.get("required_quality_mode"),
                "best_effort": seat.get("best_effort"),
                "exclude_from_publish_gate": seat.get("exclude_from_publish_gate"),
                "calibration_status": (seat.get("calibration") or {}).get("status"),
                "calibration_error_code": ((seat.get("calibration") or {}).get("error") or {}).get("code"),
                "calibration_age_hours": (seat.get("calibration") or {}).get("age_hours"),
                "calibrated_at": (seat.get("calibration") or {}).get("calibrated_at"),
            }
            for seat in seat_rows
        ],
        "isolation": {
            "uses_system_mouse": False,
            "uses_system_keyboard": False,
            "uses_system_clipboard": False,
            "browser_profiles": "one persistent profile per seat",
            "automation": (
                "Chrome CDP input events in fixed visible tabs"
                if automation_driver == "chrome_cdp"
                else
                "Chrome Apple Events DOM actions in fixed visible tabs"
                if automation_driver == "chrome_apple_events"
                else "Playwright DOM actions in a separate browser process"
            ),
        },
        "automation_driver": automation_driver,
        "chrome_apple_events": chrome_status,
        "chrome_cdp": cdp_status,
        "chrome_cdp_wake": cdp_wake,
    }
    if config.get("login_state_audit", True):
        _write_login_state_audit(config, status_payload)
    return status_payload


def _write_login_state_audit(config: dict[str, Any], status_payload: dict[str, Any]) -> None:
    try:
        path_value = str(config.get("login_state_path") or "").strip()
        path = Path(path_value).expanduser() if path_value else DATA_DIR / "seat_login_state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for seat in status_payload.get("seat_browser_matrix") or []:
            rows.append({
                "seat": seat.get("seat"),
                "provider": seat.get("provider"),
                "ready": bool(seat.get("ready")),
                "reason": seat.get("reason"),
                "login_state": seat.get("login_state"),
                "url": seat.get("url"),
                "fresh_url": seat.get("fresh_url"),
                "execution_required": bool(seat.get("execution_required")),
                "best_effort": bool(seat.get("best_effort")),
            })
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "automation_driver": status_payload.get("automation_driver"),
            "enabled_count": status_payload.get("enabled_count"),
            "configured_count": status_payload.get("configured_count"),
            "ready_count": status_payload.get("ready_count"),
            "chrome_cdp": status_payload.get("chrome_cdp"),
            "seats": rows,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def calibrate_bridge(
    seats: list[str] | None = None,
    config_path: str | Path | None = None,
    timeout_seconds: float = 12,
    progress: Callable[[str, float], None] | None = None,
) -> dict[str, Any]:
    """Run a lightweight real probe for selected seats and persist results."""
    config = load_bridge_config(config_path)
    requested = [seat.lower() for seat in (seats or list(SEAT_PERSONAS)) if seat.lower() in SEAT_PERSONAS]
    calibration = load_calibration()
    calibration.setdefault("version", 1)
    calibration.setdefault("seats", {})
    automation_driver = str(config.get("automation_driver") or "playwright").strip().lower()
    if automation_driver == "chrome_cdp":
        status = chrome_cdp_status(config)
        tabs = []
        if status.get("available"):
            try:
                tabs = list_cdp_tabs(config)
            except Exception:
                tabs = []
        total = max(1, len(requested))
        for index, seat in enumerate(requested, 1):
            if progress:
                progress(f"校准 Chrome CDP 标签：{seat} ({index}/{total})", index / total)
            seat_config = _seat_config(config, seat)
            channel = str(seat_config.get("channel") or "web")
            if not seat_config.get("enabled"):
                result = _calibration_failure(seat, "disabled", "Seat is disabled in web_seats.json.", driver="chrome_cdp")
            elif channel == "desktop":
                result = _calibrate_desktop_seat(seat, seat_config)
            elif not status.get("available"):
                result = _calibration_failure(
                    seat,
                    str(status.get("reason") or "cdp_unavailable"),
                    str(status.get("message") or "Chrome CDP is not available."),
                    driver="chrome_cdp",
                )
            elif not _fixed_chrome_tab_available(seat_config, tabs):
                result = _calibration_failure(
                    seat,
                    "fixed_tab_not_found",
                    "No open Chrome CDP tab matched this seat URL/title.",
                    driver="chrome_cdp",
                )
            else:
                result = {
                    "seat": seat,
                    "seat_name": SEAT_PERSONAS[seat]["name"],
                    "status": "pass",
                    "driver": "chrome_cdp",
                    "calibrated_at": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": 0,
                    "sample_chars": 0,
                    "error": None,
                }
            calibration["seats"][seat] = result
        save_calibration(calibration)
        return {
            "ok": any((calibration["seats"].get(seat) or {}).get("status") == "pass" for seat in requested),
            "results": [calibration["seats"][seat] for seat in requested],
            "status": bridge_status(config_path),
        }
    if automation_driver == "chrome_apple_events":
        status = chrome_apple_events_status()
        tabs = []
        if status.get("available"):
            try:
                tabs = list_chrome_tabs()
            except Exception:
                tabs = []
        total = max(1, len(requested))
        for index, seat in enumerate(requested, 1):
            if progress:
                progress(f"校准固定 Chrome 标签：{seat} ({index}/{total})", index / total)
            seat_config = _seat_config(config, seat)
            channel = str(seat_config.get("channel") or "web")
            if not seat_config.get("enabled"):
                result = _calibration_failure(seat, "disabled", "Seat is disabled in web_seats.json.", driver="chrome_apple_events")
            elif channel == "desktop":
                result = _calibrate_desktop_seat(seat, seat_config)
            elif not status.get("available"):
                result = _calibration_failure(
                    seat,
                    str(status.get("reason") or "apple_events_js_disabled"),
                    str(status.get("message") or "Chrome Apple Events JavaScript is not available."),
                    driver="chrome_apple_events",
                )
            elif not _fixed_chrome_tab_available(seat_config, tabs):
                result = _calibration_failure(
                    seat,
                    "fixed_tab_not_found",
                    "No open Chrome tab matched this seat URL/title.",
                    driver="chrome_apple_events",
                )
            else:
                result = {
                    "seat": seat,
                    "seat_name": SEAT_PERSONAS[seat]["name"],
                    "status": "pass",
                    "driver": "chrome_apple_events",
                    "calibrated_at": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": 0,
                    "sample_chars": 0,
                    "error": None,
                }
            calibration["seats"][seat] = result
        save_calibration(calibration)
        return {
            "ok": any((calibration["seats"].get(seat) or {}).get("status") == "pass" for seat in requested),
            "results": [calibration["seats"][seat] for seat in requested],
            "status": bridge_status(config_path),
        }
    installed = playwright_installed()
    total = max(1, len(requested))

    if installed:
        from playwright.sync_api import sync_playwright
    else:
        sync_playwright = None

    if sync_playwright is None:
        for index, seat in enumerate(requested, 1):
            if progress:
                progress(f"校准席位：{seat} ({index}/{total})", index / total)
            calibration["seats"][seat] = _calibration_failure(seat, "playwright_missing", "Playwright is not installed.")
        save_calibration(calibration)
        return {"ok": False, "results": [calibration["seats"][seat] for seat in requested], "status": bridge_status(config_path)}

    with sync_playwright() as playwright:
        for index, seat in enumerate(requested, 1):
            if progress:
                progress(f"校准席位：{seat} ({index}/{total})", index / total)
            seat_config = _seat_config(config, seat)
            channel = str(seat_config.get("channel") or "web")
            driver_name = driver_for_bridge_seat({"channel": channel})["driver"]
            if not seat_config.get("enabled"):
                result = _calibration_failure(seat, "disabled", "Seat is disabled in web_seats.json.", driver=driver_name)
            elif channel == "desktop":
                result = _calibrate_desktop_seat(seat, seat_config)
            elif not seat_config.get("url"):
                result = _calibration_failure(seat, "missing_url", "Seat URL is empty.")
            else:
                try:
                    result = _calibrate_web_seat(playwright, config, seat_config, seat, timeout_seconds)
                except Exception as exc:  # pragma: no cover - depends on local browser permissions/network
                    result = _calibration_failure(seat, "browser_launch_failed", str(exc), driver="web_dom")
            calibration["seats"][seat] = result

    save_calibration(calibration)
    return {
        "ok": any((calibration["seats"].get(seat) or {}).get("status") == "pass" for seat in requested),
        "results": [calibration["seats"][seat] for seat in requested],
        "status": bridge_status(config_path),
    }


def run_web_seats(
    question: str,
    seats: list[str],
    mode: str = "flash",
    config_path: str | Path | None = None,
    config_overrides: dict[str, Any] | None = None,
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    """Ask configured web model seats and return raw responses.

    Raises SeatBridgeError when Playwright is missing or no requested seat is
    enabled. Per-seat webpage/login/selector failures are returned as structured
    failed results so the verdict can make the failure visible.
    """
    config = merge_bridge_config_overrides(load_bridge_config(config_path), config_overrides)
    requested = [seat.lower() for seat in seats if seat.lower() in SEAT_PERSONAS]
    if trace:
        trace("bridge", "load_config", "读取网页席位配置", {
            "config_path": config.get("_config_path"),
            "requested_seats": requested,
        })
    if not requested:
        raise SeatBridgeError("No valid seats requested for the web bridge.")

    automation_driver = str(config.get("automation_driver") or "playwright").strip().lower()
    enabled_requested = [seat for seat in requested if _seat_config(config, seat).get("enabled")]
    if not enabled_requested:
        if trace:
            trace("bridge", "no_enabled_seats", "请求席位没有任何一个被启用", {"requested_seats": requested})
        raise SeatBridgeError(
            f"No requested seats are enabled in {config.get('_config_path')}. "
            "Run `python -m bridges.web_seat_bridge --init-config`, then enable seats after login."
        )

    if automation_driver == "chrome_apple_events":
        if progress:
            progress("Chrome 固定标签 Operator 启动", 0.12)
        if trace:
            trace("bridge", "chrome_fixed_tabs_driver", "使用 Chrome 固定标签 Operator 执行网页席位", {
                "requested_seats": requested,
                "uses_system_mouse": False,
                "uses_system_keyboard": False,
                "uses_system_clipboard": False,
            })
        return _run_driver_with_retries(
            runner=run_chrome_fixed_tabs,
            question=question,
            seats=requested,
            config=config,
            mode=mode,
            progress=progress,
            trace=trace,
            driver_label="Chrome 固定标签",
        )
    if automation_driver == "chrome_cdp":
        if progress:
            progress("Chrome CDP 固定标签 Operator 启动", 0.12)
        if trace:
            trace("bridge", "chrome_cdp_driver", "使用 Chrome CDP 固定标签 Operator 执行网页席位", {
                "requested_seats": requested,
                "uses_system_mouse": False,
                "uses_system_keyboard": False,
                "uses_system_clipboard": False,
            })
        return _run_driver_with_retries(
            runner=run_chrome_cdp_tabs,
            question=question,
            seats=requested,
            config=config,
            mode=mode,
            progress=progress,
            trace=trace,
            driver_label="Chrome CDP",
        )

    if not playwright_installed():
        if trace:
            trace("bridge", "runtime_missing", "Playwright 未安装，无法启动 web_dom", {})
        raise SeatBridgeError(
            "Playwright is not installed. Install the optional web bridge dependency first: "
            "pip install 'ai-judge[web-bridge]' && python -m playwright install chromium"
        )

    calibration = load_calibration()

    from playwright.sync_api import sync_playwright

    results: list[dict[str, Any]] = []
    total = max(1, len(requested))
    with sync_playwright() as playwright:
        for index, seat in enumerate(requested, 1):
            # P1.7: flash stop_event check — skip remaining seats when total timeout fires
            stop_event = config.get("_stop_event")
            if stop_event is not None and stop_event.is_set():
                if trace:
                    trace("bridge", "flash_stopped", f"flash 总时限到达，跳过剩余席位（含 {seat}）", {"seat": seat, "remaining": len(requested) - index + 1})
                item = _failed_result(seat, "flash_timeout", "Flash total timeout reached; seat skipped.")
                results.append(item)
                continue
            pct = 0.12 + 0.58 * (index - 1) / total
            if progress:
                progress(f"后台网页席位：{seat} ({index}/{total})", pct)
            if trace:
                trace("seat", "start", f"开始处理席位 {seat}", {"seat": seat, "index": index, "total": total})
            seat_config = _seat_config(config, seat)
            if not seat_config.get("enabled"):
                item = _failed_result(seat, "disabled", "Seat is not enabled in web_seats.json.")
                results.append(item)
                if trace:
                    trace("seat", "skip_disabled", f"{seat} 未启用", {"seat": seat, "error": item.get("error")})
                continue
            channel = str(seat_config.get("channel") or "web")
            driver = driver_for_bridge_seat({"channel": channel})
            calibration_entry = _calibration_entry(calibration, seat)
            if channel == "desktop":
                code, message = _desktop_collection_block(seat, seat_config)
                item = _failed_result(seat, code, message)
                results.append(item)
                if trace:
                    trace("seat", "skip_desktop_operator", f"{seat} 是桌面客户端席位，后台 Operator 未启用", {
                        "seat": seat,
                        "driver": driver.get("driver"),
                        "error": item.get("error"),
                    })
                continue
            if not (calibration_entry["status"] == "pass" and calibration_entry["fresh"] and driver["safe_background"]):
                item = _failed_result(seat, "needs_calibration", "Seat must pass calibration before deep background collection.")
                results.append(item)
                if trace:
                    trace("seat", "skip_calibration", f"{seat} 未通过校准，跳过深度收集", {
                        "seat": seat,
                        "driver": driver.get("driver"),
                        "calibration": calibration_entry,
                        "error": item.get("error"),
                    })
                continue
            try:
                item = _ask_one_seat(playwright, config, seat_config, seat, question, mode, trace=trace)
                results.append(item)
                if trace:
                    trace("seat", "complete", f"{seat} 收集完成", {
                        "seat": seat,
                        "ok": item.get("ok"),
                        "elapsed_seconds": item.get("elapsed_seconds"),
                        "response_chars": len(str(item.get("response") or "")),
                        "error": item.get("error"),
                    })
            except Exception as exc:  # pragma: no cover - external browser/webpage dependent
                item = _failed_result(seat, "browser_error", str(exc))
                results.append(item)
                if trace:
                    trace("seat", "browser_error", f"{seat} 浏览器收集异常", {"seat": seat, "error": item.get("error")})

    if progress:
        progress("网页席位收集完成，进入评分", 0.72)
    return annotate_execution_results(results, config=config)


def _run_driver_with_retries(
    runner: Callable[..., list[dict[str, Any]]],
    question: str,
    seats: list[str],
    config: dict[str, Any],
    mode: str,
    progress: Callable[[str, float], None] | None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None,
    driver_label: str,
) -> list[dict[str, Any]]:
    """Run a fixed-tab driver and retry transient collection failures per seat."""
    try:
        raw_results = runner(question=question, seats=seats, config=config, mode=mode, progress=progress, trace=trace)
    except Exception as exc:
        if trace:
            trace("bridge", "driver_exception", f"{driver_label} driver failed before returning seat results", {
                "driver": driver_label,
                "seats": seats,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        return annotate_execution_results(
            [
                _failed_result(
                    seat,
                    "web_collection_driver_exception",
                    f"{driver_label} driver failed before returning a structured result: {type(exc).__name__}: {exc}",
                )
                for seat in seats
            ],
            config=config,
        )

    results = annotate_execution_results(
        raw_results,
        config=config,
    )
    attempts = _retry_attempts(config)
    if attempts <= 0:
        return results

    for attempt in range(1, attempts + 1):
        retry_seats = [str(item.get("seat")) for item in results if _should_retry_result(item)]
        retry_seats = [seat for seat in retry_seats if seat in SEAT_PERSONAS]
        if not retry_seats:
            break
        if trace:
            trace(
                "bridge",
                "web_retry_start",
                f"{driver_label} 补跑慢席/波动席位 ({attempt}/{attempts})",
                {
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "seats": retry_seats,
                    "reason": "retryable_transient_web_collection_failure",
                },
            )
            # P3.6: per-seat retry trace
            for seat in retry_seats:
                trace("seat", "seat_retry_started",
                      f"{seat} 开始重试 ({attempt}/{attempts})",
                      {"seat": seat, "attempt": attempt, "max_attempts": attempts})
        # P1.7: flash stop_event check — skip retries when total timeout fires
        stop_event = config.get("_stop_event")
        if stop_event is not None and stop_event.is_set():
            break
        retry_config = dict(config)
        retry_config["_retry_run"] = True
        retry_timeout = config.get("retry_timeout_seconds") or config.get("timeout_seconds")
        if retry_timeout:
            retry_config["timeout_seconds"] = retry_timeout

        def retry_progress(step: str, pct: float) -> None:
            if not progress:
                return
            pct = max(0.0, min(1.0, pct))
            mapped = 0.74 + 0.22 * ((attempt - 1) + pct) / max(1, attempts)
            progress(f"补跑 {attempt}/{attempts}：{step}", min(0.96, mapped))

        retry_results = runner(
            question=question,
            seats=retry_seats,
            config=retry_config,
            mode=mode,
            progress=retry_progress,
            trace=trace,
        )
        results = annotate_execution_results(_merge_retry_results(results, retry_results, attempt), config=config)
        if trace:
            trace(
                "bridge",
                "web_retry_complete",
                f"{driver_label} 补跑完成 ({attempt}/{attempts})",
                {
                    "attempt": attempt,
                    "ok_count": sum(1 for item in retry_results if item.get("ok")),
                    "failed_count": sum(1 for item in retry_results if not item.get("ok")),
                    "seats": retry_seats,
                },
            )
    if progress:
        progress("网页席位补跑完成，进入评分", 0.96)
    return annotate_execution_results(results, config=config)


def _retry_attempts(config: dict[str, Any]) -> int:
    if config.get("retry_failed_seats") is False:
        return 0
    try:
        attempts = int(config.get("retry_attempts", 1))
    except Exception:
        attempts = 1
    return max(0, min(3, attempts))


def _should_retry_result(item: dict[str, Any]) -> bool:
    validity = item.get("execution_validity") if isinstance(item.get("execution_validity"), dict) else {}
    if item.get("ok") and validity.get("valid", True):
        return False
    error = item.get("error") or {}
    code = str(error.get("code") or validity.get("reason") or "")
    if code not in RETRYABLE_WEB_ERROR_CODES:
        return False
    retry_history = item.get("retry_history") or []
    return len(retry_history) < 3


def _merge_retry_results(
    original: list[dict[str, Any]],
    retry_results: list[dict[str, Any]],
    attempt: int,
) -> list[dict[str, Any]]:
    by_seat = {str(item.get("seat")): dict(item) for item in original}
    for retry_item in retry_results:
        seat = str(retry_item.get("seat") or "")
        previous = by_seat.get(seat)
        if not previous:
            by_seat[seat] = dict(retry_item)
            continue
        history = list(previous.get("retry_history") or [])
        history.append(_retry_snapshot(previous, attempt - 1))
        merged = dict(retry_item)
        merged["retry_attempts"] = attempt
        merged["retry_history"] = history
        if retry_item.get("ok") and not previous.get("ok"):
            merged["recovered_by_retry"] = True
        by_seat[seat] = merged
    return [by_seat.get(str(item.get("seat")), item) for item in original]


def _retry_snapshot(item: dict[str, Any], attempt: int) -> dict[str, Any]:
    error = item.get("error") or {}
    return {
        "attempt": attempt,
        "ok": bool(item.get("ok")),
        "error_code": error.get("code"),
        "error_message": error.get("message"),
        "response_chars": len(str(item.get("response") or "")),
        "elapsed_seconds": item.get("elapsed_seconds"),
    }


def _fixed_chrome_tab_available(seat_config: dict[str, Any], tabs: list[Any]) -> bool:
    """Return whether an open Chrome tab appears to match this seat."""
    return _matching_chrome_tab(seat_config, tabs) is not None


def _matching_chrome_tab(seat_config: dict[str, Any], tabs: list[Any]) -> Any | None:
    urls = _url_candidates(seat_config)
    labels = _match_labels(seat_config)
    domains = _match_domains(seat_config, urls)
    for tab in tabs:
        tab_url = str(getattr(tab, "url", "") or "")
        tab_title = str(getattr(tab, "title", "") or "")
        if any(url and tab_url.rstrip("/") == url.rstrip("/") for url in urls):
            return tab
        if any(domain and domain in tab_url.lower() for domain in domains):
            return tab
        if not _label_fallback_enabled(seat_config):
            continue
        haystack = f"{tab_title} {tab_url}".lower()
        if any(label and label in haystack for label in labels):
            return tab
    return None


def _is_xunfei_seat(seat_config: dict[str, Any], tab_url: str = "") -> bool:
    fields: list[str] = [
        str(seat_config.get("id") or ""),
        str(seat_config.get("seat") or ""),
        str(seat_config.get("provider") or ""),
        str(seat_config.get("name") or ""),
        str(seat_config.get("browser_label") or ""),
        str(tab_url or ""),
    ]
    fields.extend(_url_candidates(seat_config))
    fields.extend(str(value or "") for value in seat_config.get("match_domains") or [])
    haystack = " ".join(fields).lower()
    return any(marker in haystack for marker in ("xunfei", "xinghuo", "xfyun", "讯飞"))


def _seat_login_state(seat_config: dict[str, Any], tabs: list[Any]) -> dict[str, Any]:
    """Best-effort visible-tab login marker without reading cookies or private account data."""
    tab = _matching_chrome_tab(seat_config, tabs)
    if tab is None:
        return {"state": "missing", "title": "", "url": ""}
    title = str(getattr(tab, "title", "") or "")
    url = str(getattr(tab, "url", "") or "")
    # Query params can contain benign tracking values such as ``from_login=1``.
    # Do not let tracking/query strings trip the login wall detector.
    login_haystack = f"{title} {url.split('?', 1)[0]}".lower()
    haystack = f"{title} {url}".lower()
    error_haystack = f"{title} {url.split('?', 1)[0]}".lower()
    login_markers = (
        "/login", "/signin", "/sign_in", "/sign-in", "/auth", "accounts.google.com",
        "accounts.x.ai", "exchange-token-error", "/c/guest",
        "sign in", "signin", "sign_in", "log in", "logout",
        "登录", "登陆", "注册", "未登录", "请登录", "无法登录", "继续前往xai",
    )
    challenge_url_markers = (
        "captcha", "challenge", "turnstile", "cf_chl", "/verify", "/verification",
        "verify-human", "security-check",
    )
    challenge_title_markers = (
        "captcha", "human verification", "verify you are human", "checking your browser",
        "security check", "安全检查", "人机验证", "人机", "请完成验证",
    )
    error_markers = ("err_connection", "无法访问", "not found", "timeout", "出错了")
    restricted_markers = (
        "/restricted", "account hold", "account on hold", "restricted",
        "suspended", "blocked", "request a review",
    )
    error_404 = bool(re.search(r"(^|[^0-9])404([^0-9]|$)", error_haystack))
    url_lower = url.lower()
    title_lower = title.lower()
    if any(marker in url_lower for marker in challenge_url_markers) or any(marker in title_lower for marker in challenge_title_markers):
        state = "challenge_required"
    elif any(marker in haystack for marker in restricted_markers):
        state = "provider_account_restricted"
    elif any(marker in login_haystack for marker in login_markers):
        state = "login_required"
    elif any(marker in error_haystack for marker in error_markers) or error_404:
        state = "page_error"
    elif _is_xunfei_seat(seat_config, url) and "/desk" not in url.split("?", 1)[0].lower():
        state = "desk_auto_recoverable"
    else:
        state = "session_present"
    result = {
        "state": state,
        "title": title[:160],
        "url": url,
    }
    if state == "desk_auto_recoverable":
        result["required_url"] = "https://xinghuo.xfyun.cn/desk"
        result["message"] = "讯飞固定标签当前在首页；AI Judge 会在运行前安装临时路由守门并自动拉回 /desk。"
    return result


def _url_candidates(seat_config: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("url", "fresh_url", "fallback_url", "display_url"):
        value = str(seat_config.get(key) or "").strip()
        if value:
            urls.append(value)
    for value in seat_config.get("match_urls") or []:
        value = str(value or "").strip()
        if value:
            urls.append(value)
    return list(dict.fromkeys(urls))


def _match_domains(seat_config: dict[str, Any], urls: list[str]) -> list[str]:
    domains: list[str] = []
    for value in seat_config.get("match_domains") or []:
        value = str(value or "").strip().lower()
        if value:
            domains.append(value)
    for url in urls:
        domain = _domain(url)
        if domain:
            domains.append(domain)
    return list(dict.fromkeys(domains))


def _match_labels(seat_config: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for key in ("browser_label", "provider"):
        value = str(seat_config.get(key) or "").strip().lower()
        if value:
            labels.append(value)
    return list(dict.fromkeys(labels))


def _label_fallback_enabled(seat_config: dict[str, Any]) -> bool:
    return seat_config.get("allow_label_fallback", True) is not False and not bool(seat_config.get("strict_match_domains"))


def _domain(url: str) -> str:
    if "://" in url:
        url = url.split("://", 1)[1]
    return url.split("/", 1)[0].split("?", 1)[0].lower()


def _calibration_entry(calibration: dict[str, Any], seat: str) -> dict[str, Any]:
    raw = dict((calibration.get("seats") or {}).get(seat) or {})
    if not raw:
        return {
            "seat": seat,
            "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
            "status": "missing",
            "fresh": False,
            "calibrated_at": None,
            "age_hours": None,
            "error": None,
        }
    calibrated_at = raw.get("calibrated_at")
    age_hours = None
    fresh = False
    try:
        stamp = datetime.fromisoformat(str(calibrated_at).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)
        age_hours = round(age.total_seconds() / 3600, 2)
        fresh = age <= timedelta(hours=CALIBRATION_MAX_AGE_HOURS)
    except Exception:
        fresh = False
    raw.setdefault("seat", seat)
    raw.setdefault("seat_name", SEAT_PERSONAS.get(seat, {}).get("name", seat))
    raw.setdefault("status", "missing")
    raw["fresh"] = fresh
    raw["age_hours"] = age_hours
    return raw


def _readiness_reason(
    channel: str,
    enabled: bool,
    installed: bool,
    configured: bool,
    desktop_installed: bool,
    seat_config: dict[str, Any],
    calibration_entry: dict[str, Any],
    driver: dict[str, Any],
) -> str:
    if not enabled:
        return "disabled"
    if channel == "desktop":
        if not desktop_installed:
            return "desktop_app_missing"
        if _is_deepseek_desktop_seat(seat_config):
            return "deepseek_desktop_expert_operator_missing"
        if not driver.get("safe_background"):
            return "desktop_operator_pending"
    else:
        if not installed:
            return "playwright_missing"
        if not seat_config.get("url"):
            return "missing_url"
    if not configured:
        return "not_configured"
    if calibration_entry.get("status") == "missing":
        return "needs_calibration"
    if not calibration_entry.get("fresh"):
        return "calibration_stale"
    if calibration_entry.get("status") != "pass":
        error = calibration_entry.get("error") or {}
        return str(error.get("code") or "calibration_failed")
    return "ready"


def _calibrate_web_seat(
    playwright: Any,
    config: dict[str, Any],
    seat_config: dict[str, Any],
    seat: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.time()
    probe_config = dict(seat_config)
    probe_config["timeout_seconds"] = timeout_seconds
    result = _ask_one_seat(
        playwright=playwright,
        config=config,
        seat_config=probe_config,
        seat=seat,
        question="AI Judge bridge calibration. Please reply with READY only.",
        mode="flash",
    )
    if result.get("ok"):
        return {
            "seat": seat,
            "seat_name": SEAT_PERSONAS[seat]["name"],
            "status": "pass",
            "driver": "web_dom",
            "calibrated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - started, 2),
            "sample_chars": len(str(result.get("response") or "")),
            "error": None,
        }
    error = result.get("error") or {}
    return _calibration_failure(
        seat,
        str(error.get("code") or "unknown"),
        str(error.get("message") or "Calibration did not capture an answer."),
        driver="web_dom",
        elapsed_seconds=round(time.time() - started, 2),
    )


def _calibrate_desktop_seat(seat: str, seat_config: dict[str, Any]) -> dict[str, Any]:
    desktop_app = seat_config.get("desktop_app") or {}
    desktop_path = desktop_app.get("path")
    if not (desktop_path and Path(desktop_path).exists()):
        return _calibration_failure(seat, "desktop_app_missing", "Desktop app is not installed.", driver="desktop_operator")
    if seat == "deepseek" or _is_deepseek_desktop_seat(seat_config):
        return _calibration_failure(
            seat,
            "deepseek_desktop_expert_operator_missing",
            "DeepSeek native Mac desktop collection is not implemented with an expert-mode verifier yet. Use the browser DeepSeek expert-mode bridge, or add a dedicated AX desktop Operator that verifies 专家模式、深度思考、智能搜索 before submit.",
            driver="desktop_operator",
        )
    return _calibration_failure(
        seat,
        "desktop_operator_pending",
        "Desktop app exists, but a safe background Operator is not implemented yet.",
        driver="desktop_operator",
    )


def _calibration_failure(
    seat: str,
    code: str,
    message: str,
    driver: str = "web_dom",
    elapsed_seconds: float = 0,
) -> dict[str, Any]:
    return {
        "seat": seat,
        "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "status": "fail",
        "driver": driver,
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed_seconds,
        "error": {"code": code, "message": message},
    }


def _ask_one_seat(
    playwright: Any,
    config: dict[str, Any],
    seat_config: dict[str, Any],
    seat: str,
    question: str,
    mode: str,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    url = str(seat_config.get("url") or "").strip()
    if not url:
        return _failed_result(seat, "missing_url", "Seat URL is empty.")

    timeout_seconds = float(seat_config.get("timeout_seconds") or config.get("timeout_seconds") or 120)
    timeout_ms = int(timeout_seconds * 1000)
    headless = seat_config.get("headless")
    if headless is None:
        headless = bool(config.get("headless", True))

    profile_dir = Path(seat_config.get("profile_dir") or _profile_dir(config, seat))
    profile_dir.mkdir(parents=True, exist_ok=True)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=bool(headless),
        viewport={"width": 1360, "height": 920},
        args=["--disable-dev-shm-usage"],
    )
    started = time.time()
    try:
        page = context.pages[0] if context.pages else context.new_page()
        if trace:
            trace("browser", "context_started", f"{seat} 独立浏览器 profile 已启动", {
                "seat": seat,
                "headless": bool(headless),
                "profile_dir": str(profile_dir),
                "url": url,
        })
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        if trace:
            trace("browser", "page_loaded", f"{seat} 页面已加载", {"seat": seat, "url": url})
        prompt_id = f"AIJUDGE-{seat}-{time.time_ns()}"
        _humanized_sleep(config, seat_config, seat, "before_submit")
        if _quality_mode_prepare_required(seat):
            prepared = _prepare_playwright_submission_ui(page, prompt_id)
            if not _quality_mode_prepare_verified(seat, prepared):
                code, message = _quality_mode_failure(seat)
                if trace:
                    trace("seat", _quality_mode_trace_action(seat), _quality_mode_trace_message(seat), {
                        "seat": seat,
                        "prepared": prepared,
                        "code": code,
                        "required_quality_mode": _quality_mode_required_mode(seat),
                    })
                return _failed_result(seat, code, message)
        prompt = _seat_prompt(seat, question, mode)
        input_locator = _find_visible_locator(page, _selectors(config, seat_config, "input_selectors"), min(timeout_ms, 20000))
        if input_locator is None and _recover_playwright_page(page, config, seat_config, seat, "input_not_found", trace):
            input_locator = _find_visible_locator(page, _selectors(config, seat_config, "input_selectors"), min(timeout_ms, 20000))
        if input_locator is None:
            if trace:
                trace("browser", "input_not_found", f"{seat} 未找到输入框", {
                    "seat": seat,
                    "selectors": _selectors(config, seat_config, "input_selectors"),
                })
            return _failed_result(seat, "input_not_found", "Prompt input was not found. The seat may need login or selector tuning.")
        input_locator.fill(prompt, timeout=min(timeout_ms, 20000))
        _humanized_sleep(config, seat_config, seat, "after_write")
        if trace:
            trace("browser", "prompt_filled", f"{seat} 已写入专业提示词", {
                "seat": seat,
                "prompt_chars": len(prompt),
            })

        submit_locator = _find_visible_locator(page, _selectors(config, seat_config, "submit_selectors"), 5000)
        if submit_locator is not None:
            submit_locator.click(timeout=5000)
            _humanized_sleep(config, seat_config, seat, "after_click")
            if trace:
                trace("browser", "submit_clicked", f"{seat} 发送按钮已点击", {"seat": seat})
        else:
            page.keyboard.press("Enter")
            _humanized_sleep(config, seat_config, seat, "after_click")
            if trace:
                trace("browser", "submit_enter", f"{seat} 未找到发送按钮，改用 Enter 提交", {"seat": seat})

        answer = _wait_for_response_text(
            page=page,
            selectors=_selectors(config, seat_config, "response_selectors"),
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            settle_seconds=float(config.get("settle_seconds", 3)),
        )
        if not answer:
            if trace:
                trace("browser", "response_timeout", f"{seat} 未在超时时间内读回回答", {"seat": seat, "timeout_seconds": timeout_seconds})
            return _failed_result(
                seat,
                "slow_response_pending",
                "No assistant response was captured before timeout; the seat may still be generating and can be supplemented later.",
            )

        return {
            "seat": seat,
            "seat_name": SEAT_PERSONAS[seat]["name"],
            "ok": True,
            "url": url,
            "profile_dir": str(profile_dir),
            "elapsed_seconds": round(time.time() - started, 2),
            "response": answer[-8000:],
            "error": None,
        }
    finally:
        context.close()


def _recover_playwright_page(
    page: Any,
    config: dict[str, Any],
    seat_config: dict[str, Any],
    seat: str,
    reason: str,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> bool:
    """Reload an isolated browser tab once when a model page loses its composer."""
    try:
        attempts = int(seat_config.get("page_recovery_attempts") or config.get("page_recovery_attempts") or 0)
    except Exception:
        attempts = 0
    if attempts <= 0:
        return False
    try:
        page.reload(wait_until="domcontentloaded", timeout=15000)
        delay = _humanized_sleep(config, seat_config, seat, "after_reload")
        wait_seconds = float(seat_config.get("page_recovery_wait_seconds") or config.get("page_recovery_wait_seconds") or 8)
        page.wait_for_timeout(max(800, min(20000, int(wait_seconds * 1000))))
        if trace:
            trace("seat", "playwright_tab_recovery", f"{seat} 页面已刷新恢复", {
                "seat": seat,
                "reason": reason,
                "delay_seconds": round(delay, 2),
            })
        return True
    except Exception as exc:
        if trace:
            trace("seat", "playwright_tab_recovery_failed", f"{seat} 页面刷新恢复失败", {
                "seat": seat,
                "reason": reason,
                "error": str(exc),
            })
        return False


def _is_worldcup_prompt(question: str) -> bool:
    if not question:
        return False
    head = question[:5000]
    return any(marker in head for marker in WORLDCUP_PROMPT_MARKERS)


def _is_a_share_reduction_prompt(question: str) -> bool:
    if not question:
        return False
    head = question[:8000]
    return sum(1 for marker in A_SHARE_REDUCTION_PROMPT_MARKERS if marker in head) >= 2


def _compact_a_share_reduction_context(question: str, limit: int = 5200) -> str:
    text = re.sub(r"\n{3,}", "\n\n", question or "").strip()
    if len(text) <= limit:
        return text
    keep_patterns = (
        "硬性要求",
        "研究问题",
        "数据口径",
        "plan_events",
        "unique_stocks_with_director_plan",
        "early_complete",
        "unknown_completion_events",
        "valid_price_events",
        "upper_bound_ret_to_first2_high_pct",
        "ret_to_day1_open_pct",
        "ret_to_day1_close_pct",
        "ret_to_day2_open_pct",
        "ret_to_day2_close_pct",
        "ret_to_5d_close_pct",
        "ret_to_10d_close_pct",
        "ret_to_30d_close_pct",
        "trend_price_ok_events",
        "trend_status_counts",
        "first2_high_is_period_high",
        "ret_to_period_high_pct",
        "ret_to_period_end_close_pct",
        "period_max_drawdown_pct",
        "trend_classification_counts",
        "前 2 交易日完成样本",
        "老师解读",
        "事后上界",
        "可交易",
        "每个席位",
        "Round",
        "不得",
        "必须",
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    for line in lines:
        if any(pattern in line for pattern in keep_patterns):
            selected.append(line)
    compact_body = "\n".join(selected)
    if len(compact_body) < 1800:
        compact_body = f"{text[:2200]}\n...\n{text[-1800:]}"
    header = (
        "AI Judge A股董事减持长材料压缩版。原始问题包含全量 CSV/JSON 统计，"
        "本席位使用无未来函数的压缩事实包作答；不得虚构来源或把未知当作否定。\n\n"
    )
    return (header + compact_body)[:limit]


def _a_share_reduction_short_prompt(seat: str, question: str, mode: str) -> str:
    persona = SEAT_PERSONAS.get(seat, {})
    seat_name = persona.get("name") or seat
    context = _compact_a_share_reduction_context(question)
    return (
        f"AI Judge A股董事减持数据优先裁决短版输入。你是 {seat_name}（seat_id={seat}）。\n"
        "请基于下面压缩事实包完成回答，必须区分事实、判断、假设和下一轮验证。\n"
        "如果你没有联网能力，请明确 web_search_used=false；禁止编造来源。\n\n"
        f"{context}\n\n"
        "请按以下结构输出中文：\n"
        "1. 立场：支持 / 不支持 / 暂不充分。\n"
        "2. 数据审计：可信统计、缺失统计、可能补丁。\n"
        "3. 未来函数审计：哪些收益只是事后上界，哪些是可交易现实。\n"
        "4. 二轮共振：你要追问其他席位的 2-3 个问题，以及看完他人证据后的复判条件。\n"
        "5. 老师解读素材：用通俗话解释一个关键误区。\n"
        "6. 下一轮样本外验证方案。\n"
        f"当前模式：{mode}。"
    )


def _compact_worldcup_context(question: str, limit: int = 1800) -> str:
    text = re.sub(r"\n{3,}", "\n\n", question or "").strip()
    if len(text) <= limit:
        return text
    keep_patterns = (
        "Run #6",
        "本轮必须",
        "14 席",
        "Claude",
        "Grok",
        "MiniMax",
        "文心",
        "Zhipu",
        "贷款",
        "奖励",
        "本轮主要下注对象",
        "当前预测池基线",
        "输出必须包含",
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    for line in lines:
        if any(pattern in line for pattern in keep_patterns):
            selected.append(line)
    compact = "\n".join(selected)
    if len(compact) < 500:
        compact = f"{text[:900]}\n...\n{text[-700:]}"
    return compact[:limit]


def _worldcup_short_prompt(seat: str, question: str, mode: str) -> str:
    persona = SEAT_PERSONAS.get(seat, {})
    seat_name = persona.get("name") or seat
    context = _compact_worldcup_context(question)
    return (
        f"AI Judge 世界杯预测池短回执。你是 {seat_name}（seat_id={seat}）。\n"
        "任务：本轮必须给出真实赛事投注判断；如果网页、额度、登录或信息不足，也要输出状态和原因，不要空白或只说无法完成。\n\n"
        "背景摘要：\n"
        f"{context}\n\n"
        "请只输出中文，尽量短，不要长篇推理，不要 Markdown 表格。\n"
        "必须输出一个 ```json 代码块，字段如下：\n"
        "{\n"
        '  "seat": "seat_id",\n'
        '  "seat_status": "real_bet | account_limited | auth_required | page_blocked | info_gap",\n'
        '  "loan_decision": {"apply": true/false, "amount_gp": 0, "reason": "一句话"},\n'
        '  "model_account": {"available_gp": 0, "max_loss_gp": 0, "strategy": "守榜/追赶/翻盘"},\n'
        '  "bet_ledger": [{"match": "比赛", "pick": "投注方向", "stake_gp": 0, "confidence": "高/中/低", "conditions": "撤单/加注条件"}],\n'
        '  "betting_thought": "为什么这么押，尤其说明是否修正小球假设",\n'
        '  "source_cards": [{"source_type": "阵容/伤停/赔率/赛程/战术/天气/旅行", "claim": "你用到的信息", "need_human_confirm": true/false}],\n'
        '  "risk_rules": ["止损/撤单/不下注条件"],\n'
        '  "opponent_context": "你在追谁或防谁",\n'
        '  "settlement_pending": ["需要盘口、赔率、让球线或赛果确认的项目"]\n'
        "}\n"
        "JSON 后再用一句中文总结你的本轮投注态度。"
        f"\n当前模式：{mode}。"
    )


def _seat_prompt(seat: str, question: str, mode: str) -> str:
    # Werewolf / game prompts are self-contained; skip jury persona injection.
    head = question[:200] if question else ""
    if "AI Judge 狼人杀" in head or "AI Judge 的模型狼人杀" in head:
        return question
    if "AI_JUDGE_RERUN_MARKER:POOL_" in str(question or ""):
        return question
    if _is_worldcup_prompt(question) and seat in WORLDCUP_FRAGILE_SHORT_PROMPT_SEATS:
        return _worldcup_short_prompt(seat, question, mode)
    if _is_a_share_reduction_prompt(question) and seat in LONG_PROMPT_FRAGILE_SEATS and len(question) > 12000:
        return _a_share_reduction_short_prompt(seat, question, mode)
    base = render_jury_prompt(seat, question) or question
    is_resonance_followup = "[AIJUDGE_RESONANCE_FOLLOWUP]" in question
    if is_resonance_followup:
        return (
            f"{base}\n\n"
            "请作为 AI Judge 的同一个独立席位执行第二轮共振回答。输出要求：\n"
            "1. 逐条回答上一轮你提出的共振提问，先给结论再给理由。\n"
            "2. 明确带入用户角色，说明如果你是用户会如何取舍、推进和验收。\n"
            "3. 给出详细技术方案：模块拆分、数据流、接口/状态字段、执行步骤、测试与回滚。\n"
            "4. 保留事实、假设、建议三层隔离，不要覆盖第一轮原文。\n"
            f"5. 当前模式：{mode}。这是第二轮方案执行，不需要继续提出新问题。"
        )
    return (
        f"{base}\n\n"
        "请作为 AI Judge 的一个独立席位回答。输出要求：\n"
        "1. 先给出明确立场：支持 / 条件支持 / 反对 / 信息不足。\n"
        "2. 给出 3 条理由，每条尽量包含可验证依据或需要验证的假设。\n"
        "3. 给出最大风险和最小下一步。\n"
        "4. 单独输出「共振提问」：站在用户目标和你的席位专长上，提出 3-5 个能显著补强方案的问题。\n"
        f"5. 当前模式：{mode}。请保持结论紧凑，避免套话。"
    )


def _prepare_playwright_submission_ui(page: Any, prompt_id: str) -> dict[str, Any]:
    def evaluate_once() -> dict[str, Any]:
        try:
            raw = page.evaluate(_build_prepare_submission_ui_js(prompt_id))
        except Exception as exc:
            return {"ok": False, "error": str(exc), "clicked_names": []}
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except Exception:
                return {"ok": False, "error": raw, "clicked_names": []}
            return parsed if isinstance(parsed, dict) else {"ok": False, "raw": parsed, "clicked_names": []}
        return raw if isinstance(raw, dict) else {"ok": False, "raw": raw, "clicked_names": []}

    prepared = evaluate_once()
    if prepared.get("clicked"):
        page.wait_for_timeout(800)
    if prepared.get("needs_followup"):
        followup = evaluate_once()
        prepared["followup"] = followup
        if followup.get("clicked"):
            page.wait_for_timeout(800)
    return prepared


def _find_visible_locator(page: Any, selectors: list[str], timeout_ms: int) -> Any | None:
    deadline = time.time() + max(timeout_ms, 1000) / 1000
    while time.time() < deadline:
        for selector in selectors:
            locator = page.locator(selector)
            try:
                count = min(locator.count(), 5)
            except Exception:
                count = 0
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible(timeout=250):
                        return candidate
                except Exception:
                    continue
        time.sleep(0.35)
    return None


def _wait_for_response_text(
    page: Any,
    selectors: list[str],
    prompt: str,
    timeout_seconds: float,
    settle_seconds: float,
) -> str:
    time.sleep(settle_seconds)
    deadline = time.time() + timeout_seconds
    last_text = ""
    prompt_head = prompt[:120]
    while time.time() < deadline:
        for selector in selectors:
            try:
                texts = [text.strip() for text in page.locator(selector).all_inner_texts() if text.strip()]
            except Exception:
                texts = []
            for text in reversed(texts):
                if len(text) < 40:
                    continue
                if prompt_head and prompt_head in text:
                    continue
                if text != last_text:
                    last_text = text
                if len(text) >= 120:
                    return text
        time.sleep(1.0)
    return last_text


def _selectors(config: dict[str, Any], seat_config: dict[str, Any], key: str) -> list[str]:
    value = seat_config.get(key) or config.get(key) or []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if str(item).strip()]


def _seat_config(config: dict[str, Any], seat: str) -> dict[str, Any]:
    seats = config.get("seats") or {}
    merged = dict(default_config()["seats"].get(seat, {}))
    merged.update(seats.get(seat, {}))
    return merged


def _profile_dir(config: dict[str, Any], seat: str) -> Path:
    root = Path(config.get("profile_root") or PROFILE_ROOT).expanduser()
    if not root.is_absolute():
        root = (_PROJECT_ROOT / root).resolve()
    return root / seat


def _desktop_app_running(app_name: str | None) -> bool:
    if not app_name:
        return False
    try:
        result = subprocess.run(
            ["osascript", "-e", f'tell application "System Events" to get name of every process whose name is "{app_name}"'],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return False
    return app_name in result.stdout


def _failed_result(seat: str, code: str, message: str) -> dict[str, Any]:
    result = {
        "seat": seat,
        "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "ok": False,
        "url": "",
        "profile_dir": "",
        "elapsed_seconds": 0,
        "response": "",
        "error": {"code": code, "message": message},
    }
    if code == "slow_response_pending":
        result["supplementable"] = True
    return result


def _is_deepseek_desktop_seat(seat_config: dict[str, Any]) -> bool:
    values = [
        seat_config.get("provider"),
        seat_config.get("browser_label"),
        (seat_config.get("desktop_app") or {}).get("name"),
        (seat_config.get("desktop_app") or {}).get("bundle_id"),
        (seat_config.get("desktop_app") or {}).get("path"),
    ]
    haystack = " ".join(str(value or "") for value in values).lower()
    return "deepseek" in haystack or "深度求索" in haystack


def _desktop_collection_block(seat: str, seat_config: dict[str, Any]) -> tuple[str, str]:
    if seat == "deepseek" or _is_deepseek_desktop_seat(seat_config):
        return (
            "deepseek_desktop_expert_operator_missing",
            "DeepSeek native Mac desktop collection is blocked because no desktop Operator verifies 专家模式、深度思考、智能搜索 before submission. Use the browser DeepSeek expert-mode bridge until the native AX Operator exists.",
        )
    return (
        "desktop_bridge_pending",
        "Desktop client collection is mapped but not automated in the background collector yet.",
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="AI Judge isolated web-seat bridge")
    parser.add_argument("--status", action="store_true", help="Print bridge readiness JSON")
    parser.add_argument("--init-config", action="store_true", help="Write data/web_seats.json template")
    parser.add_argument("--calibrate", action="store_true", help="Run calibration probes and persist results")
    parser.add_argument("--seats", help="Comma-separated seats for calibration")
    parser.add_argument("--timeout-seconds", type=float, default=12, help="Per-seat calibration timeout")
    parser.add_argument("--config", help="Custom bridge config path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing config when initializing")
    args = parser.parse_args()

    if args.init_config:
        path = write_default_config(Path(args.config) if args.config else None, overwrite=args.overwrite)
        print(path)
        return 0

    if args.calibrate:
        seats = [item.strip() for item in (args.seats or "").split(",") if item.strip()] or None
        print(json.dumps(calibrate_bridge(seats=seats, config_path=args.config, timeout_seconds=args.timeout_seconds), ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(bridge_status(args.config), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
