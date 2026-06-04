#!/usr/bin/env python3
"""P8 Release Archive generator.

Generates:
  - {runs_dir}/release-archive-p8.json
  - {vault_dir}/Indexes/release-archive-p8.md

Usage:
  python3 release_archive.py \\
    --product-dir PRODUCT \\
    --runs-dir RUNS \\
    --vault-dir VAULT \\
    --run-id RUN_ID
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

BUILD_ID = "p8.2-release-shortcut-e2e-v1"
SAMPLE_RUN_ID = "1142374c8b6d"

CORE_APIS = [
    "/api/health",
    "/api/runs",
    "/api/runs/recent",
    "/api/runs/universe",
    "/api/judge/<run_id>/verdict",
    "/api/runs/<run_id>/index.html",
    "/api/runs/<run_id>/hermes-output.json",
    "/api/runs/<run_id>/summary",
    "/api/runs/<run_id>/stop",
    "/api/runs/<run_id>/resume",
    "/api/runs/<run_id>/trace",
    "/api/runs/<run_id>/events",
    "/api/hermes/index",
    "/api/hermes/seats",
    "/api/gavel/<run_id>",
    "/api/gavel/<run_id>/history",
    "/api/gavel/digest",
    "/api/claims/calibration",
    "/api/claims/calibration/<run_id>",
    "/api/trust/calibration",
    "/api/trust/seat/<seat_name>",
    "/api/decision/intelligence",
    "/api/release/readiness",
    "/api/release/regression",
    "/api/runs/release-readiness",
]

CORE_DOCUMENTS = [
    "RELEASE_ARCHIVE_P8.md",
    "OPERATOR_GUIDE.md",
    "ROLLBACK_GUIDE.md",
    "REGRESSION_CHECKLIST.md",
    "RELEASE_FREEZE_P8.md",
]

VAULT_INDEXES = [
    "Indexes/hermes-index.md",
    "Indexes/claim-calibration.md",
    "Indexes/run-universe.md",
    "Indexes/trust-calibration.md",
    "Indexes/gavel-review-digest.md",
    "Indexes/release-readiness.md",
    "Indexes/release-archive-p8.md",
]


def build_release_archive(product_dir, runs_dir, vault_dir, run_id):
    """Build release archive data structure."""
    readiness_path = Path(runs_dir) / "release-readiness.json"
    overall_status = "unknown"
    pass_count = fail_count = blockers_count = 0
    if readiness_path.exists():
        try:
            data = json.loads(readiness_path.read_text(encoding="utf-8"))
            overall_status = data.get("overall_status", "unknown")
            pass_count = data.get("pass_count", 0)
            fail_count = data.get("fail_count", 0)
            blockers_count = len(data.get("blockers", []))
        except (json.JSONDecodeError, OSError):
            pass

    archive = {
        "schema_version": "ai-judge-release-archive-p8-v1",
        "build_id": BUILD_ID,
        "sample_run_id": run_id,
        "overall_status": overall_status,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "blockers_count": blockers_count,
        "core_apis": CORE_APIS,
        "core_documents": CORE_DOCUMENTS,
        "vault_indexes": VAULT_INDEXES,
        "readiness_path": str(readiness_path),
        "product_dir": str(product_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return archive


def write_release_archive(archive, runs_dir, vault_dir):
    """Write archive to JSON and Markdown."""
    # JSON output
    json_path = Path(runs_dir) / "release-archive-p8.json"
    json_path.write_text(json.dumps(archive, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Wrote: {json_path}")

    # Markdown output
    vault_indexes = Path(vault_dir) / "Indexes"
    vault_indexes.mkdir(parents=True, exist_ok=True)
    md_path = vault_indexes / "release-archive-p8.md"

    status_emoji = "✅" if archive["overall_status"] == "pass" else "❌"
    md = f"""# AI Judge P8 Release Archive

## Identity
- **Build ID**: `{archive['build_id']}`
- **Sample Run**: `{archive['sample_run_id']}`
- **Overall Status**: {status_emoji} **{archive['overall_status'].upper()}**
- **Pass/Fail**: {archive['pass_count']}/{archive['fail_count']}
- **Blockers**: {archive['blockers_count']}
- **Generated**: {archive['generated_at']}

## Core APIs ({len(archive['core_apis'])})
"""
    for api in archive["core_apis"]:
        md += f"- `{api}`\n"

    md += f"\n## Documents ({len(archive['core_documents'])})\n"
    for doc in archive["core_documents"]:
        md += f"- {doc}\n"

    md += f"\n## Vault Indexes ({len(archive['vault_indexes'])})\n"
    for idx in archive["vault_indexes"]:
        md += f"- {idx}\n"

    md += "\n## Freeze Decision\n"
    if archive["overall_status"] == "pass":
        md += "P8 baseline frozen — all checks pass, blockers=0. Ready for handoff.\n"
    else:
        md += f"P8 baseline NOT frozen — {archive['blockers_count']} blocker(s) remain.\n"

    md_path.write_text(md, encoding="utf-8")
    print(f"  Wrote: {md_path}")

    return {"json": str(json_path), "md": str(md_path)}


def main():
    parser = argparse.ArgumentParser(description="P8 Release Archive Generator")
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    archive = build_release_archive(args.product_dir, args.runs_dir, args.vault_dir, args.run_id)
    paths = write_release_archive(archive, args.runs_dir, args.vault_dir)
    print(f"\nOverall: {archive['overall_status'].upper()}")
    print(f"  JSON: {paths['json']}")
    print(f"  MD:   {paths['md']}")


if __name__ == "__main__":
    main()
