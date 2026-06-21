#!/usr/bin/env python3
"""Chrome DevTools Protocol fixed-tab bridge for AI Judge."""

from __future__ import annotations

import json
import os
import re
import signal
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

_SEAT_PROMPT_CHAR_LIMITS = {
    # Wenxin rejects oversized composer text and shows "输入区字数超限".
    "wenxin": 3000,
    # These web composers are more reliable with compact strategic prompts.
    "qwen": 4200,
    "minimax": 4200,
    "chatgpt": 5200,
    "kimi": 6500,
    "grok": 4200,
    "yuanbao": 4200,
    "doubao": 3600,
    "mimo": 3000,
    "zhipu": 3200,
    # SparkDesk can accept longer text, but the public desk often drops/redirects
    # AI Judge's full system wrapper. Keep this seat on a compact contract.
    "xunfei": 1200,
}

_MINIMAX_COMPOSER_SELECTOR = (
    ".tiptap.ProseMirror[contenteditable='true'], "
    "[class*='rich-text-editor'][contenteditable='true'], "
    ".ProseMirror[contenteditable='true'], "
    "div[contenteditable='true'][role='textbox'], "
    "div[role='textbox'][contenteditable='true'], "
    "textarea, [role='textbox']"
)
_MIMO_COMPOSER_SELECTOR = (
    "textarea,input,[contenteditable='true'],[contenteditable='plaintext-only'],"
    "[role='textbox'],[aria-label*='输入'],[placeholder*='输入']"
)
_XUNFEI_COMPOSER_SELECTOR = (
    "textarea,input,[contenteditable='true'],[contenteditable='plaintext-only'],"
    "[role='textbox'],[aria-label*='输入'],[aria-label*='消息'],[aria-label*='提问'],"
    "[placeholder*='输入'],[placeholder*='消息'],[placeholder*='提问'],"
    "[placeholder*='有问必答'],[placeholder*='可以问'],"
    "[class*='input' i],[class*='editor' i],[class*='textarea' i],[class*='composer' i]"
)


def _compact_prompt_for_seat(seat: str, prompt: str) -> tuple[str, dict[str, Any] | None]:
    """Fit provider composer limits while preserving the answer marker tail."""
    limit = int(_SEAT_PROMPT_CHAR_LIMITS.get(seat) or 0)
    if limit <= 0 or len(prompt) <= limit:
        return prompt, None
    if seat == "xunfei":
        return _compact_xunfei_prompt(prompt, limit)
    notice = (
        "\n\n[AI Judge bridge note: 为适配该网页输入上限，已压缩席位提示词；"
        "请严格依据题目、已给证据和最终答案标记作答，不得虚构；"
        "直接在当前聊天输出正文，不要创建文档、画布或卡片，不要只输出思考过程。]\n\n"
    )
    head_len = max(1000, int(limit * 0.45))
    tail_len = max(1200, limit - head_len - len(notice))
    compacted = prompt[:head_len].rstrip() + notice + prompt[-tail_len:].lstrip()
    if len(compacted) > limit:
        compacted = compacted[: max(0, limit - tail_len)] + prompt[-tail_len:]
    return compacted, {
        "original_chars": len(prompt),
        "compacted_chars": len(compacted),
        "limit": limit,
        "head_chars": head_len,
        "tail_chars": tail_len,
    }


def _compact_xunfei_prompt(prompt: str, limit: int) -> tuple[str, dict[str, Any]]:
    """Create a short SparkDesk prompt while preserving AI Judge answer markers."""
    original = str(prompt or "")

    def _extract(pattern: str, default: str = "") -> str:
        match = re.search(pattern, original, flags=re.S)
        return (match.group(1).strip() if match else default).strip()

    def _extract_from(text: str, pattern: str, default: str = "") -> str:
        match = re.search(pattern, text, flags=re.S)
        return (match.group(1).strip() if match else default).strip()

    system = _extract(r"\[SYSTEM\]\s*(.*?)(?:\n\s*\[QUESTION\]|\Z)", "")
    question = _extract(
        r"\[QUESTION\]\s*(.*?)(?:\n\n请作为 AI Judge|\n\n重要：|\n\n桥接器输出合同：|\Z)",
        original[:800],
    )
    source_question = "question_block"
    user_task = _extract_from(
        question,
        r"用户原始任务：\s*(.*?)(?:\n\n规范化任务：|\n\n任务意图：|\n\n裁决模式：|\Z)",
    )
    normalized_task = _extract_from(
        question,
        r"规范化任务：\s*(.*?)(?:\n\n任务意图：|\n\n裁决模式：|\n\n输出必须包含：|\Z)",
    )
    if user_task:
        question = user_task
        source_question = "resonance_original_task"
    elif normalized_task:
        question = normalized_task
        source_question = "resonance_normalized_task"
    question = re.sub(r"^\[AIJUDGE_PRE_RUN_CONFIRMATION\]\s*", "", question).strip()
    question = re.sub(r"\n\s*\[(?:DOMAIN_PACK|五维预拆解|THREE_ROUND_PROTOCOL)[^\]]*\].*", "", question, flags=re.S).strip()
    start_marker = _extract(r"(\[AIJUDGE_ANSWER_START:[^\]]+\])", "")
    end_marker = _extract(r"(\[AIJUDGE_ANSWER_END:[^\]]+\])", "")
    trace_id = _extract(r"(\[trace_id:[^\]]+\])", "")
    if not start_marker or not end_marker:
        marker_tail = original[-420:]
    else:
        marker_tail = f"{start_marker}\n你的最终答案\n{end_marker}"
        if trace_id:
            marker_tail += f"\n\n{trace_id}"

    system = system[:180]
    marker_budget = len(marker_tail) + 260
    question_budget = max(220, limit - marker_budget - len(system))
    compact_question = question[:question_budget].rstrip()
    compact = (
        f"[SYSTEM] {system or '作为科大讯飞 AI Judge 席位，请用推理模式给出稳健判断。'}\n\n"
        f"[QUESTION] {compact_question}\n\n"
        "请在推理模式下完成本轮 AI Judge 回答：\n"
        "1. 先给明确立场：支持 / 条件支持 / 反对 / 信息不足。\n"
        "2. 给 2-3 条关键理由，标注事实依据或待验证假设。\n"
        "3. 给最大风险和最小下一步。\n"
        "4. 最终正文必须完整包裹在以下标记之间，标记必须原样保留：\n"
        f"{marker_tail}"
    )
    if len(compact) > limit:
        overflow = len(compact) - limit
        compact_question = compact_question[: max(120, len(compact_question) - overflow - 20)].rstrip()
        compact = (
            f"[SYSTEM] {system or '作为科大讯飞 AI Judge 席位，请用推理模式给出稳健判断。'}\n\n"
            f"[QUESTION] {compact_question}\n\n"
            "请给明确立场、2条理由、最大风险、最小下一步；最终正文必须完整包裹在以下标记之间：\n"
            f"{marker_tail}"
        )
    return compact, {
        "original_chars": len(original),
        "compacted_chars": len(compact),
        "limit": limit,
        "strategy": "xunfei_short_contract",
        "source_question": source_question,
        "question_chars": len(compact_question),
    }


def _minimum_complete_answer_chars(seat: str, config: dict[str, Any], item: dict[str, Any] | None = None) -> int:
    try:
        return int(minimum_required_response_chars(seat, config=config, item=item or {}))
    except Exception:
        return 1


def _answer_contract_shortfall(
    seat: str,
    config: dict[str, Any],
    item: dict[str, Any] | None,
    response_text: str,
) -> tuple[bool, int, int]:
    response_chars = len(str(response_text or "").strip())
    if _answer_contract_requires_json(config, item):
        return False, response_chars, 0
    min_chars = _minimum_complete_answer_chars(seat, config, item)
    return response_chars < min_chars, response_chars, min_chars


def _answer_contract_requires_json(config: dict[str, Any] | None, item: dict[str, Any] | None = None) -> bool:
    """Return true when the collection contract is a structured JSON receipt.

    JSON receipt tasks must not use the generic "long answer + start/end marker"
    recovery prompt. That prompt is useful for prose reports, but it corrupts
    betting receipts by encouraging explanations around the JSON object.
    """
    contracts: list[dict[str, Any]] = []
    if isinstance(item, dict) and isinstance(item.get("answer_contract"), dict):
        contracts.append(item["answer_contract"])
    if isinstance(config, dict) and isinstance(config.get("answer_contract"), dict):
        contracts.append(config["answer_contract"])
    if not contracts:
        return False
    for contract in contracts:
        fmt = str(
            contract.get("response_format")
            or contract.get("format")
            or contract.get("schema_format")
            or ""
        ).strip().lower()
        kind = str(contract.get("kind") or "").strip().lower()
        reason = str(contract.get("reason") or "").lower()
        if fmt in {"json", "json_object", "structured_json"}:
            return True
        if contract.get("structured_json_required") is True or contract.get("json_required") is True:
            return True
        if kind == "sports_worldcup_pool_prediction_complete_answer" and "json" in reason:
            return True
    return False


def _answer_contract_requires_compact_line(config: dict[str, Any] | None, item: dict[str, Any] | None = None) -> bool:
    """Return true for the PRED-INVEST compact line receipt contract.

    This contract is deliberately not a generic prose answer.  The generic
    "你的最终答案" marker prompt causes models to echo placeholders or wrap the
    line protocol in explanatory text, so CDP submission must use a dedicated
    wrapper.
    """
    contracts: list[dict[str, Any]] = []
    if isinstance(item, dict) and isinstance(item.get("answer_contract"), dict):
        contracts.append(item["answer_contract"])
    if isinstance(config, dict) and isinstance(config.get("answer_contract"), dict):
        contracts.append(config["answer_contract"])
    for contract in contracts:
        fmt = str(contract.get("response_format") or contract.get("format") or "").strip().lower()
        kind = str(contract.get("kind") or "").strip().lower()
        reason = str(contract.get("reason") or "").strip().lower()
        if fmt in {"compact_line_receipt", "line_receipt"}:
            return True
        if kind == "sports_worldcup_pool_prediction_complete_answer" and "pred_invest_compact_receipt" in reason:
            return True
    return False


def _prompt_with_answer_marker(
    prompt: str,
    prompt_id: str,
    *,
    config: dict[str, Any] | None = None,
    item: dict[str, Any] | None = None,
) -> str:
    if _answer_contract_requires_compact_line(config, item):
        return (
            f"{prompt}\n\n"
            "桥接器输出合同：你必须只输出当前轮 PRED_INVEST_RECEIPT 投注单，不要复述题目，不要解释，不要 Markdown。"
            "最终回答必须完整包裹在以下两行标记之间；标记内第一行必须是 PRED_INVEST_RECEIPT，"
            "并且必须覆盖题目列出的全部 match_id，AUDIT 行 ready 必须为 true：\n"
            f"[AIJUDGE_ANSWER_START:{prompt_id}]\n"
            "PRED_INVEST_RECEIPT\n"
            f"[AIJUDGE_ANSWER_END:{prompt_id}]\n\n"
            f"[trace_id: {prompt_id}]"
        )
    return (
        f"{prompt}\n\n"
        "重要：不要只进行思考，必须在最终回答区域输出正文。请将你的最终答案完整包裹在以下两行标记之间，"
        "标记必须原样输出，标记外不要输出正文。不要输出（你的最终答案）这几个占位字，请替换成你的实际回答：\n"
        f"[AIJUDGE_ANSWER_START:{prompt_id}]\n"
        "你的最终答案\n"
        f"[AIJUDGE_ANSWER_END:{prompt_id}]\n\n"
        f"[trace_id: {prompt_id}]"
    )


def _wait_for_provider_composer(page: Any, seat: str) -> dict[str, Any]:
    """Wait for providers whose new-task click mounts the composer asynchronously."""
    if seat not in {"minimax", "mimo", "xunfei"}:
        return {"ok": True, "waited": False}
    if seat == "mimo":
        selector = _MIMO_COMPOSER_SELECTOR
        timeout = 10000
    elif seat == "xunfei":
        selector = _XUNFEI_COMPOSER_SELECTOR
        timeout = 12000
    else:
        selector = _MINIMAX_COMPOSER_SELECTOR
        timeout = 8000
    if seat == "xunfei" and os.environ.get("AI_JUDGE_XUNFEI_STABILITY_GATE", "1") != "0":
        ready = _ensure_xunfei_desk_ready(page, wait_ms=2200, stability_ms=7200)
        ready.update({"waited": True, "seat": seat, "selector": selector})
        return ready
    if seat == "xunfei":
        try:
            current_url = str(getattr(page, "url", "") or "")
            if "xinghuo.xfyun.cn/desk" not in current_url:
                page.goto("https://xinghuo.xfyun.cn/desk", wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1600)
        except Exception:
            # The SparkDesk shell sometimes blocks direct routing until the
            # user session hydrates.  The activation loop below is the fallback.
            pass
        last_activation: dict[str, Any] | None = None
        last_error = ""
        composer_probe_js = """() => {
          const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const usableInput = el => {
            if (!visible(el)) return false;
            const rect = el.getBoundingClientRect();
            return rect.width >= 20 && rect.height >= 8;
          };
          const candidates = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[contenteditable='plaintext-only'],[role='textbox']"))
            .filter(usableInput);
          const input = candidates[candidates.length - 1] || null;
          return {
            ok: !!input,
            url: location.href,
            title: document.title,
            tag: input ? String(input.tagName || "") : "",
            placeholder: input ? String(input.getAttribute?.("placeholder") || "") : "",
            aria_label: input ? String(input.getAttribute?.("aria-label") || "") : ""
          };
        }"""
        activation_js = """() => {
          const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const labelOf = el => [
            el.getAttribute?.("placeholder") || "",
            el.getAttribute?.("aria-label") || "",
            el.getAttribute?.("data-placeholder") || "",
            el.title || "",
            el.innerText || "",
            el.textContent || "",
            String(el.className || "")
          ].join(" ").replace(/\\s+/g, " ").trim();
          const textOf = el => (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
          const usableInput = el => {
            if (!visible(el)) return false;
            const rect = el.getBoundingClientRect();
            return rect.width >= 20 && rect.height >= 8;
          };
          const hasInput = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[contenteditable='plaintext-only'],[role='textbox']"))
            .some(usableInput);
          if (hasInput) return {ok:true, already_has_input:true, url: location.href};
          const isActionEntry = el => {
            const tag = String(el.tagName || "").toUpperCase();
            const role = String(el.getAttribute?.("role") || "").toLowerCase();
            const cls = String(el.className || "");
            const label = labelOf(el);
            if (label.length > 80 && !/(btn|button|try-now|chat|dialog|conversation)/i.test(cls)) return false;
            if (/讯飞绘文|讯飞智文|讯飞文书|星火纪要|星火投标|星火陪练|讯飞绘镜/.test(label) && label.length > 60) return false;
            return tag === "A" || tag === "BUTTON" || role === "button" || /(btn|button|try-now|chat|dialog|conversation)/i.test(cls) || label.length <= 16;
          };
          const scoreEntry = el => {
            const rect = el.getBoundingClientRect();
            if (rect.width < 20 || rect.height < 16) return 0;
            if (!isActionEntry(el)) return 0;
            const label = labelOf(el);
            const text = textOf(el);
            const cls = String(el.className || "");
            if (/^SparkDesk$/i.test(text) && rect.top >= -8 && rect.top <= 140) return 1100;
            if (/SparkDesk/i.test(label) && label.length <= 120 && rect.top >= -8 && rect.top <= 160) return 1000;
            if (text === "新建对话" || label === "新建对话") return 850;
            if (text === "立即对话" || label === "立即对话") return 760 + (/(try-now|hm-content__btn)/i.test(cls) ? 80 : 0);
            return 0;
          };
          const target = Array.from(document.querySelectorAll("a,button,[role='button'],[class*='btn'],[class*='button'],[class*='try-now'],div,span"))
            .filter(visible)
            .map(el => ({el, score: scoreEntry(el)}))
            .filter(item => item.score > 0)
            .sort((a, b) => b.score - a.score)[0]?.el || null;
          if (!target) return {
            ok:false,
            error:"xunfei_chat_entry_not_found",
            url: location.href,
            title: document.title,
            body_sample: (document.body?.innerText || "").replace(/\\s+/g, " ").trim().slice(0, 220)
          };
          const rect = target.getBoundingClientRect();
          const opts = {bubbles:true, cancelable:true, view:window, clientX:rect.left + rect.width / 2, clientY:rect.top + rect.height / 2};
          for (const type of ["pointerdown","mousedown","pointerup","mouseup","click"]) {
            const Ctor = type.startsWith("pointer") ? PointerEvent : MouseEvent;
            try { target.dispatchEvent(new Ctor(type, opts)); } catch (_) {}
          }
          try { target.click(); } catch (_) {}
          return {ok:true, clicked:true, label:labelOf(target).slice(0,80), text:textOf(target).slice(0,80), url: location.href};
        }"""
        for attempt in range(1, 7):
            try:
                last_activation = page.evaluate(activation_js)
            except Exception as exc:
                last_activation = {"ok": False, "error": str(exc)}
            page.wait_for_timeout(1000)
            try:
                probe = page.evaluate(composer_probe_js)
            except Exception as exc:
                probe = {"ok": False, "error": str(exc)}
            if isinstance(probe, dict) and probe.get("ok"):
                return {
                    "ok": True,
                    "waited": True,
                    "seat": seat,
                    "url": page.url,
                    "selector": selector,
                    "attempt": attempt,
                    "activation": last_activation,
                    "probe": probe,
                }
            try:
                page.wait_for_selector(selector, state="visible", timeout=min(timeout, 2500))
                return {
                    "ok": True,
                    "waited": True,
                    "seat": seat,
                    "url": page.url,
                    "selector": selector,
                    "attempt": attempt,
                    "activation": last_activation,
                }
            except Exception as exc:
                last_error = str(exc)
        return {
            "ok": False,
            "waited": True,
            "seat": seat,
            "url": getattr(page, "url", ""),
            "error": last_error,
            "activation": last_activation,
        }
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout)
        return {"ok": True, "waited": True, "seat": seat, "url": page.url, "selector": selector}
    except Exception as exc:
        return {"ok": False, "waited": True, "seat": seat, "url": getattr(page, "url", ""), "error": str(exc)}


# P2.9: CDP submit subphase hard timeouts (seconds)
_CDP_SUBPHASE_TIMEOUT = {
    "tab_focus": 5,
    "input_locate": 8,
    "text_inject": 8,
    "send_click": 8,
    "post_click_ack": 10,
    "answer_poll_handoff": 5,
}

from core.seat_personas import SEAT_PERSONAS
from core.bridge_run_lock import set_bridge_phase  # P2.9
from core.seat_execution_policy import minimum_required_response_chars
from bridges.chrome_fixed_tab_bridge import (
    _build_capture_js,
    _build_click_send_js,
    _build_clear_blocking_ui_js,
    _build_existing_answer_capture_js,
    _build_prepare_submission_ui_js,
    _build_prompt_presence_js,
    _build_retry_submit_js,
    _build_submission_check_js,
    _build_write_prompt_js,
    _append_prepare_followup,
    _capture_acceptance,
    _failed_result,
    _humanized_sleep,
    _page_state_needs_reload,
    _quality_mode_failure,
    _quality_mode_policy_snapshot,
    _quality_mode_prepare_required,
    _quality_mode_prepare_verified,
    _quality_mode_required_mode,
    _quality_mode_strict_required,
    _quality_mode_trace_action,
    _quality_mode_trace_message,
    _response_text_from_capture,
    _seat_config,
    _seat_prompt,
    _seat_timeout_seconds,
    _should_send_final_answer_nudge,
)


DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:9222"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_XUNFEI_DESK_EVENT_PATH = _PROJECT_ROOT / "data" / "xunfei_desk_events.jsonl"
_XUNFEI_DESK_GUARD_TTL_MS = 180_000
_XUNFEI_DESK_GUARD_SCRIPT = r"""
(() => {
  const ACTIVE_KEY = "ai_judge_xunfei_hold_desk";
  const UNTIL_KEY = "ai_judge_xunfei_hold_until";
  const LAST_KEY = "ai_judge_xunfei_last_good_path";
  const REDIRECT_KEY = "ai_judge_xunfei_guard_redirects";
  const BLOCKED_PATHS = new Set(["/", "/spark", "/homepage"]);
  const now = Date.now();
  const nextUntil = now + 180000;
  const oldUntil = Number(sessionStorage.getItem(UNTIL_KEY) || "0") || 0;
  sessionStorage.setItem(ACTIVE_KEY, "1");
  sessionStorage.setItem(UNTIL_KEY, String(Math.max(oldUntil, nextUntil)));
  window.__AIJUDGE_XUNFEI_ROUTE_GUARD_BLOCKED__ = window.__AIJUDGE_XUNFEI_ROUTE_GUARD_BLOCKED__ || [];
  const blocked = window.__AIJUDGE_XUNFEI_ROUTE_GUARD_BLOCKED__;
  const active = () => (
    sessionStorage.getItem(ACTIVE_KEY) === "1" &&
    Date.now() < (Number(sessionStorage.getItem(UNTIL_KEY) || "0") || 0)
  );
  const remember = () => {
    if (location.hostname === "xinghuo.xfyun.cn" && location.pathname === "/desk") {
      sessionStorage.setItem(LAST_KEY, "/desk");
    }
  };
  const blockedUrl = url => {
    try {
      const next = new URL(String(url || location.href), location.href);
      return active() &&
        location.hostname === "xinghuo.xfyun.cn" &&
        next.origin === location.origin &&
        sessionStorage.getItem(LAST_KEY) === "/desk" &&
        BLOCKED_PATHS.has(next.pathname);
    } catch (_) {
      return false;
    }
  };
  remember();
  if (!window.__AIJUDGE_XUNFEI_ROUTE_GUARD__) {
    window.__AIJUDGE_XUNFEI_ROUTE_GUARD__ = true;
    const pushState = history.pushState.bind(history);
    const replaceState = history.replaceState.bind(history);
    history.pushState = function(state, title, url) {
      if (blockedUrl(url)) {
        blocked.push({type: "push", url: String(url), ts: Date.now()});
        return replaceState(state, title, "/desk");
      }
      const result = pushState(state, title, url);
      remember();
      return result;
    };
    history.replaceState = function(state, title, url) {
      if (blockedUrl(url)) {
        blocked.push({type: "replace", url: String(url), ts: Date.now()});
        return replaceState(state, title, "/desk");
      }
      const result = replaceState(state, title, url);
      remember();
      return result;
    };
    window.addEventListener("popstate", () => {
      if (blockedUrl(location.href)) {
        blocked.push({type: "popstate", url: location.href, ts: Date.now()});
        history.replaceState(null, "", "/desk");
      }
      remember();
    });
    const timer = setInterval(() => {
      if (!active()) {
        clearInterval(timer);
        return;
      }
      remember();
      if (blockedUrl(location.href) && location.pathname !== "/desk") {
        blocked.push({type: "interval", url: location.href, ts: Date.now()});
        history.replaceState(null, "", "/desk");
      }
    }, 250);
  }
  if (active() && sessionStorage.getItem(LAST_KEY) === "/desk" && BLOCKED_PATHS.has(location.pathname)) {
    const redirects = Number(sessionStorage.getItem(REDIRECT_KEY) || "0") || 0;
    blocked.push({type: "document_start_home", url: location.href, redirects, ts: Date.now()});
    history.replaceState(null, "", "/desk");
    if (redirects < 3) {
      sessionStorage.setItem(REDIRECT_KEY, String(redirects + 1));
      setTimeout(() => {
        const hasComposer = !!document.querySelector("#askwindow-textarea, textarea, [role='textbox']");
        if (active() && location.hostname === "xinghuo.xfyun.cn" && location.pathname !== "/desk" && !hasComposer) {
          location.replace("/desk");
        }
      }, 80);
    }
  }
  return {
    installed: true,
    active: active(),
    url: location.href,
    until: Number(sessionStorage.getItem(UNTIL_KEY) || "0") || 0,
    last_good_path: sessionStorage.getItem(LAST_KEY) || "",
    blocked_count: blocked.length,
    redirects: Number(sessionStorage.getItem(REDIRECT_KEY) || "0") || 0
  };
})()
"""


def _cdp_quality_mode_policy(config: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = (config or {}).get("quality_mode_policy")
    return policy if isinstance(policy, dict) else _quality_mode_policy_snapshot()


def _record_xunfei_desk_event(event: dict[str, Any]) -> None:
    try:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **event,
        }
        _XUNFEI_DESK_EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _XUNFEI_DESK_EVENT_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def _install_xunfei_desk_guard(page: Any) -> dict[str, Any]:
    """Install a temporary SparkDesk route guard for AI Judge submission windows."""
    details: dict[str, Any] = {"ok": False}
    try:
        if hasattr(page, "add_init_script"):
            try:
                page.add_init_script(_XUNFEI_DESK_GUARD_SCRIPT)
                details["init_script"] = True
            except Exception as exc:
                details["init_script_error"] = str(exc)[:180]
        result = page.evaluate(_XUNFEI_DESK_GUARD_SCRIPT)
        if isinstance(result, dict):
            details.update(result)
        else:
            details["result"] = result
        details["ok"] = True
    except Exception as exc:
        details["error"] = str(exc)[:240]
    return details


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
    target_id: str = ""
    page: Any | None = None


def _target_closed_error(error: Any) -> bool:
    text = str(error or "").lower()
    return any(
        marker in text
        for marker in (
            "target page",
            "target closed",
            "context or browser has been closed",
            "browser has been closed",
            "page has been closed",
        )
    )


def _page_is_closed(page: Any) -> bool:
    if page is None:
        return True
    try:
        return bool(page.is_closed())
    except Exception:
        return False


def _live_cdp_tabs(browser: Any) -> list[CDPTab]:
    tabs: list[CDPTab] = []
    try:
        contexts = list(getattr(browser, "contexts", []) or [])
    except Exception:
        return tabs
    for context in contexts:
        for page in list(getattr(context, "pages", []) or []):
            if _page_is_closed(page):
                continue
            try:
                url = str(page.url or "")
            except Exception:
                continue
            tabs.append(CDPTab(title=_safe_page_title(page), url=url, page=page))
    return tabs


def ensure_chrome_cdp_awake(
    config: dict[str, Any] | None = None,
    *,
    open_tabs: bool = True,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Wake the dedicated AI Judge Chrome CDP bridge without killing the user's Chrome."""
    with _cdp_wake_lock(config):
        return _ensure_chrome_cdp_awake_locked(config, open_tabs=open_tabs, trace=trace)


def _ensure_chrome_cdp_awake_locked(
    config: dict[str, Any] | None = None,
    *,
    open_tabs: bool = True,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Wake Chrome CDP while holding the interprocess wake lock."""
    config = config or {}
    endpoint = _endpoint(config)
    status = chrome_cdp_status(config)
    bypass_cooldown = False
    if status.get("reason") in {"wrong_cdp_profile", "profile_marker_missing"} and config.get("auto_terminate_wrong_cdp_profile", True):
        terminated = _terminate_cdp_process(status.get("process") or {}, trace)
        bypass_cooldown = bool(terminated)
        status = chrome_cdp_status(config)
    if (
        status.get("reason") == "cdp_playwright_unhealthy"
        and config.get("auto_recover_unhealthy_cdp", True)
        and (status.get("process") or {}).get("profile_match") is True
    ):
        terminated = _terminate_cdp_process(status.get("process") or {}, trace)
        bypass_cooldown = bool(terminated)
        status = chrome_cdp_status(config)
    if status.get("available"):
        opened = _ensure_enabled_cdp_tabs(config, trace) if open_tabs else []
        result = {"ok": True, "woke": False, "endpoint": endpoint, "opened_tabs": opened, "status": status, "quality_mode_policy": _cdp_quality_mode_policy(config)}
        _write_cdp_state(config, result)
        return result

    if config.get("auto_wake_cdp") is False:
        result = {"ok": False, "woke": False, "endpoint": endpoint, "reason": status.get("reason"), "status": status, "quality_mode_policy": _cdp_quality_mode_policy(config)}
        _write_cdp_state(config, result)
        return result

    if not bypass_cooldown and _cdp_wake_in_cooldown(config):
        result = {
            "ok": False,
            "woke": False,
            "endpoint": endpoint,
            "reason": "wake_cooldown",
            "status": status,
            "quality_mode_policy": _cdp_quality_mode_policy(config),
        }
        _write_cdp_state(config, result)
        return result

    _write_cdp_state(config, {"ok": False, "woke": False, "endpoint": endpoint, "reason": "wake_starting", "quality_mode_policy": _cdp_quality_mode_policy(config)})
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
                "quality_mode_policy": _cdp_quality_mode_policy(config),
            })
    except Exception as exc:
        result = {"ok": False, "woke": False, "endpoint": endpoint, "reason": "launch_failed", "error": str(exc), "launch_strategy": launch_label, "quality_mode_policy": _cdp_quality_mode_policy(config)}
        _write_cdp_state(config, result)
        return result

    deadline = time.time() + float(config.get("auto_wake_wait_seconds") or 25)
    while time.time() < deadline:
        time.sleep(0.75)
        status = chrome_cdp_status(config)
        if status.get("available"):
            opened = _ensure_enabled_cdp_tabs(config, trace) if open_tabs else []
            result = {"ok": True, "woke": True, "endpoint": endpoint, "opened_tabs": opened, "status": status, "launch_strategy": launch_label, "quality_mode_policy": _cdp_quality_mode_policy(config)}
            _write_cdp_state(config, result)
            return result
    result = {"ok": False, "woke": True, "endpoint": endpoint, "reason": "wake_timeout", "status": chrome_cdp_status(config), "launch_strategy": launch_label, "quality_mode_policy": _cdp_quality_mode_policy(config)}
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
                "quality_mode_policy": _cdp_quality_mode_policy(config),
            }
        if process.get("pid") and process.get("profile_match") is False:
            return {
                "available": False,
                "reason": "wrong_cdp_profile",
                "message": "Chrome CDP port is owned by a non AI Judge profile.",
                "endpoint": endpoint,
                "process": process,
                "profile_marker": marker,
                "quality_mode_policy": _cdp_quality_mode_policy(config),
            }
    try:
        version = _cdp_get_json(f"{endpoint}/json/version", timeout=2)
        tabs = _cdp_get_json(f"{endpoint}/json/list", timeout=2)
    except Exception as exc:
        return {"available": False, "reason": "cdp_unavailable", "message": str(exc), "endpoint": endpoint, "quality_mode_policy": _cdp_quality_mode_policy(config)}
    probe: dict[str, Any] | None = None
    if (config or {}).get("cdp_playwright_probe", True):
        probe = _playwright_cdp_probe(config, timeout_seconds=float((config or {}).get("cdp_probe_timeout_seconds") or 4))
        if not probe.get("ok"):
            return {
                "available": False,
                "reason": "cdp_playwright_unhealthy",
                "message": probe.get("message") or "Playwright could not attach to Chrome CDP.",
                "endpoint": endpoint,
                "browser": version.get("Browser"),
                "tab_count": len(tabs) if isinstance(tabs, list) else 0,
                "process": process,
                "playwright_probe": probe,
                "quality_mode_policy": _cdp_quality_mode_policy(config),
            }
    result = {
        "available": True,
        "reason": "ready",
        "endpoint": endpoint,
        "browser": version.get("Browser"),
        "tab_count": len(tabs) if isinstance(tabs, list) else 0,
        "process": process,
        "quality_mode_policy": _cdp_quality_mode_policy(config),
    }
    if probe is not None:
        result["playwright_probe"] = probe
    return result


def _connect_cdp_browser(playwright: Any, config: dict[str, Any], timeout_ms: int) -> Any:
    """Attach Playwright to an existing Chrome CDP endpoint.

    Chrome 149 can reject Playwright's default context overrides with
    Browser.setDownloadBehavior / browser context management errors. no_defaults
    keeps the user's fixed tabs untouched and avoids that default override path.
    """
    with _local_cdp_proxy_bypass():
        try:
            return playwright.chromium.connect_over_cdp(_connect_endpoint(config), timeout=timeout_ms, no_defaults=True)
        except TypeError:
            return playwright.chromium.connect_over_cdp(_connect_endpoint(config), timeout=timeout_ms)


def _playwright_cdp_probe(config: dict[str, Any] | None = None, *, timeout_seconds: float = 4) -> dict[str, Any]:
    started = time.time()
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = _connect_cdp_browser(playwright, config or {}, int(timeout_seconds * 1000))
            contexts = browser.contexts
            pages = sum(len(context.pages) for context in contexts)
            # This browser is an attachment to the user's fixed Chrome CDP
            # profile, not a Playwright-owned browser. Calling close() here can
            # close the external Chrome target and invalidate every fixed tab.
            # Let the Playwright context manager tear down only its transport.
        return {
            "ok": True,
            "elapsed_seconds": round(time.time() - started, 3),
            "contexts": len(contexts),
            "pages": pages,
        }
    except Exception as exc:
        return {
            "ok": False,
            "elapsed_seconds": round(time.time() - started, 3),
            "error_type": type(exc).__name__,
            "message": str(exc)[:800],
        }


def list_cdp_tabs(config: dict[str, Any] | None = None) -> list[CDPTab]:
    endpoint = _endpoint(config)
    tabs = _cdp_get_json(f"{endpoint}/json/list", timeout=3)
    return [
        CDPTab(
            title=str(tab.get("title") or ""),
            url=str(tab.get("url") or ""),
            target_id=str(tab.get("id") or ""),
        )
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
    return False


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


@contextmanager
def _cdp_wake_lock(config: dict[str, Any] | None = None):
    """Serialize Chrome wake attempts so concurrent probes do not launch duplicates."""
    path = _cdp_state_path(config).with_suffix(".lock")
    handle = None
    locked = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+", encoding="utf-8")
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
        except Exception:
            locked = False
        yield
    finally:
        if handle is not None:
            if locked:
                try:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
            try:
                handle.close()
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
    if config.get("dedupe_enabled_cdp_tabs", True):
        closed = _dedupe_enabled_cdp_tabs(config, tabs, endpoint, trace)
        if closed:
            try:
                tabs = list_cdp_tabs(config)
            except Exception:
                pass
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


def _trace_subphase(
    phase, seat, trace, run_id, tab_id, url_host, elapsed_ms, timeout_ms, ok=True, error=None
):
    """P2.9: Emit a CDP submit subphase trace event."""
    if trace is None:
        return
    payload = {
        "run_id": run_id,
        "seat_id": seat,
        "phase": phase,
        "elapsed_ms": round(elapsed_ms, 1),
        "timeout_ms": round(timeout_ms * 1000, 0),
        "tab_id": tab_id,
        "url_host": url_host,
        "ok": ok,
        "error": error,
    }
    category = "seat_timeout" if not ok else "seat"
    trace(category, phase, seat + " CDP " + phase, payload)


def _run_subphase(phase, seat, operation, trace, run_id, tab_id, url_host, timeout_s=None):
    """Execute a CDP submit subphase with trace.

    Returns {"ok": True, "result": ..., "phase": ..., "elapsed_ms": ...}
    or {"ok": False, "error": ..., "phase": ..., "elapsed_ms": ...}.

    Playwright's sync API is greenlet/thread-affine. Running page operations
    in a watchdog worker thread raises "Cannot switch to a different thread".
    Keep operations on the Playwright owner thread and rely on the page/locator
    timeouts already configured by the caller.
    """
    if timeout_s is None:
        timeout_s = _CDP_SUBPHASE_TIMEOUT.get(phase, 8)

    start_phase = "cdp_" + phase + "_started"
    success_phase = "cdp_" + phase + "_succeeded"
    timeout_phase = "cdp_" + phase + "_timeout"

    t0 = time.time()
    set_bridge_phase(start_phase, seat)
    _trace_subphase(start_phase, seat, trace, run_id, tab_id, url_host, 0.0, timeout_s, ok=True)

    try:
        result = operation()
    except Exception as exc:
        elapsed_ms = (time.time() - t0) * 1000
        set_bridge_phase(timeout_phase, seat)
        _trace_subphase(timeout_phase, seat, trace, run_id, tab_id, url_host,
                       elapsed_ms, timeout_s, ok=False, error=str(exc))
        return {"ok": False, "error": str(exc), "phase": phase,
                "elapsed_ms": elapsed_ms}

    elapsed_ms = (time.time() - t0) * 1000
    set_bridge_phase(success_phase, seat)
    _trace_subphase(success_phase, seat, trace, run_id, tab_id, url_host,
                   elapsed_ms, timeout_s, ok=True)
    return {"ok": True, "result": result or {},
            "phase": phase, "elapsed_ms": elapsed_ms}


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
        try:
            browser = _connect_cdp_browser(playwright, config, cdp_connect_timeout_ms)
        except Exception as exc:
            if (
                config.get("auto_recover_unhealthy_cdp", True)
                and (status.get("process") or {}).get("profile_match") is True
                and _terminate_cdp_process(status.get("process") or {}, trace)
            ):
                wake = ensure_chrome_cdp_awake(config, open_tabs=bool(config.get("auto_wake_open_tabs", True)), trace=trace)
                status = chrome_cdp_status(config)
                if trace:
                    trace("chrome", "cdp_connect_recovered", "Chrome CDP 连接失败后已尝试重建", {
                        "wake": wake,
                        "status": status,
                        "first_error": str(exc)[:500],
                    })
                browser = _connect_cdp_browser(playwright, config, cdp_connect_timeout_ms)
            else:
                return [
                    _failed_result(seat, "cdp_connect_failed", str(exc))
                    for seat in requested
                ]
        def _set_browser_page_timeouts() -> None:
            pages = [page for context in browser.contexts for page in context.pages if not _page_is_closed(page)]
            for page in pages:
                try:
                    page.set_default_timeout(int(float(config.get("cdp_default_timeout_seconds") or 8) * 1000))
                    page.set_default_navigation_timeout(int(float(config.get("cdp_navigation_timeout_seconds") or 15) * 1000))
                except Exception:
                    pass

        def _reconnect_cdp_after_target_closed(seat: str, error: Any) -> bool:
            nonlocal browser, status, tabs
            recovery_config = dict(config)
            recovery_config["cdp_playwright_probe"] = False
            try:
                if trace:
                    trace("chrome", "cdp_target_closed_reconnect_start", "Chrome CDP target closed，尝试重连并继续剩余席位", {
                        "seat": seat,
                        "error": str(error)[:800],
                    })
                wake = ensure_chrome_cdp_awake(
                    recovery_config,
                    open_tabs=bool(config.get("auto_wake_open_tabs", True)),
                    trace=trace,
                )
                status = chrome_cdp_status(recovery_config)
                browser = _connect_cdp_browser(playwright, recovery_config, cdp_connect_timeout_ms)
                _set_browser_page_timeouts()
                tabs = _live_cdp_tabs(browser)
                if trace:
                    trace("chrome", "cdp_target_closed_reconnect_complete", "Chrome CDP 已重连，继续后续席位", {
                        "seat": seat,
                        "wake": wake,
                        "status": {k: v for k, v in status.items() if k != "quality_mode_policy"},
                        "tab_count": len(tabs),
                    })
                return True
            except Exception as reconnect_exc:
                if trace:
                    trace("chrome", "cdp_target_closed_reconnect_failed", "Chrome CDP target closed 后重连失败", {
                        "seat": seat,
                        "error": str(error)[:800],
                        "reconnect_error": str(reconnect_exc)[:800],
                    })
                return False

        _set_browser_page_timeouts()
        tabs = _live_cdp_tabs(browser)
        if trace:
            trace("chrome", "cdp_tabs_listed", "读取当前 Chrome CDP 标签页", {
                "count": len(tabs),
                "tabs": [{"title": tab.title, "url": tab.url} for tab in tabs],
            })

        # P3.6: per-seat SLA — thread-safe timeout via threading, no signal dependency
        seat_submit_timeout = int(float(config.get("seat_submit_timeout_seconds") or _SEAT_SLA["submit_stage"]))
        for index, seat in enumerate(requested, 1):
            seat_config = _seat_config(config, seat)
            seat_timeout_seconds = _seat_timeout_seconds(config, seat_config)
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
            refreshed_tabs = _live_cdp_tabs(browser)
            if refreshed_tabs:
                tabs = refreshed_tabs
                if trace:
                    trace("chrome", "cdp_tabs_refreshed", f"{seat} 提交前刷新 CDP 标签句柄", {
                        "seat": seat,
                        "count": len(tabs),
                    })
            tab = _match_tab(seat_config, tabs)
            if tab is not None and _page_is_closed(tab.page):
                tabs = _live_cdp_tabs(browser)
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
            answer_contract = dict(config.get("answer_contract") or seat_config.get("answer_contract") or {})
            prompt_with_marker = _prompt_with_answer_marker(
                prompt,
                prompt_id,
                config=config,
                item={"answer_contract": answer_contract},
            )
            prompt_with_marker, prompt_compaction = _compact_prompt_for_seat(seat, prompt_with_marker)
            if progress:
                progress(f"Chrome CDP 提交：{seat} ({index}/{total})", 0.14 + 0.22 * index / total)
            if trace:
                trace("seat", "cdp_submit_start", f"{seat} CDP 标签开始输入提示词", {
                    "seat": seat,
                    "title": tab.title,
                    "url": tab.url,
                    "prompt_chars": len(prompt_with_marker),
                    "prompt_compaction": prompt_compaction,
                })

            # P2.9: tab_id / url_host for subphase tracing
            _run_id = config.get("_run_id", "unknown")
            _tab_id = tab.url or ""
            _url_host = urlparse(tab.url).hostname or "" if tab.url else ""
            # P3.6: per-seat timeout via threading — no signal, safe in daemon threads
            seat_timeout_flag = threading.Event()
            seat_watchdog = threading.Timer(seat_submit_timeout, lambda: seat_timeout_flag.set())
            seat_watchdog.daemon = True
            seat_watchdog.start()
            seat_deadline = time.time() + seat_timeout_seconds
            submit_started_at = time.time()

            # P2.9: subphase failure tracking
            _subphase_failed = False
            _subphase_error = ""

            try:
                def _check_submit_deadline(stage: str) -> None:
                    nonlocal _subphase_error
                    elapsed = time.time() - submit_started_at
                    if seat_timeout_flag.is_set() or elapsed > seat_submit_timeout:
                        _subphase_error = f"seat_submit_deadline_exceeded:{stage}"
                        if trace:
                            trace("seat_timeout", "cdp_submit_deadline_exceeded", f"{seat} 提交阶段超过硬截止线", {
                                "seat": seat,
                                "stage": stage,
                                "elapsed_seconds": round(elapsed, 2),
                                "timeout_seconds": seat_submit_timeout,
                            })
                        raise TimeoutError(_subphase_error)

                # ── P2.9 Subphase 1: Tab Focus ──
                _sp1 = _run_subphase(
                    "tab_focus", seat,
                    lambda pg=page: (pg.bring_to_front() or {"ok": True, "method": "bring_to_front"}),
                    trace, _run_id, _tab_id, _url_host,
                    timeout_s=_CDP_SUBPHASE_TIMEOUT["tab_focus"],
                )
                if not _sp1["ok"]:
                    _subphase_failed = True
                    _subphase_error = _sp1["error"]
                    raise TimeoutError("cdp_tab_focus_timeout: " + _sp1["error"])
                _check_submit_deadline("tab_focus")

                _humanized_sleep(config, seat_config, seat, "before_submit")
                _check_submit_deadline("before_submit_sleep")
                fresh_url = str(seat_config.get("fresh_url") or "").strip()
                if seat == "xunfei":
                    if fresh_url and _seat_requires_fresh_conversation(config, seat_config, seat) and trace:
                        trace("seat", "cdp_fresh_navigation_disabled", f"{seat} 保留固定标签登录态，不执行直接 fresh 跳转", {
                            "seat": seat,
                            "fresh_url": fresh_url,
                            "url": page.url,
                            "policy": "xunfei_fixed_tab_session_reuse",
                        })
                    fresh_url = ""
                if fresh_url and _seat_requires_fresh_conversation(config, seat_config, seat):
                    try:
                        fresh_timeout_ms = int(float(config.get("fresh_navigation_timeout_seconds") or 12) * 1000)
                        page.goto(fresh_url, wait_until="domcontentloaded", timeout=fresh_timeout_ms)
                        _humanized_sleep(config, seat_config, seat, "after_reload")
                        page.wait_for_timeout(int(float(config.get("fresh_load_seconds") or 3.0) * 1000))
                        if trace:
                            trace("seat", "cdp_fresh_navigation", f"{seat} 跳转到干净会话入口", {
                                "seat": seat,
                                "fresh_url": fresh_url,
                                "url": page.url,
                                "policy": "seat_forced_fresh_chat" if seat == "grok" else "fresh_conversation_per_run",
                            })
                    except Exception as exc:
                        if trace:
                            trace("seat", "cdp_fresh_navigation_skipped", f"{seat} 新会话跳转超时，继续使用当前固定标签", {
                                "seat": seat,
                                "url": page.url,
                                "fresh_url": fresh_url,
                                "error": str(exc),
                            })
                    _check_submit_deadline("fresh_navigation")
                preflight = _clear_or_recover_page(page, config, seat_config, seat, "preflight", trace)
                _check_submit_deadline("preflight")

                # ── P2.9 Subphase 2: Input Locate ──
                _sp2 = _run_subphase(
                    "input_locate", seat,
                    lambda pg=page, pid=prompt_id: _prepare_submission_ui(pg, pid),
                    trace, _run_id, _tab_id, _url_host,
                    timeout_s=_CDP_SUBPHASE_TIMEOUT["input_locate"],
                )
                if not _sp2["ok"]:
                    _subphase_failed = True
                    _subphase_error = _sp2["error"]
                    raise TimeoutError("cdp_input_locate_timeout: " + _sp2["error"])
                prepared = _sp2["result"]
                _check_submit_deadline("input_locate")

                if prepared.get("clicked"):
                    _humanized_sleep(config, seat_config, seat, "after_click")
                    _check_submit_deadline("input_prepare_click")
                prepare_attempt = 1
                max_prepare_attempts = int(float(config.get("mode_prepare_max_attempts") or 4))
                while prepared.get("needs_followup") and prepare_attempt < max_prepare_attempts:
                    followup = _prepare_submission_ui(page, prompt_id)
                    _append_prepare_followup(prepared, followup)
                    prepare_attempt += 1
                    _check_submit_deadline(f"input_prepare_followup_{prepare_attempt}")
                    if followup.get("clicked"):
                        _humanized_sleep(config, seat_config, seat, "after_click")
                        _check_submit_deadline(f"input_prepare_followup_click_{prepare_attempt}")
                    if trace:
                        trace("seat", "cdp_submission_ui_prepare_followup", f"{seat} CDP 提交前模式第 {prepare_attempt} 次确认", {
                            "seat": seat,
                            "prepared": prepared,
                        })
                    if _quality_mode_prepare_required(seat) and _quality_mode_prepare_verified(seat, prepared):
                        break
                    if not followup.get("needs_followup"):
                        break
                if _quality_mode_prepare_required(seat) and not _quality_mode_prepare_verified(seat, prepared):
                    forced = _force_quality_mode_with_playwright(page, seat, prompt_id, trace)
                    if forced.get("attempted"):
                        _append_prepare_followup(prepared, forced)
                        _check_submit_deadline("input_prepare_playwright_force")
                composer_wait = _wait_for_provider_composer(page, seat)
                if composer_wait.get("waited") and trace:
                    trace("seat", "provider_composer_wait", f"{seat} 等待异步输入框挂载", composer_wait)
                _check_submit_deadline("provider_composer_wait")
                if (
                    _quality_mode_prepare_required(seat)
                    and not _quality_mode_prepare_verified(seat, prepared)
                    and _quality_mode_strict_required(seat)
                ):
                    code, message = _quality_mode_failure(seat)
                    submissions[seat] = _failed_result(seat, code, message)
                    if trace:
                        trace("seat", _quality_mode_trace_action(seat), _quality_mode_trace_message(seat), {
                            "seat": seat,
                            "prepared": prepared,
                            "code": code,
                            "required_quality_mode": _quality_mode_required_mode(seat),
                        })
                    continue
                if _quality_mode_prepare_required(seat) and not _quality_mode_prepare_verified(seat, prepared):
                    if trace:
                        trace("seat", "quality_mode_unverified_non_strict", f"{seat} 未确认高质量模式，按非严格策略继续提交", {
                            "seat": seat,
                            "prepared": prepared,
                            "required_quality_mode": _quality_mode_required_mode(seat),
                        })
                before = _capture_page(page, prompt_id)
                _check_submit_deadline("pre_submit_capture")

                # ── P2.9 Subphase 3: Text Inject ──
                _sp3 = _run_subphase(
                    "text_inject", seat,
                    lambda pg=page, pwm=prompt_with_marker, pid=prompt_id: _fill_prompt(pg, pwm, pid),
                    trace, _run_id, _tab_id, _url_host,
                    timeout_s=_CDP_SUBPHASE_TIMEOUT["text_inject"],
                )
                if not _sp3["ok"]:
                    _subphase_failed = True
                    _subphase_error = _sp3["error"]
                    raise TimeoutError("cdp_text_inject_timeout: " + _sp3["error"])
                fill_result = _sp3["result"]
                _check_submit_deadline("text_inject")
                if not fill_result.get("ok"):
                    submissions[seat] = _failed_result(
                        seat,
                        str(fill_result.get("error") or "prompt_write_failed"),
                        str(fill_result.get("message") or "Prompt was not verified in the visible composer after CDP write."),
                    )
                    if trace:
                        trace("seat", "cdp_prompt_write_unconfirmed", f"{seat} 未确认写入提示词，跳过提交", {
                            "seat": seat,
                            "fill": fill_result,
                        })
                    continue

                _humanized_sleep(config, seat_config, seat, "after_write")
                _check_submit_deadline("after_write_sleep")

                # ── P2.9 Subphase 4: Send Click ──
                _sp4 = _run_subphase(
                    "send_click", seat,
                    lambda pg=page, pid=prompt_id, cfg=config, sc=seat_config, st=seat: _send_prompt_for_seat(pg, pid, cfg, sc, st, trace),
                    trace, _run_id, _tab_id, _url_host,
                    timeout_s=_CDP_SUBPHASE_TIMEOUT["send_click"],
                )
                if not _sp4["ok"]:
                    _subphase_failed = True
                    _subphase_error = _sp4["error"]
                    raise TimeoutError("cdp_send_click_timeout: " + _sp4["error"])
                send_result = _sp4["result"]
                _check_submit_deadline("send_click")

                _humanized_sleep(config, seat_config, seat, "after_click")
                _check_submit_deadline("post_send_sleep")

                # ── P2.9 Subphase 5: Post-Click Ack ──
                submitted = dict(send_result)
                submitted["write"] = fill_result
                _sp5 = _run_subphase(
                    "post_click_ack", seat,
                    lambda pg=page, pid=prompt_id, sr=send_result: _confirm_or_retry_submission(pg, pid, sr),
                    trace, _run_id, _tab_id, _url_host,
                    timeout_s=_CDP_SUBPHASE_TIMEOUT["post_click_ack"],
                )
                if not _sp5["ok"]:
                    _subphase_failed = True
                    _subphase_error = _sp5["error"]
                    raise TimeoutError("cdp_post_click_ack_timeout: " + _sp5["error"])
                _check_submit_deadline("post_click_ack")
                submitted.update(_sp5["result"])
                submission_confirmed = bool(submitted.get("submitted"))
                if not submission_confirmed:
                    code = str(
                        submitted.get("error")
                        or (submitted.get("verification") or {}).get("reason")
                        or (submitted.get("retry") or {}).get("error")
                        or "submit_unconfirmed"
                    )
                    message = str(
                        submitted.get("message")
                        or (submitted.get("verification") or {}).get("message")
                        or (submitted.get("retry") or {}).get("message")
                        or "Prompt was written, but the CDP bridge could not confirm that the model page accepted it as a submitted user turn."
                    )
                    submissions[seat] = _failed_result(seat, code, message)
                    if trace:
                        trace("seat", "cdp_submit_unconfirmed", f"{seat} 未确认提交，跳过回答轮询", {
                            "seat": seat,
                            "submit": submitted,
                        })
                    continue
                submissions[seat] = {
                    "seat": seat,
                    "seat_name": SEAT_PERSONAS[seat]["name"],
                    "ok": False,
                    "page": page,
                    "prompt_id": prompt_id,
                    "answer_contract": answer_contract,
                    "submitted_at": time.time(),
                    "seat_deadline": seat_deadline,
                    "before_length": before.get("text_length") or 0,
                    "before_text": before.get("text") or "",
                    "submission_confirmed": submission_confirmed,
                    "submit_result": {"fill": fill_result, "send": send_result, "confirm": submitted, "preflight": preflight},
                    "seat_timeout_seconds": seat_timeout_seconds,
                    "timeout_seconds": seat_timeout_seconds,
                    "final_nudge_timeout_seconds": (
                        seat_config.get("final_nudge_timeout_seconds")
                        or config.get("final_nudge_timeout_seconds")
                        or seat_config.get("required_final_nudge_timeout_seconds")
                        or config.get("required_final_nudge_timeout_seconds")
                        or 90
                    ),
                }
                if trace:
                    trace("seat", "cdp_submit_complete", f"{seat} 提示词已发送", {
                        "seat": seat,
                        "seat_timeout_seconds": seat_timeout_seconds,
                        "seat_submit_timeout_seconds": seat_submit_timeout,
                        "answer_contract": answer_contract,
                        "fill": fill_result,
                        "send": send_result,
                        "confirm": submitted,
                    })
            except TimeoutError:
                if _target_closed_error(_subphase_error):
                    error_code = "cdp_target_closed"
                    error_msg = "Chrome CDP target closed during submission; this seat is recoverable with targeted recheck. Original error: " + _subphase_error
                else:
                    error_code = _subphase_error if _subphase_error else "seat_submit_timeout"
                    error_msg = "Seat submission timed out — " + _subphase_error if _subphase_error else "Seat submission timed out after " + str(seat_submit_timeout) + "s"
                submissions[seat] = _failed_result(seat, error_code, error_msg)
                if trace:
                    trace("seat", "cdp_submit_timeout", f"{seat} 提交超时 ({seat_submit_timeout}s)", {
                        "seat": seat,
                        "timeout_seconds": seat_submit_timeout,
                        "subphase_failed": _subphase_failed,
                        "subphase_error": _subphase_error,
                    })
                if error_code == "cdp_target_closed":
                    _reconnect_cdp_after_target_closed(seat, _subphase_error)
            except Exception as exc:
                error_code = "cdp_target_closed" if _target_closed_error(exc) else "cdp_submit_failed"
                submissions[seat] = _failed_result(seat, error_code, str(exc))
                if trace:
                    trace("seat", "cdp_submit_failed", f"{seat} 发送失败", {"seat": seat, "error": str(exc), "code": error_code})
                if error_code == "cdp_target_closed":
                    _reconnect_cdp_after_target_closed(seat, exc)
            finally:
                seat_watchdog.cancel()
                if seat_timeout_flag.is_set() and submissions[seat].get("ok") is False and not submissions[seat].get("error"):
                    error_code = _subphase_error if _subphase_failed else "seat_submit_timeout"
                    error_msg = "Submit subphase timeout: " + _subphase_error if _subphase_failed else "Seat submission timed out after " + str(seat_submit_timeout) + "s"
                    submissions[seat] = _failed_result(seat, error_code, error_msg)
                    if trace:
                        trace("seat", "seat_timeout", f"{seat} 超时 ({seat_submit_timeout}s)", {
                            "seat": seat,
                            "timeout_seconds": seat_submit_timeout,
                            "subphase_failed": _subphase_failed,
                            "subphase_error": _subphase_error,
                        })

        # ── P2.9 Subphase 6: Answer Poll Handoff ──
        for seat in submissions:
            item = submissions[seat]
            if item.get("page"):
                _url_host_poll = urlparse(item.get("url", "")).hostname or ""
                _trace_subphase("cdp_answer_poll_started", seat, trace, _run_id,
                              item.get("url", ""), _url_host_poll,
                              0.0, _CDP_SUBPHASE_TIMEOUT["answer_poll_handoff"], ok=True)
                set_bridge_phase("cdp_answer_poll_started", seat)

        pending = {seat for seat, item in submissions.items() if item.get("page")}
        seat_deadlines = [
            float(item.get("seat_deadline") or 0)
            for item in submissions.values()
            if item.get("page") and item.get("seat_deadline")
        ]
        poll_deadline = max([time.time() + timeout_seconds, *seat_deadlines]) if seat_deadlines else time.time() + timeout_seconds
        poll_window_seconds = max(timeout_seconds, poll_deadline - time.time())
        # P3.6: per-seat answer poll with individual deadline tracking
        if trace:
            trace("seat", "seat_answer_wait_started", "开始席位回答轮询", {
                "pending_seats": list(pending),
                "global_deadline": poll_deadline,
                "poll_window_seconds": round(poll_window_seconds, 1),
            })
        poll_round = 0
        while pending and time.time() < poll_deadline:
            poll_round += 1
            elapsed = max(0.0, poll_window_seconds - (poll_deadline - time.time()))
            if progress:
                progress(f"Chrome CDP 回答轮询：剩余 {len(pending)} 席", 0.42 + 0.30 * min(1.0, elapsed / max(poll_window_seconds, 1)))
            for seat in list(pending):
                item = submissions[seat]
                # P3.6: check per-seat deadline
                seat_dl = item.get("seat_deadline")
                if seat_dl and time.time() > seat_dl:
                    deadline_seconds = float(item.get("seat_timeout_seconds") or timeout_seconds)
                    capture, assessment, used_seat_fallback = _capture_page_with_seat_fallback(
                        item["page"], item["prompt_id"], seat, item, question
                    )
                    response_text = assessment["response_text"]
                    text = assessment["text"]
                    marker_found = bool(capture.get("marker_found"))
                    marker_in_input = bool(capture.get("marker_in_input"))
                    known_error = capture.get("known_error") or {}
                    matches_question = assessment["matches_question"]
                    json_receipt = assessment.get("json_receipt") or {}
                    if capture.get("ok") and assessment["accepted"]:
                        shortfall, response_chars, min_chars = _answer_contract_shortfall(seat, config, item, response_text)
                        if shortfall:
                            if not item.get("short_answer_nudge_sent_at"):
                                nudge = _send_cdp_short_answer_completion_nudge(
                                    item["page"],
                                    item["prompt_id"],
                                    response_chars=response_chars,
                                    min_chars=min_chars,
                                    config=config,
                                    item=item,
                                )
                                nudge_timeout = float(item.get("final_nudge_timeout_seconds") or 90.0)
                                next_deadline = time.time() + nudge_timeout
                                item["short_answer_nudge"] = nudge
                                item["short_answer_nudge_sent_at"] = time.time()
                                item["seat_deadline"] = max(float(item.get("seat_deadline") or 0), next_deadline)
                                poll_deadline = max(poll_deadline, next_deadline)
                                if trace:
                                    trace("seat", "cdp_short_answer_completion_nudge", f"{seat} 回答低于完整度合同，已追问补全", {
                                        "seat": seat,
                                        "response_chars": response_chars,
                                        "min_response_chars": min_chars,
                                        "nudge": nudge,
                                    })
                                continue
                            submissions[seat] = _short_answer_failed_result(
                                seat,
                                item,
                                response_text,
                                response_chars=response_chars,
                                min_chars=min_chars,
                            )
                            pending.remove(seat)
                            if trace:
                                trace("seat", "cdp_short_answer_rejected", f"{seat} 回答仍低于完整度合同", {
                                    "seat": seat,
                                    "response_chars": response_chars,
                                    "min_response_chars": min_chars,
                                    "marker_found": marker_found,
                                    "marker_in_input": marker_in_input,
                                    "matches_question": matches_question,
                                    "json_receipt": json_receipt,
                                    "capture_fallback": capture.get("cdp_capture_fallback") if used_seat_fallback else None,
                                })
                            continue
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
                            partial_payload = {
                                "seat": seat,
                                "response_chars": len(response_text),
                                "captured_chars": len(text),
                                "elapsed_seconds": submissions[seat]["elapsed_seconds"],
                                "marker_found": marker_found,
                                "marker_in_input": marker_in_input,
                                "matches_question": matches_question,
                                "json_receipt": json_receipt,
                                "capture_mode": assessment["mode"],
                                "capture_fallback": capture.get("cdp_capture_fallback") if used_seat_fallback else None,
                                "url": item["page"].url,
                                "_process_guard_response": response_text,
                            }
                            if config.get("emit_captured_response_in_trace"):
                                partial_payload["response"] = response_text
                            trace("seat", "cdp_partial_response_captured", f"{seat} 截止时已读取回答", partial_payload)
                    else:
                        code = "slow_response_pending"
                        message = "This seat exceeded its per-seat deadline after a confirmed submit; keep it supplementable for late answer recovery."
                        if known_error.get("code"):
                            code = str(known_error.get("code"))
                            message = str(known_error.get("message") or "The model page returned an error.")
                        elif capture.get("ok") and len(response_text) >= 240 and not matches_question:
                            code = "response_not_relevant"
                            message = "Captured text did not match the current question, so the bridge rejected it instead of treating stale page content as an answer."
                        failed = _failed_result(seat, code, message)
                        if code == "slow_response_pending":
                            failed.update({
                                "supplementable": True,
                                "url": item["page"].url,
                                "profile_dir": "Chrome CDP fixed tab",
                                "prompt_id": item.get("prompt_id"),
                                "submitted_at": item.get("submitted_at"),
                                "submission_confirmed": bool(item.get("submission_confirmed")),
                            })
                        submissions[seat] = failed
                    pending.remove(seat)
                    if trace:
                        trace("seat", "seat_timeout", f"{seat} 超过单席位截止时间", {
                            "seat": seat,
                            "seat_deadline": seat_dl,
                            "timeout_seconds": deadline_seconds,
                            "now": time.time(),
                            "poll_round": poll_round,
                            "response_chars": len(response_text),
                            "captured_chars": len(text),
                            "marker_found": marker_found,
                            "marker_in_input": marker_in_input,
                            "matches_question": matches_question,
                            "json_receipt": json_receipt,
                            "capture_fallback": capture.get("cdp_capture_fallback") if used_seat_fallback else None,
                            "known_error": known_error,
                            "result_code": (submissions[seat].get("error") or {}).get("code") if not submissions[seat].get("ok") else None,
                        })
                    continue
                capture, assessment, used_seat_fallback = _capture_page_with_seat_fallback(
                    item["page"], item["prompt_id"], seat, item, question
                )
                text = assessment["text"]
                response_text = assessment["response_text"]
                marker_found = bool(capture.get("marker_found"))
                marker_in_input = bool(capture.get("marker_in_input"))
                matches_question = assessment["matches_question"]
                known_error = capture.get("known_error") or {}
                json_receipt = assessment.get("json_receipt") or {}
                if known_error.get("code"):
                    code = str(known_error.get("code"))
                    if code == "answer_in_document_canvas" and not item.get("document_canvas_nudge_sent_at"):
                        nudge = _send_cdp_final_answer_nudge(
                            item["page"],
                            item["prompt_id"],
                            config=config,
                            item=item,
                        )
                        item["document_canvas_nudge"] = nudge
                        item["document_canvas_nudge_sent_at"] = time.time()
                        item["seat_deadline"] = min(
                            float(item.get("seat_deadline") or time.time() + 120.0),
                            time.time() + float(item.get("final_nudge_timeout_seconds") or 120.0),
                        )
                        if trace:
                            trace("seat", "cdp_document_canvas_nudge", f"{seat} 生成文档面，已追问粘贴正文", {
                                "seat": seat,
                                "known_error": known_error,
                                "nudge": nudge,
                            })
                        continue
                    message = str(known_error.get("message") or "The model page returned an error.")
                    failed = _failed_result(seat, code, message)
                    failed.update({
                        "url": item["page"].url,
                        "profile_dir": "Chrome CDP fixed tab",
                        "prompt_id": item.get("prompt_id"),
                        "submitted_at": item.get("submitted_at"),
                        "submission_confirmed": bool(item.get("submission_confirmed")),
                    })
                    submissions[seat] = failed
                    pending.remove(seat)
                    if trace:
                        trace("seat", "cdp_response_page_error", f"{seat} 页面返回错误", {
                            "seat": seat,
                            "known_error": known_error,
                            "marker_found": marker_found,
                            "marker_in_input": marker_in_input,
                        })
                    continue
                if trace:
                    trace("seat", "seat_answer_poll", f"{seat} 轮询 ({poll_round})", {
                        "seat": seat,
                        "round": poll_round,
                        "marker_found": marker_found,
                        "accepted": assessment["accepted"],
                        "response_chars": len(response_text),
                        "json_receipt": json_receipt,
                        "capture_fallback": capture.get("cdp_capture_fallback") if used_seat_fallback else None,
                        "elapsed_s": round(time.time() - float(item["submitted_at"]), 1),
                    })
                if _should_send_final_answer_nudge(seat, item, capture, assessment):
                    nudge = _send_cdp_final_answer_nudge(
                        item["page"],
                        item["prompt_id"],
                        config=config,
                        item=item,
                    )
                    item["final_answer_nudge"] = nudge
                    item["final_answer_nudge_sent_at"] = time.time()
                    item["seat_deadline"] = min(
                        float(item.get("seat_deadline") or time.time() + 90.0),
                        time.time() + float(item.get("final_nudge_timeout_seconds") or 90.0),
                    )
                    if trace:
                        trace("seat", "cdp_final_answer_nudge", f"{seat} 检测到空思考回复，已追问最终答案", {
                            "seat": seat,
                            "nudge": nudge,
                        })
                    continue
                if capture.get("ok") and assessment["accepted"]:
                    shortfall, response_chars, min_chars = _answer_contract_shortfall(seat, config, item, response_text)
                    if shortfall:
                        if not item.get("short_answer_nudge_sent_at"):
                            nudge = _send_cdp_short_answer_completion_nudge(
                                item["page"],
                                item["prompt_id"],
                                response_chars=response_chars,
                                min_chars=min_chars,
                                config=config,
                                item=item,
                            )
                            nudge_timeout = float(item.get("final_nudge_timeout_seconds") or 90.0)
                            next_deadline = time.time() + nudge_timeout
                            item["short_answer_nudge"] = nudge
                            item["short_answer_nudge_sent_at"] = time.time()
                            item["seat_deadline"] = max(float(item.get("seat_deadline") or 0), next_deadline)
                            poll_deadline = max(poll_deadline, next_deadline)
                            if trace:
                                trace("seat", "cdp_short_answer_completion_nudge", f"{seat} 回答低于完整度合同，已追问补全", {
                                    "seat": seat,
                                    "response_chars": response_chars,
                                    "min_response_chars": min_chars,
                                    "nudge": nudge,
                                })
                            continue
                        submissions[seat] = _short_answer_failed_result(
                            seat,
                            item,
                            response_text,
                            response_chars=response_chars,
                            min_chars=min_chars,
                        )
                        pending.remove(seat)
                        if trace:
                            trace("seat", "cdp_short_answer_rejected", f"{seat} 回答仍低于完整度合同", {
                                "seat": seat,
                                "response_chars": response_chars,
                                "min_response_chars": min_chars,
                                "marker_found": marker_found,
                                "marker_in_input": marker_in_input,
                                "matches_question": matches_question,
                                "json_receipt": json_receipt,
                                "capture_mode": assessment["mode"],
                                "capture_fallback": capture.get("cdp_capture_fallback") if used_seat_fallback else None,
                                "url": item["page"].url,
                            })
                        continue
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
                        captured_payload = {
                            "seat": seat,
                            "response_chars": len(response_text),
                            "captured_chars": len(text),
                            "elapsed_seconds": submissions[seat]["elapsed_seconds"],
                            "marker_found": marker_found,
                            "marker_in_input": marker_in_input,
                            "matches_question": matches_question,
                            "json_receipt": json_receipt,
                            "capture_mode": assessment["mode"],
                            "capture_fallback": capture.get("cdp_capture_fallback") if used_seat_fallback else None,
                            "url": item["page"].url,
                            "_process_guard_response": response_text,
                        }
                        if config.get("emit_captured_response_in_trace"):
                            captured_payload["response"] = response_text
                        trace("seat", "cdp_response_captured", f"{seat} 已读取回答", captured_payload)
            if pending:
                time.sleep(4)

        for seat in list(pending):
            item = submissions[seat]
            capture, assessment, used_seat_fallback = _capture_page_with_seat_fallback(
                item["page"], item["prompt_id"], seat, item, question
            )
            text = assessment["text"]
            response_text = assessment["response_text"]
            marker_found = bool(capture.get("marker_found"))
            marker_in_input = bool(capture.get("marker_in_input"))
            matches_question = assessment["matches_question"]
            known_error = capture.get("known_error") or {}
            json_receipt = assessment.get("json_receipt") or {}
            if capture.get("ok") and assessment["accepted"]:
                shortfall, response_chars, min_chars = _answer_contract_shortfall(seat, config, item, response_text)
                if shortfall:
                    submissions[seat] = _short_answer_failed_result(
                        seat,
                        item,
                        response_text,
                        response_chars=response_chars,
                        min_chars=min_chars,
                    )
                    if trace:
                        trace("seat", "cdp_short_answer_rejected", f"{seat} 回答低于完整度合同，未进入正式结果", {
                            "seat": seat,
                            "response_chars": response_chars,
                            "min_response_chars": min_chars,
                            "marker_found": marker_found,
                            "marker_in_input": marker_in_input,
                            "matches_question": matches_question,
                            "json_receipt": json_receipt,
                            "capture_mode": assessment["mode"],
                            "capture_fallback": capture.get("cdp_capture_fallback") if used_seat_fallback else None,
                            "url": item["page"].url,
                        })
                    continue
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
                    partial_payload = {
                        "seat": seat,
                        "response_chars": len(response_text),
                        "captured_chars": len(text),
                        "marker_found": marker_found,
                        "marker_in_input": marker_in_input,
                        "matches_question": matches_question,
                        "json_receipt": json_receipt,
                        "capture_mode": assessment["mode"],
                        "url": item["page"].url,
                        "elapsed_seconds": submissions[seat]["elapsed_seconds"],
                        "_process_guard_response": response_text,
                    }
                    if config.get("emit_captured_response_in_trace"):
                        partial_payload["response"] = response_text
                    trace("seat", "cdp_partial_response_captured", f"{seat} 超时前读取到部分回答", partial_payload)
            else:
                code = "slow_response_pending"
                message = "This seat was still slow after the collection window. It can be rechecked with the supplement action instead of being treated as a final model failure."
                if known_error.get("code"):
                    code = str(known_error.get("code"))
                    message = str(known_error.get("message") or "The model page returned an error.")
                elif capture.get("ok") and len(response_text) >= 240 and not matches_question:
                    code = "response_not_relevant"
                    message = "Captured text did not match the current question, so the bridge rejected it instead of treating stale page content as an answer."
                failed = _failed_result(seat, code, message)
                if code == "slow_response_pending":
                    failed.update({
                        "supplementable": True,
                        "url": item["page"].url,
                        "profile_dir": "Chrome CDP fixed tab",
                        "prompt_id": item.get("prompt_id"),
                        "submitted_at": item.get("submitted_at"),
                        "submission_confirmed": bool(item.get("submission_confirmed")),
                    })
                submissions[seat] = failed
                if trace:
                    trace("seat", "cdp_response_rejected" if code == "response_not_relevant" else "cdp_response_timeout", f"{seat} 未读到可用回答", {
                        "seat": seat,
                        "code": code,
                        "response_chars": len(response_text),
                        "captured_chars": len(text),
                        "marker_found": marker_found,
                        "marker_in_input": marker_in_input,
                        "matches_question": matches_question,
                        "json_receipt": json_receipt,
                        "known_error": known_error,
                    })

    if progress:
        progress("Chrome CDP 收集完成，进入评分", 0.74)
    return list(submissions.values())


def _json_receipt_nudge_prompt() -> str:
    return (
        "上一轮没有产出可入库的结构化投注单。现在必须只输出一个 JSON 对象，"
        "不要 Markdown 代码块、不要解释、不要开始/结束标记、不要卡片标题。"
        "JSON 顶层必须包含：model_account、seat_id、one_sentence_strategy、forecasts、investments、loan_decision、risk_notes、self_audit。"
        "forecasts 必须覆盖原题赛事清单里的每一个 match_id。"
        "investments 也必须覆盖每一个 match_id；即使不下注，也要写一条 action 为 no_bet 的记录并说明理由。"
        "不要替换或改写 match_id，尤其必须保留原题中的葡萄牙/哥伦比亚 match_id。"
        "self_audit.covered_match_ids 必须列出全部已覆盖 match_id，missing_match_ids 必须是空数组，ready_for_frontend_ingest 必须是 true。"
        "如果某场盘口不适合下注，仍要在 investments 里写 action:no_bet，而不是遗漏该场。"
    )


def _line_receipt_nudge_prompt(prompt_id: str) -> str:
    return (
        "上一轮没有产出可入库的 PRED_INVEST_RECEIPT。现在不要解释、不要复述题目、不要 Markdown，"
        "必须重新输出完整投注单并覆盖原题全部 match_id。最终回答必须包裹在同一组标记内；"
        "标记内第一行必须是 PRED_INVEST_RECEIPT，包含 model_account、seat_id、STRATEGY、"
        "每场一条 F|、每场一条 B|，最后一条 AUDIT|...|true。"
        "不要输出占位字段，不要遗漏 no_bet 场次。"
        f"开始标记内容是 AIJUDGE_ANSWER_START:{prompt_id}；"
        f"结束标记内容是 AIJUDGE_ANSWER_END:{prompt_id}。"
    )


def _cdp_final_answer_nudge_prompt(
    prompt_id: str,
    *,
    config: dict[str, Any] | None = None,
    item: dict[str, Any] | None = None,
) -> str:
    if _answer_contract_requires_compact_line(config, item):
        return _line_receipt_nudge_prompt(prompt_id)
    if _answer_contract_requires_json(config, item):
        return _json_receipt_nudge_prompt()
    return (
        "上一轮只显示了思考、占位符或空回复。现在请不要继续思考，不要创建文档/画布/卡片，"
        "如果上一轮生成了文档卡片或法律意见文档，请把该文档全文直接粘贴回当前聊天窗口，"
        "不要只给卡片标题。下一条回复必须先输出开始标记，然后直接写实际正文，最后输出结束标记；"
        "禁止输出“最终答案正文”“完整修订答案正文”“你的最终答案”等占位词。"
        "注意：为避免系统把本条追问误读为答案，我不会在追问里直接写出完整标记。"
        "你必须自行重建并输出两行半角方括号标记："
        f"开始标记内容是 AIJUDGE_ANSWER_START:{prompt_id}；"
        f"结束标记内容是 AIJUDGE_ANSWER_END:{prompt_id}。"
    )


def _send_cdp_final_answer_nudge(
    page: Any,
    prompt_id: str,
    *,
    config: dict[str, Any] | None = None,
    item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nudge_prompt = _cdp_final_answer_nudge_prompt(prompt_id, config=config, item=item)
    written = _fill_prompt(page, nudge_prompt, prompt_id)
    if not written.get("ok"):
        return {"ok": False, "stage": "write", "write": written}
    try:
        page.wait_for_timeout(800)
    except Exception:
        pass
    clicked = _send_prompt(page, prompt_id)
    if not clicked.get("ok"):
        return {"ok": False, "stage": "send", "write": written, "send": clicked}
    try:
        page.wait_for_timeout(900)
    except Exception:
        pass
    confirmed = _confirm_or_retry_submission(page, prompt_id, clicked)
    return {
        "ok": bool(confirmed.get("submitted") or confirmed.get("ok")),
        "stage": "confirm",
        "write": written,
        "send": clicked,
        "confirm": confirmed,
    }


def _cdp_short_answer_completion_nudge_prompt(
    prompt_id: str,
    *,
    response_chars: int,
    min_chars: int,
    config: dict[str, Any] | None = None,
    item: dict[str, Any] | None = None,
) -> str:
    if _answer_contract_requires_compact_line(config, item):
        return _line_receipt_nudge_prompt(prompt_id)
    if _answer_contract_requires_json(config, item):
        return _json_receipt_nudge_prompt()
    return (
        f"上一轮最终答案只有 {response_chars} 字，不满足本轮 AI Judge 完整答案合同的最低 {min_chars} 字要求。"
        "请不要解释系统限制，不要只给结论。请严格围绕本轮用户任务输出完整修订答案，"
        "不要切换到金融、法律、狼人杀、赛事以外的历史上下文。"
        "如果本轮任务要求标准 JSON 或结构化回执，下一条回复必须只输出符合本轮 schema 的 JSON 对象；"
        "如果本轮任务要求自然语言报告，则至少补齐：明确结论、关键依据、具体方案、风险、触发条件、下一步。"
        "下一条回复必须先输出开始标记，然后直接写不少于最低字数要求的实际正文，最后输出结束标记；"
        "禁止输出“完整修订答案正文”“最终答案正文”“你的最终答案”等占位词。"
        "注意：为避免系统把本条追问误读为答案，我不会在追问里直接写出完整标记。"
        "你必须自行重建并输出两行半角方括号标记："
        f"开始标记内容是 AIJUDGE_ANSWER_START:{prompt_id}；"
        f"结束标记内容是 AIJUDGE_ANSWER_END:{prompt_id}。"
    )


def _send_cdp_short_answer_completion_nudge(
    page: Any,
    prompt_id: str,
    *,
    response_chars: int,
    min_chars: int,
    config: dict[str, Any] | None = None,
    item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nudge_prompt = _cdp_short_answer_completion_nudge_prompt(
        prompt_id,
        response_chars=response_chars,
        min_chars=min_chars,
        config=config,
        item=item,
    )
    written = _fill_prompt(page, nudge_prompt, prompt_id)
    if not written.get("ok"):
        return {"ok": False, "stage": "write", "write": written}
    try:
        page.wait_for_timeout(800)
    except Exception:
        pass
    clicked = _send_prompt(page, prompt_id)
    if not clicked.get("ok"):
        return {"ok": False, "stage": "send", "write": written, "send": clicked}
    try:
        page.wait_for_timeout(900)
    except Exception:
        pass
    confirmed = _confirm_or_retry_submission(page, prompt_id, clicked)
    return {
        "ok": bool(confirmed.get("submitted") or confirmed.get("ok")),
        "stage": "confirm",
        "write": written,
        "send": clicked,
        "confirm": confirmed,
    }


def _short_answer_failed_result(
    seat: str,
    item: dict[str, Any],
    response_text: str,
    *,
    response_chars: int,
    min_chars: int,
) -> dict[str, Any]:
    failed = _failed_result(
        seat,
        "response_below_minimum",
        f"Captured answer has {response_chars} chars, below the complete-answer contract ({min_chars} chars).",
    )
    failed.update({
        "supplementable": True,
        "url": getattr(item.get("page"), "url", "") or item.get("url"),
        "profile_dir": "Chrome CDP fixed tab",
        "prompt_id": item.get("prompt_id"),
        "submitted_at": item.get("submitted_at"),
        "submission_confirmed": bool(item.get("submission_confirmed")),
        "response": response_text,
        "response_chars": response_chars,
        "min_response_chars": min_chars,
    })
    return failed


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


def _click_last_visible(page: Any, selectors: list[str], *, timeout_ms: int = 2500) -> dict[str, Any]:
    last_error = ""
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = locator.count()
            for index in range(count - 1, -1, -1):
                candidate = locator.nth(index)
                if candidate.is_visible(timeout=700):
                    label = ""
                    try:
                        label = candidate.inner_text(timeout=500)
                    except Exception:
                        try:
                            label = candidate.get_attribute("aria-label") or ""
                        except Exception:
                            label = ""
                    candidate.click(timeout=timeout_ms)
                    return {"ok": True, "selector": selector, "index": index, "label": label}
        except Exception as exc:
            last_error = str(exc)
    return {"ok": False, "error": last_error or "visible_click_target_not_found"}


def _force_quality_mode_with_playwright(
    page: Any,
    seat: str,
    prompt_id: str,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Use real Playwright clicks for provider menus that ignore DOM click()."""
    seat = seat.lower()
    result: dict[str, Any] = {"ok": False, "attempted": False, "seat": seat}
    try:
        if seat == "wenxin":
            result["attempted"] = True
            open_result = _click_last_visible(
                page,
                [
                    "._select-button_1gcxw_1",
                    "[class*='select-button']",
                    "div:has-text('自动模式')",
                ],
            )
            page.wait_for_timeout(900)
            deep_result = _click_last_visible(
                page,
                [
                    "._list-item_1gcxw_89:has-text('深度思考')",
                    "[class*='list-item']:has-text('深度思考')",
                    "div:has-text('深度思考')",
                    "span:has-text('深度思考')",
                ],
            )
            page.wait_for_timeout(900)
            prepared = _prepare_submission_ui(page, prompt_id)
            result.update(prepared)
            result["attempted"] = True
            result["playwright_force"] = {"open": open_result, "select": deep_result}
            deep_visible = bool(page.evaluate(
                """() => Array.from(document.querySelectorAll("[class*='select-button'],[class*='button-content'],[class*='label'],button,[role='button']"))
                  .some((el) => {
                    const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
                    return /深度思考|深度思维|思考模式|Thinking|Think/i.test(text)
                      && !/自动模式|快速|普通|Fast|Auto|None|No Thinking/i.test(text);
                  })"""
            ))
            if deep_visible:
                result["clicked_names"] = [
                    name
                    for name in result.get("clicked_names") or []
                    if not str(name).startswith("wenxin_deep_thinking_verified:")
                ] + ["wenxin_deep_thinking_verified:yes"]
                result["needs_followup"] = False
                result["playwright_verified"] = True
                result["playwright_verified_by"] = "visible_deep_thinking_control"
        elif seat == "gemini":
            result["attempted"] = True
            open_result = _click_last_visible(
                page,
                [
                    "button[aria-label*='模式选择器']",
                    "button:has-text('Pro')",
                    "button:has-text('Gemini')",
                ],
            )
            page.wait_for_timeout(900)
            pro_result = _click_last_visible(
                page,
                [
                    "gem-menu-item:has-text('3.1 Pro')",
                    "[role='menuitem']:has-text('3.1 Pro')",
                    "gem-menu-item:has-text('Pro')",
                ],
            )
            page.wait_for_timeout(900)
            open_again = _click_last_visible(
                page,
                [
                    "button[aria-label*='模式选择器']",
                    "button:has-text('Pro')",
                ],
            )
            page.wait_for_timeout(900)
            thinking_menu = _click_last_visible(
                page,
                [
                    "gem-menu-item:has-text('思考等级')",
                    "[role='menuitem']:has-text('思考等级')",
                    "gem-menu-item:has-text('Thinking')",
                ],
            )
            page.wait_for_timeout(900)
            expanded_result = _click_last_visible(
                page,
                [
                    "gem-menu-item:has-text('扩展')",
                    "[role='menuitem']:has-text('扩展')",
                    "gem-menu-item:has-text('Extended')",
                ],
            )
            page.wait_for_timeout(900)
            prepared = _prepare_submission_ui(page, prompt_id)
            result.update(prepared)
            result["attempted"] = True

            def _label_matches(item: dict[str, Any], pattern: str, negative: str = "") -> bool:
                label = str(item.get("label") or "")
                if not item.get("ok") or not label:
                    return False
                if not re.search(pattern, label, re.IGNORECASE):
                    return False
                return not bool(negative and re.search(negative, label, re.IGNORECASE))

            pro_verified_by_click = bool(pro_result.get("ok")) or _label_matches(
                open_again,
                r"\bpro\b|高级版",
                r"flash|lite|preview|image|veo|imagen",
            )
            expanded_verified_by_click = bool(expanded_result.get("ok")) or _label_matches(
                expanded_result,
                r"扩展|extended|expanded|deep think|复杂问题",
                r"标准|standard|auto|默认|自动",
            )
            if pro_verified_by_click and expanded_verified_by_click:
                result["clicked_names"] = [
                    name
                    for name in result.get("clicked_names") or []
                    if not str(name).startswith("gemini_pro_verified:")
                    and not str(name).startswith("gemini_expanded_verified:")
                ] + ["gemini_pro_verified:yes", "gemini_expanded_verified:yes"]
                result["needs_followup"] = False
                result["playwright_verified"] = True
                result["playwright_verified_by"] = "pro_control_and_expanded_click"
            result["playwright_force"] = {
                "open": open_result,
                "pro": pro_result,
                "open_again": open_again,
                "thinking_menu": thinking_menu,
                "expanded": expanded_result,
            }
        if trace and result.get("attempted"):
            trace("seat", "quality_mode_playwright_force", f"{seat} 使用 Playwright 真实点击确认高质量模式", {
                "seat": seat,
                "ok": _quality_mode_prepare_verified(seat, result),
                "clicked_names": result.get("clicked_names"),
                "playwright_force": result.get("playwright_force"),
            })
    except Exception as exc:
        result.update({"ok": False, "attempted": True, "error": str(exc)})
        if trace:
            trace("seat", "quality_mode_playwright_force_failed", f"{seat} Playwright 模式确认失败", {
                "seat": seat,
                "error": str(exc),
            })
    return result


def _evaluate_json(page: Any, js: str, fallback_error: str) -> dict[str, Any]:
    try:
        raw = page.evaluate(js)
    except Exception as exc:
        return {"ok": False, "error": fallback_error, "message": str(exc)}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            return {"ok": False, "error": fallback_error, "raw": raw}
        return parsed if isinstance(parsed, dict) else {"ok": False, "error": fallback_error, "raw": parsed}
    return raw if isinstance(raw, dict) else {"ok": False, "error": fallback_error, "raw": raw}


def _prompt_presence(page: Any, prompt_id: str) -> dict[str, Any]:
    return _evaluate_json(page, _build_prompt_presence_js(prompt_id), "prompt_presence_failed")


def _xunfei_prompt_state(page: Any) -> dict[str, Any]:
    return _evaluate_json(
        page,
        """() => {
          const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const usableInput = el => {
            if (!visible(el)) return false;
            const rect = el.getBoundingClientRect();
            return rect.width >= 20 && rect.height >= 8;
          };
          const inputs = Array.from(document.querySelectorAll("#askwindow-textarea,textarea,input,[contenteditable='true'],[contenteditable='plaintext-only'],[role='textbox']"))
            .filter(usableInput);
          const input = inputs[inputs.length - 1] || null;
          const sends = Array.from(document.querySelectorAll("#ask_window_send_btn,[id='ask_window_send_btn'],[class*='AskWindow_send'],[class*='send__'],button,[role='button']"))
            .filter(visible)
            .map(btn => ({
              text: (btn.innerText || btn.textContent || "").replace(/\\s+/g, " ").trim(),
              class_name: String(btn.className || ""),
              id: btn.id || "",
              disabled: !!btn.disabled || btn.getAttribute("aria-disabled") === "true",
              pointer: getComputedStyle(btn).pointerEvents
            }))
            .slice(-12);
          const bodyText = document.body?.innerText || document.body?.textContent || "";
          return {
            ok: inputs.length > 0,
            url: location.href,
            title: document.title,
            input_count: inputs.length,
            input_chars: input ? String(input.value || input.innerText || input.textContent || "").length : 0,
            placeholder: input ? String(input.getAttribute?.("placeholder") || "") : "",
            reasoning_mode_visible: bodyText.includes("推理模式"),
            route_guard_installed: !!window.__AIJUDGE_XUNFEI_ROUTE_GUARD__,
            route_guard_blocked_count: Array.isArray(window.__AIJUDGE_XUNFEI_ROUTE_GUARD_BLOCKED__) ? window.__AIJUDGE_XUNFEI_ROUTE_GUARD_BLOCKED__.length : 0,
            route_guard_blocked: Array.isArray(window.__AIJUDGE_XUNFEI_ROUTE_GUARD_BLOCKED__) ? window.__AIJUDGE_XUNFEI_ROUTE_GUARD_BLOCKED__.slice(-5) : [],
            submit_ready: sends.some(btn => /ask_window_send_btn|AskWindow_send|send__/i.test(btn.id + " " + btn.class_name) && !btn.disabled && btn.pointer !== "none"),
            buttons: sends
          };
        }""",
        "xunfei_state_probe_failed",
    )


def _ensure_xunfei_desk_ready(
    page: Any,
    *,
    force_reload: bool = False,
    wait_ms: int = 2200,
    stability_ms: int = 7200,
) -> dict[str, Any]:
    """Keep SparkDesk on the logged-in desk route before touching its React composer.

    SparkDesk can briefly render /desk and then bounce back to the marketing
    homepage. Treat the desk as ready only after it survives a short stability
    window with a visible composer.
    """
    steps: list[dict[str, Any]] = []
    bounce_count = 0
    try:
        current_url = str(getattr(page, "url", "") or "")
        guard = _install_xunfei_desk_guard(page)
        steps.append({"action": "install_route_guard", "state": guard})
        if force_reload or "xinghuo.xfyun.cn/desk" not in current_url:
            page.goto("https://xinghuo.xfyun.cn/desk", wait_until="domcontentloaded", timeout=15000)
            steps.append({"action": "goto_desk", "from_url": current_url, "to_url": str(getattr(page, "url", "") or "")})
            guard = _install_xunfei_desk_guard(page)
            steps.append({"action": "reinstall_route_guard", "state": guard})
        page.wait_for_timeout(wait_ms)
        for attempt in range(1, 4):
            try:
                page.wait_for_selector("#askwindow-textarea, textarea, [role='textbox']", state="visible", timeout=5000)
            except Exception as exc:
                steps.append({"action": "wait_selector", "attempt": attempt, "error": str(exc)[:180]})
            state = _xunfei_prompt_state(page)
            steps.append({"action": "probe", "attempt": attempt, "state": state})
            state_url = str(state.get("url") or getattr(page, "url", "") or "")
            if state.get("ok") and "xinghuo.xfyun.cn/desk" in state_url:
                steps.append({"action": "stability_wait", "attempt": attempt, "ms": stability_ms, "url": state_url})
                page.wait_for_timeout(stability_ms)
                stable_state = _xunfei_prompt_state(page)
                steps.append({"action": "stability_probe", "attempt": attempt, "state": stable_state})
                stable_url = str(stable_state.get("url") or getattr(page, "url", "") or "")
                if stable_state.get("ok") and "xinghuo.xfyun.cn/desk" in stable_url:
                    stable_state["stable_ms"] = stability_ms
                    stable_state["ready_steps"] = steps
                    _record_xunfei_desk_event({
                        "event": "desk_ready_stable",
                        "attempt": attempt,
                        "url": stable_url,
                        "input_count": stable_state.get("input_count"),
                        "reasoning_mode_visible": stable_state.get("reasoning_mode_visible"),
                    })
                    return stable_state
                bounce_count += 1
                steps.append({
                    "action": "desk_bounce_detected",
                    "attempt": attempt,
                    "before_url": state_url,
                    "after_url": stable_url,
                    "stable_state": stable_state,
                })
                _record_xunfei_desk_event({
                    "event": "desk_bounce_detected",
                    "attempt": attempt,
                    "before_url": state_url,
                    "after_url": stable_url,
                    "stable_ms": stability_ms,
                    "input_count_before": state.get("input_count"),
                    "input_count_after": stable_state.get("input_count"),
                })
            if "xinghuo.xfyun.cn/desk" not in str(state.get("url") or getattr(page, "url", "") or ""):
                guard = _install_xunfei_desk_guard(page)
                steps.append({"action": "regoto_route_guard", "attempt": attempt, "state": guard})
                page.goto("https://xinghuo.xfyun.cn/desk", wait_until="domcontentloaded", timeout=15000)
                steps.append({"action": "regoto_desk", "attempt": attempt, "url": str(getattr(page, "url", "") or "")})
                guard = _install_xunfei_desk_guard(page)
                steps.append({"action": "post_regoto_route_guard", "attempt": attempt, "state": guard})
            page.wait_for_timeout(1600)
        state = _xunfei_prompt_state(page)
        if bounce_count:
            state["ok"] = False
            state["error"] = "xunfei_desk_bounced_to_home"
            state["message"] = "SparkDesk /desk rendered briefly but bounced back before the stability window completed."
            state["bounce_count"] = bounce_count
        state["ready_steps"] = steps
        _record_xunfei_desk_event({
            "event": state.get("error") or "desk_ready_failed",
            "url": state.get("url") or str(getattr(page, "url", "") or ""),
            "bounce_count": bounce_count,
            "input_count": state.get("input_count"),
            "steps": steps[-8:],
        })
        return state
    except Exception as exc:
        failure = {"ok": False, "error": "xunfei_desk_ready_failed", "message": str(exc), "steps": steps, "url": str(getattr(page, "url", "") or "")}
        _record_xunfei_desk_event({"event": "desk_ready_exception", **failure})
        return failure


def _clipboard_paste_prompt(page: Any, prompt: str, prompt_id: str, last_error: str = "") -> dict[str, Any]:
    """Last-resort composer write path for sites that ignore DOM/Playwright input events."""
    selectors = [
        "[placeholder*='有问必答']",
        "[placeholder*='可以问']",
        "[placeholder*='提问']",
        "[placeholder*='消息']",
        "[aria-label*='提问']",
        "[aria-label*='消息']",
        "[data-placeholder*='输入']",
        "[data-placeholder*='提问']",
        "[data-placeholder*='消息']",
        ".tiptap.ProseMirror[contenteditable='true']",
        "[class*='rich-text-editor'][contenteditable='true']",
        ".chat-input-editor[contenteditable='true']",
        "[class*='input'][contenteditable='true']",
        "[class*='editor'][contenteditable='true']",
        "[class*='textarea'] textarea",
        "[class*='input'] textarea",
        "[class*='editor'] textarea",
        "textarea[data-testid='prompt-textarea']",
        "div[contenteditable='true'][role='textbox']",
        "div[role='textbox'][contenteditable='true']",
        ".ProseMirror[contenteditable='true']",
        "[class*='ProseMirror'][contenteditable='true']",
        "[class*='ql-editor'][contenteditable='true']",
        "[class*='cm-content'][contenteditable='true']",
        "[class*='input'][contenteditable='true']",
        "[class*='editor'][contenteditable='true']",
        "[contenteditable='plaintext-only']",
        "[aria-label*='输入']",
        "[placeholder*='输入']",
        "div[contenteditable='true']",
        "textarea",
        "[role='textbox']",
    ]
    try:
        proc = subprocess.run(
            ["pbcopy"],
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=6,
            check=False,
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": "clipboard_write_failed",
                "message": (proc.stderr or proc.stdout or "pbcopy failed").strip(),
                "last_error": last_error[:160],
            }
        for selector in selectors:
            locator = page.locator(selector)
            count = locator.count()
            for idx in range(count - 1, -1, -1):
                candidate = locator.nth(idx)
                try:
                    if not candidate.is_visible(timeout=600):
                        continue
                    candidate.click(timeout=2000)
                    page.keyboard.press("Meta+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.press("Meta+V")
                    page.wait_for_timeout(500)
                    presence = _prompt_presence(page, prompt_id)
                    if presence.get("prompt_written"):
                        return {
                            "ok": True,
                            "method": "system_clipboard_paste",
                            "selector": selector,
                            "presence": presence,
                        }
                except Exception as exc:
                    last_error = str(exc)
                    continue
        return {
            "ok": False,
            "error": "clipboard_paste_unconfirmed",
            "message": last_error or "Clipboard paste did not expose the AI Judge marker in the composer.",
            "presence": _prompt_presence(page, prompt_id),
        }
    except Exception as exc:
        return {"ok": False, "error": "clipboard_paste_failed", "message": str(exc), "last_error": last_error[:160]}


def _fill_xunfei_prompt_with_keyboard_once(page: Any, prompt: str, prompt_id: str) -> dict[str, Any]:
    """Write through Xunfei SparkDesk's React-controlled textarea and enable its send affordance."""
    ready_state = _ensure_xunfei_desk_ready(page)
    if not ready_state.get("ok"):
        return {
            "ok": False,
            "error": "xunfei_desk_input_not_ready",
            "message": "SparkDesk desk route did not expose a usable composer before write.",
            "state": ready_state,
        }
    write_state = _evaluate_json(
        page,
        f"""() => {{
          const prompt = {json.dumps(prompt, ensure_ascii=False)};
          const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const usableInput = el => {{
            if (!visible(el)) return false;
            const rect = el.getBoundingClientRect();
            return rect.width >= 20 && rect.height >= 8;
          }};
          const inputs = Array.from(document.querySelectorAll("#askwindow-textarea,textarea,input,[contenteditable='true'],[contenteditable='plaintext-only'],[role='textbox']"))
            .filter(usableInput);
          const input = inputs[inputs.length - 1] || null;
          if (!input) return JSON.stringify({{ok:false, error:"xunfei_input_not_found", url:location.href, title:document.title}});
          const before = String(input.value || input.innerText || input.textContent || "");
          input.focus();
          try {{ input.click(); }} catch (_) {{}}
          const proto = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype
            : input instanceof HTMLInputElement ? HTMLInputElement.prototype
            : Object.getPrototypeOf(input);
          const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set
            || Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")?.set;
          try {{ input._valueTracker?.setValue(before === prompt ? "" : before); }} catch (_) {{}}
          if ("value" in input) {{
            if (setter) setter.call(input, "");
            else input.value = "";
            input.dispatchEvent(new Event("input", {{ bubbles: true, cancelable: true }}));
            try {{ input.setSelectionRange(0, 0); }} catch (_) {{}}
          }} else {{
            input.textContent = "";
          }}
          let inserted = false;
          try {{ inserted = document.execCommand("insertText", false, prompt); }} catch (_) {{ inserted = false; }}
          let mid = String(input.value || input.innerText || input.textContent || "");
          if (!mid.includes("{prompt_id}")) {{
            try {{ input._valueTracker?.setValue(mid === prompt ? "" : mid); }} catch (_) {{}}
            if ("value" in input) {{
              if (setter) setter.call(input, prompt);
              else input.value = prompt;
            }} else {{
              input.textContent = prompt;
            }}
            input.dispatchEvent(new Event("input", {{ bubbles: true, cancelable: true }}));
            input.dispatchEvent(new Event("change", {{ bubbles: true, cancelable: true }}));
          }}
          input.focus();
          const after = String(input.value || input.innerText || input.textContent || "");
          return JSON.stringify({{
            ok: after.includes("{prompt_id}"),
            method: inserted ? "exec_command_insert_text" : "direct_value_tracker_event",
            url: location.href,
            title: document.title,
            before_length: before.length,
            value_length: after.length,
            marker_present: after.includes("{prompt_id}"),
            exec_command_inserted: inserted,
            active: document.activeElement === input
          }});
        }}""",
        "xunfei_direct_write_failed",
    )
    page.wait_for_timeout(1200)
    presence = _prompt_presence(page, prompt_id)
    state = _xunfei_prompt_state(page)
    if presence.get("prompt_written"):
        return {
            "ok": True,
            "prompt_written": True,
            "method": "xunfei.direct_value_tracker_event",
            "presence": presence,
            "write_state": write_state,
            "state": state,
            "ready_state": ready_state,
        }
    return {
        "ok": False,
        "error": "xunfei_react_write_failed",
        "message": "marker_not_found_after_xunfei_direct_value_tracker_event",
        "state": {
            "presence": presence,
            "write_state": write_state,
            "current": state,
            "ready_state": ready_state,
        },
    }


def _fill_xunfei_prompt_with_keyboard(page: Any, prompt: str, prompt_id: str) -> dict[str, Any]:
    """Retry Xunfei writes across SparkDesk SPA navigation churn."""
    last_result: dict[str, Any] = {}
    for attempt in range(1, 4):
        result = _fill_xunfei_prompt_with_keyboard_once(page, prompt, prompt_id)
        if result.get("ok") or result.get("prompt_written"):
            result["xunfei_keyboard_attempt"] = attempt
            return result
        last_result = result
        message = str(result.get("message") or result.get("error") or "")
        retryable = re.search(r"Execution context was destroyed|navigation|Target closed|marker_not_found|input_not_ready|desk route", message, flags=re.I)
        if not retryable:
            break
        try:
            _ensure_xunfei_desk_ready(page, force_reload=True, wait_ms=2600)
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        page.wait_for_timeout(1600)
    last_result["xunfei_keyboard_attempts"] = 3
    return last_result


def _fill_prompt(page: Any, prompt: str, prompt_id: str) -> dict[str, Any]:
    host = urlparse(getattr(page, "url", "") or "").hostname or ""
    if host.endswith("xinghuo.xfyun.cn"):
        xunfei_written = _fill_xunfei_prompt_with_keyboard(page, prompt, prompt_id)
        if xunfei_written.get("ok") or xunfei_written.get("prompt_written"):
            xunfei_written["ok"] = True
            return xunfei_written
        page.wait_for_timeout(1200)
        xunfei_retry = _fill_xunfei_prompt_with_keyboard(page, prompt, prompt_id)
        if xunfei_retry.get("ok") or xunfei_retry.get("prompt_written"):
            xunfei_retry["ok"] = True
            xunfei_retry["retry_after_initial_keyboard_write"] = True
            xunfei_retry["initial_keyboard_write"] = xunfei_written
            return xunfei_retry
        xunfei_written["retry_after_initial_keyboard_write"] = xunfei_retry
        return xunfei_written

    written = _evaluate_json(page, _build_write_prompt_js(prompt, prompt_id), "dom_prompt_write_failed")
    if written.get("ok") or written.get("prompt_written"):
        written["ok"] = True
        return written
    xunfei_activation = written.get("xunfei_activation") if isinstance(written, dict) else None
    if isinstance(xunfei_activation, dict) and xunfei_activation.get("clicked"):
        try:
            page.wait_for_timeout(1600)
            retry_written = _evaluate_json(page, _build_write_prompt_js(prompt, prompt_id), "dom_prompt_write_failed_after_xunfei_activation")
        except Exception as exc:
            retry_written = {"ok": False, "error": "xunfei_write_retry_failed", "message": str(exc)}
        if retry_written.get("ok") or retry_written.get("prompt_written"):
            retry_written["ok"] = True
            retry_written["retry_after_xunfei_activation"] = True
            retry_written["initial_write"] = written
            return retry_written
        written["retry_after_xunfei_activation"] = retry_written

    selectors = [
        "[placeholder*='有问必答']",
        "[placeholder*='可以问']",
        "[placeholder*='提问']",
        "[placeholder*='消息']",
        "[aria-label*='提问']",
        "[aria-label*='消息']",
        "[data-placeholder*='输入']",
        "[data-placeholder*='提问']",
        "[data-placeholder*='消息']",
        ".tiptap.ProseMirror[contenteditable='true']",
        "[class*='rich-text-editor'][contenteditable='true']",
        ".chat-input-editor[contenteditable='true']",
        "[class*='input'][contenteditable='true']",
        "[class*='editor'][contenteditable='true']",
        "[class*='textarea'] textarea",
        "[class*='input'] textarea",
        "[class*='editor'] textarea",
        "textarea[data-testid='prompt-textarea']",
        "div[contenteditable='true'][role='textbox']",
        "div[role='textbox'][contenteditable='true']",
        ".ProseMirror[contenteditable='true']",
        "[class*='ProseMirror'][contenteditable='true']",
        "[class*='ql-editor'][contenteditable='true']",
        "[class*='cm-content'][contenteditable='true']",
        "[contenteditable='plaintext-only']",
        "[aria-label*='输入']",
        "[placeholder*='输入']",
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
                    candidate.fill(prompt, timeout=8000)
                    presence = _prompt_presence(page, prompt_id)
                    if presence.get("prompt_written"):
                        return {
                            "ok": True,
                            "method": "locator.fill",
                            "selector": selector,
                            "dom_write": written,
                            "presence": presence,
                        }
                except Exception as exc:
                    last_error = str(exc)
                try:
                    page.keyboard.press("Meta+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.insert_text(prompt)
                    presence = _prompt_presence(page, prompt_id)
                    if presence.get("prompt_written"):
                        return {
                            "ok": True,
                            "method": "browser_input.insert_text",
                            "selector": selector,
                            "dom_write": written,
                            "presence": presence,
                        }
                    last_error = "marker_not_found_after_insert_text"
                except Exception as exc:
                    last_error = str(exc)
            except Exception as exc:
                last_error = str(exc)
    dom_fallback = page.evaluate(
        """({prompt, marker, lastError}) => {
          const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const usableInput = el => {
            if (!visible(el)) return false;
            const rect = el.getBoundingClientRect();
            return rect.width >= 20 && rect.height >= 8;
          };
          const selectors = [
            "[placeholder*='有问必答']",
            "[placeholder*='可以问']",
            "[placeholder*='提问']",
            "[placeholder*='消息']",
            "[aria-label*='提问']",
            "[aria-label*='消息']",
            "[data-placeholder*='输入']",
            "[data-placeholder*='提问']",
            "[data-placeholder*='消息']",
            ".tiptap.ProseMirror[contenteditable='true']",
            "[class*='rich-text-editor'][contenteditable='true']",
            ".chat-input-editor[contenteditable='true']",
            "[class*='input'][contenteditable='true']",
            "[class*='editor'][contenteditable='true']",
            "[class*='textarea'] textarea",
            "[class*='input'] textarea",
            "[class*='editor'] textarea",
            "textarea[data-testid='prompt-textarea']",
            "div[contenteditable='true'][role='textbox']",
            "div[role='textbox'][contenteditable='true']",
            ".ProseMirror[contenteditable='true']",
            "[class*='ProseMirror'][contenteditable='true']",
            "[class*='ql-editor'][contenteditable='true']",
            "[class*='cm-content'][contenteditable='true']",
            "[contenteditable='plaintext-only']",
            "[aria-label*='输入']",
            "[placeholder*='输入']",
            "div[contenteditable='true']",
            "textarea",
            "[role='textbox']"
          ];
          let input = null;
          let selectorUsed = "";
          for (const selector of selectors) {
            const candidates = Array.from(document.querySelectorAll(selector)).filter(usableInput);
            input = candidates[candidates.length - 1];
            if (input) { selectorUsed = selector; break; }
          }
          if (!input) return {ok:false, error:"input_not_found"};
          input.focus();
          if (input.matches("textarea,input")) {
            const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")?.set;
            input.dispatchEvent(new InputEvent("beforeinput", {bubbles:true, cancelable:true, inputType:"insertText", data:prompt}));
            if (setter) setter.call(input, prompt); else input.value = prompt;
          } else {
            const range = document.createRange();
            range.selectNodeContents(input);
            const sel = window.getSelection();
            sel.removeAllRanges(); sel.addRange(range);
            let inserted = false;
            input.dispatchEvent(new InputEvent("beforeinput", {bubbles:true, cancelable:true, inputType:"insertText", data:prompt}));
            try {
              inserted = document.execCommand("insertText", false, prompt);
            } catch (_) {
              inserted = false;
            }
            if (!inserted || !(input.innerText || input.textContent || "").includes(marker)) {
              if (/ProseMirror|rich-text-editor/i.test(String(input.className || ""))) {
                input.innerHTML = "";
                const p = document.createElement("p");
                p.textContent = prompt;
                input.appendChild(p);
              } else {
                input.textContent = prompt;
              }
            }
          }
          input.dispatchEvent(new InputEvent("input", {bubbles:true, inputType:"insertText", data:prompt}));
          input.dispatchEvent(new Event("change", {bubbles:true}));
          input.dispatchEvent(new KeyboardEvent("keyup", {key:"Process", code:"Process", bubbles:true}));
          const value = input.value || input.innerText || input.textContent || "";
          const pageText = document.body?.innerText || document.body?.textContent || "";
          const promptWritten = value.includes(marker) || pageText.includes(marker);
          return {
            ok:promptWritten,
            prompt_written:promptWritten,
            method:"dom_execCommand",
            selector:selectorUsed,
            last_error:lastError
          };
        }"""
        ,
        {"prompt": prompt, "marker": prompt_id, "lastError": last_error[:160]},
    )
    presence = _prompt_presence(page, prompt_id)
    if presence.get("prompt_written"):
        if isinstance(dom_fallback, dict):
            dom_fallback["presence"] = presence
            dom_fallback["dom_write"] = written
            return dom_fallback
        return {"ok": True, "method": "dom_execCommand", "dom_write": written, "presence": presence}
    clipboard_fallback = _clipboard_paste_prompt(page, prompt, prompt_id, last_error)
    if clipboard_fallback.get("ok"):
        clipboard_fallback["dom_write"] = written
        clipboard_fallback["dom_fallback"] = dom_fallback
        return clipboard_fallback
    if isinstance(dom_fallback, dict):
        dom_fallback["ok"] = False
        dom_fallback["error"] = "prompt_write_unconfirmed"
        dom_fallback["presence"] = presence
        dom_fallback["dom_write"] = written
        dom_fallback["clipboard_fallback"] = clipboard_fallback
        return dom_fallback
    return {
        "ok": False,
        "error": "prompt_write_unconfirmed",
        "message": last_error or "The visible composer did not contain the AI Judge marker after write attempts.",
        "presence": presence,
        "dom_write": written,
        "clipboard_fallback": clipboard_fallback,
    }


def _send_prompt(page: Any, prompt_id: str) -> dict[str, Any]:
    host = urlparse(page.url).hostname or ""
    if host.endswith("chat.deepseek.com"):
        result = _send_deepseek_prompt(page)
        if result.get("ok"):
            return result

    dom_click = _evaluate_json(page, _build_click_send_js(prompt_id), "dom_send_click_failed")
    if dom_click.get("ok"):
        return dom_click
    if host.endswith("xinghuo.xfyun.cn"):
        return {
            "ok": False,
            "error": dom_click.get("error") or "xunfei_send_button_not_found",
            "message": dom_click.get("message") or "Xunfei requires the explicit SparkDesk send button; Enter fallback is disabled.",
            "method": "xunfei.explicit_button_required",
            "dom_click": dom_click,
        }

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


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def _seat_requires_fresh_conversation(
    config: dict[str, Any] | None,
    seat_config: dict[str, Any] | None,
    seat: str,
) -> bool:
    config = config or {}
    seat_config = seat_config or {}
    if seat == "grok":
        return True
    if seat == "xunfei":
        return False
    if "force_fresh_conversation" in seat_config:
        return _truthy(seat_config.get("force_fresh_conversation"))
    if "fresh_conversation_per_run" in seat_config:
        return _truthy(seat_config.get("fresh_conversation_per_run"))
    return _truthy(config.get("fresh_conversation_per_run"))


def _seat_uses_system_keyboard(
    config: dict[str, Any] | None,
    seat_config: dict[str, Any] | None,
    seat: str,
) -> bool:
    config = config or {}
    seat_config = seat_config or {}
    if seat == "grok":
        return True
    for key in ("force_keyboard_submit", "use_system_keyboard", "uses_system_keyboard"):
        if key in seat_config:
            return _truthy(seat_config.get(key))
    return _truthy(config.get("use_system_keyboard"))


def _system_keyboard_submit(
    page: Any,
    seat: str,
    seat_config: dict[str, Any] | None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    seat_config = seat_config or {}
    key_name = str(seat_config.get("system_keyboard_key") or "return").strip().lower()
    key_code = "36" if key_name in {"return", "enter", "keyboard.enter"} else "36"
    try:
        page.bring_to_front()
        page.wait_for_timeout(int(float(seat_config.get("system_keyboard_focus_delay_seconds") or 0.25) * 1000))
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events"', "-e", f"key code {key_code}", "-e", "end tell"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=4,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "osascript failed").strip())
        payload = {"ok": True, "method": "system_keyboard.enter", "key_code": int(key_code)}
    except Exception as exc:
        payload = {"ok": False, "error": "system_keyboard_failed", "message": str(exc), "method": "system_keyboard.enter"}
    if trace:
        trace(
            "seat",
            "cdp_system_keyboard_submit" if payload.get("ok") else "cdp_system_keyboard_submit_failed",
            f"{seat} 使用系统键盘提交" if payload.get("ok") else f"{seat} 系统键盘提交失败，回落 DOM 提交",
            {"seat": seat, "result": payload},
        )
    return payload


def _send_prompt_for_seat(
    page: Any,
    prompt_id: str,
    config: dict[str, Any] | None,
    seat_config: dict[str, Any] | None,
    seat: str,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    keyboard_attempt: dict[str, Any] = {}
    if _seat_uses_system_keyboard(config, seat_config, seat):
        keyboard_attempt = _system_keyboard_submit(page, seat, seat_config, trace)
        if keyboard_attempt.get("ok"):
            return keyboard_attempt
    result = _send_prompt(page, prompt_id)
    if keyboard_attempt:
        result["system_keyboard_attempt"] = keyboard_attempt
    return result


def _confirm_or_retry_submission(page: Any, prompt_id: str, send_result: dict[str, Any]) -> dict[str, Any]:
    submitted: dict[str, Any] = {
        "ok": bool(send_result.get("ok")),
        "send_result": send_result,
        "submitted": False,
    }
    if not send_result.get("ok"):
        submitted["error"] = str(send_result.get("error") or "send_failed")
        submitted["message"] = str(send_result.get("message") or "Prompt was written, but no send action succeeded.")
        return submitted

    def _poll_submission_state(label: str, attempts: int = 7, interval_ms: int = 850) -> dict[str, Any]:
        last: dict[str, Any] = {}
        for attempt in range(max(1, attempts)):
            last = _evaluate_json(page, _build_submission_check_js(prompt_id), "submission_check_failed")
            last["poll_label"] = label
            last["poll_attempt"] = attempt + 1
            if last.get("submitted"):
                return last
            reason = str(last.get("reason") or last.get("error") or "")
            if reason in {"provider_quota_limited", "prompt_too_long", "chrome_crash", "page_error", "login_required", "blank_page"}:
                return last
            try:
                page.wait_for_timeout(interval_ms)
            except Exception:
                break
        return last

    verification = _poll_submission_state("after_send")
    submitted["verification"] = verification
    if verification.get("submitted"):
        submitted["submitted"] = True
        submitted["ok"] = True
        return submitted

    retry = _evaluate_json(page, _build_retry_submit_js(prompt_id), "retry_submit_failed")
    submitted["retry"] = retry
    if retry.get("ok"):
        verification = _poll_submission_state("after_retry")
        submitted["verification"] = verification
        if verification.get("submitted"):
            submitted["submitted"] = True
            submitted["ok"] = True
            return submitted

    submitted["ok"] = False
    submitted["error"] = str(
        retry.get("error")
        or verification.get("reason")
        or verification.get("error")
        or "submit_unconfirmed"
    )
    submitted["message"] = str(
        retry.get("message")
        or verification.get("message")
        or "Prompt was written, but the page still showed it in the composer or did not expose it as a user turn."
    )
    return submitted


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


def _capture_page_with_seat_fallback(
    page: Any,
    marker: str,
    seat: str,
    item: dict[str, Any],
    question: str,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Capture by exact prompt marker, then fall back to latest same-seat marker."""
    capture = _capture_page(page, marker)
    assessment = _capture_acceptance(capture, item, question)
    if assessment.get("accepted") or capture.get("marker_found"):
        return capture, assessment, False

    try:
        raw = page.evaluate(_build_existing_answer_capture_js(seat))
        fallback = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
    except Exception as exc:
        fallback = {"ok": False, "error": "seat_marker_capture_failed", "message": str(exc)}
    if not isinstance(fallback, dict) or not fallback.get("ok"):
        return capture, assessment, False

    fallback_assessment = _capture_acceptance(fallback, item, question)
    if fallback_assessment.get("accepted"):
        fallback["cdp_capture_fallback"] = "same_page_seat_marker"
        return fallback, fallback_assessment, True
    return capture, assessment, False


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
    matches = _matching_tabs(seat_config, tabs)
    return matches[0] if matches else None


def _matching_tabs(seat_config: dict[str, Any], tabs: list[CDPTab]) -> list[CDPTab]:
    urls = _url_candidates(seat_config)
    domains = _match_domains(seat_config, urls)
    labels = _match_labels(seat_config)
    exact: list[CDPTab] = []
    domain_matches: list[CDPTab] = []
    label_matches: list[CDPTab] = []

    for tab in tabs:
        tab_url = str(tab.url or "")
        if any(url and tab_url.rstrip("/") == url.rstrip("/") for url in urls):
            exact.append(tab)
            continue
        lower_url = tab_url.lower()
        if any(domain and domain in lower_url for domain in domains):
            domain_matches.append(tab)
            continue
        if lower_url.startswith("chrome-error://"):
            lower_title = str(tab.title or "").lower()
            if any(domain and domain in lower_title for domain in domains):
                domain_matches.append(tab)
                continue
        if _label_fallback_enabled(seat_config):
            haystack = f"{tab.title} {tab.url}".lower()
            if any(label and label in haystack for label in labels):
                label_matches.append(tab)

    return _unique_tabs([*exact, *domain_matches, *label_matches])


def _unique_tabs(tabs: list[CDPTab]) -> list[CDPTab]:
    seen: set[str] = set()
    unique: list[CDPTab] = []
    for tab in tabs:
        key = _tab_identity(tab)
        if key in seen:
            continue
        seen.add(key)
        unique.append(tab)
    return unique


def _tab_identity(tab: CDPTab) -> str:
    return str(tab.target_id or f"{tab.title}\0{tab.url}\0{id(tab)}")


def _dedupe_enabled_cdp_tabs(
    config: dict[str, Any],
    tabs: list[CDPTab],
    endpoint: str,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    seat_matches: dict[str, list[CDPTab]] = {}
    primary_keys: set[str] = set()
    for seat, seat_config in (config.get("seats") or {}).items():
        if not seat_config.get("enabled") or str(seat_config.get("channel") or "web") != "web":
            continue
        matches = _matching_tabs(seat_config, tabs)
        if not matches:
            continue
        seat_matches[seat] = matches
        primary_keys.add(_tab_identity(matches[0]))

    closed: list[dict[str, Any]] = []
    closed_keys: set[str] = set()
    for seat, matches in seat_matches.items():
        for tab in matches[1:]:
            key = _tab_identity(tab)
            if key in primary_keys or key in closed_keys:
                continue
            result = _close_cdp_tab(endpoint, tab)
            result["seat"] = seat
            result["url"] = tab.url
            result["title"] = tab.title
            closed.append(result)
            closed_keys.add(key)
            if trace:
                event = "cdp_fixed_tab_duplicate_closed" if result.get("ok") else "cdp_fixed_tab_duplicate_close_failed"
                trace("seat", event, f"{seat} 重复固定标签已处理", result)
    return closed


def _close_cdp_tab(endpoint: str, tab: CDPTab) -> dict[str, Any]:
    target_id = str(tab.target_id or "").strip()
    if not target_id:
        return {"ok": False, "reason": "missing_target_id"}
    try:
        session = requests.Session()
        session.trust_env = False
        response = session.get(f"{endpoint}/json/close/{target_id}", timeout=5)
        response.raise_for_status()
        return {"ok": True, "target_id": target_id}
    except Exception as exc:
        return {"ok": False, "target_id": target_id, "error": str(exc)}


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
