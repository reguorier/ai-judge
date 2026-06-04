#!/usr/bin/env python3
"""World Cup prediction-pool report generation.

This module is intentionally scoped to the worldcup_pool product mode. It writes
round reports and a small report index without changing normal jury or werewolf
flows.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.worldcup_pool import ACCOUNT_LEDGER, leaderboard_rows, worldcup_pool_seats


REPORT_SCHEMA = "ai_judge.worldcup_pool.report.v1"
ARTIFACT_NAMES = {
    "json": "worldcup_pool_report.json",
    "markdown": "worldcup_pool_report.md",
    "html": "worldcup_pool_report.html",
    "pdf": "worldcup_pool_report.pdf",
}
PLATFORM_LIMITED_ADAPTER_SEATS: set[str] = set()
REPORT_FORMAT_STANDARD: dict[str, Any] = {
    "source": "/Users/audimacmini/Documents/AI-Pool-Report-Format-Standard.md",
    "single_source_of_truth": "json",
    "scope": "worldcup_pool_only",
    "section_order": [
        "Cover",
        "Match Result",
        "Council Assessment",
        "Seat-by-Seat Review",
        "Strategy Matrix",
        "Key Lessons",
        "Outlook",
        "Footer",
    ],
    "page": {"size": "A4", "margin_cm": {"top": 1.6, "right": 1.5, "bottom": 1.6, "left": 1.5}},
    "typography": {
        "report_title_px": 28,
        "section_header_px": 15,
        "sub_header_px": 12,
        "body_px": 10.5,
        "table_header_px": 9,
        "table_cell_px": 10,
        "badge_px": 8,
        "score_px": 22,
        "gp_monospace_px": 11,
        "footer_px": 9,
    },
    "palette": {
        "light_background": "#ffffff",
        "light_panel": "#fafbfc",
        "text": "#1a1a2e",
        "secondary": "#57606a",
        "accent_gold": "#F0883E",
        "green": "#3FB950",
        "red": "#F85149",
        "blue": "#58A6FF",
        "border": "#d0d7de",
        "dark_background": "#0d1117",
        "dark_text": "#e6edf3",
    },
    "tier_rules": {
        "badge-a": "+200 GP or more",
        "badge-b": "+100 to +150 GP",
        "badge-c": "No participation",
        "badge-d": "-150 GP or more",
    },
    "rules": [
        "Every report must follow sections 0-7 exactly.",
        "Every seat must render as a card block with Strategy, Hit/Miss, Edge/Problem, Takeaway.",
        "Strategy Matrix must be a single table and include tier badges.",
        "Key Lessons must be a numbered 01-06 two-column grid in HTML and paired rows in PDF.",
        "GP values use monospace and positive/negative value coloring in HTML/PDF.",
        "N/A values render as em dash.",
    ],
}


def write_worldcup_pool_report(
    run_id: str,
    verdict: dict[str, Any],
    runs_dir: Path,
    reports_dir: Path,
) -> dict[str, Any] | None:
    """Write report artifacts for a persisted worldcup_pool run."""
    state = verdict.get("worldcup_pool")
    if not isinstance(state, dict):
        return None
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    trace = _load_trace(run_dir / "trace.json")
    report = build_worldcup_pool_report(run_id, verdict, trace)

    json_path = run_dir / ARTIFACT_NAMES["json"]
    md_path = run_dir / ARTIFACT_NAMES["markdown"]
    html_path = run_dir / ARTIFACT_NAMES["html"]
    pdf_path = run_dir / ARTIFACT_NAMES["pdf"]

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(report["markdown"], encoding="utf-8")
    html_path.write_text(report["html"], encoding="utf-8")
    pdf_ok = _render_pdf_with_helper(json_path, pdf_path)

    manifest = {
        "schema": REPORT_SCHEMA,
        "run_id": run_id,
        "report_id": report["report_id"],
        "title": report["title"],
        "generated_at": report["generated_at"],
        "source_run_created_at": report["source_run_created_at"],
        "state_updated_at": report["state_updated_at"],
        "counts": report["counts"],
        "failed_seats": report["failed_seats"],
        "adapter_seats": report["adapter_seats"],
        "artifacts": {
            "json": f"/api/worldcup-pool/report/{run_id}/json",
            "markdown": f"/api/worldcup-pool/report/{run_id}/markdown",
            "html": f"/api/worldcup-pool/report/{run_id}/html",
            "pdf": f"/api/worldcup-pool/report/{run_id}/pdf" if pdf_ok else None,
        },
    }
    verdict["worldcup_pool_report"] = manifest
    _update_report_index(reports_dir / "index.json", manifest)
    return manifest


def build_worldcup_pool_report(
    run_id: str,
    verdict: dict[str, Any],
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = verdict.get("worldcup_pool") if isinstance(verdict, dict) else {}
    state = state if isinstance(state, dict) else {}
    generated_at = datetime.now(timezone.utc).isoformat()
    title = "AI 预测池 · 全量赛事预测与分析报告"
    report_id = f"RPT-WORLDCUP-POOL-{_date_compact(generated_at)}-{run_id}"
    active_seats = set(worldcup_pool_seats())
    player_results = [
        p for p in state.get("player_results") or []
        if isinstance(p, dict) and str(p.get("seat") or "").lower() in active_seats
    ]
    raw_results = [
        r for r in (verdict.get("web_bridge") or {}).get("raw_results") or []
        if isinstance(r, dict) and str(r.get("seat") or "").lower() in active_seats
    ]
    raw_by_seat = {str(r.get("seat") or "").lower(): r for r in raw_results}
    seat_times = _seat_timeline(trace or {})
    failed_seats = [p.get("seat") for p in player_results if not p.get("ok")]
    adapter_seats = []
    for p in player_results:
        seat = str(p.get("seat") or "").lower()
        raw = raw_by_seat.get(seat, {})
        if (
            p.get("platform_limited")
            or p.get("status") == "platform_limited_adapter"
            or raw.get("platform_limited")
            or raw.get("method") == "worldcup_pool_platform_limited_adapter"
            or seat in PLATFORM_LIMITED_ADAPTER_SEATS
        ):
            adapter_seats.append(seat)
    counts = {
        "players": len(player_results),
        "ok": sum(1 for p in player_results if p.get("ok")),
        "failed": sum(1 for p in player_results if not p.get("ok")),
        "sources": len(_filter_rows_by_seat(state.get("source_board") or [], active_seats)),
        "resonance": len(_filter_rows_by_seat(state.get("resonance_board") or [], active_seats)),
        "product_feedback": len(_filter_rows_by_seat(state.get("product_feedback") or [], active_seats)),
    }
    sections = _build_sections(run_id, verdict, state, player_results, raw_by_seat, seat_times)
    markdown = _render_markdown(title, report_id, verdict, state, counts, failed_seats, adapter_seats, sections)
    html_text = _render_html(title, markdown, report_id)
    return {
        "schema": REPORT_SCHEMA,
        "report_id": report_id,
        "run_id": run_id,
        "title": title,
        "generated_at": generated_at,
        "source_run_created_at": verdict.get("created_at"),
        "state_updated_at": state.get("updated_at"),
        "counts": counts,
        "failed_seats": failed_seats,
        "adapter_seats": adapter_seats,
        "sections": sections,
        "format_standard": REPORT_FORMAT_STANDARD,
        "markdown": markdown,
        "html": html_text,
    }


def _build_sections(
    run_id: str,
    verdict: dict[str, Any],
    state: dict[str, Any],
    player_results: list[dict[str, Any]],
    raw_by_seat: dict[str, dict[str, Any]],
    seat_times: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    active_seats = set(worldcup_pool_seats())
    leaderboard = leaderboard_rows()
    source_board = _sanitize_removed_seat_text(_filter_rows_by_seat(state.get("source_board") or [], active_seats))
    resonance_board = _sanitize_removed_seat_text(_filter_rows_by_seat(state.get("resonance_board") or [], active_seats))
    product_feedback = _sanitize_removed_seat_text(_filter_rows_by_seat(state.get("product_feedback") or [], active_seats))
    player_sections = []
    for player in player_results:
        seat = str(player.get("seat") or "").lower()
        account = ACCOUNT_LEDGER.get(seat, {})
        receipt = player.get("receipt") if isinstance(player.get("receipt"), dict) else {}
        raw = raw_by_seat.get(seat, {})
        platform_limited = (
            bool(player.get("platform_limited"))
            or player.get("status") == "platform_limited_adapter"
            or raw.get("platform_limited")
            or raw.get("method") == "worldcup_pool_platform_limited_adapter"
            or seat in PLATFORM_LIMITED_ADAPTER_SEATS
        )
        status = "透明适配" if platform_limited else ("失败" if not player.get("ok") else "已提交")
        player_sections.append({
            "seat": seat,
            "seat_name": account.get("display") or player.get("seat_name") or seat,
            "rank": account.get("rank") or player.get("rank"),
            "current_gp": account.get("gp") or player.get("current_gp"),
            "status": status,
            "ok": bool(player.get("ok")),
            "method": player.get("method") or raw.get("method"),
            "platform_limited": platform_limited,
            "adapter_note": _sanitize_removed_seat_text(player.get("adapter_note") or raw.get("adapter_note")),
            "error": player.get("error") or raw.get("error"),
            "url": raw.get("url"),
            "elapsed_seconds": raw.get("elapsed_seconds"),
            "timeline": seat_times.get(seat, {}),
            "loan_decision": _sanitize_removed_seat_text(receipt.get("loan_decision") or receipt.get("risk_credit_decision") or "未结构化"),
            "bets": _sanitize_removed_seat_text(receipt.get("bets") or receipt.get("forecast_entries") or []),
            "sources": _sanitize_removed_seat_text(receipt.get("source_log") or []),
            "opponent_reads": _sanitize_removed_seat_text(receipt.get("opponent_reads") or []),
            "product_feedback": _sanitize_removed_seat_text(receipt.get("product_feedback") or []),
            "sections": _sanitize_removed_seat_text(player.get("sections") or {}),
            "response": _sanitize_removed_seat_text(player.get("response") or raw.get("response") or ""),
        })
    base_sections = {
        "round_context": {
            "run_id": run_id,
            "round_label": state.get("round_label"),
            "upcoming_events": state.get("upcoming_events") or [],
            "game_rules": state.get("game_rules") or [],
            "separation": state.get("separation") or {},
            "view_url": state.get("view_url") or verdict.get("view_url"),
        },
        "leaderboard": leaderboard,
        "players": player_sections,
        "source_board": source_board,
        "resonance_board": resonance_board,
        "product_feedback": product_feedback,
        "audit": _build_audit(player_sections),
    }
    base_sections["format_sections"] = _build_format_sections(run_id, verdict, state, base_sections)
    return base_sections


def _build_format_sections(
    run_id: str,
    verdict: dict[str, Any],
    state: dict[str, Any],
    sections: dict[str, Any],
) -> dict[str, Any]:
    players = sections.get("players") or []
    seat_cards = [_seat_review_card(player) for player in players]
    tier_counts: dict[str, int] = {}
    for card in seat_cards:
        tier_counts[card["tier"]] = tier_counts.get(card["tier"], 0) + 1
    structured_count = sum(1 for card in seat_cards if card["structured_bets"])
    real_completed = sum(1 for card in seat_cards if card["real_warmup_bets"])
    adapter_count = sum(1 for card in seat_cards if card["status"] == "透明适配")
    failed_count = sum(1 for card in seat_cards if card["status"] == "失败")
    missing = [card["seat_name"] for card in seat_cards if not card["real_warmup_bets"]]
    match_result = {
        "match": "PSG vs Arsenal",
        "venue": "UEFA Champions League Final",
        "result_90min": "PSG 1-1 Arsenal",
        "extra_time": "No additional scoring recorded in pool ledger",
        "penalties": "PSG 4-3 Arsenal",
        "champion": "PSG",
        "hitting_markets": [
            {"market": "Champion", "hit": "PSG", "status": "hit"},
            {"market": "Under 2.5", "hit": "1-1 after 90min", "status": "hit"},
            {"market": "Draw protection", "hit": "90min draw", "status": "hit"},
            {"market": "Arsenal win", "hit": "miss", "status": "miss"},
        ],
    }
    return {
        "cover": {
            "title": "AI 预测池赛事报告",
            "subtitle": "欧冠决赛结算 + 2026 世界杯赛前热身赛投注审计",
            "match_info": "PSG vs Arsenal · PSG 1-1 Arsenal (4-3p) · PSG champion",
            "metadata": {
                "date": _fmt_time(verdict.get("created_at") or state.get("updated_at")),
                "venue": "UEFA Champions League Final / Pre-World Cup Warm-up Window",
                "run_id": run_id,
                "seats": len(players),
            },
        },
        "match_result": match_result,
        "council_assessment": {
            "consensus_vs_reality": [
                {"item": "PSG champion path", "consensus": "主流席位倾向 PSG 冠军/不败", "reality": "PSG 点球夺冠", "verdict": "命中"},
                {"item": "Low-scoring path", "consensus": "DeepSeek/MiMo/Claude 倾向低比分保护", "reality": "90 分钟 1-1", "verdict": "命中"},
                {"item": "Arsenal upset", "consensus": "Grok/Kimi 等底部席位偏反打", "reality": "阿森纳未夺冠", "verdict": "失败"},
                {"item": "Warm-up coverage", "consensus": f"{real_completed}/14 席完成真实热身赛结构化投注", "reality": "未达到全员投注", "verdict": "待补"},
            ],
            "scoring_distribution": [
                {"tier": tier, "count": tier_counts.get(tier, 0)}
                for tier in ["Tier A", "Tier B", "Tier C", "Tier D"]
            ],
            "key_finding": (
                f"欧冠结算已完成，但世界杯开赛前热身赛投注没有全员完成："
                f"{real_completed}/14 席拥有真实结构化热身赛投注，{adapter_count} 席是透明适配，"
                f"{failed_count} 席失败，缺口席位为 {', '.join(missing) if missing else '无'}。"
            ),
        },
        "seat_reviews": seat_cards,
        "strategy_matrix": [_strategy_matrix_row(card) for card in seat_cards],
        "key_lessons": [
            {"num": "01", "title": "低比分路径比热门胜负更稳", "body": "冠军盘与小球/平局保护组合贡献了本轮最高质量收益。"},
            {"num": "02", "title": "结构化投注比长文重要", "body": "没有 bets 字段的席位即使有分析，也无法进入可回溯结算链。"},
            {"num": "03", "title": "贷款应服务覆盖率", "body": "不限额度贷款后，关键不是借多少，而是能否转化成多场可验证仓位。"},
            {"num": "04", "title": "适配席位不能冒充预测", "body": "透明适配只保留流程、信源和产品反馈，不计作真实模型投注。"},
            {"num": "05", "title": "热身赛要每日评分", "body": "6月1日至10日窗口适合用每日 ROI、有效投注数和信源质量拉开排行。"},
            {"num": "06", "title": "信源时间戳是资产", "body": "官方赛程、伤停、首发、天气和赔率变化必须标注检索时间。"},
        ],
        "outlook": {
            "capital_landscape": [
                {"seat": row.get("seat_name"), "rank": row.get("rank"), "gp": row.get("gp"), "loan": row.get("loan_advice")}
                for row in sections.get("leaderboard") or []
            ],
            "warmup_audit": {
                "fixture_window": "2026-06-01 至 2026-06-10",
                "source": "FIFA · Every nation's pre-FIFA World Cup 2026 warm-up matches · checked 2026-06-01",
                "real_completed": real_completed,
                "structured_count": structured_count,
                "missing_or_non_real": missing,
            },
            "strategy_guidance": (
                "下一轮必须让 14 席全部围绕热身赛窗口提交结构化 bets。贷款不设额度上限；"
                "破产贷款参考 20%/轮，投资贷款参考 10%/轮。日报榜按净 GP、ROI、有效投注数、"
                "可验证信源质量和排名提升综合评分。"
            ),
        },
        "footer": {
            "report_id": "",
            "run_id": run_id,
            "disclaimer": "This report is a simulated prediction-pool artifact, not financial or betting advice.",
        },
    }


def _seat_review_card(player: dict[str, Any]) -> dict[str, Any]:
    current_gp = _to_int(player.get("current_gp"), 0)
    change = current_gp - 1000
    structured_bets = _has_structured_bets(player)
    real_warmup_bets = _has_real_warmup_bets(player)
    tier = _seat_tier(player, change, structured_bets, real_warmup_bets)
    return {
        "seat": player.get("seat"),
        "seat_name": player.get("seat_name") or player.get("seat"),
        "rank": player.get("rank"),
        "current_gp": current_gp,
        "change_gp": change,
        "score": _seat_score(player, change, structured_bets, real_warmup_bets),
        "tier": tier,
        "badge_class": {"Tier A": "badge-a", "Tier B": "badge-b", "Tier C": "badge-c", "Tier D": "badge-d"}.get(tier, "badge-c"),
        "status": player.get("status") or "未知",
        "structured_bets": structured_bets,
        "real_warmup_bets": real_warmup_bets,
        "strategy": _seat_strategy(player),
        "hit_miss": _seat_hit_miss(player, structured_bets, real_warmup_bets),
        "edge_problem": _seat_edge_problem(player),
        "takeaway": _seat_takeaway(player, structured_bets, real_warmup_bets),
        "loan_decision": player.get("loan_decision"),
    }


def _strategy_matrix_row(card: dict[str, Any]) -> dict[str, Any]:
    if card["status"] == "失败":
        strategy_type = "Bridge Recovery"
        best_for = "补跑和登录修复"
    elif not card["real_warmup_bets"]:
        strategy_type = "Completion Gap"
        best_for = "补齐结构化 bets"
    elif card["change_gp"] >= 200:
        strategy_type = "Capital Leader"
        best_for = "多场分散守榜"
    elif card["change_gp"] < 0:
        strategy_type = "Comeback Loan"
        best_for = "破产/追赶贷款"
    else:
        strategy_type = "Balanced Growth"
        best_for = "投资贷款扩张"
    return {
        "strategy_type": strategy_type,
        "seat": card["seat_name"],
        "tier": card["tier"],
        "return": f"{card['change_gp']:+d} GP",
        "score": f"{card['score']:.1f}/10",
        "best_for": best_for,
    }


def _seat_tier(player: dict[str, Any], change: int, structured_bets: bool, real_warmup_bets: bool) -> str:
    if not player.get("ok") or not structured_bets or not real_warmup_bets:
        return "Tier C"
    if change >= 200:
        return "Tier A"
    if 100 <= change <= 150:
        return "Tier B"
    if change <= -150:
        return "Tier D"
    return "Tier C"


def _seat_score(player: dict[str, Any], change: int, structured_bets: bool, real_warmup_bets: bool) -> float:
    if not player.get("ok"):
        return 0.0
    score = 5.0 + max(min(change / 220, 3.0), -3.0)
    if structured_bets:
        score += 0.8
    if real_warmup_bets:
        score += 0.9
    if player.get("platform_limited"):
        score = min(score, 4.0)
    return round(max(0.0, min(10.0, score)), 1)


def _has_structured_bets(player: dict[str, Any]) -> bool:
    bets = player.get("bets") or []
    return any(isinstance(bet, dict) and (bet.get("event") or bet.get("match") or bet.get("stake_gp")) for bet in bets)


def _has_real_warmup_bets(player: dict[str, Any]) -> bool:
    if player.get("platform_limited") or player.get("status") == "透明适配":
        return False
    for bet in player.get("bets") or []:
        if not isinstance(bet, dict):
            continue
        text = " ".join(str(bet.get(key) or "") for key in ("event", "match", "observation_item", "market", "prediction_item"))
        if re.search(r"热身|友谊|friendly|2026-06-0[1-9]|2026-06-10|6月[1-9]日|6月10日", text, re.I):
            return True
    return False


def _seat_strategy(player: dict[str, Any]) -> str:
    bets = player.get("bets") or []
    if player.get("status") == "失败":
        return "桥接失败，尚未形成可结算策略。"
    if not _has_structured_bets(player):
        return "有文字分析但缺少结构化 bets，不能进入自动结算。"
    first = bets[0] if isinstance(bets[0], dict) else {}
    return _one_line(first.get("event") or first.get("observation_item") or "多场赛事组合", 80)


def _seat_hit_miss(player: dict[str, Any], structured_bets: bool, real_warmup_bets: bool) -> str:
    if player.get("status") == "失败":
        return "未提交，待补跑。"
    if player.get("platform_limited"):
        return "透明适配，仅保留观察项，不计真实投注。"
    if real_warmup_bets:
        return "已覆盖热身赛结构化投注，等待赛后结算。"
    if structured_bets:
        return "有结构化投注，但热身赛覆盖不足。"
    return "未提交结构化投注。"


def _seat_edge_problem(player: dict[str, Any]) -> str:
    if player.get("error"):
        return _one_line(player.get("error"), 120)
    if player.get("platform_limited"):
        return "平台/桥接限制，需要与真实网页预测分开展示。"
    sources = player.get("sources") or []
    if sources:
        return f"已提交 {len(sources)} 条信源，但仍需检查时间戳和可复核性。"
    return "缺少可复核信源或结构化字段。"


def _seat_takeaway(player: dict[str, Any], structured_bets: bool, real_warmup_bets: bool) -> str:
    if real_warmup_bets:
        return "保留原仓位并在赛前 2 小时用首发/伤停/赔率变化复核。"
    if structured_bets:
        return "补足 6/1-6/10 热身赛覆盖范围，并写清放弃其它赛事的理由。"
    return "下一轮必须输出 JSON bets、贷款类型、贷款金额、利率和 daily_score_plan。"


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _render_markdown(
    title: str,
    report_id: str,
    verdict: dict[str, Any],
    state: dict[str, Any],
    counts: dict[str, int],
    failed_seats: list[str],
    adapter_seats: list[str],
    sections: dict[str, Any],
) -> str:
    fmt = sections.get("format_sections") or {}
    cover = fmt.get("cover") or {}
    match = fmt.get("match_result") or {}
    council = fmt.get("council_assessment") or {}
    outlook = fmt.get("outlook") or {}
    lines: list[str] = []
    lines.append("CONFIDENTIAL · INTERNAL USE ONLY")
    lines.append("")
    lines.append(f"# {cover.get('title') or title}")
    lines.append("")
    lines.append(f"**{cover.get('subtitle') or 'AI Prediction Pool Report'}**")
    lines.append("")
    meta = cover.get("metadata") or {}
    lines.append("| 项目 | 结果 |")
    lines.append("| --- | --- |")
    lines.append(f"| Match Info | {cover.get('match_info') or '—'} |")
    lines.append(f"| Date | {meta.get('date') or '—'} |")
    lines.append(f"| Venue | {meta.get('venue') or '—'} |")
    lines.append(f"| Report ID | {report_id} |")
    lines.append(f"| Run ID | {sections['round_context']['run_id']} |")
    lines.append(f"| Seats | {meta.get('seats') or counts['players']} |")
    lines.append(f"| Result URL | {sections['round_context'].get('view_url') or '—'} |")
    lines.append("")
    lines.append("<div class=\"page-break\"></div>")
    lines.append("")
    lines.append("## 1. Match Result")
    lines.append("")
    lines.append("| Score Card | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| 90min | {match.get('result_90min') or '—'} |")
    lines.append(f"| ET | {match.get('extra_time') or '—'} |")
    lines.append(f"| Penalties | {match.get('penalties') or '—'} |")
    lines.append(f"| Champion | {match.get('champion') or '—'} |")
    lines.append("")
    lines.append("| Market | Hit | Status |")
    lines.append("| --- | --- | --- |")
    for row in match.get("hitting_markets") or []:
        lines.append(f"| {row.get('market') or '—'} | {row.get('hit') or '—'} | {row.get('status') or '—'} |")
    lines.append("")
    lines.append("## 2. Council Assessment")
    lines.append("")
    lines.append("| Item | Consensus | Reality | Verdict |")
    lines.append("| --- | --- | --- | --- |")
    for row in council.get("consensus_vs_reality") or []:
        lines.append(f"| {row.get('item')} | {_one_line(row.get('consensus'), 90)} | {_one_line(row.get('reality'), 90)} | {row.get('verdict')} |")
    lines.append("")
    lines.append("| Tier | Count |")
    lines.append("| --- | ---: |")
    for row in council.get("scoring_distribution") or []:
        lines.append(f"| {row.get('tier')} | {row.get('count')} |")
    lines.append("")
    lines.append("> **KEY FINDING**: " + _one_line(council.get("key_finding"), 360))
    lines.append("")
    lines.append("## 3. Seat-by-Seat Review")
    for card in fmt.get("seat_reviews") or []:
        change = f"{card.get('change_gp', 0):+d}"
        lines.append("")
        lines.append(f"### {card.get('seat_name')} — `{card.get('current_gp')} GP` (`{change}`)    `{card.get('score')}/10` · {card.get('tier')}")
        lines.append("")
        lines.append(f"**Strategy**: {_one_line(card.get('strategy'), 180)}")
        lines.append("")
        lines.append(f"**Hit/Miss**: {_one_line(card.get('hit_miss'), 180)}")
        lines.append("")
        lines.append(f"**Edge/Problem**: {_one_line(card.get('edge_problem'), 180)}")
        lines.append("")
        lines.append(f"**Takeaway**: {_one_line(card.get('takeaway'), 180)}")
    lines.append("")
    lines.append("## 4. Strategy Matrix")
    lines.append("")
    lines.append("| Strategy Type | Seat | Tier | Return | Score | Best For |")
    lines.append("| --- | --- | --- | ---: | --- | --- |")
    for row in fmt.get("strategy_matrix") or []:
        lines.append(f"| {row.get('strategy_type')} | {row.get('seat')} | {row.get('tier')} | {row.get('return')} | {row.get('score')} | {row.get('best_for')} |")
    lines.append("")
    lines.append("## 5. Key Lessons")
    lines.append("")
    for lesson in fmt.get("key_lessons") or []:
        lines.append(f"**{lesson.get('num')} · {lesson.get('title')}**")
        lines.append("")
        lines.append(str(lesson.get("body") or ""))
        lines.append("")
    lines.append("## 6. Outlook")
    lines.append("")
    lines.append("| Rank | Seat | GP | Loan Guidance |")
    lines.append("| --- | --- | ---: | --- |")
    for row in outlook.get("capital_landscape") or []:
        lines.append(f"| #{row.get('rank')} | {row.get('seat')} | {row.get('gp')} | {_one_line(row.get('loan'), 120)} |")
    lines.append("")
    audit = outlook.get("warmup_audit") or {}
    lines.append("| Warm-up Audit | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Fixture Window | {audit.get('fixture_window') or '—'} |")
    lines.append(f"| Source | {audit.get('source') or '—'} |")
    lines.append(f"| Real Completed | {audit.get('real_completed')} / 13 |")
    lines.append(f"| Structured Count | {audit.get('structured_count')} / 13 |")
    lines.append(f"| Missing / Non-real | {', '.join(audit.get('missing_or_non_real') or []) or '—'} |")
    lines.append("")
    lines.append("> **STRATEGY GUIDANCE**: " + _one_line(outlook.get("strategy_guidance"), 420))
    lines.append("")
    lines.append("## 7. Footer")
    lines.append("")
    lines.append(f"Report ID: {report_id}")
    lines.append("")
    lines.append(f"Run ID: {sections['round_context']['run_id']}")
    lines.append("")
    lines.append("Disclaimer: This report is a simulated prediction-pool artifact, not financial or betting advice.")
    return "\n".join(lines) + "\n"


def _render_player_markdown(player: dict[str, Any]) -> list[str]:
    lines = [
        "",
        f"### {player.get('seat_name')} · #{player.get('rank')} · {player.get('current_gp')}GP · {player.get('status')}",
        "",
        f"- 提交时间：{_fmt_time((player.get('timeline') or {}).get('submit_at'))}",
        f"- 收集/失败时间：{_fmt_time((player.get('timeline') or {}).get('finish_at'))}",
        f"- 网页 URL：{player.get('url') or 'N/A'}",
        f"- 桥接耗时：{player.get('elapsed_seconds') if player.get('elapsed_seconds') is not None else 'N/A'} 秒",
        f"- 贷款/额度：{_one_line(player.get('loan_decision'), 220)}",
    ]
    if player.get("platform_limited"):
        lines.append(f"- 适配说明：{player.get('adapter_note') or '平台限制透明适配；非真实网页预测。'}")
    if player.get("error"):
        lines.append(f"- 错误：`{_one_line(player.get('error'), 240)}`")
    bets = player.get("bets") or []
    if bets:
        lines.append("")
        lines.append("| 赛事/观察项 | 市场/预测项 | GP/PTS | 置信度 | 信息源 | 撤销/降权条件 |")
        lines.append("| --- | --- | ---: | --- | --- | --- |")
        for bet in bets:
            if isinstance(bet, dict):
                event = bet.get("event") or bet.get("observation_item") or bet.get("match") or "N/A"
                market = bet.get("market") or bet.get("prediction_item") or bet.get("variables") or "N/A"
                stake = bet.get("stake_gp") or bet.get("allocated_pts") or bet.get("stake") or "N/A"
                confidence = bet.get("confidence") or "N/A"
                sources = bet.get("sources") or bet.get("sources_needed") or []
                cancel = bet.get("reduce_or_cancel_if") or "N/A"
                lines.append(f"| {_one_line(event, 80)} | {_one_line(market, 100)} | {stake} | {confidence} | {_one_line(sources, 120)} | {_one_line(cancel, 120)} |")
    else:
        section_e = _first_section(player, "E.")
        if section_e:
            lines.append("")
            lines.append("预测/观察计划摘录：")
            lines.append(_block(section_e))
    if player.get("sources"):
        lines.append("")
        lines.append("信源记录：")
        for source in player["sources"]:
            lines.append(f"- {_one_line(source, 220)}")
    raw_response = str(player.get("response") or "")
    if raw_response:
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>完整原始回答</summary>")
        lines.append("")
        lines.append(_block(raw_response))
        lines.append("")
        lines.append("</details>")
    return lines


def _render_html(title: str, markdown: str, report_id: str) -> str:
    body = _markdownish_to_html(markdown)
    body = _wrap_seat_cards(body)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · {html.escape(report_id)}</title>
  <style>
    :root{{--bg:#ffffff;--panel:#fafbfc;--text:#1a1a2e;--secondary:#57606a;--gold:#F0883E;--green:#3FB950;--red:#F85149;--blue:#58A6FF;--border:#d0d7de;--dark:#0d1117;--dark-text:#e6edf3}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",Arial,sans-serif;margin:0;background:#f3f4f6;color:var(--text);line-height:1.58}}
    main{{max-width:980px;margin:0 auto;padding:40px 34px 78px;background:var(--bg);min-height:100vh}}
    h1{{font-size:28px;line-height:1.2;margin:10px 0 18px;font-weight:700;color:#0d1117;letter-spacing:0}}
    h2{{font-size:15px;line-height:1.35;margin:34px 0 14px;border-bottom:2px solid var(--gold);padding-bottom:7px;font-weight:700;color:#0d1117}}
    h3{{font-size:12px;line-height:1.45;margin:18px 0 8px;color:#24292f;font-weight:700}}
    p{{font-size:10.5px;margin:6px 0;color:var(--text)}}
    table{{width:100%;border-collapse:collapse;margin:12px 0 20px;font-size:10px;page-break-inside:avoid}}
    th,td{{border:1px solid var(--border);padding:7px 8px;vertical-align:top}} th{{background:#f6f8fa;text-align:left;font-size:9px;font-weight:700;text-transform:uppercase;color:#24292f}} tbody tr:nth-child(even) td{{background:#fafbfc}} td.num,th.num{{text-align:right;font-family:"SF Mono",Menlo,Consolas,monospace;font-weight:800}}
    code,pre{{font-family:"SF Mono",Menlo,Consolas,monospace}} pre{{white-space:pre-wrap;background:#F9FAFB;border:1px solid var(--border);border-radius:6px;padding:12px;overflow:auto;font-size:12px}}
    details{{border:1px solid var(--border);border-radius:6px;padding:10px 12px;margin:10px 0;background:#fff;page-break-inside:avoid}} summary{{cursor:pointer;font-weight:700}}
    .conf{{font-size:9px;letter-spacing:.08em;color:var(--secondary);font-weight:700;text-transform:uppercase;border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:10px}}
    .key-finding{{background:#fff8f0;border-left:3px solid var(--gold);padding:11px 13px;margin:13px 0 18px;font-size:10.5px;color:var(--text);page-break-inside:avoid}}
    .seat-card{{border:1px solid var(--border);border-radius:7px;background:#fff;padding:12px 14px;margin:10px 0 14px;page-break-inside:avoid}}
    .seat-card h3{{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:0 0 8px;padding-bottom:8px;border-bottom:1px solid var(--border)}}
    .seat-card code{{font-size:11px;font-weight:800}}
    .tier-a{{border-left:4px solid var(--green)}}.tier-b{{border-left:4px solid var(--blue)}}.tier-c{{border-left:4px solid #8b949e}}.tier-d{{border-left:4px solid var(--red)}}
    .lesson-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:12px 0}}
    .page-break{{page-break-after:always}}
    @media print{{@page{{size:A4;margin:1.6cm 1.5cm}}body{{background:#fff}}main{{box-shadow:none;padding:0}}thead{{display:table-header-group}}tr,details,.seat-card{{page-break-inside:avoid}}}}
  </style>
</head>
<body><main>{body}</main></body></html>"""


def _markdownish_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    in_pre = False
    table_lines: list[str] = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            out.append(_table_lines_to_html(table_lines))
            table_lines = []

    for line in lines:
        if not in_pre and line.startswith("|"):
            table_lines.append(line)
            continue
        flush_table()
        if line == "CONFIDENTIAL · INTERNAL USE ONLY":
            out.append(f"<div class='conf'>{html.escape(line)}</div>")
        elif line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("```"):
            out.append("<pre>" if not in_pre else "</pre>")
            in_pre = not in_pre
        elif in_pre:
            out.append(html.escape(line))
        elif line.startswith("- "):
            out.append(f"<p>• {_inline_md(line[2:])}</p>")
        elif re.match(r"^\d+\. ", line):
            out.append(f"<p>{_inline_md(line)}</p>")
        elif line.startswith("&nbsp;"):
            out.append(line)
        elif line.startswith("> "):
            out.append(f"<div class='key-finding'>{_inline_md(line[2:])}</div>")
        elif (
            line.startswith("<details>")
            or line.startswith("</details>")
            or line.startswith("<summary>")
            or line.startswith("</summary>")
            or line.startswith("<div")
            or line.startswith("</div>")
        ):
            out.append(line)
        elif line.strip():
            out.append(f"<p>{_inline_md(line)}</p>")
        else:
            out.append("")
    flush_table()
    if in_pre:
        out.append("</pre>")
    return "\n".join(out)


def _wrap_seat_cards(body: str) -> str:
    pattern = re.compile(r"(<h3>(?P<title>[^<]*? — .*?Tier (?P<tier>[ABCD])[^<]*?)</h3>(?P<content>.*?))(?=<h3>|<h2>|$)", re.S)

    def repl(match: re.Match[str]) -> str:
        tier = match.group("tier").lower()
        return f"<section class='seat-card tier-{tier}'>{match.group(1)}</section>"

    return pattern.sub(repl, body)


def _table_lines_to_html(lines: list[str]) -> str:
    rows = [_split_table_row(line) for line in lines if line.strip().startswith("|")]
    rows = [row for row in rows if row]
    if not rows:
        return ""
    aligns: list[str] = []
    if len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in rows[1]):
        aligns = ["num" if cell.strip().endswith(":") else "" for cell in rows[1]]
        body_rows = rows[2:]
    else:
        body_rows = rows[1:]
    header = rows[0]
    html_rows = ["<table><thead><tr>"]
    for idx, cell in enumerate(header):
        cls = " class='num'" if idx < len(aligns) and aligns[idx] == "num" else ""
        html_rows.append(f"<th{cls}>{_inline_md(cell.strip())}</th>")
    html_rows.append("</tr></thead><tbody>")
    for row in body_rows:
        html_rows.append("<tr>")
        for idx, cell in enumerate(row):
            cls = " class='num'" if idx < len(aligns) and aligns[idx] == "num" else ""
            html_rows.append(f"<td{cls}>{_inline_md(cell.strip())}</td>")
        html_rows.append("</tr>")
    html_rows.append("</tbody></table>")
    return "".join(html_rows)


def _split_table_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip() for cell in text.split("|")]


def _inline_md(text: Any) -> str:
    escaped = html.escape(str(text or ""))
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return escaped


def _render_pdf_with_helper(report_json_path: Path, pdf_path: Path) -> bool:
    helper = Path(__file__).resolve().parent.parent / "tools" / "render_worldcup_pool_pdf.py"
    python_candidates = [
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
        Path("/usr/bin/python3"),
    ]
    for python in python_candidates:
        if not python.exists() or not helper.exists():
            continue
        try:
            completed = subprocess.run(
                [str(python), str(helper), str(report_json_path), str(pdf_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=90,
                check=False,
            )
        except Exception:
            continue
        if completed.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 1000:
            return True
    return False


def _load_trace(trace_path: Path) -> dict[str, Any]:
    if not trace_path.exists():
        return {}
    try:
        data = json.loads(trace_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _seat_timeline(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    timelines: dict[str, dict[str, Any]] = {}
    for event in trace.get("events") or []:
        if not isinstance(event, dict):
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        seat = str(data.get("seat") or "").lower()
        if not seat:
            continue
        row = timelines.setdefault(seat, {"events": []})
        action = str(event.get("action") or "")
        at = event.get("at")
        row["events"].append({"at": at, "action": action, "detail": event.get("detail")})
        if "submit_start" in action:
            row.setdefault("submit_at", at)
        if "collected" in action or "answer" in action or "failed" in action:
            row["finish_at"] = at
    return timelines


def _build_audit(players: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for player in players:
        seat_name = str(player.get("seat_name") or player.get("seat") or "")
        if player.get("seat") == "chatgpt" and player.get("error"):
            rows.append({
                "seat_name": seat_name,
                "finding": "ChatGPT 本轮不是模型拒答，而是桥接提交失败；根因是旧选择器曾命中 input[type=file] 文件上传框。后续代码已排除文件输入框；若页面显示会话过期，需要重新登录后补跑。",
            })
        elif player.get("platform_limited"):
            rows.append({
                "seat_name": seat_name,
                "finding": "该席位为透明适配结果，只记录账本、信源规则和产品反馈，不代表真实网页模型预测，不应用于胜负/仓位准确率统计。",
            })
    if not rows:
        rows.append({"seat_name": "系统", "finding": "未发现桥接失败或透明适配席位。"})
    return rows


def _filter_rows_by_seat(rows: list[Any], active_seats: set[str]) -> list[Any]:
    filtered = []
    for row in rows:
        if not isinstance(row, dict):
            filtered.append(row)
            continue
        seat = str(row.get("seat") or "").lower()
        if not seat or seat in active_seats:
            filtered.append(row)
    return filtered


def _sanitize_removed_seat_text(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return [_sanitize_removed_seat_text(item) for item in value]
    if isinstance(value, dict):
        return {_sanitize_removed_seat_text(key): _sanitize_removed_seat_text(val) for key, val in value.items()}
    return value


def _update_report_index(index_path: Path, manifest: dict[str, Any]) -> None:
    try:
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"schema": REPORT_SCHEMA, "reports": []}
    except Exception:
        index = {"schema": REPORT_SCHEMA, "reports": []}
    reports = [r for r in index.get("reports", []) if isinstance(r, dict) and r.get("run_id") != manifest.get("run_id")]
    reports.insert(0, manifest)
    index["schema"] = REPORT_SCHEMA
    index["updated_at"] = datetime.now(timezone.utc).isoformat()
    index["reports"] = reports[:200]
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _source_text_and_time(source: Any) -> tuple[str, str | None]:
    if isinstance(source, dict):
        time_value = source.get("time") or source.get("date") or source.get("timestamp")
        text = json.dumps(source, ensure_ascii=False)
        return text, str(time_value) if time_value else None
    return str(source), _find_time(str(source))


def _find_time(text: str) -> str | None:
    match = re.search(r"20\d{2}[-./年]\d{1,2}[-./月]\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?", text)
    return match.group(0) if match else None


def _first_section(player: dict[str, Any], prefix: str) -> str:
    for key, value in (player.get("sections") or {}).items():
        if str(key).startswith(prefix):
            return str(value)
    return ""


def _block(text: Any) -> str:
    return "```\n" + str(text).strip() + "\n```"


def _one_line(value: Any, limit: int = 120) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value or "")
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _fmt_time(value: Any) -> str:
    if not value:
        return "N/A"
    return str(value)


def _date_compact(value: str) -> str:
    return re.sub(r"\D", "", value)[:14] or "unknown"
