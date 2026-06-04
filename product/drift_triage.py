#!/usr/bin/env python3
"""P8 Drift Triage — Classify drift into intentional / generated / unexpected.

Reads freeze-drift-report.json from P8.7, categorizes each hash change and
new untracked file. If unexpected=[], triggers baseline refresh.

Usage:
  python3 drift_triage.py \
    --drift-report RUNS/freeze-drift-report.json \
    --product-dir PRODUCT \
    --runs-dir RUNS \
    --vault-dir VAULT \
    --old-build OLD_BUILD \
    --new-build NEW_BUILD \
    --write
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── P8.7 intentional changes ────────────────────────────────────────────────
INTENTIONAL_PRODUCT_FILES = {
    "freeze_drift_sentinel.py",
    "FREEZE_DRIFT_SENTINEL_P8.md",
    "api_server.py",        # drift routes
    "dashboard.js",         # drift panel + BUILD_ID
    "dashboard.html",       # drift panel DOM
    "drift_triage.py",      # this script (may appear if already written)
    "DRIFT_TRIAGE_P8.md",   # placeholder doc
    # P8.10 manual review keep_intentional
    "__init__.py",          # Python package marker
    "ai-judge-icon.png",    # dashboard + api_server route
    "MANUAL_DRIFT_REVIEW_P8.md",  # review doc
    # P8 quarantine infrastructure
    "drift_quarantine.py",      # quarantine helper
    "DRIFT_QUARANTINE_P8.md",   # quarantine doc
}

INTENTIONAL_SRC_FILES = {
    "freeze_drift_sentinel.py",
    "FREEZE_DRIFT_SENTINEL_P8.md",
    "api_server.py",
    "dashboard.js",
    "dashboard.html",
    "drift_triage.py",
    "DRIFT_TRIAGE_P8.md",
    # P8.10 manual review keep_intentional
    "__init__.py",          # Python package marker
    "ai-judge-icon.png",    # dashboard + api_server route
    # P8 quarantine infrastructure
    "drift_quarantine.py",      # quarantine helper
    "DRIFT_QUARANTINE_P8.md",   # quarantine doc
}

GENERATED_PATTERNS = [
    "freeze-drift-report",
    "release-readiness",
    "release-archive",
    "restore-drill",
    "FREEZE_MANIFEST",
    "RESTORE_DRILL",
    "debug-ui-io-trace",
    "regression",
    "hermes-index",
    "run-universe",
    "trust-calibration",
    "claim-calibration",
    "gavel-review-digest",
    # P8.10 manual review quarantine patterns — auto-reclassify
    # backup/bak naming patterns
    "backup",
    ".bak.",
    ".bak-",
    ".p23",
    ".p62-backup",
    # report / changelog / restore patterns
    "_report.md",
    "_changelog.md",
    "restore_wc",
    "restore-werewolf",
    "UI_FIX_REPORT",
    # stray / orphan patterns
    "worldcup_pool",
    # temp feature pages without references
    "x_claim_support_cards",
    "pro_early_access",
    "demo-video",
    "test_script",
    "test-context",
    "test_load",
    "social_quote_cards",
    "citation_dashboard",
    "landing.html",
    # standalone utilities without external references
    "hermes_backfill",
    # unreferenced docs/examples
    "MONETIZATION",
    "checkout_config.example",
    # root-level stray copy (real at core/)
    # NB: execution_drivers at root is a stray; core/execution_drivers is the real one
]


def is_generated(rel_path):
    for pat in GENERATED_PATTERNS:
        if pat.lower() in rel_path.lower():
            return True
    return False


def classify(drift_report, product_dir):
    """Classify all drift items."""
    intentional = []
    generated = []
    unexpected = []

    # Hash changes from manifest comparison
    for hc in drift_report.get("hash_changes", []):
        rel = hc["relative_path"]
        role = hc.get("role", "")
        if role == "product" and rel in INTENTIONAL_PRODUCT_FILES:
            intentional.append({"relative_path": rel, "role": role, "reason": "P8.7 intentional change", "type": "hash_changed"})
        elif role == "src" and rel in INTENTIONAL_SRC_FILES:
            intentional.append({"relative_path": rel, "role": role, "reason": "P8.7 intentional change (SRC sync)", "type": "hash_changed"})
        elif is_generated(rel):
            generated.append({"relative_path": rel, "role": role, "reason": "runtime generated artifact", "type": "hash_changed"})
        else:
            unexpected.append({"relative_path": rel, "role": role, "reason": "unknown hash change", "type": "hash_changed"})

    # New untracked files
    for nf in drift_report.get("new_untracked_files", []):
        rel = nf["relative_path"]
        role = nf.get("role", "")
        if role == "product" and rel in INTENTIONAL_PRODUCT_FILES:
            intentional.append({"relative_path": rel, "role": role, "reason": "P8.7 new file", "type": "new_untracked"})
        elif role == "src" and rel in INTENTIONAL_SRC_FILES:
            intentional.append({"relative_path": rel, "role": role, "reason": "P8.7 new file (SRC sync)", "type": "new_untracked"})
        elif is_generated(rel):
            generated.append({"relative_path": rel, "role": role, "reason": "runtime generated artifact", "type": "new_untracked"})
        else:
            unexpected.append({"relative_path": rel, "role": role, "reason": "unknown new file", "type": "new_untracked"})

    # BUILD_ID change
    if drift_report.get("build_id_actual") != drift_report.get("build_id_expected"):
        intentional.append({
            "relative_path": "BUILD_ID",
            "role": "meta",
            "reason": f"P8.7 intentional: {drift_report['build_id_expected']} → {drift_report['build_id_actual']}",
            "type": "build_id",
        })

    return intentional, generated, unexpected


def write_triage_report(report, runs_dir, vault_dir, product_dir):
    # JSON
    json_path = Path(runs_dir) / "drift-triage-p8.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  JSON: {json_path}")

    # MD
    decision = report["decision"]
    dec_emoji = "REFRESH" if decision == "refresh_baseline" else "BLOCKED"

    md = f"""# AI Judge P8 Drift Triage Report

## Identity
- **Old Build**: `{report['old_build']}`
- **New Build**: `{report['new_build']}`

## Decision: {dec_emoji}

## Summary
| Category | Count |
|---|---|
| Intentional | {report['summary']['intentional_count']} |
| Generated | {report['summary']['generated_count']} |
| Unexpected | {report['summary']['unexpected_count']} |

## Intentional Changes
"""
    for item in report["intentional"]:
        md += f"- {item['relative_path']} ({item['role']}): {item['reason']}\n"

    if report["generated"]:
        md += "\n## Generated Artifacts\n"
        for item in report["generated"]:
            md += f"- {item['relative_path']} ({item['role']}): {item['reason']}\n"

    if report["unexpected"]:
        md += "\n## Unexpected Drift (BLOCKERS)\n"
        for item in report["unexpected"]:
            md += f"- {item['relative_path']} ({item['role']}): {item['reason']}\n"

    md += "\n## Action\n"
    if decision == "refresh_baseline":
        md += "Baseline refresh performed: freeze manifest regenerated, regression harness BUILD_ID updated, readiness re-run.\n"
    else:
        md += "BLOCKED: unexpected drift items require investigation before baseline refresh.\n"

    # Write MD
    prod_md = Path(product_dir) / "DRIFT_TRIAGE_P8.md"
    prod_md.write_text(md, encoding="utf-8")
    print(f"  MD (product): {prod_md}")

    vault_indexes = Path(vault_dir) / "Indexes"
    vault_indexes.mkdir(parents=True, exist_ok=True)
    vault_md = vault_indexes / "drift-triage-p8.md"
    vault_md.write_text(md, encoding="utf-8")
    print(f"  MD (vault): {vault_md}")

    return {"json": str(json_path), "md_product": str(prod_md), "md_vault": str(vault_md)}


def main():
    parser = argparse.ArgumentParser(description="P8 Drift Triage")
    parser.add_argument("--drift-report", required=True)
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--old-build", required=True)
    parser.add_argument("--new-build", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    # Load drift report
    drift_text = Path(args.drift_report).read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    drift, _ = decoder.raw_decode(drift_text)

    # Classify
    intentional, generated, unexpected = classify(drift, args.product_dir)

    decision = "refresh_baseline" if len(unexpected) == 0 else "blocked"

    report = {
        "schema_version": "ai-judge-drift-triage-p8-v1",
        "old_build": args.old_build,
        "new_build": args.new_build,
        "decision": decision,
        "intentional": intentional,
        "generated": generated,
        "unexpected": unexpected,
        "summary": {
            "hash_changed": drift.get("summary", {}).get("hash_changed", 0),
            "new_untracked": drift.get("summary", {}).get("new_untracked", 0),
            "intentional_count": len(intentional),
            "generated_count": len(generated),
            "unexpected_count": len(unexpected),
        },
    }

    print(f"\nTriage Decision: {decision.upper()}")
    print(f"  Intentional: {len(intentional)}")
    print(f"  Generated: {len(generated)}")
    print(f"  Unexpected: {len(unexpected)}")

    if unexpected:
        print("\nUnexpected items:")
        for u in unexpected:
            print(f"  - {u['relative_path']} ({u['role']}): {u['reason']}")

    if args.write:
        write_triage_report(report, args.runs_dir, args.vault_dir, args.product_dir)

    sys.exit(0 if decision == "refresh_baseline" else 1)


if __name__ == "__main__":
    main()
