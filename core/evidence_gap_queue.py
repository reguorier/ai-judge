#!/usr/bin/env python3
"""Evidence gap task queue for unverifiable citations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def build_evidence_gap_queue(grand_report: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    created_at = generated_at or datetime.now(timezone.utc).isoformat()
    suggestions = (grand_report.get("evidence_gap_suggestions") or {}).get("suggestions") or []
    tasks = []
    for index, item in enumerate(suggestions, 1):
        status = str(item.get("status") or "unverifiable")
        task = {
            "task_id": f"GAP-{index:03d}-{_hash_payload(item)[:6].upper()}",
            "citation_id": item.get("citation_id"),
            "raw": item.get("raw"),
            "status": status,
            "priority": _priority(status),
            "mentor_level": item.get("mentor_level"),
            "gap": item.get("gap"),
            "suggested_action": item.get("suggested_action"),
            "queue_status": "open",
            "created_at": created_at,
        }
        tasks.append(task)
    queue = {
        "schema": "evidence_gap_queue.v1",
        "created_at": created_at,
        "open_count": len(tasks),
        "tasks": tasks,
        "policy": "证据缺口是待办队列，不会自动改写模型原文或用户正文。",
    }
    queue["queue_hash"] = _hash_payload(queue)
    return queue


def resolve_gap_task(queue: dict[str, Any], *, task_id: str, resolution: str, evidence_id: str | None = None) -> dict[str, Any]:
    updated = json.loads(json.dumps(queue, ensure_ascii=False))
    found = False
    for task in updated.get("tasks") or []:
        if str(task.get("task_id")) != task_id:
            continue
        found = True
        task["queue_status"] = "resolved"
        task["resolution"] = resolution
        task["resolved_evidence_id"] = evidence_id
        task["resolved_at"] = datetime.now(timezone.utc).isoformat()
    if not found:
        raise ValueError(f"gap task not found: {task_id}")
    updated["open_count"] = sum(1 for task in updated.get("tasks") or [] if task.get("queue_status") == "open")
    updated["queue_hash"] = _hash_payload(updated)
    return updated


def _priority(status: str) -> str:
    if status == "contradicted":
        return "critical"
    if status == "unverifiable":
        return "high"
    if status in {"weakly_verified", "irrelevant"}:
        return "medium"
    return "low"


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
