#!/usr/bin/env python3
"""High-risk formal verdict blocker brief renderer."""

from __future__ import annotations

import html
from typing import Any

from core.high_risk_domain_gate import (
    BLOCKER_BRIEF_REPORT_TYPE,
    DOMAIN_PENDING_DOSSIER_SLOTS,
    evaluate_high_risk_domain_gate,
)
from core.required_seat_recovery_queue import build_required_seat_recovery_queue
from product.reporting.partial_evidence_digest import build_partial_evidence_digest


INCOMPLETE_REPORT_SCHEMA = "ai_judge.high_risk_formal_verdict_blocker_brief.v1"
REPORT_NAME_EN = "High-Risk Formal Verdict Blocker Brief"
REPORT_NAME_ZH = "高风险正式裁决阻断诊断单"

DOMAIN_SUMMARIES = {
    "finance": "本报告未签发金融正式裁决；RIA/SEC、fiduciary、advice vs education、trade execution、AI-washing 的结构化证据链仍被缺失席位阻断。",
    "medical": "本报告未签发医疗正式裁决；FDA/SaMD/CDS、clinical validation、human clinician responsibility、shutdown rollback、bias monitoring 的结构化证据链仍被缺失席位阻断。",
    "legal": "本报告未签发法律正式裁决；privilege、UPL、attorney supervision、citation lock、court candor、client consent 的结构化证据链仍被缺失席位阻断。",
}

DOMAIN_CANNOT_CONCLUDE = {
    "finance": [
        "不能判断 AI 金融顾问是否可上线。",
        "不能判断 RIA/SEC 与 fiduciary 边界是否满足。",
        "不能判断个性化投资建议、教育信息和交易草案的边界。",
        "不能判断广告、AI-washing 和客户适当性披露是否合格。",
    ],
    "medical": [
        "不能判断该系统是否满足 FDA/SaMD/CDS 路径。",
        "不能判断临床验证是否足够。",
        "不能判断医生责任边界、停机回滚、偏倚监控和 PHI/HIPAA 控制是否合格。",
    ],
    "legal": [
        "不能判断 privilege/confidentiality 控制是否充分。",
        "不能判断 UPL、律师监督、citation lock、法院 candor、客户同意和跨州规则差异是否合格。",
    ],
}

DOMAIN_BLOCKER_REASONS = {
    "finance": "金融 run 虽执行结束，但 R1 必需席位缺失，RIA/SEC、fiduciary、advice vs education、trade execution 与 AI-washing 证据链不足。",
    "medical": "医疗 run 虽执行结束，但 R1 必需席位缺失，FDA/SaMD/CDS、clinical validation、human clinician responsibility、shutdown rollback 与 bias monitoring 证据链不足。",
    "legal": "法律 run 虽执行结束，但 R1 必需席位缺失，privilege、UPL、attorney supervision、citation lock、court candor 与 client consent 证据链不足。",
}

SLOT_KEYWORDS = {
    "ria_sec_boundary": ["ria", "sec", "投资顾问", "监管"],
    "fiduciary_duty": ["fiduciary", "受托", "信义"],
    "advice_vs_education_boundary": ["advice", "education", "建议", "教育"],
    "ai_washing_and_advertising": ["ai-washing", "washing", "广告", "宣传"],
    "trade_execution_gate": ["trade", "execution", "交易", "执行"],
    "human_approval_points": ["human", "approval", "人工", "审批"],
    "audit_trail": ["audit", "审计", "留痕"],
    "suitability_and_risk_profile": ["suitability", "适当性", "风险画像"],
    "privacy_security": ["privacy", "security", "隐私", "安全"],
    "intended_use": ["intended use", "预期用途", "适用场景"],
    "fda_samd_cds_classification": ["fda", "samd", "cds"],
    "clinical_validation": ["clinical validation", "临床验证", "验证"],
    "human_clinician_responsibility": ["clinician", "医生", "责任"],
    "shutdown_rollback": ["shutdown", "rollback", "停机", "回滚"],
    "bias_monitoring": ["bias", "偏倚", "公平"],
    "ehr_phi_hipaa": ["ehr", "phi", "hipaa"],
    "incident_response": ["incident", "应急", "响应"],
    "privilege_confidentiality": ["privilege", "confidentiality", "保密", "特权"],
    "upl_and_attorney_supervision": ["upl", "attorney supervision", "律师监督"],
    "citation_lock": ["citation", "引用", "判例"],
    "court_candor": ["court candor", "candor", "法院", "诚信"],
    "client_consent": ["client consent", "客户同意", "同意"],
    "access_control": ["access control", "访问控制", "权限"],
    "cross_jurisdiction_rules": ["jurisdiction", "跨州", "管辖"],
    "blocked_use_cases": ["blocked", "禁用", "不得"],
}


def build_incomplete_high_risk_report(
    verdict: dict[str, Any],
    gate: dict[str, Any] | None = None,
    recovery_queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = gate if isinstance(gate, dict) else evaluate_high_risk_domain_gate(verdict)
    recovery_queue = recovery_queue if isinstance(recovery_queue, dict) else build_required_seat_recovery_queue(verdict, gate)
    domain = str(gate.get("domain") or "unknown")
    round1 = gate.get("round_1") or gate.get("round1_completion") or {}
    round2 = gate.get("round_2") or gate.get("round2_completion") or {}
    impact_matrix = gate.get("missing_seat_impact_matrix") if isinstance(gate.get("missing_seat_impact_matrix"), list) else []
    blocking = gate.get("blocking_missing_seats") if isinstance(gate.get("blocking_missing_seats"), list) else []
    quality = gate.get("quality_recovery_seats") if isinstance(gate.get("quality_recovery_seats"), list) else []
    digest_missing = _digest_missing_items(impact_matrix, blocking)
    partial_digest = build_partial_evidence_digest(
        domain=domain,
        returned_seat_claims=verdict.get("claims") if isinstance(verdict.get("claims"), list) else [],
        missing_required_seats=digest_missing,
        domain_slots=DOMAIN_PENDING_DOSSIER_SLOTS.get(domain, []),
    )
    pending = _pending_dossier(domain, gate, partial_digest)
    first_screen = {
        "formal_verdict": "NOT_ISSUED",
        "blocker_reason": DOMAIN_BLOCKER_REASONS.get(domain, "高风险 run 缺少正式裁决所需的必需席位和领域 slot。"),
        "missing_impact": _first_screen_impacts(impact_matrix),
        "minimum_recovery_actions": (recovery_queue.get("minimum_actions") or [])[:3],
        "regeneration_condition": str(recovery_queue.get("regeneration_condition") or _default_regeneration_condition(domain)),
    }
    return {
        "schema": INCOMPLETE_REPORT_SCHEMA,
        "report_type": BLOCKER_BRIEF_REPORT_TYPE,
        "report_name": REPORT_NAME_EN,
        "report_name_zh": REPORT_NAME_ZH,
        "run_id": str(verdict.get("run_id") or ""),
        "domain": domain,
        "formal_verdict": "NOT_ISSUED",
        "execution_status": str(gate.get("execution_status") or "COMPLETED_WITH_MISSING_REQUIRED_SEATS"),
        "formal_report_status": str(gate.get("formal_report_status") or gate.get("publish_gate") or "BLOCKED_REQUIRED_SEATS"),
        "evidence_status": str(gate.get("evidence_status") or (gate.get("evidence_confidence") or {}).get("label") or "INSUFFICIENT_FOR_FORMAL_VERDICT"),
        "evidence_confidence": gate.get("evidence_confidence") or {"label": "INSUFFICIENT_FOR_FORMAL_VERDICT"},
        "first_screen": first_screen,
        "domain_summary": DOMAIN_SUMMARIES.get(domain, "高风险正式裁决被阻断，必须补齐领域证据链。"),
        "missing_required_seats": gate.get("missing_required_seats") if isinstance(gate.get("missing_required_seats"), list) else [],
        "blocking_missing_seats": blocking,
        "quality_recovery_seats": quality,
        "missing_seat_impact_matrix": impact_matrix,
        "partial_evidence_digest": partial_digest,
        "pending_dossier": pending,
        "round_1": round1,
        "round_2": round2,
        "round1_completion": round1,
        "round2_completion": round2,
        "why_formal_report_is_blocked": _blocked_reasons(gate, domain),
        "trusted_from_partial_evidence": _trusted_from_partial_evidence(domain),
        "cannot_be_concluded": DOMAIN_CANNOT_CONCLUDE.get(domain, ["不能判断该高风险系统是否满足正式上线或部署条件。"]),
        "recovery_queue_actions": recovery_queue.get("actions") or [],
        "required_re_run_plan": recovery_queue.get("minimum_actions") or [],
        "regeneration_condition": [str(recovery_queue.get("regeneration_condition") or _default_regeneration_condition(domain))],
        "recovery_queue": recovery_queue,
        "required_slots": gate.get("required_slots") or {},
    }


def render_incomplete_high_risk_report_html(report: dict[str, Any]) -> str:
    esc = html.escape
    domain = str(report.get("domain") or "unknown")
    first = report.get("first_screen") if isinstance(report.get("first_screen"), dict) else {}
    r1 = report.get("round_1") or {}
    r2 = report.get("round_2") or {}
    queue = report.get("recovery_queue") or {}
    title = f"{REPORT_NAME_ZH} · {domain.upper()} · NOT_ISSUED"
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif; background:#f6f7f9; color:#172033; }}
    main {{ max-width:1120px; margin:0 auto; padding:28px 20px 48px; }}
    .hero {{ background:#fff; border:2px solid #c84655; border-radius:8px; padding:22px; margin-bottom:16px; }}
    .badge {{ display:inline-block; background:#fee2e2; color:#991b1b; font-weight:800; padding:6px 10px; border-radius:999px; }}
    h1 {{ margin:14px 0 8px; font-size:32px; line-height:1.2; }}
    h2 {{ font-size:20px; margin:0 0 10px; }}
    section {{ background:#fff; border:1px solid #d7e2ef; border-radius:8px; padding:18px; margin:12px 0; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .card {{ border:1px solid #d7e2ef; border-radius:8px; padding:12px; background:#fbfcfe; }}
    .card span {{ display:block; color:#64748b; font-size:12px; margin-bottom:6px; }}
    .card strong {{ display:block; overflow-wrap:anywhere; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ border-bottom:1px solid #e5e7eb; text-align:left; vertical-align:top; padding:9px; }}
    th {{ color:#64748b; background:#f8fafc; }}
    li {{ margin:6px 0; line-height:1.55; }}
    .blocked {{ color:#c84655; font-weight:800; }}
    .muted {{ color:#64748b; }}
    @media (max-width: 760px) {{ .grid {{ grid-template-columns:1fr; }} h1 {{ font-size:26px; }} }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <span class="badge">{esc(str(report.get("formal_report_status") or "BLOCKED_REQUIRED_SEATS"))}</span>
    <h1>{REPORT_NAME_ZH}</h1>
    <p><strong>正式裁决：未签发</strong> <span class="blocked">NOT_ISSUED</span></p>
    <p><strong>阻断原因：</strong>{esc(str(first.get("blocker_reason") or ""))}</p>
    {_inline_list("缺失影响", first.get("missing_impact") or [])}
    {_inline_list("最小恢复动作", first.get("minimum_recovery_actions") or [])}
    <p><strong>预计重生成条件：</strong>{esc(str(first.get("regeneration_condition") or ""))}</p>
  </section>
  <section>
    <h2>{REPORT_NAME_EN}</h2>
    <p>{esc(str(report.get("domain_summary") or ""))}</p>
    <div class="grid">
      <div class="card"><span>Run ID</span><strong>{esc(str(report.get("run_id") or ""))}</strong></div>
      <div class="card"><span>Domain</span><strong>{esc(domain)}</strong></div>
      <div class="card"><span>Formal verdict</span><strong class="blocked">NOT_ISSUED</strong></div>
      <div class="card"><span>Evidence status</span><strong>{esc(str(report.get("evidence_status") or ""))}</strong></div>
    </div>
  </section>
  <section>
    <h2>Status Split</h2>
    <div class="grid">
      <div class="card"><span>execution_status</span><strong>{esc(str(report.get("execution_status") or ""))}</strong></div>
      <div class="card"><span>formal_report_status</span><strong>{esc(str(report.get("formal_report_status") or ""))}</strong></div>
      <div class="card"><span>formal_verdict</span><strong class="blocked">NOT_ISSUED</strong></div>
      <div class="card"><span>evidence_status</span><strong>{esc(str(report.get("evidence_status") or ""))}</strong></div>
    </div>
  </section>
  <section>
    <h2>Round Completion</h2>
    <div class="grid">
      <div class="card"><span>Round 1 total</span><strong>{esc(str(r1.get("total_completed", r1.get("ok_count", 0))))}/{esc(str(r1.get("total_expected", r1.get("requested_count", 0))))}</strong></div>
      <div class="card"><span>Round 1 required</span><strong>{esc(str(r1.get("required_completed", r1.get("required_valid_count", 0))))}/{esc(str(r1.get("required_expected", r1.get("required_count", 0))))}</strong></div>
      <div class="card"><span>R1 required missing</span><strong>{esc(str(r1.get("required_missing", 0)))}</strong></div>
      <div class="card"><span>Round 2 total</span><strong>{esc(str(r2.get("total_completed", r2.get("completed_count", 0))))}/{esc(str(r2.get("total_expected", r2.get("scheduled_count", 0))))}</strong></div>
    </div>
  </section>
  <section>
    <h2>已返回内容摘要 / Partial Evidence Digest</h2>
    {_digest_html(report.get("partial_evidence_digest") or {})}
  </section>
  <section>
    <h2>Missing Seat Impact Matrix</h2>
    {_impact_table(report.get("missing_seat_impact_matrix") or [])}
  </section>
  <section>
    <h2>Blocking Missing Seats</h2>
    {_queue_table(queue.get("blocking_missing_seats") or [])}
  </section>
  <section>
    <h2>Quality Recovery Seats</h2>
    {_queue_table(queue.get("quality_recovery_seats") or [])}
  </section>
  <section>
    <h2>{_pending_title(domain)}</h2>
    {_pending_table(report.get("pending_dossier") or [])}
  </section>
  {_section_list("Why Formal Report Is Blocked", report.get("why_formal_report_is_blocked") or [])}
  {_section_list("What Can Be Trusted From Partial Evidence", report.get("trusted_from_partial_evidence") or [])}
  {_section_list("What Cannot Be Concluded", report.get("cannot_be_concluded") or [])}
  {_section_list("Recovery Queue Actions", report.get("recovery_queue_actions") or [])}
  {_section_list("Regeneration Condition", report.get("regeneration_condition") or [])}
</main>
</body>
</html>"""


def render_incomplete_high_risk_report_markdown(report: dict[str, Any]) -> str:
    first = report.get("first_screen") if isinstance(report.get("first_screen"), dict) else {}
    r1 = report.get("round_1") or {}
    r2 = report.get("round_2") or {}
    lines = [
        f"# {REPORT_NAME_ZH}",
        "",
        f"Report type: {REPORT_NAME_EN}",
        f"Run ID: {report.get('run_id')}",
        f"Domain: {report.get('domain')}",
        "Formal verdict: NOT_ISSUED",
        f"execution_status: {report.get('execution_status')}",
        f"formal_report_status: {report.get('formal_report_status')}",
        f"evidence_status: {report.get('evidence_status')}",
        "",
        "## First Screen",
        "正式裁决：未签发",
        f"阻断原因：{first.get('blocker_reason')}",
        "缺失影响：",
    ]
    lines.extend(f"- {item}" for item in first.get("missing_impact") or [])
    lines.append("最小恢复动作：")
    lines.extend(f"- {item}" for item in first.get("minimum_recovery_actions") or [])
    lines.append(f"预计重生成条件：{first.get('regeneration_condition')}")
    lines.extend([
        "",
        "## Round Completion",
        f"- Round 1 total: {r1.get('total_completed', r1.get('ok_count', 0))}/{r1.get('total_expected', r1.get('requested_count', 0))}",
        f"- Round 1 required: {r1.get('required_completed', r1.get('required_valid_count', 0))}/{r1.get('required_expected', r1.get('required_count', 0))}",
        f"- Round 1 required missing: {r1.get('required_missing', 0)}",
        f"- Round 2 total: {r2.get('total_completed', r2.get('completed_count', 0))}/{r2.get('total_expected', r2.get('scheduled_count', 0))}",
        "",
        "## 已返回内容摘要 / Partial Evidence Digest",
    ])
    digest = report.get("partial_evidence_digest") or {}
    gate = digest.get("content_quality_gate") if isinstance(digest.get("content_quality_gate"), dict) else {}
    lines.append(f"digest_status: {digest.get('digest_status')}")
    lines.extend([
        "已返回内容质量：",
        f"- raw claims: {digest.get('claim_count') or 0}",
        f"- domain matched claims: {digest.get('domain_claim_count') or 0}",
        f"- usable claims: {digest.get('usable_claim_count') or 0}",
        f"- discarded claims: {digest.get('discarded_claim_count') or 0}",
        f"- content_quality: {gate.get('content_quality') or 'UNREADABLE'}",
    ])
    for key in ["readable_summary", "early_consensus", "key_disagreements", "missing_evidence_blocks"]:
        lines.append(f"{key}:")
        for item in digest.get(key) or []:
            lines.append(f"- {item}")
    lines.extend([
        "",
        "## Missing Seat Impact Matrix",
    ])
    for item in report.get("missing_seat_impact_matrix") or []:
        slots = ", ".join(item.get("blocked_domain_slots") or [])
        lines.append(f"- {item.get('seat_id')} / {item.get('round')} / {item.get('blocking_level')} / {item.get('information_mandate')} / slots: {slots}")
    lines.extend(["", "## Blocking Missing Seats"])
    for item in (report.get("recovery_queue") or {}).get("blocking_missing_seats") or []:
        lines.append(f"- {item.get('seat_id')} / {item.get('round')} / {item.get('failure_reason')} / {item.get('recovery_status')}")
    lines.extend(["", "## Quality Recovery Seats"])
    for item in (report.get("recovery_queue") or {}).get("quality_recovery_seats") or []:
        lines.append(f"- {item.get('seat_id')} / {item.get('round')} / {item.get('failure_reason')} / {item.get('recovery_status')}")
    lines.extend(["", f"## {_pending_title(str(report.get('domain') or ''))}"])
    for row in report.get("pending_dossier") or []:
        blocking = ", ".join(row.get("blocking_seats") or [])
        lines.append(
            f"- {row.get('slot')}: {row.get('status')} — 可读初步判断：{row.get('readable_preliminary_judgment')}；"
            f"为什么重要：{row.get('why_it_matters')}；缺失证据：{row.get('missing_evidence')}；阻断席位：{blocking}"
        )
    for title, key in [
        ("Why Formal Report Is Blocked", "why_formal_report_is_blocked"),
        ("What Can Be Trusted From Partial Evidence", "trusted_from_partial_evidence"),
        ("What Cannot Be Concluded", "cannot_be_concluded"),
        ("Recovery Queue Actions", "recovery_queue_actions"),
        ("Regeneration Condition", "regeneration_condition"),
    ]:
        lines.extend(["", f"## {title}"])
        for item in report.get(key) or []:
            lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def _blocked_reasons(gate: dict[str, Any], domain: str) -> list[str]:
    reasons = [str(item) for item in gate.get("blocked_reasons") or [] if item]
    domain_reason = DOMAIN_BLOCKER_REASONS.get(domain)
    if domain_reason and domain_reason not in reasons:
        reasons.insert(0, domain_reason)
    return reasons or ["高风险领域证据不足，正式领域报告被确定性门禁阻断。"]


def _trusted_from_partial_evidence(domain: str) -> list[str]:
    label = {
        "finance": "金融",
        "medical": "医疗",
        "legal": "法律",
    }.get(domain, "高风险领域")
    return [
        f"可以信任 {label} run 的运行审计事实：哪些席位返回、哪些席位缺失、二轮追问完成度和 recovery queue。",
        "可以把已返回席位的原文作为待复核材料，但不能把它们提升为正式领域裁决。",
        "可以使用 Missing Seat Impact Matrix 判断先补哪些信息责任和 blocked domain slots。",
    ]


def _pending_dossier(
    domain: str,
    gate: dict[str, Any],
    partial_digest: dict[str, Any],
) -> list[dict[str, Any]]:
    slots = DOMAIN_PENDING_DOSSIER_SLOTS.get(domain, [])
    missing_slots = set(((gate.get("required_slots") or {}).get("missing_slots") or []))
    findings = {
        str(row.get("slot") or ""): row
        for row in partial_digest.get("domain_relevant_findings") or []
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for slot in slots:
        finding = findings.get(slot) or {}
        if slot not in missing_slots:
            status = "READY_FOR_REVIEW"
            judgment = str(finding.get("readable_preliminary_judgment") or "该判断项已有可读初步判断。")
            why = str(finding.get("why_it_matters") or "这决定该判断项是否具备可复核治理边界。")
            missing = "该判断项当前不阻断正式报告。"
            blocking_seats: list[str] = []
        elif finding.get("status") == "PRELIMINARY_ONLY":
            status = "PRELIMINARY_ONLY"
            judgment = str(finding.get("readable_preliminary_judgment") or "未从质量门禁后的可用 claim 中形成可读初步判断。")
            why = str(finding.get("why_it_matters") or "这决定该判断项是否具备可复核治理边界。")
            missing = str(finding.get("missing_evidence") or "缺少阻断席位的交叉验证。")
            blocking_seats = [str(seat) for seat in finding.get("blocking_seats") or [] if seat]
        else:
            status = "MISSING"
            judgment = "未从质量门禁后的可用 claim 中形成可读初步判断。"
            why = str(finding.get("why_it_matters") or "这决定该判断项是否具备可复核治理边界。")
            missing = str(finding.get("missing_evidence") or "需要补跑阻断席位并重新抽取。")
            blocking_seats = [str(seat) for seat in finding.get("blocking_seats") or [] if seat]
        rows.append({
            "slot": slot,
            "readable_preliminary_judgment": judgment,
            "why_it_matters": why,
            "missing_evidence": missing,
            "blocking_seats": blocking_seats,
            "status": status,
            "why": missing,
        })
    return rows


def _digest_missing_items(impact_matrix: list[Any], blocking: list[Any]) -> list[dict[str, Any]]:
    rows = [
        dict(item)
        for item in impact_matrix
        if isinstance(item, dict) and item.get("blocking_level") == "P0_BLOCKING"
    ]
    if rows:
        return rows
    return [dict(item) for item in blocking if isinstance(item, dict)]


def _first_screen_impacts(impact_matrix: list[Any]) -> list[str]:
    rows = [row for row in impact_matrix if isinstance(row, dict) and row.get("blocking_level") == "P0_BLOCKING"]
    if not rows:
        rows = [row for row in impact_matrix if isinstance(row, dict)]
    impacts: list[str] = []
    for row in rows[:3]:
        slots = "、".join(str(slot) for slot in (row.get("blocked_domain_slots") or [])[:3])
        impacts.append(f"{row.get('seat_id')} 缺席：{row.get('information_mandate')} 未回收，阻断 {slots or '领域关键 slot'}。")
    return impacts or ["缺少必需席位与领域 required slots，无法形成正式裁决证据链。"]


def _default_regeneration_condition(domain: str) -> str:
    return f"{domain} 的必需席位补齐、evidence matrix 重合并、Pending Dossier 全部 READY 后重新生成正式领域报告。"


def _pending_title(domain: str) -> str:
    return {
        "finance": "Finance Pending Dossier",
        "medical": "Medical Pending Dossier",
        "legal": "Legal Pending Dossier",
    }.get(domain, "Pending Dossier")


def _section_list(title: str, items: list[Any]) -> str:
    rows = "".join(f"<li>{html.escape(str(item))}</li>" for item in items) or "<li>无。</li>"
    return f"<section><h2>{html.escape(title)}</h2><ol>{rows}</ol></section>"


def _digest_html(digest: dict[str, Any]) -> str:
    status = html.escape(str(digest.get("digest_status") or "FAILED"))
    gate = digest.get("content_quality_gate") if isinstance(digest.get("content_quality_gate"), dict) else {}
    chunks = [
        f'<p><strong>摘要状态：</strong>{status}</p>',
        "<h3>已返回内容质量</h3>"
        "<ul>"
        f"<li>raw claims: {html.escape(str(digest.get('claim_count') or 0))}</li>"
        f"<li>domain matched claims: {html.escape(str(digest.get('domain_claim_count') or 0))}</li>"
        f"<li>usable claims: {html.escape(str(digest.get('usable_claim_count') or 0))}</li>"
        f"<li>discarded claims: {html.escape(str(digest.get('discarded_claim_count') or 0))}</li>"
        f"<li>content_quality: {html.escape(str(gate.get('content_quality') or 'UNREADABLE'))}</li>"
        "</ul>",
        _mini_section("可读摘要", digest.get("readable_summary") or []),
        _mini_section("初步共识", digest.get("early_consensus") or []),
        _mini_section("主要分歧", digest.get("key_disagreements") or []),
        _mini_section("不能签发的直接证据缺口", digest.get("missing_evidence_blocks") or []),
        _mini_section("降级或无关内容", digest.get("unsupported_or_irrelevant_content") or []),
    ]
    return "".join(chunks)


def _mini_section(title: str, items: list[Any]) -> str:
    rows = "".join(f"<li>{html.escape(str(item))}</li>" for item in items) or "<li>无。</li>"
    return f"<h3>{html.escape(title)}</h3><ul>{rows}</ul>"


def _inline_list(title: str, items: list[Any]) -> str:
    rows = "".join(f"<li>{html.escape(str(item))}</li>" for item in items[:3]) or "<li>无。</li>"
    return f"<p><strong>{html.escape(title)}：</strong></p><ul>{rows}</ul>"


def _impact_table(items: list[Any]) -> str:
    rows = ""
    for item in items:
        if not isinstance(item, dict):
            continue
        rows += (
            "<tr>"
            f"<td>{html.escape(str(item.get('seat_id') or ''))}</td>"
            f"<td>{html.escape(str(item.get('round') or ''))}</td>"
            f"<td>{html.escape(str(item.get('blocking_level') or ''))}</td>"
            f"<td>{html.escape(str(item.get('information_mandate') or ''))}</td>"
            f"<td>{html.escape('、'.join(str(slot) for slot in item.get('blocked_domain_slots') or []))}</td>"
            f"<td>{html.escape(str(item.get('why_it_matters') or ''))}</td>"
            f"<td>{html.escape(str(item.get('retry_action') or ''))}</td>"
            f"<td>{html.escape(str(item.get('recovery_status') or ''))}</td>"
            "</tr>"
        )
    rows = rows or '<tr><td colspan="8">无缺失席位影响记录。</td></tr>'
    return (
        "<table><thead><tr><th>seat_id</th><th>round</th><th>blocking_level</th>"
        "<th>information_mandate</th><th>blocked_domain_slots</th><th>why_it_matters</th>"
        "<th>retry_action</th><th>recovery_status</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _queue_table(items: list[Any]) -> str:
    rows = ""
    for item in items:
        if not isinstance(item, dict):
            continue
        rows += (
            "<tr>"
            f"<td>{html.escape(str(item.get('seat_id') or ''))}</td>"
            f"<td>{html.escape(str(item.get('required') or False))}</td>"
            f"<td>{html.escape(str(item.get('round') or ''))}</td>"
            f"<td>{html.escape(str(item.get('failure_reason') or ''))}</td>"
            f"<td>{html.escape(str(item.get('retry_policy') or ''))}</td>"
            f"<td>{html.escape(str(item.get('max_retry') or ''))}</td>"
            f"<td>{html.escape(str(item.get('recovery_status') or ''))}</td>"
            "</tr>"
        )
    rows = rows or '<tr><td colspan="7">无。</td></tr>'
    return (
        "<table><thead><tr><th>seat_id</th><th>required</th><th>round</th>"
        "<th>failure_reason</th><th>retry_policy</th><th>max_retry</th><th>recovery_status</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _pending_table(items: list[Any]) -> str:
    rows = ""
    for item in items:
        if not isinstance(item, dict):
            continue
        blocking = "、".join(str(seat) for seat in item.get("blocking_seats") or [])
        rows += (
            "<tr>"
            f"<td>{html.escape(str(item.get('slot') or ''))}</td>"
            f"<td>{html.escape(str(item.get('readable_preliminary_judgment') or ''))}</td>"
            f"<td>{html.escape(str(item.get('why_it_matters') or ''))}</td>"
            f"<td>{html.escape(str(item.get('missing_evidence') or ''))}</td>"
            f"<td>{html.escape(blocking)}</td>"
            f"<td>{html.escape(str(item.get('status') or ''))}</td>"
            "</tr>"
        )
    rows = rows or '<tr><td colspan="6">无 pending dossier。</td></tr>'
    return (
        "<table><thead><tr><th>slot</th><th>可读初步判断</th><th>为什么重要</th><th>缺失证据</th>"
        "<th>阻断席位</th><th>状态</th></tr></thead><tbody>" + rows + "</tbody></table>"
    )
