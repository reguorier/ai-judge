"""trust_calibration_layer.py — Seat Trust Calibration

Aggregates trust scores per seat from claim-calibration.json and human-gavel.json data.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "ai-judge-trust-calibration-v1"


def build_trust_calibration(runs_dir: Path) -> dict[str, Any]:
    """Aggregate trust scores per seat from calibration & gavel data."""
    seats: dict[str, dict[str, Any]] = {}

    if not runs_dir.exists():
        return _empty_calibration()

    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        run_dir = entry
        run_id = run_dir.name

        # 1) claim-calibration.json
        cal_path = run_dir / "claim-calibration.json"
        if cal_path.exists():
            try:
                cal = json.loads(cal_path.read_text(encoding="utf-8"))
                _ingest_calibration_claims(seats, cal, run_id)
            except (json.JSONDecodeError, OSError):
                pass

        # 2) human-gavel.json
        gavel_path = run_dir / "human-gavel.json"
        if gavel_path.exists():
            try:
                gavel = json.loads(gavel_path.read_text(encoding="utf-8"))
                _ingest_gavel_data(seats, gavel, run_id)
            except (json.JSONDecodeError, OSError):
                pass

    # Compute scores
    seat_list = _compute_trust_scores(seats)

    # Derived lists
    top_trusted = sorted(
        [s for s in seat_list if s["trust_score"] is not None],
        key=lambda x: x["trust_score"],
        reverse=True,
    )[:5]
    low_evidence = [s for s in seat_list if s["reviewed"] < 3]
    rejected_claim = [s for s in seat_list if s["rejected"] > 0]

    warnings: list[str] = []
    if not seat_list:
        warnings.append("no_seats_found")

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seat_count": len(seat_list),
        "seats": seat_list,
        "top_trusted_seats": [s["seat_id"] for s in top_trusted],
        "low_evidence_seats": [s["seat_id"] for s in low_evidence],
        "rejected_claim_seats": [s["seat_id"] for s in rejected_claim],
        "warnings": warnings,
    }


def write_trust_calibration(runs_dir: Path, vault_dir: Path | None = None) -> dict[str, Any]:
    """Build and write trust-calibration.json + trust-calibration.md."""
    cal = build_trust_calibration(runs_dir)

    # Write JSON
    json_path = runs_dir / "trust-calibration.json"
    json_path.write_text(json.dumps(cal, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write Markdown
    md_lines = _build_calibration_markdown(cal)
    md_path = runs_dir / "trust-calibration.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # Write to vault if available
    if vault_dir:
        vault_indexes = Path(vault_dir) / "Indexes"
        try:
            vault_indexes.mkdir(parents=True, exist_ok=True)
            vault_md = vault_indexes / "trust-calibration.md"
            vault_md.write_text("\n".join(md_lines), encoding="utf-8")
        except (OSError, PermissionError):
            pass

    # Weekly digest update
    _try_update_weekly_digest(cal, vault_dir)

    return cal


def get_seat_trust(seat_id: str, runs_dir: Path) -> dict[str, Any] | None:
    """Return single seat trust calibration with sample_runs and warnings."""
    cal = build_trust_calibration(runs_dir)
    for seat in cal.get("seats", []):
        if seat["seat_id"] == seat_id:
            return seat
    return None


def _ingest_calibration_claims(
    seats: dict[str, dict[str, Any]],
    cal: dict[str, Any],
    run_id: str,
) -> None:
    """Ingest accepted / rejected / unmatched claims from claim-calibration.json."""
    for category in ["accepted", "rejected", "unmatched"]:
        claims = cal.get(category, [])
        if not isinstance(claims, list):
            continue
        for claim in claims:
            seat_id = _extract_seat_id(claim)
            if not seat_id:
                continue
            _ensure_seat(seats, seat_id)
            seats[seat_id][category] = seats[seat_id].get(category, 0) + 1
            # track sample runs (keep most recent 3)
            sample_runs = seats[seat_id].setdefault("_sample_runs", [])
            if run_id not in sample_runs:
                sample_runs.append(run_id)
                if len(sample_runs) > 3:
                    sample_runs.pop(0)


def _ingest_gavel_data(
    seats: dict[str, dict[str, Any]],
    gavel: dict[str, Any],
    run_id: str,
) -> None:
    """Ingest human gavel data where it maps seats."""
    # Gavel may contain accepted/rejected lists and corrections
    seat_corrections = gavel.get("corrections", {})
    if not isinstance(seat_corrections, dict):
        return

    # corrections may have per-seat corrections
    for seat_id, correction in seat_corrections.items():
        if not seat_id or seat_id == "run_id":
            continue
        _ensure_seat(seats, seat_id)
        seats[seat_id]["_has_gavel"] = True


def _extract_seat_id(claim: Any) -> str | None:
    """Extract seat ID from claim entry (str or dict)."""
    if isinstance(claim, str):
        return None
    if isinstance(claim, dict):
        return claim.get("seat") or claim.get("seat_id")
    return None


def _ensure_seat(seats: dict[str, dict[str, Any]], seat_id: str) -> None:
    """Ensure seat entry exists."""
    if seat_id not in seats:
        seats[seat_id] = {
            "seat_id": seat_id,
            "accepted": 0,
            "rejected": 0,
            "unmatched": 0,
            "_sample_runs": [],
        }


def _compute_trust_scores(seats: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute trust scores for all seats using transparent formula."""
    result: list[dict[str, Any]] = []
    for seat_id, raw in seats.items():
        accepted = raw.get("accepted", 0)
        rejected = raw.get("rejected", 0)
        unmatched = raw.get("unmatched", 0)
        reviewed = accepted + rejected + unmatched

        warnings: list[str] = []
        if reviewed == 0:
            warnings.append("no_reviewed_claims")
            trust_score = None
        else:
            accepted_rate = accepted / reviewed
            rejected_rate = rejected / reviewed
            unmatched_rate = unmatched / reviewed
            trust_score = round(
                max(0.0, min(100.0, 50.0 + 40.0 * accepted_rate - 30.0 * rejected_rate - 10.0 * unmatched_rate)),
                1,
            )

        entry: dict[str, Any] = {
            "seat_id": seat_id,
            "claims_total": reviewed,
            "accepted": accepted,
            "rejected": rejected,
            "unmatched": unmatched,
            "reviewed": reviewed,
            "accepted_rate": round(accepted / reviewed, 3) if reviewed > 0 else 0.0,
            "rejected_rate": round(rejected / reviewed, 3) if reviewed > 0 else 0.0,
            "unmatched_rate": round(unmatched / reviewed, 3) if reviewed > 0 else 0.0,
            "trust_score": trust_score,
            "warnings": warnings,
            "sample_runs": raw.get("_sample_runs", [])[-3:],
        }
        result.append(entry)

    # Sort by trust_score descending (None at end)
    result.sort(key=lambda x: (x["trust_score"] is not None, x["trust_score"] or 0), reverse=True)
    return result


def _build_calibration_markdown(cal: dict[str, Any]) -> list[str]:
    """Generate Markdown for trust calibration."""
    lines: list[str] = []
    lines.append("# Trust Calibration")
    lines.append("")
    lines.append(f"- **Schema**: {cal['schema_version']}")
    lines.append(f"- **Generated**: {cal['generated_at']}")
    lines.append(f"- **Seat Count**: {cal['seat_count']}")
    lines.append("")

    # Main table
    seats = cal.get("seats", [])
    if seats:
        lines.append("## Seat Trust Scores")
        lines.append("")
        lines.append("| Seat ID | Trust Score | Accepted | Rejected | Unmatched | Reviewed |")
        lines.append("|---------|-------------|----------|----------|-----------|----------|")
        for s in seats:
            ts = str(s["trust_score"]) if s["trust_score"] is not None else "—"
            lines.append(
                f"| {s['seat_id']} | {ts} | {s['accepted']} | {s['rejected']} | {s['unmatched']} | {s['reviewed']} |"
            )
        lines.append("")

    # Top trusted
    top = cal.get("top_trusted_seats", [])
    if top:
        lines.append("## Top Trusted Seats")
        lines.append("")
        lines.append(", ".join(top))
        lines.append("")

    # Low evidence
    low = cal.get("low_evidence_seats", [])
    if low:
        lines.append("## Low Evidence Seats (< 3 reviewed)")
        lines.append("")
        lines.append(", ".join(low))
        lines.append("")

    # Rejected claim
    rej = cal.get("rejected_claim_seats", [])
    if rej:
        lines.append("## Seats with Rejected Claims")
        lines.append("")
        lines.append(", ".join(rej))
        lines.append("")

    return lines


def _try_update_weekly_digest(cal: dict[str, Any], vault_dir: str | Path | None) -> None:
    """Append calibration summary to latest weekly digest if it exists."""
    if not vault_dir:
        return
    try:
        indexes = Path(vault_dir) / "Indexes"
        if not indexes.exists():
            return

        # Find the most recent weekly digest (<YYYY-WNN>.md)
        weekly_files = sorted([f for f in indexes.iterdir() if _is_weekly_digest(f.name)], reverse=True)
        if not weekly_files:
            return

        latest = weekly_files[0]
        content = latest.read_text(encoding="utf-8")

        # Check if already has trust calibration section
        if "## Trust Calibration" in content:
            return

        seats = cal.get("seats", [])
        reviewed_total = sum(s.get("reviewed", 0) for s in seats)
        top_5 = [(s["seat_id"], s["trust_score"]) for s in seats if s["trust_score"] is not None][:5]
        top_str = ", ".join(f"{name}({score})" for name, score in top_5) if top_5 else "—"
        low_ev = cal.get("low_evidence_seats", [])
        low_str = ", ".join(low_ev) if low_ev else "—"

        # Get gaps from run-universe.json
        runs_dir = Path(os.environ.get("AI_JUDGE_RUNS_DIR", str(indexes.parent.parent / "runtime" / "runs")))
        gaps_count = 0
        universe_path = runs_dir / "run-universe.json" if runs_dir.name == "runs" else None
        if not universe_path and vault_dir:
            # Try to find runs dir relative to vault
            pass
        if universe_path and universe_path.exists():
            try:
                universe = json.loads(universe_path.read_text(encoding="utf-8"))
                gaps_count = len(universe.get("gaps", []))
            except (json.JSONDecodeError, OSError):
                pass

        digest_block = f"""

## Trust Calibration
- Reviewed claims: {reviewed_total}
- Top trusted seats: {top_str}
- Low evidence seats: {low_str}
- Universe gaps: {gaps_count}
"""
        latest.write_text(content.rstrip() + digest_block + "\n", encoding="utf-8")
    except (OSError, PermissionError):
        pass


def _is_weekly_digest(filename: str) -> bool:
    """Check if filename matches <YYYY-WNN>.md pattern."""
    import re

    return bool(re.match(r"^\d{4}-W\d{2}\.md$", filename))


def _empty_calibration() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seat_count": 0,
        "seats": [],
        "top_trusted_seats": [],
        "low_evidence_seats": [],
        "rejected_claim_seats": [],
        "warnings": ["no_seats_found"],
    }


if __name__ == "__main__":
    import sys

    runs_dir = Path(os.environ.get("AI_JUDGE_RUNS_DIR", "runtime/runs"))
    vault_dir_str = os.environ.get("AI_JUDGE_OBSIDIAN_VAULT")
    vault_dir = Path(vault_dir_str) if vault_dir_str else None

    t = write_trust_calibration(runs_dir, vault_dir)
    print(f"seats={t['seat_count']}")
    for s in t.get("seats", [])[:5]:
        print(f"  {s['seat_id']}: trust={s['trust_score']} reviewed={s['reviewed']}")
