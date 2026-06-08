#!/usr/bin/env python3
"""Chrome DevTools Protocol fixed-tab bridge for AI Judge."""

from __future__ import annotations

import json
import os
import sys
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote, urlparse
from dataclasses import dataclass
from typing import Any, Callable

import requests



# P3.6: per-seat SLA constants (seconds) — thread-safe, no signal dependency
_SEAT_SLA = {
    "submit_stage": 60,       # max time for fill+send per seat
    "answer_wait": 180,       # per-seat answer poll timeout
    "readback": 30,           # final capture attempt
    "total_per_seat": 240,    # absolute per-seat deadline
    "max_retry": 1,           # retry once on transient failure
}
_SEAT_POLL_INTERVAL = 4       # seconds between answer polls

from core.seat_personas import SEAT_PERSONAS
from bridges.chrome_fixed_tab_bridge import (
    _build_capture_js,
    _build_clear_blocking_ui_js,
    _build_prepare_submission_ui_js,
    _append_prepare_followup,
    _capture_acceptance,
    _deepseek_prepare_verified,
    _doubao_prepare_verified,
    _failed_result,
    _humanized_sleep,
    _page_state_needs_reload,
    _response_text_from_capture,
    _seat_config,
    _seat_prompt,
)


DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:9222"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@contextmanager
def _local_cdp_proxy_bypass():
    """Keep local DevTools websocket traffic off the user's HTTP proxy."""
    proxy_keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
    saved = {key: os.environ.get(key) for key in proxy_keys}
    saved_no_proxy = os.environ.get("NO_PROXY")
    try:
        for key in proxy_keys:
            os.environ.pop(key, None)
        no_proxy = [item.strip() for item in (saved_no_proxy or "").split(",") if item.strip()]
        for host in ("127.0.0.1", "localhost", "::1"):
            if host not in no_proxy:
                no_proxy.append(host)
        os.environ["NO_PROXY"] = ",".join(no_proxy)
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if saved_no_proxy is None:
            os.environ.pop("NO_PROXY", None)
        else:
            os.environ["NO_PROXY"] = saved_no_proxy


@dataclass
class CDPTab:
    title: str
    url: str
    page: Any | None = None


def ensure_chrome_cdp_awake(
    config: dict[str, Any] | None = None,
    *,
    open_tabs: bool = True,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Wake the dedicated AI Judge Chrome CDP bridge without killing the user's Chrome."""
    config = config or {}
    endpoint = _endpoint(config)
    status = chrome_cdp_status(config)
    bypass_cooldown = False
    if status.get("reason") in {"wrong_cdp_profile", "profile_marker_missing"} and config.get("auto_terminate_wrong_cdp_profile", True):
        terminated = _terminate_cdp_process(status.get("process") or {}, trace)
        bypass_cooldown = bool(terminated)
        status = chrome_cdp_status(config)
    if status.get("available"):
        opened = _ensure_enabled_cdp_tabs(config, trace) if open_tabs else []
        result = {"ok": True, "woke": False, "endpoint": endpoint, "opened_tabs": opened, "status": status}
        _write_cdp_state(config, result)
        return result

    if config.get("auto_wake_cdp") is False:
        result = {"ok": False, "woke": False, "endpoint": endpoint, "reason": status.get("reason"), "status": status}
        _write_cdp_state(config, result)
        return result

    if not bypass_cooldown and _cdp_wake_in_cooldown(config):
        result = {
            "ok": False,
            "woke": False,
            "endpoint": endpoint,
            "reason": "wake_cooldown",
            "status": status,
        }
        _write_cdp_state(config, result)
        return result

    _write_cdp_state(config, {"ok": False, "woke": False, "endpoint": endpoint, "reason": "wake_starting"})
    profile_dir = _cdp_profile_dir(config)
    profile_dir.mkdir(parents=True, exist_ok=True)
    parsed = urlparse(endpoint)
    port = parsed.port or int(str(endpoint).rsplit(":", 1)[-1].split("/", 1)[0])
    chrome_args = [
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        "--disable-features=DialMediaRouteProvider,MediaRouter",
    ]
    launch_strategy = str(config.get("chrome_launch_strategy") or "open_app").strip().lower()
    if sys.platform == "darwin" and launch_strategy == "open_app" and not config.get("chrome_binary"):
        cmd = ["/usr/bin/open", "-na", "Google Chrome", "--args", *chrome_args]
        launch_label = "macos_open_app"
    else:
        chrome_bin = str(config.get("chrome_binary") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        cmd = [chrome_bin, *chrome_args]
        launch_label = "chrome_binary"
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        if trace:
            trace("chrome", "cdp_wake_launch", "唤醒 AI Judge 专用 Chrome CDP", {
                "endpoint": endpoint,
                "profile_dir": str(profile_dir),
                "launch_strategy": launch_label,
                "kill_user_chrome": False,
            })
    except Exception as exc:
        result = {"ok": False, "woke": False, "endpoint": endpoint, "reason": "launch_failed", "error": str(exc), "launch_strategy": launch_label}
        _write_cdp_state(config, result)
        return result

    deadline = time.time() + float(config.get("auto_wake_wait_seconds") or 25)
    while time.time() < deadline:
        time.sleep(0.75)
        status = chrome_cdp_status(config)
        if status.get("available"):
            opened = _ensure_enabled_cdp_tabs(config, trace) if open_tabs else []
            result = {"ok": True, "woke": True, "endpoint": endpoint, "opened_tabs": opened, "status": status, "launch_strategy": launch_label}
            _write_cdp_state(config, result)
            return result
    result = {"ok": False, "woke": True, "endpoint": endpoint, "reason": "wake_timeout", "status": chrome_cdp_status(config), "launch_strategy": launch_label}
    _write_cdp_state(config, result)
    return result


def chrome_cdp_status(config: dict[str, Any] | None = None) -> dict[str, Any]:
    endpoint = _endpoint(config)
    process = _cdp_process_info(config)
    if config and config.get("strict_chrome_profile_guard", True):
        marker = _profile_marker_status(config)
        if not marker.get("ok"):
            return {
                "available": False,
                "reason": "profile_marker_missing",
                "message": marker.get("message"),
                "endpoint": endpoint,
                "process": process,
                "profile_marker": marker,
            }
        if process.get("pid") and process.get("profile_match") is False:
            return {
                "available": False,
                "reason": "wrong_cdp_profile",
                "message": "Chrome CDP port is owned by a non AI Judge profile.",
                "endpoint": endpoint,
                "process": process,
                "profile_marker": marker,
            }
    try:
        version = _cdp_get_json(f"{endpoint}/json/version", timeout=2)
        tabs = _cdp_get_json(f"{endpoint}/json/list", timeout=2)
    except Exception as exc:
        return {"available": False, "reason": "cdp_unavailable", "message": str(exc), "endpoint": endpoint}
    return {
        "available": True,
        "reason": "ready",
        "endpoint": endpoint,
        "browser": version.get("Browser"),
        "tab_count": len(tabs) if isinstance(tabs, list) else 0,
        "process": process,
    }


def list_cdp_tabs(config: dict[str, Any] | None = None) -> list[CDPTab]:
    endpoint = _endpoint(config)
    tabs = _cdp_get_json(f"{endpoint}/json/list", timeout=3)
    return [
        CDPTab(title=str(tab.get("title") or ""), url=str(tab.get("url") or ""))
        for tab in tabs
        if tab.get("type") == "page"
    ]


def _cdp_state_path(config: dict[str, Any] | None = None) -> Path:
    value = str((config or {}).get("chrome_cdp_state_path") or "").strip()
    return Path(value).expanduser() if value else _PROJECT_ROOT / "data" / "chrome_cdp_bridge_state.json"


def _cdp_profile_dir(config: dict[str, Any] | None = None) -> Path:
    value = str((config or {}).get("chrome_cdp_profile_dir") or "").strip()
    return Path(value).expanduser() if value else _PROJECT_ROOT / "data" / "chrome-profile"


def _profile_marker_status(config: dict[str, Any] | None = None) -> dict[str, Any]:
    if not (config or {}).get("chrome_profile_marker_required", True):
        return {"ok": True, "required": False}
    marker_value = str((config or {}).get("chrome_profile_marker_path") or "").strip()
    marker_path = Path(marker_value).expanduser() if marker_value else _cdp_profile_dir(config) / "AI_JUDGE_DEDICATED_PROFILE.txt"
    if not marker_path.exists():
        return {"ok": False, "required": True, "path": str(marker_path), "message": "Dedicated AI Judge profile marker is missing."}
    try:
        content = marker_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"ok": False, "required": True, "path": str(marker_path), "message": str(exc)}
    if "AI Judge bridge" not in content and "AI Judge" not in content:
        return {"ok": False, "required": True, "path": str(marker_path), "message": "Dedicated profile marker does not identify AI Judge."}
    return {"ok": True, "required": True, "path": str(marker_path)}


def _cdp_process_info(config: dict[str, Any] | None = None) -> dict[str, Any]:
    endpoint = _endpoint(config)
    parsed = urlparse(endpoint)
    port = parsed.port or int(str(endpoint).rsplit(":", 1)[-1].split("/", 1)[0])
    pid = _cdp_listen_pid(port)
    expected = _cdp_profile_dir(config)
    if not pid:
        return {"pid": None, "port": port, "expected_profile_dir": str(expected), "profile_match": None}
    command = _process_command(pid)
    actual_profile = _profile_dir_from_command(command)
    profile_match = None
    if actual_profile:
        profile_match = _same_path(actual_profile, expected)
    return {
        "pid": pid,
        "port": port,
        "command": command,
        "profile_dir": str(actual_profile) if actual_profile else "",
        "expected_profile_dir": str(expected),
        "profile_match": profile_match,
    }


def _cdp_listen_pid(port: int) -> int | None:
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fp"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            return int(line[1:])
    return None


def _process_command(pid: int) -> str:
    try:
        result = subprocess.run(
            ["ps", "eww", "-p", str(pid)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )
    except Exception:
        return ""
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines[-1] if len(lines) >= 2 else ""


def _profile_dir_from_command(command: str) -> Path | None:
    marker = "--user-data-dir="
    start = command.find(marker)
    if start < 0:
        return None
    value_start = start + len(marker)
    remainder = command[value_start:]
    end_candidates = [index for index in (remainder.find(" --"), remainder.find(" http://"), remainder.find(" https://")) if index >= 0]
    value = remainder[:min(end_candidates)] if end_candidates else remainder
    value = value.strip().strip("\"'")
    return Path(value).expanduser() if value else None


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except Exception:
        return str(left.expanduser()) == str(right.expanduser())


def _terminate_cdp_process(process: dict[str, Any], trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None) -> bool:
    pid = process.get("pid")
    try:
        pid_int = int(pid)
    except Exception:
        return False
    if pid_int <= 1:
        return False
    try:
        os.kill(pid_int, signal.SIGTERM)
        if trace:
            trace("chrome", "wrong_cdp_profile_terminated", "终止占用 9333 的错误 Chrome profile", {
                "pid": pid_int,
                "profile_dir": process.get("profile_dir"),
                "expected_profile_dir": process.get("expected_profile_dir"),
            })
    except Exception:
        return False
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(pid_int, 0)
        except OSError:
            return True
        time.sleep(0.25)
    return True


def _write_cdp_state(config: dict[str, Any] | None, payload: dict[str, Any]) -> None:
    try:
        path = _cdp_state_path(config)
        path.parent.mkdir(parents=True, exist_ok=True)
        current: dict[str, Any] = {}
        if path.exists():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                current = {}
        current.update(payload)
        current["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if payload.get("reason") == "wake_starting":
            current["last_launch_at"] = time.time()
        elif payload.get("woke"):
            current.setdefault("last_launch_at", time.time())
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _cdp_wake_in_cooldown(config: dict[str, Any] | None = None) -> bool:
    path = _cdp_state_path(config)
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        last = float(payload.get("last_launch_at") or 0)
    except Exception:
        return False
    cooldown = float((config or {}).get("auto_wake_cooldown_seconds") or 20)
    return last > 0 and time.time() - last < cooldown


def _ensure_enabled_cdp_tabs(
    config: dict[str, Any],
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[str]:
    try:
        tabs = list_cdp_tabs(config)
    except Exception:
        tabs = []
    endpoint = _endpoint(config)
    opened: list[str] = []
    for seat, seat_config in (config.get("seats") or {}).items():
        if not seat_config.get("enabled") or str(seat_config.get("channel") or "web") != "web":
            continue
        if _match_tab(seat_config, tabs):
            continue
        url = str(seat_config.get("fresh_url") or seat_config.get("url") or seat_config.get("fallback_url") or "").strip()
        if not url:
            continue
        try:
            encoded = quote(url, safe=":/?&=%#")
            session = requests.Session()
            session.trust_env = False
            response = session.put(f"{endpoint}/json/new?{encoded}", timeout=10)
            response.raise_for_status()
            opened.append(seat)
            try:
                tabs = list_cdp_tabs(config)
            except Exception:
                pass
            if trace:
                trace("seat", "cdp_fixed_tab_opened", f"{seat} 固定标签已补开", {"seat": seat, "url": url})
        except Exception as exc:
            if trace:
                trace("seat", "cdp_fixed_tab_open_failed", f"{seat} 固定标签补开失败", {
                    "seat": seat,
                    "url": url,
                    "error": str(exc),
                })
    return opened


def run_chrome_cdp_tabs(
    question: str,
    seats: list[str],
    config: dict[str, Any],
    mode: str = "flash",
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    status = chrome_cdp_status(config)
    if not status.get("available") and config.get("auto_wake_cdp", True):
        wake = ensure_chrome_cdp_awake(config, open_tabs=bool(config.get("auto_wake_open_tabs", True)), trace=trace)
        status = chrome_cdp_status(config)
        status["wake"] = wake
    if trace:
        trace("chrome", "cdp_probe", "检测 Chrome CDP 通道", status)
    if not status.get("available"):
        return [
            _failed_result(seat, str(status.get("reason") or "cdp_unavailable"), str(status.get("message") or "Chrome CDP is not available."))
            for seat in seats
        ]

    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    requested = [seat for seat in seats if seat in SEAT_PERSONAS]
    submissions: dict[str, dict[str, Any]] = {}
    total = max(1, len(requested))
    timeout_seconds = float(config.get("timeout_seconds") or 180)

    with sync_playwright() as playwright:
        cdp_connect_timeout_ms = int(float(config.get("cdp_connect_timeout_seconds") or 20) * 1000)
        with _local_cdp_proxy_bypass():
            browser = playwright.chromium.connect_over_cdp(_connect_endpoint(config), timeout=cdp_connect_timeout_ms)
        pages = [page for context in browser.contexts for page in context.pages]
        for page in pages:
            try:
                page.set_default_timeout(int(float(config.get("cdp_default_timeout_seconds") or 8) * 1000))
                page.set_default_navigation_timeout(int(float(config.get("cdp_navigation_timeout_seconds") or 15) * 1000))
            except Exception:
                pass
        tabs = [CDPTab(title=page.title(), url=page.url, page=page) for page in pages]
        if trace:
            trace("chrome", "cdp_tabs_listed", "读取当前 Chrome CDP 标签页", {
                "count": len(tabs),
                "tabs": [{"title": tab.title, "url": tab.url} for tab in tabs],
            })

        # P3.6: per-seat SLA — thread-safe timeout via threading, no signal dependency
        seat_submit_timeout = int(float(config.get("seat_submit_timeout_seconds") or _SEAT_SLA["submit_stage"]))
        per_seat_deadline = int(float(config.get("seat_total_timeout_seconds") or _SEAT_SLA["total_per_seat"]))
        for index, seat in enumerate(requested, 1):
            seat_config = _seat_config(config, seat)
            if not seat_config.get("enabled"):
                submissions[seat] = _failed_result(seat, "disabled", "Seat is disabled.")
                continue
            if str(seat_config.get("channel") or "web") == "desktop":
                submissions[seat] = _failed_result(
                    seat,
                    "desktop_operator_pending",
                    "Desktop Operator is mapped but not enabled for safe background collection.",
                )
                continue
            tab = _match_tab(seat_config, tabs)
            if (tab is None or tab.page is None) and config.get("open_missing_fixed_tabs", True):
                recovered_page = _open_missing_cdp_tab(browser, seat_config, seat, trace)
                if recovered_page is not None:
                    tab = CDPTab(title=_safe_page_title(recovered_page), url=recovered_page.url, page=recovered_page)
                    tabs.append(tab)
            if tab is None or tab.page is None:
                submissions[seat] = _failed_result(seat, "fixed_tab_not_found", "No Chrome CDP tab matched this seat URL/title.")
                if trace:
                    trace("seat", "cdp_tab_not_found", f"{seat} 未找到 Chrome CDP 标签", {"seat": seat, "url": seat_config.get("url")})
                continue

            page = tab.page
            prompt = _seat_prompt(seat, question, mode)
            prompt_id = f"AIJUDGE-{seat}-{time.time_ns()}"
            prompt_with_marker = (
                f"{prompt}\n\n"
                "重要：不要只进行思考，必须在最终回答区域输出正文。请将你的最终答案完整包裹在以下两行标记之间，"
                "标记必须原样输出，标记外不要输出正文。不要输出（你的最终答案）这几个占位字，请替换成你的实际回答：\n"
                f"[AIJUDGE_ANSWER_START:{prompt_id}]\n"
                "你的最终答案\n"
                f"[AIJUDGE_ANSWER_END:{prompt_id}]\n\n"
                f"[trace_id: {prompt_id}]"
            )
            if progress:
                progress(f"Chrome CDP 提交：{seat} ({index}/{total})", 0.14 + 0.22 * index / total)
            if trace:
                trace("seat", "cdp_submit_start", f"{seat} CDP 标签开始输入提示词", {
                    "seat": seat,
                    "title": tab.title,
                    "url": tab.url,
                    "prompt_chars": len(prompt_with_marker),
                })
            # P3.6: per-seat timeout via threading — no signal, safe in daemon threads
            seat_timeout_flag = threading.Event()
            seat_watchdog = threading.Timer(seat_submit_timeout, lambda: seat_timeout_flag.set())
            seat_watchdog.daemon = True
            seat_watchdog.start()
            seat_deadline = time.time() + per_seat_deadline
            try:
                page.bring_to_front()
                _humanized_sleep(config, seat_config, seat, "before_submit")
                fresh_url = str(seat_config.get("fresh_url") or "").strip()
                if fresh_url and config.get("fresh_conversation_per_run", False):
                    try:
                        fresh_timeout_ms = int(float(config.get("fresh_navigation_timeout_seconds") or 12) * 1000)
                        page.goto(fresh_url, wait_until="domcontentloaded", timeout=fresh_timeout_ms)
                        _humanized_sleep(config, seat_config, seat, "after_reload")
                        page.wait_for_timeout(int(float(config.get("fresh_load_seconds") or 3.0) * 1000))
                    except Exception as exc:
                        if trace:
                            trace("seat", "cdp_fresh_navigation_skipped", f"{seat} 新会话跳转超时，继续使用当前固定标签", {
                                "seat": seat,
                                "url": page.url,
                                "fresh_url": fresh_url,
                                "error": str(exc),
                            })
                preflight = _clear_or_recover_page(page, config, seat_config, seat, "preflight", trace)
                prepared = _prepare_submission_ui(page, prompt_id)
                if prepared.get("clicked"):
                    _humanized_sleep(config, seat_config, seat, "after_click")
                prepare_attempt = 1
                max_prepare_attempts = int(float(config.get("mode_prepare_max_attempts") or 4))
                while prepared.get("needs_followup") and prepare_attempt < max_prepare_attempts:
                    followup = _prepare_submission_ui(page, prompt_id)
                    _append_prepare_followup(prepared, followup)
                    prepare_attempt += 1
                    if followup.get("clicked"):
                        _humanized_sleep(config, seat_config, seat, "after_click")
                    if trace:
                        trace("seat", "cdp_submission_ui_prepare_followup", f"{seat} CDP 提交前模式第 {prepare_attempt} 次确认", {
                            "seat": seat,
                            "prepared": prepared,
                        })
                    if seat == "deepseek" and _deepseek_prepare_verified(prepared):
                        break
                    if seat == "doubao" and _doubao_prepare_verified(prepared):
                        break
                    if not followup.get("needs_followup"):
                        break
                if seat == "deepseek" and not _deepseek_prepare_verified(prepared):
                    submissions[seat] = _failed_result(
                        seat,
                        "deepseek_expert_mode_not_verified",
                        "DeepSeek expert mode, 深度思考, and 智能搜索 were not all verified before submission; the bridge refused to collect a fast-mode answer.",
                    )
                    if trace:
                        trace("seat", "deepseek_expert_mode_blocked", f"{seat} 未确认专家模式，拒绝提交", {
                            "seat": seat,
                            "prepared": prepared,
                        })
                    continue
                if seat == "doubao" and not _doubao_prepare_verified(prepared):
                    submissions[seat] = _failed_result(
                        seat,
                        "doubao_expert_mode_not_verified",
                        "Doubao expert/super mode was not verified before submission; the bridge refused to collect a fast-mode answer.",
                    )
                    if trace:
                        trace("seat", "doubao_expert_mode_blocked", f"{seat} 未确认专家/超能模式，拒绝提交", {
                            "seat": seat,
                            "prepared": prepared,
                        })
                    continue
                before = _capture_page(page, prompt_id)
                fill_result = _fill_prompt(page, prompt_with_marker)
                _humanized_sleep(config, seat_config, seat, "after_write")
                send_result = _send_prompt(page)
                _humanized_sleep(config, seat_config, seat, "after_click")
                submission_confirmed = bool(send_result.get("ok"))
                submissions[seat] = {
                    "seat": seat,
                    "seat_name": SEAT_PERSONAS[seat]["name"],
                    "ok": False,
                    "page": page,
                    "prompt_id": prompt_id,
                    "submitted_at": time.time(),
                    "seat_deadline": seat_deadline,
                    "before_length": before.get("text_length") or 0,
                    "before_text": before.get("text") or "",
                    "submission_confirmed": submission_confirmed,
                    "submit_result": {"fill": fill_result, "send": send_result, "preflight": preflight},
                }
                if trace:
                    trace("seat", "cdp_submit_complete", f"{seat} 提示词已发送", {
                        "seat": seat,
                        "fill": fill_result,
                        "send": send_result,
                    })
            except TimeoutError:
                submissions[seat] = _failed_result(seat, "seat_submit_timeout", f"Seat submission timed out after {seat_submit_timeout}s")
                if trace:
                    trace("seat", "cdp_submit_timeout", f"{seat} 提交超时 ({seat_submit_timeout}s)", {
                        "seat": seat,
                        "timeout_seconds": seat_submit_timeout,
                    })
            except Exception as exc:
                submissions[seat] = _failed_result(seat, "cdp_submit_failed", str(exc))
                if trace:
                    trace("seat", "cdp_submit_failed", f"{seat} 发送失败", {"seat": seat, "error": str(exc)})
            finally:
                seat_watchdog.cancel()
                if seat_timeout_flag.is_set() and submissions[seat].get("ok") is False and not submissions[seat].get("error"):
                    submissions[seat] = _failed_result(seat, "seat_submit_timeout",
                                                       f"Seat submission timed out after {seat_submit_timeout}s")
                    if trace:
                        trace("seat", "seat_timeout", f"{seat} 超时 ({seat_submit_timeout}s)", {
                            "seat": seat,
                            "timeout_seconds": seat_submit_timeout,
                        })

        poll_deadline = time.time() + timeout_seconds
        pending = {seat for seat, item in submissions.items() if item.get("page")}
        # P3.6: per-seat answer poll with individual deadline tracking
        if trace:
            trace("seat", "seat_answer_wait_started", "开始席位回答轮询", {
                "pending_seats": list(pending),
                "global_deadline": poll_deadline,
            })
        poll_round = 0
        while pending and time.time() < poll_deadline:
            poll_round += 1
            elapsed = max(0.0, timeout_seconds - (poll_deadline - time.time()))
            if progress:
                progress(f"Chrome CDP 回答轮询：剩余 {len(pending)} 席", 0.42 + 0.30 * min(1.0, elapsed / max(timeout_seconds, 1)))
            for seat in list(pending):
                item = submissions[seat]
                # P3.6: check per-seat deadline
                seat_dl = item.get("seat_deadline")
                if seat_dl and time.time() > seat_dl:
                    submissions[seat] = _failed_result(seat, "seat_timeout",
                                                       f"Seat {seat} exceeded per-seat deadline ({per_seat_deadline}s total)")
                    pending.remove(seat)
                    if trace:
                        trace("seat", "seat_timeout", f"{seat} 超过单席位截止时间", {
                            "seat": seat,
                            "seat_deadline": seat_dl,
                            "now": time.time(),
                            "poll_round": poll_round,
                        })
                    continue
                capture = _capture_page(item["page"], item["prompt_id"])
                assessment = _capture_acceptance(capture, item, question)
                text = assessment["text"]
                response_text = assessment["response_text"]
                marker_found = bool(capture.get("marker_found"))
                marker_in_input = bool(capture.get("marker_in_input"))
                matches_question = assessment["matches_question"]
                if trace:
                    trace("seat", "seat_answer_poll", f"{seat} 轮询 ({poll_round})", {
                        "seat": seat,
                        "round": poll_round,
                        "marker_found": marker_found,
                        "accepted": assessment["accepted"],
                        "response_chars": len(response_text),
                        "elapsed_s": round(time.time() - float(item["submitted_at"]), 1),
                    })
                if capture.get("ok") and assessment["accepted"]:
                    submissions[seat] = {
                        "seat": seat,
                        "seat_name": SEAT_PERSONAS[seat]["name"],
                        "ok": True,
                        "url": item["page"].url,
                        "profile_dir": "Chrome CDP fixed tab",
                        "elapsed_seconds": round(time.time() - float(item["submitted_at"]), 2),
                        "response": response_text,
                        "error": None,
                    }
                    pending.remove(seat)
                    if trace:
                        trace("seat", "cdp_response_captured", f"{seat} 已读取回答", {
                            "seat": seat,
                            "response_chars": len(response_text),
                            "captured_chars": len(text),
                            "elapsed_seconds": submissions[seat]["elapsed_seconds"],
                            "marker_found": marker_found,
                            "marker_in_input": marker_in_input,
                            "matches_question": matches_question,
                            "capture_mode": assessment["mode"],
                        })
            if pending:
                time.sleep(4)

        for seat in list(pending):
            item = submissions[seat]
            capture = _capture_page(item["page"], item["prompt_id"])
            assessment = _capture_acceptance(capture, item, question)
            text = assessment["text"]
            response_text = assessment["response_text"]
            marker_found = bool(capture.get("marker_found"))
            marker_in_input = bool(capture.get("marker_in_input"))
            matches_question = assessment["matches_question"]
            if capture.get("ok") and assessment["accepted"]:
                submissions[seat] = {
                    "seat": seat,
                    "seat_name": SEAT_PERSONAS[seat]["name"],
                    "ok": True,
                    "url": item["page"].url,
                    "profile_dir": "Chrome CDP fixed tab",
                    "elapsed_seconds": round(time.time() - float(item["submitted_at"]), 2),
                    "response": response_text,
                    "error": None,
                }
                if trace:
                    trace("seat", "cdp_partial_response_captured", f"{seat} 超时前读取到部分回答", {
                        "seat": seat,
                        "response_chars": len(response_text),
                        "captured_chars": len(text),
                        "marker_found": marker_found,
                        "marker_in_input": marker_in_input,
                        "matches_question": matches_question,
                        "capture_mode": assessment["mode"],
                    })
            else:
                code = "response_timeout"
                message = "No assistant response was captured from the Chrome CDP tab."
                if capture.get("ok") and len(response_text) >= 240 and not matches_question:
                    code = "response_not_relevant"
                    message = "Captured text did not match the current question, so the bridge rejected it instead of treating stale page content as an answer."
                submissions[seat] = _failed_result(seat, code, message)
                if trace:
                    trace("seat", "cdp_response_rejected" if code == "response_not_relevant" else "cdp_response_timeout", f"{seat} 未读到可用回答", {
                        "seat": seat,
                        "code": code,
                        "response_chars": len(response_text),
                        "captured_chars": len(text),
                        "marker_found": marker_found,
                        "marker_in_input": marker_in_input,
                        "matches_question": matches_question,
                    })

    if progress:
        progress("Chrome CDP 收集完成，进入评分", 0.74)
    return list(submissions.values())


def _clear_or_recover_page(
    page: Any,
    config: dict[str, Any],
    seat_config: dict[str, Any],
    seat: str,
    reason: str,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Clear blocking UI and reload a CDP tab once when it is visibly broken."""
    try:
        raw = page.evaluate(_build_clear_blocking_ui_js())
        state = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
    except Exception as exc:
        state = {"ok": False, "error": "cdp_preflight_failed", "message": str(exc)}
    if not _page_state_needs_reload(state):
        return state
    try:
        page.reload(wait_until="domcontentloaded", timeout=15000)
        delay = _humanized_sleep(config, seat_config, seat, "after_reload")
        wait_seconds = float(seat_config.get("page_recovery_wait_seconds") or config.get("page_recovery_wait_seconds") or 8)
        page.wait_for_timeout(max(800, min(20000, int(wait_seconds * 1000))))
        recovered = {"ok": True, "recovered": True, "reason": reason, "before": state, "delay_seconds": round(delay, 2)}
        if trace:
            trace("seat", "cdp_tab_recovery", f"{seat} CDP 页面已刷新恢复", {"seat": seat, **recovered})
        return recovered
    except Exception as exc:
        failed = {"ok": False, "recovered": False, "reason": reason, "before": state, "error": str(exc)}
        if trace:
            trace("seat", "cdp_tab_recovery_failed", f"{seat} CDP 页面刷新恢复失败", {"seat": seat, **failed})
        return failed


def _safe_page_title(page: Any) -> str:
    try:
        return str(page.title() or "")
    except Exception:
        return ""


def _open_missing_cdp_tab(
    browser: Any,
    seat_config: dict[str, Any],
    seat: str,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> Any | None:
    """Open a fresh fixed tab inside the dedicated AI Judge Chrome if a seat tab disappears."""
    fresh_url = (
        str(seat_config.get("fresh_url") or "").strip()
        or str(seat_config.get("url") or "").strip()
        or str(seat_config.get("fallback_url") or "").strip()
    )
    if not fresh_url:
        return None
    try:
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        page.goto(fresh_url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2500)
        if trace:
            trace("seat", "cdp_missing_tab_reopened", f"{seat} 固定标签缺失，已重新打开", {
                "seat": seat,
                "fresh_url": fresh_url,
                "url": page.url,
            })
        return page
    except Exception as exc:
        if trace:
            trace("seat", "cdp_missing_tab_reopen_failed", f"{seat} 固定标签缺失且重开失败", {
                "seat": seat,
                "fresh_url": fresh_url,
                "error": str(exc),
            })
        return None


def _fill_prompt(page: Any, prompt: str) -> dict[str, Any]:
    selectors = [
        "textarea[data-testid='prompt-textarea']",
        "div[contenteditable='true'][role='textbox']",
        "div[role='textbox'][contenteditable='true']",
        "div[contenteditable='true']",
        "textarea",
        "[role='textbox']",
    ]
    last_error = ""
    for selector in selectors:
        locator = page.locator(selector)
        count = locator.count()
        for idx in range(count - 1, -1, -1):
            candidate = locator.nth(idx)
            try:
                if not candidate.is_visible(timeout=700):
                    continue
                candidate.click(timeout=2000)
                try:
                    page.keyboard.press("Meta+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.insert_text(prompt)
                    return {"ok": True, "method": "browser_input.insert_text", "selector": selector}
                except Exception:
                    candidate.fill(prompt, timeout=8000)
                    return {"ok": True, "method": "locator.fill", "selector": selector}
            except Exception as exc:
                last_error = str(exc)
    return page.evaluate(
        """prompt => {
          const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const input = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[role='textbox']")).filter(visible).pop();
          if (!input) return {ok:false, error:"input_not_found"};
          input.focus();
          if (input.matches("textarea,input")) {
            const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")?.set;
            if (setter) setter.call(input, prompt); else input.value = prompt;
          } else {
            const range = document.createRange();
            range.selectNodeContents(input);
            const sel = window.getSelection();
            sel.removeAllRanges(); sel.addRange(range);
            document.execCommand("insertText", false, prompt);
          }
          input.dispatchEvent(new InputEvent("input", {bubbles:true, inputType:"insertText", data:prompt}));
          input.dispatchEvent(new Event("change", {bubbles:true}));
          return {ok:true, method:"dom_execCommand", last_error: %r};
        }"""
        % last_error[:160],
        prompt,
    )


def _send_prompt(page: Any) -> dict[str, Any]:
    host = urlparse(page.url).hostname or ""
    if host.endswith("chat.deepseek.com"):
        result = _send_deepseek_prompt(page)
        if result.get("ok"):
            return result

    selectors = [
        "button[data-testid='send-button']",
        "button[aria-label*='Send']",
        "button[aria-label*='发送']",
        "button[aria-label*='提交']",
        "button[type='submit']",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        count = locator.count()
        for idx in range(count - 1, -1, -1):
            candidate = locator.nth(idx)
            try:
                if candidate.is_visible(timeout=500) and candidate.is_enabled(timeout=500):
                    label = candidate.get_attribute("aria-label") or candidate.inner_text(timeout=500)
                    candidate.click(timeout=3000)
                    return {"ok": True, "method": "button", "selector": selector, "label": label}
            except Exception:
                continue
    page.keyboard.press("Enter")
    return {"ok": True, "method": "keyboard.enter"}


def _send_deepseek_prompt(page: Any) -> dict[str, Any]:
    """Use browser-level input events for DeepSeek; DOM clicks can create empty chats."""
    try:
        textarea = page.locator("textarea").last
        textarea.click(timeout=2500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(900)
        state = page.evaluate(
            """() => {
              const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const bodyText = document.body?.innerText || "";
              const input = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[role='textbox']")).filter(visible).pop();
              return {
                input_value: input ? (input.value || input.innerText || input.textContent || "") : "",
                body_tail: bodyText.slice(-900),
                busy: /停止回答|stop generating|停止生成/i.test(bodyText)
              };
            }"""
        )
        if state.get("busy") or not str(state.get("input_value") or "").strip():
            return {"ok": True, "method": "deepseek.keyboard.enter", "state": state}
    except Exception:
        pass

    try:
        button = page.locator("textarea").last.evaluate_handle(
            """input => {
              const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const rect = input.getBoundingClientRect();
              const candidates = Array.from(document.querySelectorAll("[role='button'],button"))
                .filter(visible)
                .map(el => ({el, r: el.getBoundingClientRect(), cls: String(el.className || ""), aria: el.getAttribute("aria-disabled")}))
                .filter(x => x.r.top >= rect.top - 260 && x.r.bottom <= rect.bottom + 260 && x.r.left >= rect.left - 320 && x.r.right <= rect.right + 320)
                .filter(x => x.aria !== "true" && !/disabled/.test(x.cls) && !/toggle-button/.test(x.cls));
              const sendish = candidates.filter(x => /_52c986b|ds-icon-button--l/.test(x.cls));
              return (sendish[sendish.length - 1] || candidates[candidates.length - 1] || {}).el || null;
            }"""
        )
        element = button.as_element()
        if element:
            element.click(timeout=3000)
            page.wait_for_timeout(900)
            return {"ok": True, "method": "deepseek.button.coordinate"}
    except Exception as exc:
        return {"ok": False, "error": "deepseek_submit_failed", "message": str(exc)}
    return {"ok": False, "error": "deepseek_send_button_not_found"}


def _capture_page(page: Any, marker: str) -> dict[str, Any]:
    try:
        raw = page.evaluate(_build_capture_js(marker))
        if isinstance(raw, str) and raw.strip():
            return json.loads(raw)
    except Exception as exc:
        return {"ok": False, "error": "cdp_capture_failed", "message": str(exc), "text": "", "text_length": 0}
    return {"ok": False, "error": "empty_result", "text": "", "text_length": 0}


def _prepare_submission_ui(page: Any, prompt_id: str) -> dict[str, Any]:
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


def _match_tab(seat_config: dict[str, Any], tabs: list[CDPTab]) -> CDPTab | None:
    urls = _url_candidates(seat_config)
    domains = _match_domains(seat_config, urls)
    labels = _match_labels(seat_config)
    for tab in tabs:
        tab_url = str(tab.url or "")
        if any(url and tab_url.rstrip("/") == url.rstrip("/") for url in urls):
            return tab
    for tab in tabs:
        tab_url = str(tab.url or "").lower()
        if any(domain and domain in tab_url for domain in domains):
            return tab
    if _label_fallback_enabled(seat_config):
        for tab in tabs:
            haystack = f"{tab.title} {tab.url}".lower()
            if any(label and label in haystack for label in labels):
                return tab
    return None


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


def _endpoint(config: dict[str, Any] | None = None) -> str:
    return str((config or {}).get("chrome_cdp_endpoint") or DEFAULT_CDP_ENDPOINT).rstrip("/")


def _connect_endpoint(config: dict[str, Any] | None = None) -> str:
    endpoint = _endpoint(config)
    if endpoint.startswith("ws://") or endpoint.startswith("wss://"):
        return endpoint
    try:
        version = _cdp_get_json(f"{endpoint}/json/version", timeout=2)
        websocket_url = str(version.get("webSocketDebuggerUrl") or "").strip()
        if websocket_url:
            return websocket_url
    except Exception:
        pass
    return endpoint


def _cdp_get_json(url: str, timeout: float) -> Any:
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()
