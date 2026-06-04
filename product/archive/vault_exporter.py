"""Archive final reports to Obsidian when configured, or a local pending folder."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any


def _default_vault_dir() -> Path:
    return Path(os.environ.get("AI_JUDGE_OBSIDIAN_DIR", str(Path.home() / "Documents" / "Obsidian" / "AI-Judge")))


def _safe_title(title: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z一-鿿._-]+", "-", title).strip("-._")
    return cleaned[:64] or "ai-judge-report"


def archive_report(summary: dict[str, Any], reports_root: Path, vault_dir: Path | None = None) -> dict[str, Any]:
    source = Path(summary.get("final_report_path") or "")
    if not source.exists():
        raise FileNotFoundError(f"final report not found: {source}")
    run_id = str(summary.get("run_id") or "unknown")
    title = _safe_title(str(summary.get("title") or run_id))
    target_root = vault_dir or _default_vault_dir()
    if target_root.exists():
        month = (summary.get("completed_at") or summary.get("created_at") or "0000-00")[:7]
        target_dir = target_root / month
        status = "archived"
        message = "已归档到 Obsidian/AI-Judge。"
    else:
        target_dir = reports_root / "archive_pending"
        status = "pending_local"
        message = "归档路径未配置，已保存到本地待归档。"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{run_id}-{title}.md"
    shutil.copyfile(source, target)
    return {"status": status, "message": message, "archive_path": str(target)}
