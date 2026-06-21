#!/usr/bin/env python3
"""Public report contract and renderers.

This module is the boundary between raw AI Judge run data and shareable report
surfaces. Public renderers must consume only PublicReportViewModel objects.
"""

from __future__ import annotations

import html
from dataclasses import asdict, dataclass, field
from typing import Any


PUBLIC_REPORT_SCHEMA = "ai_judge.public_report_view_model.v1"
JUDGE_VERDICT_SCHEMA = "ai_judge.verdict_document.v1"
HOMESTEAD_TOPIC_ID = "homestead_demolition_compensation"
LOOTBOX_TOPIC_ID = "lootbox_compliance_opinion"
FINANCE_MARKET_TOPIC_ID = "finance_market_timing"
COMMON_CIVIL_LAW_TOPIC_ID = "common_civil_law"
COMMON_PLATFORM_COMPLIANCE_TOPIC_ID = "common_platform_compliance_law"
COMMON_MARKET_RISK_TOPIC_ID = "common_market_risk"
ALLOWED_SURFACES = {"public", "review", "debug"}
LEGAL_SECTION_ALLOWLIST = (
    "cover",
    "one_line_verdict",
    "key_conclusions",
    "case_timeline",
    "rights_structure",
    "litigation_strategy",
    "claims",
    "preservation",
    "compensation_matrix",
    "risks",
    "evidence_checklist",
    "next_actions",
    "limited_audit_appendix",
)
LOOTBOX_SECTION_ALLOWLIST = (
    "cover",
    "one_line_verdict",
    "key_conclusions",
    "rule_decomposition",
    "regulatory_framework",
    "scenario_assessment",
    "abuse_paths",
    "risk_matrix",
    "remediation_plan",
    "launch_checklist",
    "evidence_retention",
    "limited_audit_appendix",
)
FINANCE_SECTION_ALLOWLIST = (
    "cover",
    "one_line_verdict",
    "market_snapshot",
    "judge_reframed_question",
    "scenario_matrix",
    "leverage_risk",
    "catalyst_calendar",
    "decision_framework",
    "risk_matrix",
    "evidence_checklist",
    "next_actions",
    "limited_audit_appendix",
)
FINANCE_DEFAULT_RECOMMENDATION = (
    "不建议把“贷款抄底纳斯达克”作为默认方案；若要参与，只能在可承受最大回撤、"
    "借款成本和止损纪律明确后，用非生活必需资金小仓分批验证。"
)
FINANCE_DEFAULT_RISK = (
    "最大风险不是看错方向本身，而是 30 天窗口内波动、借款成本、现金流压力和"
    "止损失效叠加，导致被迫在低点卖出。"
)
PUBLIC_OPERATIONAL_DECISION_MARKERS = (
    "补跑缺失席位",
    "evidence matrix",
    "正式裁决未签发",
    "阻断诊断单",
    "高风险领域必需席位缺失",
    "当前只能生成",
    "拆成一页目标、证据、执行动作和验收指标",
    "人工确认后推进",
)


@dataclass
class PublicReportViewModel:
    kind: str
    surface: str
    reportId: str
    title: str
    subtitle: str
    verdict: dict[str, Any]
    issue: dict[str, Any]
    keyConclusions: list[str]
    sections: list[dict[str, Any]]
    actionChecklist: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    audit: dict[str, Any]
    schema: str = PUBLIC_REPORT_SCHEMA
    exports: dict[str, str] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_judge_verdict_document(raw: dict[str, Any], *, surface: str = "public") -> dict[str, Any]:
    """Compile raw run data into the AI Judge product verdict document.

    This is the public/export source of truth. Public renderers must consume this
    object instead of raw run_state, seat answers, prompt flow, logs, or browser
    traces.
    """
    surface = surface if surface in ALLOWED_SURFACES else "public"
    if surface == "debug":
        raise ValueError("debug surface cannot use JudgeVerdictDocument public compiler")
    issue = _issue_from_raw(raw)
    audit = _limited_audit(raw)
    evidence_strength = _judge_finance_evidence_strength(raw, audit) if issue.get("topicId") == FINANCE_MARKET_TOPIC_ID else _judge_evidence_strength(raw, audit)
    gate = _judge_verdict_gate(raw, audit, evidence_strength)
    report_kind = "draft_verdict" if not gate["publishable"] else _judge_report_kind(issue)
    title = "AI Judge 阶段性裁决草案" if not gate["publishable"] else "AI Judge 最终裁决报告"
    subtitle = _judge_subtitle(issue)
    doc = {
        "schema": JUDGE_VERDICT_SCHEMA,
        "productRenderer": "ai_judge_verdict",
        "domainTemplate": _judge_domain_template(issue),
        "reportIdentity": {
            "product": "AI Judge",
            "title": title,
            "subtitle": subtitle,
            "runId": _text(raw.get("run_id") or raw.get("id") or "unknown"),
            "mode": _judge_mode(raw),
            "createdAt": _text(raw.get("created_at") or raw.get("finished_at") or raw.get("updated_at") or ""),
            "surface": surface,
            "reportKind": report_kind,
        },
        "verdictGate": gate,
        "council": _judge_council(raw, audit),
        "executiveVerdict": _judge_executive_verdict(raw, issue, gate),
        "issues": _judge_issue_sections(issue, gate),
        "domainMatrices": _judge_domain_matrices(issue),
        "actionPlan": _judge_action_plan(issue, gate),
        "evidenceStrength": evidence_strength,
        "audit": _judge_audit(raw, audit, gate),
    }
    return doc


def render_judge_verdict_html(doc: dict[str, Any]) -> str:
    """Render public/review HTML from JudgeVerdictDocument only."""
    if doc.get("schema") != JUDGE_VERDICT_SCHEMA:
        raise ValueError("render_judge_verdict_html expects JudgeVerdictDocument")
    identity = doc.get("reportIdentity") if isinstance(doc.get("reportIdentity"), dict) else {}
    gate = doc.get("verdictGate") if isinstance(doc.get("verdictGate"), dict) else {}
    title = _text(identity.get("title") or "AI Judge 阶段性裁决草案")
    surface = _text(identity.get("surface") or "public")
    domain_template = _text(doc.get("domainTemplate") or "general_verdict")
    export_label = "导出阶段性草案" if not gate.get("publishable") else "导出正式报告"
    html_body = "\n".join(
        block
        for block in (
            _ai_judge_verdict_hero(doc),
            _executive_decision_strip(doc),
            _judge_key_conclusions(doc),
            _judge_issue_sections_html(doc),
            _judge_domain_matrices_html(doc),
            _judge_risk_and_failure_section(doc),
            _judge_action_plan_section(doc),
            _judge_evidence_strength_section(doc),
            _judge_limited_audit_footer(doc),
        )
        if block
    )
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="ai-judge-surface" content="{html.escape(surface)}">
  <meta name="ai-judge-product-renderer" content="ai_judge_verdict">
  <meta name="ai-judge-domain-template" content="{html.escape(domain_template)}">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; --bg:#f4f6f2; --paper:#fffdf8; --ink:#172033; --muted:#667085; --line:#d7ddcf; --accent:#7c4d1f; --accent2:#1f6b5b; --warn:#9b5200; --bad:#a23232; --soft:#f5eadc; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--ink); letter-spacing:0; }}
    .topbar {{ position:sticky; top:0; z-index:5; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 20px; border-bottom:1px solid var(--line); background:rgba(244,246,242,.96); backdrop-filter:blur(12px); }}
    .topbar strong {{ font-size:14px; }}
    .topbar-actions {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }}
    .topbar button, .topbar a {{ border:1px solid var(--line); border-radius:8px; background:var(--paper); color:var(--ink); padding:8px 11px; font-weight:850; text-decoration:none; cursor:pointer; }}
    main.AiJudgeVerdictReport {{ max-width:1140px; margin:0 auto; padding:26px 20px 58px; }}
    .VerdictHero {{ display:grid; gap:16px; padding:28px 0 22px; border-bottom:1px solid var(--line); }}
    .kicker {{ margin:0; color:var(--accent); font-size:12px; font-weight:900; }}
    h1 {{ margin:0; font-size:38px; line-height:1.14; }}
    h2 {{ margin:0 0 14px; font-size:23px; line-height:1.25; }}
    h3 {{ margin:0 0 8px; font-size:16px; color:var(--accent); }}
    p {{ margin:0; line-height:1.72; }}
    ul, ol {{ margin:0; padding-left:22px; line-height:1.75; }}
    li + li {{ margin-top:6px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th, td {{ border-bottom:1px solid var(--line); padding:10px; text-align:left; vertical-align:top; line-height:1.58; }}
    th {{ background:#eef1ea; color:var(--muted); font-weight:900; }}
    .subtitle {{ color:var(--muted); font-size:17px; }}
    .meta-grid, .ExecutiveDecisionStrip, .issue-grid, .EvidenceStrengthSection .meter-grid, .LimitedAuditFooter .audit-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .meta-card, .decision-card, .issue-card, .matrix-card, .RiskAndFailureSection, .ActionPlanSection, .EvidenceStrengthSection, .LimitedAuditFooter, .KeyConclusions {{ border:1px solid var(--line); border-radius:8px; background:var(--paper); padding:14px; }}
    .meta-card span, .decision-card span, .issue-card span {{ display:block; color:var(--muted); font-size:11px; font-weight:900; margin-bottom:6px; }}
    .meta-card strong, .decision-card strong, .issue-card strong {{ display:block; overflow-wrap:anywhere; line-height:1.42; }}
    .gate-badge {{ display:inline-flex; align-items:center; width:max-content; border:1px solid #d49a60; border-radius:999px; background:#fff6ea; color:var(--warn); padding:6px 10px; font-size:12px; font-weight:900; }}
    .ExecutiveDecisionStrip {{ margin:18px 0; }}
    .decision-card.primary {{ grid-column:span 2; border-color:#d49a60; background:#fff8ef; }}
    .KeyConclusions, .IssueVerdictSection, .DomainMatrixSection, .RiskAndFailureSection, .ActionPlanSection, .EvidenceStrengthSection, .LimitedAuditFooter {{ margin:14px 0; }}
    .IssueVerdictSection {{ border:1px solid var(--line); border-radius:8px; background:var(--paper); padding:16px; }}
    .issue-grid {{ grid-template-columns:1.2fr 1fr 1fr 1fr; }}
    .matrix-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:8px; background:var(--paper); }}
    .pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 8px; background:#fff; color:var(--accent); font-weight:850; font-size:12px; }}
    .risk-high {{ color:var(--bad); font-weight:900; }}
    .risk-medium {{ color:var(--warn); font-weight:900; }}
    @media print {{ .topbar, script {{ display:none !important; }} body {{ background:#fff; }} main.AiJudgeVerdictReport {{ max-width:none; padding:0; }} .IssueVerdictSection, .matrix-card, .decision-card, .meta-card {{ break-inside:avoid; }} }}
    @media (max-width:780px) {{ main.AiJudgeVerdictReport {{ padding:20px 14px 44px; }} h1 {{ font-size:30px; }} .meta-grid, .ExecutiveDecisionStrip, .issue-grid, .EvidenceStrengthSection .meter-grid, .LimitedAuditFooter .audit-grid {{ grid-template-columns:1fr; }} .decision-card.primary {{ grid-column:auto; }} .topbar {{ align-items:flex-start; flex-direction:column; }} }}
  </style>
</head>
<body data-surface="{html.escape(surface)}" data-product-renderer="ai_judge_verdict" data-domain-template="{html.escape(domain_template)}">
<nav class="topbar">
  <strong>AI Judge</strong>
  <div class="topbar-actions">
    <button type="button" data-print-public-report>{html.escape(export_label)}</button>
    <a href="public-report.md" download>下载 Markdown</a>
  </div>
</nav>
<main class="AiJudgeVerdictReport">
{html_body}
</main>
<script>
document.addEventListener("click", (event) => {{
  if (event.target.closest("[data-print-public-report]")) window.print();
}});
</script>
</body>
</html>"""


def render_judge_verdict_markdown(doc: dict[str, Any]) -> str:
    """Render Markdown from the same JudgeVerdictDocument as HTML/PDF."""
    identity = doc.get("reportIdentity") if isinstance(doc.get("reportIdentity"), dict) else {}
    gate = doc.get("verdictGate") if isinstance(doc.get("verdictGate"), dict) else {}
    council = doc.get("council") if isinstance(doc.get("council"), dict) else {}
    executive = doc.get("executiveVerdict") if isinstance(doc.get("executiveVerdict"), dict) else {}
    lines = [
        f"# {_text(identity.get('title') or 'AI Judge 阶段性裁决草案')}",
        "",
        f"> AI Judge · {doc.get('productRenderer')} / {doc.get('domainTemplate')} · {_text(gate.get('label'))} · 有效席位 {council.get('validSeats', 0)}/{council.get('requiredSeats', 0)}",
        "",
        "## 执行裁决",
        "",
        f"- 裁决：{_text(executive.get('oneLine'))}",
        f"- 决策：{_text(executive.get('decision'))}",
        f"- 最大风险：{_text(executive.get('largestRisk'))}",
        f"- 最小下一步：{_text(executive.get('minimumNextStep'))}",
        "",
    ]
    prohibited = executive.get("prohibitedClaimsOrActions") if isinstance(executive.get("prohibitedClaimsOrActions"), list) else []
    if prohibited:
        lines += ["## 禁止动作", ""]
        lines += [f"- {_text(item)}" for item in prohibited]
        lines.append("")
    if doc.get("issues"):
        lines += ["## 核心结论", ""]
        for issue in doc["issues"]:
            lines.append(f"### {_text(issue.get('title'))}")
            lines.append("")
            lines.append(f"- 共识：{_text(issue.get('consensusBadge'))}")
            lines.append(f"- 结论：{_text(issue.get('coreConclusion'))}")
            lines.append(f"- 风险：{_text(issue.get('riskLevel'))}")
            for item in issue.get("actionItems") or []:
                lines.append(f"- 行动：{_text(item)}")
            lines.append("")
    for matrix in doc.get("domainMatrices") or []:
        lines += [f"## {_text(matrix.get('title'))}", ""]
        columns = matrix.get("columns") or []
        rows = matrix.get("rows") or []
        if columns and rows:
            lines.append("| " + " | ".join(_text(c) for c in columns) + " |")
            lines.append("|" + "|".join("---" for _ in columns) + "|")
            for row in rows:
                lines.append("| " + " | ".join(_text(row.get(c, "")).replace("|", "\\|") for c in columns) + " |")
            lines.append("")
    action_plan = doc.get("actionPlan") if isinstance(doc.get("actionPlan"), list) else []
    if action_plan:
        lines += ["## 上线门禁与行动计划", ""]
        lines += [f"- {_text(item)}" for item in action_plan]
        lines.append("")
    evidence = doc.get("evidenceStrength") if isinstance(doc.get("evidenceStrength"), dict) else {}
    lines += [
        "## 证据强度",
        "",
        f"- 法规覆盖：{_text(evidence.get('lawCoverage'))}",
        f"- 案例覆盖：{_text(evidence.get('caseCoverage'))}",
        f"- 交叉验证：{_text(evidence.get('crossValidation'))}",
        f"- 动作：{_text(evidence.get('action'))}",
        "",
    ]
    audit = doc.get("audit") if isinstance(doc.get("audit"), dict) else {}
    summary = audit.get("publicSummary") if isinstance(audit.get("publicSummary"), list) else []
    if summary:
        lines += ["## 有限审计摘要", ""]
        lines += [f"- {_text(item)}" for item in summary]
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_public_report_view_model(raw: dict[str, Any], *, surface: str = "public") -> dict[str, Any]:
    """Compile raw run data into the only object public renderers may consume."""
    surface = surface if surface in ALLOWED_SURFACES else "public"
    issue = _issue_from_raw(raw)
    if issue["topicId"] == HOMESTEAD_TOPIC_ID:
        model = _build_homestead_legal_view_model(raw, surface=surface, issue=issue)
    elif issue["topicId"] == LOOTBOX_TOPIC_ID:
        model = _build_lootbox_compliance_view_model(raw, surface=surface, issue=issue)
    elif issue["topicId"] == FINANCE_MARKET_TOPIC_ID:
        model = _build_finance_market_view_model(raw, surface=surface, issue=issue)
    else:
        model = _build_generic_view_model(raw, surface=surface, issue=issue)
    model.exports["markdown"] = render_public_report_markdown(model.to_public_dict())
    return model.to_public_dict()


def render_public_report_html(model: dict[str, Any]) -> str:
    """Render a shareable public/review report from PublicReportViewModel only."""
    surface = str(model.get("surface") or "public")
    if surface == "debug":
        raise ValueError("debug surface cannot be rendered by public renderer")
    title = _text(model.get("title") or "AI Judge 最终裁决报告")
    subtitle = _text(model.get("subtitle") or "")
    sections = {str(section.get("id") or ""): section for section in model.get("sections") or [] if isinstance(section, dict)}
    model_issue = model.get("issue") if isinstance(model.get("issue"), dict) else {}
    if model.get("kind") in {"legal_lootbox_compliance_opinion", "ai_judge_verdict_document"} or model_issue.get("topicId") == LOOTBOX_TOPIC_ID:
        html_body = _render_lootbox_compliance_body(model, sections)
    elif model.get("kind") == "financial_market_risk_opinion" or model_issue.get("topicId") == FINANCE_MARKET_TOPIC_ID:
        html_body = _render_finance_market_body(model, sections)
    else:
        html_body = "\n".join(
            block
            for block in (
                _report_header(model),
                _verdict_strip(model),
                _action_rail(model),
                _key_conclusions(model),
                _case_timeline(sections.get("case_timeline") or {}),
                _legal_position_card(sections.get("rights_structure") or {}),
                _litigation_plan(sections.get("litigation_strategy") or {}),
                _claims_draft(sections.get("claims") or {}),
                _preservation_plan(sections.get("preservation") or {}),
                _compensation_matrix(sections.get("compensation_matrix") or {}),
                _risk_matrix(sections.get("risks") or {}),
                _evidence_checklist(model),
                _next_actions(model),
                _limited_audit_appendix(model),
            )
            if block
        )
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="ai-judge-surface" content="{html.escape(surface)}">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; --bg:#f6f7f4; --paper:#fffdf8; --ink:#18202f; --muted:#667085; --line:#d8ded5; --accent:#8c4a19; --accent-soft:#f3e3d2; --good:#176a43; --warn:#a35d00; --bad:#a33131; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--ink); letter-spacing:0; }}
    main {{ max-width:1120px; margin:0 auto; padding:28px 20px 56px; }}
    .report-header {{ display:grid; gap:16px; padding:30px 0 24px; border-bottom:1px solid var(--line); }}
    .kicker {{ margin:0; color:var(--accent); font-size:12px; font-weight:850; letter-spacing:0; }}
    h1 {{ margin:0; font-size:38px; line-height:1.16; }}
    h2 {{ margin:0 0 14px; font-size:24px; line-height:1.25; }}
    h3 {{ margin:0 0 8px; font-size:16px; color:var(--accent); }}
    p {{ line-height:1.72; }}
    .subtitle {{ margin:0; color:var(--muted); font-size:17px; }}
    .header-meta, .verdict-strip, .action-rail, .card-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .meta-card, .verdict-card, .action-card, .report-section, .matrix-wrap {{ border:1px solid var(--line); border-radius:8px; background:var(--paper); padding:14px; }}
    .meta-card span, .verdict-card span, .action-card span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; margin-bottom:6px; }}
    .meta-card strong, .verdict-card strong, .action-card strong {{ display:block; overflow-wrap:anywhere; line-height:1.42; }}
    .verdict-strip {{ margin:18px 0; }}
    .verdict-card.primary {{ grid-column:span 2; border-color:#d2a06e; background:#fff8ef; }}
    .action-rail {{ margin:18px 0; }}
    .action-card strong {{ color:var(--accent); }}
    .report-section {{ margin:14px 0; }}
    .lead {{ margin:0; font-size:18px; line-height:1.76; font-weight:800; }}
    ul, ol {{ margin:0; padding-left:22px; line-height:1.75; }}
    li + li {{ margin-top:6px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th, td {{ border-bottom:1px solid var(--line); padding:10px; text-align:left; vertical-align:top; line-height:1.58; }}
    th {{ background:#f2f4ef; color:var(--muted); font-weight:850; }}
    .matrix-wrap {{ overflow:auto; padding:0; }}
    .pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 8px; background:#fff; color:var(--accent); font-weight:800; font-size:12px; }}
    .toolbar {{ position:sticky; top:0; z-index:2; display:flex; justify-content:space-between; align-items:center; gap:12px; padding:12px 20px; background:rgba(246,247,244,.96); border-bottom:1px solid var(--line); backdrop-filter:blur(14px); }}
    .toolbar a, .toolbar button {{ border:1px solid var(--line); border-radius:8px; background:var(--paper); color:var(--ink); padding:8px 11px; font-weight:800; text-decoration:none; cursor:pointer; }}
    .toolbar-actions {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }}
    @media print {{ .toolbar, script {{ display:none !important; }} body {{ background:#fff; }} main {{ max-width:none; padding:0; }} .report-section, .meta-card, .verdict-card, .action-card {{ break-inside:avoid; }} }}
    @media (max-width:760px) {{ main {{ padding:18px 14px 44px; }} h1 {{ font-size:28px; }} .header-meta {{ display:none; }} .verdict-strip, .action-rail {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .verdict-card.primary {{ grid-column:span 2; }} .card-grid {{ grid-template-columns:1fr; }} .toolbar {{ align-items:flex-start; flex-direction:column; }} }}
  </style>
</head>
<body data-surface="{html.escape(surface)}" data-report-kind="{html.escape(_text(model.get('kind')))}">
<nav class="toolbar">
  <strong>{html.escape(title)}</strong>
  <div class="toolbar-actions">
    <button type="button" data-print-public-report>下载 PDF</button>
    <a href="public-report.md" download>下载 Markdown</a>
  </div>
</nav>
<main>
{html_body}
</main>
<script>
document.addEventListener("click", (event) => {{
  if (event.target.closest("[data-print-public-report]")) {{
    window.print();
  }}
}});
</script>
</body>
</html>"""


def render_public_report_markdown(model: dict[str, Any]) -> str:
    """Render markdown from the same PublicReportViewModel as HTML."""
    lines = [
        f"# {_text(model.get('title') or 'AI Judge 最终裁决报告')}",
        "",
        f"> {_text(model.get('subtitle') or '')}",
        "",
    ]
    verdict = model.get("verdict") if isinstance(model.get("verdict"), dict) else {}
    one_line = _text(verdict.get("oneLine") or verdict.get("label") or "")
    if one_line:
        lines += ["## 一句话裁决", "", one_line, ""]
    if model.get("keyConclusions"):
        lines += ["## 核心结论", ""]
        lines += [f"- {_text(item)}" for item in model["keyConclusions"]]
        lines.append("")
    for section in model.get("sections") or []:
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("id") or "")
        if section_id in {"cover", "one_line_verdict", "key_conclusions"}:
            continue
        lines += [f"## {_text(section.get('title') or section_id)}", ""]
        if section.get("body"):
            lines += [_text(section["body"]), ""]
        if isinstance(section.get("items"), list):
            lines += [f"- {_text(item)}" for item in section["items"]]
            lines.append("")
        if section_id == "evidence_checklist":
            evidence = model.get("evidence") if isinstance(model.get("evidence"), list) else []
            public_evidence = [item for item in evidence if isinstance(item, dict)]
            if public_evidence:
                lines += ["| ID | 来源 | 用途/边界 |", "|---|---|---|"]
                for item in public_evidence:
                    title = _text(item.get("title"))
                    url = _text(item.get("url"))
                    source = f"[{title}]({url})" if url else title
                    lines.append(
                        "| "
                        + " | ".join(
                            _markdown_cell(value)
                            for value in (
                                _text(item.get("id")),
                                source,
                                _compact(_text(item.get("summary")), 240),
                            )
                        )
                        + " |"
                    )
                lines.append("")
        if isinstance(section.get("rows"), list):
            columns = section.get("columns") or []
            if columns:
                lines.append("| " + " | ".join(_text(c) for c in columns) + " |")
                lines.append("|" + "|".join("---" for _ in columns) + "|")
                for row in section["rows"]:
                    if isinstance(row, dict):
                        values = [_text(row.get(c, "")) for c in columns]
                    else:
                        values = [_text(value) for value in row]
                    lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
                lines.append("")
    if model.get("actionChecklist"):
        lines += ["## 下一步行动", ""]
        for item in model["actionChecklist"]:
            if isinstance(item, dict):
                lines.append(f"- {_text(item.get('label'))}: {_text(item.get('detail'))}")
            else:
                lines.append(f"- {_text(item)}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _markdown_cell(value: str) -> str:
    return _text(value).replace("|", "\\|").replace("\n", " ")


def render_debug_workbench_html(legacy_html: str) -> str:
    """Mark legacy/raw workbench HTML as a non-public debug surface."""
    banner = (
        '<div class="debug-surface-banner" data-surface="debug" '
        'data-share="disabled" data-access="local-only auth-or-local" '
        'style="padding:12px 18px;background:#2b1d12;color:#fff;font-weight:800;">'
        "DEBUG WORKBENCH · non-public · share-disabled · local-only/auth-or-local"
        "</div>"
    )
    text = str(legacy_html or "")
    if "<head>" in text and 'name="robots"' not in text:
        text = text.replace("<head>", '<head><meta name="robots" content="noindex,nofollow">', 1)
    if "<body" in text:
        close = text.find(">", text.find("<body"))
        if close >= 0:
            return text[: close + 1] + banner + text[close + 1 :]
    return banner + text


def _judge_mode(raw: dict[str, Any]) -> str:
    mode = _text(raw.get("mode") or raw.get("run_mode") or raw.get("requested_mode") or "strategic").lower()
    return mode if mode in {"quick", "strategic", "deep"} else "strategic"


def _judge_report_kind(issue: dict[str, Any]) -> str:
    if issue.get("topicId") == LOOTBOX_TOPIC_ID:
        return "compliance_assessment"
    if issue.get("topicId") == HOMESTEAD_TOPIC_ID:
        return "legal_risk_assessment"
    if issue.get("topicId") == FINANCE_MARKET_TOPIC_ID:
        return "financial_risk_assessment"
    return "final_verdict"


def _judge_domain_template(issue: dict[str, Any]) -> str:
    if issue.get("topicId") == FINANCE_MARKET_TOPIC_ID:
        return "financial_market_risk"
    return "legal_compliance" if issue.get("topicId") in {LOOTBOX_TOPIC_ID, HOMESTEAD_TOPIC_ID} else "general_verdict"


def _judge_subtitle(issue: dict[str, Any]) -> str:
    if issue.get("topicId") == LOOTBOX_TOPIC_ID:
        return "宝箱玩法合规风险评估 · 法律合规模板"
    if issue.get("topicId") == HOMESTEAD_TOPIC_ID:
        return "宅基地房屋拆迁补偿纠纷 · 法律争议模板"
    if issue.get("topicId") == FINANCE_MARKET_TOPIC_ID:
        return "纳斯达克未来 30 天与贷款抄底 · 金融风险模板"
    return _text(issue.get("label") or "综合裁决")


def _judge_verdict_gate(raw: dict[str, Any], audit: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    required = int(audit.get("requiredSeats") or 0)
    valid = int(audit.get("completedRequiredSeats") or 0)
    coverage = (valid / required) if required else 1.0
    gate = raw.get("high_risk_gate") if isinstance(raw.get("high_risk_gate"), dict) else {}
    publish_gate = _text(gate.get("publish_gate") or gate.get("formal_verdict_gate") or gate.get("status"))
    strategic_pass = publish_gate.upper() in {"", "PASS", "PASSED", "ALLOW", "ALLOWED", "OK"}
    degraded = []
    if required and coverage < 0.8:
        degraded.append(f"有效席位 {valid}/{required}，低于 80% 发布阈值")
    if not strategic_pass:
        degraded.append(f"战略门禁未通过：{publish_gate}")
    if evidence.get("action") != "allow":
        degraded.append("证据强度不足以签发正式 public 报告")
    if _text(raw.get("verdict")).lower() in {"unverified", "rejected"}:
        degraded.append(f"运行判定为 {raw.get('verdict')}")
    publishable = not degraded
    status = "credible" if publishable else "hold_for_review"
    return {
        "status": status,
        "label": "Credible" if publishable else "HOLD_FOR_REVIEW",
        "confidence": max(0.0, min(1.0, round(coverage, 2))),
        "publishable": publishable,
        "reason": "席位覆盖、战略门禁和证据强度均满足发布条件" if publishable else "；".join(degraded),
    }


def _judge_evidence_strength(raw: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    required = int(audit.get("requiredSeats") or 0)
    valid = int(audit.get("completedRequiredSeats") or 0)
    coverage = (valid / required) if required else 1.0
    gate = raw.get("high_risk_gate") if isinstance(raw.get("high_risk_gate"), dict) else {}
    publish_gate = _text(gate.get("publish_gate") or gate.get("formal_verdict_gate") or "")
    action = "allow"
    if required and coverage < 0.8:
        action = "hold"
    if publish_gate and "BLOCK" in publish_gate.upper():
        action = "hold"
    if _text(raw.get("verdict")).lower() == "unverified":
        action = "hold"
    return {
        "lawCoverage": "基础法规方向已覆盖；正式签发前需法务复核法规现行有效性和平台适用边界。",
        "caseCoverage": "本轮未形成可公开引用的司法案例矩阵；涉及地区案例时应补充检索和人工核验。",
        "crossValidation": f"有效席位 {valid}/{required}，二轮共振 {audit.get('round2Completed', 0)}/{audit.get('round2Scheduled', 0)}。",
        "bluffIndex": "中" if action != "allow" else "低",
        "evidenceSufficiency": "不足以签发最终裁决" if action != "allow" else "可进入正式发布复核",
        "action": action,
    }


def _judge_finance_evidence_strength(raw: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    required = int(audit.get("requiredSeats") or 0)
    valid = int(audit.get("completedRequiredSeats") or 0)
    coverage = (valid / required) if required else 1.0
    action = "allow" if coverage >= 0.8 and _text(raw.get("verdict")).lower() not in {"unverified", "rejected"} else "hold"
    return {
        "lawCoverage": "不适用：本议题为金融市场风险评估，重点是行情、宏观事件、借款成本和回撤承受证据。",
        "caseCoverage": "不适用：不引用司法案例作为投资判断依据。",
        "crossValidation": f"有效席位 {valid}/{required}，二轮共振 {audit.get('round2Completed', 0)}/{audit.get('round2Scheduled', 0)}。",
        "bluffIndex": "中" if action != "allow" else "低",
        "evidenceSufficiency": "不足以作为个人投资指令" if action != "allow" else "可作为风险讨论材料",
        "action": action,
    }


def _judge_council(raw: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    bridge = raw.get("web_bridge") if isinstance(raw.get("web_bridge"), dict) else {}
    total = int(bridge.get("requested_count") or bridge.get("total_count") or audit.get("requiredSeats") or 0)
    valid = int(audit.get("completedRequiredSeats") or 0)
    required = int(audit.get("requiredSeats") or 0)
    missing = _missing_seat_summaries(raw)
    return {
        "requiredSeats": required,
        "validSeats": valid,
        "totalSeats": total,
        "consensusLabel": f"有效席位 {valid}/{required}，{'阶段性共识不足' if required and valid / required < 0.8 else '可进入正式复核'}",
        "dissentSummary": "；".join(missing[:4]),
    }


def _missing_seat_summaries(raw: dict[str, Any]) -> list[str]:
    bridge = raw.get("web_bridge") if isinstance(raw.get("web_bridge"), dict) else {}
    rows = []
    for item in bridge.get("raw_results") or []:
        if not isinstance(item, dict) or item.get("ok"):
            continue
        seat = _text(item.get("seat"))
        if seat == "grok":
            continue
        err = item.get("error")
        if isinstance(err, dict):
            code = _text(err.get("code"))
            message = ""
        else:
            code = _text(err)
            message = ""
        rows.append(f"{seat}: {_public_failure_code(code or message)}")
    return rows


def _public_failure_code(code: str) -> str:
    text = _text(code).lower()
    if "quality_mode" in text or "mode_not_verified" in text:
        return "quality_mode_not_verified"
    if "prompt_write" in text or "submit" in text or "unconfirmed" in text:
        return "submit_unconfirmed"
    if "quota" in text or "limit" in text or "额度" in text or "上限" in text:
        return "provider_limit"
    if "timeout" in text or "slow" in text:
        return "seat_timeout"
    if "not_found" in text or "missing" in text:
        return "seat_not_found"
    return "seat_missing"


def _judge_executive_verdict(raw: dict[str, Any], issue: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    if issue.get("topicId") == LOOTBOX_TOPIC_ID:
        return {
            "oneLine": "原规则不应直接上线；必须先切断充值赠送自开、主播奖励、随机礼物与任何现金化闭环。",
            "decision": "HOLD_FOR_REVIEW：整改后灰度，不签发正式对外文件。",
            "largestRisk": "主播奖励、随机礼物价值和线下返现一旦形成现金化闭环，可能被监管理解为博彩化、违规抽奖促销或打赏套现。",
            "prohibitedClaimsOrActions": [
                "不得宣传中奖、回本、收益、保值、提现、主播返利。",
                "不得允许宝箱、礼物、账号、主播奖励在平台内外交易、回兑或折现。",
                "不得让未成年人参与充值、开箱、打赏或主播奖励链路。",
                "不得在席位覆盖不足时把本报告包装为正式定稿或对外签发文件。",
            ],
            "minimumNextStep": "上线门禁：取消或重构用户自开路径，冻结主播奖励与随机礼物价值的自动关联，并上线反套现监测。",
        }
    if issue.get("topicId") == HOMESTEAD_TOPIC_ID:
        return {
            "oneLine": "丁可以只起诉甲，但应聚焦非土地性补偿利益和损失赔偿。",
            "decision": "条件支持：先保全、再调证、后起诉。",
            "largestRisk": "甲尚未实际取得补偿款，单纯不当得利给付请求可能条件未成就。",
            "prohibitedClaimsOrActions": ["不要主张宅基地使用权归丁。", "不要主张全部拆迁补偿当然归丁。"],
            "minimumNextStep": "立即调取拆迁协议、补偿明细和付款计划，并申请诉前财产保全。",
        }
    if issue.get("topicId") == FINANCE_MARKET_TOPIC_ID:
        return {
            "oneLine": "不建议把贷款抄底纳斯达克作为默认策略；先完成行情、事件、借款成本和回撤压力测试，再决定是否用闲置资金小仓参与。",
            "decision": "HOLD_FOR_RISK_REVIEW：不得输出确定收益承诺。",
            "largestRisk": "30 天窗口内一旦先跌，借款成本、还款压力、情绪止损和强制卖出会叠加。",
            "prohibitedClaimsOrActions": [
                "不得承诺未来 30 天一定赚钱。",
                "不得用生活资金、信用贷或无法承受回撤的资金满仓抄底。",
                "不得在没有止损、还款来源和最大亏损上限时加仓。",
            ],
            "minimumNextStep": "补齐当前行情和未来 30 天事件日历，先做 5%/10%/15% 回撤压力测试。",
        }
    return {
        "oneLine": _text(raw.get("one_liner") or raw.get("summary") or "请进入人工复核。"),
        "decision": _text(raw.get("verdict") or gate.get("label") or "conditional"),
        "largestRisk": "席位覆盖或证据强度不足时，不应作为正式 public 报告发布。",
        "prohibitedClaimsOrActions": ["不要公开底层提示词、席位原文或浏览器日志。"],
        "minimumNextStep": "补齐缺失席位并复核证据强度。",
    }


def _judge_issue_sections(issue: dict[str, Any], gate: dict[str, Any]) -> list[dict[str, Any]]:
    if issue.get("topicId") == FINANCE_MARKET_TOPIC_ID:
        return [
            {
                "issueId": "finance-market-timing",
                "topic_id": FINANCE_MARKET_TOPIC_ID,
                "title": "纳斯达克未来 30 天走势",
                "consensusBadge": _text(gate.get("label")),
                "coreConclusion": "只能输出概率情景，不能把方向预测写成确定事实。",
                "judgeExplanation": "短期走势受宏观数据、利率、财报、流动性和风险偏好共同影响；模型共识也不能替代实时数据和个人风险承受能力。",
                "riskLevel": "高",
                "requiredControls": ["实时行情核验", "宏观/财报日历", "反方情景", "止损条件"],
                "evidenceRefs": [],
                "actionItems": ["先补齐证据，再做情景矩阵。"],
            },
            {
                "issueId": "finance-loan-bottom-fishing",
                "topic_id": FINANCE_MARKET_TOPIC_ID,
                "title": "贷款抄底是否可取",
                "consensusBadge": "高风险",
                "coreConclusion": "贷款抄底不是默认建议，只有在低成本、低仓位、可承受回撤和书面退出纪律同时满足时才可作为极小比例验证。",
                "judgeExplanation": "贷款资金把普通市场波动变成现金流风险，30 天内横盘或小跌也可能造成负收益。",
                "riskLevel": "高",
                "requiredControls": ["借款成本测算", "最大回撤测算", "还款来源", "禁止补仓条件"],
                "evidenceRefs": [],
                "actionItems": ["完成 5%/10%/15% 回撤压力测试。"],
            },
        ]
    if issue.get("topicId") != LOOTBOX_TOPIC_ID:
        return [
            {
                "issueId": "general-core",
                "topic_id": issue.get("topicId"),
                "title": _text(issue.get("label") or "核心问题"),
                "consensusBadge": _text(gate.get("label")),
                "coreConclusion": "公开报告仅输出裁决编译层，不输出底层调试材料。",
                "judgeExplanation": "该问题需要结合席位覆盖、证据强度和人工复核决定发布口径。",
                "riskLevel": "中",
                "requiredControls": ["复核证据", "补齐缺失席位", "隔离调试材料"],
                "evidenceRefs": [],
                "actionItems": ["进入人工复核。"],
            }
        ]
    return [
        {
            "issueId": "lootbox-user-self-open",
            "topic_id": LOOTBOX_TOPIC_ID,
            "title": "充值赠送宝箱后用户自开",
            "consensusBadge": "高风险一致",
            "coreConclusion": "不建议按原规则保留；充值与随机权益直接绑定，最容易被理解为诱导消费或抽奖式促销。",
            "judgeExplanation": "即使平台禁止回兑，自开路径仍会让用户产生随机财产期待；如果礼物具有稀有度、可展示价值或社交价值，风险会进一步放大。",
            "riskLevel": "高",
            "requiredControls": ["取消自开", "改为无财产期待展示", "显著概率公示", "充值前冷静提示"],
            "evidenceRefs": ["GAME-RANDOM-2016", "PROMOTION-2020"],
            "actionItems": ["上线前删除或重构自开入口。", "营销文案不得出现中奖、回本、收益暗示。"],
        },
        {
            "issueId": "lootbox-gift-only",
            "topic_id": LOOTBOX_TOPIC_ID,
            "title": "游戏币购买宝箱后只能打赏主播",
            "consensusBadge": "条件可控",
            "coreConclusion": "只打赏主播并不天然合规，关键看主播获得的随机礼物能否转化为奖励、分成、等级或外部收益。",
            "judgeExplanation": "如果用户购买宝箱后通过主播开箱间接实现随机收益分配，实质上仍可能构成绕开自开限制的权益转移。",
            "riskLevel": "中高",
            "requiredControls": ["礼物不可交易", "礼物不可回兑", "主播奖励独立核算", "用户与主播关联交易监测"],
            "evidenceRefs": ["GAME-CURRENCY-2009", "MINOR-LIVE-2022"],
            "actionItems": ["重写主播协议和用户规则。", "建立主播-用户串通刷礼物识别。"],
        },
        {
            "issueId": "lootbox-cash-loop",
            "topic_id": LOOTBOX_TOPIC_ID,
            "title": "主播开箱与平台奖励是否形成现金化闭环",
            "consensusBadge": "上线红线",
            "coreConclusion": "主播奖励不得与随机礼物价值、稀有度或开箱结果自动挂钩，否则现金化闭环风险最高。",
            "judgeExplanation": "平台奖励若以打赏量、随机礼物价值、主播任务完成度混同结算，用户充值、主播开箱和奖励支付之间可能形成事实上的资金回流。",
            "riskLevel": "高",
            "requiredControls": ["奖励口径独立", "延迟结算", "异常资金流拦截", "线下返现话术监测"],
            "evidenceRefs": ["ANTI-FRAUD-2022", "LIVE-TIPPING-2026"],
            "actionItems": ["把主播奖励改为服务质量、合规任务和内容表现综合评分。", "对返现、对刷、工作室批量账号设置冻结和封禁。"],
        },
        {
            "issueId": "lootbox-operating-gates",
            "topic_id": LOOTBOX_TOPIC_ID,
            "title": "未成年人、概率公示、反套现与异常交易门禁",
            "consensusBadge": "必须落地",
            "coreConclusion": "规则声明不够，必须以实名年龄识别、限额限次、概率审计、交易拦截和投诉退款 SOP 形成上线门禁。",
            "judgeExplanation": "禁止未成年人、禁止交易、禁止回兑只有进入产品、支付、风控、客服和结算系统，才具有可审计性。",
            "riskLevel": "高",
            "requiredControls": ["未成年禁入", "概率版本留存", "限额限次", "反套现模型", "退款投诉闭环"],
            "evidenceRefs": ["MINOR-GAME-2021", "MINOR-LIVE-2022"],
            "actionItems": ["上线门禁清单逐项验收。", "灰度期每天复盘异常充值、投诉退款和主播违规。"],
        },
    ]


def _judge_domain_matrices(issue: dict[str, Any]) -> list[dict[str, Any]]:
    if issue.get("topicId") == FINANCE_MARKET_TOPIC_ID:
        return [
            {
                "id": "finance_scenario_matrix",
                "title": "30 天情景矩阵",
                "columns": ["情景", "含义", "动作"],
                "rows": [
                    {"情景": "上涨", "含义": "可能赚钱，但仍需扣除借款成本。", "动作": "分批，不追涨加杠杆。"},
                    {"情景": "震荡", "含义": "收益可能被利息和交易成本吞噬。", "动作": "等待确认或用闲置资金小仓。"},
                    {"情景": "回撤", "含义": "现金流压力和被迫卖出风险最高。", "动作": "按止损退出，不贷款补仓。"},
                ],
            }
        ]
    if issue.get("topicId") != LOOTBOX_TOPIC_ID:
        return []
    return [
        {
            "id": "compliance_matrix",
            "title": "合规项目矩阵",
            "columns": ["项目", "判断", "上线条件"],
            "rows": [
                {"项目": "充值赠送宝箱", "判断": "高风险", "上线条件": "不得保留随机财产期待型自开。"},
                {"项目": "游戏币购买后打赏", "判断": "条件可做", "上线条件": "礼物不可交易回兑，主播奖励独立核算。"},
                {"项目": "主播奖励", "判断": "上线红线", "上线条件": "不得与随机礼物价值自动挂钩。"},
                {"项目": "未成年人", "判断": "禁止参与", "上线条件": "实名年龄识别、支付拦截、监护人退款 SOP。"},
            ],
        },
        {
            "id": "risk_failure_matrix",
            "title": "风险与失效路径",
            "columns": ["失效路径", "后果", "控制"],
            "rows": [
                {"失效路径": "主播承诺返现或线下分成", "后果": "现金化闭环、套现、投诉和监管风险", "控制": "话术监测、结算冻结、封禁和证据留存。"},
                {"失效路径": "工作室批量账号刷流水", "后果": "虚假繁荣、洗钱/电诈风险", "控制": "设备、IP、支付账户、行为聚类。"},
                {"失效路径": "概率配置不可追溯", "后果": "消费者知情权和虚假宣传争议", "控制": "概率公示、版本留存、抽取日志和审计。"},
            ],
        },
    ]


def _judge_action_plan(issue: dict[str, Any], gate: dict[str, Any]) -> list[str]:
    if issue.get("topicId") == FINANCE_MARKET_TOPIC_ID:
        return [
            "证据门禁：补齐当前行情、估值、波动率、资金流和未来 30 天关键事件。",
            "资金门禁：写明贷款金额、利率、期限、还款来源和最大可承受亏损。",
            "交易门禁：写明仓位、分批计划、止损、止盈、禁止补仓条件。",
            "发布门禁：报告只能作为风险讨论材料，不得作为确定投资收益承诺。",
        ]
    if issue.get("topicId") != LOOTBOX_TOPIC_ID:
        return ["补齐缺失席位。", "复核证据强度。", "只从裁决文档生成 HTML、Markdown 和 PDF。"]
    return [
        "上线门禁 1：删除或重构充值赠送宝箱后用户自开路径。",
        "上线门禁 2：主播奖励与随机礼物价值、稀有度、用户开箱结果彻底解耦。",
        "上线门禁 3：实名年龄识别、未成年禁入、限额限次、冷静提示和退款 SOP 全量上线。",
        "上线门禁 4：概率公示、抽取日志、奖池版本、异常调整记录可审计。",
        "上线门禁 5：反套现模型覆盖主播返现话术、固定互刷、批量账号、异常充值和线下交易。",
        "发布门禁：有效席位补齐或人工法务复核前，只能导出阶段性草案。",
    ]


def _judge_audit(raw: dict[str, Any], audit: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_seat_summaries(raw)
    return {
        "publicSummary": [
            f"有效席位 {audit.get('completedRequiredSeats', 0)}/{audit.get('requiredSeats', 0)}。",
            f"裁决门禁：{gate.get('label')}。",
            "公开页面只展示有限审计摘要，完整调试工作台仅限本机或授权访问。",
        ],
        "missingSeats": missing,
        "degradedReasons": [item for item in _text(gate.get("reason")).split("；") if item],
        "debugAvailable": True,
    }


def _ai_judge_verdict_hero(doc: dict[str, Any]) -> str:
    identity = doc.get("reportIdentity") if isinstance(doc.get("reportIdentity"), dict) else {}
    gate = doc.get("verdictGate") if isinstance(doc.get("verdictGate"), dict) else {}
    council = doc.get("council") if isinstance(doc.get("council"), dict) else {}
    return f"""
<section class="VerdictHero">
  <p class="kicker">AI Judge · {html.escape(_text(doc.get('productRenderer')))} · {html.escape(_text(doc.get('domainTemplate')))}</p>
  <span class="gate-badge">{html.escape(_text(gate.get('label')))}</span>
  <h1>{html.escape(_text(identity.get('title')))}</h1>
  <p class="subtitle">{html.escape(_text(identity.get('subtitle')))}</p>
  <div class="meta-grid">
    <div class="meta-card"><span>Run ID</span><strong>{html.escape(_text(identity.get('runId')))}</strong></div>
    <div class="meta-card"><span>Surface</span><strong>{html.escape(_text(identity.get('surface')))}</strong></div>
    <div class="meta-card"><span>席位覆盖</span><strong>有效席位 {council.get('validSeats', 0)}/{council.get('requiredSeats', 0)}</strong></div>
    <div class="meta-card"><span>发布状态</span><strong>{'可发布' if gate.get('publishable') else '暂缓发布'}</strong></div>
  </div>
</section>"""


def _executive_decision_strip(doc: dict[str, Any]) -> str:
    executive = doc.get("executiveVerdict") if isinstance(doc.get("executiveVerdict"), dict) else {}
    prohibited = "；".join(_text(item) for item in executive.get("prohibitedClaimsOrActions") or [])
    return f"""
<section class="ExecutiveDecisionStrip" aria-label="执行裁决">
  <div class="decision-card primary"><span>裁决是什么</span><strong>{html.escape(_text(executive.get('oneLine')))}</strong></div>
  <div class="decision-card"><span>马上做什么</span><strong>{html.escape(_text(executive.get('minimumNextStep')))}</strong></div>
  <div class="decision-card"><span>最大风险</span><strong>{html.escape(_text(executive.get('largestRisk')))}</strong></div>
  <div class="decision-card"><span>不该做什么</span><strong>{html.escape(prohibited)}</strong></div>
</section>"""


def _judge_key_conclusions(doc: dict[str, Any]) -> str:
    executive = doc.get("executiveVerdict") if isinstance(doc.get("executiveVerdict"), dict) else {}
    items = [
        _text(executive.get("oneLine")),
        _text(executive.get("largestRisk")),
        _text(executive.get("minimumNextStep")),
    ]
    lis = "".join(f"<li>{html.escape(item)}</li>" for item in items if item)
    return f'<section class="KeyConclusions"><h2>核心结论</h2><ul>{lis}</ul></section>' if lis else ""


def _judge_issue_sections_html(doc: dict[str, Any]) -> str:
    blocks = []
    for issue in doc.get("issues") or []:
        controls = "".join(f"<li>{html.escape(_text(item))}</li>" for item in issue.get("requiredControls") or [])
        actions = "".join(f"<li>{html.escape(_text(item))}</li>" for item in issue.get("actionItems") or [])
        refs = "、".join(_text(item) for item in issue.get("evidenceRefs") or [])
        risk_class = "risk-high" if "高" in _text(issue.get("riskLevel")) else "risk-medium"
        blocks.append(f"""
<section class="IssueVerdictSection">
  <h2>{html.escape(_text(issue.get('title')))}</h2>
  <div class="issue-grid">
    <div class="issue-card"><span>共识</span><strong>{html.escape(_text(issue.get('consensusBadge')))}</strong></div>
    <div class="issue-card"><span>风险等级</span><strong class="{risk_class}">{html.escape(_text(issue.get('riskLevel')))}</strong></div>
    <div class="issue-card"><span>证据引用</span><strong>{html.escape(refs)}</strong></div>
    <div class="issue-card"><span>结论</span><strong>{html.escape(_text(issue.get('coreConclusion')))}</strong></div>
  </div>
  <p>{html.escape(_text(issue.get('judgeExplanation')))}</p>
  <h3>必要控制</h3><ul>{controls}</ul>
  <h3>行动项</h3><ul>{actions}</ul>
</section>""")
    return "\n".join(blocks)


def _judge_domain_matrices_html(doc: dict[str, Any]) -> str:
    blocks = []
    for matrix in doc.get("domainMatrices") or []:
        columns = [_text(col) for col in matrix.get("columns") or []]
        head = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
        rows = []
        for row in matrix.get("rows") or []:
            rows.append("<tr>" + "".join(f"<td>{html.escape(_text(row.get(col, '')))}</td>" for col in columns) + "</tr>")
        blocks.append(
            f'<section class="DomainMatrixSection"><h2>{html.escape(_text(matrix.get("title")))}</h2>'
            f'<div class="matrix-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'
        )
    return "\n".join(blocks)


def _judge_risk_and_failure_section(doc: dict[str, Any]) -> str:
    executive = doc.get("executiveVerdict") if isinstance(doc.get("executiveVerdict"), dict) else {}
    items = executive.get("prohibitedClaimsOrActions") if isinstance(executive.get("prohibitedClaimsOrActions"), list) else []
    lis = "".join(f"<li>{html.escape(_text(item))}</li>" for item in items)
    return f'<section class="RiskAndFailureSection"><h2>风险与禁止动作</h2><p>{html.escape(_text(executive.get("largestRisk")))}</p><ul>{lis}</ul></section>'


def _judge_action_plan_section(doc: dict[str, Any]) -> str:
    items = doc.get("actionPlan") if isinstance(doc.get("actionPlan"), list) else []
    lis = "".join(f"<li>{html.escape(_text(item))}</li>" for item in items)
    return f'<section class="ActionPlanSection"><h2>上线门禁与行动计划</h2><ul>{lis}</ul></section>' if lis else ""


def _judge_evidence_strength_section(doc: dict[str, Any]) -> str:
    evidence = doc.get("evidenceStrength") if isinstance(doc.get("evidenceStrength"), dict) else {}
    return f"""
<section class="EvidenceStrengthSection">
  <h2>证据强度</h2>
  <div class="meter-grid">
    <div class="meta-card"><span>法规覆盖</span><strong>{html.escape(_text(evidence.get('lawCoverage')))}</strong></div>
    <div class="meta-card"><span>案例覆盖</span><strong>{html.escape(_text(evidence.get('caseCoverage')))}</strong></div>
    <div class="meta-card"><span>交叉验证</span><strong>{html.escape(_text(evidence.get('crossValidation')))}</strong></div>
    <div class="meta-card"><span>动作</span><strong>{html.escape(_text(evidence.get('action')))}</strong></div>
  </div>
</section>"""


def _judge_limited_audit_footer(doc: dict[str, Any]) -> str:
    audit = doc.get("audit") if isinstance(doc.get("audit"), dict) else {}
    summary = "".join(f"<li>{html.escape(_text(item))}</li>" for item in audit.get("publicSummary") or [])
    gaps = "".join(f"<li>{html.escape(_compact(_text(item), 180))}</li>" for item in audit.get("missingSeats") or [])
    return f"""
<footer class="LimitedAuditFooter">
  <h2>有限审计摘要</h2>
  <div class="audit-grid">
    <div class="meta-card"><span>公开摘要</span><strong><ul>{summary}</ul></strong></div>
    <div class="meta-card"><span>缺失席位</span><strong><ul>{gaps or '<li>无</li>'}</ul></strong></div>
    <div class="meta-card"><span>调试入口</span><strong>仅本机或授权访问</strong></div>
    <div class="meta-card"><span>导出规则</span><strong>HTML、Markdown、PDF 均来自同一裁决文档</strong></div>
  </div>
</footer>"""


def _build_homestead_legal_view_model(raw: dict[str, Any], *, surface: str, issue: dict[str, Any]) -> PublicReportViewModel:
    evidence = _topic_filtered_evidence(raw, issue["topicId"])
    audit = _limited_audit(raw)
    sections = _legal_sections()
    model = PublicReportViewModel(
        kind="legal_homestead_demolition_report",
        surface=surface,
        reportId=_text(raw.get("run_id") or raw.get("id") or "unknown"),
        title="AI Judge 裁决报告：宅基地房屋拆迁补偿纠纷",
        subtitle="只起诉甲的案由、诉讼请求与补偿项目分配",
        verdict={
            "label": "条件支持",
            "oneLine": "丁可以只起诉甲，但应聚焦非土地性补偿利益；立即做诉前财产保全，不要主张宅基地使用权或全部拆迁补偿归丁。",
            "confidence": _text(raw.get("confidence") or "81"),
            "highestRisk": "甲尚未实际取得补偿款，单纯不当得利给付请求可能被认为条件未成就。",
            "doNotClaim": "不要主张宅基地使用权归丁、房屋物权当然归丁、全部拆迁补偿归丁。",
        },
        issue=issue,
        keyConclusions=[
            "首选诉讼结构：财产损害赔偿纠纷或确认非土地性补偿利益归属，配合条件给付。",
            "不当得利可作为并列或备位请求；甲实际收款后，该路径更稳。",
            "房屋重置价值、装修附属物补偿可以附证据主张；土地性补偿原则上不主张。",
            "搬迁补助、临时安置费、按时搬迁奖励只在丁实际搬迁、居住、支出或政策对象身份成立时主张。",
        ],
        sections=sections,
        actionChecklist=[
            {"label": "马上做", "detail": "调取拆迁协议、补偿明细、评估报告和付款计划。"},
            {"label": "马上做", "detail": "准备诉前财产保全，冻结甲对拆迁主体的应收补偿款债权。"},
            {"label": "马上做", "detail": "固定丁的购买链条、付款、占有、装修、居住和搬迁证据。"},
            {"label": "不要做", "detail": "不要把诉请写成确认宅基地使用权或全部拆迁补偿归丁。"},
        ],
        evidence=evidence,
        audit=audit,
    )
    _filter_sections(model)
    return model


def _build_lootbox_compliance_view_model(raw: dict[str, Any], *, surface: str, issue: dict[str, Any]) -> PublicReportViewModel:
    audit = _limited_audit(raw)
    sections = _lootbox_sections(raw, audit)
    model = PublicReportViewModel(
        kind="ai_judge_verdict_document",
        surface=surface,
        reportId=_text(raw.get("run_id") or raw.get("id") or "unknown"),
        title="AI Judge 阶段性裁决草案",
        subtitle="宝箱玩法合规风险评估",
        verdict={
            "label": "谨慎可做",
            "oneLine": "不建议按原规则直接上线；取消或重构“充值赠送后用户自开”路径，切断随机礼物、主播奖励与现金化收益之间的闭环后，才可进入灰度。",
            "confidence": _text(raw.get("confidence") or "阶段性"),
            "highestRisk": "充值诱导、随机开箱、主播奖励和线下交易如果形成资金回流，可能被认定为变相赌博、违规抽奖促销或打赏套现链条。",
            "doNotClaim": "不得宣传中奖、回本、收益、提现、保值、主播返利；不得允许宝箱、礼物、账号或主播奖励被平台内外回兑。",
        },
        issue=issue,
        keyConclusions=[
            "结论：原规则不宜直接上线；在重大整改、概率审计、交易隔离、未成年人禁入和异常交易监测完成后，可作为高风险受控玩法灰度。",
            "充值赠送宝箱并允许用户自开，是最高风险路径；建议取消自开，或改为无财产期待的展示/娱乐结果。",
            "游戏币购买宝箱仅能打赏主播的路径，也必须防止主播奖励与随机礼物价值自动挂钩，否则会形成变相返利和资金回流。",
            "禁止回兑和禁止交易不能只写进规则，必须有技术控制、风控识别、处罚闭环、投诉退款和留痕审计。",
            "本轮 AI Judge 有效席位不足发布阈值，战略门禁未完全通过；以下内容作为阶段性裁决草案，不应包装为全席位最终共识。",
        ],
        sections=sections,
        actionChecklist=[
            {"label": "先改规则", "detail": "取消或重构充值赠送宝箱后的用户自开功能，避免以随机收益诱导充值。"},
            {"label": "先断闭环", "detail": "主播奖励不得按随机礼物价值自动结算，不得允许礼物、宝箱、账号线下交易或回兑。"},
            {"label": "上线门禁", "detail": "完成概率公示与审计、实名/未成年禁入、限额限次、异常交易监测和客服退款 SOP。"},
            {"label": "灰度监控", "detail": "监测主播与用户串通刷礼物、工作室批量账号、异常充值和线下返现。"},
        ],
        evidence=_lootbox_public_evidence(),
        audit=audit,
    )
    _filter_lootbox_sections(model)
    return model


def _build_finance_market_view_model(raw: dict[str, Any], *, surface: str, issue: dict[str, Any]) -> PublicReportViewModel:
    audit = _limited_audit(raw)
    final_report = raw.get("final_report") if isinstance(raw.get("final_report"), dict) else {}
    executive = final_report.get("executive_summary") if isinstance(final_report.get("executive_summary"), dict) else {}
    recommendation = _public_business_decision_text(
        final_report.get("recommendation") or executive.get("recommendation") or raw.get("one_liner"),
        FINANCE_DEFAULT_RECOMMENDATION,
        limit=360,
    )
    risk = _public_compiled_text(
        executive.get("risk") or raw.get("risk_summary"),
        FINANCE_DEFAULT_RISK,
        limit=280,
    )
    sections = _finance_market_sections(raw, audit, recommendation, risk)
    model = PublicReportViewModel(
        kind="financial_market_risk_opinion",
        surface=surface,
        reportId=_text(raw.get("run_id") or raw.get("id") or "unknown"),
        title="AI Judge 金融风险意见书：纳斯达克未来 30 天与贷款抄底",
        subtitle="短期指数择时、借款成本、情景矩阵与行动门禁",
        verdict={
            "label": "不建议贷款抄底",
            "oneLine": recommendation,
            "confidence": _text(raw.get("confidence") or executive.get("confidence_label") or ""),
            "highestRisk": risk,
            "doNotClaim": "不要承诺 30 天赚钱；不要用生活资金、信用贷或不可承受的杠杆去赌单边反弹；不要在没有止损和还款计划时加仓。",
        },
        issue=issue,
        keyConclusions=[
            "结论先行：贷款买入纳斯达克综合指数或相关 ETF，不应作为默认动作；这更像带融资成本和现金流约束的高波动交易，而不是低风险投资。",
            "真正要裁决的不是“纳指会不会涨”，而是：未来 30 天上涨概率、下跌幅度、借款成本、最大回撤承受和退出纪律是否同时满足。",
            "如果一定参与，优先考虑闲置资金、分批、限仓、事件后确认和明确止损；贷款资金只应作为极端谨慎的备选，且需能承受先跌 5%-10% 的压力测试。",
            "事实、推断和假设必须分层：行情与宏观事件是事实输入；未来走势是概率情景；能否赚钱取决于买入点、资金成本、仓位、期限和执行纪律。",
        ],
        sections=sections,
        actionChecklist=[
            {"label": "马上做", "detail": "补齐当前指数/ETF 价格、估值、波动率、美元利率、借款成本和未来 30 天宏观/财报日历。"},
            {"label": "先算账", "detail": "用本金、贷款利率、还款期限和 5%/10%/15% 回撤测算现金流压力。"},
            {"label": "只可小仓", "detail": "若仍要参与，采用非生活资金、分批和硬止损；不要一次性满仓贷款买入。"},
            {"label": "不要做", "detail": "不要把模型共识、历史反弹或短期利好当作确定收益承诺。"},
        ],
        evidence=_finance_public_evidence(raw),
        audit=audit,
    )
    _filter_finance_sections(model)
    return model


def _build_generic_view_model(raw: dict[str, Any], *, surface: str, issue: dict[str, Any]) -> PublicReportViewModel:
    final_report = raw.get("final_report") if isinstance(raw.get("final_report"), dict) else {}
    title = _text(final_report.get("title") or raw.get("title") or "AI Judge 最终裁决报告")
    recommendation = _text(final_report.get("recommendation") or raw.get("one_liner") or "请阅读核心结论和下一步行动。")
    return PublicReportViewModel(
        kind="standard_public_report",
        surface=surface,
        reportId=_text(raw.get("run_id") or raw.get("id") or "unknown"),
        title=title,
        subtitle="Public report",
        verdict={"label": _text(raw.get("verdict") or "conditional"), "oneLine": recommendation, "confidence": _text(raw.get("confidence") or "")},
        issue=issue,
        keyConclusions=[recommendation],
        sections=[
            {"id": "key_conclusions", "title": "核心结论", "items": [recommendation], "topic_id": issue["topicId"]},
            {"id": "next_actions", "title": "下一步行动", "items": _safe_str_list(raw.get("next_steps") or ["进入人工复核。"]), "topic_id": issue["topicId"]},
            {"id": "limited_audit_appendix", "title": "有限审计摘要", "body": "公开报告仅保留运行状态摘要，不输出底层轨迹。", "topic_id": issue["topicId"]},
        ],
        actionChecklist=[{"label": "下一步", "detail": recommendation}],
        evidence=[],
        audit=_limited_audit(raw),
    )


def _legal_sections() -> list[dict[str, Any]]:
    topic = HOMESTEAD_TOPIC_ID
    return [
        {"id": "cover", "title": "封面", "topic_id": topic},
        {"id": "one_line_verdict", "title": "一句话裁决", "body": "丁可以只起诉甲，但必须把诉讼锚定在非土地性补偿利益和损失赔偿上，并立即申请诉前财产保全。", "topic_id": topic},
        {
            "id": "key_conclusions",
            "title": "核心结论",
            "items": [
                "首选不是合同纠纷；财产损害赔偿纠纷或确认非土地性补偿利益归属更适合当前时点。",
                "不当得利在甲尚未实际取得款项时存在得利未发生抗辩，适合作为并列或备位请求。",
                "房屋重置价值、装修附属物补偿是主张重点；土地性补偿和宅基地使用权不宜主张。",
                "搬迁奖励、搬迁补助、临时安置费要看丁是否实际搬迁、居住、支出或属于政策对象。",
            ],
            "topic_id": topic,
        },
        {
            "id": "case_timeline",
            "title": "案件时间线",
            "rows": [
                {"时间": "1989年", "事件": "甲与乙围绕农村宅基地合作开发共建房屋，甲为宅基地登记权利人。"},
                {"时间": "1993年", "事件": "乙将房屋转售给丙。"},
                {"时间": "2009年", "事件": "丙将房屋转售给丁。"},
                {"时间": "2026年", "事件": "宅基地房屋纳入拆迁，甲私自与拆迁主体签约，尚未实际取得补偿款。"},
            ],
            "columns": ["时间", "事件"],
            "topic_id": topic,
        },
        {
            "id": "rights_structure",
            "title": "权利结构",
            "rows": [
                {"权利/利益": "宅基地土地性权益", "裁决": "丁原则上不能直接主张。", "理由": "宅基地使用权具有身份属性，非本集体成员取得受限。"},
                {"权利/利益": "房屋建筑物和装修投入利益", "裁决": "丁可附证据主张。", "理由": "该部分更接近投入价值、占有使用利益和无效后折价补偿。"},
                {"权利/利益": "搬迁安置行为利益", "裁决": "附条件主张。", "理由": "须证明丁为实际搬迁人、实际居住人、实际支出人或政策对象。"},
            ],
            "columns": ["权利/利益", "裁决", "理由"],
            "topic_id": topic,
        },
        {
            "id": "litigation_strategy",
            "title": "诉讼策略",
            "items": [
                "案由主轴：财产损害赔偿纠纷；同时写明确认非土地性补偿利益归属和条件给付。",
                "不当得利请求：作为并列或备位请求，特别针对甲实际取得补偿款后的返还。",
                "被告：甲。必要时申请追加拆迁主体为第三人或申请法院调取补偿协议、付款计划。",
            ],
            "topic_id": topic,
        },
        {
            "id": "claims",
            "title": "诉讼请求",
            "items": [
                "判令被告甲赔偿原告丁因其擅自签订拆迁补偿协议并排除原告参与分配所造成的房屋建筑物重置价值、装修装饰及附属物价值损失人民币 [X] 元。",
                "确认涉案拆迁补偿协议中房屋建筑物重置补偿、装修装饰补偿、附属物补偿等非土地性补偿项目中对应原告购买、占有、使用、投入部分的权益归原告享有。",
                "判令被告甲在实际取得前述补偿款后 [X] 日内向原告支付相应款项；如给付条件尚未成就，请求先行确认原告享有相应债权或分配利益。",
                "对搬迁补助、临时安置费、按时搬迁奖励，仅在原告能证明实际搬迁、实际居住、实际支出或政策对象身份时请求支付对应金额。",
                "请求本案诉讼费、保全费由被告承担。",
            ],
            "topic_id": topic,
        },
        {
            "id": "preservation",
            "title": "诉前财产保全",
            "items": [
                "申请冻结甲对拆迁主体享有的应收补偿款债权或等值财产。",
                "同步提交担保方案、补偿协议线索、付款计划线索和丁实际占有投入证据。",
                "向拆迁主体发送律师函或申请法院协助通知，提示涉案补偿款存在权属争议。",
            ],
            "topic_id": topic,
        },
        {
            "id": "compensation_matrix",
            "title": "补偿项目矩阵",
            "rows": [
                {"项目": "房屋重置/建筑物价值补偿", "能否主张": "可以主张", "条件": "证明购买链条、占有使用、建造/翻建/维护投入，且明细能区分建筑物价值。", "边界": "不等于土地性补偿。"},
                {"项目": "宅基地/土地性补偿", "能否主张": "原则上不能", "条件": "本轮未见丁具备政策资格证据。", "边界": "不得包装为宅基地使用权归丁。"},
                {"项目": "装修、附属物、构筑物补偿", "能否主张": "可以附证据主张", "条件": "证明丁实际出资装修、添附或维护。", "边界": "按投入和评估确认范围。"},
                {"项目": "搬迁补助费", "能否主张": "附条件", "条件": "丁实际搬迁、实际支出，或政策文本承认实际使用人。", "边界": "不能无条件全额主张。"},
                {"项目": "临时安置费/过渡费", "能否主张": "附条件", "条件": "丁实际居住且因拆迁产生安置损失。", "边界": "偏向人的安置利益。"},
                {"项目": "按时搬迁奖励", "能否主张": "谨慎附条件", "条件": "丁实际配合腾退、搬迁、交房且奖励与其行为对应。", "边界": "通常依政策对象和行为触发。"},
                {"项目": "停产停业损失", "能否主张": "仅有经营事实时", "条件": "证明实际经营、流水、执照、纳税或其他经营证据。", "边界": "无经营事实不得主张。"},
            ],
            "columns": ["项目", "能否主张", "条件", "边界"],
            "topic_id": topic,
        },
        {
            "id": "risks",
            "title": "风险矩阵",
            "rows": [
                {"风险": "得利未发生", "影响": "单纯不当得利给付请求可能不成熟。", "应对": "确认利益+条件给付+保全。"},
                {"风险": "非本集体成员身份", "影响": "土地性补偿和宅基地权利主张高风险。", "应对": "只主张非土地性、投入性、实际损失性项目。"},
                {"风险": "证据链断裂", "影响": "难以证明丁的购买、占有、装修和搬迁事实。", "应对": "立即固定协议、付款、水电、证人、照片、评估。"},
            ],
            "columns": ["风险", "影响", "应对"],
            "topic_id": topic,
        },
        {
            "id": "evidence_checklist",
            "title": "证据清单",
            "items": [
                "1989合作建房材料、1993转让材料、2009转让材料及付款凭证。",
                "房屋占有使用证据：水电、维修、装修、照片、邻居证言、村委材料。",
                "拆迁协议、补偿项目明细、评估报告、付款计划、当地补偿安置政策。",
                "丁实际搬迁、临时安置、装修附属物和经营损失的支出凭证。",
            ],
            "topic_id": topic,
        },
        {
            "id": "next_actions",
            "title": "下一步行动",
            "items": [
                "先调证：补偿协议、明细、评估和政策文本。",
                "再保全：冻结甲的应收补偿款债权或等值财产。",
                "后起诉：以财产损害赔偿/确认非土地性补偿利益为主，不当得利为并列或备位。",
            ],
            "topic_id": topic,
        },
        {"id": "limited_audit_appendix", "title": "有限审计摘要", "body": "公开和复核页面只显示运行完整度摘要，不输出底层轨迹或内部链路明细。", "topic_id": topic},
    ]


def _finance_market_sections(
    raw: dict[str, Any],
    audit: dict[str, Any],
    recommendation: str,
    risk: str,
) -> list[dict[str, Any]]:
    topic = FINANCE_MARKET_TOPIC_ID
    prompt_flow = raw.get("prompt_flow") if isinstance(raw.get("prompt_flow"), dict) else {}
    intake = prompt_flow.get("intake_plan") if isinstance(prompt_flow.get("intake_plan"), dict) else {}
    domain = intake.get("domain_pack") if isinstance(intake.get("domain_pack"), dict) else {}
    reframed = _public_compiled_text(
        intake.get("reframed_question"),
        "基于当前行情、未来 30 天事件、贷款成本和最大回撤承受，评估是否应借款买入纳斯达克综合指数或相关 ETF。",
        limit=420,
    )
    evidence_requirements = [
        _text(item)
        for item in (domain.get("evidence_requirements") if isinstance(domain.get("evidence_requirements"), list) else [])
        if _text(item)
    ]
    if not evidence_requirements:
        evidence_requirements = [
            "当前纳斯达克综合指数或相关 ETF 的价格、估值、趋势和波动率。",
            "未来 30 天 FOMC、CPI/PCE、就业、财报、流动性和地缘政治事件。",
            "贷款利率、期限、还款来源、最大可承受回撤和止损执行规则。",
        ]
    return [
        {"id": "cover", "title": "封面", "topic_id": topic},
        {
            "id": "one_line_verdict",
            "title": "一句话裁决",
            "body": recommendation,
            "topic_id": topic,
        },
        {
            "id": "market_snapshot",
            "title": "市场快照与数据边界",
            "rows": [
                {"项目": "当前行情", "结论": "必须以运行当日可核验行情为准。", "边界": "没有实时行情证据时，不把涨跌方向写成事实。"},
                {"项目": "时间窗口", "结论": "30 天属于短期交易窗口。", "边界": "短期收益高度受事件和情绪影响，不等同长期指数投资。"},
                {"项目": "资金来源", "结论": "贷款资金带有固定成本和还款压力。", "边界": "不能按闲置资金风险来评估贷款抄底。"},
                {"项目": "可交易标的", "结论": "可参考纳斯达克综合指数、QQQ/ONEQ 等相关工具。", "边界": "若使用杠杆 ETF 或融资融券，风险需单独上调。"},
            ],
            "columns": ["项目", "结论", "边界"],
            "topic_id": topic,
        },
        {
            "id": "judge_reframed_question",
            "title": "法官重写后的裁决问题",
            "body": reframed,
            "items": [
                "把“能不能赚钱”拆成概率、赔率、成本、回撤和执行纪律五个问题。",
                "把“纳指未来 30 天走势”拆成趋势、估值、宏观事件、财报和流动性五组变量。",
                "把“贷款抄底”拆成借款成本、还款现金流、强制卖出风险和替代方案。",
            ],
            "topic_id": topic,
        },
        {
            "id": "scenario_matrix",
            "title": "30 天情景矩阵",
            "rows": [
                {"情景": "上行情景", "触发条件": "通胀/利率预期缓和，科技龙头财报或 AI 资本开支叙事继续支撑风险偏好。", "对贷款买入的含义": "可能赚钱，但需扣除资金成本；仍不证明贷款是最优方案。", "动作": "只在计划内分批，不追涨加杠杆。"},
                {"情景": "震荡情景", "触发条件": "数据好坏交错、估值已反映乐观预期、市场等待关键事件落地。", "对贷款买入的含义": "收益可能被利息和波动吞噬。", "动作": "优先等待确认，或用小仓/定投替代。"},
                {"情景": "回撤情景", "触发条件": "通胀反复、利率上行、科技股财报不及预期、美元流动性收紧或风险事件。", "对贷款买入的含义": "最危险：账面亏损、还款压力和情绪止损会叠加。", "动作": "触发止损或暂停，不用贷款补仓。"},
            ],
            "columns": ["情景", "触发条件", "对贷款买入的含义", "动作"],
            "topic_id": topic,
        },
        {
            "id": "leverage_risk",
            "title": "贷款/杠杆压力测试",
            "rows": [
                {"变量": "借款成本", "必须计算": "年化利率、实际持有天数、提前还款费用。", "失败信号": "上涨预期不足以覆盖利息、手续费和汇率/交易成本。"},
                {"变量": "最大回撤", "必须计算": "指数下跌 5%、10%、15% 时的亏损额和还款压力。", "失败信号": "一旦先跌就需要挪用生活资金或被迫卖出。"},
                {"变量": "期限错配", "必须计算": "贷款到期和投资修复周期是否匹配。", "失败信号": "30 天内没涨就必须还款或续贷。"},
                {"变量": "行为纪律", "必须计算": "止损价、止盈价、最大仓位和禁止加仓条件。", "失败信号": "没有书面规则，只凭“应该会涨”。"},
            ],
            "columns": ["变量", "必须计算", "失败信号"],
            "topic_id": topic,
        },
        {
            "id": "catalyst_calendar",
            "title": "未来 30 天催化因素",
            "items": [
                "宏观：FOMC、CPI/PCE、非农就业、失业率、零售销售、PMI 和美债收益率。",
                "企业：纳指权重科技公司财报、AI 资本开支、芯片供应链、云业务增速和利润率指引。",
                "流动性：美元指数、美债实际利率、风险偏好、ETF 资金流和期权波动率。",
                "风险事件：地缘政治、监管政策、集中持仓拥挤、估值回调和财报踩踏。",
            ],
            "topic_id": topic,
        },
        {
            "id": "decision_framework",
            "title": "决策框架",
            "rows": [
                {"选项": "不贷款，先观察", "适用条件": "行情证据不足、事件密集、个人现金流不稳。", "优点": "避免被迫交易。", "代价": "可能错过短期反弹。"},
                {"选项": "闲置资金分批", "适用条件": "有长期配置需求且能承受波动。", "优点": "降低单点择时错误。", "代价": "短期收益不一定最大。"},
                {"选项": "贷款小仓验证", "适用条件": "有稳定还款来源、低利率、书面止损、亏损不影响生活。", "优点": "保留参与上行情景的可能。", "代价": "风险显著高于闲置资金。"},
                {"选项": "贷款满仓抄底", "适用条件": "原则上不建议。", "优点": "若短期大涨收益高。", "代价": "一旦先跌，亏损、利息和现金流压力叠加。"},
            ],
            "columns": ["选项", "适用条件", "优点", "代价"],
            "topic_id": topic,
        },
        {
            "id": "risk_matrix",
            "title": "风险矩阵",
            "rows": [
                {"风险": "方向判断错误", "等级": "高", "表现": "30 天内指数回撤或横盘。", "应对": "分批、限仓、止损，不用贷款补仓。"},
                {"风险": "成本吞噬收益", "等级": "中高", "表现": "指数小涨但扣除利息/费用后收益不足。", "应对": "先计算盈亏平衡涨幅。"},
                {"风险": "现金流断裂", "等级": "高", "表现": "还款压力迫使低位卖出。", "应对": "只用不影响生活的资金；贷款方案需有备用现金。"},
                {"风险": "模型过度自信", "等级": "高", "表现": "把多模型共识当作确定预测。", "应对": "强制保留反方情景和失败条件。"},
            ],
            "columns": ["风险", "等级", "表现", "应对"],
            "topic_id": topic,
        },
        {
            "id": "evidence_checklist",
            "title": "证据清单",
            "items": evidence_requirements,
            "topic_id": topic,
        },
        {
            "id": "next_actions",
            "title": "下一步行动",
            "items": [
                "补齐行情证据：指数/ETF 当前价格、近 30/90 日走势、估值、波动率、资金流。",
                "补齐事件证据：未来 30 天宏观数据、FOMC、财报日历和关键政策事件。",
                "先做压力测试：贷款利率、还款期限、5%-15% 回撤、止损价和备用现金。",
                "若无法书面写出止损、止盈、仓位和退出条件，本轮裁决直接禁止贷款抄底。",
                (
                    f"运行完整度：首轮有效席位 {audit.get('validSeats', 0)}/{audit.get('attemptedSeats', audit.get('requiredSeats', 0))}"
                    f"（必需席位 {audit.get('completedRequiredSeats', 0)}/{audit.get('requiredSeats', 0)}），"
                    f"二轮共振 {audit.get('round2Completed', 0)}/{audit.get('round2Scheduled', 0)}。"
                ),
            ],
            "topic_id": topic,
        },
        {
            "id": "limited_audit_appendix",
            "title": "有限审计摘要",
            "body": "公开页面只展示裁决编译结果和有限运行摘要，不公开席位原文、Prompt、浏览器日志或内部证据库。",
            "topic_id": topic,
        },
    ]


def _lootbox_sections(raw: dict[str, Any], audit: dict[str, Any]) -> list[dict[str, Any]]:
    topic = LOOTBOX_TOPIC_ID
    common = COMMON_PLATFORM_COMPLIANCE_TOPIC_ID
    completed = audit.get("completedRequiredSeats", 0)
    required = audit.get("requiredSeats", 0)
    round2 = f"{audit.get('round2Completed', 0)}/{audit.get('round2Scheduled', 0)}"
    return [
        {"id": "cover", "title": "封面", "topic_id": topic},
        {
            "id": "one_line_verdict",
            "title": "一页结论",
            "body": "该宝箱玩法属于高风险交叉合规产品；按原规则直接上线不建议，重大整改后可进入受控灰度。",
            "topic_id": topic,
        },
        {
            "id": "key_conclusions",
            "title": "核心结论",
            "items": [
                "最高风险不是“随机”本身，而是充值、随机权益、主播奖励、线下交易和资金回流可能被串成闭环。",
                "充值赠送宝箱且允许用户自开，容易被理解为以随机收益刺激充值，应取消或改造为无财产期待的娱乐展示。",
                "游戏币购买宝箱仅能打赏主播，仍要防止主播与用户串通、工作室刷量、主播奖励按随机价值结算。",
                "概率公示、限额限次、未成年人禁入、禁止回兑、禁止交易，必须落到系统控制和审计留痕。",
                "本轮运行完成但席位覆盖不足，正式对外文件应标记为阶段性，待缺失席位或人工法务复核后再签发。",
            ],
            "topic_id": topic,
        },
        {
            "id": "rule_decomposition",
            "title": "事实与规则拆解",
            "rows": [
                {"路径": "充值赠送宝箱", "规则": "用户充值获得等值游戏币并获赠宝箱，可自开或打赏。", "法律关注": "充值诱导、随机权益、有奖销售、网络游戏随机抽取、消费者知情权。", "初步判断": "高风险，应取消自开或弱化为无财产期待。"},
                {"路径": "游戏币购买宝箱", "规则": "用户用游戏币购买宝箱后只能打赏主播。", "法律关注": "虚拟道具用途限制、打赏合规、主播奖励是否变相返利。", "初步判断": "可设计，但必须切断奖励与随机价值自动挂钩。"},
                {"路径": "主播开箱", "规则": "主播获赏后开箱并随机获得礼物。", "法律关注": "主播是否获得可货币化利益、平台任务奖励是否形成财产性期待。", "初步判断": "需把礼物限定为不可交易、不可回兑、不可提现的展示或积分权益。"},
                {"路径": "平台奖励主播", "规则": "平台依据主播完成任务综合情况奖励。", "法律关注": "奖励资金来源、结算口径、税务处理、劳动/合作关系、反套现。", "初步判断": "必须独立于随机礼物价值，按合规任务与服务质量综合认定。"},
            ],
            "columns": ["路径", "规则", "法律关注", "初步判断"],
            "topic_id": topic,
        },
        {
            "id": "regulatory_framework",
            "title": "适用法规与监管口径",
            "rows": [
                {"监管领域": "网络游戏随机抽取", "依据": "《关于规范网络游戏运营加强事中事后监管工作的通知》", "适用点": "随机抽取、概率公示、抽取结果留存、不得以虚拟道具兑换法定货币或实物。", "结论": "如平台属性落入网络游戏或网络文化产品，应按随机抽取规则设计。"},
                {"监管领域": "虚拟货币/虚拟道具", "依据": "《关于加强网络游戏虚拟货币管理工作的通知》", "适用点": "虚拟货币发行、购买、使用范围和交易服务边界。", "结论": "宝箱、钻石和礼物之间不得形成可交易、可回兑、可套现闭环。"},
                {"监管领域": "有奖销售/促销", "依据": "《规范促销行为暂行规定》及《反不正当竞争法》", "适用点": "抽奖式促销、奖项信息、中奖概率、最高奖金额、不得虚假或误导。", "结论": "充值赠送加随机自开最接近促销抽奖风险，需要按有奖销售审查。"},
                {"监管领域": "直播打赏与未成年人保护", "依据": "《关于规范网络直播打赏 加强未成年人保护的意见》《关于加强网络直播打赏规范管理的通知》《未成年人保护法》", "适用点": "未成年人禁入、充值打赏限制、诱导打赏、监护人退款争议。", "结论": "需实名、年龄识别、未成年拦截和退款投诉 SOP。"},
                {"监管领域": "消费者权益与广告宣传", "依据": "《消费者权益保护法》《广告法》", "适用点": "真实、全面、显著告知；不得夸大概率、收益或稀有礼物价值。", "结论": "前端文案不得暗示中奖、回本、收益或主播返利。"},
                {"监管领域": "反洗钱/反电诈/反套现", "依据": "《反电信网络诈骗法》及平台实名、异常交易监测义务", "适用点": "批量账号、异常充值、主播与用户串通、线下返现、账号交易。", "结论": "必须建设异常交易识别、人工复核、冻结和证据留存机制。"},
            ],
            "columns": ["监管领域", "依据", "适用点", "结论"],
            "topic_id": common,
        },
        {
            "id": "scenario_assessment",
            "title": "逐场景合规评估",
            "rows": [
                {"场景": "用户充值获赠后自开", "主要风险": "付费诱导与随机财产期待叠加。", "判断": "不建议保留原设计。", "必要控制": "取消自开，或改为无价值展示、无等级收益、无主播奖励联动。"},
                {"场景": "用户充值获赠后打赏", "主要风险": "打赏诱导、未成年人、主播返利。", "判断": "谨慎可做。", "必要控制": "实名限额、未成年禁入、礼物不可回兑、主播奖励独立核算。"},
                {"场景": "游戏币购买后只打赏", "主要风险": "绕开自开限制但通过主播开箱实现随机收益。", "判断": "重大整改后可做。", "必要控制": "主播获得礼物不得直接对应现金分成或任务奖励。"},
                {"场景": "主播开箱获得随机礼物", "主要风险": "主播获得可货币化随机利益。", "判断": "高风险可控。", "必要控制": "礼物只作展示/等级/非现金积分，严禁交易和回兑。"},
                {"场景": "主播/公会线下返现", "主要风险": "变相赌博、洗钱、刷量和虚假繁荣。", "判断": "上线红线。", "必要控制": "设备指纹、IP 聚类、支付账户关联、异常资金流、黑名单和封禁。"},
            ],
            "columns": ["场景", "主要风险", "判断", "必要控制"],
            "topic_id": topic,
        },
        {
            "id": "abuse_paths",
            "title": "主体滥用路径",
            "rows": [
                {"主体": "平台", "滥用路径": "用稀有礼物、概率、主播奖励刺激充值。", "风险后果": "诱导消费、违规促销、被认定为博彩化运营。", "监控/处置": "营销文案审查、概率审计、运营活动审批。"},
                {"主体": "主播", "滥用路径": "承诺返现、诱导粉丝集中打赏、虚假任务冲榜。", "风险后果": "打赏纠纷、返利套现、税务和劳务争议。", "监控/处置": "主播协议、聊天监测、违规扣罚、结算冻结。"},
                {"主体": "用户", "滥用路径": "多账号刷流水、与主播约定线下分成。", "风险后果": "洗钱、诈骗、套利和投诉退款。", "监控/处置": "实名一致性、设备/IP/支付聚类、异常充值阈值。"},
                {"主体": "公会/工作室", "滥用路径": "批量账号刷礼物、制造榜单、回收礼物或账号。", "风险后果": "虚假交易、资金回流、平台合规失守。", "监控/处置": "公会准入、团伙识别、连坐处罚、资金延迟结算。"},
                {"主体": "未成年人", "滥用路径": "绕过年龄识别参与充值或打赏。", "风险后果": "退款争议、行政监管和舆情。", "监控/处置": "实名核验、未成年禁入、监护人申诉绿色通道。"},
            ],
            "columns": ["主体", "滥用路径", "风险后果", "监控/处置"],
            "topic_id": topic,
        },
        {
            "id": "risk_matrix",
            "title": "风险矩阵",
            "rows": [
                {"风险": "变相赌博/博彩化", "等级": "高", "触发条件": "随机礼物可交易、可回兑或与主播现金奖励挂钩。", "控制措施": "断开现金化链条；禁止交易；异常资金监测。"},
                {"风险": "违规有奖销售", "等级": "高", "触发条件": "充值赠送与随机奖项、中奖宣传或高价值奖品绑定。", "控制措施": "按促销规则披露；控制奖项价值；避免诱导充值。"},
                {"风险": "未成年人保护", "等级": "高", "触发条件": "未成年充值、打赏、开箱或规避实名。", "控制措施": "实名年龄识别；未成年禁入；退款 SOP。"},
                {"风险": "消费者知情权", "等级": "中高", "触发条件": "概率不真实、不显著或历史概率不可核验。", "控制措施": "概率公示、审计报告、日志留存和版本管理。"},
                {"风险": "主播结算/税务", "等级": "中", "触发条件": "主播奖励口径不清、礼物价值被视为收入。", "控制措施": "协议明确、税务处理、奖励独立于随机价值。"},
                {"风险": "个人信息与风控数据", "等级": "中", "触发条件": "设备指纹、行为画像、支付信息处理无告知或超范围。", "控制措施": "隐私政策、最小必要、权限隔离和数据留存期限。"},
            ],
            "columns": ["风险", "等级", "触发条件", "控制措施"],
            "topic_id": topic,
        },
        {
            "id": "remediation_plan",
            "title": "整改建议",
            "items": [
                "删除或重构“充值赠送宝箱后用户可自开”功能，避免充值和随机收益直接绑定。",
                "明确宝箱、钻石、礼物均为平台内虚拟道具，不可转让、不可交易、不可回兑、不可提现、不可兑换实物。",
                "主播奖励采用独立任务评分，不以随机礼物价值、稀有度或用户开箱结果自动结算。",
                "上线概率公示、版本留存、抽取日志、第三方或内部审计复核，并设置异常概率报警。",
                "建立未成年人禁入、限额限次、冷静期提示、投诉退款和人工复核机制。",
                "建设反套现模型：识别主播-用户强关联、批量账号、异常充值、固定互刷、线下返现话术。",
            ],
            "topic_id": topic,
        },
        {
            "id": "launch_checklist",
            "title": "上线前/上线后清单",
            "rows": [
                {"阶段": "上线前红线", "门禁": "不得存在回兑、交易、提现、实物兑换或主播奖励自动按随机价值结算。", "验收证据": "规则文本、产品截图、接口限制、结算规则、风控策略评审记录。"},
                {"阶段": "上线前红线", "门禁": "未成年人不得参与充值、打赏、开箱或宝箱玩法。", "验收证据": "实名/年龄校验链路、拦截日志、退款 SOP。"},
                {"阶段": "上线前门禁", "门禁": "概率、奖池、算法版本、抽取日志可审计。", "验收证据": "概率公示页面、审计报告、日志样本、版本发布记录。"},
                {"阶段": "灰度监测", "门禁": "异常充值、批量账号、主播返现话术和刷量团伙可识别。", "验收证据": "风控看板、处置记录、冻结/封禁 SOP。"},
                {"阶段": "上线后复盘", "门禁": "投诉、退款、未成年人、概率争议每周复核。", "验收证据": "客服工单、合规周报、整改闭环。"},
            ],
            "columns": ["阶段", "门禁", "验收证据"],
            "topic_id": topic,
        },
        {
            "id": "evidence_retention",
            "title": "证据留痕",
            "items": [
                "用户充值、宝箱取得、开箱、打赏、主播开箱、主播奖励计算的全链路日志。",
                "概率配置、奖池配置、版本发布、人工调整和异常报警记录。",
                "禁止交易/回兑的技术拦截记录、违规话术命中、账号封禁和资金冻结记录。",
                "未成年人识别、拦截、监护人投诉和退款处理记录。",
                "主播协议、公会协议、奖励规则、税务处理和结算台账。",
            ],
            "topic_id": topic,
        },
        {
            "id": "backend_audit",
            "title": "后端流程审计",
            "rows": [
                {"环节": "法官分析", "状态": "完成但降级", "记录": f"有效席位 {completed}/{required}，战略门禁未完全通过。"},
                {"环节": "题目分发", "状态": "完成", "记录": "13 席进入网页席位流程。"},
                {"环节": "网页席位回读", "状态": "部分完成", "记录": "7 席有效，6 席失败或超时。"},
                {"环节": "二轮共振", "状态": "完成", "记录": f"二轮共振 {round2}。"},
                {"环节": "最终 HTML 输出", "状态": "已由 public 编译层重建", "记录": "公开页面不输出内部资料库、席位原文或底层轨迹。"},
            ],
            "columns": ["环节", "状态", "记录"],
            "topic_id": topic,
        },
        {"id": "limited_audit_appendix", "title": "有限审计摘要", "body": "公开页面只保留运行完整度摘要；完整调试工作台仅限本机或授权访问。", "topic_id": topic},
    ]


def _lootbox_public_evidence() -> list[dict[str, Any]]:
    return [
        {
            "id": "GAME-RANDOM-2016",
            "title": "文化部关于规范网络游戏运营加强事中事后监管工作的通知",
            "url": "https://zwgk.mct.gov.cn/zfxxgkml/scgl/202012/t20201206_918193.html",
            "summary": "用于评估网络游戏随机抽取、概率公示、抽取记录留存和虚拟道具兑换边界。",
            "topic_id": COMMON_PLATFORM_COMPLIANCE_TOPIC_ID,
        },
        {
            "id": "GAME-CURRENCY-2009",
            "title": "文化部、商务部关于加强网络游戏虚拟货币管理工作的通知",
            "url": "https://zwgk.mct.gov.cn/zfxxgkml/zcfg/gfxwj/202012/t20201204_906151.html",
            "summary": "用于评估游戏币、虚拟道具的发行、使用范围、交易服务和回兑风险。",
            "topic_id": COMMON_PLATFORM_COMPLIANCE_TOPIC_ID,
        },
        {
            "id": "PROMOTION-2020",
            "title": "规范促销行为暂行规定",
            "url": "https://www.gov.cn/zhengce/2020-11/07/content_5558562.htm",
            "summary": "用于评估充值赠送、抽奖式促销、概率/奖项信息披露和误导性促销风险。",
            "topic_id": COMMON_PLATFORM_COMPLIANCE_TOPIC_ID,
        },
        {
            "id": "MINOR-LIVE-2022",
            "title": "关于规范网络直播打赏 加强未成年人保护的意见",
            "url": "https://www.cac.gov.cn/2022-05/07/c_1653537626423773.htm",
            "summary": "用于评估未成年人参与打赏、充值、主播诱导和监护人退款争议。",
            "topic_id": COMMON_PLATFORM_COMPLIANCE_TOPIC_ID,
        },
        {
            "id": "MINOR-GAME-2021",
            "title": "关于进一步严格管理切实防止未成年人沉迷网络游戏的通知",
            "url": "https://www.gov.cn/zhengce/zhengceku/2021-09/01/content_5634661.htm",
            "summary": "用于评估网络游戏场景下未成年人身份识别、时长和充值限制。",
            "topic_id": COMMON_PLATFORM_COMPLIANCE_TOPIC_ID,
        },
        {
            "id": "LIVE-TIPPING-2026",
            "title": "关于加强网络直播打赏规范管理的通知",
            "url": "https://www.cac.gov.cn/2026-04/13/c_1777815804150225.htm",
            "summary": "用于评估当前直播打赏治理、未成年人保护和平台主体责任。",
            "topic_id": COMMON_PLATFORM_COMPLIANCE_TOPIC_ID,
        },
        {
            "id": "ANTI-FRAUD-2022",
            "title": "中华人民共和国反电信网络诈骗法",
            "url": "https://www.gov.cn/xinwen/2022-09/03/content_5708123.htm",
            "summary": "用于评估异常账号、异常交易、互联网服务实名和反套现风险控制。",
            "topic_id": COMMON_PLATFORM_COMPLIANCE_TOPIC_ID,
        },
    ]


def _finance_public_evidence(raw: dict[str, Any]) -> list[dict[str, Any]]:
    bridge = raw.get("web_bridge") if isinstance(raw.get("web_bridge"), dict) else {}
    source = bridge.get("external_evidence") if isinstance(bridge.get("external_evidence"), list) else []
    rows: list[dict[str, Any]] = []
    allowed_topics = {FINANCE_MARKET_TOPIC_ID, COMMON_MARKET_RISK_TOPIC_ID}
    for item in source:
        if not isinstance(item, dict):
            continue
        topic_id = _topic_id_for_evidence(item)
        if topic_id not in allowed_topics:
            continue
        rows.append(
            {
                "id": _public_compiled_text(item.get("id"), "MARKET-EVIDENCE", limit=80),
                "title": _public_compiled_text(item.get("title"), "市场证据", limit=140),
                "url": _text(item.get("url")),
                "summary": _public_compiled_text(item.get("text") or item.get("summary"), "用于核验市场事实或风险边界。", limit=260),
                "topic_id": topic_id,
            }
        )
    return rows


def _filter_sections(model: PublicReportViewModel) -> None:
    if model.kind != "legal_homestead_demolition_report":
        return
    allowed_topics = {model.issue["topicId"], COMMON_CIVIL_LAW_TOPIC_ID}
    model.sections = [
        section
        for section in model.sections
        if section.get("id") in LEGAL_SECTION_ALLOWLIST and section.get("topic_id") in allowed_topics
    ]
    model.evidence = [
        item
        for item in model.evidence
        if item.get("topic_id") in allowed_topics and "LAW-BANKRUPTCY" not in str(item.get("id") or "")
    ]


def _filter_lootbox_sections(model: PublicReportViewModel) -> None:
    allowed_topics = {model.issue["topicId"], COMMON_PLATFORM_COMPLIANCE_TOPIC_ID}
    model.sections = [
        section
        for section in model.sections
        if section.get("id") in LOOTBOX_SECTION_ALLOWLIST and section.get("topic_id") in allowed_topics
    ]
    model.evidence = [item for item in model.evidence if item.get("topic_id") in allowed_topics]


def _filter_finance_sections(model: PublicReportViewModel) -> None:
    allowed_topics = {model.issue["topicId"], COMMON_MARKET_RISK_TOPIC_ID}
    model.sections = [
        section
        for section in model.sections
        if section.get("id") in FINANCE_SECTION_ALLOWLIST and section.get("topic_id") in allowed_topics
    ]
    model.evidence = [item for item in model.evidence if item.get("topic_id") in allowed_topics]


def _issue_from_raw(raw: dict[str, Any]) -> dict[str, Any]:
    question = _text(raw.get("question"))
    if "宅基地" in question and "拆迁" in question:
        return {"topicId": HOMESTEAD_TOPIC_ID, "label": "宅基地房屋拆迁补偿纠纷"}
    if "宝箱" in question and ("主播" in question or "打赏" in question or "合规" in question):
        return {"topicId": LOOTBOX_TOPIC_ID, "label": "宝箱玩法合规风险"}
    q_lower = question.lower()
    if any(token in q_lower for token in ("纳斯达克", "nasdaq", "qqq", "oneq", "tqqq", "指数", "贷款抄底", "抄底")):
        return {"topicId": FINANCE_MARKET_TOPIC_ID, "label": "纳斯达克 30 天走势与贷款抄底风险"}
    return {"topicId": "general_report", "label": "综合裁决报告"}


def _topic_filtered_evidence(raw: dict[str, Any], current_topic_id: str) -> list[dict[str, Any]]:
    bridge = raw.get("web_bridge") if isinstance(raw.get("web_bridge"), dict) else {}
    source = bridge.get("external_evidence") if isinstance(bridge.get("external_evidence"), list) else []
    rows: list[dict[str, Any]] = []
    allowed = {current_topic_id, COMMON_CIVIL_LAW_TOPIC_ID}
    for item in source:
        if not isinstance(item, dict):
            continue
        topic_id = _topic_id_for_evidence(item)
        if topic_id not in allowed:
            continue
        rows.append(
            {
                "id": _text(item.get("id")),
                "title": _text(item.get("title")),
                "url": _text(item.get("url")),
                "summary": _text(item.get("text")),
                "topic_id": topic_id,
            }
        )
    return rows


def _topic_id_for_evidence(item: dict[str, Any]) -> str:
    evidence_id = _text(item.get("id")).upper()
    text = " ".join(_text(item.get(key)) for key in ("id", "title", "text")).lower()
    if "bankruptcy" in evidence_id.lower() or "企业破产法" in text or "破产债权" in text or "迟延履行" in text:
        return "bankruptcy_debt_interest"
    if any(token in text for token in ("nasdaq", "纳斯达克", "qqq", "oneq", "tqqq", "market", "fomc", "cpi", "pce", "federal reserve", "美联储", "指数")):
        return COMMON_MARKET_RISK_TOPIC_ID
    if evidence_id.startswith("GZ-CASE"):
        return HOMESTEAD_TOPIC_ID
    if evidence_id.startswith("LAW-CIVILCODE") or evidence_id.startswith("LAW-LAND"):
        return COMMON_CIVIL_LAW_TOPIC_ID
    return "other"


def _limited_audit(raw: dict[str, Any]) -> dict[str, Any]:
    bridge = raw.get("web_bridge") if isinstance(raw.get("web_bridge"), dict) else {}
    gate = raw.get("high_risk_gate") if isinstance(raw.get("high_risk_gate"), dict) else {}
    strategic_stats = raw.get("_strategic_seat_stats") if isinstance(raw.get("_strategic_seat_stats"), dict) else {}
    round1 = {}
    if isinstance(gate, dict):
        round1 = gate.get("round_1") or gate.get("round1_completion") or {}
    if not isinstance(round1, dict):
        round1 = {}
    round2 = bridge.get("round2_scheduler") if isinstance(bridge.get("round2_scheduler"), dict) else {}
    raw_results = bridge.get("raw_results") if isinstance(bridge.get("raw_results"), list) else []
    attempted = int(
        strategic_stats.get("total")
        or bridge.get("requested_count")
        or len(raw_results)
        or bridge.get("required_count")
        or round1.get("required_expected")
        or 0
    )
    valid = int(
        strategic_stats.get("completed")
        or bridge.get("ok_count")
        or bridge.get("required_ok_count")
        or round1.get("required_completed")
        or 0
    )
    return {
        "surface": "limited",
        "runStatus": _text(raw.get("status") or "complete"),
        "requiredSeats": int(round1.get("required_expected") or bridge.get("required_count") or 0),
        "completedRequiredSeats": int(round1.get("required_completed") or bridge.get("required_ok_count") or 0),
        "attemptedSeats": attempted,
        "validSeats": valid,
        "optionalFailures": max(0, int(bridge.get("failed_count") or 0) - int(bridge.get("required_failed_count") or 0)),
        "round2Scheduled": int(round2.get("scheduled_count") or 0),
        "round2Completed": int(round2.get("completed_count") or 0),
        "notes": [
            "公开报告仅保留运行完整度摘要，不输出内部链路明细。",
            "完整工作台仅限本机或授权访问。",
        ],
    }


def _render_finance_market_body(model: dict[str, Any], sections: dict[str, dict[str, Any]]) -> str:
    return "\n".join(
        block
        for block in (
            _report_header(model),
            _verdict_strip(model),
            _action_rail(model),
            _key_conclusions(model),
            _table_section("market-snapshot", sections.get("market_snapshot") or {}),
            _list_section("judge-reframed-question", sections.get("judge_reframed_question") or {}),
            _table_section("scenario-matrix", sections.get("scenario_matrix") or {}),
            _table_section("leverage-risk", sections.get("leverage_risk") or {}),
            _list_section("catalyst-calendar", sections.get("catalyst_calendar") or {}),
            _table_section("decision-framework", sections.get("decision_framework") or {}),
            _table_section("risk-matrix", sections.get("risk_matrix") or {}),
            _evidence_checklist(model),
            _next_actions(model),
            _limited_audit_appendix(model),
        )
        if block
    )


def _render_lootbox_compliance_body(model: dict[str, Any], sections: dict[str, dict[str, Any]]) -> str:
    return "\n".join(
        block
        for block in (
            _report_header(model),
            _verdict_strip(model),
            _action_rail(model),
            _key_conclusions(model),
            _table_section("rule-decomposition", sections.get("rule_decomposition") or {}),
            _table_section("regulatory-framework", sections.get("regulatory_framework") or {}),
            _table_section("scenario-assessment", sections.get("scenario_assessment") or {}),
            _table_section("abuse-paths", sections.get("abuse_paths") or {}),
            _table_section("risk-matrix", sections.get("risk_matrix") or {}),
            _list_section("remediation-plan", sections.get("remediation_plan") or {}),
            _table_section("launch-checklist", sections.get("launch_checklist") or {}),
            _list_section("evidence-retention", sections.get("evidence_retention") or {}),
            _evidence_checklist(model),
            _limited_audit_appendix(model),
        )
        if block
    )


def _report_header(model: dict[str, Any]) -> str:
    audit = model.get("audit") if isinstance(model.get("audit"), dict) else {}
    return f"""
<header class="report-header">
  <p class="kicker">AI JUDGE PUBLIC REPORT · {html.escape(_text(model.get('kind')))}</p>
  <h1>{html.escape(_text(model.get('title')))}</h1>
  <p class="subtitle">{html.escape(_text(model.get('subtitle')))}</p>
  <div class="header-meta">
    <div class="meta-card"><span>Report ID</span><strong>{html.escape(_text(model.get('reportId')))}</strong></div>
    <div class="meta-card"><span>Surface</span><strong>{html.escape(_text(model.get('surface')))}</strong></div>
    <div class="meta-card"><span>必需席位</span><strong>{audit.get('completedRequiredSeats', 0)}/{audit.get('requiredSeats', 0)}</strong></div>
    <div class="meta-card"><span>二轮共振</span><strong>{audit.get('round2Completed', 0)}/{audit.get('round2Scheduled', 0)}</strong></div>
  </div>
</header>"""


def _verdict_strip(model: dict[str, Any]) -> str:
    verdict = model.get("verdict") if isinstance(model.get("verdict"), dict) else {}
    return f"""
<section class="verdict-strip" aria-label="裁决摘要">
  <div class="verdict-card primary"><span>裁决是什么</span><strong>{html.escape(_text(verdict.get('oneLine')))}</strong></div>
  <div class="verdict-card"><span>最大风险</span><strong>{html.escape(_text(verdict.get('highestRisk')))}</strong></div>
  <div class="verdict-card"><span>不该主张什么</span><strong>{html.escape(_text(verdict.get('doNotClaim')))}</strong></div>
</section>"""


def _action_rail(model: dict[str, Any]) -> str:
    cards = []
    for item in (model.get("actionChecklist") or [])[:4]:
        if not isinstance(item, dict):
            continue
        cards.append(
            f'<div class="action-card"><span>{html.escape(_text(item.get("label")))}</span>'
            f'<strong>{html.escape(_text(item.get("detail")))}</strong></div>'
        )
    return f'<section class="action-rail" aria-label="马上做什么">{"".join(cards)}</section>' if cards else ""


def _key_conclusions(model: dict[str, Any]) -> str:
    items = "".join(f"<li>{html.escape(_text(item))}</li>" for item in model.get("keyConclusions") or [])
    return f'<section class="report-section" id="key-conclusions"><h2>核心结论</h2><ul>{items}</ul></section>' if items else ""


def _case_timeline(section: dict[str, Any]) -> str:
    return _table_section("case-timeline", section)


def _legal_position_card(section: dict[str, Any]) -> str:
    return _table_section("rights-structure", section)


def _litigation_plan(section: dict[str, Any]) -> str:
    return _list_section("litigation-strategy", section)


def _claims_draft(section: dict[str, Any]) -> str:
    return _list_section("claims-draft", section, title_override="诉讼请求")


def _preservation_plan(section: dict[str, Any]) -> str:
    return _list_section("preservation-plan", section, title_override="诉前财产保全")


def _compensation_matrix(section: dict[str, Any]) -> str:
    return _table_section("compensation-matrix", section, title_override="补偿项目矩阵")


def _risk_matrix(section: dict[str, Any]) -> str:
    return _table_section("risk-matrix", section)


def _evidence_checklist(model: dict[str, Any]) -> str:
    evidence = model.get("evidence") if isinstance(model.get("evidence"), list) else []
    rows = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(_text(item.get('id')))}</td>"
            f"<td>{_evidence_link(item)}</td>"
            f"<td>{html.escape(_compact(_text(item.get('summary')), 240))}</td>"
            "</tr>"
        )
    section = _find_section(model, "evidence_checklist")
    checklist = "".join(f"<li>{html.escape(_text(item))}</li>" for item in section.get("items", []))
    _fallback_row = '<tr><td colspan="3">未提供可公开列示证据。</td></tr>'
    table = (
        '<div class="matrix-wrap"><table><thead><tr><th>ID</th><th>来源</th><th>用途/边界</th></tr></thead>'
        f"<tbody>{''.join(rows) or _fallback_row}</tbody></table></div>"
    )
    return f'<section class="report-section" id="evidence-checklist"><h2>证据清单</h2><ul>{checklist}</ul>{table}</section>'


def _next_actions(model: dict[str, Any]) -> str:
    return _list_section("next-actions", _find_section(model, "next_actions"), title_override="下一步行动")


def _limited_audit_appendix(model: dict[str, Any]) -> str:
    audit = model.get("audit") if isinstance(model.get("audit"), dict) else {}
    notes = "".join(f"<li>{html.escape(_text(note))}</li>" for note in audit.get("notes", []))
    return f"""
<section class="report-section" id="limited-audit-appendix">
  <h2>有限审计附录</h2>
  <div class="card-grid">
    <div class="meta-card"><span>运行状态</span><strong>{html.escape(_text(audit.get('runStatus')))}</strong></div>
    <div class="meta-card"><span>必需席位</span><strong>{audit.get('completedRequiredSeats', 0)}/{audit.get('requiredSeats', 0)}</strong></div>
    <div class="meta-card"><span>二轮共振</span><strong>{audit.get('round2Completed', 0)}/{audit.get('round2Scheduled', 0)}</strong></div>
    <div class="meta-card"><span>可选失败</span><strong>{audit.get('optionalFailures', 0)}</strong></div>
  </div>
  <ul>{notes}</ul>
</section>"""


def _list_section(anchor: str, section: dict[str, Any], *, title_override: str = "") -> str:
    if not section:
        return ""
    title = title_override or _text(section.get("title") or anchor)
    body = f"<p>{html.escape(_text(section.get('body')))}</p>" if section.get("body") else ""
    items = "".join(f"<li>{html.escape(_text(item))}</li>" for item in section.get("items") or [])
    return f'<section class="report-section" id="{html.escape(anchor)}"><h2>{html.escape(title)}</h2>{body}<ul>{items}</ul></section>'


def _table_section(anchor: str, section: dict[str, Any], *, title_override: str = "") -> str:
    if not section:
        return ""
    title = title_override or _text(section.get("title") or anchor)
    columns = [_text(column) for column in section.get("columns") or []]
    if not columns:
        return ""
    head = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
    rows = []
    for row in section.get("rows") or []:
        if isinstance(row, dict):
            cells = [_text(row.get(column, "")) for column in columns]
        else:
            cells = [_text(value) for value in row]
        rows.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in cells) + "</tr>")
    return (
        f'<section class="report-section" id="{html.escape(anchor)}"><h2>{html.escape(title)}</h2>'
        '<div class="matrix-wrap"><table>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody>"
        "</table></div></section>"
    )


def _find_section(model: dict[str, Any], section_id: str) -> dict[str, Any]:
    for section in model.get("sections") or []:
        if isinstance(section, dict) and section.get("id") == section_id:
            return section
    return {}


def _evidence_link(item: dict[str, Any]) -> str:
    url = _text(item.get("url"))
    title = _text(item.get("title"))
    if not url:
        return html.escape(title)
    return f'<a href="{html.escape(url)}">{html.escape(title)}</a>'


def _safe_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    if _text(value):
        return [_text(value)]
    return []


def _compact(value: str, limit: int) -> str:
    text = " ".join(_text(value).split())
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def _public_compiled_text(value: Any, fallback: str, *, limit: int = 400) -> str:
    text = _compact(_text(value), limit)
    forbidden = (
        "internal-library",
        "raw-json",
        "prompt-flow",
        "seat-answers",
        "mentor-supplements",
        "deliberation",
        "Evidence OS",
        "P3.3 Runtime Harness",
        "Chrome CDP",
        "seat_answer_poll",
        "source_lineage",
        "Prompt / JSON",
        "event logs",
        "browser profile",
        "automation config",
        "report-manuscript",
        "publicReportMarkdown",
    )
    if not text or any(marker in text for marker in forbidden):
        return fallback
    return text


def _public_business_decision_text(value: Any, fallback: str, *, limit: int = 400) -> str:
    text = _public_compiled_text(value, fallback, limit=limit)
    if any(marker in text for marker in PUBLIC_OPERATIONAL_DECISION_MARKERS):
        return fallback
    return text


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
