#!/usr/bin/env python3
"""Execution-driver decisions for AI Judge product runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.modes import resolve_mode
from core.seat_personas import SEAT_PERSONAS


MIN_WEB_READY_SEATS = 2


DRIVER_LABELS = {
    "local_synthetic": "本地稳定引擎",
    "web_dom": "隔离浏览器 DOM",
    "chrome_apple_events": "Chrome 固定标签 DOM",
    "chrome_cdp": "Chrome CDP 固定标签",
    "desktop_operator": "桌面客户端 Operator",
    "api_provider": "官方 API",
    "unconfigured": "未配置",
}


def driver_for_bridge_seat(seat_row: dict[str, Any]) -> dict[str, Any]:
    """Return driver metadata for a bridge-status seat row."""
    explicit_driver = str(seat_row.get("driver") or "")
    if explicit_driver == "chrome_apple_events":
        return {
            "driver": "chrome_apple_events",
            "driver_label": DRIVER_LABELS["chrome_apple_events"],
            "safe_background": True,
            "operator_required": False,
            "uses_system_mouse": False,
            "uses_system_keyboard": False,
            "uses_system_clipboard": False,
            "notes": "复用已打开 Chrome 标签页，通过 Apple Events 执行 DOM 脚本；需要 Chrome 开启允许 Apple 事件中的 JavaScript。",
        }
    if explicit_driver == "chrome_cdp":
        return {
            "driver": "chrome_cdp",
            "driver_label": DRIVER_LABELS["chrome_cdp"],
            "safe_background": True,
            "operator_required": False,
            "uses_system_mouse": False,
            "uses_system_keyboard": False,
            "uses_system_clipboard": False,
            "notes": "复用已打开 Chrome 标签页，通过本地 CDP 发送浏览器级输入事件；不触碰系统鼠标、键盘或剪贴板。",
        }
    channel = str(seat_row.get("channel") or "web")
    if channel == "desktop":
        return {
            "driver": "desktop_operator",
            "driver_label": DRIVER_LABELS["desktop_operator"],
            "safe_background": False,
            "operator_required": True,
            "uses_system_mouse": False,
            "uses_system_keyboard": False,
            "uses_system_clipboard": False,
            "notes": "需要专用桌面 Operator；当前不会静默抢占用户鼠标、键盘或剪贴板。",
        }
    if channel == "api":
        return {
            "driver": "api_provider",
            "driver_label": DRIVER_LABELS["api_provider"],
            "safe_background": True,
            "operator_required": False,
            "uses_system_mouse": False,
            "uses_system_keyboard": False,
            "uses_system_clipboard": False,
            "notes": "通过 provider API 后台运行。",
        }
    if channel == "web":
        return {
            "driver": "web_dom",
            "driver_label": DRIVER_LABELS["web_dom"],
            "safe_background": True,
            "operator_required": False,
            "uses_system_mouse": False,
            "uses_system_keyboard": False,
            "uses_system_clipboard": False,
            "notes": "使用独立浏览器 profile 与 DOM 操作，不触碰用户当前输入焦点。",
        }
    return {
        "driver": "unconfigured",
        "driver_label": DRIVER_LABELS["unconfigured"],
        "safe_background": False,
        "operator_required": False,
        "uses_system_mouse": False,
        "uses_system_keyboard": False,
        "uses_system_clipboard": False,
        "notes": "席位通道尚未配置。",
    }


def decide_execution(
    engine: str,
    mode: str,
    requested_seats: list[str],
    bridge_status: dict[str, Any] | None = None,
    min_web_ready: int = MIN_WEB_READY_SEATS,
) -> dict[str, Any]:
    """Return the product execution decision before a run starts."""
    config = resolve_mode(mode, override_seats=requested_seats)
    seats = [seat for seat in config["seats"] if seat in SEAT_PERSONAS]
    if engine != "web":
        return {
            "engine": engine,
            "mode": mode,
            "driver": "local_synthetic",
            "driver_label": DRIVER_LABELS["local_synthetic"],
            "requested_seats": seats,
            "runnable_seats": seats,
            "blocked_seats": [],
            "can_run_deep_collection": True,
            "minimum_ready_seats": 0,
            "decision": "run_local",
            "message": "本地稳定引擎可立即运行；它不代表真实网页/客户端回答。",
        }

    bridge_status = bridge_status or {}
    rows = {row.get("id"): row for row in bridge_status.get("seats", [])}
    runnable: list[str] = []
    blocked: list[dict[str, Any]] = []
    runnable_drivers: list[str] = []
    for seat in seats:
        row = rows.get(seat) or {}
        if row.get("ready"):
            runnable.append(seat)
            driver = row.get("driver") or driver_for_bridge_seat(row).get("driver")
            if driver:
                runnable_drivers.append(str(driver))
        else:
            blocked.append({
                "seat": seat,
                "seat_name": SEAT_PERSONAS[seat]["name"],
                "reason": row.get("reason") or "not_ready",
                "driver": row.get("driver") or driver_for_bridge_seat(row).get("driver"),
                "calibration_status": (row.get("calibration") or {}).get("status", "missing"),
            })

    can_run = len(runnable) >= min_web_ready
    driver = _dominant_driver(runnable_drivers) or "web_dom"
    return {
        "engine": engine,
        "mode": mode,
        "driver": driver,
        "driver_label": DRIVER_LABELS.get(driver, DRIVER_LABELS["web_dom"]),
        "requested_seats": seats,
        "runnable_seats": runnable,
        "blocked_seats": blocked,
        "can_run_deep_collection": can_run,
        "minimum_ready_seats": min_web_ready,
        "decision": "run_web" if can_run else "block_for_calibration",
        "message": (
            f"网页深度收集需要至少 {min_web_ready} 个校准通过席位；"
            f"当前可运行 {len(runnable)} 个。"
        ),
    }


def _dominant_driver(drivers: list[str]) -> str | None:
    if not drivers:
        return None
    return max(set(drivers), key=drivers.count)


def build_bridge_blocked_verdict(
    question: str,
    mode: str,
    seats: list[str],
    run_id: str | None,
    prompt_flow: dict[str, Any],
    execution_plan: dict[str, Any],
    bridge_status: dict[str, Any],
) -> dict[str, Any]:
    """Return a complete verdict-shaped object when deep collection is blocked."""
    config = resolve_mode(mode, override_seats=seats)
    blocked = execution_plan.get("blocked_seats") or []
    reason_lines = []
    for item in blocked[:20]:
        reason_lines.append(
            f"{item.get('seat_name', item.get('seat'))}: "
            f"{item.get('reason', 'not_ready')} / 校准={item.get('calibration_status', 'missing')}"
        )
    if not reason_lines:
        reason_lines.append("网页桥接没有足够已校准席位可用于深度收集。")

    ready_count = int(bridge_status.get("ready_count") or 0)
    configured_count = int(bridge_status.get("configured_count") or bridge_status.get("enabled_count") or 0)
    return {
        "run_id": run_id,
        "question": question,
        "mode": mode,
        "mode_name": config["name"],
        "mode_emoji": config["emoji"],
        "seats": seats,
        "seat_count": len(seats),
        "status": "complete",
        "verdict": "unverified",
        "verdict_label": "网页深度未启动",
        "one_liner": (
            f"深度网页收集被产品流阻断：已配置 {configured_count} 席，"
            f"校准可运行 {ready_count} 席，低于最低要求 {execution_plan.get('minimum_ready_seats', MIN_WEB_READY_SEATS)} 席。"
        ),
        "confidence": 0,
        "average_score": 0.0,
        "tier_distribution": {},
        "total_claims": 0,
        "seat_scores": [],
        "reasons": reason_lines,
        "next_steps": [
            "在“席位评分”页点击“校准网页席位”，逐席确认登录、输入框、发送按钮和回答读取都可用。",
            "只有校准通过的 web_dom 席位会进入后台深度收集；失败席位会保留原因，不参与判词。",
            "豆包桌面客户端需要专用 Operator 后才能后台运行；当前不会使用全局鼠标、键盘或剪贴板抢占用户操作。",
        ],
        "claims": [],
        "summary": prompt_flow.get("quick_response", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "engine": "execution-driver-router-v3.4",
        "features": config.get("features", {}),
        "prompt_flow": prompt_flow,
        "execution_plan": execution_plan,
        "web_bridge": {
            "ready_count": ready_count,
            "configured_count": configured_count,
            "enabled_count": bridge_status.get("enabled_count", 0),
            "seat_browser_matrix": bridge_status.get("seat_browser_matrix", []),
            "isolation": bridge_status.get("isolation", {}),
        },
    }
