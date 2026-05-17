#!/usr/bin/env python3
"""Visible Chrome fixed-tab bridge for AI Judge.

This bridge targets the user's already-open Chrome model tabs. It uses Chrome's
Apple Events JavaScript hook to operate the DOM inside matching tabs, so it does
not use the system clipboard, mouse, or keyboard. Chrome must have
"Allow JavaScript from Apple Events" enabled under View > Developer.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from core.seat_personas import SEAT_PERSONAS, render_jury_prompt


class ChromeFixedTabError(RuntimeError):
    """Raised when Chrome fixed-tab automation cannot run."""


MIN_MARKER_ANSWER_CHARS = 8
MIN_FALLBACK_ANSWER_CHARS = 180
SLOW_SEAT_FALLBACK_ANSWER_CHARS = 800


@dataclass
class ChromeTab:
    window_index: int
    tab_index: int
    title: str
    url: str


def chrome_apple_events_status() -> dict[str, Any]:
    """Return whether Chrome can execute JavaScript via Apple Events."""
    try:
        result = _osascript(
            [
                'tell application "Google Chrome"',
                "set windowCount to count of windows",
                'if windowCount is 0 then return "NO_WINDOWS"',
                'tell active tab of window 1',
                'execute javascript "JSON.stringify({title: document.title, url: location.href})"',
                "end tell",
                "end tell",
            ],
            timeout=8,
        )
    except Exception as exc:
        message = str(exc)
        return {
            "available": False,
            "reason": "apple_events_js_disabled" if "AppleScript" in message or "JavaScript" in message else "chrome_unavailable",
            "message": message,
        }
    try:
        sample = json.loads(result)
    except Exception:
        sample = {"raw": result}
    return {"available": True, "reason": "ready", "sample": sample}


def list_chrome_tabs() -> list[ChromeTab]:
    """List open Chrome tabs with window/tab indexes."""
    result = _osascript(
        [
            'tell application "Google Chrome"',
            'set outText to ""',
            "set delim to ASCII character 9",
            'repeat with wi from 1 to (count of windows)',
            'set winObj to window wi',
            'repeat with ti from 1 to (count of tabs of winObj)',
            'set tabObj to tab ti of winObj',
            'set tabTitle to title of tabObj',
            'set tabUrl to URL of tabObj',
            'set outText to outText & wi & delim & ti & delim & tabTitle & delim & tabUrl & linefeed',
            "end repeat",
            "end repeat",
            "return outText",
            "end tell",
        ],
        timeout=8,
    )
    tabs: list[ChromeTab] = []
    for line in result.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        try:
            tabs.append(ChromeTab(int(parts[0]), int(parts[1]), parts[2], parts[3]))
        except ValueError:
            continue
    return tabs


def run_chrome_fixed_tabs(
    question: str,
    seats: list[str],
    config: dict[str, Any],
    mode: str = "flash",
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    """Ask fixed Chrome tabs and return raw model responses."""
    status = chrome_apple_events_status()
    if trace:
        trace("chrome", "apple_events_probe", "检测 Chrome Apple Events JavaScript 通道", status)
    if not status.get("available"):
        return [
            _failed_result(
                seat,
                str(status.get("reason") or "apple_events_unavailable"),
                str(status.get("message") or "Chrome Apple Events JavaScript is not available."),
            )
            for seat in seats
        ]

    all_tabs = list_chrome_tabs()
    if trace:
        trace(
            "chrome",
            "tabs_listed",
            "读取当前 Chrome 固定标签页",
            {"count": len(all_tabs), "tabs": [{"title": tab.title, "url": tab.url} for tab in all_tabs]},
        )

    requested = [seat for seat in seats if seat in SEAT_PERSONAS]
    submissions: dict[str, dict[str, Any]] = {}
    total = max(1, len(requested))
    for index, seat in enumerate(requested, 1):
        seat_config = _seat_config(config, seat)
        seat_timeout_seconds = _seat_timeout_seconds(config, seat_config)
        final_nudge_timeout_seconds = _final_nudge_timeout_seconds(config, seat_config)
        post_timeout_grace_seconds = _post_timeout_grace_seconds(config, seat_config)
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
        tab = _match_tab(seat_config, all_tabs)
        if tab is None and config.get("auto_open_missing_tabs"):
            open_url = str(seat_config.get("fresh_url") or seat_config.get("url") or seat_config.get("fallback_url") or "").strip()
            opened = _safe_open_tab(open_url) if open_url else {"ok": False, "error": "missing_url"}
            if opened.get("ok"):
                time.sleep(float(config.get("fresh_load_seconds") or 3.0))
                all_tabs = list_chrome_tabs()
                tab = _match_tab(seat_config, all_tabs)
            if trace:
                trace(
                    "seat",
                    "chrome_missing_tab_opened" if tab else "chrome_missing_tab_open_failed",
                    f"{seat} 缺少固定标签，已尝试自动打开",
                    {"seat": seat, "url": open_url, "opened": opened, "matched": bool(tab)},
                )
        if tab is None:
            submissions[seat] = _failed_result(seat, "fixed_tab_not_found", "No open Chrome tab matched this seat URL/title.")
            if trace:
                trace("seat", "fixed_tab_not_found", f"{seat} 未找到固定 Chrome 标签", {"seat": seat, "url": seat_config.get("url")})
            continue
        prompt = _seat_prompt(seat, question, mode)
        prompt_id = f"AIJUDGE-{seat}-{time.time_ns()}"
        prompt_with_marker = (
            f"{prompt}\n\n"
            "重要：不要只进行思考，必须在最终回答区域输出正文。请将你的最终答案完整包裹在以下两行标记之间，"
            "标记必须原样输出，标记外不要输出正文。不要输出“你的最终答案”这几个占位字，请替换成你的实际回答：\n"
            f"[AIJUDGE_ANSWER_START:{prompt_id}]\n"
            "你的最终答案\n"
            f"[AIJUDGE_ANSWER_END:{prompt_id}]\n\n"
            f"[trace_id: {prompt_id}]"
        )
        if progress:
            progress(f"Chrome 固定标签提交：{seat} ({index}/{total})", 0.14 + 0.20 * index / total)
        if trace:
            trace(
                "seat",
                "chrome_submit_start",
                f"{seat} 固定标签开始写入提示词",
                {"seat": seat, "title": tab.title, "url": tab.url, "prompt_chars": len(prompt_with_marker)},
            )
        if config.get("show_fixed_tabs", True):
            _safe_activate_tab(tab)
        preflight = _safe_execute_json(tab, _build_clear_blocking_ui_js(), timeout=5)
        if preflight.get("dismissed"):
            time.sleep(0.8)
            if trace:
                trace("seat", "chrome_blocking_ui_dismissed", f"{seat} 页面阻塞态已清理", {"seat": seat, "blocking": preflight})
        fresh_url = str(seat_config.get("fresh_url") or "").strip()
        if fresh_url and config.get("fresh_conversation_per_run", False):
            fresh = _safe_execute_json(tab, _build_fresh_navigation_js(fresh_url), timeout=8)
            if trace:
                trace("seat", "chrome_fresh_navigation", f"{seat} 跳转到干净会话入口", {"seat": seat, "fresh_url": fresh_url, "result": fresh})
            if fresh.get("navigated") or fresh.get("reloaded"):
                time.sleep(float(config.get("fresh_load_seconds") or 3.0))
        blocking = _safe_execute_json(tab, _build_clear_blocking_ui_js(), timeout=5)
        if blocking.get("dismissed"):
            time.sleep(0.8)
            if trace:
                trace("seat", "chrome_blocking_ui_dismissed", f"{seat} 页面阻塞态已清理", {"seat": seat, "blocking": blocking})
        prepared = _safe_execute_json(tab, _build_prepare_submission_ui_js(prompt_id), timeout=5)
        if prepared.get("clicked"):
            time.sleep(0.8)
            if trace:
                trace("seat", "chrome_submission_ui_prepared", f"{seat} 提交前模式已准备", {"seat": seat, "prepared": prepared})
        if prepared.get("needs_followup"):
            followup = _safe_execute_json(tab, _build_prepare_submission_ui_js(prompt_id), timeout=5)
            prepared["followup"] = followup
            if followup.get("clicked"):
                time.sleep(0.8)
            if trace:
                trace("seat", "chrome_submission_ui_prepare_followup", f"{seat} 提交前模式二次确认", {"seat": seat, "prepared": prepared})
        if seat == "deepseek":
            if not _deepseek_prepare_verified(prepared):
                submissions[seat] = _failed_result(
                    seat,
                    "deepseek_expert_mode_not_verified",
                    "DeepSeek expert mode, 深度思考, and 智能搜索 were not all verified before submission; the bridge refused to collect a fast-mode answer.",
                )
                if trace:
                    trace(
                        "seat",
                        "deepseek_expert_mode_blocked",
                        f"{seat} 未确认专家模式，拒绝提交",
                        {"seat": seat, "prepared": prepared},
                    )
                continue
        composer_wait = min(45.0, max(8.0, seat_timeout_seconds / 4))
        readiness = _wait_for_composer(tab, timeout=composer_wait)
        if readiness.get("page_blocked"):
            submissions[seat] = _failed_result(
                seat,
                str(readiness.get("reason") or "page_blocked"),
                str(readiness.get("message") or "The model page is blocked before submission."),
            )
            if trace:
                trace("seat", "chrome_composer_blocked", f"{seat} 页面阻断，跳过提交", {"seat": seat, "readiness": readiness})
            continue
        if not readiness.get("input_found"):
            submissions[seat] = _failed_result(
                seat,
                str(readiness.get("reason") or "composer_not_ready"),
                str(readiness.get("message") or "The fixed Chrome tab did not expose a usable composer before timeout."),
            )
            if trace:
                trace("seat", "chrome_composer_not_ready", f"{seat} 页面未就绪", {"seat": seat, "readiness": readiness})
            continue
        if readiness.get("page_busy"):
            submissions[seat] = _failed_result(
                seat,
                "composer_busy",
                "The fixed Chrome tab is still generating or showing a stop button, so the bridge did not submit a new prompt into that busy conversation.",
            )
            if trace:
                trace("seat", "chrome_composer_busy", f"{seat} 页面仍在生成，跳过提交", {"seat": seat, "readiness": readiness})
            continue
        before = _safe_execute_json(tab, _build_capture_js(prompt_id), timeout=12)
        written = _safe_execute_json(tab, _build_write_prompt_js(prompt_with_marker, prompt_id), timeout=15)
        time.sleep(0.8)
        if not written.get("ok"):
            presence = _safe_execute_json(tab, _build_prompt_presence_js(prompt_id), timeout=8)
            if presence.get("prompt_written"):
                written["ok"] = True
                written["prompt_written"] = True
                written["presence"] = presence
        clicked = _safe_execute_json(tab, _build_click_send_js(prompt_id), timeout=10) if written.get("ok") else {}
        submitted = dict(clicked)
        if written.get("ok") and not submitted.get("ok"):
            submitted.setdefault("prompt_written", True)
            submitted.setdefault("error", clicked.get("error") or "send_button_not_found")
            submitted.setdefault("message", clicked.get("message") or "Prompt was written, but no unambiguous send button was available.")
        submitted["write"] = written
        if submitted.get("ok"):
            time.sleep(1.0)
            verification = _safe_execute_json(tab, _build_submission_check_js(prompt_id), timeout=8)
            submitted["verification"] = verification
        else:
            verification = {}
        if submitted.get("ok") or submitted.get("prompt_written"):
            submission_confirmed = bool((submitted.get("verification") or {}).get("submitted"))
            if not submission_confirmed:
                retry = _safe_execute_json(tab, _build_retry_submit_js(prompt_id), timeout=10)
                submitted["retry"] = retry
                if retry.get("ok"):
                    time.sleep(1.0)
                    verification = _safe_execute_json(tab, _build_submission_check_js(prompt_id), timeout=8)
                    submitted["verification"] = verification
                    submission_confirmed = bool(verification.get("submitted"))
                    if submission_confirmed:
                        submitted["ok"] = True
                elif retry.get("error") in {"provider_quota_limited", "page_error"}:
                    submissions[seat] = _failed_result(
                        seat,
                        str(retry.get("error")),
                        str(retry.get("message") or "The model page is blocked."),
                    )
                    if trace:
                        trace("seat", "chrome_submit_blocked", f"{seat} 页面阻断，无法提交", {"seat": seat, "submit": submitted})
                    continue
            if not submission_confirmed:
                code = str(submitted.get("error") or (submitted.get("verification") or {}).get("reason") or "submit_unconfirmed")
                message = str(
                    submitted.get("message")
                    or (submitted.get("verification") or {}).get("message")
                    or "Prompt was written, but the bridge could not confirm that the model page accepted it as a submitted user turn."
                )
                submissions[seat] = _failed_result(seat, code, message)
                if trace:
                    trace("seat", "chrome_submit_unconfirmed", f"{seat} 未确认提交，跳过回答轮询", {"seat": seat, "submit": submitted})
                continue
            submissions[seat] = {
                "seat": seat,
                "seat_name": SEAT_PERSONAS[seat]["name"],
                "ok": False,
                "tab": tab,
                "prompt_id": prompt_id,
                "submitted_at": time.time(),
                "timeout_seconds": seat_timeout_seconds,
                "final_nudge_timeout_seconds": final_nudge_timeout_seconds,
                "post_timeout_grace_seconds": post_timeout_grace_seconds,
                "deadline": time.time() + seat_timeout_seconds,
                "before_length": before.get("text_length") or 0,
                "before_text": before.get("text") or "",
                "submission_confirmed": submission_confirmed,
                "submit_error": None if submitted.get("ok") else submitted.get("error"),
                "submit_result": submitted,
            }
            if trace:
                action = "chrome_submit_complete" if submissions[seat]["submission_confirmed"] else "chrome_submit_unconfirmed"
                detail = f"{seat} 提示词已发送" if submissions[seat]["submission_confirmed"] else f"{seat} 已写入提示词，等待回答确认"
                trace("seat", action, detail, {"seat": seat, "submit": submitted})
        else:
            verification = submitted.get("verification") or {}
            submissions[seat] = _failed_result(
                seat,
                str(submitted.get("error") or verification.get("reason") or "submit_failed"),
                str(submitted.get("message") or verification.get("message") or "Could not submit prompt in fixed Chrome tab."),
            )
            if trace:
                trace("seat", "chrome_submit_failed", f"{seat} 发送失败", {"seat": seat, "submit": submitted})

    pending = {seat for seat, item in submissions.items() if item.get("tab")}
    while pending:
        now = time.time()
        active_pending = {
            seat
            for seat in pending
            if now < float(submissions[seat].get("deadline") or 0)
        }
        if not active_pending:
            break
        longest_remaining = max(
            max(0.0, float(submissions[seat].get("deadline") or now) - now)
            for seat in active_pending
        )
        longest_timeout = max(
            max(1.0, float(submissions[seat].get("timeout_seconds") or 1.0))
            for seat in active_pending
        )
        elapsed = max(0.0, longest_timeout - longest_remaining)
        if progress:
            active_labels = "、".join(_seat_label(seat) for seat in sorted(active_pending))
            progress(
                f"Chrome 固定标签回答轮询：等待 {active_labels}，剩余 {len(active_pending)} 席，最长等待 {int(longest_remaining)}s",
                0.40 + 0.32 * min(1.0, elapsed / longest_timeout),
            )
        for seat in list(active_pending):
            item = submissions[seat]
            blocking = _safe_execute_json(item["tab"], _build_clear_blocking_ui_js(), timeout=5)
            if blocking.get("dismissed"):
                time.sleep(0.8)
                if trace:
                    trace("seat", "chrome_blocking_ui_dismissed", f"{seat} 页面阻塞态已清理", {"seat": seat, "blocking": blocking})
            capture = _safe_execute_json(item["tab"], _build_capture_js(item["prompt_id"]), timeout=12)
            if capture.get("blocking_ui_active"):
                if trace:
                    trace("seat", "chrome_capture_blocked_by_ui", f"{seat} 捕获前仍有页面阻塞态", {"seat": seat, "capture": capture})
                continue
            text = str(capture.get("text") or "").strip()
            response_text = _response_text_from_capture(capture, item)
            marker_found = bool(capture.get("marker_found"))
            marker_in_input = bool(capture.get("marker_in_input"))
            known_error = capture.get("known_error") or {}
            if known_error.get("code"):
                submissions[seat] = _failed_result(seat, str(known_error.get("code")), str(known_error.get("message") or "The model page returned an error."))
                pending.remove(seat)
                if trace:
                    trace(
                        "seat",
                        "chrome_response_page_error",
                        f"{seat} 页面返回错误",
                        {"seat": seat, "known_error": known_error, "marker_found": marker_found, "marker_in_input": marker_in_input},
                    )
                continue
            assessment = _capture_acceptance(capture, item, question)
            response_text = assessment["response_text"]
            text = assessment["text"]
            polluted = assessment["polluted"]
            if polluted:
                submissions[seat] = _failed_result(
                    seat,
                    "transcript_pollution",
                    "Captured text included older AI Judge trace markers or fixed-tab history, so the bridge rejected it instead of scoring stale transcript content.",
                )
                pending.remove(seat)
                if trace:
                    trace(
                        "seat",
                        "chrome_response_rejected",
                        f"{seat} 捕获内容包含历史 transcript，已拒绝",
                        {"seat": seat, "response_chars": len(response_text), "captured_chars": len(text)},
                )
                continue
            matches_question = assessment["matches_question"]
            if _should_send_final_answer_nudge(seat, item, capture, assessment):
                nudge = _send_final_answer_nudge(item["tab"], item["prompt_id"])
                item["final_answer_nudge"] = nudge
                item["final_answer_nudge_sent_at"] = time.time()
                item["deadline"] = min(
                    float(item.get("deadline") or time.time() + 90.0),
                    time.time() + float(item.get("final_nudge_timeout_seconds") or 90.0),
                )
                if trace:
                    trace("seat", "chrome_final_answer_nudge", f"{seat} 检测到空思考回复，已追问最终答案", {"seat": seat, "nudge": nudge})
                continue
            if capture.get("ok") and assessment["accepted"]:
                submissions[seat] = {
                    "seat": seat,
                    "seat_name": SEAT_PERSONAS[seat]["name"],
                    "ok": True,
                    "url": item["tab"].url,
                    "profile_dir": "Chrome fixed tab",
                    "elapsed_seconds": round(time.time() - float(item["submitted_at"]), 2),
                    "response": response_text,
                    "error": None,
                }
                pending.remove(seat)
                if trace:
                    trace(
                        "seat",
                        "chrome_response_captured",
                        f"{seat} 已读取回答",
                        {
                            "seat": seat,
                            "response_chars": len(response_text),
                            "captured_chars": len(text),
                            "elapsed_seconds": submissions[seat]["elapsed_seconds"],
                            "marker_found": marker_found,
                            "marker_in_input": marker_in_input,
                            "matches_question": matches_question,
                            "capture_mode": assessment["mode"],
                        },
                    )
        if pending:
            time.sleep(3)

    for seat in list(pending):
        item = submissions[seat]
        grace = float(item.get("post_timeout_grace_seconds") or 0.0)
        if grace > 0:
            time.sleep(grace)
        blocking = _safe_execute_json(item["tab"], _build_clear_blocking_ui_js(), timeout=5)
        if blocking.get("dismissed"):
            time.sleep(0.8)
            if trace:
                trace("seat", "chrome_blocking_ui_dismissed", f"{seat} 页面阻塞态已清理", {"seat": seat, "blocking": blocking})
        capture = _safe_execute_json(item["tab"], _build_capture_js(item["prompt_id"]), timeout=12)
        if capture.get("blocking_ui_active"):
            capture["text"] = ""
        text = str(capture.get("text") or "").strip()
        response_text = _response_text_from_capture(capture, item)
        marker_found = bool(capture.get("marker_found"))
        marker_in_input = bool(capture.get("marker_in_input"))
        known_error = capture.get("known_error") or {}
        if known_error.get("code"):
            submissions[seat] = _failed_result(seat, str(known_error.get("code")), str(known_error.get("message") or "The model page returned an error."))
            if trace:
                trace(
                    "seat",
                    "chrome_response_page_error",
                    f"{seat} 页面返回错误",
                    {"seat": seat, "known_error": known_error, "marker_found": marker_found, "marker_in_input": marker_in_input},
                )
            continue
        assessment = _capture_acceptance(capture, item, question)
        response_text = assessment["response_text"]
        text = assessment["text"]
        polluted = assessment["polluted"]
        matches_question = assessment["matches_question"]
        if capture.get("ok") and assessment["accepted"]:
            submissions[seat] = {
                "seat": seat,
                "seat_name": SEAT_PERSONAS[seat]["name"],
                "ok": True,
                "url": item["tab"].url,
                "profile_dir": "Chrome fixed tab",
                "elapsed_seconds": round(time.time() - float(item["submitted_at"]), 2),
                "response": response_text,
                "error": None,
            }
            if trace:
                trace(
                    "seat",
                    "chrome_partial_response_captured",
                    f"{seat} 超时前读取到部分回答",
                    {
                        "seat": seat,
                        "response_chars": len(response_text),
                        "captured_chars": len(text),
                        "marker_found": marker_found,
                        "marker_in_input": marker_in_input,
                        "matches_question": matches_question,
                        "capture_mode": assessment["mode"],
                    },
                )
        else:
            submit_error = str(item.get("submit_error") or "")
            message = "This seat was still slow after the collection window. It can be rechecked with the supplement action instead of being treated as a final model failure."
            code = "slow_response_pending"
            if polluted:
                code = "transcript_pollution"
                message = "Captured text included older AI Judge trace markers or fixed-tab history, so the bridge rejected it instead of scoring stale transcript content."
            elif capture.get("ok") and len(text) >= 240 and not matches_question:
                code = "response_not_relevant"
                message = "Captured text did not match the current question, so the bridge rejected it instead of treating stale page content as an answer."
            if submit_error:
                message = f"{message} Initial submit state: {submit_error}."
            failed = _failed_result(seat, code, message)
            if code == "slow_response_pending":
                failed.update({
                    "supplementable": True,
                    "url": item["tab"].url,
                    "profile_dir": "Chrome fixed tab",
                    "prompt_id": item.get("prompt_id"),
                    "submitted_at": item.get("submitted_at"),
                })
            submissions[seat] = failed
            if trace:
                trace(
                    "seat",
                    "chrome_response_rejected" if code == "response_not_relevant" else "chrome_response_timeout",
                    f"{seat} 未读到可用回答",
                    {
                        "seat": seat,
                        "code": code,
                        "response_chars": len(response_text),
                        "captured_chars": len(text),
                        "marker_found": marker_found,
                        "marker_in_input": marker_in_input,
                        "matches_question": matches_question,
                    },
                )
    if progress:
        progress("Chrome 固定标签收集完成，进入评分", 0.74)
    return list(submissions.values())


def recover_existing_fixed_tab_answers(
    question: str,
    seats: list[str],
    config: dict[str, Any],
    mode: str = "flash",
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    """Read late answers from already-open fixed Chrome tabs without sending a new prompt."""
    status = chrome_apple_events_status()
    if trace:
        trace("chrome", "existing_answer_probe", "检测 Chrome 旧页面答案读取通道", {
            **status,
            "method": "read_existing_tabs_only",
            "sends_prompt": False,
        })
    if not status.get("available"):
        return [
            _failed_result(
                seat,
                str(status.get("reason") or "apple_events_unavailable"),
                str(status.get("message") or "Chrome Apple Events JavaScript is not available."),
            )
            for seat in seats
        ]

    all_tabs = list_chrome_tabs()
    if trace:
        trace(
            "chrome",
            "existing_tabs_listed",
            "读取当前 Chrome 固定标签页用于旧答案回收",
            {"count": len(all_tabs), "tabs": [{"title": tab.title, "url": tab.url} for tab in all_tabs]},
        )

    requested = [seat.lower() for seat in seats if seat.lower() in SEAT_PERSONAS]
    total = max(1, len(requested))
    results: list[dict[str, Any]] = []
    for index, seat in enumerate(requested, 1):
        if progress:
            progress(f"读取旧页面答案：{_seat_label(seat)} ({index}/{total})", 0.12 + 0.70 * index / total)
        seat_config = _seat_config(config, seat)
        if not seat_config.get("enabled"):
            results.append(_failed_result(seat, "disabled", "Seat is disabled in web_seats.json."))
            continue
        tab = _match_tab(seat_config, all_tabs)
        if tab is None:
            failed = _failed_result(seat, "fixed_tab_not_found", "No open Chrome tab matched this seat URL/title.")
            failed["supplementable"] = True
            results.append(failed)
            if trace:
                trace("seat", "existing_answer_tab_not_found", f"{seat} 未找到固定 Chrome 标签", {"seat": seat})
            continue
        capture = _safe_execute_json(tab, _build_existing_answer_capture_js(seat), timeout=12)
        prompt_id = str(capture.get("prompt_id") or "")
        response_text = _clean_response_text(str(capture.get("text") or ""), prompt_id)
        prompt_echo = _capture_is_prompt_echo(response_text, prompt_id)
        polluted = _capture_is_polluted(response_text, prompt_id)
        matches_question = _response_matches_question(response_text, question)
        marker_found = bool(capture.get("marker_found"))
        fallback_found = bool(capture.get("fallback_found"))
        min_answer_chars = MIN_MARKER_ANSWER_CHARS if marker_found else MIN_FALLBACK_ANSWER_CHARS
        accepted = (
            bool(capture.get("ok"))
            and (marker_found or fallback_found)
            and len(response_text) >= min_answer_chars
            and not prompt_echo
            and not polluted
            and matches_question
        )
        if accepted:
            results.append({
                "seat": seat,
                "seat_name": SEAT_PERSONAS[seat]["name"],
                "ok": True,
                "url": tab.url,
                "profile_dir": "Chrome fixed tab existing page",
                "elapsed_seconds": 0,
                "response": response_text,
                "error": None,
                "recovered_from_existing_page": True,
                "capture_mode": str(capture.get("capture_mode") or ("existing_answer_marker" if marker_found else "existing_answer_fallback")),
                "prompt_id": prompt_id,
            })
            if trace:
                trace("seat", "existing_answer_captured", f"{seat} 已从旧页面读取答案", {
                    "seat": seat,
                    "response_chars": len(response_text),
                    "prompt_id": prompt_id,
                    "url": tab.url,
                    "capture_mode": capture.get("capture_mode"),
                    "marker_found": marker_found,
                    "fallback_found": fallback_found,
                })
            continue

        code = str(capture.get("reason") or capture.get("error") or "existing_answer_not_found")
        message = str(capture.get("message") or "The existing model page did not expose a usable AI Judge answer marker.")
        if prompt_echo:
            code = "existing_answer_prompt_echo"
            message = "The existing page still contains the prompt or placeholder instead of a final answer."
        elif polluted:
            code = "transcript_pollution"
            message = "The existing page contains older AI Judge transcript markers, so it was rejected."
        elif response_text and not matches_question:
            code = "response_not_relevant"
            message = "The existing page answer marker did not match the current question."
        failed = _failed_result(seat, code, message)
        failed.update({
            "supplementable": True,
            "url": tab.url,
            "profile_dir": "Chrome fixed tab existing page",
            "recovered_from_existing_page": False,
            "capture": {
                "marker_found": marker_found,
                "fallback_found": fallback_found,
                "capture_mode": capture.get("capture_mode"),
                "placeholder_found": bool(capture.get("placeholder_found")),
                "candidate_count": int(capture.get("candidate_count") or 0),
                "page_busy": bool(capture.get("page_busy")),
            },
        })
        results.append(failed)
        if trace:
            trace("seat", "existing_answer_rejected", f"{seat} 旧页面没有可用答案", {
                "seat": seat,
                "code": code,
                "message": message,
                "response_chars": len(response_text),
                "capture": failed["capture"],
            })
    if progress:
        progress("旧页面答案读取完成，进入合并评分", 0.84)
    return results


def _safe_execute_json(tab: ChromeTab, javascript: str, timeout: float = 10) -> dict[str, Any]:
    try:
        raw = _execute_tab_js(tab, javascript, timeout=timeout)
        if isinstance(raw, str) and raw.strip():
            return json.loads(raw)
    except Exception as exc:
        return {"ok": False, "error": "apple_events_execute_failed", "message": str(exc)}
    return {"ok": False, "error": "empty_result", "message": "Chrome returned an empty JavaScript result."}


def _execute_tab_js(tab: ChromeTab, javascript: str, timeout: float = 10) -> str:
    return _osascript(
        [
            'tell application "Google Chrome"',
            f"set targetTab to tab {tab.tab_index} of window {tab.window_index}",
            "tell targetTab",
            f"set resultText to execute javascript {json.dumps(javascript, ensure_ascii=False)}",
            "return resultText",
            "end tell",
            "end tell",
        ],
        timeout=timeout,
    )


def _safe_activate_tab(tab: ChromeTab) -> None:
    try:
        _osascript(
            [
                'tell application "Google Chrome"',
                "activate",
                f"set active tab index of window {tab.window_index} to {tab.tab_index}",
                "end tell",
            ],
            timeout=4,
        )
    except Exception:
        pass


def _safe_reload_tab(tab: ChromeTab) -> None:
    try:
        _osascript(
            [
                'tell application "Google Chrome"',
                f"reload tab {tab.tab_index} of window {tab.window_index}",
                "end tell",
            ],
            timeout=4,
        )
    except Exception:
        pass


def _safe_open_tab(url: str) -> dict[str, Any]:
    if not url:
        return {"ok": False, "error": "missing_url"}
    try:
        _osascript(
            [
                'tell application "Google Chrome"',
                "if (count of windows) is 0 then make new window",
                f'make new tab at end of tabs of window 1 with properties {{URL:{json.dumps(url, ensure_ascii=False)}}}',
                "end tell",
            ],
            timeout=8,
        )
        return {"ok": True, "url": url}
    except Exception as exc:
        return {"ok": False, "error": "open_tab_failed", "message": str(exc), "url": url}


def _send_final_answer_nudge(tab: ChromeTab, prompt_id: str) -> dict[str, Any]:
    nudge_prompt = (
        "上一轮只显示了思考或空回复。现在请不要继续思考，不要使用深入/思考模式，"
        "直接输出上一题的最终答案正文。必须完整包含同一组标记：\n"
        f"[AIJUDGE_ANSWER_START:{prompt_id}]\n"
        "最终答案正文\n"
        f"[AIJUDGE_ANSWER_END:{prompt_id}]"
    )
    written = _safe_execute_json(tab, _build_write_prompt_js(nudge_prompt, prompt_id), timeout=15)
    if not written.get("ok"):
        return {"ok": False, "stage": "write", "write": written}
    time.sleep(0.8)
    clicked = _safe_execute_json(tab, _build_click_send_js(prompt_id), timeout=10)
    if not clicked.get("ok") and clicked.get("error") == "send_button_not_found":
        retry = _safe_execute_json(tab, _build_retry_submit_js(prompt_id), timeout=10)
        clicked["retry"] = retry
        if retry.get("ok"):
            return {"ok": True, "stage": "retry_send", "write": written, "send": clicked}
    return {"ok": bool(clicked.get("ok")), "stage": "send", "write": written, "send": clicked}


def _wait_for_composer(tab: ChromeTab, timeout: float = 25.0) -> dict[str, Any]:
    """Wait until the target tab exposes a visible prompt composer."""
    deadline = time.time() + timeout
    reloaded = False
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = _safe_execute_json(tab, _build_composer_probe_js(), timeout=8)
        if last.get("page_blocked"):
            return last
        if last.get("input_found") and not last.get("page_busy"):
            return last
        title = str(last.get("title") or "")
        body = str(last.get("body_sample") or "")
        page_text = f"{title}\n{body}"
        if not reloaded and (
            len(body.strip()) < 20
            or any(token in page_text for token in ("网络错误", "操作出了问题", "Aw, Snap", "This site can’t be reached"))
        ):
            _safe_reload_tab(tab)
            reloaded = True
        time.sleep(2)
    last.setdefault("ok", True)
    last.setdefault("input_found", False)
    if last.get("page_busy"):
        last.setdefault("reason", "composer_busy")
        last.setdefault("message", "Timed out waiting for the model page to finish its previous generation.")
    else:
        last.setdefault("reason", "composer_not_ready")
        last.setdefault("message", "Timed out waiting for a visible prompt composer.")
    return last


def _osascript(lines: list[str], timeout: float = 10) -> str:
    helper = os.environ.get("AI_JUDGE_CHROME_HELPER", "").strip()
    if helper and Path(helper).exists():
        completed = subprocess.run(
            [helper, "--run-applescript-json"],
            input=json.dumps({"lines": lines}, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            raise ChromeFixedTabError((completed.stderr or completed.stdout or "").strip())
        return completed.stdout.strip()

    command: list[str] = ["osascript"]
    for line in lines:
        command.extend(["-e", line])
    completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    if completed.returncode != 0:
        raise ChromeFixedTabError((completed.stderr or completed.stdout or "").strip())
    return completed.stdout.strip()


def _match_tab(seat_config: dict[str, Any], tabs: list[ChromeTab]) -> ChromeTab | None:
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


def _domain(url: str) -> str:
    if "://" in url:
        url = url.split("://", 1)[1]
    return url.split("/", 1)[0].split("?", 1)[0].lower()


def _seat_config(config: dict[str, Any], seat: str) -> dict[str, Any]:
    return dict((config.get("seats") or {}).get(seat) or {})


def _seat_label(seat: str) -> str:
    return str(SEAT_PERSONAS.get(seat, {}).get("name") or seat)


def _seat_timeout_seconds(config: dict[str, Any], seat_config: dict[str, Any]) -> float:
    """Return a per-seat answer deadline, with a slower retry path when configured."""
    retry_run = bool(config.get("_retry_run"))
    keys = ("retry_timeout_seconds", "timeout_seconds") if retry_run else ("timeout_seconds",)
    for key in keys:
        value = seat_config.get(key)
        if value is not None:
            try:
                return max(30.0, min(900.0, float(value)))
            except Exception:
                pass
    for key in keys:
        value = config.get(key)
        if value is not None:
            try:
                return max(30.0, min(900.0, float(value)))
            except Exception:
                pass
    return 120.0


def _final_nudge_timeout_seconds(config: dict[str, Any], seat_config: dict[str, Any]) -> float:
    for key in ("final_nudge_timeout_seconds", "chatgpt_final_nudge_timeout_seconds"):
        value = seat_config.get(key)
        if value is None:
            value = config.get(key)
        if value is not None:
            try:
                return max(20.0, min(240.0, float(value)))
            except Exception:
                pass
    return 90.0


def _post_timeout_grace_seconds(config: dict[str, Any], seat_config: dict[str, Any]) -> float:
    for key in ("post_timeout_grace_seconds", "chatgpt_post_timeout_grace_seconds"):
        value = seat_config.get(key)
        if value is None:
            value = config.get(key)
        if value is not None:
            try:
                return max(0.0, min(90.0, float(value)))
            except Exception:
                pass
    return 0.0


def _failed_result(seat: str, code: str, message: str) -> dict[str, Any]:
    return {
        "seat": seat,
        "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "ok": False,
        "response": "",
        "error": {"code": code, "message": message},
    }


def _response_text_from_capture(capture: dict[str, Any], item: dict[str, Any]) -> str:
    """Return the current-run answer text, not the entire historical transcript."""
    text = str(capture.get("text") or "").strip()
    if not text:
        return ""
    if capture.get("marker_found"):
        return text

    before_text = str(item.get("before_text") or "").strip()
    if not before_text:
        return text

    if text.startswith(before_text):
        return text[len(before_text):].strip()
    if before_text in text:
        return text.rsplit(before_text, 1)[-1].strip()
    return text


def _capture_acceptance(capture: dict[str, Any], item: dict[str, Any], question: str) -> dict[str, Any]:
    """Decide whether a captured transcript is a current, usable answer."""
    text = str(capture.get("text") or "").strip()
    response_text = _clean_response_text(_response_text_from_capture(capture, item), str(item.get("prompt_id") or ""))
    before_text = str(item.get("before_text") or "")
    marker_found = bool(capture.get("marker_found"))
    marker_closed = bool(capture.get("marker_closed"))
    page_busy = bool(capture.get("page_busy"))
    prompt_id = str(item.get("prompt_id") or "")
    fallback_min_chars = MIN_FALLBACK_ANSWER_CHARS
    if str(item.get("seat") or "").lower() in {"chatgpt", "qwen"}:
        fallback_min_chars = max(fallback_min_chars, SLOW_SEAT_FALLBACK_ANSWER_CHARS)
    polluted = _capture_is_polluted(response_text, prompt_id)
    prompt_echo = _capture_is_prompt_echo(response_text, prompt_id)
    matches_question = _response_matches_question(response_text, question)
    has_closed_marker_answer = (
        marker_closed
        and not polluted
        and not prompt_echo
        and len(response_text) >= MIN_MARKER_ANSWER_CHARS
    )
    has_marker_answer = (
        marker_found
        and not marker_closed
        and not page_busy
        and not polluted
        and not prompt_echo
        and matches_question
        and len(response_text) >= fallback_min_chars
    )
    has_new_fallback_answer = (
        bool(item.get("submission_confirmed"))
        and not marker_found
        and not page_busy
        and not polluted
        and not prompt_echo
        and matches_question
        and response_text != before_text
        and len(response_text) >= fallback_min_chars
        and (not before_text or len(text) >= int(item.get("before_length") or 0) + 120 or response_text != text)
    )
    mode = ""
    if has_closed_marker_answer:
        mode = "closed_marker"
    elif has_marker_answer:
        mode = "marker_after_trace_id"
    elif has_new_fallback_answer:
        mode = "confirmed_fallback_growth"
    return {
        "accepted": has_closed_marker_answer or has_marker_answer or has_new_fallback_answer,
        "mode": mode,
        "text": text,
        "response_text": response_text,
        "polluted": polluted,
        "prompt_echo": prompt_echo,
        "matches_question": matches_question,
        "marker_found": marker_found,
        "marker_closed": marker_closed,
        "page_busy": page_busy,
        "fallback_min_chars": fallback_min_chars,
    }


def _should_send_final_answer_nudge(
    seat: str,
    item: dict[str, Any],
    capture: dict[str, Any],
    assessment: dict[str, Any],
) -> bool:
    """Recover web UIs that produce an empty thinking turn but no final answer."""
    if seat not in {"chatgpt", "qwen"} or item.get("final_answer_nudge"):
        return False
    if not item.get("submission_confirmed"):
        return False
    if assessment.get("accepted") or assessment.get("polluted") or assessment.get("prompt_echo"):
        return False
    if capture.get("page_busy"):
        return False
    elapsed = time.time() - float(item.get("submitted_at") or time.time())
    if elapsed < min(60.0, max(35.0, float(item.get("timeout_seconds") or 120) * 0.20)):
        return False
    response_text = str(assessment.get("response_text") or "").strip()
    if len(response_text) >= MIN_FALLBACK_ANSWER_CHARS:
        return False
    return bool(capture.get("thinking_only") or capture.get("assistant_empty"))


def _clean_response_text(text: str, prompt_id: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    for token in ("[AIJUDGE_ANSWER_END", "AIJUDGE_ANSWER_END"):
        index = cleaned.find(token)
        if index >= 0:
            cleaned = cleaned[:index].strip()
            break
    if prompt_id and cleaned.startswith(f"[AIJUDGE_ANSWER_START:{prompt_id}]"):
        cleaned = cleaned.split("]", 1)[-1].strip()
    return cleaned


def _capture_is_prompt_echo(text: str, prompt_id: str) -> bool:
    """Reject the original user prompt or page chrome being echoed as an answer."""
    if not text:
        return False
    if prompt_id and prompt_id in text and "你的最终答案" in text and "[QUESTION]" in text:
        return True
    if "Gemini 是一款 AI 工具" in text and ("使用麦克风" in text or "搜索对话内容" in text):
        return True
    if "内容由 AI 生成，请仔细甄别" in text and "[QUESTION]" in text and prompt_id and prompt_id in text:
        return True
    return False


def _capture_is_polluted(text: str, prompt_id: str) -> bool:
    """Reject long fixed-tab transcripts that include previous AI Judge turns."""
    if not text:
        return False
    if "已选择" in text and "组对话" in text:
        return True
    markers = set(re.findall(r"AIJUDGE-[a-z0-9_-]+-\d+", text, flags=re.I))
    old_markers = {marker for marker in markers if marker != prompt_id}
    if len(old_markers) >= 1 and len(text) > 1600:
        return True
    if text.count("[QUESTION]") > 1 and len(text) > 1600:
        return True
    return False


def _seat_prompt(seat: str, question: str, mode: str) -> str:
    base = render_jury_prompt(seat, question) or question
    is_resonance_followup = "[AIJUDGE_RESONANCE_FOLLOWUP]" in question
    seat_guard = ""
    if seat == "chatgpt":
        seat_guard = "\nChatGPT 专用要求：不要切换到深入/思考模式；直接输出最终正文，并完整保留 AIJUDGE 起止标记。"
    elif seat == "qwen":
        seat_guard = "\nQwen 专用要求：不要只停在思考完成提示；必须输出最终正文，并完整保留 AIJUDGE 起止标记。"
    if is_resonance_followup:
        return (
            f"{base}\n\n"
            "请作为 AI Judge 的同一个独立席位执行第二轮共振回答。输出要求：\n"
            "1. 逐条回答上一轮你提出的共振提问，先给结论再给理由。\n"
            "2. 明确带入用户角色，说明如果你是用户会如何取舍、推进和验收。\n"
            "3. 给出详细技术方案：模块拆分、数据流、接口/状态字段、执行步骤、测试与回滚。\n"
            "4. 保留事实、假设、建议三层隔离，不要覆盖第一轮原文。\n"
            f"5. 当前模式：{mode}。这是第二轮方案执行，不需要继续提出新问题。"
            f"{seat_guard}"
        )
    return (
        f"{base}\n\n"
        "请作为 AI Judge 的一个独立席位回答。输出要求：\n"
        "1. 先给出明确立场：支持 / 条件支持 / 反对 / 信息不足。\n"
        "2. 给出 3-5 条理由，每条尽量包含可验证依据或需要验证的假设。\n"
        "3. 给出最大风险和最小下一步。\n"
        "4. 单独输出「共振提问」：站在用户目标和你的席位专长上，提出 3-5 个能显著补强方案的问题。\n"
        f"5. 当前模式：{mode}。请保持结论紧凑，避免套话。"
        f"{seat_guard}"
    )


def _response_matches_question(text: str, question: str) -> bool:
    """Reject stale page text that does not share the current prompt's topic."""
    normalized_text = (text or "").lower()
    terms = _question_terms(question)
    if not terms:
        return bool(normalized_text.strip())
    hits = {term for term in terms if term in normalized_text}
    strong_terms = [term for term in terms if term in _STRONG_TOPIC_TERMS]
    if strong_terms and not any(term in hits for term in strong_terms):
        return False
    needed = 1 if len(terms) == 1 else 2
    return len(hits) >= min(needed, len(terms))


_STRONG_TOPIC_TERMS = {
    "世界杯",
    "world cup",
    "fifa",
    "小组",
    "淘汰赛",
    "比分",
    "冠军",
    "亚军",
    "四强",
    "金靴",
    "积分",
    "赛程",
}


_DOMAIN_HINTS = (
    "世界杯",
    "小组",
    "淘汰赛",
    "比分",
    "冠军",
    "亚军",
    "四强",
    "金靴",
    "积分",
    "赛程",
    "排名",
    "预测",
    "桥接",
    "桌面",
    "网页",
    "席位",
    "模型",
    "客户端",
    "报告",
    "评分",
)


_CJK_STOP_TERMS = {
    "一下",
    "这个",
    "那个",
    "可以",
    "应该",
    "需要",
    "给出",
    "请你",
    "请作为",
    "当前",
    "完整",
    "结果",
    "分析",
    "依据",
    "明确",
    "说明",
    "如果",
}


def _question_terms(question: str) -> list[str]:
    question_l = (question or "").lower()
    terms: list[str] = []

    def add(term: str) -> None:
        term = term.strip().lower()
        if len(term) >= 2 and term not in terms and term not in _CJK_STOP_TERMS:
            terms.append(term)

    for hint in _DOMAIN_HINTS:
        if hint.lower() in question_l:
            add(hint)
    if "世界杯" in question_l:
        add("world cup")
        add("fifa")

    for token in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", question_l):
        add(token)

    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", question_l):
        if len(chunk) <= 6:
            add(chunk)
            continue
        for size in (4, 3):
            for index in range(0, max(0, len(chunk) - size + 1)):
                fragment = chunk[index : index + size]
                if any(stop in fragment for stop in _CJK_STOP_TERMS):
                    continue
                add(fragment)
                if len(terms) >= 24:
                    return terms
    return terms[:24]


def _build_clear_blocking_ui_js() -> str:
    return """
(() => {
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const bodyText = document.body?.innerText || document.body?.textContent || "";
  let dismissed = false;
  if (/chat\\.deepseek\\.com/i.test(location.hostname) && /已选择\\s*\\d+\\s*组对话/.test(bodyText)) {
    const cancel = Array.from(document.querySelectorAll("button,[role='button'],div,span"))
      .find(el => visible(el) && /^(取消|Cancel)$/i.test((el.innerText || el.textContent || "").trim()));
    if (cancel) {
      try {
        cancel.click();
        dismissed = true;
      } catch (_) {}
    }
  }
  if (/操作出了问题|出了点问题|出了些问题|please try again|try again/i.test(bodyText)) {
    const retry = Array.from(document.querySelectorAll("button,[role='button'],div,span"))
      .find(el => visible(el) && /^(再试一次|重试|Retry|Try again)$/i.test((el.innerText || el.textContent || "").trim()));
    if (retry) {
      try {
        retry.click();
        dismissed = true;
      } catch (_) {}
    }
  }
  return JSON.stringify({ ok: true, dismissed, title: document.title, url: location.href });
})();
"""


def _build_prepare_submission_ui_js(prompt_id: str) -> str:
    marker_json = json.dumps(prompt_id, ensure_ascii=False)
    return f"""
(() => {{
  const marker = {marker_json};
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const textOf = el => (el.innerText || el.textContent || el.getAttribute("aria-label") || el.title || "").trim();
  const labelOf = el => [
    el.getAttribute("aria-label") || "",
    el.getAttribute("aria-checked") || "",
    el.getAttribute("aria-pressed") || "",
    el.title || "",
    el.innerText || "",
    el.textContent || "",
    String(el.className || "")
  ].join(" ").replace(/\\s+/g, " ").trim();
  const selected = el => {{
    const cls = String(el.className || "");
    return el.getAttribute("aria-pressed") === "true"
      || el.getAttribute("aria-selected") === "true"
      || el.getAttribute("aria-checked") === "true"
      || /(^|[-_\\s])(selected|active|checked|on)([-_\\s]|$)|ds-toggle-button--selected|_31a22b0/i.test(cls);
  }};
  const clickTarget = el => el?.closest?.("button,[role='button'],label") || el;
  const key = `ai-judge-prepared-${{marker}}`;
  if (sessionStorage.getItem(key)) return JSON.stringify({{ ok: true, clicked: false, already_prepared: true, title: document.title, url: location.href }});
  const clicked = [];
  let needsFollowup = false;
  const click = (name, el) => {{
    if (!el) return;
    try {{
      clickTarget(el).click();
      clicked.push(name);
    }} catch (_) {{}}
  }};
  const exact = text => Array.from(document.querySelectorAll("button,[role='button'],label,div,span"))
    .filter(el => visible(el) && textOf(el) === text);
  const byDeepseekLabel = text => Array.from(document.querySelectorAll("button,[role='button'],label,div,span"))
    .filter(el => visible(el) && el.getBoundingClientRect().width > 20 && (
      textOf(el) === text || labelOf(el) === text || labelOf(el).includes(text)
    ))
    .sort((a, b) => {{
      const aExact = textOf(a) === text ? 0 : 1;
      const bExact = textOf(b) === text ? 0 : 1;
      const aButton = clickTarget(a) === a ? 0 : 1;
      const bButton = clickTarget(b) === b ? 0 : 1;
      return aExact - bExact || aButton - bButton || a.getBoundingClientRect().width - b.getBoundingClientRect().width;
    }});
  const deepseekSelected = el => {{
    const target = clickTarget(el);
    const selectedAncestor = el?.closest?.("[aria-pressed='true'],[aria-selected='true'],[aria-checked='true'],[class*='selected'],[class*='active'],[class*='checked'],.ds-toggle-button--selected");
    return selected(el) || selected(target) || !!selectedAncestor;
  }};
  const deepseekExpertSelected = () => {{
    const bodyText = document.body?.innerText || document.body?.textContent || "";
    if (/使用专家模式开始对话/.test(bodyText) && !/使用快速模式开始对话/.test(bodyText)) return true;
    return byDeepseekLabel("专家模式").some(deepseekSelected);
  }};
  if (/chat\\.qwen\\.ai/i.test(location.hostname)) {{
    const qwenModeLabel = () => (document.querySelector(".qwen-thinking-selector")?.innerText
      || document.querySelector(".qwen-select-thinking")?.innerText
      || "").trim();
    const optionLabel = el => (el.getAttribute("title") || el.getAttribute("aria-label") || textOf(el)).trim();
    const options = Array.from(document.querySelectorAll(".ant-select-item-option,[role='option'],.ant-select-dropdown *"))
      .filter(el => visible(el) && el.getBoundingClientRect().width > 20);
    const reliableOption = options.find(el => {{
      const label = optionLabel(el);
      return label && !/^(思考|Thinking)$/i.test(label) && /^(非思考|不思考|普通|快速|自动|Auto|Fast|Instant|None|No Thinking)$/i.test(label);
    }}) || options.find(el => {{
      const label = optionLabel(el);
      return label && !/思考|Thinking/i.test(label);
    }});
    const selector = document.querySelector(".qwen-thinking-selector")
      || document.querySelector(".qwen-select-thinking")
      || Array.from(document.querySelectorAll("[role='combobox']")).find(visible);
    if (/^(思考|Thinking)$/i.test(qwenModeLabel())) {{
      if (reliableOption) {{
        click("qwen_reliable_mode", reliableOption);
      }} else if (selector) {{
        click("qwen_mode_menu_open", selector);
        needsFollowup = true;
      }}
    }} else {{
      clicked.push("qwen_reliable_mode_verified");
    }}
  }}
  if (/chatgpt\\.com/i.test(location.hostname)) {{
    const reliableOption = Array.from(document.querySelectorAll("[role='menuitemradio'],[role='menuitem'],button,[role='option'],div,span"))
      .find(el => visible(el) && /^(Instant|快速|Fast|默认|Default)$/i.test(textOf(el)));
    const thinkingModeButton = Array.from(document.querySelectorAll("button,[role='button'],[aria-haspopup='menu']"))
      .find(el => visible(el) && /^(深入|Thinking|Think|思考|Reason|推理)$/.test(textOf(el)));
    if (reliableOption) {{
      click("chatgpt_reliable_mode", reliableOption);
    }} else if (thinkingModeButton) {{
      click("chatgpt_mode_menu_open", thinkingModeButton);
      needsFollowup = true;
    }} else {{
      clicked.push("chatgpt_reliable_mode_verified");
    }}
  }}
  if (/chat\\.deepseek\\.com/i.test(location.hostname)) {{
    const deepseekNewChatKey = `${{key}}-deepseek-new-chat`;
    if (!sessionStorage.getItem(deepseekNewChatKey)) {{
      const newChat = exact("开启新对话")[0];
      if (newChat) {{
        click("deepseek_new_chat_once", newChat);
        sessionStorage.setItem(deepseekNewChatKey, "1");
        needsFollowup = true;
      }}
    }}
    const expertCandidates = byDeepseekLabel("专家模式");
    const expertVerifiedBeforeClick = deepseekExpertSelected();
    if (!expertVerifiedBeforeClick && expertCandidates[0]) {{
      click("deepseek_专家模式", expertCandidates.find(el => !deepseekSelected(el)) || expertCandidates[0]);
      needsFollowup = true;
    }}
    for (const toolName of ["深度思考", "智能搜索"]) {{
      const candidates = byDeepseekLabel(toolName);
      const alreadyOn = candidates.some(deepseekSelected);
      if (!alreadyOn && candidates[0]) {{
        click(`deepseek_${{toolName}}_on`, candidates[0]);
        needsFollowup = true;
      }}
    }}
    const expertVerified = deepseekExpertSelected();
    const toolsVerified = ["深度思考", "智能搜索"].every(toolName => byDeepseekLabel(toolName).some(deepseekSelected));
    if (!expertVerified || !toolsVerified) needsFollowup = true;
    clicked.push(`deepseek_expert_verified:${{expertVerified ? "yes" : "no"}}`);
    clicked.push(`deepseek_tools_verified:${{toolsVerified ? "yes" : "no"}}`);
  }}
  if (!needsFollowup) sessionStorage.setItem(key, "1");
  return JSON.stringify({{ ok: true, clicked: clicked.length > 0, clicked_names: clicked, needs_followup: needsFollowup, title: document.title, url: location.href }});
}})();
"""


def _final_prepared_state(prepared: dict[str, Any]) -> dict[str, Any]:
    followup = prepared.get("followup")
    return followup if isinstance(followup, dict) else prepared


def _deepseek_prepare_verified(prepared: dict[str, Any]) -> bool:
    final_prepared = _final_prepared_state(prepared or {})
    clicked_names = [str(name) for name in (final_prepared.get("clicked_names") or [])]
    return "deepseek_expert_verified:yes" in clicked_names and "deepseek_tools_verified:yes" in clicked_names


def _build_fresh_navigation_js(fresh_url: str) -> str:
    url_json = json.dumps(fresh_url, ensure_ascii=False)
    return f"""
(() => {{
  const target = {url_json};
  const previous = location.href;
  const normalizeForNavigation = value => {{
    try {{
      const url = new URL(value, location.href);
      url.hash = "";
      return url.href.replace(/\\/$/, "");
    }} catch (_) {{
      return String(value || "").replace(/#.*$/, "").replace(/\\/$/, "");
    }}
  }};
  const currentUrl = new URL(location.href);
  const targetUrl = new URL(target, location.href);
  const sameTarget = normalizeForNavigation(currentUrl.href) === normalizeForNavigation(targetUrl.href);
  const bodyText = document.body?.innerText || document.body?.textContent || "";
  const pageError = /操作出了问题|出了点问题|出了些问题|please try again|try again/i.test(bodyText);
  if (sameTarget && pageError) {{
    location.reload();
    return JSON.stringify({{ ok: true, navigated: false, reloaded: true, reason: "page_error", url: target, previous_url: previous }});
  }}
  if (!sameTarget && location.href !== target) {{
    location.href = targetUrl.href;
    return JSON.stringify({{ ok: true, navigated: true, url: targetUrl.href, previous_url: previous }});
  }}
  return JSON.stringify({{ ok: true, navigated: false, url: location.href }});
}})();
"""


def _build_write_prompt_js(prompt: str, prompt_id: str) -> str:
    prompt_json = json.dumps(prompt, ensure_ascii=False)
    marker_json = json.dumps(prompt_id, ensure_ascii=False)
    return f"""
(() => {{
  const prompt = {prompt_json};
  const marker = {marker_json};
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const usableInput = el => {{
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 20 && rect.height >= 8;
  }};
  const dismissBlockingUi = () => {{
    if (/chat\\.deepseek\\.com/i.test(location.hostname) && /已选择\\s*\\d+\\s*组对话/.test(document.body?.innerText || "")) {{
      const cancel = Array.from(document.querySelectorAll("button,[role='button'],div,span"))
        .find(el => visible(el) && (el.innerText || "").trim() === "取消");
      if (cancel) {{
        try {{ cancel.click(); }} catch (_) {{}}
      }}
    }}
  }};
  dismissBlockingUi();
  const inputSelectors = [
    ".chat-input-editor[contenteditable='true']",
    "textarea[data-testid='prompt-textarea']",
    "div[contenteditable='true'][role='textbox']",
    "div[role='textbox'][contenteditable='true']",
    ".ProseMirror[contenteditable='true']",
    "[class*='ProseMirror'][contenteditable='true']",
    "[class*='ql-editor'][contenteditable='true']",
    "[class*='cm-content'][contenteditable='true']",
    "div[contenteditable='true']",
    "textarea",
    "[role='textbox']"
  ];
  let input = null;
  let selectorUsed = "";
  for (const selector of inputSelectors) {{
    const candidates = Array.from(document.querySelectorAll(selector)).filter(usableInput);
    input = candidates[candidates.length - 1];
    if (input) {{ selectorUsed = selector; break; }}
  }}
  if (!input) return JSON.stringify({{ ok: false, error: "input_not_found", title: document.title, url: location.href }});
  input.focus();
  if (input.tagName === "TEXTAREA" || input.tagName === "INPUT") {{
    const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")?.set;
    input.dispatchEvent(new InputEvent("beforeinput", {{ bubbles: true, cancelable: true, inputType: "insertText", data: prompt }}));
    if (setter) setter.call(input, prompt);
    else input.value = prompt;
    input.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: "insertText", data: prompt }}));
    input.dispatchEvent(new Event("change", {{ bubbles: true }}));
    input.dispatchEvent(new KeyboardEvent("keyup", {{ key: "Process", code: "Process", bubbles: true }}));
  }} else {{
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(input);
    selection.removeAllRanges();
    selection.addRange(range);
    let inserted = false;
    input.dispatchEvent(new InputEvent("beforeinput", {{ bubbles: true, cancelable: true, inputType: "insertText", data: prompt }}));
    try {{
      inserted = document.execCommand("insertText", false, prompt);
    }} catch (_) {{
      inserted = false;
    }}
    if (!inserted || !(input.innerText || input.textContent || "").includes(marker)) {{
      input.textContent = prompt;
    }}
    input.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: "insertText", data: prompt }}));
    input.dispatchEvent(new Event("change", {{ bubbles: true }}));
    input.dispatchEvent(new KeyboardEvent("keyup", {{ key: "Process", code: "Process", bubbles: true }}));
  }}
  const value = input.value || input.innerText || input.textContent || "";
  const pageText = document.body?.innerText || document.body?.textContent || "";
  const promptWritten = value.includes(marker) || pageText.includes(marker);
  return JSON.stringify({{ ok: promptWritten, prompt_written: promptWritten, method: "write_then_send", input_selector: selectorUsed, title: document.title, url: location.href }});
}})();
"""


def _build_click_send_js(prompt_id: str) -> str:
    marker_json = json.dumps(prompt_id, ensure_ascii=False)
    return f"""
(() => {{
  const marker = {marker_json};
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const usableInput = el => {{
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 20 && rect.height >= 8;
  }};
  const dismissBlockingUi = () => {{
    if (/chat\\.deepseek\\.com/i.test(location.hostname) && /已选择\\s*\\d+\\s*组对话/.test(document.body?.innerText || "")) {{
      const cancel = Array.from(document.querySelectorAll("button,[role='button'],div,span"))
        .find(el => visible(el) && (el.innerText || "").trim() === "取消");
      if (cancel) {{
        try {{ cancel.click(); }} catch (_) {{}}
      }}
    }}
  }};
  dismissBlockingUi();
  const rawLabel = el => [
    el.getAttribute("aria-label") || "",
    el.getAttribute("name") || "",
    el.title || "",
    el.innerText || "",
    el.dataset?.testid || "",
    String(el.className || ""),
    (el.closest("[class]")?.className || "")
  ].join(" ");
  const buttonLabel = el => rawLabel(el).toLowerCase();
  const hasDisabledAncestor = el => {{
    for (let node = el; node && node !== document.body; node = node.parentElement) {{
      const cls = String(node.className || "").toLowerCase();
      const classDisabled = node.classList && (node.classList.contains("disabled") || node.classList.contains("is-disabled"));
      if (node.disabled || node.getAttribute("aria-disabled") === "true" || node.dataset?.disabled === "true" || classDisabled) return true;
    }}
    return false;
  }};
  const inputs = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[role='textbox']")).filter(usableInput);
  const activeInput = inputs.find(el => ((el.value || el.innerText || el.textContent || "").includes(marker))) || inputs[inputs.length - 1];
  if (!activeInput) return JSON.stringify({{ ok: false, error: "input_not_found", title: document.title, url: location.href }});
  const blockedLabel = /(voice|语音|microphone|mic|听写|dictation|工具|附件|upload|attach|file|文件|深度|思考|联网|model|模型|settings|设置|历史|new chat|新建|menu|菜单|主菜单|more|更多|view|switch|切换|复制|copy|thumb|赞|踩|regenerate|share|分享|sidebar|侧边栏|search|搜索|incognito|learn|write|code|life stuff|choice|stop|停止|pause|暂停|timeline|suggestion|建议|示例|起手式|带入|角色|思路|解决方案)/i;
  const nearActiveInput = el => {{
    if (!activeInput) return true;
    const inputRect = activeInput.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) return false;
    const vertical = rect.top >= inputRect.top - 120 && rect.bottom <= inputRect.bottom + 160;
    const horizontal = rect.left >= inputRect.left - 120 && rect.right <= inputRect.right + 180;
    return vertical && horizontal;
  }};
  const looksLikeSend = el => {{
    const label = buttonLabel(el);
    if (hasDisabledAncestor(el) || blockedLabel.test(label)) return false;
    if (/(send|submit|发送|提交|提问|send-button|send button|composer-submit|prompt-send|submit-btn|submit-button|input-send-icon|send-icon|icon-send|icon-send1|send__|arrow-up|up-arrow)/i.test(label)) return true;
    const text = (el.innerText || "").trim();
    const aria = (el.getAttribute("aria-label") || "").trim();
    if (/^(↑|➤|➜|>)$/.test(text) || /^(↑|➤|➜|>)$/.test(aria)) return true;
    const svgText = Array.from(el.querySelectorAll("svg,title")).map(svg => svg.getAttribute("aria-label") || svg.getAttribute("name") || svg.textContent || "").join(" ").toLowerCase();
    if (/(send|submit|发送|提交|arrow-up|up-arrow)/i.test(svgText)) return true;
    return false;
  }};
  const clickableSelector = [
    "button",
    "[role='button']",
    "[aria-label]",
    "[class*='send']",
    "[class*='Send']",
    "[class*='submit']",
    "[class*='Submit']",
    "[class*='input-send']",
    "[class*='send-icon']",
    "[class*='arrow']",
    "svg[name='Send']",
    "svg[class*='send']",
    "i[class*='send']",
    "span[class*='send']",
    "div[class*='send']"
  ].join(",");
  const clickTarget = el => {{
    if (!el) return el;
    if (el.matches?.("button,[role='button']")) return el;
    const childButton = el.querySelector?.("button:not([disabled]),[role='button']:not([aria-disabled='true'])");
    if (childButton) return childButton;
    return el.closest("button,[role='button'],[class*='send'],[class*='submit'],[class*='Submit'],[class*='Send']") || el;
  }};
  const fireClick = el => {{
    const rect = el.getBoundingClientRect();
    const opts = {{ bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }};
    for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {{
      const Ctor = type.startsWith("pointer") ? PointerEvent : MouseEvent;
      el.dispatchEvent(new Ctor(type, opts));
    }}
    try {{ el.click(); }} catch (_) {{}}
  }};
  const dedupe = items => Array.from(new Set(items.filter(Boolean)));
  const allCandidates = root => dedupe(Array.from(root.querySelectorAll(clickableSelector)).map(clickTarget)).filter(el => visible(el) && nearActiveInput(el));
  const pickButton = root => allCandidates(root).find(looksLikeSend) || null;
  let sendButton = null;
  let scope = activeInput;
  for (let depth = 0; scope && depth < 10 && !sendButton; depth += 1) {{
    sendButton = pickButton(scope);
    scope = scope.parentElement;
  }}
  const buttons = allCandidates(document);
  sendButton = sendButton || buttons.find(looksLikeSend);
  if (!sendButton && /chat\\.deepseek\\.com/i.test(location.hostname)) {{
    const scopedButtons = [];
    let node = activeInput;
    for (let depth = 0; node && depth < 8; depth += 1, node = node.parentElement) {{
      scopedButtons.push(...Array.from(node.querySelectorAll("[role='button'],button")).map(clickTarget).filter(visible));
    }}
    const dsButtons = dedupe(scopedButtons).filter(btn => {{
      const label = buttonLabel(btn);
      return /ds-icon-button--l|_52c986b/i.test(label) && !hasDisabledAncestor(btn) && !blockedLabel.test(label);
    }});
    sendButton = dsButtons[dsButtons.length - 1] || null;
  }}
  if (!sendButton && /aistudio\\.xiaomimimo\\.com/i.test(location.hostname)) {{
    const inputRect = activeInput.getBoundingClientRect();
    const mimoButtons = Array.from(document.querySelectorAll("button"))
      .filter(btn => visible(btn) && !hasDisabledAncestor(btn))
      .filter(btn => {{
        const rect = btn.getBoundingClientRect();
        return rect.left >= inputRect.right - 90
          && rect.top >= inputRect.bottom - 30
          && rect.top <= inputRect.bottom + 80
          && rect.width <= 60
          && rect.height <= 60;
      }});
    sendButton = mimoButtons[mimoButtons.length - 1] || null;
  }}
  if (!sendButton && /agent\\.minimaxi\\.com/i.test(location.hostname)) {{
    const inputRect = activeInput.getBoundingClientRect();
    const miniMaxButtons = dedupe(Array.from(document.querySelectorAll("button,[role='button'],svg,i,span,div")).map(clickTarget))
      .filter(el => visible(el) && !hasDisabledAncestor(el))
      .filter(el => {{
        const rect = el.getBoundingClientRect();
        if (!rect.width || !rect.height || rect.width > 84 || rect.height > 84) return false;
        const label = buttonLabel(el);
        const forceSend = /(send|发送|submit|arrow|icon-send|input-send|up-arrow)/i.test(label);
        if (blockedLabel.test(label) && !forceSend) return false;
        if (!forceSend && /(ppt|视频|图像|回答问题|提出共振|品牌|博客|素材|模板|示例|起手式|suggestion|prompt)/i.test(label)) return false;
        const closeToComposerRight = rect.left >= inputRect.right - 140 && rect.left <= inputRect.right + 220;
        return (forceSend || closeToComposerRight)
          && rect.top >= inputRect.top - 70
          && rect.bottom <= inputRect.bottom + 140;
      }});
    sendButton = miniMaxButtons[miniMaxButtons.length - 1] || null;
  }}
  const pageTextAfterWrite = document.body?.innerText || document.body?.textContent || "";
  const pageBusyAfterWrite = /停止回答|stop generating|stop response|停止生成/i.test(pageTextAfterWrite);
  const pageHasMarkerAfterWrite = pageTextAfterWrite.includes(marker);
  if (!sendButton && pageBusyAfterWrite && pageHasMarkerAfterWrite) {{
    return JSON.stringify({{
      ok: true,
      method: "already_generating",
      prompt_written: true,
      button_label: "page_busy_after_write",
      title: document.title,
      url: location.href,
      visible_buttons: buttons.map(btn => buttonLabel(btn).slice(0, 100)).filter(Boolean).slice(-16)
    }});
  }}
  if (sendButton) {{
    fireClick(sendButton);
    return JSON.stringify({{ ok: true, method: "button", button_label: buttonLabel(sendButton).slice(0, 160), title: document.title, url: location.href }});
  }}
  return JSON.stringify({{
    ok: false,
    error: "send_button_not_found",
    prompt_written: true,
    message: "Prompt was written, but no unambiguous enabled send button was available.",
    title: document.title,
    url: location.href,
    visible_buttons: buttons.map(btn => buttonLabel(btn).slice(0, 100)).filter(Boolean).slice(-16)
  }});
}})();
"""


def _build_submit_js(prompt: str, prompt_id: str) -> str:
    prompt_json = json.dumps(prompt, ensure_ascii=False)
    marker_json = json.dumps(prompt_id, ensure_ascii=False)
    return f"""
(() => {{
  const prompt = {prompt_json};
  const marker = {marker_json};
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const inputSelectors = [
    ".chat-input-editor[contenteditable='true']",
    "textarea[data-testid='prompt-textarea']",
    "div[contenteditable='true'][role='textbox']",
    "div[role='textbox'][contenteditable='true']",
    "div[contenteditable='true']",
    "textarea",
    "[role='textbox']"
  ];
  let input = null;
  for (const selector of inputSelectors) {{
    const candidates = Array.from(document.querySelectorAll(selector)).filter(visible);
    input = candidates[candidates.length - 1];
    if (input) break;
  }}
  if (!input) return JSON.stringify({{ ok: false, error: "input_not_found", title: document.title, url: location.href }});
  input.focus();
  if (input.tagName === "TEXTAREA" || input.tagName === "INPUT") {{
    const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")?.set;
    input.dispatchEvent(new InputEvent("beforeinput", {{ bubbles: true, cancelable: true, inputType: "insertText", data: prompt }}));
    if (setter) setter.call(input, prompt);
    else input.value = prompt;
    input.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: "insertText", data: prompt }}));
    input.dispatchEvent(new Event("change", {{ bubbles: true }}));
    input.dispatchEvent(new KeyboardEvent("keyup", {{ key: "Process", code: "Process", bubbles: true }}));
  }} else {{
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(input);
    selection.removeAllRanges();
    selection.addRange(range);
    let inserted = false;
    input.dispatchEvent(new InputEvent("beforeinput", {{ bubbles: true, cancelable: true, inputType: "insertText", data: prompt }}));
    try {{
      inserted = document.execCommand("insertText", false, prompt);
    }} catch (_) {{
      inserted = false;
    }}
    if (!inserted || !(input.innerText || input.textContent || "").includes(marker)) {{
      input.textContent = prompt;
    }}
    input.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: "insertText", data: prompt }}));
    input.dispatchEvent(new Event("change", {{ bubbles: true }}));
    }}
  const rawLabel = el => [
    el.getAttribute("aria-label") || "",
    el.getAttribute("name") || "",
    el.title || "",
    el.innerText || "",
    el.dataset?.testid || "",
    String(el.className || ""),
    (el.closest("[class]")?.className || "")
  ].join(" ");
  const buttonLabel = el => rawLabel(el).toLowerCase();
  const hasDisabledAncestor = el => {{
    for (let node = el; node && node !== document.body; node = node.parentElement) {{
      const cls = String(node.className || "").toLowerCase();
      const classDisabled = node.classList && (node.classList.contains("disabled") || node.classList.contains("is-disabled"));
      if (node.disabled || node.getAttribute("aria-disabled") === "true" || node.dataset?.disabled === "true" || classDisabled) return true;
    }}
    return false;
  }};
  const blockedLabel = /(voice|语音|microphone|mic|听写|dictation|工具|附件|upload|attach|file|文件|深度|思考|联网|model|模型|settings|设置|历史|new chat|新建|menu|菜单|主菜单|more|更多|view|switch|切换|复制|copy|thumb|赞|踩|regenerate|share|分享|sidebar|侧边栏|search|搜索|incognito|learn|write|code|life stuff|choice|stop|停止|pause|暂停)/i;
  const looksLikeSend = el => {{
    const label = buttonLabel(el);
    if (hasDisabledAncestor(el) || blockedLabel.test(label)) return false;
    if (/(send|submit|发送|提交|提问|send-button|send button|composer-submit|prompt-send|submit-btn|submit-button|send-icon|icon-send|send__|arrow-up|up-arrow)/i.test(label)) return true;
    const text = (el.innerText || "").trim();
    const aria = (el.getAttribute("aria-label") || "").trim();
    if (/^(↑|➤|➜|>)$/.test(text) || /^(↑|➤|➜|>)$/.test(aria)) return true;
    const svgText = Array.from(el.querySelectorAll("svg,title")).map(svg => svg.getAttribute("aria-label") || svg.getAttribute("name") || svg.textContent || "").join(" ").toLowerCase();
    if (/(send|submit|发送|提交)/i.test(svgText)) return true;
    const emptyComposerIcon = !(el.innerText || "").trim() && /(ds-icon-button|rounded-full|submit-btn|submit-button|send-button-container)/i.test(label);
    if (emptyComposerIcon) return true;
    return false;
  }};
  const clickableSelector = [
    "button",
    "[role='button']",
    "[aria-label]",
    "[class*='send']",
    "[class*='Send']",
    "[class*='submit']",
    "[class*='Submit']",
    "[class*='arrow']",
    "svg[name='Send']",
    "svg[class*='send']",
    "i[class*='send']",
    "span[class*='send']",
    "div[class*='send']"
  ].join(",");
  const clickTarget = el => el.closest("button,[role='button'],[class*='send'],[class*='submit'],[class*='Submit'],[class*='Send']") || el;
  const dedupe = items => Array.from(new Set(items.filter(Boolean)));
  const allCandidates = root => dedupe(Array.from(root.querySelectorAll(clickableSelector)).map(clickTarget)).filter(visible);
  const pickButton = root => {{
    const scoped = allCandidates(root);
    return scoped.find(looksLikeSend) || null;
  }};
  let sendButton = null;
  let scope = input;
  for (let depth = 0; scope && depth < 8 && !sendButton; depth += 1) {{
    sendButton = pickButton(scope);
    scope = scope.parentElement;
  }}
  const buttons = allCandidates(document);
  sendButton = sendButton || buttons.find(looksLikeSend);
  if (sendButton) {{
    sendButton.click();
    return JSON.stringify({{ ok: true, method: "button", button_label: buttonLabel(sendButton).slice(0, 160), title: document.title, url: location.href }});
  }}
  return JSON.stringify({{
    ok: false,
    error: "send_button_not_found",
    prompt_written: true,
    message: "Prompt was written, but no unambiguous send button was available.",
    title: document.title,
    url: location.href,
    visible_buttons: buttons.map(btn => buttonLabel(btn).slice(0, 100)).filter(Boolean).slice(-16)
  }});
}})();
"""


def _build_composer_probe_js() -> str:
    return """
(() => {
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const usableInput = el => {
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 20 && rect.height >= 8;
  };
  const bodyText = (document.body && document.body.innerText) || "";
  const quotaBlocked = /消息限制已达|使用上限|rate limit|usage limit|message limit|too many requests|升级到\\s*SuperGrok/i.test(bodyText);
  const pageError = /操作出了问题|出了点问题|出了些问题|please try again|try again/i.test(bodyText);
  const loginRequired = /doubao\\.com/i.test(location.hostname) && /登录/.test(bodyText) && /下载电脑版/.test(bodyText);
  const inputSelectors = [
    ".chat-input-editor[contenteditable='true']",
    "textarea[data-testid='prompt-textarea']",
    "div[contenteditable='true'][role='textbox']",
    "div[role='textbox'][contenteditable='true']",
    "div[contenteditable='true']",
    "textarea",
    "[role='textbox']"
  ];
  let input = null;
  let selectorUsed = "";
  for (const selector of inputSelectors) {
    const candidates = Array.from(document.querySelectorAll(selector)).filter(usableInput);
    input = candidates[candidates.length - 1];
    if (input) { selectorUsed = selector; break; }
  }
  return JSON.stringify({
    ok: true,
    title: document.title,
    url: location.href,
    input_found: !!input,
    input_selector: selectorUsed,
    input_tag: input ? input.tagName : null,
    input_role: input ? input.getAttribute("role") : null,
    page_busy: /停止回答|stop generating|stop response|停止生成/i.test(bodyText),
    page_blocked: quotaBlocked || pageError || loginRequired,
    reason: quotaBlocked ? "provider_quota_limited" : (pageError ? "page_error" : (loginRequired ? "login_required" : null)),
    message: quotaBlocked ? "The provider page reports a usage/message limit." : (pageError ? "The provider page reports a retryable page error." : (loginRequired ? "The provider page requires login before prompts can be submitted." : null)),
    body_sample: bodyText.slice(0, 180)
  });
})();
"""


def _build_submission_check_js(prompt_id: str) -> str:
    marker_json = json.dumps(prompt_id, ensure_ascii=False)
    return f"""
(() => {{
  const marker = {marker_json};
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const usableInput = el => {{
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 20 && rect.height >= 8;
  }};
  const editableAncestors = node => {{
    for (let el = node.parentElement; el; el = el.parentElement) {{
      const tag = (el.tagName || "").toLowerCase();
      const cls = String(el.className || "");
      if (/textbox-shadow|search-box-input|search-box-container|search-box\\b/.test(cls)) return true;
      if (tag === "textarea" || tag === "input" || el.isContentEditable || el.getAttribute("role") === "textbox") return true;
    }}
    return false;
  }};
  let nonInputMarker = false;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {{
    const node = walker.currentNode;
    if ((node.nodeValue || "").includes(marker) && !editableAncestors(node)) {{
      nonInputMarker = true;
      break;
    }}
  }}
  const inputs = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[role='textbox']")).filter(usableInput);
  const inputValues = inputs.map(el => (el.value || el.innerText || el.textContent || "").trim());
  const mirrorValues = Array.from(document.querySelectorAll(".textbox-shadow,pre"))
    .filter(visible)
    .map(el => (el.innerText || el.textContent || "").trim());
  const inputHasMarker = inputValues.some(value => value.includes(marker));
  const inputHasLongPrompt = inputValues.some(value => value.length > 80 && (value.includes("[QUESTION]") || value.includes("AI Judge") || value.includes("AIJUDGE_ANSWER_START")));
  const mirrorHasMarker = mirrorValues.some(value => value.includes(marker));
  const mirrorHasLongPrompt = mirrorValues.some(value => value.length > 80 && (value.includes("[QUESTION]") || value.includes("AI Judge") || value.includes("AIJUDGE_ANSWER_START")));
  if (inputHasMarker || inputHasLongPrompt || mirrorHasMarker || mirrorHasLongPrompt) return JSON.stringify({{
    ok: true,
    submitted: false,
    reason: (inputHasMarker || mirrorHasMarker) ? "prompt_still_in_input" : "long_prompt_still_in_input",
    message: "Prompt is still in the composer, so the bridge did not confirm a real submission."
  }});
  if (nonInputMarker) return JSON.stringify({{ ok: true, submitted: true, reason: "marker_in_conversation" }});
  if (!inputHasMarker && !inputHasLongPrompt && !mirrorHasMarker && !mirrorHasLongPrompt) return JSON.stringify({{ ok: true, submitted: true, reason: "input_cleared" }});
  return JSON.stringify({{ ok: true, submitted: false, reason: "submission_unknown" }});
}})();
"""


def _build_prompt_presence_js(prompt_id: str) -> str:
    marker_json = json.dumps(prompt_id, ensure_ascii=False)
    return f"""
(() => {{
  const marker = {marker_json};
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const usableInput = el => {{
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 20 && rect.height >= 8;
  }};
  const inputs = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[role='textbox']")).filter(usableInput);
  const inputHasMarker = inputs.some(el => ((el.value || el.innerText || el.textContent || "").includes(marker)));
  const pageHasMarker = (document.body?.innerText || document.body?.textContent || "").includes(marker);
  return JSON.stringify({{
    ok: true,
    prompt_written: inputHasMarker || pageHasMarker,
    input_has_marker: inputHasMarker,
    page_has_marker: pageHasMarker,
    title: document.title,
    url: location.href
  }});
}})();
"""


def _build_retry_submit_js(prompt_id: str) -> str:
    marker_json = json.dumps(prompt_id, ensure_ascii=False)
    return f"""
(() => {{
  const marker = {marker_json};
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const usableInput = el => {{
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 20 && rect.height >= 8;
  }};
  const bodyText = document.body?.innerText || document.body?.textContent || "";
  if (/消息限制已达|使用上限|rate limit|usage limit|message limit|too many requests|升级到\\s*SuperGrok/i.test(bodyText)) {{
    return JSON.stringify({{ ok: false, error: "provider_quota_limited", message: "The provider page reports a usage/message limit.", title: document.title, url: location.href }});
  }}
  if (/操作出了问题|出了点问题|出了些问题|please try again|try again/i.test(bodyText)) {{
    return JSON.stringify({{ ok: false, error: "page_error", message: "The provider page reports a retryable page error.", title: document.title, url: location.href }});
  }}
  if (/doubao\\.com/i.test(location.hostname) && /登录/.test(bodyText) && /下载电脑版/.test(bodyText)) {{
    return JSON.stringify({{ ok: false, error: "login_required", message: "The provider page requires login before prompts can be submitted.", title: document.title, url: location.href }});
  }}
  const valueOf = el => el ? (el.value || el.innerText || el.textContent || "") : "";
  const inputs = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[role='textbox']")).filter(usableInput);
  const activeInput = inputs.find(el => valueOf(el).includes(marker)) || inputs.find(el => valueOf(el).length > 80) || inputs[inputs.length - 1];
  if (!activeInput) return JSON.stringify({{ ok: false, error: "input_not_found", message: "No composer input was available for retry submit.", title: document.title, url: location.href }});
  activeInput.focus();

  const rawLabel = el => [
    el.getAttribute("aria-label") || "",
    el.getAttribute("name") || "",
    el.title || "",
    el.innerText || "",
    el.dataset?.testid || "",
    String(el.className || ""),
    String(el.id || ""),
    (el.closest("[class]")?.className || "")
  ].join(" ").replace(/\\s+/g, " ").trim();
  const buttonLabel = el => rawLabel(el).toLowerCase();
  const hasDisabledAncestor = el => {{
    for (let node = el; node && node !== document.body; node = node.parentElement) {{
      const cls = String(node.className || "").toLowerCase();
      const classDisabled = node.classList && (node.classList.contains("disabled") || node.classList.contains("is-disabled"));
      if (node.disabled || node.getAttribute("aria-disabled") === "true" || node.dataset?.disabled === "true" || classDisabled) return true;
    }}
    return false;
  }};
  const blockedLabel = /(voice|语音|microphone|mic|听写|dictation|工具|附件|upload|attach|file|文件|深度思考|联网|model|模型|settings|设置|历史|new chat|新建|menu|菜单|主菜单|more|更多|view|switch|切换|复制|copy|thumb|赞|踩|regenerate|share|分享|sidebar|侧边栏|search|搜索|stop|停止|pause|暂停|suggestion|建议|示例|起手式)/i;
  const forceSendLabel = /(send|submit|发送|提交|提问|send-button|send button|chat-prompt-send-button|message-input-right-button-send|composer-submit|prompt-send|submit-btn|submit-button|input-send-icon|send-icon|icon-send|icon-send1|send__|arrow-up|up-arrow)/i;
  const nearActiveInput = el => {{
    const inputRect = activeInput.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) return false;
    const vertical = rect.top >= inputRect.top - 260 && rect.bottom <= inputRect.bottom + 260;
    const horizontal = rect.left >= inputRect.left - 260 && rect.right <= inputRect.right + 260;
    return vertical && horizontal;
  }};
  const clickTarget = el => {{
    if (!el) return el;
    if (el.matches?.("button,[role='button'],[class*='send'],[class*='Send'],[class*='submit'],[class*='Submit'],[class*='icon-send']")) return el;
    return el.closest("button,[role='button'],[class*='send'],[class*='Send'],[class*='submit'],[class*='Submit'],[class*='icon-send']") || el;
  }};
  const fireClick = el => {{
    const rect = el.getBoundingClientRect();
    const opts = {{ bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2, pointerType: "mouse" }};
    for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {{
      const Ctor = type.startsWith("pointer") ? PointerEvent : MouseEvent;
      el.dispatchEvent(new Ctor(type, opts));
    }}
    try {{ el.click(); }} catch (_) {{}}
  }};
  const dedupe = items => Array.from(new Set(items.filter(Boolean)));
  const selector = [
    "button",
    "[role='button']",
    "[aria-label]",
    "[class*='send']",
    "[class*='Send']",
    "[class*='submit']",
    "[class*='Submit']",
    "[class*='input-send']",
    "[class*='icon-send']",
    "[class*='arrow']",
    "svg",
    "i",
    "span",
    "div"
  ].join(",");
  const allCandidates = dedupe(Array.from(document.querySelectorAll(selector)).map(clickTarget))
    .filter(el => visible(el) && !hasDisabledAncestor(el));
  const sendCandidates = allCandidates.filter(el => {{
    const label = buttonLabel(el);
    if (!forceSendLabel.test(label)) return false;
    if (blockedLabel.test(label) && !/(submit-btn|input-send-icon|chat-prompt-send-button|message-input-right-button-send|icon-send|icon-send1|send-button)/i.test(label)) return false;
    return nearActiveInput(el) || /bigmodel\\.cn|chat\\.qwen\\.ai|aistudio\\.xiaomimimo\\.com/i.test(location.hostname);
  }});
  let button = sendCandidates[sendCandidates.length - 1] || null;
  if (!button && /aistudio\\.xiaomimimo\\.com/i.test(location.hostname)) {{
    const inputRect = activeInput.getBoundingClientRect();
    const mimoButtons = Array.from(document.querySelectorAll("button"))
      .filter(btn => visible(btn) && !hasDisabledAncestor(btn))
      .filter(btn => {{
        const rect = btn.getBoundingClientRect();
        return rect.left >= inputRect.right - 90
          && rect.top >= inputRect.bottom - 30
          && rect.top <= inputRect.bottom + 80
          && rect.width <= 60
          && rect.height <= 60;
      }});
    button = mimoButtons[mimoButtons.length - 1] || null;
  }}
  if (!button && /agent\\.minimaxi\\.com/i.test(location.hostname)) {{
    const inputRect = activeInput.getBoundingClientRect();
    const miniMaxButtons = dedupe(Array.from(document.querySelectorAll("button,[role='button'],svg,i,span,div")).map(clickTarget))
      .filter(el => visible(el) && !hasDisabledAncestor(el))
      .filter(el => {{
        const rect = el.getBoundingClientRect();
        if (!rect.width || !rect.height || rect.width > 84 || rect.height > 84) return false;
        const label = buttonLabel(el);
        const forceSend = /(send|发送|submit|arrow|icon-send|input-send|up-arrow)/i.test(label);
        if (blockedLabel.test(label) && !forceSend) return false;
        if (!forceSend && /(ppt|视频|图像|回答问题|提出共振|品牌|博客|素材|模板|示例|起手式|suggestion|prompt)/i.test(label)) return false;
        const closeToComposerRight = rect.left >= inputRect.right - 140 && rect.left <= inputRect.right + 220;
        return (forceSend || closeToComposerRight)
          && rect.top >= inputRect.top - 70
          && rect.bottom <= inputRect.bottom + 140;
      }});
    button = miniMaxButtons[miniMaxButtons.length - 1] || null;
  }}
  if (button) {{
    fireClick(button);
    for (const type of ["keydown", "keypress", "keyup"]) {{
      activeInput.dispatchEvent(new KeyboardEvent(type, {{ key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true }}));
    }}
    return JSON.stringify({{ ok: true, method: "retry_button", button_label: buttonLabel(button).slice(0, 180), title: document.title, url: location.href }});
  }}

  const form = activeInput.closest("form");
  if (form && typeof form.requestSubmit === "function") {{
    try {{
      form.requestSubmit();
      return JSON.stringify({{ ok: true, method: "form_request_submit", title: document.title, url: location.href }});
    }} catch (_) {{}}
  }}
  const keyOpts = {{ key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true }};
  for (const type of ["keydown", "keypress", "keyup"]) {{
    activeInput.dispatchEvent(new KeyboardEvent(type, keyOpts));
  }}
  return JSON.stringify({{ ok: true, method: "dom_enter_fallback", title: document.title, url: location.href }});
}})();
"""


def _build_capture_js(prompt_id: str) -> str:
    marker_json = json.dumps(prompt_id, ensure_ascii=False)
    return f"""
(() => {{
  const marker = {marker_json};
  const answerStart = `[AIJUDGE_ANSWER_START:${{marker}}]`;
  const answerEnd = `[AIJUDGE_ANSWER_END:${{marker}}]`;
  const pageRaw = document.body?.innerText || document.body?.textContent || "";
  const conversationRoot = document.querySelector("main")
    || document.querySelector("[role='main']")
    || document.body;
  const bodyRaw = conversationRoot?.innerText || conversationRoot?.textContent || pageRaw;
  const blockingUiActive = /chat\\.deepseek\\.com/i.test(location.hostname) && /已选择\\s*\\d+\\s*组对话/.test(pageRaw);
  const selectors = [
    "[data-message-author-role='assistant']",
    "[data-testid*='conversation-turn']",
    "article",
    ".markdown",
    ".response-message-content",
    "[class*='response-message-content']",
    ".custom-qwen-markdown",
    ".qwen-markdown",
    ".qwen-markdown-paragraph",
    "[class*='phase-answer']",
    "[class*='qwen-markdown']",
    "[class*='markdown-main-panel']",
    "[class*='font-claude-response']",
    "main"
  ];
  const chunks = [];
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const usableInput = el => {{
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 20 && rect.height >= 8;
  }};
  const clean = text => (text || "")
    .replace(/\\r/g, "")
    .replace(/[ \\t]+\\n/g, "\\n")
    .replace(/\\n{{3,}}/g, "\\n\\n")
    .trim();
  const assistantTexts = Array.from(document.querySelectorAll("[data-message-author-role='assistant']"))
    .filter(visible)
    .map(el => clean(el.innerText || el.textContent || ""))
    .filter(text => !text.includes("[QUESTION]"));
  const assistantEmpty = assistantTexts.length > 0 && assistantTexts.every(text => text.length < 30);
  const busyLabel = Array.from(document.querySelectorAll("button,[role='button'],[aria-label]"))
    .filter(el => visible(el))
    .map(el => [el.getAttribute("aria-label") || "", el.innerText || "", el.textContent || "", String(el.className || "")].join(" "))
    .join(" ");
  const pageBusy = /停止回答|stop generating|stop response|停止生成|generating|正在生成/i.test(pageRaw + "\\n" + bodyRaw + "\\n" + busyLabel);
  const thinkingOnly = /已思考\\s*\\d+\\s*s|thinking\\s*\\d+\\s*s|思考中|已经完成思考|已完成思考|完成思考|thinking/i.test(bodyRaw) && assistantEmpty;
  const editableAncestors = node => {{
    for (let el = node.parentElement; el; el = el.parentElement) {{
      const tag = (el.tagName || "").toLowerCase();
      const cls = String(el.className || "");
      if (/textbox-shadow|search-box-input|search-box-container|search-box\\b/.test(cls)) return true;
      if (tag === "textarea" || tag === "input" || el.isContentEditable || el.getAttribute("role") === "textbox") return true;
    }}
    return false;
  }};
  const inputs = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[role='textbox']")).filter(usableInput);
  const markerInInput = inputs.some(el => ((el.value || el.innerText || el.textContent || "").includes(marker)));
  const nonInputParts = [];
  const walker = document.createTreeWalker(conversationRoot || document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {{
    const node = walker.currentNode;
    const value = (node.nodeValue || "").trim();
    if (!value || editableAncestors(node) || !visible(node.parentElement)) continue;
    nonInputParts.push(value);
  }}
  const bodyText = nonInputParts.join("\\n").trim();
  const answerMarkerInBody = bodyText.includes(answerStart);
  const answerMarkerInRaw = bodyRaw.includes(answerStart) || pageRaw.includes(answerStart);
  let markerFound = false;
  let knownError = null;
  let markerText = "";
  let markerClosed = false;
  const extractWrapped = source => {{
    const candidates = [];
    let searchFrom = 0;
    while (true) {{
      const wrappedStartIndex = source.indexOf(answerStart, searchFrom);
      if (wrappedStartIndex < 0) break;
      const contentStart = wrappedStartIndex + answerStart.length;
      const nextStartIndex = source.indexOf(answerStart, contentStart);
      const afterStart = source.slice(contentStart);
      const relativeEndIndex = afterStart.indexOf(answerEnd);
      const endIndex = relativeEndIndex >= 0 ? contentStart + relativeEndIndex : -1;
      const contentEnd = endIndex >= 0 ? endIndex : (nextStartIndex >= 0 ? nextStartIndex : source.length);
      const wrappedText = clean(source.slice(contentStart, contentEnd));
      const isPlaceholder = /^(你的最终答案|最终答案正文)\\s*$/i.test(wrappedText);
      if (wrappedText && !isPlaceholder && wrappedText.length >= 8) {{
        candidates.push({{ text: wrappedText, closed: endIndex >= 0, index: wrappedStartIndex }});
      }}
      searchFrom = contentStart;
    }}
    candidates.sort((a, b) => a.index - b.index);
    return candidates[candidates.length - 1] || {{ text: "", closed: false }};
  }};
  for (const source of [bodyText, bodyRaw, pageRaw]) {{
    const extracted = extractWrapped(source);
    if (extracted.text) {{
      markerText = extracted.text;
      markerClosed = extracted.closed;
      markerFound = true;
      break;
    }}
  }}
  if (answerMarkerInBody || answerMarkerInRaw) {{
    const markerSource = answerMarkerInBody ? bodyText : (bodyRaw.includes(answerStart) ? bodyRaw : pageRaw);
    const afterMarker = clean(markerSource.slice(markerSource.lastIndexOf(answerStart) + answerStart.length));
    if (/(we couldn.t connect|network connection|please check your network|try again|无法连接|网络错误|请稍后重试|出了点问题|出了些问题|出错了)/i.test(afterMarker)) {{
      knownError = {{ code: "model_page_error", message: afterMarker.slice(0, 360) }};
    }}
  }}
  if (!markerText || markerText.length < 80) {{
    for (const selector of selectors) {{
      for (const el of Array.from(document.querySelectorAll(selector))) {{
        const text = clean(el.innerText || el.textContent || "");
        if (text && text.includes(answerStart)) {{
          const extracted = extractWrapped(text);
          if (extracted.text) {{
            markerText = extracted.text;
            markerClosed = extracted.closed;
            markerFound = true;
            break;
          }}
        }}
        if (text && text.length > 60 && !text.includes(marker) && !text.includes("[QUESTION]")) chunks.push(text);
      }}
      if (markerText && markerText.length >= 30) break;
    }}
  }}
  if (!markerText) {{
    const traceLine = `[trace_id: ${{marker}}]`;
    const traceSource = bodyRaw.includes(traceLine) ? bodyRaw : pageRaw;
    const traceIndex = traceSource.lastIndexOf(traceLine);
    if (traceIndex >= 0) {{
      const afterTrace = clean(traceSource.slice(traceIndex + traceLine.length));
      const claudeMatch = afterTrace.match(/Claude responded:\\s*([\\s\\S]*?)(?:\\n\\n\\n\\n\\n(?:Sonnet|Claude is AI)|\\nSonnet\\s+\\d|\\nClaude is AI|\\nShare$|$)/i);
      if (claudeMatch && clean(claudeMatch[1]).length > 60) chunks.push(clean(claudeMatch[1]));
    }}
  }}
  const unique = [];
  for (const text of chunks) {{
    if (!unique.includes(text)) unique.push(text);
  }}
  const pickFallback = list => {{
    const recent = list.slice(-12);
    if (!recent.length) return "";
    return recent
      .map((text, index) => {{
        const keywordBoost = /AIJUDGE|立场|支持|反对|信息不足|风险|下一步|不会配合|提示注入/i.test(text) ? 10000 : 0;
        return {{ text, score: keywordBoost + Math.min(text.length, 4000) + index * 250 }};
      }})
      .sort((a, b) => a.score - b.score)[recent.length - 1].text;
  }};
  const fallbackText = pickFallback(unique);
  const text = markerText && markerText.length >= 80 ? markerText : fallbackText;
  const finalText = markerClosed ? markerText : (markerText && markerText.length >= 80 ? markerText : fallbackText);
  return JSON.stringify({{ ok: true, title: document.title, url: location.href, text: finalText, text_length: finalText.length, marker_found: markerFound, marker_closed: markerClosed, marker_in_input: markerInInput, known_error: knownError, blocking_ui_active: blockingUiActive, assistant_empty: assistantEmpty, thinking_only: thinkingOnly, page_busy: pageBusy }});
}})();
"""


def _build_existing_answer_capture_js(seat: str) -> str:
    seat_json = json.dumps(seat, ensure_ascii=False)
    return f"""
(() => {{
  const seat = {seat_json}.toLowerCase();
  const pageRaw = document.body?.innerText || document.body?.textContent || "";
  const conversationRoot = document.querySelector("main")
    || document.querySelector("[role='main']")
    || document.body;
  const bodyRaw = conversationRoot?.innerText || conversationRoot?.textContent || pageRaw;
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const clean = text => (text || "")
    .replace(/\\r/g, "")
    .replace(/[ \\t]+\\n/g, "\\n")
    .replace(/\\n{{3,}}/g, "\\n\\n")
    .trim();
  const busyLabel = Array.from(document.querySelectorAll("button,[role='button'],[aria-label]"))
    .filter(visible)
    .map(el => [el.getAttribute("aria-label") || "", el.innerText || "", el.textContent || "", String(el.className || "")].join(" "))
    .join(" ");
  const pageBusy = /停止回答|stop generating|stop response|停止生成|generating|正在生成/i.test(pageRaw + "\\n" + bodyRaw + "\\n" + busyLabel);
  const editableAncestors = node => {{
    for (let el = node.parentElement; el; el = el.parentElement) {{
      const tag = (el.tagName || "").toLowerCase();
      if (tag === "textarea" || tag === "input" || el.isContentEditable || el.getAttribute("role") === "textbox") return true;
    }}
    return false;
  }};
  const nonInputParts = [];
  const walker = document.createTreeWalker(conversationRoot || document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {{
    const node = walker.currentNode;
    const value = (node.nodeValue || "").trim();
    if (!value || editableAncestors(node) || !visible(node.parentElement)) continue;
    nonInputParts.push(value);
  }}
  const bodyText = nonInputParts.join("\\n").trim();
  const safeSeat = seat.replace(/[^a-z0-9_-]/gi, "");
  const startRe = new RegExp("\\\\[AIJUDGE_ANSWER_START:(AIJUDGE-" + safeSeat + "-[^\\\\]]+)\\\\]", "gi");
  const candidates = [];
  const fallbackChunks = [];
  let placeholderFound = false;
  const extractFrom = source => {{
    if (!source) return;
    startRe.lastIndex = 0;
    let match;
    while ((match = startRe.exec(source)) !== null) {{
      const promptId = match[1];
      const contentStart = match.index + match[0].length;
      const endToken = `[AIJUDGE_ANSWER_END:${{promptId}}]`;
      const endIndex = source.indexOf(endToken, contentStart);
      const nextStart = source.indexOf("[AIJUDGE_ANSWER_START:", contentStart);
      const contentEnd = endIndex >= 0 ? endIndex : (nextStart >= 0 ? nextStart : source.length);
      const text = clean(source.slice(contentStart, contentEnd));
      const isPlaceholder = /^(你的最终答案|最终答案正文)\\s*$/i.test(text);
      if (isPlaceholder) placeholderFound = true;
      if (text && !isPlaceholder && text.length >= 8) {{
        candidates.push({{ prompt_id: promptId, text, closed: endIndex >= 0, index: match.index }});
      }}
      startRe.lastIndex = contentStart;
    }}
  }};
  extractFrom(bodyText);
  extractFrom(bodyRaw);
  extractFrom(pageRaw);
  const selectors = [
    "[data-message-author-role='assistant']",
    "[data-testid*='conversation-turn']",
    "article",
    ".markdown",
    ".response-message-content",
    "[class*='response-message-content']",
    ".custom-qwen-markdown",
    ".qwen-markdown",
    ".qwen-markdown-paragraph",
    "[class*='phase-answer']",
    "[class*='qwen-markdown']",
    "[class*='markdown-main-panel']",
    "[class*='font-claude-response']",
    "main"
  ];
  for (const selector of selectors) {{
    for (const el of Array.from(document.querySelectorAll(selector))) {{
      if (!visible(el)) continue;
      const text = clean(el.innerText || el.textContent || "");
      if (!text) continue;
      extractFrom(text);
      if (text.length > 160 && !text.includes("[QUESTION]") && !text.includes("你的最终答案")) {{
        fallbackChunks.push(text);
      }}
    }}
  }}
  const unique = [];
  const seen = new Set();
  for (const item of candidates) {{
    const key = `${{item.prompt_id}}::${{item.text}}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(item);
  }}
  unique.sort((a, b) => a.index - b.index);
  const latest = unique[unique.length - 1] || null;
  if (latest) {{
    return JSON.stringify({{
      ok: true,
      title: document.title,
      url: location.href,
      text: latest.text,
      text_length: latest.text.length,
      prompt_id: latest.prompt_id,
      marker_found: true,
      marker_closed: latest.closed,
      fallback_found: false,
      capture_mode: "existing_answer_marker",
      placeholder_found: placeholderFound,
      candidate_count: unique.length,
      page_busy: pageBusy
    }});
  }}
  const fallbackUnique = [];
  for (const text of fallbackChunks) {{
    if (!fallbackUnique.includes(text)) fallbackUnique.push(text);
  }}
  const fallback = fallbackUnique
    .map((text, index) => {{
      const keywordBoost = /AIJUDGE|立场|支持|条件支持|反对|信息不足|风险|下一步|方案|评分|结论|执行/i.test(text) ? 10000 : 0;
      return {{ text, score: keywordBoost + Math.min(text.length, 5000) + index * 200 }};
    }})
    .sort((a, b) => a.score - b.score)
    .pop();
  if (fallback && fallback.text.length >= 180) {{
    return JSON.stringify({{
      ok: true,
      title: document.title,
      url: location.href,
      text: fallback.text,
      text_length: fallback.text.length,
      prompt_id: "",
      marker_found: false,
      marker_closed: false,
      fallback_found: true,
      capture_mode: "existing_answer_fallback",
      placeholder_found: placeholderFound,
      candidate_count: unique.length,
      page_busy: pageBusy
    }});
  }}
  return JSON.stringify({{
    ok: false,
    title: document.title,
    url: location.href,
    text: "",
    text_length: 0,
    marker_found: false,
    fallback_found: false,
    capture_mode: "existing_answer_not_found",
    placeholder_found: placeholderFound,
    candidate_count: unique.length,
    page_busy: pageBusy,
    reason: placeholderFound ? "existing_answer_placeholder" : "existing_answer_not_found",
    message: placeholderFound
      ? "The existing page still shows the AI Judge placeholder instead of the model answer."
      : "No matching AI Judge answer marker was found on the existing page."
  }});
}})();
"""
