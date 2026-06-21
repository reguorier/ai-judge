#!/usr/bin/env python3
"""Runtime-only MCP proxy for AI Judge.

Claude should not import or launch AI Judge internals. This server exposes a
small MCP surface that talks to the already-running AI Judge desktop API on
localhost, keeping browser/CDP control outside Claude's sandbox.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any

import sys
from pathlib import Path as _Path
_RUNTIME_ROOT = str(_Path(__file__).resolve().parent.parent)
if _RUNTIME_ROOT not in sys.path:
    sys.path.insert(0, _RUNTIME_ROOT)

import requests
from mcp.server.fastmcp import FastMCP
try:
    from product.reporting.output_contract import render_from_verdict as _contract_render
except ImportError:
    _contract_render = None


API_BASE = os.environ.get("AI_JUDGE_API_BASE", "http://127.0.0.1:8501").rstrip("/")
DEFAULT_TIMEOUT = float(os.environ.get("AI_JUDGE_API_TIMEOUT_SECONDS", "10"))
TEXT_PREVIEW_CHARS = 1200
LIST_ITEM_PREVIEW_CHARS = 400
LIST_MAX_ITEMS = 4

mcp = FastMCP("ai-judge-runtime")


def _session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def _request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    with _session() as session:
        response = session.request(method, url, json=payload, timeout=timeout or DEFAULT_TIMEOUT)
    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}
    if response.status_code >= 400:
        return {
            "ok": False,
            "status_code": response.status_code,
            "url": url,
            "error": data,
        }
    if isinstance(data, dict):
        data.setdefault("ok", True)
        return data
    return {"ok": True, "data": data}


def _normalize_seats(seats: list[str] | str | None) -> list[str]:
    if seats is None:
        return []
    if isinstance(seats, str):
        return [item.strip().lower() for item in seats.split(",") if item.strip()]
    return [str(item).strip().lower() for item in seats if str(item).strip()]


def _compact_bridge_status(status: dict[str, Any]) -> dict[str, Any]:
    matrix = status.get("seat_browser_matrix") or []
    return {
        "ok": bool(status.get("available")),
        "available": status.get("available"),
        "automation_driver": status.get("automation_driver"),
        "configured_count": status.get("configured_count"),
        "enabled_count": status.get("enabled_count"),
        "ready_count": status.get("ready_count"),
        "chrome_cdp": status.get("chrome_cdp"),
        "not_ready": [
            {
                "seat": item.get("seat"),
                "provider": item.get("provider"),
                "reason": item.get("reason"),
                "target": item.get("target"),
            }
            for item in matrix
            if not item.get("ready")
        ],
        "ready_seats": [item.get("seat") for item in matrix if item.get("ready")],
        "config_path": status.get("config_path"),
    }


@mcp.tool()
def ai_judge_health() -> dict[str, Any]:
    """Return AI Judge desktop API health and seat count."""
    return _request_json("GET", "/api/health")


@mcp.tool()
def ai_judge_bridge_status(full: bool = False) -> dict[str, Any]:
    """Return web bridge readiness; use full=true for raw seat matrix."""
    status = _request_json("GET", "/api/bridge/status", timeout=15)
    if full:
        return status
    return _compact_bridge_status(status)


@mcp.tool()
def ai_judge_calibrate(seats: list[str] | str | None = None, timeout_seconds: float = 12) -> dict[str, Any]:
    """Run AI Judge bridge calibration for selected seats, or all seats if omitted."""
    payload: dict[str, Any] = {"timeout_seconds": timeout_seconds}
    normalized = _normalize_seats(seats)
    if normalized:
        payload["seats"] = normalized
    return _request_json("POST", "/api/bridge/calibrate", payload=payload, timeout=max(30, timeout_seconds * 5))


@mcp.tool()
def ai_judge_run(
    question: str,
    seats: list[str] | str | None = None,
    mode: str = "strategic",
    wait: bool = True,
    timeout_seconds: float = 900,
    poll_interval_seconds: float = 3,
    raw: bool = False,
) -> dict[str, Any]:
    """Submit an AI Judge web run and optionally wait for the verdict; set raw=true for full output."""
    question = str(question or "").strip()
    if not question:
        return {"ok": False, "error": "question is required"}

    payload: dict[str, Any] = {
        "question": question,
        "mode": mode,
        "engine": "web",
    }
    normalized = _normalize_seats(seats)
    if normalized:
        payload["seats"] = normalized

    submitted = _request_json("POST", "/api/judge", payload=payload, timeout=20)
    run_id = submitted.get("run_id")
    if not submitted.get("ok") or not run_id or not wait:
        return submitted

    deadline = time.time() + max(1, timeout_seconds)
    last_status: dict[str, Any] = submitted
    while time.time() < deadline:
        last_status = _request_json("GET", f"/api/task/{run_id}", timeout=10)
        status = str(last_status.get("status") or "").lower()
        if status == "complete":
            verdict = _request_json("GET", f"/api/judge/{run_id}/verdict", timeout=30)
            result = {
                "ok": True,
                "run_id": run_id,
                "status": status,
                "task": last_status,
                "verdict": _summarize_verdict(verdict),
            }
            if raw:
                result["verdict_raw"] = verdict
            return result
        if status in {"failed", "cancelled", "missing"}:
            return {"ok": False, "run_id": run_id, "status": status, "task": last_status}
        time.sleep(max(1, min(30, poll_interval_seconds)))

    return {
        "ok": False,
        "run_id": run_id,
        "status": "timeout",
        "task": last_status,
        "message": "AI Judge run did not complete before timeout; call ai_judge_result later.",
    }


@mcp.tool()
def ai_judge_result(run_id: str, raw: bool = False) -> dict[str, Any]:
    """Fetch an AI Judge verdict by run id."""
    run_id = str(run_id or "").strip()
    if not run_id:
        return {"ok": False, "error": "run_id is required"}
    verdict = _request_json("GET", f"/api/judge/{run_id}/verdict", timeout=30)
    return verdict if raw else _summarize_verdict(verdict)


@mcp.tool()
def ai_judge_cancel(run_id: str) -> dict[str, Any]:
    """Cancel an active AI Judge run."""
    run_id = str(run_id or "").strip()
    if not run_id:
        return {"ok": False, "error": "run_id is required"}
    return _request_json("POST", f"/api/judge/{run_id}/cancel", payload={}, timeout=10)


def _summarize_verdict(verdict: dict[str, Any]) -> dict[str, Any]:
    """Compact verdict output via output contract."""
    if not verdict.get("ok", True):
        return _compact_response(verdict)
    if _contract_render:
        try:
            return _contract_render(verdict, fmt="compact")
        except Exception:
            pass
    # Fallback
    bridge = verdict.get("web_bridge") or {}
    return {
        "ok": True,
        "run_id": verdict.get("run_id"),
        "verdict": verdict.get("verdict"),
        "confidence": verdict.get("confidence"),
        "one_liner": verdict.get("one_liner"),
        "status": verdict.get("status"),
        "evidence": {"ok_count": bridge.get("ok_count"), "failed_count": bridge.get("failed_count")},
        "view_url": verdict.get("view_url"),
        "reasons": verdict.get("reasons"),
    }
def _truncate_text(value: Any, limit: int = TEXT_PREVIEW_CHARS) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit].rstrip()}... [truncated {omitted} chars]"


def _compact_list(value: Any, max_items: int = LIST_MAX_ITEMS) -> list[str]:
    if not isinstance(value, list):
        return []
    compacted: list[str] = []
    for item in value[:max_items]:
        preview = _truncate_text(item, LIST_ITEM_PREVIEW_CHARS)
        if preview:
            compacted.append(preview)
    if len(value) > max_items:
        compacted.append(f"... {len(value) - max_items} more")
    return compacted


def _compact_error(error: Any) -> dict[str, Any] | str | None:
    if not error:
        return None
    if not isinstance(error, dict):
        return _truncate_text(error, LIST_ITEM_PREVIEW_CHARS)
    compact: dict[str, Any] = {}
    for key in ("code", "message", "type", "status"):
        if key in error:
            compact[key] = _truncate_text(error.get(key), LIST_ITEM_PREVIEW_CHARS)
    if not compact:
        compact["preview"] = _truncate_text(error, LIST_ITEM_PREVIEW_CHARS)
    return compact


def _compact_seat(seat: Any) -> dict[str, Any]:
    if not isinstance(seat, dict):
        return {"preview": _truncate_text(seat) or ""}

    preview = (
        seat.get("answer_preview")
        or seat.get("one_liner")
        or seat.get("summary")
        or seat.get("response")
    )
    compact = {
        "seat": seat.get("seat"),
        "seat_name": seat.get("seat_name"),
        "ok": seat.get("ok"),
        "status": seat.get("status"),
        "stance": seat.get("stance"),
        "score": seat.get("score"),
        "quality": seat.get("quality"),
        "avg_peer_score": seat.get("avg_peer_score"),
        "claims_count": seat.get("claims_count"),
        "strength": _truncate_text(seat.get("strength"), LIST_ITEM_PREVIEW_CHARS),
        "weakness": _truncate_text(seat.get("weakness"), LIST_ITEM_PREVIEW_CHARS),
        "answer_preview": _truncate_text(preview),
        "pros": _compact_list(seat.get("pros")),
        "cons": _compact_list(seat.get("cons")),
        "error": _compact_error(seat.get("error")),
    }
    return {key: value for key, value in compact.items() if value not in (None, [], {})}


def _compact_response(value: Any, *, depth: int = 0) -> Any:
    if depth >= 4:
        return _truncate_text(value, LIST_ITEM_PREVIEW_CHARS)
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"question", "prompt", "response", "raw_text", "raw", "html", "verdict_raw"}:
                compact[key] = _truncate_text(item, TEXT_PREVIEW_CHARS)
            else:
                compact[key] = _compact_response(item, depth=depth + 1)
        return {key: item for key, item in compact.items() if item not in (None, [], {})}
    if isinstance(value, list):
        items = [_compact_response(item, depth=depth + 1) for item in value[:LIST_MAX_ITEMS]]
        if len(value) > LIST_MAX_ITEMS:
            items.append(f"... {len(value) - LIST_MAX_ITEMS} more")
        return items
    if isinstance(value, str):
        return _truncate_text(value, TEXT_PREVIEW_CHARS)
    return value


def self_test() -> None:
    print(json.dumps({
        "health": ai_judge_health(),
        "bridge_status": ai_judge_bridge_status(),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        mcp.run()
