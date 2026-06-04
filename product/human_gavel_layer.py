"""
Human Gavel × Obsidian Reverse Sync Layer (P3 → P4)
Reads ## Human Gavel blocks from Obsidian run notes and writes
human-gavel.json + human-gavel.md into the corresponding run directory.

P4 additions: change history, conflict detection, claim-level mapping,
and review digest generation.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GAVEL_SCHEMA_VERSION = "ai-judge-human-gavel-v1"

# ── YAML-like field parser for Human Gavel block ──────────────────────

_GAVEL_BLOCK_RE = re.compile(
    r"##\s*Human\s+Gavel\s*\n(.*?)(?=\n##\s|\n---\s*\n|\Z)", re.DOTALL | re.IGNORECASE
)

_LIST_FIELD_RE = re.compile(r"^(\w[\w_]*)\s*:\s*$")
_KV_FIELD_RE = re.compile(r"^(\w[\w_]*)\s*:\s*(.*)$")
_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.*)$")


def _parse_yaml_like_block(block_text: str) -> dict[str, Any]:
    """Parse a simple YAML-like block (key: value, list fields)."""
    result: dict[str, Any] = {}
    lines = block_text.strip().splitlines()
    current_list_key: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for list field header: "accepted_claims:"
        lm = _LIST_FIELD_RE.match(stripped)
        if lm:
            key = lm.group(1)
            result[key] = []
            current_list_key = key
            continue

        # Check for list item: "- value"
        li = _LIST_ITEM_RE.match(stripped)
        if li and current_list_key:
            val = li.group(1).strip()
            if val.lower() == "none":
                pass  # skip "none" placeholder
            else:
                result[current_list_key].append(val)
            continue

        # Key-value line
        km = _KV_FIELD_RE.match(stripped)
        if km:
            key = km.group(1)
            val = km.group(2).strip()
            current_list_key = None

            # Type coercion
            if val.lower() in ("null", "none", ""):
                result[key] = None
            elif val.isdigit():
                result[key] = int(val)
            elif re.match(r"^\d+\.\d+$", val):
                result[key] = float(val)
            else:
                result[key] = val
            continue

    return result


def parse_human_gavel_from_note(note_path: Path) -> dict[str, Any]:
    """Parse the ## Human Gavel block from an Obsidian run note.

    Returns a dict with status='none' if the block is absent or status is empty.
    """
    if not note_path.exists():
        return {"status": "none"}

    try:
        text = note_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"status": "none"}

    m = _GAVEL_BLOCK_RE.search(text)
    if not m:
        return {"status": "none"}

    parsed = _parse_yaml_like_block(m.group(1))
    status = parsed.get("status")
    if not status or str(status).strip() == "":
        return {"status": "none"}

    return {
        "status": str(parsed.get("status", "")),
        "decision": str(parsed.get("decision", "")),
        "confidence": parsed.get("confidence"),
        "reviewer": str(parsed.get("reviewer", "")),
        "reviewed_at": str(parsed.get("reviewed_at", "")),
        "accepted_claims": parsed.get("accepted_claims", []),
        "rejected_claims": parsed.get("rejected_claims", []),
        "corrections": parsed.get("corrections", []),
        "notes": str(parsed.get("notes", "")),
    }


def _build_gavel_dict(run_id: str, parsed: dict[str, Any], source_note: str) -> dict[str, Any]:
    """Build a full human-gavel dict with validation."""
    warnings: list[str] = []
    errors: list[str] = []

    status = parsed.get("status", "none")
    decision = parsed.get("decision", "")
    confidence = parsed.get("confidence")
    reviewer = parsed.get("reviewer", "")
    reviewed_at = parsed.get("reviewed_at", "")
    accepted_claims = parsed.get("accepted_claims", [])
    rejected_claims = parsed.get("rejected_claims", [])
    corrections = parsed.get("corrections", [])
    notes = parsed.get("notes", "")

    # Validation
    if status not in ("none", "draft", "confirmed", "rejected", "needs_review"):
        warnings.append(f"unknown status: {status}")

    if confidence is not None:
        if not isinstance(confidence, (int, float)):
            warnings.append("confidence is not numeric")
            confidence = None
        elif confidence < 0 or confidence > 100:
            warnings.append("confidence out of range [0,100]")
            confidence = max(0, min(100, int(confidence)))

    if not isinstance(accepted_claims, list):
        warnings.append("accepted_claims is not a list")
        accepted_claims = []
    if not isinstance(rejected_claims, list):
        warnings.append("rejected_claims is not a list")
        rejected_claims = []
    if not isinstance(corrections, list):
        warnings.append("corrections is not a list")
        corrections = []

    ok = len(errors) == 0

    return {
        "schema_version": GAVEL_SCHEMA_VERSION,
        "run_id": run_id,
        "status": status,
        "decision": decision,
        "confidence": confidence,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "accepted_claims": accepted_claims,
        "rejected_claims": rejected_claims,
        "corrections": corrections,
        "notes": notes,
        "source_note": source_note,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "validation": {
            "ok": ok,
            "warnings": warnings,
            "errors": errors,
        },
    }


def write_human_gavel(run_dir: Path, gavel: dict[str, Any]) -> dict[str, Any]:
    """Write human-gavel.json and human-gavel.md to run_dir. Returns the gavel dict."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON
    json_path = run_dir / "human-gavel.json"
    json_path.write_text(
        json.dumps(gavel, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write human-readable Markdown
    md_path = run_dir / "human-gavel.md"
    lines: list[str] = [
        f"# Human Gavel — Run {gavel['run_id']}",
        "",
        f"- **Status**: {gavel['status']}",
        f"- **Decision**: {gavel['decision'] or '(none)'}",
        f"- **Confidence**: {gavel['confidence'] if gavel['confidence'] is not None else '(none)'}",
        f"- **Reviewer**: {gavel['reviewer'] or '(none)'}",
        f"- **Reviewed At**: {gavel['reviewed_at'] or '(none)'}",
        "",
        "## Accepted Claims",
    ]
    for c in gavel.get("accepted_claims", []):
        lines.append(f"- {c}")
    if not gavel.get("accepted_claims"):
        lines.append("(none)")

    lines.append("")
    lines.append("## Rejected Claims")
    for c in gavel.get("rejected_claims", []):
        lines.append(f"- {c}")
    if not gavel.get("rejected_claims"):
        lines.append("(none)")

    lines.append("")
    lines.append("## Corrections")
    for c in gavel.get("corrections", []):
        lines.append(f"- {c}")
    if not gavel.get("corrections"):
        lines.append("(none)")

    lines.append("")
    lines.append("## Notes")
    lines.append(gavel.get("notes", "(none)"))

    lines.append("")
    lines.append(f"- **Source Note**: {gavel['source_note']}")
    lines.append(f"- **Synced At**: {gavel['synced_at']}")
    lines.append(f"- **Validation OK**: {gavel['validation']['ok']}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return gavel


def _find_obsidian_note(run_id: str, vault_dir: Path) -> Path | None:
    """Find the Obsidian run note for a given run_id in the vault."""
    vault_dir = Path(vault_dir)
    # Security: resolve and validate
    try:
        vault_dir = vault_dir.resolve()
    except Exception:
        return None

    # Prevent path traversal
    if ".." in str(vault_dir) or not str(vault_dir).startswith("/"):
        return None

    # Search in Runs/ directory
    runs_dir = vault_dir / "Runs"
    if runs_dir.exists():
        # Try year/month structure
        for year_dir in sorted(runs_dir.iterdir(), reverse=True):
            if not year_dir.is_dir():
                continue
            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue
                candidate = month_dir / f"Run {run_id}.md"
                if candidate.exists():
                    return candidate

    # Fallback: recursive search (limited depth)
    for pattern in [f"Run {run_id}.md", f"{run_id}.md"]:
        matches = list(vault_dir.rglob(pattern))
        if matches:
            return matches[0]

    return None


def sync_human_gavel_for_run(
    run_id: str, runs_dir: Path, vault_dir: Path
) -> dict[str, Any]:
    """Sync human gavel from Obsidian note to run directory.

    Returns the gavel dict or status-only dict on failure.
    """
    runs_dir = Path(runs_dir)
    vault_dir = Path(vault_dir)

    # Security: path traversal check
    run_id_safe = run_id.replace("/", "").replace("\\", "").replace("..", "")
    run_dir = runs_dir / run_id_safe

    # Find Obsidian note
    note_path = _find_obsidian_note(run_id_safe, vault_dir)

    if not note_path:
        # Check if run_dir has obsidian-run-note.md as fallback
        local_note = run_dir / "obsidian-run-note.md"
        if local_note.exists():
            note_path = local_note
        else:
            return {
                "run_id": run_id_safe,
                "status": "none",
                "error": "obsidian_note_not_found",
                "message": f"No Obsidian note found for run {run_id_safe}",
            }

    # Parse the Human Gavel block
    parsed = parse_human_gavel_from_note(note_path)

    if parsed.get("status") == "none":
        return {
            "run_id": run_id_safe,
            "status": "none",
            "message": "No Human Gavel block found or status is empty",
            "source_note": str(note_path),
        }

    # Build the new gavel dict
    gavel = _build_gavel_dict(run_id_safe, parsed, str(note_path))

    # P4: Compute note hash for conflict detection
    note_hash = _compute_note_gavel_hash(note_path)
    gavel.setdefault("validation", {})["note_hash"] = note_hash

    # Read old gavel for history comparison (before overwriting)
    old_gavel_path = run_dir / "human-gavel.json"
    old_gavel: dict[str, Any] | None = None
    if old_gavel_path.exists():
        try:
            old_gavel = json.loads(old_gavel_path.read_text(encoding="utf-8"))
        except Exception:
            old_gavel = None

    # Write the new gavel
    write_human_gavel(run_dir, gavel)

    # P4: Conflict detection (after write so conflict object references new hash)
    conflict = check_gavel_conflict(run_dir, note_path)
    # Patch conflict into the written JSON
    _patch_gavel_json_field(run_dir, "conflict", conflict)

    # P4: Claim-level mapping
    claim_review = map_gavel_claims(run_dir, gavel)
    _patch_gavel_json_field(run_dir, "claim_review", claim_review)

    # P4: Write history
    write_human_gavel_history(run_dir, old_gavel, gavel, str(note_path))

    # Merge P4 fields into return value
    gavel["conflict"] = conflict
    gavel["claim_review"] = claim_review

    return gavel


def sync_all_human_gavels(
    runs_dir: Path, vault_dir: Path
) -> dict[str, Any]:
    """Scan all runs and sync human gavel for each."""
    runs_dir = Path(runs_dir)
    vault_dir = Path(vault_dir)

    results: list[dict[str, Any]] = []
    synced = 0
    skipped = 0
    errors = 0

    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name

        try:
            gavel = sync_human_gavel_for_run(run_id, runs_dir, vault_dir)
            results.append(gavel)
            if gavel.get("status") == "none":
                skipped += 1
            elif gavel.get("error"):
                errors += 1
            else:
                synced += 1
        except Exception as exc:
            results.append({
                "run_id": run_id,
                "status": "none",
                "error": str(exc),
            })
            errors += 1

    return {
        "total": len(results),
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
        "results": results,
    }


def ensure_human_gavel_template(note_path: Path) -> bool:
    """Ensure the Obsidian note has a ## Human Gavel block.

    Appends a template (status: draft) if missing. Returns True if block
    already existed, False if template was appended.
    """
    note_path = Path(note_path)

    if not note_path.exists():
        return False

    try:
        text = note_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False

    if _GAVEL_BLOCK_RE.search(text):
        return True  # Already exists

    template = """
## Human Gavel

status: draft
decision:
confidence:
reviewer:
reviewed_at:
accepted_claims:
- none
rejected_claims:
- none
corrections:
- none
notes:
"""

    try:
        note_path.write_text(text.rstrip() + template, encoding="utf-8")
    except Exception:
        return False

    return False


def _patch_gavel_json_field(run_dir: Path, field: str, value: Any) -> None:
    """Read gavel JSON, inject field, write back. No-op if JSON missing."""
    json_path = run_dir / "human-gavel.json"
    if not json_path.exists():
        return
    try:
        gavel = json.loads(json_path.read_text(encoding="utf-8"))
        gavel[field] = value
        json_path.write_text(
            json.dumps(gavel, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
# P4 — Change History
# ═══════════════════════════════════════════════════════════════════════

def write_human_gavel_history(
    run_dir: Path,
    old_gavel: dict[str, Any] | None,
    new_gavel: dict[str, Any],
    source_note: str,
) -> dict[str, Any]:
    """Append a change event to human-gavel-history.jsonl in run_dir.

    Compares old vs new gavel to identify changed_fields. Always writes
    a line, even when nothing changed (changed_fields: []).

    Args:
        run_dir: The run directory.
        old_gavel: Previous gavel dict or None for first sync.
        new_gavel: Current gavel dict.
        source_note: Path to the Obsidian note that triggered the sync.

    Returns:
        The history entry dict (the line written to JSONL).
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    run_id = new_gavel.get("run_id", run_dir.name)

    # Determine changed fields
    changed_fields: list[str] = []
    if old_gavel:
        for field in ("status", "decision", "confidence",
                       "accepted_claims", "rejected_claims",
                       "corrections", "notes"):
            old_val = old_gavel.get(field)
            new_val = new_gavel.get(field)
            # For lists, compare sorted
            if isinstance(old_val, list) and isinstance(new_val, list):
                if sorted(str(v) for v in old_val) != sorted(str(v) for v in new_val):
                    changed_fields.append(field)
            elif old_val != new_val:
                changed_fields.append(field)
    else:
        # First sync — mark all meaningful fields as changed
        changed_fields = ["status", "decision", "confidence",
                          "accepted_claims", "rejected_claims"]

    entry: dict[str, Any] = {
        "event": "human_gavel_synced",
        "run_id": run_id,
        "old_status": old_gavel.get("status", "") if old_gavel else "",
        "new_status": new_gavel.get("status", ""),
        "old_decision": old_gavel.get("decision", "") if old_gavel else "",
        "new_decision": new_gavel.get("decision", ""),
        "old_confidence": old_gavel.get("confidence") if old_gavel else None,
        "new_confidence": new_gavel.get("confidence"),
        "source_note": source_note,
        "synced_at": new_gavel.get("synced_at", datetime.now(timezone.utc).isoformat()),
        "changed_fields": changed_fields,
    }

    history_path = run_dir / "human-gavel-history.jsonl"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


# ═══════════════════════════════════════════════════════════════════════
# P4 — Conflict Detection
# ═══════════════════════════════════════════════════════════════════════

def _compute_note_gavel_hash(note_path: Path) -> str:
    """Compute SHA-256 of the ## Human Gavel block text (normalised)."""
    if not note_path.exists():
        return ""
    try:
        text = note_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    m = _GAVEL_BLOCK_RE.search(text)
    if not m:
        return ""

    # Normalise: strip leading/trailing whitespace per line
    block = "\n".join(line.strip() for line in m.group(1).splitlines())
    return hashlib.sha256(block.encode("utf-8")).hexdigest()


def check_gavel_conflict(
    run_dir: Path,
    note_path: Path,
) -> dict[str, Any]:
    """Detect whether the Obsidian note's Human Gavel block has diverged
    from the last-synced state stored in human-gavel.json.

    Args:
        run_dir: The run directory containing human-gavel.json.
        note_path: Path to the Obsidian run note.

    Returns:
        Dict with has_conflict, reason, note_hash, json_hash, last_synced_at.
    """
    run_dir = Path(run_dir)
    note_path = Path(note_path)

    gavel_json_path = run_dir / "human-gavel.json"

    if not gavel_json_path.exists():
        return {
            "has_conflict": False,
            "reason": "No gavel data",
            "note_hash": "",
            "json_hash": "",
            "last_synced_at": "",
        }

    try:
        gavel = json.loads(gavel_json_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "has_conflict": False,
            "reason": "Gavel JSON unreadable",
            "note_hash": "",
            "json_hash": "",
            "last_synced_at": "",
        }

    validation = gavel.get("validation", {})
    json_hash = validation.get("note_hash", "")
    note_hash = _compute_note_gavel_hash(note_path)
    last_synced = gavel.get("synced_at", "")

    if not json_hash:
        # Pre-P4 gavel: no hash stored, can't detect conflict
        return {
            "has_conflict": False,
            "reason": "No note_hash in gavel (pre-P4)",
            "note_hash": note_hash,
            "json_hash": "",
            "last_synced_at": last_synced,
        }

    if note_hash and note_hash != json_hash:
        return {
            "has_conflict": True,
            "reason": "Note modified after last sync",
            "note_hash": note_hash,
            "json_hash": json_hash,
            "last_synced_at": last_synced,
        }

    return {
        "has_conflict": False,
        "reason": "Clean (hash matches)" if note_hash else "Note not found or no gavel block",
        "note_hash": note_hash,
        "json_hash": json_hash,
        "last_synced_at": last_synced,
    }


# ═══════════════════════════════════════════════════════════════════════
# P4 — Claim-Level Mapping
# ═══════════════════════════════════════════════════════════════════════

def _normalize_claim_text(text: str) -> str:
    """Normalize claim text for fuzzy matching: lowercase, strip punctuation/spaces."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def map_gavel_claims(run_dir: Path, gavel: dict[str, Any]) -> dict[str, Any]:
    """Map accepted/rejected claims from the Human Gavel onto the
    top_claims in hermes-output.json using 4-layer matching.

    Matching priority (P5 upgrade):
      1. claim_id exact match
      2. top_claim_N format parse (e.g. top_claim_1 → index 0)
      3. index pure numeric parse (e.g. "1" → index 0)
      4. normalized text contains (lowercase, de-punctuated substring)

    Accepts both str (simple claim name) and dict (with claim_id/text) formats.

    Args:
        run_dir: The run directory.
        gavel: The human gavel dict (must contain accepted_claims and
               rejected_claims lists).

    Returns:
        Dict with accepted, rejected, unmatched, and warnings lists.
    """
    run_dir = Path(run_dir)

    hermes_path = run_dir / "hermes-output.json"
    if not hermes_path.exists():
        return {
            "accepted": [],
            "rejected": [],
            "unmatched": [],
            "warnings": ["hermes-output.json not found"],
        }

    try:
        hermes = json.loads(hermes_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "accepted": [],
            "rejected": [],
            "unmatched": [],
            "warnings": ["hermes-output.json unreadable"],
        }

    top_claims: list[dict[str, Any]] = hermes.get("top_claims", [])
    if not top_claims:
        return {
            "accepted": [],
            "rejected": [],
            "unmatched": [],
            "warnings": ["no top_claims in hermes-output"],
        }

    # Normalize all top_claims texts
    norm_texts: list[str] = []
    for c in top_claims:
        t = str(c.get("text", "") or c.get("claim", "") or c.get("title", ""))
        norm_texts.append(_normalize_claim_text(t))

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    warnings: list[str] = []

    # Track already-matched claim indices to detect multi-hit
    used_indices: set[int] = set()

    def _resolve_gavel_entry(entry: Any) -> tuple[str, str, str]:
        """Extract claim_id, reference, and normalized text from a gavel entry.
        Entry can be str (e.g. 'top_claim_1') or dict (with claim_id/text fields).
        Returns (claim_id, reference_str, normalized_text)."""
        if isinstance(entry, str):
            return ("", entry.strip(), _normalize_claim_text(entry))
        elif isinstance(entry, dict):
            eid = str(entry.get("claim_id", "")).strip()
            ref = str(entry.get("claim_reference", entry.get("reference", "") or "")).strip()
            txt = _normalize_claim_text(str(entry.get("text", entry.get("claim", "") or "")))
            return (eid, ref, txt)
        return ("", "", "")

    def _match_one(gavel_entry: Any, status_label: str) -> None:
        """Match a single gavel entry against all top_claims using 4-layer priority."""
        eid, ref, gtext = _resolve_gavel_entry(gavel_entry)
        if not eid and not ref and not gtext:
            unmatched.append({"entry": gavel_entry, "reason": "empty entry"})
            return

        hits: list[int] = []  # matching claim indices

        # Layer 1: claim_id exact match
        if eid:
            for i, c in enumerate(top_claims):
                cid = str(c.get("claim_id", "") or c.get("id", "")).strip()
                if cid and cid == eid:
                    if i not in used_indices:
                        hits.append(i)

        # Layer 2 & 3: top_claim_N or index from reference string
        if not hits and ref:
            m = re.match(r"top_claim_(\d+)", ref, re.IGNORECASE)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(top_claims) and idx not in used_indices:
                    hits.append(idx)
            else:
                try:
                    idx = int(ref) - 1
                    if 0 <= idx < len(top_claims) and idx not in used_indices:
                        hits.append(idx)
                except (ValueError, TypeError):
                    pass

        # Layer 4: normalized text contains
        if not hits and gtext:
            for i, nt in enumerate(norm_texts):
                if i in used_indices:
                    continue
                if gtext and nt and (gtext in nt or nt in gtext):
                    hits.append(i)

        if len(hits) == 0:
            unmatched.append({"entry": gavel_entry, "reason": "no match found"})
        elif len(hits) > 1:
            warnings.append(f"multi-hit for gavel entry '{ref or eid or str(gavel_entry)[:40]}': matched claims {[i+1 for i in hits]}")
            # Use first hit only
            idx = hits[0]
            used_indices.add(idx)
            c = top_claims[idx]
            result = {
                "claim_id": c.get("claim_id", c.get("id", "")),
                "index": idx + 1,
                "seat": c.get("seat", c.get("seat_name", "")),
                "text": c.get("text", c.get("claim", "")),
                "match_type": "multi_hit_first",
                "status": status_label,
            }
            if status_label == "accepted":
                accepted.append(result)
            else:
                rejected.append(result)
        else:
            idx = hits[0]
            used_indices.add(idx)
            c = top_claims[idx]

            # Determine match_type description
            match_type = "text"
            if eid and str(c.get("claim_id", c.get("id", ""))).strip() == eid:
                match_type = "claim_id"
            elif ref:
                if re.match(r"top_claim_\d+", ref, re.IGNORECASE):
                    match_type = "top_claim_N"
                elif re.match(r"\d+", ref):
                    match_type = "index"

            result = {
                "claim_id": c.get("claim_id", c.get("id", "")),
                "index": idx + 1,
                "seat": c.get("seat", c.get("seat_name", "")),
                "text": c.get("text", c.get("claim", "")),
                "match_type": match_type,
                "status": status_label,
            }
            if status_label == "accepted":
                accepted.append(result)
            else:
                rejected.append(result)

    for claim in gavel.get("accepted_claims", []):
        if isinstance(claim, str) and claim.strip().lower() == "none":
            continue
        _match_one(claim, "accepted")

    for claim in gavel.get("rejected_claims", []):
        if isinstance(claim, str) and claim.strip().lower() == "none":
            continue
        _match_one(claim, "rejected")

    return {
        "accepted": accepted,
        "rejected": rejected,
        "unmatched": unmatched,
        "warnings": warnings,
    }


# ═══════════════════════════════════════════════════════════════════════
# P4 — Review Digest
# ═══════════════════════════════════════════════════════════════════════

def generate_gavel_digest(
    runs_dir: Path,
    vault_dir: Path,
) -> dict[str, Any]:
    """Scan all runs for human-gavel data and produce a summary digest.

    Writes $VAULT/Indexes/gavel-review-digest.md (creating dirs if needed).

    Args:
        runs_dir: Directory containing all run subdirectories.
        vault_dir: Obsidian vault root (Indexes/ will be created inside).

    Returns:
        Digest dict with total_runs, status_counts, conflict info,
        recent history, claim summary, and digest_md_path.
    """
    runs_dir = Path(runs_dir)
    vault_dir = Path(vault_dir)

    status_counts: dict[str, int] = {
        "none": 0, "draft": 0, "confirmed": 0,
        "rejected": 0, "needs_review": 0,
    }
    conflict_count = 0
    confirmed_runs: list[dict[str, Any]] = []
    rejected_runs: list[dict[str, Any]] = []
    needs_review_runs: list[dict[str, Any]] = []
    conflict_runs: list[dict[str, Any]] = []
    total_accepted = 0
    total_rejected = 0
    total_unmatched = 0
    total_runs = 0

    # Collect history lines from all runs (latest 20)
    all_history: list[dict[str, Any]] = []

    if runs_dir.exists():
        for run_dir in sorted(runs_dir.iterdir()):
            if not run_dir.is_dir():
                continue

            total_runs += 1
            run_id = run_dir.name
            gavel_path = run_dir / "human-gavel.json"

            if not gavel_path.exists():
                status_counts["none"] = (status_counts.get("none", 0) or 0) + 1
                continue

            try:
                gavel = json.loads(gavel_path.read_text(encoding="utf-8"))
            except Exception:
                status_counts["none"] = (status_counts.get("none", 0) or 0) + 1
                continue

            status = gavel.get("status", "none")
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts[status] = 1

            # Conflict lookup
            conflict = gavel.get("conflict", {})
            has_conflict = conflict.get("has_conflict", False)
            if has_conflict:
                conflict_count += 1
                conflict_runs.append({
                    "run_id": run_id,
                    "status": status,
                    "reason": conflict.get("reason", ""),
                })

            # Claim review stats
            claim_review = gavel.get("claim_review", {})
            total_accepted += len(claim_review.get("accepted", []))
            total_rejected += len(claim_review.get("rejected", []))
            total_unmatched += len(claim_review.get("unmatched", []))

            # Collect runs by status
            entry = {
                "run_id": run_id,
                "status": status,
                "decision": gavel.get("decision", ""),
                "confidence": gavel.get("confidence"),
                "reviewed_at": gavel.get("reviewed_at", ""),
            }
            if status == "confirmed":
                confirmed_runs.append(entry)
            elif status == "rejected":
                rejected_runs.append(entry)
            elif status == "needs_review":
                needs_review_runs.append(entry)

            # Read history for this run
            hist_path = run_dir / "human-gavel-history.jsonl"
            if hist_path.exists():
                try:
                    for line in hist_path.read_text(encoding="utf-8").strip().splitlines():
                        if line.strip():
                            all_history.append(json.loads(line))
                except Exception:
                    pass

    # Sort history by synced_at descending, take latest 20
    all_history.sort(key=lambda h: h.get("synced_at", ""), reverse=True)
    recent_history = all_history[:20]

    # Write digest Markdown to vault
    indexes_dir = vault_dir / "Indexes"
    indexes_dir.mkdir(parents=True, exist_ok=True)
    digest_md_path = indexes_dir / "gavel-review-digest.md"

    now_iso = datetime.now(timezone.utc).isoformat()
    digest_lines: list[str] = [
        f"# Human Gavel Review Digest",
        f"",
        f"- **Generated**: {now_iso}",
        f"- **Total runs**: {total_runs}",
        f"",
        f"## Status Counts",
    ]
    for st in ["none", "draft", "confirmed", "rejected", "needs_review"]:
        digest_lines.append(f"- **{st}**: {status_counts.get(st, 0)}")

    digest_lines.append("")
    digest_lines.append(f"## Conflicts ({conflict_count})")
    if conflict_runs:
        for cr in conflict_runs:
            digest_lines.append(f"- `{cr['run_id']}` ({cr['status']}): {cr['reason']}")
    else:
        digest_lines.append("(none)")

    def _write_run_section(title: str, runs_list: list[dict[str, Any]]) -> None:
        digest_lines.append("")
        digest_lines.append(f"## {title} ({len(runs_list)})")
        if runs_list:
            for r in runs_list:
                conf_str = f", confidence: {r['confidence']}" if r.get("confidence") is not None else ""
                digest_lines.append(
                    f"- `{r['run_id']}`: {r.get('decision', '')}{conf_str}"
                )
        else:
            digest_lines.append("(none)")

    _write_run_section("Confirmed", confirmed_runs)
    _write_run_section("Rejected", rejected_runs)
    _write_run_section("Needs Review", needs_review_runs)

    digest_lines.append("")
    digest_lines.append("## Claim Summary")
    digest_lines.append(f"- **Total accepted**: {total_accepted}")
    digest_lines.append(f"- **Total rejected**: {total_rejected}")
    digest_lines.append(f"- **Total unmatched**: {total_unmatched}")

    digest_lines.append("")
    digest_lines.append("## Recent History (latest 20)")
    if recent_history:
        for h in recent_history:
            changed = ", ".join(h.get("changed_fields", [])) or "(none)"
            digest_lines.append(
                f"- `{h.get('run_id','')}` → `{h.get('new_status','')}` "
                f"(changed: {changed}) @ {h.get('synced_at','')}"
            )
    else:
        digest_lines.append("(none)")

    digest_md_path.write_text("\n".join(digest_lines) + "\n", encoding="utf-8")

    return {
        "total_runs": total_runs,
        "status_counts": status_counts,
        "conflict_count": conflict_count,
        "confirmed_runs": confirmed_runs,
        "rejected_runs": rejected_runs,
        "needs_review_runs": needs_review_runs,
        "conflict_runs": conflict_runs,
        "recent_history": recent_history,
        "claim_summary": {
            "total_accepted": total_accepted,
            "total_rejected": total_rejected,
            "total_unmatched": total_unmatched,
        },
        "digest_md_path": str(digest_md_path),
    }