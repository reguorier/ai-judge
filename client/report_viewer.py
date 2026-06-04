"""Open and summarize generated report files without requiring a dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def report_summary(report_payload: dict[str, Any]) -> str:
    summary = report_payload.get("summary") or report_payload
    return "\n".join(
        [
            f"run_id: {summary.get('run_id', 'unknown')}",
            f"status: {summary.get('status', 'unknown')}",
            f"human_status: {summary.get('human_status', 'unknown')}",
            f"final_report: {summary.get('final_report_path', '')}",
        ]
    )


def read_markdown(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
