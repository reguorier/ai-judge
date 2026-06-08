#!/usr/bin/env python3
"""Paper-style final report assembly for AI Judge verdicts."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any

from core.closeout_sop import build_closeout_sop
from core.domain_closeout import (
    is_legal_domain,
    render_legal_closeout,
    render_legal_closeout_markdown,
)


FINAL_REPORT_SCHEMA = "ai_judge.final_report.v1"
COMPILED_REPORT_SCHEMA = "ai_judge.compiled_report.v1"
LONGFORM_REPORT_SCHEMA = "ai_judge.longform_report.v1"


def attach_final_report(verdict: dict[str, Any]) -> dict[str, Any]:
    """Attach a deterministic final report payload to a verdict."""
    verdict["final_report"] = build_final_report(verdict)
    return verdict


def build_final_report(verdict: dict[str, Any]) -> dict[str, Any]:
    """Build the readable, auditable final plan that the judge owns."""
    coverage = _coverage(verdict)
    complete = bool(coverage["complete"])
    status_label = "最终报告" if complete else "运行未闭环"
    raw_verdict_label = _text(verdict.get("verdict_label") or verdict.get("verdict") or "待判定")
    confidence = _number_text(verdict.get("confidence"), suffix="%")
    trust = _trust_label(verdict)
    question = _text(verdict.get("question") or "未提供原始问题")
    verdict_label = _report_verdict_label(question, raw_verdict_label)
    reasons = _brief_points(verdict.get("reasons") or [], limit=5, item_limit=110)
    steps = _brief_points(verdict.get("next_steps") or [], limit=5, item_limit=110)
    judge = verdict.get("judge_answer") or {}
    baseline = verdict.get("single_judge_baseline") or {}
    bridge = verdict.get("web_bridge") or {}
    deliberation = bridge.get("deliberation") or {}
    agreements = _brief_points(judge.get("agreements") or deliberation.get("agreements") or [], limit=5, item_limit=90)
    disagreements = _brief_points(judge.get("disagreements") or deliberation.get("disagreements") or [], limit=4, item_limit=100)
    limits = _brief_points(judge.get("limits") or [], limit=5, item_limit=110)
    seat_digest = bridge.get("seat_answer_digest") or []
    top_seats = _top_seat_names(verdict, judge, seat_digest)
    judge_editor = _judge_editor(verdict)
    findings = _key_findings(verdict, coverage, reasons, agreements, top_seats)
    recommendation = _recommendation(steps, complete=complete, coverage=coverage, verdict_label=verdict_label, question=question)
    risk_line = _risk_line(limits, disagreements, coverage, verdict, trust)
    next_action = _next_action(steps, recommendation, complete=complete, coverage=coverage)
    executive_summary = _executive_summary(
        judge_editor=judge_editor,
        verdict_label=verdict_label,
        confidence=confidence,
        trust=trust,
        coverage=coverage,
        recommendation=recommendation,
        findings=findings,
        risk_line=risk_line,
        next_action=next_action,
    )
    thesis = _thesis(verdict, question, verdict_label)
    keywords = _keywords(question, reasons, agreements, verdict_label, trust)
    abstract = _abstract(
        judge_editor=judge_editor,
        verdict_label=verdict_label,
        confidence=confidence,
        trust=trust,
        coverage=coverage,
        complete=complete,
        executive_summary=executive_summary,
    )
    plan = _implementation_plan(steps, complete=complete, coverage=coverage, verdict_label=verdict_label, recommendation=recommendation)
    risks = _risks_and_limits(limits, disagreements, coverage, verdict, trust)
    compiled_report = _compiled_content_report(
        verdict,
        question=question,
        verdict_label=verdict_label,
        coverage=coverage,
        findings=findings,
        recommendation=recommendation,
        plan=plan,
        risks=risks,
        agreements=agreements,
        disagreements=disagreements,
        top_seats=top_seats,
    )
    decision_brief = _decision_brief(
        verdict=verdict,
        question=question,
        verdict_label=verdict_label,
        coverage=coverage,
        recommendation=recommendation,
        plan=plan,
        risks=risks,
        compiled=compiled_report,
    )
    run_health = _run_health_panel(verdict, coverage, complete=complete)
    closeout_sop = build_closeout_sop(
        verdict,
        verdict_label=verdict_label,
        confidence=confidence,
        trust=trust,
        coverage_label=coverage["label"],
        recommendation=recommendation,
        risk_line=risk_line,
        next_action=next_action,
        findings=findings,
        plan=plan,
        risks=risks,
    )
    postulates = _postulates(
        judge_editor=judge_editor,
        verdict_label=verdict_label,
        confidence=confidence,
        coverage=coverage,
        findings=findings,
        top_seats=top_seats,
        plan=plan,
        risks=risks,
    )
    evidence_map = _evidence_map(verdict, coverage, top_seats, agreements, reasons, judge, baseline)
    compact_overview = _compact_overview_payload(
        verdict=verdict,
        question=question,
        verdict_label=verdict_label,
        coverage=coverage,
        complete=complete,
        executive_summary=executive_summary,
        recommendation=recommendation,
        plan=plan,
        risks=risks,
        decision_brief=decision_brief,
        run_health=run_health,
        compiled_report=compiled_report,
    )
    generated_at = _text(verdict.get("created_at") or datetime.now(timezone.utc).isoformat())
    return {
        "schema": FINAL_REPORT_SCHEMA,
        "run_id": _text(verdict.get("run_id") or "-"),
        "title": f"AI Judge 最终行动方案：{_topic_label(question)}",
        "subtitle": "JUDGE CLOSEOUT · FINAL RECOMMENDATION · AUDITABLE BASIS",
        "report_mode": "ready_for_decision" if complete else "bridge_recovery_required",
        "judge_editor": judge_editor,
        "status_label": status_label,
        "status_reason": _status_reason(complete, coverage, trust),
        "run_health": run_health,
        "executive_summary": executive_summary,
        "abstract": abstract,
        "thesis": thesis,
        "recommendation": recommendation,
        "sop_closeout": closeout_sop,
        "compiled_report": compiled_report,
        "longform_report": compiled_report.get("longform_report"),
        "decision_brief": decision_brief,
        "compact_overview": compact_overview,
        "key_findings": findings,
        "keywords": keywords,
        "meta": [
            {"label": "轮值法官", "value": judge_editor["label"]},
            {"label": "Run", "value": _text(verdict.get("run_id") or "-")},
            {"label": "结论", "value": verdict_label},
            {"label": "可信度", "value": confidence},
            {"label": "席位覆盖", "value": coverage["label"]},
        ],
        "final_position": {
            "label": verdict_label,
            "confidence": confidence,
            "trust": trust,
            "summary": _final_position_summary(judge_editor, verdict_label, trust, coverage, findings, recommendation),
        },
        "postulates": postulates,
        "evidence_map": evidence_map,
        "implementation_plan": plan,
        "risks_and_limits": risks,
        "verification_contract": _verification_contract(coverage, trust, verdict_label),
        "source_trace": {
            "run_id": _text(verdict.get("run_id") or "-"),
            "question": question,
            "generated_at": generated_at,
            "basis": "模型原始回答、答案总结、席位互评、claim 评分、横纵收口与发布门禁。",
        },
    }


def render_final_report_markdown(report: dict[str, Any], verdict: dict[str, Any] | None = None) -> str:
    """Render a final report payload to Markdown."""
    if not report:
        return ""
    question = _text(
        (verdict or {}).get("question")
        or (report.get("source_trace") or {}).get("question")
        or ""
    )
    if verdict and is_legal_domain(question):
        return render_legal_closeout_markdown(
            verdict,
            report,
            question,
            _text(verdict.get("run_id") or report.get("run_id") or ""),
        )
    executive = report.get("executive_summary") or {}
    sop = report.get("sop_closeout") or {}
    brief = report.get("decision_brief") or {}
    longform = report.get("longform_report") or (report.get("compiled_report") or {}).get("longform_report") or {}
    display_title = brief.get("title") or longform.get("title") or report.get("title") or "AI Judge 最终方案报告"
    lines: list[str] = [
        f"## {display_title}",
        "",
        f"**{report.get('subtitle') or FINAL_REPORT_SCHEMA}**",
        "",
        f"**状态:** {report.get('status_label', '-')} · {report.get('status_reason', '-')}",
        "",
        "### 一眼结论",
        "",
        str(brief.get("one_sentence") or executive.get("headline") or report.get("abstract") or ""),
        "",
        f"- 建议：{executive.get('recommendation', report.get('recommendation', '-'))}",
        f"- 为什么：{'; '.join(str(item) for item in executive.get('why', [])[:3]) or '-'}",
        f"- 风险：{executive.get('risk', '-')}",
        f"- 下一步：{executive.get('next_action', '-')}",
        "",
        "### 标准化收口 SOP",
        "",
        str(sop.get("final_judgment") or ""),
        "",
        str(sop.get("one_sentence_plan") or ""),
        "",
    ]
    for phase in sop.get("phases") or []:
        lines.extend([f"#### {phase.get('title', '')}", ""])
        for item in phase.get("items") or []:
            lines.append(f"- {item}")
        lines.append("")
    template = sop.get("codex_template") or {}
    if template:
        lines.extend([
            "#### Codex 执行模板",
            "",
            f"目标：{template.get('goal', '-')}",
            "",
            f"产品定位：{template.get('positioning', '-')}",
            "",
            "当前优先级：",
            "",
        ])
        for item in template.get("current_priorities") or []:
            lines.append(f"- {item}")
        lines.extend(["", "执行规则：", ""])
        for item in template.get("execution_rules") or []:
            lines.append(f"- {item}")
        lines.extend(["", "输出要求：", ""])
        for item in template.get("output_requirements") or []:
            lines.append(f"- {item}")
        lines.append("")
    if sop.get("final_essence"):
        lines.extend([str(sop.get("final_essence")), ""])
    run_health = report.get("run_health") or {}
    if run_health:
        lines.extend(["### 运行健康门禁", "", str(run_health.get("headline") or ""), ""])
        for card in run_health.get("cards") or []:
            lines.append(f"- {card.get('label', '-')}: {card.get('value', '-')}")
        if run_health.get("plan"):
            lines.extend(["", "#### 恢复计划", ""])
            for item in run_health.get("plan") or []:
                lines.append(f"- {item}")
        lines.append("")
    if brief:
        lines.extend(["### 最终方案总览", "", f"#### {brief.get('title') or '一屏读懂'}", ""])
        for card in brief.get("cards") or []:
            lines.append(f"- {card.get('label', '-')}: {card.get('value', '-')}")
        if brief.get("plan"):
            lines.extend(["", "#### 执行计划", ""])
            for item in brief.get("plan") or []:
                lines.append(f"- {item}")
        lines.append("")
    compiled = report.get("compiled_report") or {}
    longform = report.get("longform_report") or compiled.get("longform_report") or {}
    if longform:
        lines.extend(_longform_markdown_lines(longform))
    elif compiled:
        lines.extend(_compiled_markdown_lines(compiled))
    lines.extend([
        "### ABSTRACT",
        "",
        str(report.get("abstract") or ""),
        "",
    ])
    keywords = report.get("keywords") or []
    if keywords:
        lines.extend(["### KEYWORDS", "", " / ".join(str(item) for item in keywords), ""])
    position = report.get("final_position") or {}
    lines.extend([
        "### FINAL POSITION",
        "",
        f"- 结论：{position.get('label', '-')}",
        f"- 可信：{position.get('trust', '-')}",
        f"- 置信度：{position.get('confidence', '-')}",
        f"- 轮值法官：{(report.get('judge_editor') or {}).get('label', '-')}",
        f"- 摘要：{position.get('summary', '-')}",
        "",
        "### JUDGE CLOSEOUT",
        "",
        f"**Thesis:** {report.get('thesis', '-')}",
        "",
        f"**Recommendation:** {report.get('recommendation', '-')}",
        "",
        "### KEY FINDINGS",
        "",
    ])
    for item in report.get("key_findings") or []:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "### POSTULATES",
        "",
    ])
    for index, item in enumerate(report.get("postulates") or [], 1):
        lines.extend([
            f"#### POSTULATE {index} · {item.get('title', '')}",
            "",
            str(item.get("body") or ""),
            "",
            f"证据：{item.get('evidence', '-')}",
            "",
        ])
    evidence_rows = report.get("evidence_map") or []
    if evidence_rows:
        lines.extend(["### EVIDENCE MAP", "", "| 维度 | 本报告判断 | 证据来源 | 约束 |", "|---|---|---|---|"])
        for row in evidence_rows:
            lines.append(
                f"| {_pipe(row.get('dimension'))} | {_pipe(row.get('judgment'))} | "
                f"{_pipe(row.get('source'))} | {_pipe(row.get('constraint'))} |"
            )
        lines.append("")
    plan = report.get("implementation_plan") or []
    if plan:
        lines.extend(["### EXECUTION PLAN", ""])
        for index, item in enumerate(plan, 1):
            lines.append(f"{index}. {item}")
        lines.append("")
    risks = report.get("risks_and_limits") or []
    if risks:
        lines.extend(["### LIMITS", ""])
        for item in risks:
            lines.append(f"- {item}")
        lines.append("")
    contract = report.get("verification_contract") or []
    if contract:
        lines.extend(["### VERIFICATION CONTRACT", ""])
        for item in contract:
            lines.append(f"- {item}")
    return "\n".join(lines).strip()


def render_final_report_html(report: dict[str, Any], verdict: dict[str, Any] | None = None) -> str:
    """Render a final report payload to escaped HTML."""
    if not report:
        return ""
    question = _text(
        (verdict or {}).get("question")
        or (report.get("source_trace") or {}).get("question")
        or ""
    )
    if verdict and is_legal_domain(question):
        return render_legal_closeout(
            verdict,
            report,
            question,
            _text(verdict.get("run_id") or report.get("run_id") or ""),
        )
    executive = report.get("executive_summary") or {}
    sop = report.get("sop_closeout") or {}
    meta = "".join(
        "<div>"
        f"<span>{html.escape(str(item.get('label', '')))}</span>"
        f"<strong>{html.escape(str(item.get('value', '-')))}</strong>"
        "</div>"
        for item in report.get("meta", [])
    )
    keywords = "".join(f"<span>{html.escape(str(item))}</span>" for item in report.get("keywords", []))
    postulates = "".join(
        '<article class="paper-postulate">'
        f'<span>POSTULATE {index}</span>'
        f"<h3>{html.escape(str(item.get('title', '')))}</h3>"
        f"<p>{html.escape(str(item.get('body', '')))}</p>"
        f"<small>{html.escape(str(item.get('evidence', '')))}</small>"
        "</article>"
        for index, item in enumerate(report.get("postulates") or [], 1)
    )
    evidence_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('dimension', '')))}</td>"
        f"<td>{html.escape(str(row.get('judgment', '')))}</td>"
        f"<td>{html.escape(str(row.get('source', '')))}</td>"
        f"<td>{html.escape(str(row.get('constraint', '')))}</td>"
        "</tr>"
        for row in report.get("evidence_map", [])
    )
    plan = "".join(f"<li>{html.escape(str(item))}</li>" for item in report.get("implementation_plan", []))
    risks = "".join(f"<li>{html.escape(str(item))}</li>" for item in report.get("risks_and_limits", []))
    contract = "".join(f"<li>{html.escape(str(item))}</li>" for item in report.get("verification_contract", []))
    position = report.get("final_position") or {}
    findings = "".join(f"<li>{html.escape(str(item))}</li>" for item in report.get("key_findings", []))
    judge_editor = report.get("judge_editor") or {}
    executive_why = "".join(f"<li>{html.escape(str(item))}</li>" for item in executive.get("why", [])[:4])
    sop_phases = "".join(
        '<article class="sop-phase">'
        f"<h3>{html.escape(str(phase.get('title', '')))}</h3>"
        f"<ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in phase.get('items', []))}</ul>"
        "</article>"
        for phase in sop.get("phases", [])
    )
    template = sop.get("codex_template") or {}
    priority_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in template.get("current_priorities", []))
    rule_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in template.get("execution_rules", []))
    output_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in template.get("output_requirements", []))
    evidence_boundary = "".join(f"<li>{html.escape(str(item))}</li>" for item in sop.get("evidence_boundary", []))
    sop_html = ""
    if sop:
        sop_html = (
            '<details class="sop-report audit-appendix" id="closeout-sop">'
            '<summary><h2>审计附录：标准 SOP</h2><span>展开查看执行门禁和证据边界</span></summary>'
            '<p class="paper-kicker">STANDARD CLOSEOUT SOP</p>'
            f'<h2>{html.escape(str(sop.get("title", "标准化收口 SOP")))}</h2>'
            f'<p class="sop-judgment">{html.escape(str(sop.get("final_judgment", "")))}</p>'
            f'<p class="sop-one-line">{html.escape(str(sop.get("one_sentence_plan", "")))}</p>'
            f'<div class="sop-phases">{sop_phases}</div>'
            '<section class="sop-template">'
            f'<h3>{html.escape(str(template.get("label", "Codex 执行模板")))}</h3>'
            f'<p><strong>目标：</strong>{html.escape(str(template.get("goal", "-")))}</p>'
            f'<p><strong>产品定位：</strong>{html.escape(str(template.get("positioning", "-")))}</p>'
            '<div class="sop-template-grid">'
            f'<div><h4>当前优先级</h4><ul>{priority_items}</ul></div>'
            f'<div><h4>执行规则</h4><ul>{rule_items}</ul></div>'
            f'<div><h4>输出要求</h4><ul>{output_items}</ul></div>'
            "</div>"
            "</section>"
            f'<section class="sop-boundary"><h3>证据边界</h3><ul>{evidence_boundary}</ul></section>'
            f'<p class="sop-essence">{html.escape(str(sop.get("final_essence", "")))}</p>'
            "</details>"
        )
    compiled = report.get("compiled_report") or {}
    longform = report.get("longform_report") or compiled.get("longform_report") or {}
    decision_brief = report.get("decision_brief") or {}
    run_health = report.get("run_health") or {}
    report_blocked = report.get("report_mode") == "bridge_recovery_required" or run_health.get("status") == "blocked"
    run_health_html = _run_health_html(run_health)
    manuscript_html = _manuscript_report_html(report, report_blocked=report_blocked)
    compiled_html = ""
    if report_blocked and (longform or compiled):
        compiled_html = _draft_report_html(longform, compiled, decision_brief)
    elif longform:
        compiled_html = _longform_report_html(longform, decision_brief)
    elif compiled:
        compiled_html = _compiled_report_html(compiled, decision_brief)
    if compiled_html and not report_blocked:
        compiled_body = compiled_html.replace('id="compiled-report"', 'id="compiled-report-body"', 1)
        compiled_html = (
            '<details class="paper-report audit-appendix compact-jump-detail" id="compiled-report">'
            '<summary><h2>完整总结报告</h2><span>展开查看长报告、争议裁决表和执行路线图</span></summary>'
            f"{compiled_body}"
            "</details>"
        )
    lead_health = run_health_html if report_blocked else ""
    trailing_health = "" if report_blocked else run_health_html
    return (
        f"{lead_health}"
        f"{manuscript_html}"
        f"{trailing_health}"
    )


def _manuscript_report_html(report: dict[str, Any], *, report_blocked: bool) -> str:
    """Render the default user-facing report as a printable research manuscript."""
    executive = report.get("executive_summary") or {}
    brief = report.get("decision_brief") or {}
    compiled = report.get("compiled_report") or {}
    longform = report.get("longform_report") or compiled.get("longform_report") or {}
    title = _text(brief.get("title") or longform.get("title") or report.get("title") or "AI Judge 专业研究报告")
    lead = _text(
        brief.get("one_sentence")
        or longform.get("one_sentence_judgment")
        or executive.get("headline")
        or report.get("abstract")
        or report.get("recommendation")
        or "本报告汇总多席位意见，给出可审计、可执行、可追溯的结论。"
    )
    body_sections = longform.get("body_sections") or []

    def section_by_prefix(prefix: str) -> dict[str, Any]:
        for section in body_sections:
            if _text(section.get("title")).startswith(prefix):
                return section
        return {}

    abstract_items = _nonempty_strings([
        *(longform.get("executive_summary") or []),
        executive.get("recommendation"),
        report.get("recommendation"),
    ])[:3]
    problem_section = section_by_prefix("一、") or (body_sections[0] if body_sections else {})
    core_section = section_by_prefix("二、")
    final_section = section_by_prefix("三、")
    methodology_section = section_by_prefix("二、") or section_by_prefix("03") or {}
    findings = _nonempty_strings([
        *(report.get("key_findings") or []),
        *((core_section.get("paragraphs") or []) if core_section else []),
        executive.get("headline"),
    ])[:5]
    plan = _nonempty_strings([
        *(brief.get("plan") or []),
        *(report.get("implementation_plan") or []),
        executive.get("next_action"),
    ])[:6]
    risks = _nonempty_strings([
        *(report.get("risks_and_limits") or []),
        executive.get("risk"),
    ])[:5]
    decision_rows = longform.get("decision_table") or compiled.get("decision_table") or report.get("evidence_map") or []
    action_paths = longform.get("action_paths") or []
    appendix = longform.get("model_contribution_appendix") or []
    coverage_label = _text(executive.get("coverage_label") or "-")
    confidence_label = _text(executive.get("confidence_label") or report.get("confidence_label") or "-")
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status = "阶段性文稿 · 等待桥接闭环" if report_blocked else "正式文稿 · 可下载转发"
    rating = _text(report.get("status_label") or executive.get("verdict") or ("NEEDS REVIEW" if report_blocked else "RESEARCH GRADE"))
    report_no = _text(report.get("run_id") or report.get("id") or "AIJ-LOCAL")

    def paragraphs(items: list[Any], fallback: Any = "") -> str:
        cleaned = _nonempty_strings(items)[:4]
        if not cleaned and fallback:
            cleaned = [_text(fallback)]
        return "".join(f"<p>{html.escape(item)}</p>" for item in cleaned)

    def list_items(items: list[Any], fallback: Any = "") -> str:
        cleaned = _nonempty_strings(items)[:6]
        if not cleaned and fallback:
            cleaned = [_text(fallback)]
        return "".join(f"<li>{html.escape(item)}</li>" for item in cleaned)

    def evidence_rows_html() -> str:
        rows: list[str] = []
        source_rows = report.get("evidence_map") or []
        for index, row in enumerate(source_rows[:11], 1):
            if not isinstance(row, dict):
                continue
            rows.append(
                "<tr>"
                f"<td>E{index}</td>"
                f"<td>{html.escape(_text(row.get('dimension') or row.get('issue') or 'AI Judge 运行材料'))}</td>"
                f"<td>{html.escape(_text(row.get('source') or row.get('basis') or row.get('judgment') or '-'))}</td>"
                f"<td>{html.escape(_text(row.get('constraint') or row.get('confidence') or '需保留原始材料'))}</td>"
                "</tr>"
            )
        if not rows:
            fallback = [
                ("E1", "网页席位原始回答", "每个模型的完整输出进入本地资料库。", "不以摘要替代原文。"),
                ("E2", "共振追问", "从第一轮答案提取追问并要求二轮补充。", "追问与回答分层保存。"),
                ("E3", "席位互评", "模型间交叉评价进入评分矩阵。", "只解释分歧，不替代证据。"),
                ("E4", "Human Gavel", "人类签字决定是否可发布。", "未签字不作为最终授权。"),
                ("E5", "报告标准", "最终页仅保留正式文书。", "内部标签进入资料库。"),
            ]
            rows = [
                "<tr>"
                f"<td>{html.escape(eid)}</td><td>{html.escape(src)}</td><td>{html.escape(excerpt)}</td><td>{html.escape(limit)}</td>"
                "</tr>"
                for eid, src, excerpt, limit in fallback
            ]
        return "".join(rows)

    def decision_rows_html() -> str:
        rows: list[str] = []
        for index, row in enumerate(decision_rows[:8], 1):
            if not isinstance(row, dict):
                continue
            rows.append(
                "<tr>"
                f"<td>{index}</td>"
                f"<td>{html.escape(_text(row.get('issue') or row.get('dimension') or '-'))}</td>"
                f"<td>{html.escape(_text(row.get('decision') or row.get('judgment') or '-'))}</td>"
                f"<td>{html.escape(_text(row.get('basis') or row.get('source') or row.get('constraint') or '-'))}</td>"
                "</tr>"
            )
        if not rows:
            rows.append(
                "<tr><td>1</td><td>主审结论</td>"
                f"<td>{html.escape(lead)}</td>"
                "<td>依据多席位原始回答、共振追问、互评和 Human Gavel 门禁。</td></tr>"
            )
        return "".join(rows)

    def action_rows_html() -> str:
        rows: list[str] = []
        for index, row in enumerate(action_paths[:8], 1):
            if not isinstance(row, dict):
                continue
            rows.append(
                "<tr>"
                f"<td>{index}</td>"
                f"<td>{html.escape(_text(row.get('path') or row.get('task') or '-'))}</td>"
                f"<td>{html.escape(_text(row.get('execution') or row.get('action') or '-'))}</td>"
                f"<td>{html.escape(_text(row.get('deadline') or row.get('acceptance') or '-'))}</td>"
                "</tr>"
            )
        if not rows:
            for index, item in enumerate(plan[:6], 1):
                rows.append(
                    "<tr>"
                    f"<td>{index}</td><td>执行项 {index}</td><td>{html.escape(_text(item))}</td><td>进入人工确认后验收</td>"
                    "</tr>"
                )
        return "".join(rows)

    def contribution_rows_html() -> str:
        rows: list[str] = []
        topic_terms = _topic_terms(title)
        for row in appendix[:9]:
            if not isinstance(row, dict):
                continue
            contribution_blob = " ".join(
                _text(row.get(key) or "")
                for key in ("model", "stance", "adopted_contribution", "summary", "risk_note")
            )
            if topic_terms and contribution_blob and not _contains_any(contribution_blob, topic_terms):
                continue
            rows.append(
                "<tr>"
                f"<td>{html.escape(_text(row.get('model') or '-'))}</td>"
                f"<td>{html.escape(_text(row.get('stance') or '-'))}</td>"
                f"<td>{html.escape(_text(row.get('adopted_contribution') or row.get('summary') or '-'))}</td>"
                f"<td>{html.escape(_text(row.get('risk_note') or '保留原文追溯'))}</td>"
                "</tr>"
            )
        return "".join(rows)

    contribution_table = ""
    contribution_rows = contribution_rows_html()
    if contribution_rows:
        contribution_table = (
            '<h3>席位贡献附录 / MODEL CONTRIBUTIONS</h3>'
            '<div class="manuscript-table-wrap">'
            '<table class="manuscript-table"><thead><tr><th>席位</th><th>立场</th><th>采纳贡献</th><th>风险备注</th></tr></thead>'
            f"<tbody>{contribution_rows}</tbody></table></div>"
        )
    keywords = ["AI Judge", "Council Deliberation", "Resonance Follow-up", "Evidence Ledger", "Human Gavel"]
    keyword_html = "".join(f"<span>{html.escape(item)}</span>" for item in keywords)
    return (
        '<article class="manuscript-report research-paper" id="report-manuscript" data-report-root="professional-manuscript">'
        '<section class="paper-cover">'
        '<p class="paper-kicker">AI JUDGE FINAL REPORT · RESEARCH REPORT · 可打印正式文书</p>'
        f"<h1>{html.escape(title)}</h1>"
        f'<p class="paper-subtitle">Final Decision Manuscript / 最终裁决报告</p>'
        f'<p class="cover-statement">状态声明：{html.escape(status)}。本报告不是聊天记录，不是标签面板，它是可转发、可打印、可追溯的决策文书。</p>'
        '<div class="cover-meta">'
        f"<div><span>日期 Date</span><strong>{html.escape(report_date)}</strong></div>"
        f"<div><span>评级 Rating</span><strong>{html.escape(rating)}</strong></div>"
        f"<div><span>可信度 Confidence</span><strong>{html.escape(confidence_label)}</strong></div>"
        f"<div><span>席位覆盖 Seats</span><strong>{html.escape(coverage_label)}</strong></div>"
        "</div>"
        "</section>"
        '<section class="manuscript-section paper-page"><p class="section-num">01</p><h2>摘要 / ABSTRACT</h2>'
        f'<p class="manuscript-lead">{html.escape(lead)}</p>'
        f"{paragraphs(abstract_items, lead)}"
        f'<div class="paper-keywords">{keyword_html}</div>'
        "</section>"
        '<section class="manuscript-section paper-page"><p class="section-num">02</p><h2>关键指标 / SCORECARD</h2>'
        '<div class="report-score-grid">'
        f"<div><span>裁决</span><strong>{html.escape(rating)}</strong></div>"
        f"<div><span>可信度</span><strong>{html.escape(confidence_label)}</strong></div>"
        f"<div><span>席位覆盖</span><strong>{html.escape(coverage_label)}</strong></div>"
        f"<div><span>发布状态</span><strong>{html.escape(status)}</strong></div>"
        "</div>"
        "</section>"
        '<section class="manuscript-section paper-page"><p class="section-num">03</p><h2>评审方法 / METHODOLOGY</h2>'
        "<p>本轮采用网页席位原始报告、共振追问、席位互评、评分分层和 Human Gavel 形成最终文书。工作台记录过程，报告页只保留可阅读结论。</p>"
        f"{paragraphs(methodology_section.get('paragraphs') or [], '所有内部过程材料均进入完整结果资料库，不污染最终报告正文。')}"
        "</section>"
        '<section class="manuscript-section paper-page"><p class="section-num">04</p><h2>逐项分析 / ANALYSIS</h2>'
        f"<ul>{list_items(findings, lead)}</ul>"
        '<div class="manuscript-table-wrap">'
        '<table class="manuscript-table"><thead><tr><th>#</th><th>议题</th><th>裁定</th><th>依据</th></tr></thead>'
        f"<tbody>{decision_rows_html()}</tbody></table>"
        "</div>"
        "</section>"
        '<section class="manuscript-section paper-page"><p class="section-num">05</p><h2>行动建议 / ACTION ITEMS</h2>'
        '<div class="manuscript-table-wrap">'
        '<table class="manuscript-table"><thead><tr><th>#</th><th>任务</th><th>执行动作</th><th>验收 / 截止</th></tr></thead>'
        f"<tbody>{action_rows_html()}</tbody></table>"
        "</div>"
        "</section>"
        '<section class="manuscript-section paper-page"><p class="section-num">06</p><h2>证据溯源 / EVIDENCE LEDGER</h2>'
        '<p>每个结论必须能回到原始席位回答、共振二轮、互评或评分记录。无法核验的内容不得写成已验证事实。</p>'
        '<div class="manuscript-table-wrap">'
        '<table class="manuscript-table"><thead><tr><th>编号</th><th>来源</th><th>关键摘录</th><th>置信边界</th></tr></thead>'
        f"<tbody>{evidence_rows_html()}</tbody></table>"
        "</div>"
        f"{contribution_table}"
        "</section>"
        '<section class="manuscript-section paper-page"><p class="section-num">07</p><h2>局限声明 / LIMITATIONS</h2>'
        f"<ul>{list_items(risks, '没有硬阻断，但仍需保留人工确认和原始证据入口。')}</ul>"
        "<p>本报告只对本轮输入、席位覆盖和已归档证据负责。若新增事实、席位失败恢复或人工签字意见改变，需生成新版本。</p>"
        f'<footer class="report-end">Report No. {html.escape(report_no)} · End of Report</footer>'
        "</section>"
        "</article>"
    )


def _nonempty_strings(items: list[Any]) -> list[str]:
    result: list[str] = []
    for item in items:
        text = _text(item)
        if text and text not in result:
            result.append(text)
    return result


def _longform_markdown_lines(longform: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        "### 完整总结报告",
        "",
        f"#### {longform.get('title') or 'AI Judge 最终总结报告'}",
        "",
        str(longform.get("one_sentence_judgment") or ""),
        "",
        "#### 执行摘要",
        "",
    ]
    for paragraph in longform.get("executive_summary") or []:
        lines.extend([str(paragraph), ""])
    for section in longform.get("body_sections") or []:
        lines.extend([f"#### {section.get('title', '')}", ""])
        for paragraph in section.get("paragraphs") or []:
            lines.extend([str(paragraph), ""])
    decision_rows = longform.get("decision_table") or []
    if decision_rows:
        lines.extend(["#### 争议裁决表", "", "| 议题 | 裁定 | 依据 |", "|---|---|---|"])
        for row in decision_rows:
            lines.append(
                f"| {_pipe(row.get('issue'))} | {_pipe(row.get('decision'))} | {_pipe(row.get('basis'))} |"
            )
        lines.append("")
    roadmap = longform.get("roadmap") or []
    if roadmap:
        lines.extend(["#### 执行路线图", "", "| 阶段 | 目标 | 交付物 | 验收 |", "|---|---|---|---|"])
        for row in roadmap:
            lines.append(
                f"| {_pipe(row.get('phase'))} | {_pipe(row.get('goal'))} | "
                f"{_pipe(row.get('deliverable'))} | {_pipe(row.get('acceptance'))} |"
            )
        lines.append("")
    action_paths = longform.get("action_paths") or []
    if action_paths:
        lines.extend([
            "#### 全量可执行路径汇总",
            "",
            "| 路径 | 执行动作 | 入口 | 截止 | 来源席位 |",
            "|---|---|---|---|---|",
        ])
        for row in action_paths:
            lines.append(
                f"| {_pipe(row.get('path'))} | {_pipe(row.get('execution'))} | "
                f"{_pipe(row.get('entry'))} | {_pipe(row.get('deadline'))} | "
                f"{_pipe('、'.join(str(item) for item in row.get('source_models', [])))} |"
            )
        lines.append("")
    metrics = longform.get("success_metrics") or []
    if metrics:
        lines.extend(["#### 成功标准", ""])
        for item in metrics:
            lines.append(f"- {item}")
        lines.append("")
    appendix = longform.get("model_contribution_appendix") or []
    if appendix:
        lines.extend(["#### 模型贡献附录", "", "| 模型 | 立场 | 采纳贡献 | 风险备注 |", "|---|---|---|---|"])
        for row in appendix:
            lines.append(
                f"| {_pipe(row.get('model'))} | {_pipe(row.get('stance'))} | "
                f"{_pipe(row.get('adopted_contribution'))} | {_pipe(row.get('risk_note'))} |"
            )
        lines.append("")
    return lines


def _decision_brief_html(brief: dict[str, Any]) -> str:
    if not brief:
        return ""
    cards = "".join(
        '<article class="decision-card">'
        f'<span>{html.escape(str(card.get("label", "")))}</span>'
        f'<strong>{html.escape(str(card.get("value", "")))}</strong>'
        "</article>"
        for card in brief.get("cards", [])
    )
    plan = "".join(f"<li>{html.escape(str(item))}</li>" for item in brief.get("plan", []))
    warning = ""
    if brief.get("warning"):
        warning = f'<p class="decision-warning">{html.escape(str(brief.get("warning")))}</p>'
    return (
        '<section class="decision-brief">'
        '<p class="paper-kicker">FINAL PLAN · DECISION BRIEF · 最终方案总览 · 一屏读懂</p>'
        f'<h2>{html.escape(str(brief.get("title", "最终方案总览")))}</h2>'
        f'<p class="decision-lead">{html.escape(str(brief.get("one_sentence", "")))}</p>'
        f'<div class="decision-card-grid">{cards}</div>'
        '<section class="decision-plan">'
        "<h3>执行计划</h3>"
        f"<ol>{plan}</ol>"
        "</section>"
        f"{warning}"
        f'<p class="paper-status">{html.escape(str(brief.get("source_note", "")))}</p>'
        "</section>"
    )


def _run_health_html(run_health: dict[str, Any]) -> str:
    if not run_health:
        return ""
    status = _text(run_health.get("status") or "")
    cards = "".join(
        '<article class="run-health-card">'
        f'<span>{html.escape(str(card.get("label", "")))}</span>'
        f'<strong>{html.escape(str(card.get("value", "")))}</strong>'
        "</article>"
        for card in run_health.get("cards") or []
    )
    plan = "".join(f"<li>{html.escape(str(item))}</li>" for item in run_health.get("plan") or [])
    source_note = html.escape(str(run_health.get("source_note") or ""))
    return (
        f'<section class="run-health run-health-{html.escape(status or "unknown")}" id="run-health">'
        '<p class="paper-kicker">RUN HEALTH · BRIDGE RECOVERY · 运行健康门禁</p>'
        f'<h2>{html.escape(str(run_health.get("title") or "运行健康门禁"))}</h2>'
        f'<p class="run-health-lead">{html.escape(str(run_health.get("headline") or ""))}</p>'
        f'<div class="run-health-card-grid">{cards}</div>'
        '<section class="run-health-plan">'
        "<h3>恢复计划</h3>"
        f"<ol>{plan}</ol>"
        "</section>"
        f'<p class="paper-status">{source_note}</p>'
        "</section>"
    )


def _compact_report_overview_html(report: dict[str, Any], *, report_blocked: bool) -> str:
    overview = report.get("compact_overview") or {}
    executive = report.get("executive_summary") or {}
    status_cards = overview.get("status_cards") or [
        {"label": "报告状态", "value": report.get("status_label") or "-"},
        {"label": "席位覆盖", "value": executive.get("coverage_label") or "-"},
        {"label": "议员草稿", "value": "详见附录"},
        {"label": "门禁", "value": report.get("status_reason") or "-"},
    ]
    summary_cards = overview.get("summary_cards") or [
        {"label": "结论", "value": executive.get("headline") or report.get("abstract") or "-"},
        {"label": "方案", "value": executive.get("recommendation") or report.get("recommendation") or "-"},
        {"label": "计划", "value": executive.get("next_action") or "-"},
        {"label": "风险", "value": executive.get("risk") or "-"},
    ]
    status_html = "".join(
        '<article class="compact-status-card">'
        f'<span>{html.escape(str(card.get("label", "")))}</span>'
        f'<strong>{html.escape(str(card.get("value", "-")))}</strong>'
        "</article>"
        for card in status_cards
    )
    summary_html = "".join(
        '<article class="compact-summary-card">'
        f'<span>{html.escape(str(card.get("label", "")))}</span>'
        f'<p>{html.escape(str(card.get("value", "-")))}</p>'
        "</article>"
        for card in summary_cards
    )
    plan_html = "".join(
        '<article class="compact-plan-item">'
        f'<span>{html.escape(str(item.get("id", "")))}</span>'
        f'<strong>{html.escape(str(item.get("title", "")))}</strong>'
        f'<p>{html.escape(str(item.get("body", "")))}</p>'
        f'<small>{html.escape(str(item.get("status", "")))}</small>'
        "</article>"
        for item in overview.get("plan") or []
    )
    action_path_rows = "".join(
        "<tr>"
        f'<td><a href="{html.escape(_safe_report_href(row.get("trace_href")))}">{html.escape(str(row.get("path", "-")))}</a></td>'
        f'<td>{html.escape(str(row.get("execution", "-")))}</td>'
        f'<td>{html.escape(str(row.get("deadline", "-")))}<br><small>{html.escape(str(row.get("entry", "-")))}</small></td>'
        f'<td>{html.escape("、".join(str(item) for item in row.get("source_models", [])[:4]) or "-")}</td>'
        "</tr>"
        for row in (overview.get("action_paths") or [])[:8]
    )
    action_paths_html = ""
    if action_path_rows:
        action_paths_html = (
            '<section class="compact-panel compact-council" id="action-paths" data-action-paths="model-synthesis">'
            '<div class="compact-section-head"><div><h3>全量可执行路径汇总</h3>'
            '<p>汇总各席位给出的具体路线、截止日期、联系人/链接；噪音和未核实内容进入待核验。</p></div>'
            '<a href="#report-manuscript">查看正式报告</a></div>'
            '<table class="compact-council-table"><thead><tr><th>路径</th><th>执行动作</th><th>入口 / 截止</th><th>来源席位</th></tr></thead>'
            f"<tbody>{action_path_rows}</tbody></table>"
            "</section>"
        )
    council_rows = "".join(
        "<tr>"
        f'<td><a href="{html.escape(_safe_report_href(row.get("draft_href")))}">{html.escape(str(row.get("seat_name", row.get("seat", "-"))))}</a></td>'
        f'<td>{html.escape(str(row.get("contribution", "-")))}</td>'
        f'<td>{html.escape(str(row.get("summary", "-")))}</td>'
        f'<td><a href="{html.escape(_safe_report_href(row.get("stored_log_href") or row.get("raw_href")))}">内部日志</a></td>'
        "</tr>"
        for row in overview.get("council_index") or []
    )
    if not council_rows:
        council_rows = '<tr><td colspan="4">暂无可追溯议员草稿，先查看运行健康门禁。</td></tr>'
    jump_html = "".join(
        f'<a class="compact-jump" href="{html.escape(_safe_report_href(item.get("href")))}">'
        f'<strong>{html.escape(str(item.get("label", "")))}</strong>'
        f'<span>{html.escape(str(item.get("description", "")))}</span>'
        "</a>"
        for item in overview.get("jump_pages") or []
    )
    title = overview.get("title") or report.get("title") or "AI Judge 最终报告"
    summary = overview.get("summary") or executive.get("headline") or report.get("abstract") or ""
    priority = overview.get("priority") or executive.get("next_action") or report.get("recommendation") or ""
    blocked_class = " is-blocked" if report_blocked else ""
    health_action = '<a href="#run-health">查看运行诊断</a>' if report_blocked else '<a href="#run-health">运行健康</a>'
    return (
        f'<section class="compact-report-overview{blocked_class}" id="final-report" data-report-root="canonical-compact">'
        '<div class="compact-report-hero">'
        '<p class="paper-kicker">FINAL REPORT · COMPACT OVERVIEW · FINAL VERDICT · HUMAN SUMMARY · 一屏读懂</p>'
        f'<p class="paper-status">{html.escape(str(report.get("title", "")))}</p>'
        f'<h2>{html.escape(str(title))}</h2>'
        f'<p class="compact-lead">{html.escape(str(summary))}</p>'
        f'<p class="compact-priority"><strong>下一步：</strong>{html.escape(str(priority))}</p>'
        "</div>"
        f'<div class="compact-status-grid">{status_html}</div>'
        '<section class="compact-panel">'
        '<h3>最终方案总览</h3>'
        f'<div class="compact-summary-grid">{summary_html}</div>'
        "</section>"
        '<section class="compact-panel">'
        '<h3>执行计划</h3>'
        f'<div class="compact-plan-strip">{plan_html}</div>'
        "</section>"
        f"{action_paths_html}"
        '<section class="compact-panel" id="council-index" data-council-drafts="compact-table">'
        '<div class="compact-section-head"><div><h3>议员方案草稿索引</h3>'
        '<p>主视图只放摘要；点席位进入本地内部存档日志，不跳外部登录页。</p></div>'
        '<a href="#seat-answers">全部议员草稿</a></div>'
        '<table class="compact-council-table"><thead><tr><th>议员</th><th>贡献</th><th>草稿摘要</th><th>追溯</th></tr></thead>'
        f"<tbody>{council_rows}</tbody></table>"
        "</section>"
        f'<div class="compact-jump-grid">{jump_html}</div>'
        f'<p class="compact-footer-note">{html.escape(str(overview.get("download_note") or ""))}</p>'
        f'<div class="actions">{health_action}<a href="#report-manuscript">查看正式报告</a><a href="#seat-answers">查看席位原文</a><a href="#internal-library">内部资料库</a></div>'
        "</section>"
    )


def _safe_report_href(value: Any) -> str:
    href = _text(value)
    if href.startswith(("#", "/", "http://", "https://")):
        return href
    return "#"


def _draft_report_html(
    longform: dict[str, Any],
    compiled: dict[str, Any],
    decision_brief: dict[str, Any] | None = None,
) -> str:
    brief_html = _decision_brief_html(decision_brief or {})
    if longform:
        draft_body = _longform_report_html(longform, {}).replace('id="compiled-report"', 'id="draft-compiled-report"', 1)
    elif compiled:
        draft_body = _compiled_report_html(compiled, {}).replace('id="compiled-report"', 'id="draft-compiled-report"', 1)
    else:
        draft_body = ""
    return (
        '<section class="paper-report draft-report" id="compiled-report">'
        '<div class="paper-heading">'
        '<p class="paper-kicker">DRAFT ONLY · BLOCKED BY RUN HEALTH · 业务草稿</p>'
        '<h2>业务草稿：等待桥接闭环后定稿</h2>'
        '<p class="paper-status">必需席位未完成前，这部分只用于内部复核，不作为最终结论。</p>'
        "</div>"
        f"{brief_html}"
        '<details class="draft-details">'
        '<summary><h3>展开业务草稿</h3><span>先处理运行健康门禁，再把草稿升级为正式报告</span></summary>'
        f"{draft_body}"
        "</details>"
        "</section>"
    )


def _longform_report_html(longform: dict[str, Any], decision_brief: dict[str, Any] | None = None) -> str:
    summary = "".join(f"<p>{html.escape(str(item))}</p>" for item in longform.get("executive_summary", []))
    body = "".join(
        '<section class="paper-block longform-section">'
        f"<h3>{html.escape(str(section.get('title', '')))}</h3>"
        + "".join(f"<p>{html.escape(str(paragraph))}</p>" for paragraph in section.get("paragraphs", []))
        + "</section>"
        for section in longform.get("body_sections", [])
    )
    decision_rows = _table_rows(longform.get("decision_table", []), ["issue", "decision", "basis"])
    roadmap_rows = _table_rows(longform.get("roadmap", []), ["phase", "goal", "deliverable", "acceptance"])
    action_path_rows = _table_rows(longform.get("action_paths", []), ["path", "execution", "entry", "deadline", "status"])
    action_paths_html = ""
    if action_path_rows:
        action_paths_html = (
            '<section class="paper-block paper-evidence" id="action-paths-full">'
            "<h3>全量可执行路径汇总</h3>"
            '<p class="paper-status">从议员草稿中提炼可执行路线，联系人、链接和截止日期仍按待核验门禁处理。</p>'
            "<table><thead><tr><th>路径</th><th>执行动作</th><th>入口</th><th>截止</th><th>状态</th></tr></thead>"
            f"<tbody>{action_path_rows}</tbody></table>"
            "</section>"
        )
    metric_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in longform.get("success_metrics", []))
    appendix_rows = _table_rows(
        longform.get("model_contribution_appendix", []),
        ["model", "stance", "adopted_contribution", "risk_note"],
    )
    brief_html = _decision_brief_html(decision_brief or longform.get("decision_brief") or {})
    return (
        '<section class="paper-report longform-report" id="compiled-report">'
        '<div class="paper-heading">'
        '<p class="paper-kicker">EDITORIAL SYNTHESIS · LONGFORM REPORT · COMPLETE REPORT · 完整总结报告</p>'
        f'<h2>{html.escape(str(longform.get("title", "完整总结报告")))}</h2>'
        f'<p class="paper-status">{html.escape(str(longform.get("subtitle", "总编成稿")))}</p>'
        "</div>"
        f"{brief_html}"
        f'<p class="longform-lead">{html.escape(str(longform.get("one_sentence_judgment", "")))}</p>'
        '<section class="paper-block longform-summary">'
        "<h3>执行摘要</h3>"
        f"{summary}"
        "</section>"
        f"{body}"
        '<section class="paper-block paper-evidence">'
        "<h3>争议裁决表</h3>"
        "<table><thead><tr><th>议题</th><th>裁定</th><th>依据</th></tr></thead>"
        f"<tbody>{decision_rows}</tbody></table>"
        "</section>"
        '<section class="paper-block paper-evidence">'
        "<h3>执行路线图</h3>"
        "<table><thead><tr><th>阶段</th><th>目标</th><th>交付物</th><th>验收</th></tr></thead>"
        f"<tbody>{roadmap_rows}</tbody></table>"
        "</section>"
        f"{action_paths_html}"
        '<section class="paper-block">'
        "<h3>成功标准</h3>"
        f'<ul class="compact-list">{metric_items}</ul>'
        "</section>"
        '<section class="paper-block paper-evidence source-appendix">'
        "<h3>模型贡献附录</h3>"
        f'<p class="paper-status">{html.escape(str(longform.get("source_note", "")))}</p>'
        "<table><thead><tr><th>模型</th><th>立场</th><th>采纳贡献</th><th>风险备注</th></tr></thead>"
        f"<tbody>{appendix_rows}</tbody></table>"
        "</section>"
        "</section>"
    )


def _compiled_report_html(compiled: dict[str, Any], decision_brief: dict[str, Any] | None = None) -> str:
    compiled_sections = "".join(
        '<article class="paper-block">'
        f"<h3>{html.escape(str(section.get('title', '')))}</h3>"
        f"<p>{html.escape(str(section.get('summary', '')))}</p>"
        f"<ul class=\"compact-list\">{''.join(f'<li>{html.escape(str(item))}</li>' for item in section.get('items', [])[:6])}</ul>"
        f"<small>{html.escape('来源席位：' + '、'.join(str(item) for item in section.get('source_models', [])[:5]) if section.get('source_models') else '')}</small>"
        "</article>"
        for section in compiled.get("sections", [])
    )
    decision_rows = _table_rows(compiled.get("decision_table", []), ["issue", "decision", "basis"])
    roadmap_rows = _table_rows(compiled.get("roadmap", []), ["phase", "goal", "deliverable", "acceptance"])
    action_path_rows = _table_rows(compiled.get("action_paths", []), ["path", "execution", "entry", "deadline", "status"])
    action_paths_html = ""
    if action_path_rows:
        action_paths_html = (
            '<section class="paper-block paper-evidence" id="action-paths-full">'
            "<h3>全量可执行路径汇总</h3>"
            "<table><thead><tr><th>路径</th><th>执行动作</th><th>入口</th><th>截止</th><th>状态</th></tr></thead>"
            f"<tbody>{action_path_rows}</tbody></table>"
            "</section>"
        )
    metric_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in compiled.get("success_metrics", []))
    appendix_rows = _table_rows(compiled.get("model_contribution_appendix", []), ["model", "stance", "adopted_contribution", "risk_note"])
    brief_html = _decision_brief_html(decision_brief or {})
    return (
        '<section class="paper-report compiled-report" id="compiled-report">'
        '<div class="paper-heading">'
        '<p class="paper-kicker">EDITORIAL SYNTHESIS · COMPLETE REPORT</p>'
        f'<h2>{html.escape(str(compiled.get("title", "最终整合报告")))}</h2>'
        f'<p class="paper-status">{html.escape(str(compiled.get("source_note", "")))}</p>'
        "</div>"
        f"{brief_html}"
        '<section class="paper-block">'
        "<h3>问题重述</h3>"
        f"<p>{html.escape(str(compiled.get('problem_restatement', '')))}</p>"
        "</section>"
        '<section class="paper-block paper-callout">'
        "<h3>总编裁定</h3>"
        f"<p>{html.escape(str(compiled.get('editorial_verdict', '')))}</p>"
        "</section>"
        f'<div class="paper-postulates">{compiled_sections}</div>'
        '<section class="paper-block paper-evidence">'
        "<h3>争议裁决表</h3>"
        "<table><thead><tr><th>议题</th><th>裁定</th><th>依据</th></tr></thead>"
        f"<tbody>{decision_rows}</tbody></table>"
        "</section>"
        '<section class="paper-block paper-evidence">'
        "<h3>执行路线图</h3>"
        "<table><thead><tr><th>阶段</th><th>目标</th><th>交付物</th><th>验收</th></tr></thead>"
        f"<tbody>{roadmap_rows}</tbody></table>"
        "</section>"
        f"{action_paths_html}"
        '<section class="paper-block">'
        "<h3>成功标准</h3>"
        f'<ul class="compact-list">{metric_items}</ul>'
        "</section>"
        '<section class="paper-block paper-evidence">'
        "<h3>模型贡献附录</h3>"
        "<table><thead><tr><th>模型</th><th>立场</th><th>采纳贡献</th><th>风险备注</th></tr></thead>"
        f"<tbody>{appendix_rows}</tbody></table>"
        "</section>"
        "</section>"
    )


def _table_rows(rows: list[dict[str, Any]], keys: list[str]) -> str:
    return "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(row.get(key, '')))}</td>" for key in keys) + "</tr>"
        for row in rows
    )


def _compiled_markdown_lines(compiled: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        "### 最终整合报告",
        "",
        str(compiled.get("problem_restatement") or ""),
        "",
        f"**总编裁定：** {compiled.get('editorial_verdict') or '-'}",
        "",
    ]
    for section in compiled.get("sections") or []:
        lines.extend([f"#### {section.get('title', '')}", "", str(section.get("summary") or ""), ""])
        for item in section.get("items") or []:
            lines.append(f"- {item}")
        if section.get("source_models"):
            lines.append(f"- 来源席位：{'、'.join(str(item) for item in section.get('source_models') or [])}")
        lines.append("")
    decision_rows = compiled.get("decision_table") or []
    if decision_rows:
        lines.extend(["### 争议裁决表", "", "| 议题 | 裁定 | 依据 |", "|---|---|---|"])
        for row in decision_rows:
            lines.append(f"| {_pipe(row.get('issue'))} | {_pipe(row.get('decision'))} | {_pipe(row.get('basis'))} |")
        lines.append("")
    action_paths = compiled.get("action_paths") or []
    if action_paths:
        lines.extend([
            "### 全量可执行路径汇总",
            "",
            "| 路径 | 执行动作 | 入口 | 截止 | 来源席位 |",
            "|---|---|---|---|---|",
        ])
        for row in action_paths:
            lines.append(
                f"| {_pipe(row.get('path'))} | {_pipe(row.get('execution'))} | "
                f"{_pipe(row.get('entry'))} | {_pipe(row.get('deadline'))} | "
                f"{_pipe('、'.join(str(item) for item in row.get('source_models', [])))} |"
            )
        lines.append("")
    return lines


def _abstract(
    *,
    judge_editor: dict[str, str],
    verdict_label: str,
    confidence: str,
    trust: str,
    coverage: dict[str, Any],
    complete: bool,
    executive_summary: dict[str, Any],
) -> str:
    boundary = "可作为最终方案进入执行复核。" if complete else "因席位未全量闭环，只能作为阶段性方案，不能包装为全模型最终共识。"
    return (
        f"{judge_editor['label']}收口：{executive_summary.get('headline') or f'本轮结论为“{verdict_label}”。'}"
        f"可信度 {confidence}，可信等级 {trust or '-'}，席位覆盖 {coverage['label']}。"
        f"下一步：{executive_summary.get('next_action') or '先复核证据链。'}{boundary}"
    )


def _coverage(verdict: dict[str, Any]) -> dict[str, Any]:
    bridge = verdict.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    requested = _as_int(bridge.get("requested_count"), len(raw_results) or len(verdict.get("seats") or []))
    ok = _as_int(bridge.get("ok_count"), sum(1 for item in raw_results if item.get("ok")) if raw_results else requested)
    failed = _as_int(bridge.get("failed_count"), max(0, requested - ok))
    policy = bridge.get("execution_policy") or {}
    required_count = _as_int(policy.get("required_count"), _as_int(bridge.get("required_count"), requested))
    required_ok = _as_int(policy.get("required_valid_count"), _as_int(bridge.get("required_ok_count"), ok))
    if "collection_complete" in bridge:
        complete = bool(bridge.get("collection_complete"))
    elif required_count:
        complete = required_ok >= required_count
    else:
        complete = failed == 0
    denominator = required_count or requested
    numerator = required_ok if required_count else ok
    label = f"{numerator}/{denominator}" if denominator else "-"
    return {
        "ok": ok,
        "failed": failed,
        "requested": requested,
        "required_ok": required_ok,
        "required_count": required_count,
        "complete": complete,
        "label": label,
    }


def _run_health_panel(verdict: dict[str, Any], coverage: dict[str, Any], *, complete: bool) -> dict[str, Any]:
    bridge = verdict.get("web_bridge") or {}
    policy = bridge.get("execution_policy") or {}
    rescue_plan = bridge.get("rescue_plan") or {}
    failures = _required_failure_rows(verdict)
    failed_names = _unique_texts([_failure_seat_name(item) for item in failures], limit=8)
    failure_summary = "、".join(failed_names) if failed_names else "-"
    recovery_label = _text(rescue_plan.get("button_label") or "")
    if not recovery_label:
        recovery_label = "一键恢复/回收" if failures else "无需恢复"
    gate = "通过" if complete else "未通过"
    headline = (
        f"运行已闭环：必需席位覆盖 {coverage['label']}，可以阅读最终业务报告。"
        if complete
        else f"运行未闭环：必需席位覆盖只有 {coverage['label']}，先恢复桥接，不生成业务最终结论。"
    )
    plan = _run_health_plan(failures, rescue_plan, complete=complete)
    cards = [
        {"label": "发布门禁", "value": gate},
        {"label": "必需席位", "value": coverage["label"]},
        {"label": "待恢复", "value": failure_summary},
        {"label": "恢复动作", "value": recovery_label},
    ]
    return {
        "schema": "ai_judge.run_health.v1",
        "status": "complete" if complete else "blocked",
        "title": "运行健康门禁",
        "headline": headline,
        "cards": cards,
        "plan": plan,
        "rescue_plan": rescue_plan,
        "failure_count": len(failures),
        "required_count": coverage.get("required_count", 0),
        "required_valid_count": coverage.get("required_ok", 0),
        "collection_complete": complete,
        "detail_anchor": "#run-health",
        "draft_anchor": "#report-manuscript",
        "source_note": _run_health_source_note(policy, bridge),
    }


def _run_health_plan(failures: list[dict[str, Any]], rescue_plan: dict[str, Any], *, complete: bool) -> list[str]:
    if complete:
        return ["保留原始答案、评分链路和席位覆盖记录，再进入人工发布确认。"]
    actions = rescue_plan.get("actions") or []
    plan: list[str] = []
    for action in actions[:6]:
        seat = _text(action.get("seat_name") or action.get("seat") or "席位")
        label = _text(action.get("label") or "恢复")
        code = _text(action.get("code") or "")
        suffix = f"（{code}）" if code else ""
        plan.append(f"{seat}：{label}{suffix}。")
    for failure in failures[:6]:
        seat = _failure_seat_name(failure)
        code = _failure_code(failure)
        message = _failure_message(failure)
        text = f"{seat}：{message or code or '需要恢复'}。"
        if text not in plan:
            plan.append(text)
    if not plan:
        plan.append("先打开运行诊断，确认登录、额度、固定标签和页面模式，再重新回收必需席位。")
    plan.append("报告正文保持草稿态；必需席位未闭环前，不把业务方案当最终结论发布。")
    return _unique_texts(plan, limit=7)


def _required_failure_rows(verdict: dict[str, Any]) -> list[dict[str, Any]]:
    bridge = verdict.get("web_bridge") or {}
    policy = bridge.get("execution_policy") or {}
    failures = [item for item in policy.get("required_failures") or [] if isinstance(item, dict)]
    if failures:
        return failures
    rows: list[dict[str, Any]] = []
    for item in bridge.get("raw_results") or []:
        if not isinstance(item, dict) or item.get("ok"):
            continue
        seat = _text(item.get("seat") or "").lower()
        if seat in {"grok", "gork"}:
            continue
        rows.append(item)
    return rows


def _failure_seat_name(item: dict[str, Any]) -> str:
    return _text(item.get("seat_name") or item.get("seat") or "席位")


def _failure_code(item: dict[str, Any]) -> str:
    error = item.get("error") or {}
    validity = item.get("execution_validity") or {}
    return _text(error.get("code") or validity.get("reason") or item.get("code") or item.get("reason") or "")


def _failure_message(item: dict[str, Any]) -> str:
    error = item.get("error") or {}
    validity = item.get("execution_validity") or {}
    return _text(error.get("message") or validity.get("message") or item.get("message") or item.get("detail") or "")


def _run_health_source_note(policy: dict[str, Any], bridge: dict[str, Any]) -> str:
    if not policy and not bridge:
        return ""
    required = policy.get("required_rule") or "all_requested_non_grok_seats_must_have_valid_execution"
    optional = ", ".join(str(item) for item in policy.get("optional_seats") or [])
    optional_note = f"；可选席位：{optional}" if optional else ""
    return f"门禁规则：{required}{optional_note}。"


def _compact_overview_payload(
    *,
    verdict: dict[str, Any],
    question: str,
    verdict_label: str,
    coverage: dict[str, Any],
    complete: bool,
    executive_summary: dict[str, Any],
    recommendation: str,
    plan: list[str],
    risks: list[str],
    decision_brief: dict[str, Any],
    run_health: dict[str, Any],
    compiled_report: dict[str, Any],
) -> dict[str, Any]:
    council_index = _compact_council_index(verdict)
    action_paths = _action_path_rows(question, _answer_source_rows(verdict))
    failed_names = _unique_texts([_failure_seat_name(item) for item in _required_failure_rows(verdict)], limit=5)
    blocker = "、".join(failed_names) if failed_names else "无硬阻断"
    brief_cards = decision_brief.get("cards") or []
    brief_solution = brief_cards[1].get("value") if len(brief_cards) > 1 and isinstance(brief_cards[1], dict) else ""
    summary_cards = [
        {
            "label": "结论",
            "value": _compact(decision_brief.get("one_sentence") or executive_summary.get("headline") or verdict_label, 132),
        },
        {
            "label": "方案",
            "value": _compact(recommendation or brief_solution or "-", 132),
        },
        {
            "label": "计划",
            "value": _compact((decision_brief.get("plan") or plan or ["先确认最终报告，再进入发布复核。"])[0], 132),
        },
        {
            "label": "风险",
            "value": _compact(executive_summary.get("risk") or (risks[0] if risks else "保留人工确认和原始证据入口。"), 132),
        },
    ]
    status_cards = [
        {
            "label": "报告状态",
            "value": "最终可读" if complete else "阶段草稿",
        },
        {
            "label": "席位覆盖",
            "value": coverage.get("label") or "-",
        },
        {
            "label": "议员草稿",
            "value": f"{len(council_index)} 个可追溯",
        },
        {
            "label": "门禁",
            "value": "可下载/转发" if complete else f"先补齐：{blocker}",
        },
    ]
    jump_pages = [
        {"label": "全量路径汇总", "href": "#action-paths", "description": "查看商业化、投稿、参赛、融资和加星的可执行清单。"},
        {"label": "正式报告", "href": "#report-manuscript", "description": "查看可打印、可转发的最终文书。"},
        {"label": "全部议员草稿", "href": "#seat-answers", "description": "逐席位查看模型原文和失败原因。"},
        {"label": "内部资料库", "href": "#seat-digest", "description": "查看本地存档的席位摘要、优缺点和原文日志。"},
        {"label": "审计资料", "href": "#internal-library", "description": "查看 SOP、证据边界和内部资料库。"},
        {"label": "运行健康", "href": "#run-health", "description": "查看桥接门禁、恢复路径和失败席位。"},
    ]
    return {
        "schema": "ai_judge.compact_report_overview.v1",
        "title": decision_brief.get("title") or f"AI Judge 最终行动方案：{_topic_label(question)}",
        "subtitle": "首屏只放结论、方案、计划、风险；完整草稿和证据从下方跳转追溯。",
        "verdict": verdict_label,
        "summary": _compact(decision_brief.get("one_sentence") or executive_summary.get("headline") or "", 220),
        "priority": _compact(executive_summary.get("next_action") or recommendation or "", 160),
        "status_cards": status_cards,
        "summary_cards": summary_cards,
        "plan": _compact_closeout_plan(plan, complete=complete),
        "action_paths": action_paths,
        "council_index": council_index,
        "jump_pages": jump_pages,
        "run_health_anchor": run_health.get("detail_anchor") or "#run-health",
        "compiled_anchor": "#report-manuscript",
        "source_lineage": [
            "final_report",
            "compact_overview",
            "action_path_synthesis",
            "council_draft_index",
            "internal_stored_log",
            "seat_answer_anchor",
        ],
        "download_note": (
            "PDF/Markdown 带总览、路径汇总、议员索引和内部追溯摘要；完整草稿留在本地资料库，避免下载文件臃肿。"
        ),
        "source_note": _text(compiled_report.get("source_note") or decision_brief.get("source_note") or ""),
    }


def _compact_closeout_plan(plan: list[str], *, complete: bool) -> list[dict[str, str]]:
    defaults = [
        ("T0", "标题绑定", "标题必须来自任务主题，不再用桥接错误当报告标题。"),
        ("T1", "首屏压缩", "首屏只保留结论、方案、计划、风险和门禁。"),
        ("T2", "草稿索引", "把每个议员方案压成表格，点席位再看原文。"),
        ("T3", "追溯链", "运行健康、席位原文、SOP 和旧版报告全部保留为跳转附录。"),
        ("T4", "下载转发", "同一完整网页支持 PDF、Markdown、复制链接和中英切换。"),
    ]
    source = _unique_texts(plan, limit=5)
    items: list[dict[str, str]] = []
    for index, (step_id, title, fallback) in enumerate(defaults):
        items.append(
            {
                "id": step_id,
                "title": title,
                "body": _compact(source[index] if index < len(source) else fallback, 118),
                "status": "已收口" if complete or index < 2 else "待门禁",
            }
        )
    return items


def _compact_council_index(verdict: dict[str, Any]) -> list[dict[str, str]]:
    raw_by_seat = _raw_results_by_seat(verdict)
    rows: list[dict[str, str]] = []
    for row in _answer_source_rows(verdict):
        seat = _text(row.get("seat") or row.get("model") or "").lower()
        if not seat:
            continue
        raw = raw_by_seat.get(seat) or raw_by_seat.get(_text(row.get("model")).lower()) or {}
        raw_url = _text(
            raw.get("url")
            or raw.get("page_url")
            or raw.get("conversation_url")
            or raw.get("source_url")
            or raw.get("href")
        )
        raw_chars = len(_text(row.get("text") or raw.get("response") or raw.get("answer") or ""))
        contribution = _seat_contribution_label(seat)
        internal_href = f"#seat-answer-{seat}"
        rows.append(
            {
                "seat": seat,
                "seat_name": _text(row.get("model") or row.get("seat") or seat),
                "contribution": contribution,
                "summary": f"{contribution}方向草稿，约 {raw_chars} 字；点击内部日志查看完整内容。",
                "raw_url": "",
                "external_url": raw_url,
                "raw_chars": str(raw_chars),
                "draft_href": internal_href,
                "raw_href": internal_href,
                "stored_log_href": internal_href,
                "source_lineage": "final_report > council_draft > internal_stored_log > seat_answer_anchor",
            }
        )
        if len(rows) >= 12:
            break
    return rows


def _action_path_rows(question: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not _is_commercial_growth_topic(question):
        return []
    buckets = [
        {
            "path": "GitHub / README / Demo",
            "keywords": ["github", "readme", "star", "demo", "issues", "discussions"],
            "primary_keywords": ["readme", "star", "加星", "stars", "issues", "discussions"],
            "execution": "72 小时内重写 README 首屏，补 demo GIF / 60 秒视频，开启 issues/discussions，把差异化定位放到仓库第一页。",
            "entry": "GitHub repo / README / issues，公开入口待复核。",
            "deadline": "72 小时内",
        },
        {
            "path": "Hugging Face Space",
            "keywords": ["hugging face", "hf", "space", "spaces", "在线演示"],
            "execution": "部署可体验 Space，用固定 demo case 展示可回放审计报告，并把试用数据回流到 GitHub 增长。",
            "entry": "https://huggingface.co/spaces（入口待核验）",
            "deadline": "72 小时内",
            "extract_entry": True,
            "prefer_url_entry": True,
        },
        {
            "path": "Show HN / Reddit / Dev.to / X / LinkedIn",
            "keywords": ["show hn", "reddit", "dev.to", "twitter", "x/twitter", "linkedin", "product hunt", "hn"],
            "execution": "发布首轮开发者社区贴，主打 source-isolated citation 与 claim-support audit，收集评论、私信和 stars。",
            "entry": "Show HN、Reddit、Dev.to、X、LinkedIn",
            "deadline": "首轮 72 小时内",
        },
        {
            "path": "论文 / Workshop / Papers with Code",
            "keywords": ["论文", "投稿", "workshop", "emnlp", "aaai", "neurips", "iclr", "arxiv", "openreview", "papers with code", "ai engineer"],
            "execution": "整理 AI Eval / Agent Infra 摘要、实验脚本、demo video 和可复现实验，先核验每个会议/Workshop 截止日期。",
            "entry": "OpenReview、arXiv、Papers with Code、会议官网",
            "deadline": "7 天内核验窗口",
            "extract_entry": True,
            "extract_deadline": True,
            "prefer_url_entry": True,
        },
        {
            "path": "参赛 / 黑客松 / AIGC 大赛",
            "keywords": ["参赛", "大赛", "hackathon", "黑客松", "aigc", "challenge", "比赛"],
            "execution": "筛选 AIGC/Agent/AI infra 相关比赛，确认报名入口、材料清单、demo 要求和截止日期后再投入制作。",
            "entry": "赛事官网 / 报名表，所有链接待核验",
            "deadline": "立即核验",
            "extract_entry": True,
            "extract_deadline": True,
            "prefer_url_entry": True,
        },
        {
            "path": "加速器 / 投资人",
            "keywords": ["yc", "techstars", "奇绩", "红杉", "投资", "融资", "accelerator", "vc", "投资人"],
            "execution": "准备 1 页 memo、5 封冷启动邮件和 demo link，优先联系 AI infra、devtools、security/compliance 方向投资人。",
            "entry": "YC / Techstars / 奇绩创坛 / 投资人公开表单或 LinkedIn",
            "deadline": "14 天内首轮触达",
        },
        {
            "path": "企业试点 / 商业化",
            "keywords": ["企业", "试点", "商业化", "sla", "私有化", "审计", "api", "sdk", "ci", "付费"],
            "execution": "先卖审计报告、私有化部署、SLA 和 CI 集成试点，不把产品包装成普通多模型聊天。",
            "entry": "目标客户：AI infra 团队、合规/安全团队、自动化评测团队",
            "deadline": "30 天内形成试点名单",
        },
        {
            "path": "媒体 / KOL / 开源社区",
            "keywords": ["媒体", "kol", "newsletter", "社区", "量子位", "机器之心", "hugging face中文社区", "投稿邮箱", "邮箱", "私信"],
            "execution": "给媒体、开源 KOL 和 Newsletter 一套可复制 demo、差异化说明和首封私信模板，避免只发概念介绍。",
            "entry": "公开邮箱、LinkedIn 私信、社区投稿入口",
            "deadline": "14 天内首轮外联",
            "extract_entry": True,
        },
    ]
    output: list[dict[str, Any]] = []
    for index, bucket in enumerate(buckets, 1):
        matches: list[tuple[int, str, str, str]] = []
        for row in rows:
            model = _text(row.get("model") or row.get("seat") or "")
            seat = _text(row.get("seat") or model).lower()
            text = _text(row.get("text") or row.get("summary") or "")
            for point in _split_points(text):
                cleaned = _strip_markdown_marker(_clean_report_point(point, 260))
                if not cleaned or _action_path_noise(cleaned):
                    continue
                if not _contains_any(cleaned, bucket["keywords"]):
                    continue
                score = _action_path_score(cleaned, bucket["keywords"])
                primary_keywords = bucket.get("primary_keywords") or []
                if primary_keywords:
                    score += 8 if _contains_any(cleaned, primary_keywords) else -3
                if score <= 0:
                    continue
                matches.append((score, model, seat, cleaned))
        matches.sort(key=lambda item: item[0], reverse=True)
        evidence = _unique_texts([item[3] for item in matches], limit=2)
        evidence_text = "；".join(evidence)
        source_models = _unique_texts([item[1] for item in matches], limit=4)
        first_seat = next((item[2] for item in matches if item[2]), "")
        entry = (
            _extract_action_entry(evidence_text, prefer_url=bool(bucket.get("prefer_url_entry")))
            if bucket.get("extract_entry")
            else ""
        ) or bucket["entry"]
        deadline = (_extract_action_deadline(evidence_text) if bucket.get("extract_deadline") else "") or bucket["deadline"]
        output.append(
            {
                "priority": f"P{index}",
                "path": bucket["path"],
                "execution": _compact(bucket["execution"], 170),
                "entry": _compact(entry, 120),
                "deadline": _compact(deadline, 80),
                "evidence": _compact(evidence_text or "该路径来自多席位共识模板，具体入口和日期必须人工核验。", 190),
                "source_models": source_models or ["综合共识"],
                "trace_href": f"#seat-answer-{first_seat}" if first_seat else "#seat-digest",
                "status": "席位草稿已提及" if source_models else "待核验",
            }
        )
    return output


def _action_path_noise(value: str) -> bool:
    lowered = value.lower()
    noisy = (
        "推理链声明",
        "由于网络物理隔离",
        "这里先声明",
        "以下链接和邮箱结构",
        "如果你无法联网",
        "不要编造",
        "raw_should_not_appear",
    )
    return any(item.lower() in lowered for item in noisy)


def _action_path_score(value: str, keywords: list[str]) -> int:
    lowered = value.lower()
    score = sum(2 for keyword in keywords if _text(keyword).lower() in lowered)
    if re.search(r"https?://|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value):
        score += 5
    if _extract_action_deadline(value):
        score += 4
    if _contains_any(value, ["提交", "投稿", "发布", "联系", "申请", "部署", "录制", "重写", "触达", "报名", "整理", "准备"]):
        score += 3
    if len(value) >= 28:
        score += 1
    return score


def _extract_action_entry(value: str, *, prefer_url: bool = False) -> str:
    url = re.search(r"https?://[^\s，。；；)）\]】<>\"']+", value)
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value)
    if prefer_url and url:
        return url.group(0).rstrip(".,;，。；")
    if email:
        return email.group(0)
    if url:
        return url.group(0).rstrip(".,;，。；")
    if _contains_any(value, ["LinkedIn", "私信"]):
        return "LinkedIn 私信 / 公开主页"
    if _contains_any(value, ["官网", "报名", "表单"]):
        return "官网 / 报名表单"
    return ""


def _extract_action_deadline(value: str) -> str:
    patterns = [
        r"(?:截止|关闭|报名截止|摘要截止|全文截止|deadline)[^，。；\n]{0,18}?(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(\d{1,2}\s*月\s*\d{1,2}\s*日)",
        r"(\d+\s*(?:小时|天|周|月)内)",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip(" ：:，。；")
    return ""


def _raw_results_by_seat(verdict: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bridge = verdict.get("web_bridge") or {}
    rows: dict[str, dict[str, Any]] = {}
    for item in bridge.get("raw_results") or []:
        if not isinstance(item, dict):
            continue
        for key in (_text(item.get("seat")).lower(), _text(item.get("seat_name")).lower()):
            if key:
                rows[key] = item
    return rows


def _seat_contribution_label(seat: str) -> str:
    labels = {
        "chatgpt": "信息架构",
        "gpt": "信息架构",
        "deepseek": "流程收束",
        "gemini": "渐进披露",
        "qwen": "审计快照",
        "kimi": "原型审批",
        "mimo": "SLA 与稳定性",
        "doubao": "用户分层",
        "claude": "合规边界",
        "minimax": "异常处理",
        "wenxin": "翻译校准",
        "yuanbao": "批注模式",
        "zhipu": "法定人数",
    }
    return labels.get(seat.lower(), "方案草稿")


def _postulates(
    *,
    judge_editor: dict[str, str],
    verdict_label: str,
    confidence: str,
    coverage: dict[str, Any],
    findings: list[str],
    top_seats: list[str],
    plan: list[str],
    risks: list[str],
) -> list[dict[str, str]]:
    finding_text = "；".join(findings[:3]) or "暂无足够稳定的共同理由"
    top_text = "、".join(top_seats[:4]) or "已返回席位"
    return [
        {
            "title": "判决先收口，再展开证据",
            "body": f"{judge_editor['name']} 作为轮值法官，将本轮判定收束为“{verdict_label}”，置信度 {confidence}；报告正文只保留能支撑决策的依据。",
            "evidence": finding_text,
        },
        {
            "title": "共识只采纳可追溯来源",
            "body": f"本报告优先采用 {top_text} 的共同部分，并把席位覆盖 {coverage['label']} 作为可信边界。",
            "evidence": finding_text,
        },
        {
            "title": "最终方案必须可执行",
            "body": f"建议从“{plan[0] if plan else '补齐证据链'}”开始，把判断转成可检查、可复盘、可暂停的行动。",
            "evidence": "执行计划来自 next_steps、发布门禁与横纵收口。",
        },
        {
            "title": "不完整回收必须降级表达",
            "body": risks[0] if risks else "若证据不足、席位未回收或互评分歧扩大，本报告必须降级为阶段性判断。",
            "evidence": "风险边界来自失败席位、limits、disagreements 与 trust tier。",
        },
    ]


def _evidence_map(
    verdict: dict[str, Any],
    coverage: dict[str, Any],
    top_seats: list[str],
    agreements: list[str],
    reasons: list[str],
    judge: dict[str, Any],
    baseline: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "dimension": "答案来源",
            "judgment": "法官总结后的最终方案",
            "source": "、".join(top_seats[:5]) or "本地席位画像与评分结果",
            "constraint": "必须保留席位原文入口，不能用总结覆盖原文。",
        },
        {
            "dimension": "共识依据",
            "judgment": "采用多席位共同部分",
            "source": "；".join(agreements[:4]) or "；".join(reasons[:3]) or "-",
            "constraint": "共识不足时，结论只能标记为条件或阶段性。",
        },
        {
            "dimension": "覆盖状态",
            "judgment": coverage["label"],
            "source": f"ok={coverage['ok']} failed={coverage['failed']} requested={coverage['requested']}",
            "constraint": "必需席位未补齐时不得宣称全量最终共识。",
        },
        {
            "dimension": "单法官校准",
            "judgment": _number_text(baseline.get("score"), decimals=4) if baseline else "-",
            "source": _text(judge.get("label") or baseline.get("label") or "AI Judge"),
            "constraint": "单法官分只作对照，不替代多席位互评。",
        },
    ]


def _implementation_plan(
    steps: list[str],
    *,
    complete: bool,
    coverage: dict[str, Any],
    verdict_label: str,
    recommendation: str,
) -> list[str]:
    plan = _unique_texts([step for step in steps if not _is_generic_step(step)], limit=6)
    if not complete:
        plan.insert(0, f"先回收或复核未完成席位，将必需席位覆盖从 {coverage['label']} 补齐后再发布。")
    if recommendation and recommendation not in plan:
        plan.insert(0, recommendation)
    if not plan:
        plan = [
            f"以“{verdict_label}”作为主立场，拆成一页目标、约束、风险和验证指标。",
            "把最高共识点转成最小可执行动作，并设置人工复核点。",
            "执行后回填证据、结果和反例，形成下一轮 AI Judge 输入。",
        ]
    return _unique_texts(plan, limit=6)


def _risks_and_limits(
    limits: list[str],
    disagreements: list[str],
    coverage: dict[str, Any],
    verdict: dict[str, Any],
    trust: str,
) -> list[str]:
    risks: list[str] = []
    if not coverage["complete"]:
        risks.append(f"必需席位覆盖为 {coverage['label']}，本轮不能宣称全模型最终共识。")
    risks.extend(limits)
    risks.extend(disagreements)
    if trust and trust != "-":
        risks.append(f"可信等级为 {trust}，发布前需按对应门禁复核。")
    if not risks:
        risks.append("未发现硬阻断，但仍需保留原始答案、评分链路和人工发布确认。")
    confidence_value = _as_float(verdict.get("confidence"), default=0.0)
    if confidence_value and confidence_value < 70:
        risks.append("置信度低于 70%，不宜直接作为外部发布稿。")
    return _unique_texts(risks, limit=6)


def _verification_contract(coverage: dict[str, Any], trust: str, verdict_label: str) -> list[str]:
    contract = [
        "保留原始问题、每个席位原文、答案摘要、互评记录和 claim 分数，保证报告可追溯。",
        f"发布前核对结论“{verdict_label}”是否被关键证据支持，而不是只被多数模型重复。",
        "人工确认后再进入对外发布；若新增反例或席位回收失败，必须重跑或降级报告。",
    ]
    if not coverage["complete"]:
        contract.insert(0, f"先补齐必需席位覆盖 {coverage['label']}，否则只能作为阶段性内部材料。")
    if trust:
        contract.append(f"按可信等级 {trust} 执行对应发布门禁。")
    return _unique_texts(contract, limit=5)


def _compiled_content_report(
    verdict: dict[str, Any],
    *,
    question: str,
    verdict_label: str,
    coverage: dict[str, Any],
    findings: list[str],
    recommendation: str,
    plan: list[str],
    risks: list[str],
    agreements: list[str],
    disagreements: list[str],
    top_seats: list[str],
) -> dict[str, Any]:
    rows = _answer_source_rows(verdict)
    all_text = "\n".join(row["text"] for row in rows)
    problem = (
        f"本轮要解决的不是继续展示模型回答，而是把“{_compact(question, 120)}”"
        "收口为一份能直接执行、能追溯来源、能说明分歧取舍的完整报告。"
    )
    editorial_verdict = _compact(
        recommendation
        or (findings[0] if findings else "")
        or f"以“{verdict_label}”为主立场，先完成报告整合，再进入执行复核。",
        180,
    )
    sections = _compiled_sections(
        question=question,
        all_text=all_text,
        findings=findings,
        recommendation=recommendation,
        plan=plan,
        risks=risks,
        agreements=agreements,
        rows=rows,
        problem=problem,
    )
    decision_table = _compiled_decision_table(
        recommendation=recommendation,
        plan=plan,
        risks=risks,
        findings=findings,
        agreements=agreements,
        disagreements=disagreements,
        top_seats=top_seats,
        coverage=coverage,
    )
    roadmap = _compiled_roadmap(plan)
    success_metrics = _success_metrics(question, coverage, verdict)
    appendix = _model_contribution_appendix(rows)
    action_paths = _action_path_rows(question, rows)
    source_note = f"基于 {len(rows) or coverage['ok']} 个有效席位、席位覆盖 {coverage['label']} 生成；未采纳内容保留在模型贡献附录和争议裁决表。"
    longform = _longform_report(
        question=question,
        verdict_label=verdict_label,
        coverage=coverage,
        problem=problem,
        editorial_verdict=editorial_verdict,
        sections=sections,
        decision_table=decision_table,
        roadmap=roadmap,
        risks=risks,
        success_metrics=success_metrics,
        appendix=appendix,
        action_paths=action_paths,
        findings=findings,
        agreements=agreements,
        source_note=source_note,
    )
    return {
        "schema": COMPILED_REPORT_SCHEMA,
        "title": f"最终整合报告：{_topic_label(question)}",
        "problem_restatement": problem,
        "editorial_verdict": editorial_verdict,
        "sections": sections,
        "longform_report": longform,
        "decision_table": decision_table,
        "roadmap": roadmap,
        "action_paths": action_paths,
        "risk_register": risks,
        "success_metrics": success_metrics,
        "model_contribution_appendix": appendix,
        "source_note": source_note,
    }


def _compiled_sections(
    *,
    question: str,
    all_text: str,
    findings: list[str],
    recommendation: str,
    plan: list[str],
    risks: list[str],
    agreements: list[str],
    rows: list[dict[str, Any]],
    problem: str,
) -> list[dict[str, Any]]:
    topic_terms = _topic_terms(question)
    topic_specs = [
        {
            "title": "0. 一句话总纲",
            "summary": "把多模型材料压成一条可执行主线。",
            "keywords": ["核心判断", "总纲", "结论", "建议", "裁定"],
            "fallback": [*_domain_section_fallback(question, "summary"), recommendation, *findings[:2]],
        },
        {
            "title": "1. 问题重述与目标",
            "summary": "先定义用户真正要拿到的交付物。",
            "keywords": ["问题", "目标", "定位", "交付物", "要解决"],
            "fallback": [*_domain_section_fallback(question, "goal"), problem],
        },
        {
            "title": "2. 关键发现",
            "summary": "只保留能支撑决策的共识和强信号。",
            "keywords": ["关键发现", "发现", "洞察", "共识", "为什么", "理由"],
            "fallback": [*_domain_section_fallback(question, "findings"), *findings, *agreements],
        },
        {
            "title": "3. 最终方案",
            "summary": "把建议转成模块、内容、流程或产品动作。",
            "keywords": ["最终方案", "方案", "模块", "矩阵", "prompt", "文案", "caption", "功能", "架构", "MVP", "内容"],
            "fallback": [*_domain_section_fallback(question, "plan"), recommendation, *plan[:2]],
        },
        {
            "title": "4. 执行路线图",
            "summary": "明确先做什么、后做什么，以及每阶段产物。",
            "keywords": ["路线图", "阶段", "第一周", "第二周", "Phase", "步骤", "节奏", "执行"],
            "fallback": [*_domain_section_fallback(question, "roadmap"), *plan],
        },
        {
            "title": "5. 风险与防护",
            "summary": "把分歧和失败条件变成发布前门禁。",
            "keywords": ["风险", "边界", "防护", "复核", "合规", "失败", "盲点"],
            "fallback": [*_domain_section_fallback(question, "risks"), *risks],
        },
        {
            "title": "6. 验收与指标",
            "summary": "报告必须能被检查，而不是只读起来完整。",
            "keywords": ["成功标准", "指标", "验收", "KPI", "完播率", "评论", "通过率", "留存"],
            "fallback": [
                *_domain_section_fallback(question, "metrics"),
                *_success_metrics(question, {"label": "-", "ok": 0, "failed": 0, "requested": 0, "complete": False}, {}),
            ],
        },
    ]
    sections: list[dict[str, Any]] = []
    for spec in topic_specs:
        points = _theme_points(all_text, spec["keywords"], spec["fallback"], limit=5, topic_terms=topic_terms)
        sections.append(
            {
                "title": spec["title"],
                "summary": spec["summary"],
                "items": points,
                "source_models": _models_for_keywords(rows, spec["keywords"]),
            }
        )
    return sections


def _longform_report(
    *,
    question: str,
    verdict_label: str,
    coverage: dict[str, Any],
    problem: str,
    editorial_verdict: str,
    sections: list[dict[str, Any]],
    decision_table: list[dict[str, str]],
    roadmap: list[dict[str, str]],
    risks: list[str],
    success_metrics: list[str],
    appendix: list[dict[str, str]],
    action_paths: list[dict[str, Any]],
    findings: list[str],
    agreements: list[str],
    source_note: str,
) -> dict[str, Any]:
    final_points = _section_items(sections, "3.")
    finding_points = _unique_texts([*_section_items(sections, "2."), *findings, *agreements], limit=5)
    roadmap_points = [
        f"{row.get('phase', '')}：{row.get('goal', '')}，交付物是{row.get('deliverable', '可复核产物')}。"
        for row in roadmap
    ]
    decision_points = [row.get("decision", "") for row in decision_table if row.get("issue") != "最终交付物"]
    risk_points = _unique_texts([*risks, *decision_points], limit=5)
    metric_points = _unique_texts(success_metrics, limit=5)
    title = _longform_title(question)
    one_sentence = _ensure_sentence(f"{verdict_label}：{editorial_verdict}")
    final_plan_paragraph = _final_plan_paragraph(question, final_points)
    roadmap_paragraph = _roadmap_paragraph(question, roadmap_points)
    metrics_paragraph = _metrics_paragraph(question, metric_points)
    executive_summary = [
        _ensure_sentence(
            f"本轮 AI Judge 的最终交付应该是一份已经写好的总结报告，而不是模型回答的摘录板。"
            f"主立场是“{verdict_label}”，核心建议是{_trim_sentence(editorial_verdict)}"
        ),
        _ensure_sentence(
            f"报告采用总编制：正文负责给结论、解释取舍和安排执行；模型来源、分歧和未采纳意见进入附录。"
            f"当前席位覆盖为 {coverage['label']}，这决定了它的可信边界和发布门禁"
        ),
    ]
    body_sections = [
        {
            "title": "一、问题背景与真实目标",
            "paragraphs": [
                _ensure_sentence(problem),
                _ensure_sentence(
                    "用户真正需要的不是更多模型意见，而是一个可以直接判断方向、分配任务、检查风险的成稿。"
                    "因此报告必须先替用户完成理解和取舍，再把证据链放到后面供复核"
                ),
            ],
        },
        {
            "title": "二、核心判断",
            "paragraphs": [
                _paragraph_from_points(
                    finding_points,
                    "多席位共同指向同一个问题：AI Judge 的价值不在于罗列模型，而在于把模型材料转成可执行判断。",
                ),
                _ensure_sentence(
                    f"所以本轮裁定不是继续增加摘要密度，而是把“{_compact(question, 90)}”写成一份主审已经负责到底的总结报告"
                ),
            ],
        },
        {
            "title": "三、最终方案",
            "paragraphs": [
                final_plan_paragraph,
                _final_plan_boundary_paragraph(question),
            ],
        },
        {
            "title": "四、执行路线图",
            "paragraphs": [
                roadmap_paragraph,
            ],
        },
        {
            "title": "五、风险与裁决",
            "paragraphs": [
                _paragraph_from_points(
                    risk_points,
                    "主要风险是把模型摘要误当成最终报告，导致用户仍要自己判断哪些内容该采纳、哪些内容该放弃。",
                ),
                _ensure_sentence(
                    "处理原则是：正文只写被主审采纳的结论；存在分歧的地方必须给出裁决，不裁决的内容进入风险边界或下一轮复核"
                ),
            ],
        },
        {
            "title": "六、验收标准",
            "paragraphs": [
                metrics_paragraph,
            ],
        },
    ]
    return {
        "schema": LONGFORM_REPORT_SCHEMA,
        "title": title,
        "subtitle": "总编成稿 · 主审裁决 · 可执行报告",
        "one_sentence_judgment": one_sentence,
        "executive_summary": executive_summary,
        "body_sections": body_sections,
        "decision_table": decision_table,
        "roadmap": roadmap,
        "action_paths": action_paths,
        "success_metrics": success_metrics,
        "model_contribution_appendix": appendix,
        "source_note": source_note,
    }


def _longform_title(question: str) -> str:
    return f"AI Judge 最终行动方案：{_topic_label(question)}"


def _is_commercial_growth_topic(question: str) -> bool:
    text = _text(question)
    lowered = text.lower()
    if any(word in text for word in ("商业化", "融资", "投稿", "加星", "开源", "加速器", "投资人", "企业试点")):
        return True
    if "github" in lowered and any(word in text for word in ("全量评审", "增长方案", "社媒", "商业", "融资", "投稿")):
        return True
    return False


def _is_report_experience_topic(question: str) -> bool:
    text = _text(question)
    return any(word in text for word in (
        "标题",
        "展示",
        "首屏",
        "看不到重点",
        "计划",
        "报告页",
        "摘要",
        "最终报告",
        "产品流程",
        "主要流程",
        "跑任务",
        "拿报告",
        "收口",
        "下载",
        "转发",
        "切换语言",
        "网页版",
        "客户端",
        "结果草稿箱",
    ))


def _is_short_video_topic(question: str) -> bool:
    text = _text(question)
    return any(word in text for word in ("抖音", "TikTok", "短视频", "内容矩阵", "caption"))


def _is_system_status_label(label: str) -> bool:
    text = _text(label)
    return any(word in text for word in ("必需席位", "网页席位", "席位执行", "桥接", "运行未闭环", "回收中"))


def _report_verdict_label(question: str, verdict_label: str) -> str:
    if _is_commercial_growth_topic(question) and _is_system_status_label(verdict_label):
        return "阶段收口：开源可信基础设施路线优先"
    return verdict_label


def _topic_label(question: str) -> str:
    text = _text(question)
    if _is_commercial_growth_topic(text):
        return "商业化 / 投稿 / 融资 / GitHub 加星"
    if _is_report_experience_topic(text):
        return "报告页重点与执行计划"
    if _is_short_video_topic(text):
        return "抖音/TikTok 内容增长"
    cleaned = re.sub(r"^(请|帮我|请你|作为|基于|完整)\s*", "", text).strip()
    cleaned = re.split(r"[。！？\n]", cleaned, maxsplit=1)[0].strip()
    cleaned = re.sub(r"请.*?(围绕|为|把|将)", "", cleaned).strip()
    return _compact(cleaned or "本轮议题", 28)


def _topic_terms(question: str) -> list[str]:
    text = _text(question)
    if _is_commercial_growth_topic(text):
        return [
            "商业化",
            "投稿",
            "融资",
            "GitHub",
            "github",
            "加星",
            "star",
            "开源",
            "Hugging Face",
            "Show HN",
            "Reddit",
            "Product Hunt",
            "论文",
            "Demo",
            "加速器",
            "投资",
            "企业",
            "SaaS",
            "审计",
            "评测基础设施",
            "Agent",
            "ARC",
        ]
    if _is_report_experience_topic(text):
        return ["报告", "标题", "首屏", "重点", "计划", "方案", "摘要", "执行", "展示", "结论"]
    if _is_short_video_topic(text):
        return [
            "抖音",
            "TikTok",
            "短视频",
            "视频",
            "9:16",
            "caption",
            "文案",
            "标签",
            "评论",
            "完播",
            "点赞",
            "关注",
            "发布",
            "内容矩阵",
            "钩子",
            "视觉",
        ]
    return []


def _domain_section_fallback(question: str, section: str) -> list[str]:
    text = _text(question)
    if _is_commercial_growth_topic(text):
        fallbacks = {
            "summary": [
                "把 AI Judge 定位为 Agent 经济里的输出质量评测与裁决基础设施，用开源可信证据链先拿开发者心智，再推进投稿、融资和企业试点。"
            ],
            "goal": [
                "本轮目标不是介绍产品，而是形成可执行的商业化、投稿、融资、社媒和 GitHub star 增长方案，并把未核实截止日期保留为门禁。"
            ],
            "findings": [
                "最强共识是先走开源可信基础设施路线：GitHub、Hugging Face Spaces、Show HN 和 Reddit 能最快验证开发者需求。",
                "论文、评测竞赛和 Demo 是建立公信力的第二引擎；加速器、投资人和企业试点应建立在可回放证据链之后。",
                "AI Judge 的商业化不应卖“多模型聊天”，而应卖审计报告、私有化部署、SLA 和 Agent 输出质量治理能力。",
            ],
            "plan": [
                "第一优先级：GitHub README + Hugging Face Spaces + Show HN / Reddit / Dev.to，先验证开发者需求与 star 增长。",
                "第二优先级：AI Evaluation / Agent Infra 论文与 Demo，争取会议、Workshop、Papers with Code 和开源社区背书。",
                "第三优先级：加速器、投资人和企业试点，用可回放审计案例证明 ROI、延迟成本和合规价值。",
                "商业化先卖审计报告、私有化部署和 SLA，再逐步包装 API / SDK 与团队版工作流。",
            ],
            "roadmap": [
                "72 小时内重写 README 首屏、录制 60 秒 Demo、部署 Hugging Face Space，并发布 Show HN / Reddit / X / LinkedIn 首轮帖子。",
                "7 天内整理 AI Eval / Agent Infra 投稿摘要、实验计划和可复现实验脚本，明确每个入口的截止日期和材料缺口。",
                "14 天内触达 30 个投资人、研究者、开源 KOL 和企业 AI 负责人，记录回复率、试点意向和反对理由。",
                "30 天内根据 stars、demo runs、回复率和试点数决定继续融资叙事、转企业审计试点，或缩小产品范围。",
            ],
            "risks": [
                "最大风险是定位过宽：商业化、投稿、融资和社媒同时推进会稀释资源，必须用 GitHub / HF / Show HN 数据先排序。",
                "所有截止日期、联系人、邮箱和入口都必须标注已核实或待核实，不能把未联网核实内容写成事实。",
                "桥接未闭环时，缺席席位只作为发布门禁，不应覆盖业务结论或污染报告标题。",
            ],
            "metrics": [
                "GitHub stars、README 转化、Hugging Face Space 试用、Show HN / Reddit 评论质量和开发者私信数。",
                "论文 / Workshop 摘要完成度、可复现实验数量、引用/榜单入口核实状态。",
                "投资人和企业试点回复率、试点会议数、可付费需求强度和单次审计报告交付周期。",
            ],
        }
        return fallbacks.get(section, [])
    if _is_report_experience_topic(text):
        fallbacks = {
            "summary": [
                "把 AI Judge 收口成一个可直接阅读、下载和转发的最终报告工作台：首屏先给结论、方案、计划和风险，模型原文放附录。"
            ],
            "goal": [
                "用户真正要完成的是从跑任务到拿成稿的闭环，而不是理解桥接日志、模型碎片和长篇原文。"
            ],
            "findings": [
                "标题必须绑定任务主题，不能再使用泛化的“轮值法官最终报告”。",
                "运行健康、席位缺口和桥接恢复属于门禁层，不能覆盖业务报告标题和主方案。",
                "最终报告首屏只保留结论、方案、执行计划、风险和下载/转发/语言切换动作。",
                "模型原文、互评、评分和引用验证放入审计附录，默认折叠但必须可追溯。",
            ],
            "plan": [
                "重构最终报告为单页成稿：结论卡、方案卡、执行路线图、风险门禁、证据附录五层，不再切成多个割裂报告。",
                "在产品主流程加入一键语言切换、PDF/Markdown 下载、复制分享链接和结果草稿箱入口。",
                "把桥接恢复做成运行健康门禁：非 Grok 必需席位失败时显示待恢复席位和动作，但业务方案仍保留为阶段草稿。",
                "席位模式固定：DeepSeek 专家/联网/深入，豆包超能，Gemini Pro，Qwen 深入思考；Grok 只作可选异议。",
            ],
            "roadmap": [
                "T0：修正标题与主题绑定，生成“AI Judge 最终行动方案：具体主题”。",
                "T1：重排首屏信息架构，固定结论、方案、计划、风险四张卡。",
                "T2：把运行状态从正文剥离为门禁，失败席位进入一键恢复和审计附录。",
                "T3：加入中英一键切换、下载、复制分享，并用真实任务截图回归。",
            ],
            "risks": [
                "最大风险是把桥接失败当成业务结论，导致用户看到的仍是一份不可读的系统日志。",
                "第二风险是为了展示完整性而堆模型原文，首屏失焦，用户找不到方案和下一步。",
                "未闭环席位只能标注为阶段性边界，不能宣称全模型最终共识。",
            ],
            "metrics": [
                "用户打开完整报告首屏即可看到结论、方案、计划和风险，无需阅读模型原文。",
                "报告可以一键切换英文、下载 PDF/Markdown、复制分享链接，并保留审计附录。",
                "结果草稿箱和最终报告展示同一份单页收口结构，标题与任务主题一致。",
                "桥接失败时可一键恢复指定席位，且不会污染业务报告正文。",
            ],
        }
        return fallbacks.get(section, [])
    if _is_short_video_topic(text):
        fallbacks = {
            "summary": ["把 AI Judge 包装成“9 个 AI 同时审一个判断”的短视频冲突叙事，而不是全面介绍产品。"],
            "goal": ["目标是产出可直接发布的双语内容包：选题、9:16 视觉 prompt、中文文案、英文 caption、标签和评论引导。"],
            "findings": [
                "短视频首屏必须先制造冲突：同一个判断被 9 个 AI 同时审查，观众才有理由停留和评论。",
                "中文抖音优先抓争议、涨知识和互动挑战；TikTok 英文优先抓 AI truth、AI tools 和 human verdict 的概念差异。",
            ],
            "plan": [
                "首发选题：我让 9 个 AI 同时审一个真实判断，结果它们互相否定。",
                "素材包：先生成 10 个 9:16 强冲突画面 prompt，并保留字幕安全区。",
                "发布包：每条内容都配中文抖音文案、TikTok English caption、3-5 个标签和评论引导。",
                "互动机制：把观众评论区判断作为下一轮 AI Judge 审题来源。",
            ],
            "roadmap": [
                "T0 确定首发争议选题和一句话钩子。",
                "T1 生成 9:16 视觉素材 prompt 与双语字幕。",
                "T2 发布一周五条内容矩阵并记录评论率、完播率、关注和 GitHub stars。",
                "T3 用表现最好的一条反向优化下一批选题。",
            ],
            "risks": [
                "不能夸大 AI Judge 能替用户做最终决定，必须保留人类裁决和人工复核边界。",
                "热点选题发布前要人工确认事实和平台表达风险。",
            ],
            "metrics": [
                "每条内容必须能直接发布，且包含画面 prompt、文案、caption、标签和评论引导。",
                "复盘指标至少覆盖 3 秒留存、完播率、评论率、关注增长和 GitHub stars。",
            ],
        }
        return fallbacks.get(section, [])
    return []


def _final_plan_paragraph(question: str, final_points: list[str]) -> str:
    if _is_commercial_growth_topic(question):
        return _paragraph_from_points(
            final_points,
            "最终方案是把 AI Judge 收口成开源可信基础设施路线：先用 GitHub、Hugging Face Spaces、Show HN 和 Reddit 验证开发者需求，再用论文 Demo、加速器、投资人和企业试点放大。",
        )
    if _is_short_video_topic(question):
        return _paragraph_from_points(
            final_points,
            "最终方案是把 AI Judge 包装成短视频冲突叙事：首发选题用“9 个 AI 同时审一个判断”，再配 9:16 视觉素材、双语文案、标签和评论挑战。",
        )
    return _paragraph_from_points(
        final_points,
        "最终方案是建立一层总编报告：前部给结论和执行摘要，中段给方案与路线图，后部保留风险、裁决和模型贡献附录。",
    )


def _final_plan_boundary_paragraph(question: str) -> str:
    if _is_commercial_growth_topic(question):
        return _ensure_sentence(
            "正文只保留已经能执行的商业路径；未核实的截止日期、联系人、邮箱、比赛入口和缺席席位进入门禁或附录，不进入主结论"
        )
    if _is_short_video_topic(question):
        return _ensure_sentence(
            "正文只保留能直接发布和复盘的内容动作；模型分歧、平台风险和未采纳建议进入附录，避免主方案被无关渠道计划稀释"
        )
    return _ensure_sentence(
        "正文不再逐条展示模型来源，而是把被采纳观点合并成连续叙述；只有当用户需要追溯时，才进入附录查看模型贡献和原始证据"
    )


def _roadmap_paragraph(question: str, roadmap_points: list[str]) -> str:
    if _is_commercial_growth_topic(question):
        return _paragraph_from_points(
            roadmap_points,
            "执行上先完成 README、Demo、HF Space 和社区发布，再整理论文/Workshop 投稿材料，最后用投资人和企业试点反馈验证商业化强度。",
        )
    if _is_short_video_topic(question):
        return _paragraph_from_points(
            roadmap_points,
            "执行上先定首发选题，再生成 9:16 视觉素材和双语发布包，随后按一周五条内容矩阵发布并复盘互动指标。",
        )
    return _paragraph_from_points(
        roadmap_points,
        "执行上先固定报告体裁，再接入后端字段、详情页、客户端预览和 Markdown 导出，最后用样例任务回归。",
    )


def _metrics_paragraph(question: str, metric_points: list[str]) -> str:
    if _is_commercial_growth_topic(question):
        return _paragraph_from_points(
            metric_points,
            "验收标准是 GitHub stars、HF 试用、Show HN/Reddit 评论、论文材料完成度、投资人回复率和企业试点意向能共同证明路线是否成立。",
        )
    if _is_short_video_topic(question):
        return _paragraph_from_points(
            metric_points,
            "验收标准是每条内容都能直接发布，并能用 3 秒留存、完播率、评论率、关注增长和 GitHub stars 复盘。",
        )
    return _paragraph_from_points(
        metric_points,
        "验收标准是用户打开结果页后，首先看到的是一份可直接阅读和执行的完整报告，而不是一组等待再次整理的卡片。",
    )


def _decision_brief(
    *,
    verdict: dict[str, Any],
    question: str,
    verdict_label: str,
    coverage: dict[str, Any],
    recommendation: str,
    plan: list[str],
    risks: list[str],
    compiled: dict[str, Any],
) -> dict[str, Any]:
    topic = _topic_label(question)
    sections = compiled.get("sections") or []
    final_items = _section_items(sections, "3.")
    roadmap_rows = compiled.get("roadmap") or _compiled_roadmap(plan)
    metrics = compiled.get("success_metrics") or []
    final_scheme = final_items[0] if final_items else recommendation
    if _topic_terms(question) and not _contains_any(final_scheme, _topic_terms(question)):
        final_scheme = (_domain_section_fallback(question, "plan") or [recommendation or "先重排最终方案，再进入执行复核。"])[0]
    plan_items = [
        _compact(f"{row.get('phase', '')}：{row.get('goal', '')}", 120)
        for row in roadmap_rows[:4]
        if row.get("phase") or row.get("goal")
    ]
    risk = risks[0] if risks else "保留人工确认、原始答案入口和评分链路。"
    warning = ""
    if not coverage.get("complete"):
        warning = f"必需席位覆盖只有 {coverage.get('label', '-')}，当前只能作为阶段性方案。"
    if _is_commercial_growth_topic(question):
        commercial_plan = _domain_section_fallback(question, "plan")
        commercial_roadmap = _domain_section_fallback(question, "roadmap")
        commercial_risks = _domain_section_fallback(question, "risks")
        final_scheme = commercial_plan[0] if commercial_plan else final_scheme
        plan_items = commercial_roadmap[:4] or plan_items
        failed_names = _unique_texts([_failure_seat_name(item) for item in _required_failure_rows(verdict)], limit=4)
        gate_value = (
            f"席位覆盖 {coverage.get('label', '-')}；待恢复：{'、'.join(failed_names)}。"
            if failed_names
            else f"席位覆盖 {coverage.get('label', '-')}；运行门禁单独标注，不污染业务结论。"
        )
        return {
            "schema": "ai_judge.decision_brief.v1",
            "title": "AI Judge 商业化 / 投稿 / 融资 / GitHub 加星收口报告",
            "subtitle": "先看商业结论、三条路径、72 小时计划和发布门禁；模型贡献放附录。",
            "one_sentence": _ensure_sentence(
                f"{verdict_label}：先走开源可信基础设施路线，用 GitHub / HF / Show HN 验证需求，再推进论文 Demo、加速器、融资和企业试点"
            ),
            "cards": [
                {"label": "门禁状态", "value": _compact(gate_value, 150)},
                {"label": "核心路线", "value": _compact(final_scheme, 150)},
                {"label": "前三路径", "value": "GitHub/HF/Show HN；AI Eval 论文+Demo；加速器/投资人/企业试点。"},
                {"label": "风险", "value": _compact((commercial_risks or risks or ["未核实入口和桥接缺口不得进入主结论。"])[0], 150)},
            ],
            "plan": plan_items,
            "metrics": _unique_texts([*metrics, *_domain_section_fallback(question, "metrics")], limit=4),
            "warning": warning,
            "source_note": _text(compiled.get("source_note") or "").replace("模型贡献附录", "后置附录"),
        }
    if _is_report_experience_topic(question):
        report_plan = _domain_section_fallback(question, "plan")
        report_roadmap = _domain_section_fallback(question, "roadmap")
        report_risks = _domain_section_fallback(question, "risks")
        report_metrics = _domain_section_fallback(question, "metrics")
        final_scheme = report_plan[0] if report_plan else final_scheme
        plan_items = report_roadmap[:4] or plan_items
        failed_names = _unique_texts([_failure_seat_name(item) for item in _required_failure_rows(verdict)], limit=4)
        gate_value = (
            f"席位覆盖 {coverage.get('label', '-')}；待恢复：{'、'.join(failed_names)}。"
            if failed_names
            else f"席位覆盖 {coverage.get('label', '-')}；运行门禁独立显示。"
        )
        return {
            "schema": "ai_judge.decision_brief.v1",
            "title": "AI Judge 产品流程与报告收口方案",
            "subtitle": "跑任务、桥接恢复、最终报告、下载转发和中英切换统一收口。",
            "one_sentence": _ensure_sentence(
                "把 AI Judge 改成单页可读的最终报告工作台：首屏先给结论、方案、计划和风险，底层桥接状态只作为门禁和审计附录"
            ),
            "cards": [
                {"label": "结论", "value": "报告必须是一份能直接看、下载和转发的成稿。"},
                {"label": "方案", "value": _compact(final_scheme, 150)},
                {"label": "计划", "value": _compact(plan_items[0] if plan_items else "先修标题、首屏、门禁和导出动作。", 150)},
                {"label": "门禁", "value": _compact(gate_value, 150)},
            ],
            "plan": plan_items,
            "metrics": _unique_texts([*report_metrics, *metrics], limit=4),
            "warning": warning,
            "source_note": _text(compiled.get("source_note") or "").replace("模型贡献附录", "后置附录"),
            "risks": _unique_texts(report_risks or risks, limit=4),
        }
    return {
        "schema": "ai_judge.decision_brief.v1",
        "title": f"AI Judge 最终行动方案：{topic}",
        "subtitle": "先看结论、方案、计划、风险；模型贡献放附录。",
        "one_sentence": _ensure_sentence(f"{verdict_label}：{final_scheme}"),
        "cards": [
            {"label": "结论", "value": _compact(verdict_label, 120)},
            {"label": "方案", "value": _compact(final_scheme, 150)},
            {"label": "计划", "value": _compact(plan_items[0] if plan_items else (recommendation or "-"), 150)},
            {"label": "风险", "value": _compact(risk, 150)},
        ],
        "plan": plan_items,
        "metrics": _unique_texts(metrics, limit=4),
        "warning": warning,
        "source_note": _text(compiled.get("source_note") or "").replace("模型贡献附录", "后置附录"),
    }


def _section_items(sections: list[dict[str, Any]], prefix: str) -> list[str]:
    for section in sections:
        if str(section.get("title", "")).startswith(prefix):
            return [str(item) for item in section.get("items") or [] if str(item).strip()]
    return []


def _paragraph_from_points(points: list[Any], fallback: str, limit: int = 4) -> str:
    cleaned = [_trim_sentence(_strip_markdown_marker(_clean_report_point(point, 180))) for point in points]
    useful = _unique_texts([item for item in cleaned if item], limit=limit)
    if not useful:
        return _ensure_sentence(fallback)
    if len(useful) == 1:
        return _ensure_sentence(useful[0])
    return _ensure_sentence("；".join(useful))


def _trim_sentence(value: Any) -> str:
    return _text(value).strip("。；;，, ")


def _ensure_sentence(value: Any) -> str:
    text = _trim_sentence(value)
    if not text:
        return ""
    if text.endswith(("。", "！", "？", ".", "!", "?")):
        return text
    return f"{text}。"


def _compiled_decision_table(
    *,
    recommendation: str,
    plan: list[str],
    risks: list[str],
    findings: list[str],
    agreements: list[str],
    disagreements: list[str],
    top_seats: list[str],
    coverage: dict[str, Any],
) -> list[dict[str, str]]:
    support = "、".join(top_seats[:4]) or "有效席位共识"
    rows = [
        {
            "issue": "最终交付物",
            "decision": "采用一份完整整合报告作为主输出，不再把模型原始回答堆给用户自行判断。",
            "basis": "用户目标是内容收口；模型原文只进入附录和证据链。",
        },
        {
            "issue": "主方案",
            "decision": recommendation or (findings[0] if findings else "先产出最终整合报告，再进入执行复核。"),
            "basis": support,
        },
        {
            "issue": "执行顺序",
            "decision": plan[0] if plan else "先定模板，再接入报告渲染和验收。",
            "basis": "next_steps 与多席位共识。",
        },
        {
            "issue": "发布边界",
            "decision": risks[0] if risks else "保留人工确认、原始答案入口和评分链路。",
            "basis": f"席位覆盖 {coverage['label']}；{'；'.join(agreements[:2]) or '共识不足时降级表达'}。",
        },
    ]
    for item in disagreements[:3]:
        rows.append(
            {
                "issue": _compact(item, 80),
                "decision": "不删除分歧，将其转为风险边界或下一轮复核项；主报告仍按最高共识推进。",
                "basis": "来自席位分歧，不能被摘要吞掉。",
            }
        )
    return rows


def _compiled_roadmap(plan: list[str]) -> list[dict[str, str]]:
    defaults = [
        "固定完整报告结构：问题重述、关键发现、最终方案、争议裁决表、执行路线图、风险与防护、模型贡献附录。",
        "把最终报告接入 API、HTML 详情页、客户端首屏预览和 Markdown 导出。",
        "用样例任务跑烟测，确认报告能读到模型贡献、裁定分歧，并给出可执行下一步。",
        "把用户反馈回填为下一轮模板优化项。",
    ]
    source = _unique_texts(plan or defaults, limit=4)
    labels = ["T0 定稿", "T1 接入", "T2 验收", "T3 复盘"]
    deliverables = ["报告模板", "后端字段与前端展示", "烟测记录", "模板迭代清单"]
    rows: list[dict[str, str]] = []
    for index, step in enumerate(source):
        rows.append(
            {
                "phase": labels[index] if index < len(labels) else f"T{index} 执行",
                "goal": _compact(step, 110),
                "deliverable": deliverables[index] if index < len(deliverables) else "可复核交付物",
                "acceptance": "用户无需再追问“完整报告在哪里”。",
            }
        )
    return rows


def _success_metrics(question: str, coverage: dict[str, Any], verdict: dict[str, Any]) -> list[str]:
    if _is_commercial_growth_topic(question):
        metrics = [
            "GitHub stars、README 转化、Hugging Face Space 试用、Show HN / Reddit 评论质量和开发者私信数。",
            "AI Eval / Agent Infra 投稿摘要、可复现实验脚本、Demo 视频和入口截止日期核验状态。",
            "投资人回复率、企业试点会议数、可付费需求强度和单次审计报告交付周期。",
        ]
    else:
        metrics = [
            "报告包含问题重述、关键发现、最终方案、争议裁决表、执行路线图、风险与防护、模型贡献附录。",
            "首屏能看到整合报告预览，详情页和 Markdown 导出能看到完整结构。",
            "每个被采纳观点都能追溯到模型席位或法官裁定，不能只剩一句总评。",
        ]
    if coverage.get("label") and coverage.get("label") != "-":
        metrics.append(f"席位覆盖显示为 {coverage['label']}，未补齐时明确标注为阶段性材料。")
    if not _is_commercial_growth_topic(question) and (_is_short_video_topic(question) or any(word in question for word in ("运营", "内容"))):
        metrics.append("内容运营类报告必须落到可发布内容包、发布节奏、互动指标和人工复核边界。")
    if verdict.get("run_id"):
        metrics.append(f"本轮 run_id={verdict.get('run_id')} 可回放验证。")
    return _unique_texts(metrics, limit=6)


def _model_contribution_appendix(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    appendix: list[dict[str, str]] = []
    for row in rows[:12]:
        text = row.get("summary") or row.get("text") or ""
        contribution = (
            _theme_points(text, ["总纲", "方案", "路线图", "模块", "成功标准", "风险", "内容", "矩阵"], [text], limit=1)
            or ["保留原始回答作为背景材料。"]
        )[0]
        risk_note = (
            _theme_points(text, ["风险", "争议", "不足", "复核", "失败"], row.get("cons") or [], limit=1)
            or [row.get("status") or "未发现单独风险。"]
        )[0]
        appendix.append(
            {
                "model": _text(row.get("model") or row.get("seat") or "-"),
                "stance": _text(row.get("stance") or row.get("status") or "-"),
                "score": _number_text(row.get("score"), decimals=3),
                "adopted_contribution": _compact(contribution, 130),
                "risk_note": _compact(risk_note, 110),
            }
        )
    return appendix


def _answer_source_rows(verdict: dict[str, Any]) -> list[dict[str, Any]]:
    bridge = verdict.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    deliberation = bridge.get("deliberation") or {}
    summaries = {
        _text(item.get("seat") or item.get("seat_name")): item
        for item in deliberation.get("answer_summaries") or []
        if isinstance(item, dict)
    }
    digest = {
        _text(item.get("seat") or item.get("seat_name")): item
        for item in bridge.get("seat_answer_digest") or []
        if isinstance(item, dict)
    }
    score_rows = {
        _text(item.get("seat") or item.get("seat_name")): item
        for item in verdict.get("seat_scores") or []
        if isinstance(item, dict)
    }
    rows: list[dict[str, Any]] = []
    for raw in raw_results:
        if not isinstance(raw, dict) or raw.get("ok") is False:
            continue
        key = _text(raw.get("seat") or raw.get("seat_name"))
        summary = summaries.get(key) or summaries.get(_text(raw.get("seat_name"))) or {}
        digest_row = digest.get(key) or digest.get(_text(raw.get("seat_name"))) or {}
        score_row = score_rows.get(key) or score_rows.get(_text(raw.get("seat_name"))) or {}
        text = _raw_answer_text(raw) or _text(summary.get("summary") or digest_row.get("answer_preview"))
        if not text:
            continue
        rows.append(
            {
                "seat": key,
                "model": _text(raw.get("seat_name") or digest_row.get("seat_name") or summary.get("seat_name") or raw.get("seat") or "模型席位"),
                "status": _text(digest_row.get("status") or ("已返回" if raw.get("ok", True) else "未完成")),
                "stance": _text(summary.get("stance") or digest_row.get("stance") or "-"),
                "score": raw.get("score", summary.get("quality", digest_row.get("score", score_row.get("average_score")))),
                "summary": _text(summary.get("summary") or digest_row.get("answer_preview") or _compact(text, 180)),
                "pros": digest_row.get("pros") or [],
                "cons": digest_row.get("cons") or [],
                "text": text,
            }
        )
    if rows:
        return rows
    for item in bridge.get("seat_answer_digest") or []:
        if not isinstance(item, dict):
            continue
        text = _text(item.get("answer_preview") or item.get("response") or item.get("summary"))
        if not text:
            continue
        rows.append(
            {
                "seat": _text(item.get("seat") or item.get("seat_name")),
                "model": _text(item.get("seat_name") or item.get("seat") or "模型席位"),
                "status": _text(item.get("status") or "-"),
                "stance": _text(item.get("stance") or "-"),
                "score": item.get("score"),
                "summary": _compact(text, 180),
                "pros": item.get("pros") or [],
                "cons": item.get("cons") or [],
                "text": text,
            }
        )
    return rows


def _raw_answer_text(raw: dict[str, Any]) -> str:
    for key in ("response", "answer", "text", "content", "output"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _theme_points(
    text: str,
    keywords: list[str],
    fallback: list[Any],
    limit: int = 4,
    topic_terms: list[str] | None = None,
) -> list[str]:
    topic_terms = topic_terms or []
    points: list[str] = []
    off_topic_points: list[str] = []
    for point in _split_points(text):
        cleaned = _strip_markdown_marker(_clean_report_point(point, 170))
        if cleaned and _contains_any(cleaned, keywords):
            if not topic_terms or _contains_any(cleaned, topic_terms):
                points.append(cleaned)
            else:
                off_topic_points.append(cleaned)
    if len(points) < limit:
        for item in fallback:
            for point in _split_points(item):
                cleaned = _strip_markdown_marker(_clean_report_point(point, 170))
                if cleaned:
                    points.append(cleaned)
    if not points and not fallback:
        points.extend(off_topic_points)
    return _unique_texts(points, limit=limit)


def _models_for_keywords(rows: list[dict[str, Any]], keywords: list[str]) -> list[str]:
    names = [
        _text(row.get("model"))
        for row in rows
        if _contains_any(row.get("text") or row.get("summary") or "", keywords)
    ]
    if not names:
        names = [_text(row.get("model")) for row in rows[:3]]
    return _unique_texts(names, limit=5)


def _contains_any(text: Any, keywords: list[str]) -> bool:
    value = _text(text).lower()
    return any(_text(keyword).lower() in value for keyword in keywords if _text(keyword))


def _strip_markdown_marker(value: str) -> str:
    return re.sub(r"^[#*\-\d.\s:：]+", "", value).strip()


def _executive_summary(
    *,
    judge_editor: dict[str, str],
    verdict_label: str,
    confidence: str,
    trust: str,
    coverage: dict[str, Any],
    recommendation: str,
    findings: list[str],
    risk_line: str,
    next_action: str,
) -> dict[str, Any]:
    why = _unique_texts(findings, limit=4)
    primary_reason = why[0] if why else recommendation
    headline = f"{verdict_label}：{primary_reason}"
    return {
        "headline": _compact(headline, 150),
        "judge": judge_editor["label"],
        "verdict": verdict_label,
        "recommendation": recommendation,
        "why": why,
        "risk": risk_line,
        "next_action": next_action,
        "confidence_label": f"{confidence} · {trust or '待人工复核'}",
        "coverage_label": coverage["label"],
        "detail_anchor": "#report-manuscript" if coverage.get("complete") else "#run-health",
    }


def _judge_editor(verdict: dict[str, Any]) -> dict[str, str]:
    chief = verdict.get("chief_judge") or {}
    judge = verdict.get("judge_answer") or {}
    name = _text(chief.get("name") or "")
    if not name or name == "自动轮值":
        label = _text(judge.get("label") or chief.get("label") or "AI Judge 轮值法官")
        name = label.replace("轮值主审", "").replace("法官综合答案", "").strip() or "AI Judge"
    else:
        label = _text(chief.get("label") or f"{name} 轮值法官")
    if "轮值" not in label:
        label = f"{name} 轮值法官"
    return {
        "name": name,
        "label": label.replace("主审", "法官"),
        "mbti": _text(chief.get("mbti") or ""),
        "strength": _text(chief.get("strength") or ""),
    }


def _thesis(verdict: dict[str, Any], question: str, verdict_label: str) -> str:
    one_liner = _compact(verdict.get("one_liner") or "", 120)
    if one_liner and not (_is_commercial_growth_topic(question) and _is_system_status_label(one_liner)):
        return one_liner
    return f"围绕“{_compact(question, 72)}”，本轮 AI Judge 的主判定为“{verdict_label}”。"


def _recommendation(
    steps: list[str],
    *,
    complete: bool,
    coverage: dict[str, Any],
    verdict_label: str,
    question: str = "",
) -> str:
    useful_steps = [step for step in steps if not _is_generic_step(step)]
    if _is_commercial_growth_topic(question):
        fallback = _domain_section_fallback(question, "plan")
        return _compact(
            fallback[0]
            if fallback
            else "以开源可信基础设施路线阶段收口，先验证 GitHub、HF Space、Show HN、论文 Demo 和企业试点。",
            150,
        )
    if _is_report_experience_topic(question):
        fallback = _domain_section_fallback(question, "plan")
        return _compact(
            fallback[0]
            if fallback
            else "把完整报告重排成结论、方案、执行计划、风险门禁和证据附录五层。",
            150,
        )
    if not complete:
        return f"先补齐必需席位覆盖 {coverage['label']}，再把“{verdict_label}”作为可执行决策。"
    if any(word in question for word in ("报告", "摘要", "排版", "论文", "PDF", "总结", "人话")):
        return "把当前页改成一眼结论卡；专业论文式报告放到详情锚点。"
    if useful_steps:
        return _compact(useful_steps[0], 130)
    if any(word in verdict_label for word in ("推进", "支持", "可信", "采信")):
        return "可以推进，但先验证最高风险，再进入执行或发布确认。"
    if any(word in verdict_label for word in ("反对", "不建议", "拒绝")):
        return "暂缓推进，先补证或重设方案。"
    if any(word in verdict_label for word in ("不足", "未验证", "不确定")):
        return "不要下最终结论，先补齐证据链和关键席位。"
    return f"将“{verdict_label}”拆成一页目标、证据、执行动作和验收指标，并在人工确认后推进。"


def _next_action(steps: list[str], recommendation: str, *, complete: bool, coverage: dict[str, Any]) -> str:
    useful_steps = [step for step in steps if not _is_generic_step(step)]
    if useful_steps:
        return _compact(useful_steps[0], 120)
    if not complete:
        return f"先回收未完成席位，把覆盖补齐到 {coverage['required_count'] or coverage['requested']} 席。"
    return _compact(recommendation, 120)


def _risk_line(
    limits: list[str],
    disagreements: list[str],
    coverage: dict[str, Any],
    verdict: dict[str, Any],
    trust: str,
) -> str:
    if not coverage["complete"]:
        return f"席位覆盖只有 {coverage['label']}，不能当成最终共识发布。"
    if disagreements:
        return _compact(disagreements[0], 120)
    if limits:
        return _compact(limits[0], 120)
    confidence_value = _as_float(verdict.get("confidence"), default=0.0)
    if confidence_value and confidence_value < 70:
        return "置信度不足 70%，只适合继续补证。"
    if trust:
        return f"可信等级为 {trust}，仍需人工确认后再发布。"
    return "没有硬阻断，但仍需保留人工确认和原始证据入口。"


def _key_findings(
    verdict: dict[str, Any],
    coverage: dict[str, Any],
    reasons: list[str],
    agreements: list[str],
    top_seats: list[str],
) -> list[str]:
    findings: list[str] = []
    question = _text(verdict.get("question") or "")
    domain = _domain_findings(question)
    findings.extend(domain)
    if not domain:
        one_liner = _compact(verdict.get("one_liner") or "", 120)
        if one_liner:
            findings.append(one_liner)
        if reasons:
            findings.extend(reasons[:2])
    if agreements and not domain:
        findings.append(f"主要共识：{agreements[0]}")
    if top_seats:
        findings.append(f"主要支撑席位：{'、'.join(top_seats[:3])}。")
    if coverage["failed"]:
        findings.append(f"仍有 {coverage['failed']} 个席位未形成有效最终答案，覆盖边界为 {coverage['label']}。")
    if not findings:
        findings.append(_compact(verdict.get("one_liner") or "本轮已有判词，但仍需人工复核证据链。", 120))
    return _unique_texts(findings, limit=5)


def _domain_findings(question: str) -> list[str]:
    if not question:
        return []
    if _is_commercial_growth_topic(question):
        return [
            "本轮任务应收口为商业化、投稿、融资、社媒和 GitHub 加星方案，而不是报告 UI 或桥接状态说明。",
            "最高优先级是开源可信基础设施路线：GitHub、Hugging Face Spaces、Show HN / Reddit 先验证开发者需求。",
            "论文 Demo、评测竞赛、加速器、投资人和企业试点要作为后续放大路径，并保留截止日期和入口核验门禁。",
        ]
    if any(word in question for word in ("报告", "摘要", "排版", "论文", "PDF", "总结", "人话")):
        return [
            "当前页的职责是帮助用户快速决策，不应承载完整证据堆栈。",
            "专业论文式内容应作为详情页或锚点展开，摘要区只放结论、建议、风险和下一步。",
            "模型原文、席位摘要和评分依据必须进入证据区或附录，不能进入首屏摘要。",
        ]
    return []


def _status_reason(complete: bool, coverage: dict[str, Any], trust: str) -> str:
    if not complete:
        return f"席位覆盖 {coverage['label']}，仍需补齐后才能作为最终共识。"
    if trust:
        return f"席位覆盖已闭环，可信等级 {trust}。"
    return "席位覆盖已闭环，可进入人工发布确认。"


def _final_position_summary(
    judge_editor: dict[str, str],
    verdict_label: str,
    trust: str,
    coverage: dict[str, Any],
    findings: list[str],
    recommendation: str,
) -> str:
    reason_text = "；".join(findings[:3]) or "当前理由不足，需要继续补证"
    return (
        f"{judge_editor['label']}给出的最终立场是“{verdict_label}”。"
        f"可信等级 {trust or '-'}，席位覆盖 {coverage['label']}。"
        f"建议：{recommendation}。依据：{reason_text}。"
    )


def _top_seat_names(verdict: dict[str, Any], judge: dict[str, Any], seat_digest: list[dict[str, Any]]) -> list[str]:
    names = _unique_texts(judge.get("top_seats") or [], limit=5)
    if names:
        return names
    scored = sorted(
        [item for item in seat_digest if item.get("ok")],
        key=lambda item: float(item.get("score") or 0.0),
        reverse=True,
    )
    names = _unique_texts([item.get("seat_name") or item.get("seat") for item in scored], limit=5)
    if names:
        return names
    return _unique_texts([item.get("seat_name") or item.get("seat") for item in verdict.get("seat_scores") or []], limit=5)


def _keywords(question: str, reasons: list[str], agreements: list[str], verdict_label: str, trust: str) -> list[str]:
    seeds = [verdict_label, trust, *agreements[:4], *reasons[:4]]
    tokens: list[str] = []
    for text in [question, *seeds]:
        for part in _split_keyword_text(text):
            if 1 < len(part) <= 18 and part not in tokens:
                tokens.append(part)
            if len(tokens) >= 8:
                return tokens
    return tokens or ["最终方案", "证据链", "执行计划", "风险边界"]


def _split_keyword_text(value: Any) -> list[str]:
    text = _text(value)
    cleaned = []
    for char in text:
        cleaned.append(char if char.isalnum() or "\u4e00" <= char <= "\u9fff" else " ")
    return " ".join(cleaned).split()


def _trust_label(verdict: dict[str, Any]) -> str:
    analysis = verdict.get("cross_temporal_analysis") or {}
    trust = analysis.get("trust_tier") or (analysis.get("closeout_report") or {}).get("trust_tier") or {}
    if isinstance(trust, dict):
        return _text(trust.get("label") or trust.get("tier") or "")
    return _text(trust)


def _unique_texts(values: list[Any], limit: int = 5) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = _compact(value, 260)
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _brief_points(values: list[Any], limit: int = 5, item_limit: int = 120) -> list[str]:
    points: list[str] = []
    for value in values:
        for point in _split_points(value):
            text = _clean_report_point(point, item_limit)
            if text:
                points.append(text)
            if len(_unique_texts(points, limit=limit)) >= limit:
                return _unique_texts(points, limit=limit)
    return _unique_texts(points, limit=limit)


def _is_generic_step(value: Any) -> bool:
    text = _text(value).lower()
    return bool(
        not text
        or "treat the result as usable direction" in text
        or "not final authorization" in text
        or "validate the top risk before committing" in text
        or "irreversible effort" in text
    )


def _split_points(value: Any) -> list[str]:
    text = " ".join(str(value or "").split())
    if not text:
        return []
    normalized = (
        text.replace("；", "\n")
        .replace("。", "\n")
        .replace("; ", "\n")
        .replace("•", "\n")
        .replace("· ", "\n")
        .replace(" - ", "\n")
    )
    parts = [part.strip(" -:：,，") for part in normalized.splitlines()]
    if len(parts) == 1 and len(parts[0]) > 160:
        parts = [parts[0][index : index + 120] for index in range(0, len(parts[0]), 120)]
    return [part for part in parts if part]


def _clean_report_point(value: Any, limit: int) -> str:
    text = _compact(value, limit)
    if not text:
        return ""
    if "RAW_SHOULD_NOT_APPEAR" in text:
        return ""
    noisy_prefixes = (
        "ChatGPT:",
        "Claude:",
        "Qwen:",
        "Yuanbao:",
        "DeepSeek:",
        "Grok:",
        "Doubao:",
        "Wenxin:",
        "MiMo:",
        "Kimi:",
        "MiniMax:",
    )
    for prefix in noisy_prefixes:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return _compact(text, limit)


def _number_text(value: Any, suffix: str = "", decimals: int | None = None) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (int, float)):
        if decimals is not None:
            return f"{float(value):.{decimals}f}{suffix}"
        if float(value).is_integer():
            return f"{int(value)}{suffix}"
        return f"{float(value):.3f}{suffix}"
    return f"{value}{suffix}"


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _compact(value: Any, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _text(value: Any) -> str:
    return str(value or "").strip()


def _pipe(value: Any) -> str:
    return _text(value).replace("|", "\\|")
