"""Maintain reports/index.json for client-first report runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_index(reports_root: Path) -> dict[str, Any]:
    path = reports_root / "index.json"
    if not path.exists():
        return {"schema": "ai_judge.reports_index.v1", "runs": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema": "ai_judge.reports_index.v1", "runs": [], "warnings": ["previous index was invalid JSON"]}


def update_index(reports_root: Path, summary: dict[str, Any]) -> Path:
    reports_root.mkdir(parents=True, exist_ok=True)
    path = reports_root / "index.json"
    index = load_index(reports_root)
    runs = [item for item in index.get("runs", []) if item.get("run_id") != summary.get("run_id")]
    runs.insert(0, {
        "run_id": summary.get("run_id"),
        "title": summary.get("title"),
        "mode": summary.get("mode"),
        "status": summary.get("status"),
        "reliability": summary.get("reliability"),
        "created_at": summary.get("created_at"),
        "completed_at": summary.get("completed_at"),
        "final_report_path": summary.get("final_report_path"),
        "html_report_path": summary.get("html_report_path"),
    })
    index["runs"] = runs[:100]
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
