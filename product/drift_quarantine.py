#!/usr/bin/env python3
"""P8 Drift Quarantine — Safely isolate unexpected drift files.

Moves unexpected files from PRODUCT/SRC into a quarantine directory,
preserving relative paths. Never deletes. Never touches RUNS/VAULT.

Usage:
  # dry-run first
  python3 drift_quarantine.py --triage TRIAGE_JSON --product-dir P --src-dir S --quarantine-root Q --dry-run
  # execute
  python3 drift_quarantine.py --triage TRIAGE_JSON --product-dir P --src-dir S --quarantine-root Q --runs-dir R --vault-dir V --write
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Auto-quarantine patterns ─────────────────────────────────────────────────
AUTO_QUARANTINE_PATTERNS = [
    "*.bak",
    "*.bak-*",
    "*.backup",
    "*.backup-*",
    "*.tmp",
    "*.old",
    "test_*.js",
    "test_*.html",
    "test-*.md",
    "restore-*.sh",
    "demo-*.html",
    "*_test.html",
]

AUTO_QUARANTINE_NAMES = {
    "demo-video.html",
    "landing.html",
    "worldcup_pool.html",
    "citation_dashboard.html",
    "social_quote_cards.html",
}

MANUAL_REVIEW_NAMES = {
    "checkout_config.example.json",
    "MONETIZATION.md",
    "ai-judge-icon.png",
}


def matches_auto(filename):
    """Check if filename matches any auto-quarantine pattern."""
    if filename in AUTO_QUARANTINE_NAMES:
        return True
    import fnmatch
    for pat in AUTO_QUARANTINE_PATTERNS:
        if fnmatch.fnmatch(filename, pat):
            return True
    return False


def is_manual_review(filename):
    return filename in MANUAL_REVIEW_NAMES


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_triage(path):
    text = Path(path).read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    triage, _ = decoder.raw_decode(text)
    return triage


def resolve_path(base_dir, relative_path, role):
    """Map role+relative_path to absolute source path."""
    if role in ("product", "runtime"):
        base = base_dir["product"]
    elif role == "src":
        base = base_dir["src"]
    else:
        return None
    return str(Path(base) / relative_path)


def plan_quarantine(triage, product_dir, src_dir):
    """Build quarantine plan from triage unexpected items."""
    base = {"product": product_dir, "src": src_dir}
    moved = []
    manual_review = []

    for item in triage.get("unexpected", []):
        rel = item["relative_path"]
        role = item.get("role", "")
        fname = Path(rel).name
        src_path = resolve_path(base, rel, role)

        if not src_path or not os.path.exists(src_path):
            continue  # already gone

        if matches_auto(fname):
            moved.append({
                "relative_path": rel,
                "role": role,
                "filename": fname,
                "source_path": src_path,
                "size": os.path.getsize(src_path),
                "sha256": sha256_file(src_path),
                "reason": f"auto-quarantine: matches pattern or known name '{fname}'",
            })
        elif is_manual_review(fname):
            manual_review.append({
                "relative_path": rel,
                "role": role,
                "filename": fname,
                "source_path": src_path,
                "size": os.path.getsize(src_path),
                "reason": "manual review: config/asset/media file — verify not referenced before quarantining",
            })
        else:
            # Default: manual review for anything not matching auto patterns
            manual_review.append({
                "relative_path": rel,
                "role": role,
                "filename": fname,
                "source_path": src_path,
                "size": os.path.getsize(src_path),
                "reason": f"manual review: no auto-quarantine rule matches '{fname}'",
            })

    return {
        "moved": moved,
        "manual_review": manual_review,
        "planned_count": len(moved) + len(manual_review),
        "moved_count_planned": len(moved),
        "manual_review_count": len(manual_review),
    }


def execute_quarantine(plan, quarantine_root, dry_run=False):
    """Move planned files to quarantine directory."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    qdir = Path(quarantine_root) / f"p8-unexpected-drift-{ts}"
    if not dry_run:
        qdir.mkdir(parents=True, exist_ok=True)

    results = []
    for m in plan["moved"]:
        dest_rel = Path(m["role"]) / m["relative_path"]
        dest = qdir / dest_rel
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Handle name collision
            if dest.exists():
                from datetime import datetime as dt_local
                stamp = dt_local.now().strftime("%Y%m%d%H%M%S")
                dest = dest.with_stem(f"{dest.stem}_{stamp}")
            shutil.move(m["source_path"], str(dest))
        results.append({
            **m,
            "quarantine_path": str(dest),
            "moved": not dry_run,
        })

    return {
        "quarantine_dir": str(qdir),
        "moved": results,
        "moved_count": len(results),
    }


def write_quarantine_report(report, runs_dir, vault_dir):
    json_path = Path(runs_dir) / "drift-quarantine-p8.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  JSON: {json_path}")

    md = f"""# AI Judge P8 Drift Quarantine Report

## Summary
- **Planned**: {report['planned_count']}
- **Moved**: {report['moved_count']}
- **Manual Review**: {report['manual_review_count']}
- **Quarantine Dir**: `{report['quarantine_dir']}`

## Safety
- **Deleted files**: {report['safety']['deleted_files']}
- **Touched runs**: {report['safety']['touched_runs']}
- **Touched vault**: {report['safety']['touched_vault']}
"""
    if report["moved"]:
        md += "\n## Moved Files\n"
        for m in report["moved"]:
            md += f"- `{m['relative_path']}` ({m['role']}) → `{m.get('quarantine_path', 'DRY-RUN')}` [{m['size']} bytes]\n"

    if report["manual_review"]:
        md += "\n## Manual Review Required\n"
        for mr in report["manual_review"]:
            md += f"- `{mr['relative_path']}` ({mr['role']}): {mr['reason']}\n"

    vault_indexes = Path(vault_dir) / "Indexes"
    vault_indexes.mkdir(parents=True, exist_ok=True)
    vault_md = vault_indexes / "drift-quarantine-p8.md"
    vault_md.write_text(md, encoding="utf-8")
    print(f"  MD (vault): {vault_md}")

    return {"json": str(json_path), "md_vault": str(vault_md)}


def main():
    parser = argparse.ArgumentParser(description="P8 Drift Quarantine")
    parser.add_argument("--triage", required=True, help="Path to drift-triage-p8.json")
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--src-dir", required=True)
    parser.add_argument("--quarantine-root", required=True)
    parser.add_argument("--runs-dir", default="")
    parser.add_argument("--vault-dir", default="")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, do not move")
    parser.add_argument("--write", action="store_true", help="Execute quarantine + write report")
    args = parser.parse_args()

    triage = load_triage(args.triage)
    plan = plan_quarantine(triage, args.product_dir, args.src_dir)

    print(f"\nQuarantine Plan ({'DRY RUN' if args.dry_run else 'EXECUTE'}):")
    print(f"  Auto-quarantine (movable): {plan['moved_count_planned']}")
    for m in plan["moved"]:
        print(f"    - {m['relative_path']} ({m['role']}) [{m['size']} bytes]")
    print(f"  Manual review: {plan['manual_review_count']}")
    for mr in plan["manual_review"]:
        print(f"    - {mr['relative_path']} ({mr['role']}): {mr['reason']}")

    if args.dry_run:
        print("\nDry run complete. No files moved.")
        return

    if args.write:
        result = execute_quarantine(plan, args.quarantine_root, dry_run=False)

        report = {
            "schema_version": "ai-judge-drift-quarantine-p8-v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_triage": args.triage,
            "quarantine_dir": result["quarantine_dir"],
            "planned_count": plan["planned_count"],
            "moved_count": result["moved_count"],
            "manual_review_count": plan["manual_review_count"],
            "moved": result["moved"],
            "manual_review": plan["manual_review"],
            "safety": {
                "deleted_files": False,
                "touched_runs": False,
                "touched_vault": False,
            },
        }

        write_quarantine_report(report, args.runs_dir, args.vault_dir)


if __name__ == "__main__":
    main()
