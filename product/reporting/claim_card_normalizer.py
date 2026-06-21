#!/usr/bin/env python3
"""Normalize usable high-risk claims into readable claim cards."""

from __future__ import annotations

import re
from typing import Any


DOMAIN_SLOT_PROFILES: dict[str, list[dict[str, Any]]] = {
    "finance": [
        {"slot": "ria_sec_boundary", "label": "投顾监管边界", "keywords": ["ria", "sec", "注册投资顾问", "投资顾问", "投顾监管"]},
        {"slot": "fiduciary_duty", "label": "受托责任", "keywords": ["fiduciary", "受托", "信义义务", "信托责任"]},
        {"slot": "advice_vs_education_boundary", "label": "投资建议与教育信息边界", "keywords": ["advice", "education", "投资建议", "教育信息", "个性化建议"]},
        {"slot": "ai_washing_and_advertising", "label": "广告披露与 AI-washing", "keywords": ["ai-washing", "ai washing", "广告", "宣传", "披露"]},
        {"slot": "trade_execution_gate", "label": "交易执行门禁", "keywords": ["trade execution", "交易执行", "自动交易", "交易草案", "下单"]},
        {"slot": "human_approval_points", "label": "人工审批", "keywords": ["human approval", "人工审批", "人工确认", "人类审批", "human-in-the-loop"]},
        {"slot": "audit_trail", "label": "审计留痕", "keywords": ["audit trail", "审计", "留痕", "日志", "可追溯"]},
        {"slot": "suitability_and_risk_profile", "label": "客户适当性与风险画像", "keywords": ["suitability", "适当性", "风险画像", "risk profile"]},
        {"slot": "privacy_security", "label": "隐私与安全控制", "keywords": ["privacy", "security", "隐私", "安全", "数据保护", "银行流水"]},
        {"slot": "blocked_use_cases", "label": "禁止用例", "keywords": ["blocked", "禁止", "不得", "冻结", "no-go"]},
    ],
    "medical": [
        {"slot": "intended_use", "label": "预期用途边界", "keywords": ["intended use", "预期用途", "用途边界", "适用场景"]},
        {"slot": "fda_samd_cds_classification", "label": "FDA/SaMD/CDS 分类", "keywords": ["fda", "samd", "cds", "医疗器械"]},
        {"slot": "clinical_validation", "label": "临床验证", "keywords": ["clinical validation", "临床验证", "验证", "shadow mode", "影子模式"]},
        {"slot": "human_clinician_responsibility", "label": "医生责任边界", "keywords": ["clinician", "医生", "医师", "人工最终", "责任边界"]},
        {"slot": "shutdown_rollback", "label": "停机回滚", "keywords": ["shutdown", "rollback", "停机", "回滚", "安全退出"]},
        {"slot": "bias_monitoring", "label": "偏倚监控", "keywords": ["bias", "偏倚", "公平", "bias monitoring"]},
        {"slot": "ehr_phi_hipaa", "label": "EHR/PHI/HIPAA 数据控制", "keywords": ["ehr", "phi", "hipaa", "病历", "健康信息"]},
        {"slot": "incident_response", "label": "事件响应", "keywords": ["incident", "不良事件", "事件响应", "应急", "复盘"]},
        {"slot": "blocked_use_cases", "label": "禁止用例", "keywords": ["blocked", "禁止", "不得", "冻结", "no-go"]},
    ],
    "legal": [
        {"slot": "privilege_confidentiality", "label": "保密与特权通信", "keywords": ["privilege", "confidentiality", "保密", "特权", "客户保密"]},
        {"slot": "upl_and_attorney_supervision", "label": "UPL 与律师监督", "keywords": ["upl", "unauthorized practice", "attorney supervision", "律师监督", "非法执业"]},
        {"slot": "citation_lock", "label": "引用核验锁", "keywords": ["citation", "引用", "判例", "核验锁", "citation lock"]},
        {"slot": "court_candor", "label": "对法院诚信义务", "keywords": ["court candor", "candor", "法院", "诚信义务"]},
        {"slot": "client_consent", "label": "客户同意", "keywords": ["client consent", "客户同意", "告知", "consent"]},
        {"slot": "access_control", "label": "访问控制", "keywords": ["access control", "访问控制", "权限", "隔离"]},
        {"slot": "cross_jurisdiction_rules", "label": "跨管辖区规则", "keywords": ["jurisdiction", "跨州", "管辖区", "multi-jurisdiction"]},
        {"slot": "audit_log", "label": "审计日志", "keywords": ["audit", "审计", "日志", "责任追踪"]},
        {"slot": "blocked_use_cases", "label": "禁止用例", "keywords": ["blocked", "禁止", "不得", "冻结", "no-go"]},
    ],
}

DOMAIN_PREFIX = {"finance": "F", "medical": "M", "legal": "L"}


def slot_profiles_for_domain(domain: str) -> list[dict[str, Any]]:
    return list(DOMAIN_SLOT_PROFILES.get(str(domain or "").lower(), []))


def matched_slots_for_text(domain: str, text: str) -> list[str]:
    lower = str(text or "").lower()
    slots = []
    for profile in slot_profiles_for_domain(domain):
        if any(str(keyword).lower() in lower for keyword in profile.get("keywords") or []):
            slots.append(str(profile["slot"]))
    return list(dict.fromkeys(slots))


def label_for_slot(domain: str, slot: str) -> str:
    for profile in slot_profiles_for_domain(domain):
        if profile.get("slot") == slot:
            return str(profile.get("label") or slot)
    return slot


def normalize_claim_cards(
    *,
    domain: str,
    usable_claims: list[dict[str, Any]],
    missing_required_seats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    domain = str(domain or "").lower()
    cards: list[dict[str, Any]] = []
    for index, claim in enumerate(usable_claims, start=1):
        text = _plain_language(str(claim.get("claim") or ""))
        slots = claim.get("matched_slots") if isinstance(claim.get("matched_slots"), list) else matched_slots_for_text(domain, text)
        stance = classify_stance(text)
        card_id = f"{DOMAIN_PREFIX.get(domain, 'C')}-{index:03d}"
        blocked = _blocked_by_missing(domain, slots, missing_required_seats)
        cards.append({
            "claim_id": card_id,
            "source_claim_id": str(claim.get("claim_id") or ""),
            "plain_language_claim": text,
            "why_it_matters": _why_it_matters(domain, slots),
            "supporting_seats": [str(claim.get("seat") or "")] if claim.get("seat") else [],
            "evidence_status": _evidence_status(text),
            "decision_impact": _decision_impact(slots),
            "blocked_by_missing_seats": blocked,
            "status": "PRELIMINARY_ONLY",
            "stance": stance,
            "matched_slots": list(dict.fromkeys(str(slot) for slot in slots if slot)),
        })
    return cards


def classify_stance(text: str) -> str:
    lower = str(text or "").lower()
    if any(token in lower for token in ["no-go", "不可上线", "不得上线", "不应上线", "禁止上线", "拒绝上线", "不能部署", "暂停上线"]):
        return "NO_GO"
    conditional_tokens = [
        "conditional-go",
        "conditional go",
        "条件支持",
        "附条件",
        "有限上线",
        "分阶段",
        "灰度",
        "可以上线，但",
        "可上线，但",
        "可以部署，但",
        "可部署，但",
        "仅限",
        "必须先",
        "必须满足",
    ]
    if any(token in lower for token in conditional_tokens):
        return "CONDITIONAL_GO"
    if any(token in lower for token in ["可以上线", "可上线", "可以部署", "可部署", "支持上线", "go"]):
        return "GO"
    return "UNKNOWN"


def stance_counts(cards: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"NO_GO": 0, "CONDITIONAL_GO": 0, "GO": 0, "UNKNOWN": 0}
    for card in cards:
        stance = str(card.get("stance") or "UNKNOWN")
        counts[stance if stance in counts else "UNKNOWN"] += 1
    return counts


def _plain_language(text: str) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    clean = re.sub(r"^[A-Za-z0-9_\-]+[:：]\s*", "", clean)
    clean = clean.replace("...", "").replace("…", "")
    return clean


def _why_it_matters(domain: str, slots: list[str]) -> str:
    labels = [label_for_slot(domain, slot) for slot in slots[:2]]
    if labels:
        return f"这会影响 {'、'.join(labels)} 是否能形成可复核判断。"
    return "这会影响该高风险系统是否具备可复核的治理边界。"


def _evidence_status(text: str) -> str:
    lower = str(text or "").lower()
    if any(token in lower for token in ["sec", "fda", "hipaa", "aba", "model rule", "来源", "可验证", "依据", "证据"]):
        return "UNVERIFIED"
    return "MISSING_SOURCE"


def _decision_impact(slots: list[str]) -> str:
    high = {
        "trade_execution_gate",
        "fda_samd_cds_classification",
        "clinical_validation",
        "privilege_confidentiality",
        "upl_and_attorney_supervision",
        "citation_lock",
    }
    if any(slot in high for slot in slots):
        return "HIGH"
    if slots:
        return "MEDIUM"
    return "LOW"


def _blocked_by_missing(domain: str, slots: list[str], missing_required_seats: list[dict[str, Any]]) -> list[str]:
    rows: list[str] = []
    for item in missing_required_seats or []:
        if not isinstance(item, dict):
            continue
        blocked_slots = item.get("blocked_domain_slots") or []
        if not slots or any(slot in blocked_slots for slot in slots):
            seat = str(item.get("seat_id") or "").lower()
            if seat:
                rows.append(seat)
    return list(dict.fromkeys(rows))
