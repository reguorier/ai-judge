#!/usr/bin/env python3
"""Chrome DevTools Protocol fixed-tab bridge for AI Judge."""

from __future__ import annotations

import json
import time
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Any, Callable

import requests

from core.seat_personas import SEAT_PERSONAS
from bridges.chrome_fixed_tab_bridge import (
    _build_capture_js,
    _build_clear_blocking_ui_js,
    _build_prepare_submission_ui_js,
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


@dataclass
class CDPTab:
    title: str
    url: str
    page: Any | None = None


def chrome_cdp_status(config: dict[str, Any] | None = None) -> dict[str, Any]:
    endpoint = _endpoint(config)
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
    }


def list_cdp_tabs(config: dict[str, Any] | None = None) -> list[CDPTab]:
    endpoint = _endpoint(config)
    tabs = _cdp_get_json(f"{endpoint}/json/list", timeout=3)
    return [
        CDPTab(title=str(tab.get("title") or ""), url=str(tab.get("url") or ""))
        for tab in tabs
        if tab.get("type") == "page"
    ]


def run_chrome_cdp_tabs(
    question: str,
    seats: list[str],
    config: dict[str, Any],
    mode: str = "flash",
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    status = chrome_cdp_status(config)
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
        browser = playwright.chromium.connect_over_cdp(_endpoint(config), timeout=5000)
        pages = [page for context in browser.contexts for page in context.pages]
        tabs = [CDPTab(title=page.title(), url=page.url, page=page) for page in pages]
        if trace:
            trace("chrome", "cdp_tabs_listed", "读取当前 Chrome CDP 标签页", {
                "count": len(tabs),
                "tabs": [{"title": tab.title, "url": tab.url} for tab in tabs],
            })

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
                "标记必须原样输出，标记外不要输出正文。不要输出“你的最终答案”这几个占位字，请替换成你的实际回答：\n"
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
            try:
                page.bring_to_front()
                _humanized_sleep(config, seat_config, seat, "before_submit")
                fresh_url = str(seat_config.get("fresh_url") or "").strip()
                if fresh_url and config.get("fresh_conversation_per_run", False):
                    page.goto(fresh_url, wait_until="domcontentloaded", timeout=15000)
                    _humanized_sleep(config, seat_config, seat, "after_reload")
                    page.wait_for_timeout(int(float(config.get("fresh_load_seconds") or 3.0) * 1000))
                preflight = _clear_or_recover_page(page, config, seat_config, seat, "preflight", trace)
                prepared = _prepare_submission_ui(page, prompt_id)
                if prepared.get("clicked"):
                    _humanized_sleep(config, seat_config, seat, "after_click")
                if prepared.get("needs_followup"):
                    followup = _prepare_submission_ui(page, prompt_id)
                    prepared["followup"] = followup
                    if followup.get("clicked"):
                        _humanized_sleep(config, seat_config, seat, "after_click")
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
            except Exception as exc:
                submissions[seat] = _failed_result(seat, "cdp_submit_failed", str(exc))
                if trace:
                    trace("seat", "cdp_submit_failed", f"{seat} 发送失败", {"seat": seat, "error": str(exc)})

        poll_deadline = time.time() + timeout_seconds
        pending = {seat for seat, item in submissions.items() if item.get("page")}
        while pending and time.time() < poll_deadline:
            elapsed = max(0.0, timeout_seconds - (poll_deadline - time.time()))
            if progress:
                progress(f"Chrome CDP 回答轮询：剩余 {len(pending)} 席", 0.42 + 0.30 * min(1.0, elapsed / max(timeout_seconds, 1)))
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


def _endpoint(config: dict[str, Any] | None = None) -> str:
    return str((config or {}).get("chrome_cdp_endpoint") or DEFAULT_CDP_ENDPOINT).rstrip("/")


def _cdp_get_json(url: str, timeout: float) -> Any:
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()
