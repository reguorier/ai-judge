"""Present backend run state as compact client status."""

from __future__ import annotations

from typing import Any


def controls_for(summary: dict[str, Any]) -> dict[str, bool]:
    status = summary.get("status")
    failed = int(summary.get("failed_seats") or 0)
    return {
        "can_pause": status in {"created", "queued", "running", "collecting", "judging", "reporting"},
        "can_resume": status == "paused",
        "can_stop": status in {"created", "queued", "running", "collecting", "judging", "reporting", "paused"},
        "can_rerun_failed": failed > 0 and status in {"partial_completed", "completed", "needs_rerun", "failed"},
    }


def human_status(summary: dict[str, Any]) -> str:
    status = summary.get("status", "unknown")
    valid = int(summary.get("valid_seats") or 0)
    total = int(summary.get("total_seats") or 0)
    failed = int(summary.get("failed_seats") or 0)
    if status == "completed":
        return f"运行完成，{valid}/{total} 个席位有效，失败席位 {failed} 个。最终报告已生成。"
    if status == "partial_completed":
        return f"部分完成，{valid}/{total} 个席位有效，失败席位 {failed} 个。可以生成部分报告或补跑失败席位。"
    if status == "paused":
        return f"已暂停，当前 {valid}/{total} 个席位有效。可以继续或终止。"
    if status == "cancelled":
        return "运行已终止，未继续生成新的主报告。"
    if status == "failed":
        return "运行失败，请查看 summary.json 和 operator_note.md。"
    if status in {"created", "queued"}:
        return "任务已创建，等待开始执行。"
    if status in {"running", "collecting", "judging", "reporting"}:
        return f"正在运行：已有 {valid}/{total} 个席位有效，失败席位 {failed} 个。"
    return "状态 unknown，请检查 run summary。"


def present_summary(summary: dict[str, Any]) -> dict[str, Any]:
    payload = dict(summary)
    payload["controls"] = controls_for(payload)
    payload["human_status"] = human_status(payload)
    return payload
