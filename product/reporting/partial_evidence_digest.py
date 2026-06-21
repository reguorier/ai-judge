#!/usr/bin/env python3
"""Build partial evidence digests from quality-gated claim cards."""

from __future__ import annotations

from typing import Any

from product.reporting.claim_card_normalizer import (
    label_for_slot,
    normalize_claim_cards,
    slot_profiles_for_domain,
    stance_counts,
)
from product.reporting.returned_content_quality_gate import evaluate_returned_content_quality


DIGEST_SCHEMA = "ai_judge.partial_evidence_digest.v2"

DISCARD_REASON_LABELS = {
    "runtime_or_failure_record": "运行日志、失败记录或超时记录",
    "raw_template_or_truncation_residue": "原始内容含截断、摘要或模板残留",
    "review_or_summary_not_domain_claim": "内容是互评、答案摘要或席位主回答，不是可展示的领域 claim",
    "claim_too_long_for_report_body": "内容过长，无法作为正文 claim 展示",
    "not_complete_natural_language_sentence": "不是完整自然语言句子",
    "not_directly_related_to_domain_core_slots": "未直接命中该领域核心判断项",
    "missing_clear_judgment_object": "缺少明确判断对象",
    "missing_clear_judgment_direction": "缺少明确判断方向",
    "missing_evidence_or_verification_path": "缺少依据、假设或可核验路径",
}

PRELIMINARY_JUDGMENTS = {
    "finance": {
        "ria_sec_boundary": "已返回可用内容倾向认为：该系统可能触及投顾监管边界，必须先完成监管身份、披露和监督责任判断。",
        "fiduciary_duty": "已返回可用内容倾向认为：系统不能替代受托责任，投顾责任仍应由持牌主体和人工审批链承担。",
        "advice_vs_education_boundary": "已返回可用内容倾向认为：系统必须区分教育信息、投资建议和个性化行动指令。",
        "ai_washing_and_advertising": "已返回可用内容倾向认为：对外宣传不能声称 AI 消除风险或保证收益，需要单独审查 AI-washing。",
        "trade_execution_gate": "已返回可用内容倾向认为：系统最多生成交易草案，不应自动执行真实交易。",
        "human_approval_points": "已返回可用内容倾向认为：高风险建议必须经过人工审批或用户明确确认。",
        "audit_trail": "已返回可用内容倾向认为：系统需要完整审计留痕，才能追踪建议、审批和交易草案。",
        "suitability_and_risk_profile": "已返回可用内容倾向认为：客户适当性和风险画像必须先被验证，不能只依赖模型自述。",
        "privacy_security": "已返回可用内容倾向认为：账户、税务和银行流水属于敏感数据，需要最小化访问和安全控制。",
        "blocked_use_cases": "已返回可用内容倾向认为：自动交易、保证收益和无人工监督的个性化建议应进入禁止用例。",
    },
    "medical": {
        "intended_use": "已返回可用内容倾向认为：系统预期用途必须先锁定，不能把高风险临床分诊包装成普通办公辅助。",
        "fda_samd_cds_classification": "已返回可用内容倾向认为：急诊排序、检查建议和持续学习功能可能触发 FDA/SaMD/CDS 路径判断。",
        "clinical_validation": "已返回可用内容倾向认为：临床验证不足前，系统不应直接进入真实临床决策流程。",
        "human_clinician_responsibility": "已返回可用内容倾向认为：医生最终责任不能被模型输出替代。",
        "shutdown_rollback": "已返回可用内容倾向认为：系统必须具备停机、回滚和安全退出机制。",
        "bias_monitoring": "已返回可用内容倾向认为：偏倚监控必须进入部署前和部署后的持续审查。",
        "ehr_phi_hipaa": "已返回可用内容倾向认为：EHR、PHI 和 HIPAA 控制必须先被验证。",
        "incident_response": "已返回可用内容倾向认为：医疗事故响应和复盘机制必须在上线前明确。",
        "blocked_use_cases": "已返回可用内容倾向认为：高风险急诊自动排序、持续学习和未验证检查建议应进入禁止或冻结用例。",
    },
    "legal": {
        "privilege_confidentiality": "已返回可用内容倾向认为：特权通信和客户保密必须优先隔离，不能进入不受控模型链路。",
        "upl_and_attorney_supervision": "已返回可用内容倾向认为：系统不能替代律师判断，必须处在律师监督之下。",
        "citation_lock": "已返回可用内容倾向认为：引用必须被核验锁定，不能把模型生成的引用直接用于法院材料。",
        "court_candor": "已返回可用内容倾向认为：对法院诚信义务要求律师复核 AI 输出，不能提交未核验内容。",
        "client_consent": "已返回可用内容倾向认为：涉及客户材料和 AI 使用边界时，需要客户告知与同意机制。",
        "access_control": "已返回可用内容倾向认为：案卷、权限和跨案访问必须硬隔离。",
        "cross_jurisdiction_rules": "已返回可用内容倾向认为：跨州律所必须处理不同管辖区的执业规则差异。",
        "audit_log": "已返回可用内容倾向认为：系统需要审计日志来追踪谁使用了哪些客户材料和输出。",
        "blocked_use_cases": "已返回可用内容倾向认为：自动法律判断、自动法院提交和无律师审批的客户建议应进入禁止用例。",
    },
}


def build_partial_evidence_digest(
    *,
    domain: str,
    returned_seat_claims: list[Any],
    missing_required_seats: list[Any],
    domain_slots: list[str],
) -> dict[str, Any]:
    domain = str(domain or "").lower()
    missing_rows = [item for item in missing_required_seats or [] if isinstance(item, dict)]
    quality_gate = evaluate_returned_content_quality(
        domain=domain,
        raw_claims=returned_seat_claims,
        raw_seat_outputs=[],
        missing_required_seats=missing_rows,
    )
    cards = normalize_claim_cards(
        domain=domain,
        usable_claims=quality_gate.get("usable_claims") or [],
        missing_required_seats=missing_rows,
    )
    counts = stance_counts(cards)
    slot_findings = _slot_findings(domain, domain_slots, cards, missing_rows)
    status = _digest_status(cards, quality_gate)
    return {
        "schema": DIGEST_SCHEMA,
        "domain": domain,
        "digest_status": status,
        "claim_count": int(quality_gate.get("raw_claim_count") or 0),
        "domain_claim_count": int(quality_gate.get("domain_matched_claim_count") or 0),
        "usable_claim_count": len(cards),
        "discarded_claim_count": len(quality_gate.get("discarded_claims") or []),
        "content_quality_gate": quality_gate,
        "usable_claim_cards": cards,
        "stance_counts": counts,
        "readable_summary": _readable_summary(domain, status, cards, quality_gate),
        "early_consensus": _early_consensus(domain, cards),
        "key_disagreements": _key_disagreements(cards, counts),
        "domain_relevant_findings": slot_findings,
        "unsupported_or_irrelevant_content": _unsupported_or_irrelevant(quality_gate),
        "missing_evidence_blocks": _missing_blocks(domain, domain_slots, slot_findings, missing_rows),
    }


def _digest_status(cards: list[dict[str, Any]], quality_gate: dict[str, Any]) -> str:
    if len(cards) < 3:
        return "FAILED"
    if quality_gate.get("content_quality") == "USABLE" and len(cards) >= 6:
        return "READY"
    return "WEAK"


def _readable_summary(
    domain: str,
    status: str,
    cards: list[dict[str, Any]],
    quality_gate: dict[str, Any],
) -> list[str]:
    label = {"finance": "金融", "medical": "医疗", "legal": "法律"}.get(domain, "高风险")
    if status == "FAILED":
        return [
            "已返回内容无法形成可读摘要。",
            "原因：可用 claim 少于 3 条。",
            "原因：原始内容多为截断片段、互评、运行日志或无法核验文本。",
        ]
    slots = _covered_labels(domain, cards)
    return [
        f"已返回内容中有 {len(cards)} 条可读、可用但仅供复核的初步判断；正式{label}裁决仍未签发。",
        f"这些初步判断主要覆盖：{'、'.join(slots[:6]) if slots else '尚未形成稳定判断项'}。",
        f"内容质量为 {quality_gate.get('content_quality')}，仍需补齐阻断席位后重建证据表。",
    ]


def _early_consensus(domain: str, cards: list[dict[str, Any]]) -> list[str]:
    by_slot: dict[str, set[str]] = {}
    for card in cards:
        for slot in card.get("matched_slots") or []:
            by_slot.setdefault(str(slot), set()).update(str(seat) for seat in card.get("supporting_seats") or [] if seat)
    rows = [
        f"多个可用 claim 指向「{label_for_slot(domain, slot)}」；支持席位：{', '.join(sorted(seats))}。"
        for slot, seats in by_slot.items()
        if len(seats) >= 2
    ]
    return rows[:5] or ["可用 claim 尚未形成多席位共识，只能作为补跑后的待复核材料。"]


def _key_disagreements(cards: list[dict[str, Any]], counts: dict[str, int]) -> list[str]:
    if not cards:
        return ["没有足够可用 claim 统计部署立场分歧。"]
    return [
        "可用 claim 的单一立场统计："
        f"NO_GO {counts.get('NO_GO', 0)}，"
        f"CONDITIONAL_GO {counts.get('CONDITIONAL_GO', 0)}，"
        f"GO {counts.get('GO', 0)}，"
        f"UNKNOWN {counts.get('UNKNOWN', 0)}。"
    ]


def _slot_findings(
    domain: str,
    domain_slots: list[str],
    cards: list[dict[str, Any]],
    missing_required_seats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    slots = domain_slots or [str(profile.get("slot")) for profile in slot_profiles_for_domain(domain)]
    rows: list[dict[str, Any]] = []
    for slot in slots:
        matching = [card for card in cards if slot in (card.get("matched_slots") or [])]
        blocking_seats = _blocking_seats_for_slot(slot, missing_required_seats)
        if matching:
            rows.append({
                "slot": slot,
                "label": label_for_slot(domain, slot),
                "readable_preliminary_judgment": PRELIMINARY_JUDGMENTS.get(domain, {}).get(slot) or _fallback_judgment(domain, slot),
                "why_it_matters": _why_slot_matters(domain, slot),
                "missing_evidence": _missing_evidence(slot, blocking_seats),
                "blocking_seats": blocking_seats,
                "supporting_seats": _supporting_seats(matching),
                "supporting_claim_card_ids": [str(card.get("claim_id")) for card in matching[:5]],
                "status": "PRELIMINARY_ONLY",
            })
        else:
            rows.append({
                "slot": slot,
                "label": label_for_slot(domain, slot),
                "readable_preliminary_judgment": "未从质量门禁后的可用 claim 中形成可读初步判断。",
                "why_it_matters": _why_slot_matters(domain, slot),
                "missing_evidence": _missing_evidence(slot, blocking_seats) if blocking_seats else "缺少可用 claim card，需要重新抽取或补跑席位。",
                "blocking_seats": blocking_seats,
                "supporting_seats": [],
                "supporting_claim_card_ids": [],
                "status": "MISSING",
            })
    return rows


def _unsupported_or_irrelevant(quality_gate: dict[str, Any]) -> list[str]:
    reasons = quality_gate.get("discard_reasons") if isinstance(quality_gate.get("discard_reasons"), dict) else {}
    if not reasons:
        return ["没有被内容质量门禁丢弃的 claim。"]
    ordered = sorted(reasons.items(), key=lambda item: item[1], reverse=True)
    return [f"{DISCARD_REASON_LABELS.get(reason, reason)}：{count} 条 claim 被丢弃。" for reason, count in ordered[:6]]


def _missing_blocks(
    domain: str,
    domain_slots: list[str],
    slot_findings: list[dict[str, Any]],
    missing_required_seats: list[dict[str, Any]],
) -> list[str]:
    rows = []
    for finding in slot_findings:
        if finding.get("status") == "MISSING":
            rows.append(f"{finding.get('label')} 缺少可用 claim card，不能签发该判断项。")
        elif finding.get("blocking_seats"):
            rows.append(f"{finding.get('label')} 只有初步判断，仍缺少 {', '.join(finding.get('blocking_seats') or [])} 的交叉验证。")
    return rows[:8]


def _covered_labels(domain: str, cards: list[dict[str, Any]]) -> list[str]:
    labels = []
    for card in cards:
        for slot in card.get("matched_slots") or []:
            labels.append(label_for_slot(domain, str(slot)))
    return list(dict.fromkeys(labels))


def _blocking_seats_for_slot(slot: str, missing_required_seats: list[dict[str, Any]]) -> list[str]:
    seats: list[str] = []
    for item in missing_required_seats or []:
        blocked_slots = item.get("blocked_domain_slots") if isinstance(item, dict) else []
        if slot in (blocked_slots or []) or not blocked_slots:
            seat = str(item.get("seat_id") or "").lower()
            if seat:
                seats.append(seat)
    return list(dict.fromkeys(seats))


def _supporting_seats(cards: list[dict[str, Any]]) -> list[str]:
    rows: list[str] = []
    for card in cards:
        rows.extend(str(seat) for seat in card.get("supporting_seats") or [] if seat)
    return list(dict.fromkeys(rows))


def _fallback_judgment(domain: str, slot: str) -> str:
    return f"已返回可用内容对「{label_for_slot(domain, slot)}」形成初步判断，但该判断仍不能替代正式裁决。"


def _why_slot_matters(domain: str, slot: str) -> str:
    return f"这决定「{label_for_slot(domain, slot)}」是否具备可复核、可追责的治理边界。"


def _missing_evidence(slot: str, blocking_seats: list[str]) -> str:
    if blocking_seats:
        return f"缺少 {', '.join(blocking_seats)} 的交叉验证。"
    return "缺少可核验来源、假设边界或阻断席位回填。"
