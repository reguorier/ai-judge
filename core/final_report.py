#!/usr/bin/env python3
"""Paper-style final report assembly for AI Judge verdicts."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any


FINAL_REPORT_SCHEMA = "ai_judge.final_report.v1"


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
    recommendation = _recommendation(steps, complete=complete, coverage=coverage, verdict_label=verdict_label)
    thesis = _thesis(verdict, question, verdict_label)
    keywords = _keywords(question, reasons, agreements, verdict_label, trust)
    abstract = _abstract(
        judge_editor=judge_editor,
        verdict_label=verdict_label,
        confidence=confidence,
        trust=trust,
        coverage=coverage,
        complete=complete,
        recommendation=recommendation,
        findings=findings,
    )
    plan = _implementation_plan(steps, complete=complete, coverage=coverage, verdict_label=verdict_label, recommendation=recommendation)
    risks = _risks_and_limits(limits, disagreements, coverage, verdict, trust)
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
        "abstract": abstract,
        "thesis": thesis,
        "recommendation": recommendation,
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
    lines: list[str] = [
        f"## {report.get('title') or 'AI Judge 最终方案报告'}",
        "",
        f"**{report.get('subtitle') or FINAL_REPORT_SCHEMA}**",
        "",
        f"**状态:** {report.get('status_label', '-')} · {report.get('status_reason', '-')}",
        "",
        "### ABSTRACT",
        "",
        str(report.get("abstract") or ""),
        "",
    ]
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
    return (
        '<section class="paper-report" id="final-report">'
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
        "</section>"
    )


def _abstract(
    *,
    judge_editor: dict[str, str],
    verdict_label: str,
    confidence: str,
    trust: str,
    coverage: dict[str, Any],
    complete: bool,
    recommendation: str,
    findings: list[str],
) -> str:
    basis = "；".join(findings[:2]) or "当前证据仍需继续补强"
    boundary = "可作为最终方案进入执行复核。" if complete else "因席位未全量闭环，只能作为阶段性方案，不能包装为全模型最终共识。"
    return (
        f"{judge_editor['label']}收口：本轮结论为“{verdict_label}”，可信度 {confidence}，"
        f"可信等级 {trust or '-'}，席位覆盖 {coverage['label']}。"
        f"最终建议：{recommendation}。核心依据：{basis}。{boundary}"
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
    plan = _unique_texts(steps, limit=6)
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
) -> str:
    if not complete:
        return f"先补齐必需席位覆盖 {coverage['label']}，再把“{verdict_label}”作为可执行决策。"
    if steps:
        return _compact(steps[0], 130)
    return f"将“{verdict_label}”拆成一页目标、证据、执行动作和验收指标，并在人工确认后推进。"


def _key_findings(
    verdict: dict[str, Any],
    coverage: dict[str, Any],
    reasons: list[str],
    agreements: list[str],
    top_seats: list[str],
) -> list[str]:
    findings: list[str] = []
    one_liner = _compact(verdict.get("one_liner") or "", 120)
    if one_liner:
        findings.append(one_liner)
    if reasons:
        findings.extend(reasons[:2])
    if agreements:
        findings.append(f"主要共识：{agreements[0]}")
    if top_seats:
        findings.append(f"主要支撑席位：{'、'.join(top_seats[:3])}。")
    if coverage["failed"]:
        findings.append(f"仍有 {coverage['failed']} 个席位未形成有效最终答案，覆盖边界为 {coverage['label']}。")
    if not findings:
        findings.append(_compact(verdict.get("one_liner") or "本轮已有判词，但仍需人工复核证据链。", 120))
    return _unique_texts(findings, limit=5)


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
