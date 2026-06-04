"""Schema constants for client-first AI Judge final reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

REPORT_SCHEMA_VERSION: Final = "ai_judge.client_final_report.v1"
SUMMARY_SCHEMA_VERSION: Final = "ai_judge.client_run_summary.v1"

CLIENT_MODES: Final = {
    "quick_judge": "快速判决",
    "deep_judge": "深度裁决",
    "ops_check": "运维验收",
    "prediction_pool": "预测池",
    "simulation_game": "模拟博弈",
}

REPORT_SECTION_TITLES: Final = [
    "核心结论",
    "适用边界",
    "已验证事实",
    "推断与判断",
    "席位观点摘要",
    "共识与分歧",
    "证据强度",
    "风险与失败条件",
    "推荐行动",
    "审计附件",
]

TERMINAL_STATUSES: Final = {"completed", "partial_completed", "failed", "cancelled"}
ACTIVE_STATUSES: Final = {"created", "queued", "running", "collecting", "judging", "reporting", "paused"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_mode(mode: str | None) -> str:
    candidate = (mode or "deep_judge").strip()
    if candidate in CLIENT_MODES:
        return candidate
    aliases = {
        "quick": "quick_judge",
        "deep": "deep_judge",
        "ops": "ops_check",
        "prediction": "prediction_pool",
        "game": "simulation_game",
        "werewolf": "simulation_game",
    }
    return aliases.get(candidate, "deep_judge")


def mode_label(mode: str | None) -> str:
    return CLIENT_MODES.get(normalize_mode(mode), CLIENT_MODES["deep_judge"])
