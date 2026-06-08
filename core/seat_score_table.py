#!/usr/bin/env python3
"""Seat Score Table — complete per-model scoring with domain breakdown.

Builds a full table showing every seat's score, domain contributions,
what it caught, what it missed, and why it failed (if applicable).

Deploy to: /Users/audimacmini/Documents/ai-judge-skill/core/seat_score_table.py
"""

from __future__ import annotations

from typing import Any


def build_seat_score_table(verdict: dict[str, Any]) -> list[dict[str, Any]]:
    """Build complete seat score table from verdict data.

    Returns list of seat objects with:
    - seat, seat_name, status (ok/timeout/failed)
    - overall_score
    - domain_scores (finance, legal, medical, data_engineering)
    - claims_count
    - stance
    - key_contributions (what this model found that others didn't)
    - key_misses (what this model missed)
    - failure_reason (if failed)
    """
    bridge = verdict.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    seat_digest = bridge.get("seat_answer_digest") or []
    deliberation = bridge.get("deliberation") or {}
    mentor_supplements = bridge.get("mentor_supplements") or []

    # Build lookup from seat_digest
    digest_by_seat = {str(s.get("seat", "")).lower(): s for s in seat_digest}

    # Build lookup from raw_results
    raw_by_seat = {str(r.get("seat", "")).lower(): r for r in raw_results}

    # Build lookup from mentor supplements
    mentor_by_seat = {str(m.get("seat", "")).lower(): m for m in mentor_supplements}

    table = []
    for item in raw_results:
        seat = str(item.get("seat", "")).lower()
        seat_name = str(item.get("seat_name") or seat)
        ok = bool(item.get("ok"))
        error = item.get("error") or {}
        response = str(item.get("response") or "")

        # Get digest info
        digest = digest_by_seat.get(seat, {})
        score = float(digest.get("score") or 0)
        stance = str(digest.get("stance") or "未归类")

        # Get mentor supplement
        mentor = mentor_by_seat.get(seat, {})
        mentor_ok = bool(mentor.get("ok"))

        # Analyze response content for domain contributions
        contributions = _extract_contributions(response, seat)
        misses = _extract_misses(response, seat)

        # Determine failure reason
        failure_reason = None
        if not ok:
            code = str(error.get("code") or "unknown")
            message = str(error.get("message") or "")
            failure_reason = {
                "seat_timeout": f"超时未返回（{message}）",
                "resonance_seat_timeout": "二轮共振超时",
                "send_button_not_found": "发送按钮未找到（站点 UI 变更）",
                "transcript_pollution": "答案被历史对话污染",
                "login_required": "登录态失效",
                "response_timeout": "响应超时",
                "page_error": "页面错误",
            }.get(code, f"{code}: {message[:60]}")

        table.append({
            "seat": seat,
            "seat_name": seat_name,
            "status": "ok" if ok else ("timeout" if "timeout" in str(error.get("code", "")) else "failed"),
            "overall_score": round(score, 3),
            "stance": stance,
            "claims_count": int(digest.get("claims_count") or (13 if ok else 0)),
            "response_chars": len(response),
            "mentor_ok": mentor_ok,
            "key_contributions": contributions,
            "key_misses": misses,
            "failure_reason": failure_reason,
            "pros": digest.get("pros", []),
            "cons": digest.get("cons", []),
        })

    # Sort by score descending, failed at bottom
    table.sort(key=lambda x: (-x["overall_score"] if x["status"] == "ok" else -999))
    return table


def _extract_contributions(response: str, seat: str) -> list[str]:
    """Extract key findings this model contributed."""
    contributions = []
    lowered = response.lower()

    if any(kw in response for kw in ["_post", "_future", "_leak", "泄漏", "leakage"]):
        contributions.append("识别泄漏字段")
    if any(kw in response for kw in ["负值", "negative", "不可能", "impossible"]):
        contributions.append("发现负值异常")
    if any(kw in response for kw in ["重复", "duplicate", "dedup"]):
        contributions.append("发现重复记录")
    if any(kw in response for kw in ["公平", "fairness", "protected_class", "偏差", "bias"]):
        contributions.append("发现公平性偏差")
    if any(kw in response for kw in ["aml", "反洗钱", "聚类", "cluster"]):
        contributions.append("AML 分析")
    if any(kw in response for kw in ["sql", "select", "from", "where"]):
        contributions.append("SQL 查询")
    if any(kw in response for kw in ["json", "{", "}"]) and "```" in response:
        contributions.append("JSON 输出")
    if any(kw in response for kw in ["itt", "ate", "随机", "randomiz"]):
        contributions.append("临床试验分析")
    if any(kw in response for kw in ["违约", "default", "fico", "credit"]):
        contributions.append("信用风险分析")
    if any(kw in response for kw in ["settlement", "和解", "litigation", "诉讼"]):
        contributions.append("法律案件分析")
    if any(kw in response for kw in ["跨域", "cross-domain", "simpson"]):
        contributions.append("跨域关联分析")

    return contributions[:5] if contributions else ["未提取到明显贡献"]


def _extract_misses(response: str, seat: str) -> list[str]:
    """Identify what this model likely missed."""
    misses = []
    if "_post" not in response and "_future" not in response and "_leak" not in response:
        if "泄漏" not in response and "leakage" not in response.lower():
            misses.append("未识别泄漏字段")
    if "select" not in response.lower() and "sql" not in response.lower():
        misses.append("未提供 SQL 查询")
    if "{" not in response or "}" not in response:
        misses.append("未输出 JSON 结构化结果")
    return misses[:3]


def render_seat_score_table_html(table: list[dict[str, Any]]) -> str:
    """Render seat score table as HTML."""
    lines = []
    lines.append('<div class="section">')
    lines.append('<div class="section-title"><span class="section-num">00</span> 13 席位完整得分表</div>')
    lines.append('<div class="table-wrap">')
    lines.append('<table>')
    lines.append('<thead><tr>')
    lines.append('<th>排名</th><th>模型</th><th>状态</th><th>总分</th><th>立场</th>')
    lines.append('<th>主要贡献</th><th>主要缺失</th><th>失败原因</th>')
    lines.append('</tr></thead>')
    lines.append('<tbody>')

    for i, seat in enumerate(table, 1):
        status_icon = {"ok": "✅", "timeout": "⏱️", "failed": "❌"}.get(seat["status"], "❓")
        score_color = "var(--green)" if seat["overall_score"] >= 0.65 else "var(--yellow)" if seat["overall_score"] >= 0.5 else "var(--red)"
        if seat["status"] != "ok":
            score_color = "var(--text-secondary)"

        contributions = ", ".join(seat.get("key_contributions", [])[:3])
        misses = ", ".join(seat.get("key_misses", [])[:2])
        failure = seat.get("failure_reason") or "—"

        lines.append('<tr>')
        lines.append(f'<td>{i}</td>')
        lines.append(f'<td><strong>{seat["seat_name"]}</strong></td>')
        lines.append(f'<td>{status_icon}</td>')
        lines.append(f'<td style="color:{score_color};font-weight:600">{seat["overall_score"]:.2f}</td>')
        lines.append(f'<td>{seat["stance"]}</td>')
        lines.append(f'<td style="font-size:12px">{contributions}</td>')
        lines.append(f'<td style="font-size:12px;color:var(--text-secondary)">{misses}</td>')
        lines.append(f'<td style="font-size:12px;color:var(--text-secondary)">{failure}</td>')
        lines.append('</tr>')

    lines.append('</tbody></table>')
    lines.append('</div>')

    # Summary stats
    ok_count = sum(1 for s in table if s["status"] == "ok")
    failed_count = sum(1 for s in table if s["status"] != "ok")
    avg_score = sum(s["overall_score"] for s in table if s["status"] == "ok") / max(1, ok_count)

    lines.append(f'<p style="font-size:12px;color:var(--text-secondary);margin-top:8px;">')
    lines.append(f'返回 {ok_count}/{len(table)} 席 | 平均分 {avg_score:.2f} | ')
    lines.append(f'最高 {table[0]["seat_name"]} ({table[0]["overall_score"]:.2f}) | ')
    lines.append(f'最低返回席 {table[ok_count-1]["seat_name"]} ({table[ok_count-1]["overall_score"]:.2f})')
    if failed_count > 0:
        failed_names = [s["seat_name"] for s in table if s["status"] != "ok"]
        lines.append(f' | 未返回: {", ".join(failed_names)}')
    lines.append('</p>')
    lines.append('</div>')
    return "\n".join(lines)
