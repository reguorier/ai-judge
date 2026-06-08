#!/usr/bin/env python3
"""Executive Summary module — traffic-light, no-jargon, business-language layer.

Produces a one-page summary that non-technical stakeholders can read:
- Traffic light indicators (green/yellow/red) for each dimension
- Plain language explanations (no ATE, ITT, CV, FICO jargon)
- "If you ignore this" consequence statements
- Top 3 priority actions with owner and deadline

Apply to: core/final_report.py (import and call)
Deploy to: /Users/audimacmini/Documents/ai-judge-skill/core/executive_summary.py
"""

from __future__ import annotations

from typing import Any


# --- Traffic light thresholds ---
def _traffic_light(score: float) -> str:
    """Convert 0-10 score to traffic light."""
    if score >= 7:
        return "green"
    if score >= 4:
        return "yellow"
    return "red"


def _traffic_emoji(light: str) -> str:
    return {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(light, "⚪")


def _traffic_label(light: str) -> str:
    return {"green": "安全", "yellow": "注意", "red": "紧急"}.get(light, "未知")


# --- Jargon translator ---
JARGON_MAP = {
    "ATE": "治疗效果差异",
    "ITT": "全部患者分析（不管有没有坚持治疗）",
    "PP": "坚持治疗的患者分析",
    "CV": "价格波动幅度",
    "FICO": "信用评分",
    "AML": "反洗钱",
    "SAR": "可疑交易报告",
    "VaR": "最大可能亏损",
    "CVaR": "极端情况亏损",
    "ETL": "数据搬运管道",
    "Simpson's Paradox": "分组看结论相反的统计陷阱",
    "leakage": "用了不该用的未来信息",
    "data leakage": "数据泄漏（用了未来的数据训练现在的模型）",
    "protected class": "受法律保护的人群类别",
    "fairness audit": "公平性检查",
    "adversarial debiasing": "用对抗方法消除偏见",
    "equalized odds": "确保不同群体获得相同待遇",
    "power of attorney": "授权委托书",
    "privilege": "律师-客户保密特权",
    "sepsis": "脓毒症（严重感染引发的全身反应）",
    "troponin": "心肌损伤指标",
    "creatinine": "肾功能指标",
    "HbA1c": "血糖控制指标（近3个月平均血糖）",
    "opioid": "阿片类止痛药",
    "benzodiazepine": "安定类药物",
}


def translate_jargon(text: str) -> str:
    """Replace technical jargon with plain language."""
    result = text
    for eng, chn in JARGON_MAP.items():
        result = result.replace(eng, f"{eng}（{chn}）")
    return result


# --- Executive Summary Builder ---
def build_executive_summary(
    verdict: dict[str, Any],
    data_audit: dict[str, Any] | None = None,
    domain_scores: dict[str, float] | None = None,
    findings: list[dict[str, Any]] | None = None,
    priority_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a non-technical executive summary with traffic lights.

    Returns a dict with:
    - headline: one-sentence verdict in plain language
    - traffic_lights: per-dimension green/yellow/red
    - consequences: "if you ignore this" statements
    - top_actions: top 3 priority actions
    - seat_summary: which models agreed, which disagreed
    """

    # Default domain scores from data audit
    if domain_scores is None:
        domain_scores = _infer_domain_scores(verdict, data_audit)

    traffic_lights = {}
    for domain, score in domain_scores.items():
        light = _traffic_light(score)
        traffic_lights[domain] = {
            "score": round(score, 1),
            "light": light,
            "emoji": _traffic_emoji(light),
            "label": _traffic_label(light),
        }

    # Build headline
    overall_score = sum(domain_scores.values()) / max(1, len(domain_scores))
    overall_light = _traffic_light(overall_score)
    headline = _build_headline(overall_light, traffic_lights)

    # Build consequences
    consequences = _build_consequences(traffic_lights, data_audit, findings)

    # Build top actions
    if priority_actions is None:
        priority_actions = _infer_priority_actions(traffic_lights, data_audit)
    top_actions = priority_actions[:3]

    # Build seat summary
    seat_summary = _build_seat_summary(verdict)

    return {
        "schema": "executive_summary.v1",
        "headline": headline,
        "overall_traffic_light": overall_light,
        "overall_score": round(overall_score, 1),
        "traffic_lights": traffic_lights,
        "consequences": consequences,
        "top_actions": top_actions,
        "seat_summary": seat_summary,
        "readability_note": "本摘要为非技术管理层编写，所有专业术语已翻译为日常用语。",
    }


def _build_headline(overall_light: str, traffic_lights: dict[str, Any]) -> str:
    """Build a one-sentence headline in plain language."""
    red_domains = [d for d, v in traffic_lights.items() if v["light"] == "red"]
    yellow_domains = [d for d, v in traffic_lights.items() if v["light"] == "yellow"]

    if overall_light == "red":
        return f"⚠️ 数据存在严重问题，不能直接使用。{', '.join(red_domains)} 领域需要紧急修复。"
    if overall_light == "yellow":
        return f"⚡ 数据基本可用但有风险。{', '.join(yellow_domains)} 领域需要修复后再用。"
    return "✅ 数据质量良好，可以进入下一步分析。"


def _infer_domain_scores(
    verdict: dict[str, Any],
    data_audit: dict[str, Any] | None,
) -> dict[str, float]:
    """Infer domain scores from verdict data."""
    scores = {}

    # Data quality score
    dq = float(verdict.get("data_quality_score") or 5.0)
    scores["数据质量"] = dq

    # Infer from web_bridge results
    bridge = verdict.get("web_bridge") or {}
    ok_count = int(bridge.get("ok_count") or 0)
    total = int(bridge.get("requested_count") or 1)
    coverage_score = min(10, ok_count / max(1, total) * 10)
    scores["席位覆盖"] = coverage_score

    # From confidence
    conf = float(verdict.get("confidence") or 0) * 10
    scores["结论可信度"] = min(10, conf)

    # From data audit if available
    if data_audit:
        leakage = int(data_audit.get("leakage_columns") or 0)
        scores["数据安全"] = max(0, 10 - leakage * 0.7)
        anomalies = int(data_audit.get("anomalies") or 0)
        scores["异常控制"] = max(0, 10 - anomalies * 0.4)

    return scores


def _build_consequences(
    traffic_lights: dict[str, Any],
    data_audit: dict[str, Any] | None,
    findings: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Build 'if you ignore this' consequence statements."""
    consequences = []

    for domain, info in traffic_lights.items():
        if info["light"] == "red":
            consequences.append({
                "domain": domain,
                "severity": "red",
                "consequence": _consequence_for_red(domain, data_audit),
            })
        elif info["light"] == "yellow":
            consequences.append({
                "domain": domain,
                "severity": "yellow",
                "consequence": _consequence_for_yellow(domain, data_audit),
            })

    return consequences


def _consequence_for_red(domain: str, data_audit: dict[str, Any] | None) -> str:
    """Generate consequence statement for red-light domain."""
    mapping = {
        "数据质量": "如果直接使用脏数据训练模型，模型上线后预测结果会出错，可能导致错误的业务决策（如批准不该批的贷款、漏诊高风险患者）。",
        "数据安全": "如果用泄漏了未来信息的数据训练模型，模型在测试环境表现很好，上线后完全失效——这等于用考试答案来证明学生学得好。",
        "席位覆盖": "评审席位不完整意味着结论可能有偏差。就像法庭缺了法官，判决不能生效。",
        "结论可信度": "当前结论的可信度不够高，不建议作为重大决策的唯一依据。",
        "异常控制": "大量异常数据未处理，说明数据管道有系统性问题，修好之前不建议继续分析。",
    }
    return mapping.get(domain, f"{domain} 存在严重问题，不修复就继续使用会带来不可预见的风险。")


def _consequence_for_yellow(domain: str, data_audit: dict[str, Any] | None) -> str:
    mapping = {
        "数据质量": "部分数据有小问题（如少量缺失值），短期内可以使用但应尽快修复。",
        "数据安全": "存在潜在的数据使用风险，建议在建模前确认没有使用不该用的字段。",
        "席位覆盖": "大部分评审席位已返回结果，少量缺失不影响大局，但最好补全。",
        "结论可信度": "结论基本可信，但在做重大决策前建议再验证关键假设。",
        "异常控制": "有一些异常数据需要关注，但数量不多，不影响整体分析。",
    }
    return mapping.get(domain, f"{domain} 有需要注意的地方，建议在使用前做进一步检查。")


def _infer_priority_actions(
    traffic_lights: dict[str, Any],
    data_audit: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Infer top priority actions from traffic lights."""
    actions = []
    reds = [(d, v) for d, v in traffic_lights.items() if v["light"] == "red"]
    yellows = [(d, v) for d, v in traffic_lights.items() if v["light"] == "yellow"]

    for domain, info in reds:
        actions.append({
            "priority": "P0",
            "action": f"修复 {domain} 问题（当前评分 {info['score']}/10）",
            "owner": "数据工程团队",
            "deadline": "本周内",
            "consequence": _consequence_for_red(domain, data_audit),
        })

    for domain, info in yellows[:2]:
        actions.append({
            "priority": "P1",
            "action": f"改善 {domain}（当前评分 {info['score']}/10）",
            "owner": "分析团队",
            "deadline": "两周内",
            "consequence": _consequence_for_yellow(domain, data_audit),
        })

    return actions[:3]


def _build_seat_summary(verdict: dict[str, Any]) -> dict[str, Any]:
    """Build a plain-language summary of which models agreed/disagreed."""
    bridge = verdict.get("web_bridge") or {}
    seat_digest = bridge.get("seat_answer_digest") or []
    deliberation = bridge.get("deliberation") or {}
    stance_dist = deliberation.get("stance_distribution") or {}

    ok_seats = [s for s in seat_digest if s.get("ok")]
    failed_seats = [s for s in seat_digest if not s.get("ok")]

    # Stance translation
    stance_cn = {
        "支持/推进": "看好",
        "反对/谨慎": "有顾虑",
        "条件/待验证": "有条件支持",
        "中性/信息型": "中立",
    }

    stance_summary = {}
    for stance, count in stance_dist.items():
        stance_summary[stance_cn.get(stance, stance)] = count

    top_3 = sorted(ok_seats, key=lambda s: float(s.get("score") or 0), reverse=True)[:3]

    return {
        "total_seats": len(seat_digest),
        "responded": len(ok_seats),
        "failed": len(failed_seats),
        "stance_distribution": stance_summary,
        "top_models": [
            {"name": s.get("seat_name"), "score": round(float(s.get("score") or 0), 2)}
            for s in top_3
        ],
        "consensus_level": "高度一致" if len(stance_dist) <= 2 else "有分歧但主流意见明确" if len(stance_dist) <= 3 else "意见分歧较大",
    }


# --- HTML Renderer ---
def render_executive_summary_html(summary: dict[str, Any]) -> str:
    """Render executive summary as HTML for inclusion in reports."""
    lines = []
    lines.append('<div class="executive-summary" style="background:#f8fafc;border:2px solid #1a1a2e;border-radius:12px;padding:24px;margin-bottom:32px;">')
    lines.append(f'<h2 style="font-size:18px;margin-bottom:16px;">📋 管理层摘要</h2>')
    lines.append(f'<p style="font-size:16px;font-weight:600;margin-bottom:16px;">{summary["headline"]}</p>')

    # Traffic lights
    lines.append('<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;">')
    for domain, info in summary.get("traffic_lights", {}).items():
        bg = {"green": "#dcfce7", "yellow": "#fef9c3", "red": "#fee2e2"}[info["light"]]
        lines.append(f'<div style="background:{bg};border-radius:8px;padding:12px 16px;min-width:120px;text-align:center;">')
        lines.append(f'<div style="font-size:24px;">{info["emoji"]}</div>')
        lines.append(f'<div style="font-size:13px;font-weight:600;">{domain}</div>')
        lines.append(f'<div style="font-size:12px;color:#5a6072;">{info["score"]}/10 · {info["label"]}</div>')
        lines.append('</div>')
    lines.append('</div>')

    # Consequences
    consequences = summary.get("consequences", [])
    if consequences:
        lines.append('<h3 style="font-size:14px;margin-bottom:8px;">⚠️ 如果不修复会怎样</h3>')
        for c in consequences:
            icon = "🔴" if c["severity"] == "red" else "🟡"
            lines.append(f'<p style="font-size:13px;margin-bottom:6px;">{icon} <strong>{c["domain"]}</strong>：{c["consequence"]}</p>')

    # Top actions
    actions = summary.get("top_actions", [])
    if actions:
        lines.append('<h3 style="font-size:14px;margin:16px 0 8px;">🎯 最重要的三件事</h3>')
        for i, a in enumerate(actions, 1):
            lines.append(f'<p style="font-size:13px;margin-bottom:4px;"><strong>{i}. [{a["priority"]}]</strong> {a["action"]} — 负责人: {a["owner"]}，期限: {a["deadline"]}</p>')

    # Seat summary
    seats = summary.get("seat_summary", {})
    if seats:
        lines.append(f'<p style="font-size:12px;color:#5a6072;margin-top:12px;">')
        lines.append(f'评审席位：{seats.get("responded", 0)}/{seats.get("total_seats", 0)} 个模型返回结果，共识程度：{seats.get("consensus_level", "未知")}')
        top = seats.get("top_models", [])
        if top:
            names = ", ".join(f'{m["name"]}({m["score"]})' for m in top)
            lines.append(f'。评分最高：{names}')
        lines.append('</p>')

    lines.append(f'<p style="font-size:11px;color:#9ca3af;margin-top:8px;">{summary.get("readability_note", "")}</p>')
    lines.append('</div>')
    return "\n".join(lines)
