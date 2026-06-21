#!/usr/bin/env python3
"""Recovery queue for blocked high-risk AI Judge reports."""

from __future__ import annotations

from typing import Any

from core.high_risk_domain_gate import evaluate_high_risk_domain_gate


RECOVERY_QUEUE_SCHEMA = "ai_judge.required_seat_recovery_queue.v1"
RECOVERY_STATE_MACHINE = [
    "REPORT_BLOCKED_REQUIRED_SEATS",
    "RECOVERY_QUEUE_CREATED",
    "MISSING_SEATS_RETRIED",
    "SEAT_RESULT_ATTACHED",
    "EVIDENCE_REMERGED",
    "DOMAIN_REPORT_REGENERATED",
]


def build_required_seat_recovery_queue(
    verdict: dict[str, Any],
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = gate if isinstance(gate, dict) else evaluate_high_risk_domain_gate(verdict)
    blocking_missing = gate.get("blocking_missing_seats") if isinstance(gate.get("blocking_missing_seats"), list) else []
    quality_recovery = gate.get("quality_recovery_seats") if isinstance(gate.get("quality_recovery_seats"), list) else []
    if not blocking_missing and not quality_recovery:
        legacy = gate.get("missing_required_seats") if isinstance(gate.get("missing_required_seats"), list) else []
        blocking_missing = [item for item in legacy if isinstance(item, dict) and str(item.get("round") or "").upper() != "R2"]
        quality_recovery = [item for item in legacy if isinstance(item, dict) and str(item.get("round") or "").upper() == "R2"]
    blocking_items = [_queue_item(item, required=True) for item in blocking_missing if isinstance(item, dict)]
    quality_items = [_queue_item(item, required=bool(item.get("required"))) for item in quality_recovery if isinstance(item, dict)]
    items = blocking_items + quality_items
    minimum_actions = _minimum_actions(blocking_items, quality_items)
    return {
        "schema": RECOVERY_QUEUE_SCHEMA,
        "state_machine": RECOVERY_STATE_MACHINE,
        "current_state": "RECOVERY_QUEUE_CREATED" if items else "DOMAIN_REPORT_REGENERATED",
        "source_state": "REPORT_BLOCKED_REQUIRED_SEATS" if gate.get("blocked") else "DOMAIN_REPORT_REGENERATED",
        "retry_scope": "missing_required_seats_only",
        "rerun_all_seats": False,
        "domain": gate.get("domain") or "",
        "run_id": str(verdict.get("run_id") or ""),
        "blocking_missing_seats": blocking_items,
        "quality_recovery_seats": quality_items,
        "items": items,
        "minimum_actions": minimum_actions,
        "regeneration_condition": _regeneration_condition(gate),
        "actions": [
            "先补跑 Blocking Missing Seats 中列出的 R1 必需缺失席位。",
            "Quality Recovery Seats 仅用于二轮质量补强；除非被配置为 hard_required，不作为正式裁决硬阻断。",
            "补跑成功后将 seat result attach 回原 run。",
            "重建 evidence matrix 后重新评估 high_risk_domain_gate。",
            "只有 publish_gate 解除且领域 required slots 完整，才生成正式领域报告。",
        ],
    }


def _queue_item(item: dict[str, Any], *, required: bool) -> dict[str, Any]:
    reason = _normalize_reason(item.get("failure_reason"))
    return {
        "seat_id": str(item.get("seat_id") or ""),
        "required": required,
        "round": "R2" if str(item.get("round") or "").upper() == "R2" else "R1",
        "failure_reason": reason,
        "retry_policy": _retry_policy(reason),
        "max_retry": 2,
        "recovery_status": "queued",
    }


def _normalize_reason(reason: Any) -> str:
    text = str(reason or "").lower()
    if "process_timeout" in text:
        return "process_timeout"
    if "timeout" in text or text in {"queued", "failed_or_skipped"}:
        return "timeout"
    if "parse" in text:
        return "parse_failed"
    if "submit" in text or "send" in text or "input" in text:
        return "submit_failed"
    return text or "timeout"


def _retry_policy(reason: str) -> str:
    if reason == "process_timeout":
        return "retry_missing_seat_in_fresh_process_with_partial_capture"
    if reason == "timeout":
        return "retry_missing_seat_with_short_prompt_and_answer_markers"
    if reason == "parse_failed":
        return "retry_missing_seat_with_strict_json_and_marker_parse"
    if reason == "submit_failed":
        return "repair_submission_selector_then_retry_missing_seat"
    return "retry_missing_seat_once_then_escalate_to_manual_recovery"


def _minimum_actions(blocking_items: list[dict[str, Any]], quality_items: list[dict[str, Any]]) -> list[str]:
    if blocking_items:
        seats = "、".join(item["seat_id"] for item in blocking_items[:4] if item.get("seat_id"))
        actions = [
            f"优先补跑 R1 必需席位：{seats}。",
            "补跑成功后只 attach 缺失 seat result，不重跑全部席位。",
            "重建 evidence matrix 并重新计算领域 required slots。",
        ]
        return actions[:3]
    if quality_items:
        seats = "、".join(item["seat_id"] for item in quality_items[:4] if item.get("seat_id"))
        return [
            f"补跑 R2 质量追问席位：{seats}。",
            "将二轮修订意见合并回信息板。",
            "重新生成正式领域报告前保留质量恢复审计记录。",
        ]
    return ["无需补跑席位；重新评估领域 required slots。"]


def _regeneration_condition(gate: dict[str, Any]) -> str:
    domain = str(gate.get("domain") or "high-risk")
    if gate.get("required_seats_missing"):
        return f"{domain} 的 R1 必需席位全部补齐、evidence matrix 重合并、required slots 全部 READY 后重新生成正式领域报告。"
    return f"{domain} 的领域 required slots 全部 READY 且 publish_gate=PASS 后重新生成正式领域报告。"
