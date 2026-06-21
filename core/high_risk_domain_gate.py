#!/usr/bin/env python3
"""Deterministic gate for high-risk domain AI Judge reports."""

from __future__ import annotations

import re
from typing import Any

from core.seat_execution_policy import normalize_error
from core.seat_personas import SEAT_PERSONAS
from core.three_round_protocol import INFORMATION_LANES, SEAT_INFORMATION_PROFILES


HIGH_RISK_DOMAINS = ["finance", "medical", "legal"]
HIGH_RISK_GATE_SCHEMA = "ai_judge.high_risk_domain_gate.v1"
BLOCKER_BRIEF_REPORT_TYPE = "high_risk_formal_verdict_blocker_brief"

DOMAIN_REPORT_NAMES = {
    "finance": "finance_ai_governance_report",
    "medical": "medical_ai_safety_report",
    "legal": "legal_ai_governance_report",
}

DOMAIN_REQUIRED_SLOTS = {
    "finance": [
        "deployment_verdict",
        "ria_sec_boundary",
        "fiduciary_duty",
        "advice_vs_education_boundary",
        "ai_washing_and_advertising",
        "trade_execution_gate",
        "human_approval_points",
        "audit_trail",
        "suitability_and_risk_profile",
        "privacy_security",
        "blocked_use_cases",
    ],
    "medical": [
        "deployment_verdict",
        "intended_use",
        "fda_samd_cds_classification",
        "clinical_validation",
        "human_clinician_responsibility",
        "shutdown_rollback",
        "bias_monitoring",
        "ehr_phi_hipaa",
        "incident_response",
        "blocked_use_cases",
    ],
    "legal": [
        "deployment_verdict",
        "privilege_confidentiality",
        "upl_and_attorney_supervision",
        "citation_lock",
        "court_candor",
        "client_consent",
        "access_control",
        "cross_jurisdiction_rules",
        "audit_log",
        "blocked_use_cases",
    ],
}

DOMAIN_PENDING_DOSSIER_SLOTS = {
    "finance": [
        "ria_sec_boundary",
        "fiduciary_duty",
        "advice_vs_education_boundary",
        "ai_washing_and_advertising",
        "trade_execution_gate",
        "human_approval_points",
        "audit_trail",
        "suitability_and_risk_profile",
        "privacy_security",
        "blocked_use_cases",
    ],
    "medical": [
        "intended_use",
        "fda_samd_cds_classification",
        "clinical_validation",
        "human_clinician_responsibility",
        "shutdown_rollback",
        "bias_monitoring",
        "ehr_phi_hipaa",
        "incident_response",
        "blocked_use_cases",
    ],
    "legal": [
        "privilege_confidentiality",
        "upl_and_attorney_supervision",
        "citation_lock",
        "court_candor",
        "client_consent",
        "access_control",
        "cross_jurisdiction_rules",
        "audit_log",
        "blocked_use_cases",
    ],
}

DOMAIN_SLOT_IMPACT_BY_LANE = {
    "finance": {
        "real_time_web": ["ria_sec_boundary", "ai_washing_and_advertising", "privacy_security"],
        "chinese_context": ["ria_sec_boundary", "advice_vs_education_boundary", "ai_washing_and_advertising"],
        "long_context": ["audit_trail", "suitability_and_risk_profile", "privacy_security"],
        "deep_reasoning": ["fiduciary_duty", "advice_vs_education_boundary", "trade_execution_gate"],
        "dissent": ["blocked_use_cases", "ai_washing_and_advertising", "fiduciary_duty"],
        "execution": ["trade_execution_gate", "human_approval_points", "audit_trail"],
        "product_experience": ["advice_vs_education_boundary", "suitability_and_risk_profile", "privacy_security"],
    },
    "medical": {
        "real_time_web": ["fda_samd_cds_classification", "intended_use", "incident_response"],
        "chinese_context": ["ehr_phi_hipaa", "bias_monitoring", "incident_response"],
        "long_context": ["clinical_validation", "ehr_phi_hipaa", "human_clinician_responsibility"],
        "deep_reasoning": ["intended_use", "fda_samd_cds_classification", "clinical_validation"],
        "dissent": ["blocked_use_cases", "shutdown_rollback", "bias_monitoring"],
        "execution": ["shutdown_rollback", "incident_response", "human_clinician_responsibility"],
        "product_experience": ["human_clinician_responsibility", "bias_monitoring", "ehr_phi_hipaa"],
    },
    "legal": {
        "real_time_web": ["citation_lock", "court_candor", "cross_jurisdiction_rules"],
        "chinese_context": ["cross_jurisdiction_rules", "client_consent", "access_control"],
        "long_context": ["privilege_confidentiality", "audit_log", "access_control"],
        "deep_reasoning": ["upl_and_attorney_supervision", "court_candor", "citation_lock"],
        "dissent": ["blocked_use_cases", "court_candor", "privilege_confidentiality"],
        "execution": ["access_control", "audit_log", "client_consent"],
        "product_experience": ["client_consent", "citation_lock", "access_control"],
    },
}

_SEAT_NAME_TO_ID = {
    str(persona.get("name") or seat).strip().lower(): seat
    for seat, persona in SEAT_PERSONAS.items()
}


def infer_high_risk_domain(question: str) -> str:
    text = str(question or "").lower()
    if any(token in text for token in ("金融", "投顾", "ria", "sec", "finra", "fintech", "投资顾问", "fiduciary", "portfolio")):
        return "finance"
    if any(token in text for token in ("医疗", "医院", "临床", "医生", "fda", "samd", "cds", "ehr", "hipaa", "clinical")):
        return "medical"
    if any(token in text for token in ("法律", "律所", "律师", "法院", "诉讼", "aba", "privilege", "citation", "attorney", "legal")):
        return "legal"
    return ""


def required_slots_for_domain(domain: str) -> list[str]:
    return list(DOMAIN_REQUIRED_SLOTS.get(str(domain or "").lower(), []))


def validate_domain_required_slots(domain: str, report: dict[str, Any] | None) -> dict[str, Any]:
    domain = str(domain or "").lower()
    required = required_slots_for_domain(domain)
    report = report if isinstance(report, dict) else {}
    missing = [slot for slot in required if not _slot_present(report.get(slot))]
    return {
        "report_name": DOMAIN_REPORT_NAMES.get(domain, ""),
        "required_slots": required,
        "missing_slots": missing,
        "complete": bool(required) and not missing,
    }


def evaluate_high_risk_domain_gate(verdict: dict[str, Any], source: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the high-risk report gate decision.

    The function accepts either a raw verdict or the normalized output contract.
    When the run is high-risk and unverified or required evidence is missing,
    the formal domain verdict is blocked deterministically.
    """
    source = source if isinstance(source, dict) else verdict
    question = str(_first_value(verdict, source, key="question") or "")
    explicit_domain = str(_first_value(verdict, source, key="domain") or "").lower()
    domain = explicit_domain if explicit_domain in HIGH_RISK_DOMAINS else infer_high_risk_domain(question)
    high_risk = domain in HIGH_RISK_DOMAINS
    blocking_missing = _missing_required_items(verdict, source)
    quality_recovery = _round2_missing_items(verdict, source)
    all_missing = blocking_missing + quality_recovery
    run_unverified = str(_first_value(verdict, source, key="verdict") or "").lower() == "unverified"
    slots = validate_domain_required_slots(domain, _domain_report(verdict, source, domain))
    required_seats_missing = len(blocking_missing)

    blocked_by_required_seats = high_risk and required_seats_missing > 0
    blocked_by_unverified = high_risk and run_unverified
    blocked_by_slots = high_risk and not slots.get("complete")
    blocked = blocked_by_required_seats or blocked_by_unverified or blocked_by_slots
    impact_matrix = _missing_seat_impact_matrix(domain, blocking_missing, quality_recovery)
    round1_completion = _round1_completion(verdict, source, blocking_missing)
    round2_completion = _round2_completion(verdict, source, quality_recovery)
    execution_status = _execution_status(blocked, required_seats_missing, run_unverified)

    if not high_risk:
        report_type = str(_first_value(verdict, source, key="report_type") or "standard_report")
        domain_verdict = str(_first_value(verdict, source, key="domain_verdict") or "")
        publish_gate = "PASS"
        confidence_label = "STANDARD_REPORT"
    elif blocked:
        report_type = BLOCKER_BRIEF_REPORT_TYPE
        domain_verdict = "NOT_ISSUED"
        publish_gate = "BLOCKED_REQUIRED_SEATS" if blocked_by_required_seats or blocked_by_unverified else "BLOCKED_REQUIRED_SLOTS"
        confidence_label = "INSUFFICIENT_FOR_FORMAL_VERDICT"
    else:
        report_type = DOMAIN_REPORT_NAMES.get(domain, "high_risk_domain_report")
        domain_verdict = str(_first_value(verdict, source, key="domain_verdict") or "READY_FOR_FORMAL_REPORT")
        publish_gate = "PASS"
        confidence_label = "SUFFICIENT_FOR_FORMAL_VERDICT"

    reasons = []
    if blocked_by_required_seats:
        reasons.append("必需席位缺失或回收不足。")
    if blocked_by_unverified:
        reasons.append("运行状态为 unverified，不能签发高风险领域正式裁决。")
    if blocked_by_slots:
        reasons.append("领域专用 required slots 尚未完整生成。")

    return {
        "schema": HIGH_RISK_GATE_SCHEMA,
        "domain": domain,
        "high_risk_domain": high_risk,
        "report_type": report_type,
        "domain_verdict": domain_verdict,
        "publish_gate": publish_gate,
        "execution_status": execution_status,
        "formal_report_status": publish_gate,
        "formal_verdict": domain_verdict,
        "evidence_status": confidence_label,
        "formal_report_allowed": high_risk and not blocked,
        "blocked": bool(blocked),
        "blocked_reasons": reasons,
        "evidence_confidence": {"label": confidence_label},
        "required_seats_missing": required_seats_missing,
        "missing_required_seats": all_missing,
        "blocking_missing_seats": blocking_missing,
        "quality_recovery_seats": quality_recovery,
        "missing_seat_impact_matrix": impact_matrix,
        "round_1": round1_completion,
        "round_2": round2_completion,
        "round1_completion": round1_completion,
        "round2_completion": round2_completion,
        "required_slots": slots,
    }


def should_apply_high_risk_blocker(
    verdict: dict[str, Any],
    gate: dict[str, Any],
    *,
    source: dict[str, Any] | None = None,
) -> bool:
    """Return whether the high-risk blocker should replace a normal report.

    Legal case-analysis prompts often contain "法院" or "诉讼", so they are
    legal-domain prompts but not legal-AI deployment/governance reports. The
    blocker is reserved for high-risk AI system governance reports.
    """
    if not isinstance(gate, dict) or not gate.get("blocked") or not gate.get("high_risk_domain"):
        return False
    domain = str(gate.get("domain") or _first_value(verdict, source or {}, key="domain") or "").lower()
    if domain != "legal":
        return True

    text_parts: list[str] = []
    for container in (verdict, source):
        if not isinstance(container, dict):
            continue
        for key in ("question", "deep_prompt", "original_question", "report_type", "domain_verdict"):
            value = container.get(key)
            if isinstance(value, str):
                text_parts.append(value)
    text = " ".join(text_parts).lower()
    governance_markers = (
        "legal_ai_governance_report",
        "ai governance",
        "ai治理",
        "ai 治理",
        "法律ai",
        "法律 ai",
        "上线审查",
        "部署审查",
        "合规审查",
        "合规评估",
        "deployment_verdict",
        "privilege_confidentiality",
        "upl_and_attorney_supervision",
        "citation_lock",
        "court_candor",
        "client_consent",
        "access_control",
        "cross_jurisdiction_rules",
        "blocked_use_cases",
    )
    return any(marker in text for marker in governance_markers)


def attach_high_risk_domain_gate(verdict: dict[str, Any], source: dict[str, Any] | None = None) -> dict[str, Any]:
    gate = evaluate_high_risk_domain_gate(verdict, source=source)
    verdict["high_risk_gate"] = gate
    blocker_applies = should_apply_high_risk_blocker(verdict, gate, source=source)
    if not gate.get("blocked") or blocker_applies:
        verdict["report_type"] = gate["report_type"]
        verdict["domain_verdict"] = gate["domain_verdict"]
        verdict["publish_gate"] = gate["publish_gate"]
        verdict["evidence_confidence"] = gate["evidence_confidence"]
    elif gate.get("high_risk_domain"):
        if str(verdict.get("report_type") or "") == BLOCKER_BRIEF_REPORT_TYPE:
            verdict["report_type"] = "standard_report"
        if str(verdict.get("domain_verdict") or "") == "NOT_ISSUED":
            verdict.pop("domain_verdict", None)
        if str(verdict.get("publish_gate") or "").startswith("BLOCKED"):
            verdict["publish_gate"] = "READY_TO_PUBLISH"
        confidence = verdict.get("evidence_confidence") if isinstance(verdict.get("evidence_confidence"), dict) else {}
        if str(confidence.get("label") or "").startswith("INSUFFICIENT_"):
            verdict["evidence_confidence"] = {"label": "STANDARD_REPORT"}
        if str(verdict.get("verdict_label") or "") == "正式裁决未签发":
            verdict.pop("verdict_label", None)
        if str(verdict.get("one_liner") or "").startswith("高风险领域必需席位缺失"):
            verdict.pop("one_liner", None)
        if str(verdict.get("business_verdict") or "") == "INSUFFICIENT_EVIDENCE":
            verdict.pop("business_verdict", None)
        blocked_steps = [
            "补跑缺失席位并重建 evidence matrix。",
            "只补 recovery queue 中的缺失席位，不重新跑完整战略 run。",
            "缺失席位回填、证据重合并、领域 required slots 全部完成后，才允许重新生成正式领域报告。",
        ]
        if verdict.get("next_steps") == blocked_steps:
            verdict.pop("next_steps", None)
        actions = verdict.get("actions")
        if isinstance(actions, list) and any("required slots" in str(item) or "无需补跑席位" in str(item) for item in actions):
            verdict.pop("actions", None)
        risks = verdict.get("risks")
        if isinstance(risks, list) and any("UPL" in str(item) or "privilege" in str(item) for item in risks):
            verdict.pop("risks", None)
    if blocker_applies:
        verdict["verdict_label"] = "正式裁决未签发"
        verdict["one_liner"] = "高风险领域必需席位缺失或证据回收不足；当前只能生成正式裁决阻断诊断单。"
        verdict["next_steps"] = [
            "补跑缺失席位并重建 evidence matrix。",
            "只补 recovery queue 中的缺失席位，不重新跑完整战略 run。",
            "缺失席位回填、证据重合并、领域 required slots 全部完成后，才允许重新生成正式领域报告。",
        ]
    return verdict


def _domain_report(verdict: dict[str, Any], source: dict[str, Any], domain: str) -> dict[str, Any]:
    name = DOMAIN_REPORT_NAMES.get(domain, "")
    for container in (verdict, source):
        if not isinstance(container, dict):
            continue
        report = container.get("domain_report")
        if isinstance(report, dict):
            nested = report.get(name)
            if isinstance(nested, dict):
                return nested
            return report
        nested = container.get(name)
        if isinstance(nested, dict):
            return nested
    return {}


def _first_value(verdict: dict[str, Any], source: dict[str, Any], *, key: str) -> Any:
    for container in (verdict, source):
        if isinstance(container, dict) and container.get(key) not in (None, ""):
            return container.get(key)
    return None


def _slot_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _missing_required_items(verdict: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    policy = _execution_policy(verdict, source)
    failures = policy.get("required_failures") if isinstance(policy, dict) else None
    rows: list[dict[str, Any]] = []
    if isinstance(failures, list) and failures:
        for failure in failures:
            if not isinstance(failure, dict):
                continue
            rows.append(_missing_item_from_failure(failure, round_id="R1"))
        return rows

    for reason in _reason_rows(verdict, source):
        parsed = _missing_item_from_reason(reason)
        if parsed:
            rows.append(parsed)
    return rows


def _round2_missing_items(verdict: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    scheduler = _round2_scheduler(verdict, source)
    rows: list[dict[str, Any]] = []
    for item in scheduler.get("priority_order") or []:
        if not isinstance(item, dict):
            continue
        if not item.get("scheduled") or item.get("completed"):
            continue
        seat_id = _normalize_seat_id(item.get("seat") or item.get("seat_name"))
        rows.append({
            "seat_id": seat_id,
            "seat_name": str(item.get("seat_name") or SEAT_PERSONAS.get(seat_id, {}).get("name") or seat_id),
            "required": bool(item.get("hard_required")),
            "round": "R2",
            "failure_reason": str(item.get("status") or item.get("deferred_reason") or "timeout"),
            "message": "二轮优先追问未完成。",
        })
    return rows


def _missing_item_from_failure(failure: dict[str, Any], *, round_id: str) -> dict[str, Any]:
    error = normalize_error(failure.get("error"), fallback_code=str(failure.get("reason") or "missing"))
    seat_id = _normalize_seat_id(failure.get("seat") or failure.get("seat_name"))
    return {
        "seat_id": seat_id,
        "seat_name": str(failure.get("seat_name") or SEAT_PERSONAS.get(seat_id, {}).get("name") or seat_id),
        "required": True,
        "round": round_id,
        "failure_reason": _failure_reason(error.get("code") or failure.get("reason")),
        "message": str(error.get("message") or failure.get("reason") or "Required seat did not produce a valid answer."),
    }


def _missing_item_from_reason(reason: str) -> dict[str, Any] | None:
    text = str(reason or "")
    if not text:
        return None
    match = re.match(r"([^:：]+)[:：].*?(web_collection_process_timeout|seat_timeout|timeout|parse_failed|submit_failed|send_button_not_found|transcript_pollution)", text)
    if not match:
        return None
    seat_id = _normalize_seat_id(match.group(1))
    return {
        "seat_id": seat_id,
        "seat_name": SEAT_PERSONAS.get(seat_id, {}).get("name", match.group(1).strip()),
        "required": True,
        "round": "R1",
        "failure_reason": _failure_reason(match.group(2)),
        "message": text,
    }


def _failure_reason(code: Any) -> str:
    text = str(code or "").lower()
    if "process_timeout" in text or "web_collection_process_timeout" in text:
        return "process_timeout"
    if "timeout" in text:
        return "timeout"
    if "parse" in text:
        return "parse_failed"
    if "submit" in text or "send_button" in text or "input" in text:
        return "submit_failed"
    return text or "timeout"


def _normalize_seat_id(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return _SEAT_NAME_TO_ID.get(raw, raw)


def _execution_policy(verdict: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    for container in (source, verdict):
        bridge = container.get("web_bridge") if isinstance(container, dict) else {}
        if isinstance(bridge, dict) and isinstance(bridge.get("execution_policy"), dict):
            return bridge["execution_policy"]
    return {}


def _round2_scheduler(verdict: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    for container in (source, verdict):
        if not isinstance(container, dict):
            continue
        bridge = container.get("web_bridge") if isinstance(container.get("web_bridge"), dict) else {}
        if isinstance(bridge.get("round2_scheduler"), dict):
            return bridge["round2_scheduler"]
        audit = container.get("audit") if isinstance(container.get("audit"), dict) else {}
        if isinstance(audit.get("round2_scheduler"), dict):
            return audit["round2_scheduler"]
    return {}


def _missing_seat_impact_matrix(
    domain: str,
    blocking_missing: list[dict[str, Any]],
    quality_recovery: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in blocking_missing:
        rows.append(_impact_row(domain, item, blocking_level="P0_BLOCKING"))
    for item in quality_recovery:
        rows.append(_impact_row(domain, item, blocking_level="P1_QUALITY_RECOVERY"))
    return rows


def _impact_row(domain: str, item: dict[str, Any], *, blocking_level: str) -> dict[str, Any]:
    seat_id = _normalize_seat_id(item.get("seat_id") or item.get("seat_name"))
    round_id = "R2" if str(item.get("round") or "").upper() == "R2" else "R1"
    return {
        "seat_id": seat_id,
        "seat_name": str(item.get("seat_name") or SEAT_PERSONAS.get(seat_id, {}).get("name") or seat_id),
        "round": round_id,
        "blocking_level": blocking_level,
        "information_mandate": _seat_information_mandate(seat_id),
        "blocked_domain_slots": _blocked_domain_slots(domain, seat_id),
        "why_it_matters": _why_missing_seat_matters(domain, seat_id, round_id, blocking_level),
        "retry_action": _retry_action_for_round(round_id, item.get("failure_reason")),
        "recovery_status": "queued",
    }


def _seat_information_mandate(seat_id: str) -> str:
    lanes = SEAT_INFORMATION_PROFILES.get(seat_id) or []
    labels = [INFORMATION_LANES.get(lane, {}).get("label", lane) for lane in lanes]
    return " / ".join(label for label in labels if label) or "通用模型判断"


def _blocked_domain_slots(domain: str, seat_id: str) -> list[str]:
    domain = str(domain or "").lower()
    lanes = SEAT_INFORMATION_PROFILES.get(seat_id) or []
    rows: list[str] = []
    impact = DOMAIN_SLOT_IMPACT_BY_LANE.get(domain) or {}
    for lane in lanes:
        rows.extend(impact.get(lane) or [])
    if not rows:
        rows = DOMAIN_PENDING_DOSSIER_SLOTS.get(domain, [])[:3]
    return list(dict.fromkeys(rows))


def _why_missing_seat_matters(domain: str, seat_id: str, round_id: str, blocking_level: str) -> str:
    slots = _blocked_domain_slots(domain, seat_id)
    slot_text = "、".join(slots[:3]) if slots else "领域关键断言"
    if blocking_level == "P0_BLOCKING":
        return f"{round_id} 必需席位未回收，导致 {slot_text} 缺少可交叉验证的结构化证据。"
    return f"{round_id} 优先追问未完成，主要削弱 {slot_text} 的二轮共振校正和信息反哺质量。"


def _retry_action_for_round(round_id: str, reason: Any) -> str:
    failure = _failure_reason(reason)
    if round_id == "R2":
        return f"补跑该席位二轮追问，保留原始首轮结论并追加修订意见；失败原因：{failure}。"
    return f"补跑该席位首轮结构化回答，成功后 attach 回原 run 并重建 evidence matrix；失败原因：{failure}。"


def _execution_status(blocked: bool, required_seats_missing: int, run_unverified: bool) -> str:
    if blocked and required_seats_missing > 0:
        return "COMPLETED_WITH_MISSING_REQUIRED_SEATS"
    if blocked and run_unverified:
        return "COMPLETED_UNVERIFIED"
    if blocked:
        return "COMPLETED_WITH_REQUIRED_SLOT_GAPS"
    return "COMPLETED"


def _round1_completion(
    verdict: dict[str, Any],
    source: dict[str, Any],
    blocking_missing: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    bridge = source.get("web_bridge") if isinstance(source.get("web_bridge"), dict) else {}
    evidence = verdict.get("evidence") if isinstance(verdict.get("evidence"), dict) else {}
    requested = _int(bridge.get("requested_count"), _int(evidence.get("requested_count")))
    ok = _int(bridge.get("ok_count"), _int(evidence.get("ok_count")))
    failed = _int(bridge.get("failed_count"), _int(evidence.get("failed_count"), max(0, requested - ok)))
    policy = _execution_policy(verdict, source)
    missing_count = len(blocking_missing or [])
    policy_required_count = _int(policy.get("required_count"))
    policy_required_valid = _int(policy.get("required_valid_count"))
    if missing_count and (not policy_required_count or policy_required_count < missing_count):
        required_expected = missing_count
        required_completed = 0
    else:
        required_expected = policy_required_count
        required_completed = policy_required_valid
    return {
        "total_expected": requested,
        "total_completed": ok,
        "required_expected": required_expected,
        "required_completed": required_completed,
        "required_missing": max(0, required_expected - required_completed) if policy_required_count else missing_count,
        "ok_count": ok,
        "requested_count": requested,
        "failed_count": failed,
        "required_valid_count": required_completed,
        "required_count": required_expected,
        "collection_complete": bool(policy.get("collection_complete") if policy else evidence.get("collection_complete")),
    }


def _round2_completion(
    verdict: dict[str, Any],
    source: dict[str, Any],
    quality_recovery: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scheduler = _round2_scheduler(verdict, source)
    return {
        "total_expected": _int(scheduler.get("scheduled_count")),
        "total_completed": _int(scheduler.get("completed_count")),
        "quality_recovery_missing": len(quality_recovery or []),
        "scheduled_count": _int(scheduler.get("scheduled_count")),
        "completed_count": _int(scheduler.get("completed_count")),
        "deferred_count": _int(scheduler.get("deferred_count")),
        "failed_count": _int(scheduler.get("failed_count")),
    }


def _reason_rows(verdict: dict[str, Any], source: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for container in (verdict, source):
        if isinstance(container, dict) and isinstance(container.get("reasons"), list):
            rows.extend(str(item) for item in container["reasons"] if item)
    return list(dict.fromkeys(rows))


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default
