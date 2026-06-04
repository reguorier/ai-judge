"""Load existing report artifacts for a follow-up note."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_followup_context(run_dir: Path) -> dict[str, Any]:
    files = {
        "final_report": run_dir / "final_report.md",
        "summary": run_dir / "summary.json",
        "evidence_packet": run_dir / "evidence_packet.json",
        "seat_matrix": run_dir / "seat_matrix.json",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing follow-up context files: {', '.join(missing)}")
    return {
        "final_report": files["final_report"].read_text(encoding="utf-8"),
        "summary": json.loads(files["summary"].read_text(encoding="utf-8")),
        "evidence_packet": json.loads(files["evidence_packet"].read_text(encoding="utf-8")),
        "seat_matrix": json.loads(files["seat_matrix"].read_text(encoding="utf-8")),
    }
