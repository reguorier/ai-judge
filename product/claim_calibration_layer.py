"""
P5 Claim Review Calibration Layer
=================================
Implements claim calibration between AI Judge top_claims and Human Gavel decisions.

Features:
- ensure_claim_ids: generate stable claim_id for each top_claim
- build_claim_calibration: match AI claims with human gavel decisions
- write_claim_calibration: write JSON + Markdown outputs
- build_claim_calibration_index: global index across all runs
"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


# ── Constants ──────────────────────────────────────────────────────────────

CLAIM_ID_SALT_SEPARATOR = "|"


# ── Helpers ────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha1_short(*parts: str, length: int = 12) -> str:
    h = hashlib.sha1(CLAIM_ID_SALT_SEPARATOR.join(parts).encode("utf-8")).hexdigest()
    return h[:length]


def _normalize_claim_text(text: str) -> str:
    """Normalize claim text for fuzzy matching: lowercase, strip punctuation/spaces."""
    if not text:
        return ""
    t = text.lower().strip()
    # Remove common punctuation
    t = re.sub(r"[^\w\s]", "", t)
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t)
    return t


def _load_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_markdown(path: Path, md: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)


# ── 1. ensure_claim_ids ──────────────────────────────────────────────────

def ensure_claim_ids(run_dir: Path) -> dict:
    """
    Read hermes-output.json, ensure every top_claims entry has a stable claim_id.
    Returns {"ok": bool, "claims_updated": int}.
    """
    hermes_path = run_dir / "hermes-output.json"
    data = _load_json(hermes_path)
    if not data:
        return {"ok": False, "claims_updated": 0, "error": "hermes-output.json not found or invalid"}

    run_id = data.get("run_id", run_dir.name)
    top_claims = data.get("top_claims", [])
    if not isinstance(top_claims, list):
        return {"ok": False, "claims_updated": 0, "error": "top_claims is not a list"}

    updated = 0
    for i, claim in enumerate(top_claims):
        if not isinstance(claim, dict):
            continue
        # Skip if already has a claim_id
        if claim.get("claim_id") and str(claim["claim_id"]).strip():
            continue
        seat = claim.get("seat", claim.get("seat_name", ""))
        text = claim.get("text", claim.get("claim", ""))
        # Fallback: use index
        if not seat and not text:
            seat = f"claim_{i}"
            text = f"top_claim_{i}"
        claim_id = _sha1_short(run_id, str(seat), _normalize_claim_text(str(text)))
        claim["claim_id"] = claim_id
        updated += 1

    data["top_claims"] = top_claims
    _save_json(hermes_path, data)
    return {"ok": True, "claims_updated": updated}


# ── 2. build_claim_calibration ────────────────────────────────────────────

def build_claim_calibration(run_dir: Path) -> dict:
    """
    Build claim calibration by matching top_claims with human gavel decisions.
    Matching priority:
      1. claim_id exact match
      2. top_claim_N format (e.g. top_claim_1 → index 0)
      3. index number (e.g. "1" → index 0)
      4. normalized text contains match
    """
    run_id = run_dir.name
    hermes_path = run_dir / "hermes-output.json"
    gavel_path = run_dir / "human-gavel.json"

    hermes = _load_json(hermes_path) or {}
    gavel = _load_json(gavel_path) or {}

    top_claims = hermes.get("top_claims", [])
    accepted_claims = gavel.get("accepted_claims", [])
    rejected_claims = gavel.get("rejected_claims", [])

    # Build gavel lookup by various keys
    gavel_entries = []
    for entry in accepted_claims:
        gavel_entries.append({"entry": entry, "status": "accepted"})
    for entry in rejected_claims:
        gavel_entries.append({"entry": entry, "status": "rejected"})

    accepted_out = []
    rejected_out = []
    unmatched = []
    warnings = []
    seat_summary: dict = {}
    source_files = {
        "hermes_output": str(hermes_path),
        "human_gavel": str(gavel_path),
    }

    # Pre-build lookup structures for gavel entries
    gavel_by_claim_id: dict = {}
    gavel_by_index: dict = {}
    gavel_by_normalized_text: dict = {}

    for ge in gavel_entries:
        e = ge["entry"]
        # e can be str (direct user input like "top_claim_1") or dict (claim_review style)
        if isinstance(e, str):
            raw_ref = e
            gid = ""
            gtext = _normalize_claim_text(e)
        elif isinstance(e, dict):
            gid = e.get("claim_id", "")
            raw_ref = e.get("claim_reference", e.get("reference", ""))
            gtext = _normalize_claim_text(str(e.get("text", e.get("claim", ""))))
            ge["entry"] = e
        else:
            continue

        if gid:
            gavel_by_claim_id[gid] = ge
        # Check for top_claim_N or index
        if raw_ref:
            # top_claim_N
            m = re.match(r"top_claim_(\d+)", str(raw_ref), re.IGNORECASE)
            if m:
                idx = int(m.group(1)) - 1
                gavel_by_index[idx] = ge
            else:
                # pure number
                try:
                    idx = int(raw_ref) - 1
                    gavel_by_index[idx] = ge
                except (ValueError, TypeError):
                    pass
        # normalized text
        if gtext:
            gavel_by_normalized_text[gtext] = ge

    # Now match each top_claim
    for i, claim in enumerate(top_claims):
        if not isinstance(claim, dict):
            continue
        cid = claim.get("claim_id", "")
        seat = claim.get("seat", claim.get("seat_name", ""))
        text = claim.get("text", claim.get("claim", ""))
        norm_text = _normalize_claim_text(str(text))

        matched_ge = None
        match_type = ""

        # 1. claim_id exact match
        if cid and cid in gavel_by_claim_id:
            matched_ge = gavel_by_claim_id[cid]
            match_type = "claim_id"

        # 2. top_claim_N / index
        if not matched_ge and i in gavel_by_index:
            matched_ge = gavel_by_index[i]
            match_type = "index"

        # 3. normalized text contains
        if not matched_ge and norm_text:
            for gk in gavel_by_normalized_text:
                if norm_text in gk or gk in norm_text:
                    matched_ge = gavel_by_normalized_text[gk]
                    match_type = "text"
                    break

        claim_out = {
            "claim_id": cid,
            "index": i + 1,
            "seat": seat,
            "text": text,
            "gavel_match": match_type or "",
            "gavel_status": matched_ge["status"] if matched_ge else "unmatched",
        }

        if matched_ge:
            if matched_ge["status"] == "accepted":
                accepted_out.append(claim_out)
            else:
                rejected_out.append(claim_out)
        else:
            unmatched.append(claim_out)

        # seat summary
        s = seat or "unknown"
        if s not in seat_summary:
            seat_summary[s] = {"accepted": 0, "rejected": 0, "unmatched": 0}
        if matched_ge:
            key = matched_ge["status"]
            if key == "accepted":
                seat_summary[s]["accepted"] += 1
            else:
                seat_summary[s]["rejected"] += 1
        else:
            seat_summary[s]["unmatched"] += 1

    result = {
        "schema_version": "ai-judge-claim-calibration-v1",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "claim_count": len(top_claims),
        "accepted": accepted_out,
        "rejected": rejected_out,
        "unmatched": unmatched,
        "seat_summary": seat_summary,
        "warnings": warnings,
        "source_files": source_files,
    }
    return result


# ── 3. write_claim_calibration ────────────────────────────────────────────

def _render_calibration_markdown(cal: dict) -> str:
    """Render claim calibration as human-readable Markdown."""
    lines = []
    lines.append(f"# Claim Calibration Report")
    lines.append(f"")
    lines.append(f"- Run ID: {cal['run_id']}")
    lines.append(f"- Generated: {cal['generated_at']}")
    lines.append(f"- Schema: {cal['schema_version']}")
    lines.append(f"- Total Claims: {cal['claim_count']}")
    lines.append(f"")
    lines.append(f"## Summary")
    lines.append(f"- ✅ Accepted: {len(cal['accepted'])}")
    lines.append(f"- ❌ Rejected: {len(cal['rejected'])}")
    lines.append(f"- ⚠️ Unmatched: {len(cal['unmatched'])}")
    lines.append(f"")

    if cal["accepted"]:
        lines.append("## Accepted Claims")
        lines.append("")
        for c in cal["accepted"]:
            lines.append(f"### [{c['index']}] {c['seat']}")
            lines.append(f"- **Claim ID**: `{c['claim_id']}`")
            lines.append(f"- **Text**: {c['text']}")
            lines.append(f"- **Gavel Match**: {c['gavel_match']}")
            lines.append(f"- **Status**: ✅ accepted")
            lines.append("")

    if cal["rejected"]:
        lines.append("## Rejected Claims")
        lines.append("")
        for c in cal["rejected"]:
            lines.append(f"### [{c['index']}] {c['seat']}")
            lines.append(f"- **Claim ID**: `{c['claim_id']}`")
            lines.append(f"- **Text**: {c['text']}")
            lines.append(f"- **Gavel Match**: {c['gavel_match']}")
            lines.append(f"- **Status**: ❌ rejected")
            lines.append("")

    if cal["unmatched"]:
        lines.append("## Unmatched Claims")
        lines.append("")
        for c in cal["unmatched"]:
            lines.append(f"### [{c['index']}] {c['seat']}")
            lines.append(f"- **Claim ID**: `{c['claim_id']}`")
            lines.append(f"- **Text**: {c['text']}")
            lines.append(f"- **Status**: ⚠️ unmatched")
            lines.append("")

    if cal["seat_summary"]:
        lines.append("## Seat Summary")
        lines.append("")
        lines.append("| Seat | Accepted | Rejected | Unmatched |")
        lines.append("|-------|----------|----------|-----------|")
        for seat, counts in cal["seat_summary"].items():
            lines.append(f"| {seat} | {counts['accepted']} | {counts['rejected']} | {counts['unmatched']} |")
        lines.append("")

    if cal["warnings"]:
        lines.append("## Warnings")
        for w in cal["warnings"]:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    lines.append("--- ")
    lines.append(f"*Generated by AI Judge Claim Calibration Layer*")
    return "\n".join(lines)


def write_claim_calibration(run_dir: Path) -> dict:
    """
    Build claim calibration and write both JSON and Markdown files.
    Returns the calibration dict.
    """
    cal = build_claim_calibration(run_dir)

    json_path = run_dir / "claim-calibration.json"
    md_path = run_dir / "claim-calibration.md"

    _save_json(json_path, cal)
    _save_markdown(md_path, _render_calibration_markdown(cal))

    cal["_files_written"] = {
        "json": str(json_path),
        "md": str(md_path),
    }
    return cal


# ── 4. build_claim_calibration_index ───────────────────────────────────────

def build_claim_calibration_index(runs_dir: Path, vault_dir: Path | None = None) -> dict:
    """
    Scan all runs for claim-calibration.json, build global index.
    Write index JSON to runs_dir and Markdown to vault_dir/Indexes/.
    """
    runs_dir = Path(runs_dir)
    vault_dir = Path(vault_dir) if vault_dir else None

    total_runs = 0
    total_claims_reviewed = 0
    total_accepted = 0
    total_rejected = 0
    total_unmatched = 0
    runs_list = []
    seat_summary_global: dict = {}
    warnings_global = []

    if not runs_dir.exists():
        warnings_global.append(f"Runs directory does not exist: {runs_dir}")

    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        cal_path = run_dir / "claim-calibration.json"
        if not cal_path.exists():
            continue

        cal = _load_json(cal_path)
        if not cal:
            warnings_global.append(f"Failed to read {cal_path}")
            continue

        total_runs += 1
        run_id = cal.get("run_id", run_dir.name)
        n_claims = cal.get("claim_count", 0)
        n_accepted = len(cal.get("accepted", []))
        n_rejected = len(cal.get("rejected", []))
        n_unmatched = len(cal.get("unmatched", []))

        total_claims_reviewed += n_claims
        total_accepted += n_accepted
        total_rejected += n_rejected
        total_unmatched += n_unmatched

        # Determine status
        status = "ready"
        if n_unmatched > 0:
            status = "warning"

        runs_list.append({
            "run_id": run_id,
            "claim_count": n_claims,
            "accepted_count": n_accepted,
            "rejected_count": n_rejected,
            "unmatched_count": n_unmatched,
            "status": status,
            "generated_at": cal.get("generated_at", ""),
        })

        # Aggregate seat summary
        for seat, counts in cal.get("seat_summary", {}).items():
            if seat not in seat_summary_global:
                seat_summary_global[seat] = {"accepted": 0, "rejected": 0, "unmatched": 0}
            seat_summary_global[seat]["accepted"] += counts.get("accepted", 0)
            seat_summary_global[seat]["rejected"] += counts.get("rejected", 0)
            seat_summary_global[seat]["unmatched"] += counts.get("unmatched", 0)

    # Top rejected seats
    top_rejected = sorted(
        [{"seat": s, "rejected": c["rejected"]} for s, c in seat_summary_global.items()],
        key=lambda x: x["rejected"],
        reverse=True,
    )[:3]

    index = {
        "schema_version": "ai-judge-claim-calibration-index-v1",
        "generated_at": _now_iso(),
        "total_runs": total_runs,
        "total_claims_reviewed": total_claims_reviewed,
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
        "total_unmatched": total_unmatched,
        "runs": runs_list,
        "seat_summary": seat_summary_global,
        "top_rejected_seats": top_rejected,
        "vault_md_path": "",
        "warnings": warnings_global,
    }

    # Write index JSON
    index_path = runs_dir / "claim-calibration-index.json"
    _save_json(index_path, index)

    # Write vault Markdown
    vault_md_path = ""
    if vault_dir:
        vault_md_dir = vault_dir / "Indexes"
        vault_md_dir.mkdir(parents=True, exist_ok=True)
        vault_md_path = vault_md_dir / "claim-calibration.md"
        _save_markdown(vault_md_path, _render_index_markdown(index))
        index["vault_md_path"] = str(vault_md_path)

    index["_files_written"] = {
        "index_json": str(index_path),
        "vault_md": str(vault_md_path) if vault_md_path else "",
    }
    return index


def _render_index_markdown(index: dict) -> str:
    lines = []
    lines.append("# Claim Calibration Index")
    lines.append("")
    lines.append(f"- Generated: {index['generated_at']}")
    lines.append(f"- Schema: {index['schema_version']}")
    lines.append(f"- Total Runs: {index['total_runs']}")
    lines.append(f"- Total Claims Reviewed: {index['total_claims_reviewed']}")
    lines.append(f"- ✅ Total Accepted: {index['total_accepted']}")
    lines.append(f"- ❌ Total Rejected: {index['total_rejected']}")
    lines.append(f"- ⚠️ Total Unmatched: {index['total_unmatched']}")
    lines.append("")

    if index["runs"]:
        lines.append("## Runs")
        lines.append("")
        lines.append("| Run ID | Claims | Accepted | Rejected | Unmatched | Status |")
        lines.append("|---------|--------|----------|----------|-----------|--------|")
        for r in index["runs"]:
            status_emoji = "✅" if r["status"] == "ready" else "⚠️"
            lines.append(
                f"| {r['run_id']} | {r['claim_count']} | {r['accepted_count']} "
                f"| {r['rejected_count']} | {r['unmatched_count']} | {status_emoji} {r['status']} |"
            )
        lines.append("")

    if index["seat_summary"]:
        lines.append("## Global Seat Summary")
        lines.append("")
        lines.append("| Seat | Accepted | Rejected | Unmatched |")
        lines.append("|-------|----------|----------|-----------|")
        for seat, counts in index["seat_summary"].items():
            lines.append(f"| {seat} | {counts['accepted']} | {counts['rejected']} | {counts['unmatched']} |")
        lines.append("")

    if index["top_rejected_seats"]:
        lines.append("## Top Rejected Seats")
        lines.append("")
        for item in index["top_rejected_seats"]:
            lines.append(f"- **{item['seat']}**: {item['rejected']} rejected")
        lines.append("")

    if index["warnings"]:
        lines.append("## Warnings")
        for w in index["warnings"]:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    lines.append("--- ")
    lines.append("*Generated by AI Judge Claim Calibration Layer*")
    return "\n".join(lines)


# ── CLI / Direct Execution ─────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    runs_dir = Path.home() / "Library" / "Application Support" / "AI Judge" / "runtime" / "runs"
    vault_dir = Path.home() / "Documents" / "AI-Judge-Obsidian-Vault"

    if len(sys.argv) > 1:
        run_id = sys.argv[1]
        run_dir = runs_dir / run_id
        print(f"[ensure_claim_ids] {run_dir}")
        result = ensure_claim_ids(run_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"\n[write_claim_calibration] {run_dir}")
        cal = write_claim_calibration(run_dir)
        print(json.dumps(cal, ensure_ascii=False, indent=2))
    else:
        print(f"[build_claim_calibration_index]")
        print(f"  runs_dir = {runs_dir}")
        print(f"  vault_dir = {vault_dir}")
        index = build_claim_calibration_index(runs_dir, vault_dir)
        print(json.dumps(index, ensure_ascii=False, indent=2))
