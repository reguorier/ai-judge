#!/usr/bin/env python3
"""Evidence gap suggestion layer for Grand Judge Phase 2.

This module never rewrites the user's answer. It only identifies missing proof
and returns mentor-level feedback that can be reviewed or sent back to seats.
"""

from __future__ import annotations

from typing import Any


MENTOR_LEVELS = {
    "L1": "明确引用缺口：需要 URL、DOI、报告页码、数据表或可复核出处。",
    "L2": "间接来源缺口：需要把“某报告/研究表明”升级成具体来源。",
    "L3": "无引用缺口：该段目前只能作为模型推理，不能作为事实认证依据。",
}


def suggest_evidence_gaps(
    citation_report: dict[str, Any] | str,
    *,
    mentor_level: str | None = None,
    max_suggestions: int = 12,
) -> dict[str, Any]:
    """Return evidence gap suggestions without filling or rewriting正文."""
    if isinstance(citation_report, str):
        items = [{
            "citation_id": "TEXT-001",
            "raw": "整段回答",
            "kind": "text",
            "status": "unverifiable",
            "reason": "仅提供正文，未提供 citation_validator 报告。",
        }]
    else:
        items = _flatten_items(citation_report)

    suggestions: list[dict[str, Any]] = []
    for item in items:
        status = str(item.get("status") or "")
        if status not in {"unverifiable", "weakly_verified", "irrelevant", "contradicted"}:
            continue
        level = mentor_level or _derive_level(item)
        suggestions.append({
            "citation_id": item.get("citation_id"),
            "raw": item.get("raw"),
            "status": status,
            "mentor_level": level,
            "mentor_feedback": MENTOR_LEVELS.get(level, MENTOR_LEVELS["L3"]),
            "gap": _gap_text(status),
            "suggested_action": _suggested_action(status),
            "will_rewrite_body": False,
            "action": "suggest_evidence_gap",
        })
        if len(suggestions) >= max_suggestions:
            break

    return {
        "schema": "evidence_gap_filler.suggestion_only.v1",
        "will_rewrite_body": False,
        "policy": "只输出证据缺口建议；不得替用户补正文或把模型补充混入原文。",
        "mentor_levels": MENTOR_LEVELS,
        "suggestions": suggestions,
        "suggestion_count": len(suggestions),
    }


def _flatten_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    if report.get("items"):
        return list(report.get("items") or [])
    items: list[dict[str, Any]] = []
    for entry in report.get("replay_ledger") or []:
        raw_report = entry.get("citation_verification") or {}
        items.extend(raw_report.get("items") or [])
        mentor_report = entry.get("mentor_citation_verification") or {}
        items.extend(mentor_report.get("items") or [])
    return items


def _derive_level(item: dict[str, Any]) -> str:
    kind = str(item.get("kind") or "")
    if kind in {"url", "doi", "arxiv", "paper"}:
        return "L1"
    if kind == "implied":
        return "L2"
    return "L3"


def _gap_text(status: str) -> str:
    return {
        "unverifiable": "缺少可匹配的外部证据。",
        "weakly_verified": "已有弱匹配，但来源精度或上下文相关性不足。",
        "irrelevant": "来源可找到，但与当前论点关系弱。",
        "contradicted": "已有外部证据显示冲突，需要人工裁决或改写主张。",
    }.get(status, "需要补充证据。")


def _suggested_action(status: str) -> str:
    return {
        "unverifiable": "补充可复核 URL/DOI/报告页码，或标记为不可认证。",
        "weakly_verified": "补充更精确出处，并说明该来源支持哪一句断言。",
        "irrelevant": "替换为直接支持当前断言的来源。",
        "contradicted": "保留冲突记录，重新核查断言是否应降级或撤回。",
    }.get(status, "补充外部证据后重跑 citation_validator。")
