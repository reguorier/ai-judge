#!/usr/bin/env python3
"""P8 Restore Drill — Dry-run recovery from freeze backup.

Reads FREEZE_MANIFEST_P8.json, copies backup to isolated restore workspace,
verifies file existence + SHA256, compares current product/src against manifest,
generates restore drill report (JSON + 2×MD). Never overwrites current runtime.

Usage:
  python3 restore_drill.py \
    --manifest RUNS/FREEZE_MANIFEST_P8.json \
    --backup-dir BACKUP_DIR \
    --restore-root RESTORE_ROOT \
    --product-dir PRODUCT \
    --src-dir SRC \
    --runs-dir RUNS \
    --vault-dir VAULT \
    --run-id RUN_ID \
    --port PORT \
    --trace TRACE
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_backup_structure(backup_dir):
    """Check that backup_dir has the expected subdirectories and files."""
    bp = Path(backup_dir)
    expected_dirs = ["product", "src", "docs", "manifest"]
    result = {"ok": True, "missing_dirs": [], "dirs_found": [], "file_counts": {}}

    for d in expected_dirs:
        dp = bp / d
        if dp.is_dir():
            files = list(dp.iterdir())
            result["dirs_found"].append(d)
            result["file_counts"][d] = len(files)
        else:
            result["missing_dirs"].append(d)
            result["ok"] = False

    print(f"  Backup structure: {result['dirs_found']} found, {result['missing_dirs']} missing")
    return result


def verify_backup_hashes(manifest, backup_dir):
    """Compare backup product/ files against manifest SHA256 values."""
    bp = Path(backup_dir)
    missing = []
    mismatches = []

    for f in manifest.get("files", []):
        if f["role"] not in ("product", "src"):
            continue
        backup_file = bp / "product" / f["relative_path"]
        if not backup_file.is_file():
            missing.append(f["relative_path"])
        elif f["sha256"]:
            actual = _sha256(backup_file)
            if actual != f["sha256"]:
                mismatches.append({
                    "relative_path": f["relative_path"],
                    "expected": f["sha256"],
                    "actual": actual,
                })

    ok = len(missing) == 0 and len(mismatches) == 0
    print(f"  Backup hashes: {'PASS' if ok else 'FAIL'} — {len(missing)} missing, {len(mismatches)} mismatches")
    return {"ok": ok, "missing": missing, "mismatches": mismatches}


def copy_to_restore_workspace(backup_dir, restore_workspace):
    """Copy product/src/docs/manifest from backup to restore workspace."""
    ws = Path(restore_workspace)
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True, exist_ok=True)

    bp = Path(backup_dir)
    for sub in ["product", "src", "docs", "manifest"]:
        src = bp / sub
        if src.is_dir():
            dst = ws / sub
            shutil.copytree(str(src), str(dst))
            print(f"  Copied {sub}/ → {dst}")

    return str(ws)


def verify_workspace_hashes(manifest, restore_workspace):
    """Verify all product/src files in restore workspace match manifest hashes."""
    ws = Path(restore_workspace)
    missing = []
    mismatches = []

    for f in manifest.get("files", []):
        if f["role"] not in ("product", "src"):
            continue
        ws_file = ws / "product" / f["relative_path"]
        if not ws_file.is_file():
            missing.append(f["relative_path"])
        elif f["sha256"]:
            actual = _sha256(ws_file)
            if actual != f["sha256"]:
                mismatches.append({
                    "relative_path": f["relative_path"],
                    "expected": f["sha256"],
                    "actual": actual,
                })

    ok = len(missing) == 0 and len(mismatches) == 0
    print(f"  Workspace hashes: {'PASS' if ok else 'FAIL'}")
    return {"ok": ok, "missing": missing, "mismatches": mismatches}


def compare_current_to_manifest(manifest, product_dir, src_dir):
    """Compare current PRODUCT and SRC files against manifest hashes."""
    drift = []
    product_dir = Path(product_dir)
    src_dir = Path(src_dir)

    for f in manifest.get("files", []):
        if f["role"] == "product":
            cur = product_dir / f["relative_path"]
        elif f["role"] == "src":
            cur = src_dir / f["relative_path"]
        else:
            continue

        if cur.is_file() and f["sha256"]:
            actual = _sha256(cur)
            if actual != f["sha256"]:
                drift.append({
                    "relative_path": f["relative_path"],
                    "role": f["role"],
                    "manifest_sha256": f["sha256"],
                    "current_sha256": actual,
                })

    matches = len(drift) == 0
    if matches:
        print("  Current vs manifest: MATCH — no drift detected")
    else:
        print(f"  Current vs manifest: DRIFT — {len(drift)} files differ")
        for d in drift:
            print(f"    {d['relative_path']} ({d['role']})")

    return {"matches": matches, "drift": drift}


def run_readiness(product_dir, runs_dir, vault_dir, run_id, port, trace):
    """Run release_readiness.py and return status."""
    cmd = [
        sys.executable,
        str(Path(product_dir) / "release_readiness.py"),
        "--runs-dir", str(runs_dir),
        "--vault-dir", str(vault_dir),
        "--run-id", run_id,
        "--port", port,
        "--trace", trace,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        print(f"  Readiness: exit={result.returncode}")

        # Parse from output
        overall_status = "unknown"
        blockers = 0
        for line in output.splitlines():
            if line.startswith("Overall:"):
                overall_status = line.split(":")[1].strip().lower()
            if "Blockers:" in line:
                try:
                    blockers = int(line.split("Blockers:")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass

        return {"overall_status": overall_status, "blockers": blockers, "exit_code": result.returncode}
    except Exception as e:
        print(f"  Readiness error: {e}")
        return {"overall_status": "error", "blockers": -1, "exit_code": -1}


def write_restore_drill_report(report, runs_dir, vault_dir, product_dir):
    """Write restore-drill-p8.json + 2× MD files."""
    # JSON
    json_path = Path(runs_dir) / "restore-drill-p8.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  JSON: {json_path}")

    # Build MD
    ws_ok = report["workspace_hashes_ok"]
    status_emoji = "✅" if ws_ok else "❌"

    md = f"""# AI Judge P8 Restore Drill Report

## Identity
- **Schema**: {report['schema_version']}
- **Generated**: {report['generated_at']}
- **Mode**: {report['mode']}
- **Manifest**: {report['manifest_path']}

## Summary: {status_emoji} {'RESTORABLE' if ws_ok else 'BLOCKED'}

| Check | Result |
|---|---|
| Backup structure | {'✅' if report['backup_structure_ok'] else '❌'} |
| Backup hashes | {'✅' if report['backup_hashes_ok'] else '❌'} |
| Workspace hashes | {'✅' if report['workspace_hashes_ok'] else '❌'} |
| Current matches manifest | {'✅' if report['current_matches_manifest'] else '⚠️ DRIFT'} |
| Readiness | {report['readiness_status'].upper()} |

## Safety
- **Overwrote current runtime**: {report['safety']['overwrote_current_runtime']}
- **Deleted runs or vault**: {report['safety']['deleted_runs_or_vault']}

## Restore Workspace
- **Path**: {report['restore_workspace']}

## Backup Structure
"""
    for d, count in report.get("backup_structure", {}).get("file_counts", {}).items():
        md += f"- **{d}/**: {count} files\n"

    if report.get("backup_structure", {}).get("missing_dirs"):
        md += "\n### Missing\n"
        for d in report["backup_structure"]["missing_dirs"]:
            md += f"- {d}\n"

    if report["missing_files"]:
        md += "\n## Missing Files\n"
        for mf in report["missing_files"]:
            md += f"- {mf}\n"

    if report["hash_mismatches"]:
        md += "\n## Hash Mismatches\n"
        for hm in report["hash_mismatches"]:
            md += f"- {hm['relative_path']}: expected {hm['expected'][:16]}..., actual {hm['actual'][:16]}...\n"

    if report["current_drift"]:
        md += "\n## Current Drift (not auto-fixed)\n"
        for d in report["current_drift"]:
            md += f"- {d['relative_path']} ({d['role']})\n"

    if report["restore_plan"]:
        md += "\n## Restore Plan\n"
        for step in report["restore_plan"]:
            md += f"- {step}\n"

    md += "\n## Recovery Note\n"
    md += "This is a dry-run drill. No current runtime files were modified. "
    md += "The restore workspace contains a verified snapshot that can be used for actual recovery if needed.\n"

    # Write MD to two locations
    prod_md = Path(product_dir) / "RESTORE_DRILL_P8.md"
    prod_md.write_text(md, encoding="utf-8")
    print(f"  MD (product): {prod_md}")

    vault_indexes = Path(vault_dir) / "Indexes"
    vault_indexes.mkdir(parents=True, exist_ok=True)
    vault_md = vault_indexes / "restore-drill-p8.md"
    vault_md.write_text(md, encoding="utf-8")
    print(f"  MD (vault): {vault_md}")

    return {"json": str(json_path), "md_product": str(prod_md), "md_vault": str(vault_md)}


def run_restore_drill(manifest_path, backup_dir, restore_root,
                      product_dir, src_dir, runs_dir, vault_dir,
                      run_id, port, trace):
    """Main restore drill function."""

    # Load manifest (use raw_decode to tolerate trailing content)
    raw = Path(manifest_path).read_text(encoding="utf-8")
    manifest, _ = json.JSONDecoder().raw_decode(raw)
    print(f"Loaded manifest: {manifest['build_id']}, {len(manifest['files'])} files")

    # 1. Verify backup structure
    backup_structure = verify_backup_structure(backup_dir)

    # 2. Verify backup hashes
    backup_hashes = verify_backup_hashes(manifest, backup_dir)

    # 3. Create restore workspace
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    restore_workspace = str(Path(restore_root) / f"p8-restore-dryrun-{timestamp}")
    copy_to_restore_workspace(backup_dir, restore_workspace)

    # 4. Verify workspace hashes
    workspace_hashes = verify_workspace_hashes(manifest, restore_workspace)

    # Save verification report to workspace
    verify_dir = Path(restore_workspace) / "verification"
    verify_dir.mkdir(parents=True, exist_ok=True)
    verify_report = {
        "backup_structure": backup_structure,
        "backup_hashes": backup_hashes,
        "workspace_hashes": workspace_hashes,
    }
    (verify_dir / "verification.json").write_text(
        json.dumps(verify_report, indent=2, ensure_ascii=False), encoding="utf-8")

    # 5. Compare current to manifest
    current_compare = compare_current_to_manifest(manifest, product_dir, src_dir)

    # 6. Run readiness
    readiness = run_readiness(product_dir, runs_dir, vault_dir, run_id, port, trace)

    # 7. Build report
    report = {
        "schema_version": "ai-judge-restore-drill-p8-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run_no_overwrite",
        "manifest_path": manifest_path,
        "backup_dir": backup_dir,
        "restore_workspace": restore_workspace,
        "backup_structure_ok": backup_structure["ok"],
        "backup_hashes_ok": backup_hashes["ok"],
        "workspace_hashes_ok": workspace_hashes["ok"],
        "current_matches_manifest": current_compare["matches"],
        "readiness_status": readiness["overall_status"],
        "missing_files": workspace_hashes.get("missing", []),
        "hash_mismatches": workspace_hashes.get("mismatches", []),
        "current_drift": current_compare["drift"],
        "restore_plan": [],
        "backup_structure": backup_structure,
        "safety": {
            "overwrote_current_runtime": False,
            "deleted_runs_or_vault": False,
        },
    }

    # Generate restore plan
    if not current_compare["matches"]:
        for d in current_compare["drift"]:
            report["restore_plan"].append(
                f"Restore {d['relative_path']} from backup (manifest {d['manifest_sha256'][:16]}... → current {d['current_sha256'][:16]}...)"
            )

    # 8. Write reports
    write_restore_drill_report(report, runs_dir, vault_dir, product_dir)

    # 9. Summary
    print(f"\n{'='*50}")
    print(f"Restore Drill: {'PASS' if workspace_hashes['ok'] else 'FAIL'}")
    print(f"  Backup structure: {'OK' if backup_structure['ok'] else 'FAIL'}")
    print(f"  Backup hashes: {'OK' if backup_hashes['ok'] else 'FAIL'}")
    print(f"  Workspace: {restore_workspace}")
    print(f"  Current drift: {len(current_compare['drift'])} files")
    print(f"  Readiness: {readiness['overall_status']}")

    return report


def main():
    parser = argparse.ArgumentParser(description="P8 Restore Drill")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--backup-dir", required=True)
    parser.add_argument("--restore-root", required=True)
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--src-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--trace", required=True)
    args = parser.parse_args()

    report = run_restore_drill(
        args.manifest, args.backup_dir, args.restore_root,
        args.product_dir, args.src_dir, args.runs_dir, args.vault_dir,
        args.run_id, args.port, args.trace,
    )

    ok = report["workspace_hashes_ok"] and report["backup_structure_ok"] and report["backup_hashes_ok"]
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
