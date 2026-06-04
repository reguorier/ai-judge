#!/usr/bin/env python3
"""P8 Freeze Manifest & Backup Verification.

Generates:
  - {runs_dir}/FREEZE_MANIFEST_P8.json
  - {vault_dir}/Indexes/FREEZE_MANIFEST_P8.md
  - {product_dir}/FREEZE_MANIFEST_P8.md
  - {backup_root}/p8-freeze-{timestamp}/ (code + release docs snapshot)

Usage:
  python3 freeze_manifest.py \\
    --product-dir PRODUCT \\
    --src-dir SRC \\
    --runs-dir RUNS \\
    --vault-dir VAULT \\
    --backup-root BACKUP_ROOT \\
    --build-id BUILD_ID \\
    --write \\
    --verify
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BUILD_ID_DEFAULT = "p8.2-release-shortcut-e2e-v1"
HASH_ALGORITHM = "sha256"


# ── Required files inventory ─────────────────────────────────────────────────
REQUIRED_PRODUCT_FILES = [
    "api_server.py",
    "dashboard.js",
    "dashboard.html",
    "hermes_output_layer.py",
    "hermes_index_layer.py",
    "human_gavel_layer.py",
    "claim_calibration_layer.py",
    "run_universe_layer.py",
    "trust_calibration_layer.py",
    "regression_harness.py",
    "release_readiness.py",
    "release_archive.py",
    "RELEASE_ARCHIVE_P8.md",
    "OPERATOR_GUIDE.md",
    "ROLLBACK_GUIDE.md",
    "REGRESSION_CHECKLIST.md",
    "RELEASE_FREEZE_P8.md",
]

REQUIRED_RUNS_FILES = [
    "release-readiness.json",
    "release-archive-p8.json",
    "hermes-index.json",
    "run-universe.json",
    "trust-calibration.json",
    "claim-calibration-index.json",
]

REQUIRED_VAULT_FILES = [
    "Indexes/release-readiness.md",
    "Indexes/release-archive-p8.md",
    "Indexes/run-universe.md",
    "Indexes/trust-calibration.md",
    "Indexes/claim-calibration.md",
    "Indexes/hermes-index.md",
    "Indexes/gavel-review-digest.md",
]


def _sha256(path):
    """Return SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_files(base_dir, file_list, role):
    """Scan files with SHA256. Missing files still included with size=-1, sha256=''."""
    entries = []
    for rel in file_list:
        fp = Path(base_dir) / rel
        if fp.is_file():
            entries.append({
                "path": str(fp),
                "relative_path": rel,
                "role": role,
                "size": fp.stat().st_size,
                "sha256": _sha256(fp),
            })
        else:
            entries.append({
                "path": str(fp),
                "relative_path": rel,
                "role": role,
                "size": -1,
                "sha256": "",
            })
    return entries


def build_freeze_manifest(product_dir, src_dir, runs_dir, vault_dir, backup_root, build_id):
    """Build the full freeze manifest."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(backup_root) / f"p8-freeze-{timestamp}"

    # Read readiness
    readiness_path = Path(runs_dir) / "release-readiness.json"
    readiness = {"overall_status": "unknown", "blockers": []}
    if readiness_path.is_file():
        try:
            data = json.loads(readiness_path.read_text(encoding="utf-8"))
            readiness["overall_status"] = data.get("overall_status", "unknown")
            readiness["blockers"] = data.get("blockers", [])
        except (json.JSONDecodeError, OSError):
            pass

    # Scan all files
    files = []
    files.extend(_scan_files(product_dir, REQUIRED_PRODUCT_FILES, "product"))
    files.extend(_scan_files(src_dir, REQUIRED_PRODUCT_FILES, "src"))
    files.extend(_scan_files(runs_dir, REQUIRED_RUNS_FILES, "runs"))
    files.extend(_scan_files(vault_dir, REQUIRED_VAULT_FILES, "vault"))

    manifest = {
        "schema_version": "ai-judge-freeze-manifest-p8-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "build_id": build_id,
        "freeze_label": "p8-freeze",
        "product_dir": str(product_dir),
        "src_dir": str(src_dir),
        "runs_dir": str(runs_dir),
        "vault_dir": str(vault_dir),
        "backup_dir": str(backup_dir),
        "files": files,
        "hash_algorithm": HASH_ALGORITHM,
        "release_readiness": readiness,
        "verification": {"ok": True, "missing_files": [], "hash_mismatches": []},
    }

    # Verification pass
    missing = [f["relative_path"] for f in files if f["size"] == -1]
    manifest["verification"]["missing_files"] = missing
    manifest["verification"]["ok"] = len(missing) == 0

    return manifest


def write_freeze_manifest(manifest, product_dir, runs_dir, vault_dir):
    """Write manifest to JSON and two MD locations."""
    # JSON
    json_path = Path(runs_dir) / "FREEZE_MANIFEST_P8.json"
    json_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  JSON: {json_path}")

    # MD content
    total_files = len(manifest["files"])
    present = sum(1 for f in manifest["files"] if f["size"] != -1)
    missing = sum(1 for f in manifest["files"] if f["size"] == -1)
    status_emoji = "✅" if manifest["verification"]["ok"] else "❌"

    md = f"""# AI Judge P8 Freeze Manifest

## Identity
- **Schema**: {manifest['schema_version']}
- **Build ID**: `{manifest['build_id']}`
- **Freeze Label**: {manifest['freeze_label']}
- **Generated**: {manifest['generated_at']}

## Verification: {status_emoji} {'PASS' if manifest['verification']['ok'] else 'FAIL'}
- **Files**: {present}/{total_files} present, {missing} missing
- **Algorithm**: {HASH_ALGORITHM}
- **Backup**: {manifest['backup_dir']}

## Readiness
- **Overall Status**: {manifest['release_readiness']['overall_status'].upper()}
- **Blockers**: {len(manifest['release_readiness']['blockers'])}

## File Inventory

| Relative Path | Role | Size | SHA256 |
|---|---|---|---|
"""
    for f in manifest["files"]:
        size_str = str(f["size"]) if f["size"] != -1 else "MISSING"
        sha_short = f["sha256"][:16] + "..." if f["sha256"] else "—"
        md += f"| {f['relative_path']} | {f['role']} | {size_str} | {sha_short} |\n"

    if manifest["verification"]["missing_files"]:
        md += "\n## Missing Files\n"
        for mf in manifest["verification"]["missing_files"]:
            md += f"- {mf}\n"

    md += "\n## Recovery Note\n"
    md += "Backup snapshot at `{manifest['backup_dir']}` contains code + release docs. "
    md += "Runs and Vault data directories are NOT included — those must be preserved separately.\n"

    # Write to two locations
    prod_md = Path(product_dir) / "FREEZE_MANIFEST_P8.md"
    prod_md.write_text(md, encoding="utf-8")
    print(f"  MD (product): {prod_md}")

    vault_indexes = Path(vault_dir) / "Indexes"
    vault_indexes.mkdir(parents=True, exist_ok=True)
    vault_md = vault_indexes / "FREEZE_MANIFEST_P8.md"
    vault_md.write_text(md, encoding="utf-8")
    print(f"  MD (vault): {vault_md}")

    return {"json": str(json_path), "md_product": str(prod_md), "md_vault": str(vault_md)}


def do_backup(manifest):
    """Copy code + docs to backup_dir. Does not copy runs/vault data directories."""
    backup_dir = Path(manifest["backup_dir"])
    if backup_dir.exists():
        print(f"  Backup dir exists, creating fresh: {backup_dir}")
        shutil.rmtree(backup_dir)

    # product/ — only the listed product files (code + docs), not entire directory
    product_dst = backup_dir / "product"
    product_dst.mkdir(parents=True, exist_ok=True)
    for f in manifest["files"]:
        if f["role"] in ("product", "src") and f["size"] != -1:
            dst = product_dst / f["relative_path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f["path"], dst)

    # src/ — same file list, copied from src_dir
    src_dst = backup_dir / "src"
    src_dst.mkdir(parents=True, exist_ok=True)
    src_dir = Path(manifest["src_dir"])
    for rel in REQUIRED_PRODUCT_FILES:
        src_path = src_dir / rel
        if src_path.is_file():
            dst = src_dst / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_path), str(dst))

    # docs/ — MD documents
    docs_dst = backup_dir / "docs"
    docs_dst.mkdir(parents=True, exist_ok=True)
    for f in manifest["files"]:
        if f["role"] in ("runs", "vault") and f["relative_path"].endswith(".md") and f["size"] != -1:
            # Only copy MD docs from runs/vault that are release-related
            name = Path(f["relative_path"]).name
            if "release" in name.lower() or "freeze" in name.lower() or "archive" in name.lower():
                dst = docs_dst / name
                shutil.copy2(f["path"], dst)

    # manifest/
    manifest_dst = backup_dir / "manifest"
    manifest_dst.mkdir(parents=True, exist_ok=True)
    json_src = Path(manifest["runs_dir"]) / "FREEZE_MANIFEST_P8.json"
    if json_src.is_file():
        shutil.copy2(str(json_src), str(manifest_dst / "FREEZE_MANIFEST_P8.json"))

    print(f"  Backup created at: {backup_dir}")
    return str(backup_dir)


def verify_freeze_manifest(manifest):
    """Re-verify all files exist and hashes match. Returns updated manifest."""
    missing = []
    mismatches = []
    for f in manifest["files"]:
        fp = Path(f["path"])
        if not fp.is_file():
            missing.append(f["relative_path"])
        elif f["sha256"]:
            current = _sha256(fp)
            if current != f["sha256"]:
                mismatches.append({"relative_path": f["relative_path"], "expected": f["sha256"], "actual": current})

    manifest["verification"]["missing_files"] = missing
    manifest["verification"]["hash_mismatches"] = mismatches
    manifest["verification"]["ok"] = (len(missing) == 0 and len(mismatches) == 0)

    if manifest["verification"]["ok"]:
        print("  Verification: PASS — all files present, all hashes match")
    else:
        if missing:
            print(f"  Missing files: {missing}")
        if mismatches:
            print(f"  Hash mismatches: {[m['relative_path'] for m in mismatches]}")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="P8 Freeze Manifest Generator")
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--src-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--backup-root", required=True)
    parser.add_argument("--build-id", default=BUILD_ID_DEFAULT)
    parser.add_argument("--write", action="store_true", help="Write manifest files + create backup")
    parser.add_argument("--verify", action="store_true", help="Re-verify after generation")
    args = parser.parse_args()

    manifest = build_freeze_manifest(
        args.product_dir, args.src_dir, args.runs_dir, args.vault_dir,
        args.backup_root, args.build_id,
    )

    if args.write:
        write_freeze_manifest(manifest, args.product_dir, args.runs_dir, args.vault_dir)
        do_backup(manifest)

    if args.verify:
        manifest = verify_freeze_manifest(manifest)

    print(f"\nBuild: {manifest['build_id']}")
    print(f"Files: {sum(1 for f in manifest['files'] if f['size'] != -1)}/{len(manifest['files'])} present")
    print(f"Readiness: {manifest['release_readiness']['overall_status']}")
    print(f"Verification: {'PASS' if manifest['verification']['ok'] else 'FAIL'}")

    sys.exit(0 if manifest["verification"]["ok"] else 1)


if __name__ == "__main__":
    main()
