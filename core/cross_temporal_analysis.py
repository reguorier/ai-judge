"""Cross-temporal report layer for AI Judge verdicts.

The module keeps the user's "vertical history + horizontal comparison" method
close to the verdict data itself, so every surface can render the same
professional closeout instead of rebuilding summaries in the UI.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any


def attach_cross_temporal_analysis(verdict: dict[str, Any]) -> dict[str, Any]:
    """Attach a cross-temporal analysis block to a verdict in place."""
    verdict["cross_temporal_analysis"] = build_cross_temporal_analysis(verdict)
    return verdict


def build_cross_temporal_analysis(verdict: dict[str, Any]) -> dict[str, Any]:
    """Build the product-ready cross-temporal analysis payload."""
    bridge = verdict.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    seat_scores = _seat_score_rows(verdict)
    if bridge:
        requested = _int(bridge.get("requested_count"), len(raw_results) or _int(verdict.get("seat_count"), 0))
        ok_count = _int(bridge.get("ok_count"), sum(1 for item in raw_results if item.get("ok")))
        failed_count = _int(bridge.get("failed_count"), max(0, requested - ok_count))
        pending_count = sum(1 for item in raw_results if _is_recoverable_raw_result(item))
    else:
        requested = _int(verdict.get("seat_count"), len(seat_scores) or len(verdict.get("seats") or []))
        ok_count = len([item for item in seat_scores if item.get("score") is not None]) or requested
        failed_count = 0
        pending_count = 0
    scores = [float(item["score"]) for item in seat_scores if item.get("score") is not None]
    confidence = _int(verdict.get("confidence"), 0)
    average_score = _float(verdict.get("average_score"), None)
    score_stats = _score_stats(scores)
    vertical = _vertical_trace(verdict)
    horizontal = _horizontal_comparison(verdict, seat_scores, requested, ok_count, failed_count, pending_count)
    math_signals = _math_signals(
        verdict=verdict,
        scores=scores,
        score_stats=score_stats,
        requested=requested,
        ok_count=ok_count,
        failed_count=failed_count,
        pending_count=pending_count,
    )
    recommended_actions = _recommended_actions(
        verdict=verdict,
        vertical=vertical,
        horizontal=horizontal,
        math_signals=math_signals,
        confidence=confidence,
        pending_count=pending_count,
    )
    closeout = _closeout_report(
        verdict=verdict,
        horizontal=horizontal,
        math_signals=math_signals,
        recommended_actions=recommended_actions,
        confidence=confidence,
        average_score=average_score,
    )
    return {
        "schema": "cross_temporal_analysis.v1",
        "method": "纵向追时间深度，横向追同期广度，交叉后形成可执行判断。",
        "closeout_report": closeout,
        "vertical_trace": vertical,
        "horizontal_comparison": horizontal,
        "math_audit": {
            "score_stats": score_stats,
            "signals": math_signals,
        },
        "recommended_actions": recommended_actions,
    }


def cross_temporal_markdown(verdict: dict[str, Any]) -> list[str]:
    """Render the analysis block as Markdown lines."""
    analysis = verdict.get("cross_temporal_analysis") or build_cross_temporal_analysis(verdict)
    closeout = analysis.get("closeout_report") or {}
    vertical = analysis.get("vertical_trace") or {}
    horizontal = analysis.get("horizontal_comparison") or {}
    math_audit = analysis.get("math_audit") or {}
    actions = analysis.get("recommended_actions") or []
    signals = math_audit.get("signals") or []
    lines = [
        "## Cross-Temporal Closeout",
        "",
        f"**Final judgment:** {closeout.get('final_judgment', '-')}",
        f"**Decision score:** {closeout.get('decision_score', '-')}",
        "",
        closeout.get("executive_summary", ""),
        "",
        "### Vertical Trace",
        "",
        f"- Current stage: {vertical.get('current_stage', '-')}",
        f"- Key turn: {vertical.get('key_turn', '-')}",
        f"- Bridge health: {vertical.get('bridge_health', '-')}",
        "",
        "### Horizontal Comparison",
        "",
        f"- Returned seats: {horizontal.get('ok_count', 0)}/{horizontal.get('requested_count', 0)}",
        f"- Leader: {horizontal.get('leader', {}).get('seat_name', '-')}",
        f"- Outlier: {horizontal.get('outlier', {}).get('seat_name', '-')}",
        f"- Consensus: {horizontal.get('consensus_label', '-')}",
        "",
        "### Math Audit Signals",
        "",
    ]
    for signal in signals[:6]:
        lines.append(f"- {signal.get('label')}: {signal.get('summary')}")
    lines.extend(["", "### Recommended Actions", ""])
    for action in actions[:6]:
        lines.append(f"- {action}")
    return lines


def _vertical_trace(verdict: dict[str, Any]) -> dict[str, Any]:
    events = ((verdict.get("execution_trace") or {}).get("events") or [])[:]
    phases = [str(event.get("phase") or "") for event in events if event.get("phase")]
    phase_counts = Counter(phases)
    bridge = verdict.get("web_bridge") or {}
    retry_events = [
        event for event in events
        if "retry" in str(event.get("phase") or "").lower()
        or "retry" in str(event.get("action") or "").lower()
        or "补" in str(event.get("detail") or "")
        or "回收" in str(event.get("detail") or "")
    ]
    timeout_events = [
        event for event in events
        if "timeout" in str(event.get("action") or "").lower()
        or "超时" in str(event.get("detail") or "")
        or "等待" in str(event.get("detail") or "")
    ]
    last_event = events[-1] if events else {}
    key_turn = "已完成本地评分"
    if bridge and not bridge.get("collection_complete", True):
        key_turn = "网页席位未全量回收，结论必须带条件"
    elif retry_events:
        key_turn = "通过旧页面回收/补采修正了席位缺口"
    elif timeout_events:
        key_turn = "执行中出现等待或超时，需要保留追踪原因"
    return {
        "event_count": len(events),
        "phase_counts": dict(phase_counts),
        "current_stage": str(last_event.get("phase") or verdict.get("status") or "complete"),
        "key_turn": key_turn,
        "bridge_health": _bridge_health_label(bridge),
        "retry_event_count": len(retry_events),
        "timeout_event_count": len(timeout_events),
        "last_event": {
            "phase": last_event.get("phase"),
            "action": last_event.get("action"),
            "detail": last_event.get("detail"),
        },
        "timeline": [
            {
                "index": event.get("index"),
                "phase": event.get("phase"),
                "action": event.get("action"),
                "detail": event.get("detail"),
            }
            for event in events[-8:]
        ],
    }


def _horizontal_comparison(
    verdict: dict[str, Any],
    seat_scores: list[dict[str, Any]],
    requested: int,
    ok_count: int,
    failed_count: int,
    pending_count: int,
) -> dict[str, Any]:
    ordered = sorted(seat_scores, key=lambda item: (item.get("score") is None, -(item.get("score") or 0.0)))
    scored = [item for item in ordered if item.get("score") is not None]
    leader = scored[0] if scored else {}
    weakest = scored[-1] if scored else {}
    spread = round((leader.get("score", 0.0) or 0.0) - (weakest.get("score", 0.0) or 0.0), 4) if len(scored) >= 2 else 0.0
    consensus_label = "强共识"
    if pending_count or failed_count:
        consensus_label = "席位不完整"
    elif spread >= 0.22:
        consensus_label = "高分歧"
    elif spread >= 0.12:
        consensus_label = "中等分歧"
    outlier = weakest if spread >= 0.12 else {}
    return {
        "requested_count": requested,
        "ok_count": ok_count,
        "failed_count": failed_count,
        "pending_count": pending_count,
        "coverage_ratio": round(ok_count / requested, 4) if requested else 0.0,
        "consensus_label": consensus_label,
        "score_spread": spread,
        "leader": _compact_seat(leader),
        "outlier": _compact_seat(outlier),
        "seat_ranking": [_compact_seat(item) for item in ordered],
        "comparison_note": _comparison_note(verdict, ok_count, requested, consensus_label, leader, weakest),
    }


def _math_signals(
    *,
    verdict: dict[str, Any],
    scores: list[float],
    score_stats: dict[str, Any],
    requested: int,
    ok_count: int,
    failed_count: int,
    pending_count: int,
) -> list[dict[str, Any]]:
    bridge = verdict.get("web_bridge") or {}
    rounds = bridge.get("score_rounds") or []
    stage_counts = Counter(str(event.get("phase") or "") for event in ((verdict.get("execution_trace") or {}).get("events") or []))
    entropy = _entropy(scores)
    stddev = _float(score_stats.get("stddev"), 0.0) or 0.0
    spread = _float(score_stats.get("spread"), 0.0) or 0.0
    trend = _least_squares_trend([_float(item.get("average_score"), None) for item in rounds])
    coverage = ok_count / requested if requested else 0.0
    signals = [
        {
            "id": "coverage_gate",
            "label": "容斥式席位覆盖",
            "value": round(coverage, 4),
            "severity": "block" if requested and ok_count < requested else "ok",
            "summary": f"{ok_count}/{requested} 席形成有效答案，{pending_count} 席可继续只读回收。",
            "next_action": _coverage_next_action(requested, ok_count, pending_count),
        },
        {
            "id": "entropy",
            "label": "信息熵分歧",
            "value": entropy,
            "severity": "warn" if entropy >= 1.2 else "ok",
            "summary": f"评分分布熵为 {entropy:.3f}，用于判断模型是否集中在同一判断带。",
            "next_action": "熵高时优先查看最低分/最高分席位的理由差异。" if entropy >= 1.2 else "分布相对集中，重点验证证据而非重开讨论。",
        },
        {
            "id": "cauchy_schwarz_spread",
            "label": "C-S 稳定边界",
            "value": round(stddev, 4),
            "severity": "warn" if stddev >= 0.12 or spread >= 0.24 else "ok",
            "summary": f"标准差 {stddev:.3f}，极差 {spread:.3f}；衡量席位向量是否稳定。",
            "next_action": "若极差过大，把低分席位作为反例审查入口。" if stddev >= 0.12 or spread >= 0.24 else "席位评分稳定，可把精力放到执行路径。",
        },
        {
            "id": "least_squares_trend",
            "label": "最小二乘轮次趋势",
            "value": trend,
            "severity": "warn" if trend is not None and trend < -0.02 else "ok",
            "summary": "评分轮次随审议推进的斜率为 " + ("-" if trend is None else f"{trend:.4f}"),
            "next_action": "趋势下行说明互评或补采暴露了新风险。" if trend is not None and trend < -0.02 else "趋势未显示明显塌陷。",
        },
        {
            "id": "svd_consensus_proxy",
            "label": "SVD 共识主轴代理",
            "value": _svd_consensus_proxy(scores),
            "severity": "warn" if _svd_consensus_proxy(scores) < 0.55 else "ok",
            "summary": "用评分方差集中度近似判断是否存在清晰共识主轴。",
            "next_action": "主轴弱时不要只读平均分，要展示分歧席位原文。",
        },
        {
            "id": "markov_stage_trace",
            "label": "马尔可夫阶段跳转",
            "value": len(stage_counts),
            "severity": "warn" if failed_count and len(stage_counts) <= 3 else "ok",
            "summary": f"执行轨迹覆盖 {len(stage_counts)} 类阶段，帮助定位卡点发生在哪一步。",
            "next_action": "阶段过少且有失败时，优先查桥接提交/采集日志。",
        },
    ]
    return signals


def _recommended_actions(
    *,
    verdict: dict[str, Any],
    vertical: dict[str, Any],
    horizontal: dict[str, Any],
    math_signals: list[dict[str, Any]],
    confidence: int,
    pending_count: int,
) -> list[str]:
    actions: list[str] = []
    if pending_count:
        actions.append("先执行旧页面只读回收，补齐仍有页面答案但未进 verdict 的席位。")
    elif horizontal.get("failed_count", 0):
        actions.append("查看失败席位原因；若不可只读回收，就重新校准桥接或重跑该席位。")
    if confidence < 80:
        actions.append("把当前结论标记为条件支持，补一轮外部证据或小实验后再发布。")
    if horizontal.get("score_spread", 0) >= 0.12:
        actions.append("打开模型对比页，优先阅读最高分与最低分席位原文，确认分歧来自事实还是策略偏好。")
    if vertical.get("timeout_event_count", 0):
        actions.append("保留桥接等待/超时日志，作为后续修复模型页面适配的证据。")
    if not actions:
        actions.append("结论、席位覆盖和数学信号均未触发阻断，可进入证据审查和发布门禁。")
    for step in verdict.get("next_steps") or []:
        text = str(step).strip()
        if text and text not in actions:
            actions.append(text)
        if len(actions) >= 6:
            break
    severe = [signal for signal in math_signals if signal.get("severity") == "block"]
    if severe and not any("发布" in item for item in actions):
        actions.append("存在阻断信号，发布前必须重新检查覆盖率与证据链。")
    return actions[:6]


def _closeout_report(
    *,
    verdict: dict[str, Any],
    horizontal: dict[str, Any],
    math_signals: list[dict[str, Any]],
    recommended_actions: list[str],
    confidence: int,
    average_score: float | None,
) -> dict[str, Any]:
    label = str(verdict.get("verdict_label") or verdict.get("verdict") or "待判断")
    score_text = f"{confidence}/100"
    if average_score is not None:
        score_text = f"{confidence}/100 · 均分 {average_score:.3f}"
    bridge_clause = (
        f"席位覆盖 {horizontal.get('ok_count', 0)}/{horizontal.get('requested_count', 0)}，"
        f"共识状态为{horizontal.get('consensus_label', '-')}"
    )
    risk_signals = [signal for signal in math_signals if signal.get("severity") in {"warn", "block"}]
    risk_text = "；".join(str(signal.get("summary")) for signal in risk_signals[:2]) or "数学审计未发现明显结构性阻断。"
    first_action = recommended_actions[0] if recommended_actions else "进入证据审查。"
    final_judgment = f"{label}，综合评分 {score_text}。"
    executive = (
        f"{final_judgment} {bridge_clause}。横向比较显示：{horizontal.get('comparison_note', '')}"
        f" 数学审计提示：{risk_text} 下一步：{first_action}"
    )
    return {
        "title": "最终结论与执行建议",
        "final_judgment": final_judgment,
        "decision_score": score_text,
        "executive_summary": executive,
        "risk_summary": risk_text,
        "first_action": first_action,
    }


def _score_stats(scores: list[float]) -> dict[str, Any]:
    if not scores:
        return {"count": 0, "mean": None, "min": None, "max": None, "spread": None, "stddev": None}
    mean = sum(scores) / len(scores)
    variance = sum((score - mean) ** 2 for score in scores) / len(scores)
    return {
        "count": len(scores),
        "mean": round(mean, 4),
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "spread": round(max(scores) - min(scores), 4),
        "stddev": round(math.sqrt(variance), 4),
    }


def _coverage_next_action(requested: int, ok_count: int, pending_count: int) -> str:
    if requested and ok_count < requested:
        if pending_count:
            return "先补齐可回收席位，再把结论提升为发布级。"
        return "席位缺口不可自动回收，需要查看失败原因或重跑桥接。"
    return "覆盖完整，可进入证据与发布门禁。"


def _entropy(scores: list[float]) -> float:
    if not scores:
        return 0.0
    buckets = Counter(int(max(0, min(0.999, score)) * 5) for score in scores)
    total = sum(buckets.values())
    value = 0.0
    for count in buckets.values():
        p = count / total
        value -= p * math.log2(p)
    return round(value, 4)


def _least_squares_trend(values: list[float | None]) -> float | None:
    y = [float(value) for value in values if value is not None]
    if len(y) < 2:
        return None
    n = len(y)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(y) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None
    slope = sum((x - mean_x) * (value - mean_y) for x, value in zip(xs, y)) / denom
    return round(slope, 4)


def _svd_consensus_proxy(scores: list[float]) -> float:
    if not scores:
        return 0.0
    mean = sum(scores) / len(scores)
    residual = sum((score - mean) ** 2 for score in scores)
    energy = sum(score ** 2 for score in scores) or 1.0
    return round(max(0.0, min(1.0, 1.0 - residual / energy)), 4)


def _seat_score_rows(verdict: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_by_seat = {
        str(item.get("seat")): item
        for item in ((verdict.get("web_bridge") or {}).get("raw_results") or [])
        if item.get("seat")
    }
    for item in verdict.get("seat_scores") or []:
        seat = str(item.get("seat") or "")
        raw = raw_by_seat.get(seat) or {}
        rows.append({
            "seat": seat,
            "seat_name": str(item.get("seat_name") or raw.get("seat_name") or seat),
            "score": _float(item.get("average_score"), None),
            "claims_count": _int(item.get("claims_count"), 0),
            "ok": raw.get("ok", True),
            "status": "已返回" if raw.get("ok", True) else _raw_error_label(raw),
        })
    for seat, raw in raw_by_seat.items():
        if any(item.get("seat") == seat for item in rows):
            continue
        rows.append({
            "seat": seat,
            "seat_name": str(raw.get("seat_name") or seat),
            "score": None,
            "claims_count": 0,
            "ok": bool(raw.get("ok")),
            "status": "已返回" if raw.get("ok") else _raw_error_label(raw),
        })
    return rows


def _comparison_note(
    verdict: dict[str, Any],
    ok_count: int,
    requested: int,
    consensus_label: str,
    leader: dict[str, Any],
    weakest: dict[str, Any],
) -> str:
    if requested and ok_count < requested:
        return f"只回收到 {ok_count}/{requested} 席，当前判断不能包装成全模型共识。"
    if leader and weakest and leader.get("seat") != weakest.get("seat"):
        return (
            f"{leader.get('seat_name')} 给出最高支撑，{weakest.get('seat_name')} 构成主要反例；"
            f"当前属于{consensus_label}。"
        )
    return f"当前属于{consensus_label}，结论需要继续和原问题保持一一对应。"


def _compact_seat(item: dict[str, Any]) -> dict[str, Any]:
    if not item:
        return {}
    score = item.get("score")
    return {
        "seat": item.get("seat"),
        "seat_name": item.get("seat_name"),
        "score": None if score is None else round(float(score), 4),
        "claims_count": item.get("claims_count", 0),
        "status": item.get("status"),
    }


def _bridge_health_label(bridge: dict[str, Any]) -> str:
    if not bridge:
        return "本地引擎"
    requested = _int(bridge.get("requested_count"), 0)
    ok_count = _int(bridge.get("ok_count"), 0)
    if requested and ok_count == requested and not bridge.get("failed_count"):
        return "网页桥接完整"
    if ok_count:
        return "网页桥接部分完成"
    return "网页桥接未形成有效答案"


def _is_recoverable_raw_result(item: dict[str, Any]) -> bool:
    if item.get("ok"):
        return False
    if item.get("supplementable"):
        return True
    code = str((item.get("error") or {}).get("code") or "")
    return code in {
        "slow_response_pending",
        "response_timeout",
        "send_button_not_found",
        "submit_unconfirmed",
        "composer_busy",
        "response_not_relevant",
        "long_prompt_still_in_input",
        "existing_answer_not_found",
        "existing_answer_placeholder",
        "existing_answer_prompt_echo",
    }


def _raw_error_label(raw: dict[str, Any]) -> str:
    error = raw.get("error") or {}
    return str(error.get("code") or "未完成")


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _float(value: Any, default: float | None) -> float | None:
    try:
        return float(value)
    except Exception:
        return default
