#!/usr/bin/env python3
"""Paper-style final report assembly for AI Judge verdicts."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any

from core.closeout_sop import build_closeout_sop


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
    status_label = "最终报告" if complete else "阶段性报告"
    verdict_label = _text(verdict.get("verdict_label") or verdict.get("verdict") or "待判定")
    confidence = _number_text(verdict.get("confidence"), suffix="%")
    trust = _trust_label(verdict)
    question = _text(verdict.get("question") or "未提供原始问题")
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
    generated_at = _text(verdict.get("created_at") or datetime.now(timezone.utc).isoformat())
    return {
        "schema": FINAL_REPORT_SCHEMA,
        "title": "AI Judge 轮值法官最终报告",
        "subtitle": "JUDGE CLOSEOUT · FINAL RECOMMENDATION · AUDITABLE BASIS",
        "judge_editor": judge_editor,
        "status_label": status_label,
        "status_reason": _status_reason(complete, coverage, trust),
        "executive_summary": executive_summary,
        "abstract": abstract,
        "thesis": thesis,
        "recommendation": recommendation,
        "sop_closeout": closeout_sop,
        "compiled_report": compiled_report,
        "longform_report": compiled_report.get("longform_report"),
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
            "generated_at": generated_at,
            "basis": "模型原始回答、答案总结、席位互评、claim 评分、横纵收口与发布门禁。",
        },
    }


def render_final_report_markdown(report: dict[str, Any]) -> str:
    """Render a final report payload to Markdown."""
    if not report:
        return ""
    executive = report.get("executive_summary") or {}
    sop = report.get("sop_closeout") or {}
    lines: list[str] = [
        f"## {report.get('title') or 'AI Judge 最终方案报告'}",
        "",
        f"**{report.get('subtitle') or FINAL_REPORT_SCHEMA}**",
        "",
        f"**状态:** {report.get('status_label', '-')} · {report.get('status_reason', '-')}",
        "",
        "### 一眼结论",
        "",
        str(executive.get("headline") or report.get("abstract") or ""),
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


def render_final_report_html(report: dict[str, Any]) -> str:
    """Render a final report payload to escaped HTML."""
    if not report:
        return ""
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
    compiled_html = ""
    if longform:
        compiled_html = _longform_report_html(longform)
    elif compiled:
        compiled_html = _compiled_report_html(compiled)
    return (
        '<section class="executive-report" id="final-report">'
        '<p class="paper-kicker">FINAL VERDICT · HUMAN SUMMARY</p>'
        '<h2>最终结论</h2>'
        f'<p class="executive-answer">{html.escape(str(executive.get("headline") or report.get("abstract") or ""))}</p>'
        '<div class="executive-grid">'
        f'<div><span>建议</span><strong>{html.escape(str(executive.get("recommendation") or report.get("recommendation") or "-"))}</strong></div>'
        f'<div><span>风险</span><strong>{html.escape(str(executive.get("risk") or "-"))}</strong></div>'
        f'<div><span>下一步</span><strong>{html.escape(str(executive.get("next_action") or "-"))}</strong></div>'
        f'<div><span>可信度</span><strong>{html.escape(str(executive.get("confidence_label") or "-"))}</strong></div>'
        "</div>"
        '<section class="executive-why"><h3>为什么这样判</h3>'
        f'<ul class="compact-list">{executive_why}</ul></section>'
        '<div class="actions"><a href="#compiled-report">查看完整总结报告</a><a href="#closeout-sop">审计附录</a><a href="#professional-report">旧版法官报告</a></div>'
        "</section>"
        f"{compiled_html}"
        f"{sop_html}"
        '<details class="paper-report audit-appendix" id="professional-report">'
        '<summary><h2>审计附录：旧版法官报告</h2><span>仅用于追溯，不作为默认总结报告</span></summary>'
        '<div class="paper-heading">'
        f'<p class="paper-kicker">{html.escape(str(report.get("subtitle", "")))}</p>'
        f'<h2>{html.escape(str(report.get("title", "AI Judge 最终方案报告")))}</h2>'
        f'<p class="paper-status">{html.escape(str(judge_editor.get("label", "轮值法官")))} · {html.escape(str(report.get("status_label", "-")))} · {html.escape(str(report.get("status_reason", "-")))}</p>'
        "</div>"
        f'<div class="paper-meta">{meta}</div>'
        '<section class="paper-block paper-abstract">'
        "<h3>ABSTRACT</h3>"
        f"<p>{html.escape(str(report.get('abstract', '')))}</p>"
        f'<div class="paper-keywords">{keywords}</div>'
        "</section>"
        '<section class="paper-block">'
        "<h3>FINAL POSITION</h3>"
        f"<p>{html.escape(str(position.get('summary', '')))}</p>"
        "</section>"
        '<section class="paper-columns">'
        '<div class="paper-block paper-callout"><h3>THESIS</h3>'
        f"<p>{html.escape(str(report.get('thesis', '')))}</p></div>"
        '<div class="paper-block paper-callout"><h3>RECOMMENDATION</h3>'
        f"<p>{html.escape(str(report.get('recommendation', '')))}</p></div>"
        "</section>"
        '<section class="paper-block">'
        "<h3>KEY FINDINGS</h3>"
        f'<ul class="compact-list">{findings}</ul>'
        "</section>"
        f'<div class="paper-postulates">{postulates}</div>'
        '<section class="paper-block">'
        "<h3>EVIDENCE MAP</h3>"
        "<table><thead><tr><th>维度</th><th>本报告判断</th><th>证据来源</th><th>约束</th></tr></thead>"
        f"<tbody>{evidence_rows}</tbody></table>"
        "</section>"
        '<section class="paper-columns">'
        '<div class="paper-block"><h3>EXECUTION PLAN</h3>'
        f'<ol class="compact-list">{plan}</ol></div>'
        '<div class="paper-block"><h3>LIMITS</h3>'
        f'<ul class="compact-list">{risks}</ul></div>'
        "</section>"
        '<section class="paper-block">'
        "<h3>VERIFICATION CONTRACT</h3>"
        f'<ul class="compact-list">{contract}</ul>'
        "</section>"
        "</details>"
    )


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


def _longform_report_html(longform: dict[str, Any]) -> str:
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
    metric_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in longform.get("success_metrics", []))
    appendix_rows = _table_rows(
        longform.get("model_contribution_appendix", []),
        ["model", "stance", "adopted_contribution", "risk_note"],
    )
    return (
        '<section class="paper-report longform-report" id="compiled-report">'
        '<div class="paper-heading">'
        '<p class="paper-kicker">EDITORIAL SYNTHESIS · LONGFORM REPORT · 完整总结报告</p>'
        f'<h2>{html.escape(str(longform.get("title", "完整总结报告")))}</h2>'
        f'<p class="paper-status">{html.escape(str(longform.get("subtitle", "总编成稿")))}</p>'
        "</div>"
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


def _compiled_report_html(compiled: dict[str, Any]) -> str:
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
    metric_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in compiled.get("success_metrics", []))
    appendix_rows = _table_rows(compiled.get("model_contribution_appendix", []), ["model", "stance", "adopted_contribution", "risk_note"])
    return (
        '<section class="paper-report compiled-report" id="compiled-report">'
        '<div class="paper-heading">'
        '<p class="paper-kicker">EDITORIAL SYNTHESIS · COMPLETE REPORT</p>'
        f'<h2>{html.escape(str(compiled.get("title", "最终整合报告")))}</h2>'
        f'<p class="paper-status">{html.escape(str(compiled.get("source_note", "")))}</p>'
        "</div>"
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
        findings=findings,
        agreements=agreements,
        source_note=source_note,
    )
    return {
        "schema": COMPILED_REPORT_SCHEMA,
        "title": "最终整合报告",
        "problem_restatement": problem,
        "editorial_verdict": editorial_verdict,
        "sections": sections,
        "longform_report": longform,
        "decision_table": decision_table,
        "roadmap": roadmap,
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
    topic_specs = [
        {
            "title": "0. 一句话总纲",
            "summary": "把多模型材料压成一条可执行主线。",
            "keywords": ["核心判断", "总纲", "结论", "建议", "裁定"],
            "fallback": [recommendation, *findings[:2]],
        },
        {
            "title": "1. 问题重述与目标",
            "summary": "先定义用户真正要拿到的交付物。",
            "keywords": ["问题", "目标", "定位", "交付物", "要解决"],
            "fallback": [problem],
        },
        {
            "title": "2. 关键发现",
            "summary": "只保留能支撑决策的共识和强信号。",
            "keywords": ["关键发现", "发现", "洞察", "共识", "为什么", "理由"],
            "fallback": [*findings, *agreements],
        },
        {
            "title": "3. 最终方案",
            "summary": "把建议转成模块、内容、流程或产品动作。",
            "keywords": ["最终方案", "方案", "模块", "矩阵", "prompt", "文案", "caption", "功能", "架构", "MVP", "内容"],
            "fallback": [recommendation, *plan[:2]],
        },
        {
            "title": "4. 执行路线图",
            "summary": "明确先做什么、后做什么，以及每阶段产物。",
            "keywords": ["路线图", "阶段", "第一周", "第二周", "Phase", "步骤", "节奏", "执行"],
            "fallback": plan,
        },
        {
            "title": "5. 风险与防护",
            "summary": "把分歧和失败条件变成发布前门禁。",
            "keywords": ["风险", "边界", "防护", "复核", "合规", "失败", "盲点"],
            "fallback": risks,
        },
        {
            "title": "6. 验收与指标",
            "summary": "报告必须能被检查，而不是只读起来完整。",
            "keywords": ["成功标准", "指标", "验收", "KPI", "完播率", "评论", "通过率", "留存"],
            "fallback": _success_metrics(question, {"label": "-", "ok": 0, "failed": 0, "requested": 0, "complete": False}, {}),
        },
    ]
    sections: list[dict[str, Any]] = []
    for spec in topic_specs:
        points = _theme_points(all_text, spec["keywords"], spec["fallback"], limit=5)
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
                _paragraph_from_points(
                    final_points,
                    "最终方案是建立一层总编报告：前部给结论和执行摘要，中段给方案与路线图，后部保留风险、裁决和模型贡献附录。",
                ),
                _ensure_sentence(
                    "正文不再逐条展示模型来源，而是把被采纳观点合并成连续叙述；只有当用户需要追溯时，才进入附录查看模型贡献和原始证据"
                ),
            ],
        },
        {
            "title": "四、执行路线图",
            "paragraphs": [
                _paragraph_from_points(
                    roadmap_points,
                    "执行上先固定报告体裁，再接入后端字段、详情页、客户端预览和 Markdown 导出，最后用样例任务回归。",
                )
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
                _paragraph_from_points(
                    metric_points,
                    "验收标准是用户打开结果页后，首先看到的是一份可直接阅读和执行的完整报告，而不是一组等待再次整理的卡片。",
                )
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
        "success_metrics": success_metrics,
        "model_contribution_appendix": appendix,
        "source_note": source_note,
    }


def _longform_title(question: str) -> str:
    if any(word in question for word in ("抖音", "TikTok", "运营", "短视频", "内容")):
        return "AI Judge 抖音/TikTok 运营方案总结报告"
    if any(word in question for word in ("产品", "方案", "落地", "项目")):
        return "AI Judge 最终落地方案总结报告"
    return "AI Judge 最终总结报告"


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
    metrics = [
        "报告包含问题重述、关键发现、最终方案、争议裁决表、执行路线图、风险与防护、模型贡献附录。",
        "首屏能看到整合报告预览，详情页和 Markdown 导出能看到完整结构。",
        "每个被采纳观点都能追溯到模型席位或法官裁定，不能只剩一句总评。",
    ]
    if coverage.get("label") and coverage.get("label") != "-":
        metrics.append(f"席位覆盖显示为 {coverage['label']}，未补齐时明确标注为阶段性材料。")
    if any(word in question for word in ("抖音", "TikTok", "运营", "短视频", "内容")):
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


def _theme_points(text: str, keywords: list[str], fallback: list[Any], limit: int = 4) -> list[str]:
    points: list[str] = []
    for point in _split_points(text):
        cleaned = _strip_markdown_marker(_clean_report_point(point, 170))
        if cleaned and _contains_any(cleaned, keywords):
            points.append(cleaned)
    if len(points) < limit:
        for item in fallback:
            for point in _split_points(item):
                cleaned = _strip_markdown_marker(_clean_report_point(point, 170))
                if cleaned:
                    points.append(cleaned)
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
        "detail_anchor": "#compiled-report",
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
    if one_liner:
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
