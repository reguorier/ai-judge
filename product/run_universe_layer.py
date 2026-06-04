"""run_universe_layer.py — Unified Run Universe

Scans all run directories and builds a single canonical run-universe.json + run-universe.md.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "ai-judge-run-universe-v1"

FILES_OF_INTEREST = [
    "verdict.json",
    "hermes-output.json",
    "human-gavel.json",
    "claim-calibration.json",
    "trace.json",
    "index.html",
]

KEY_MAP = {
    "verdict.json": "verdict",
    "hermes-output.json": "hermes",
    "human-gavel.json": "human_gavel",
    "claim-calibration.json": "claim_calibration",
    "trace.json": "trace",
    "index.html": "html",
}


def build_run_universe(runs_dir: Path) -> dict[str, Any]:
    """Scan all runs, build unified universe dict."""
    runs: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    counts = {v: 0 for v in KEY_MAP.values()}
    canonical_run_count = 0

    if not runs_dir.exists():
        return _empty_universe()

    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        run_dir = entry
        run_id = run_dir.name

        # Check which files exist
        has: dict[str, bool] = {}
        for fname in FILES_OF_INTEREST:
            key = KEY_MAP[fname]
            exists = (run_dir / fname).exists()
            has[key] = exists
            if exists:
                counts[key] += 1

        # Status precedence: hermes-output.json > verdict.json
        status = "unknown"
        question = ""
        created_at = ""

        hermes_path = run_dir / "hermes-output.json"
        verdict_path = run_dir / "verdict.json"

        if has.get("hermes"):
            try:
                hermes = json.loads(hermes_path.read_text(encoding="utf-8"))
                status = hermes.get("status", "unknown")
                question = hermes.get("question", "")
                created_at = hermes.get("created_at", "")
            except (json.JSONDecodeError, OSError):
                pass

        if not question and has.get("verdict"):
            try:
                verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
                if status == "unknown":
                    status = verdict.get("status", "unknown")
                if not question:
                    question = verdict.get("question", "")
                if not created_at:
                    created_at = verdict.get("created_at", "")
            except (json.JSONDecodeError, OSError):
                pass

        # Truncate question to 200 chars
        if isinstance(question, str):
            question = question[:200]

        run_entry = {
            "run_id": run_id,
            "created_at": created_at,
            "has_verdict": has.get("verdict", False),
            "has_hermes": has.get("hermes", False),
            "has_human_gavel": has.get("human_gavel", False),
            "has_claim_calibration": has.get("claim_calibration", False),
            "has_trace": has.get("trace", False),
            "has_html": has.get("html", False),
            "status": status,
            "question": question,
        }
        runs.append(run_entry)

        # Gap detection
        if has.get("verdict") and not has.get("hermes"):
            gaps.append({"run_id": run_id, "issue": "有 verdict 但没有 hermes"})
        if has.get("claim_calibration") and not has.get("hermes"):
            gaps.append({"run_id": run_id, "issue": "有 claim_calibration 但没有 hermes"})
        if has.get("human_gavel") and not has.get("hermes"):
            gaps.append({"run_id": run_id, "issue": "有 human_gavel 但没有 hermes"})

    canonical_run_count = len(runs)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_run_count": canonical_run_count,
        "counts": counts,
        "runs": runs,
        "gaps": gaps,
    }


def write_run_universe(runs_dir: Path, vault_dir: Path | None = None) -> dict[str, Any]:
    """Build and write run-universe.json + run-universe.md. Return universe dict."""
    universe = build_run_universe(runs_dir)

    # Write JSON
    json_path = runs_dir / "run-universe.json"
    json_path.write_text(json.dumps(universe, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write Markdown
    md_lines = _build_universe_markdown(universe)
    md_path = runs_dir / "run-universe.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # Write to vault if available
    if vault_dir:
        vault_indexes = Path(vault_dir) / "Indexes"
        try:
            vault_indexes.mkdir(parents=True, exist_ok=True)
            vault_md = vault_indexes / "run-universe.md"
            vault_md.write_text("\n".join(md_lines), encoding="utf-8")
        except (OSError, PermissionError):
            pass

    return universe


def _build_universe_markdown(universe: dict[str, Any]) -> list[str]:
    """Generate Markdown for run universe."""
    lines: list[str] = []
    lines.append("# Run Universe")
    lines.append("")
    lines.append(f"- **Schema**: {universe['schema_version']}")
    lines.append(f"- **Generated**: {universe['generated_at']}")
    lines.append(f"- **Canonical Run Count**: {universe['canonical_run_count']}")
    lines.append("")

    counts = universe.get("counts", {})
    lines.append("## File Counts")
    lines.append("")
    lines.append("| File | Count |")
    lines.append("|------|-------|")
    for label, key in [
        ("Verdict", "verdict"),
        ("Hermes", "hermes"),
        ("Human Gavel", "human_gavel"),
        ("Claim Calibration", "claim_calibration"),
        ("Trace", "trace"),
        ("HTML", "html"),
    ]:
        lines.append(f"| {label} | {counts.get(key, 0)} |")
    lines.append("")

    runs = universe.get("runs", [])
    if runs:
        lines.append("## Runs")
        lines.append("")
        lines.append("| Run ID | Status | V | H | G | C | T | I | Question |")
        lines.append("|--------|--------|---|---|---|---|---|---|----------|")
        for r in runs:
            v = "✓" if r.get("has_verdict") else "·"
            h = "✓" if r.get("has_hermes") else "·"
            g = "✓" if r.get("has_human_gavel") else "·"
            c = "✓" if r.get("has_claim_calibration") else "·"
            t = "✓" if r.get("has_trace") else "·"
            i = "✓" if r.get("has_html") else "·"
            q = r.get("question", "")[:60].replace("|", "\\|")
            lines.append(f"| {r['run_id']} | {r.get('status','')} | {v} | {h} | {g} | {c} | {t} | {i} | {q} |")
        lines.append("")

    gaps = universe.get("gaps", [])
    if gaps:
        lines.append("## Gaps")
        lines.append("")
        for gap in gaps:
            lines.append(f"- **{gap['run_id']}**: {gap['issue']}")
        lines.append("")

    return lines


def _empty_universe() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_run_count": 0,
        "counts": {v: 0 for v in KEY_MAP.values()},
        "runs": [],
        "gaps": [],
    }


if __name__ == "__main__":
    import sys

    runs_dir = Path(os.environ.get("AI_JUDGE_RUNS_DIR", "runtime/runs"))
    vault_dir_str = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT")
    vault_dir = Path(vault_dir_str) if vault_dir_str else None

    u = write_run_universe(runs_dir, vault_dir)
    print(f"canonical={u['canonical_run_count']} gaps={len(u['gaps'])}")
