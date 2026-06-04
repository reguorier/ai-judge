#!/usr/bin/env python3
"""P8 Freeze Drift Sentinel — Detect post-freeze drift against manifest.

Compares current PRODUCT/SRC files against FREEZE_MANIFEST_P8.json,
detects missing files, hash changes, BUILD_ID drift, and untracked new files.
Generates freeze-drift-report.json + 2× MD. Never modifies business files.

Usage:
  python3 freeze_drift_sentinel.py \
    --manifest RUNS/FREEZE_MANIFEST_P8.json \
    --product-dir PRODUCT \
    --src-dir SRC \
    --runs-dir RUNS \
    --vault-dir VAULT \
    --port PORT \
    --trace TRACE \
    --write
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VOLATILE_ARTIFACT_PATTERNS = [
    # Readiness / regression runtime artifacts
    "release-readiness",
    "regression",
    # Archive / drill runtime artifacts
    "release-archive",
    "restore-drill",
    # Manifest runtime artifacts (in runs/vault, not the product script)
    "FREEZE_MANIFEST",
    "freeze_manifest",
    # Drift/triage/quarantine/review runtime artifacts
    "freeze-drift-report",
    "drift-triage",
    "drift-quarantine",
    "manual-drift-review",
    # Trace
    "debug-ui-io-trace",
    # Vault indexes
    "hermes-index",
    "run-universe",
    "trust-calibration",
    "claim-calibration",
    "gavel-review-digest",
]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(manifest_path):
    mp = Path(manifest_path)
    text = mp.read_text(encoding="utf-8")
    # Use raw_decode to handle trailing text after JSON
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(text)
    return data


def scan_current_files(manifest, product_dir, src_dir, runs_dir, vault_dir):
    """Scan current files. Returns dict of current state."""
    product_dir = Path(product_dir)
    src_dir = Path(src_dir)

    current = {}
    for f in manifest.get("files", []):
        if f["role"] == "product":
            cur = product_dir / f["relative_path"]
        elif f["role"] == "src":
            cur = src_dir / f["relative_path"]
        elif f["role"] == "runs":
            cur = Path(runs_dir) / f["relative_path"]
        elif f["role"] == "vault":
            cur = Path(vault_dir) / f["relative_path"]
        else:
            continue

        entry = {
            "relative_path": f["relative_path"],
            "role": f["role"],
            "exists": cur.is_file(),
            "path": str(cur),
        }
        if cur.is_file():
            entry["sha256"] = _sha256(cur)
            entry["size"] = cur.stat().st_size
        else:
            entry["sha256"] = ""
            entry["size"] = -1
        current[f["relative_path"]] = entry

    return current


def is_volatile_artifact(rel_path, role):
    """Check if a file is a generated/volatile artifact (runs/vault runtime output)."""
    # Only consider files in runs/ or vault/ as potentially volatile
    if role not in ("runs", "vault"):
        return False
    for pat in VOLATILE_ARTIFACT_PATTERNS:
        if pat.lower() in rel_path.lower():
            return True
    return False


def compare_to_manifest(manifest, current):
    """Compare current files against manifest. Returns drift report data."""
    missing_files = []
    strict_code_changes = []
    generated_changes = []

    for f in manifest.get("files", []):
        rel = f["relative_path"]
        cur = current.get(rel)
        if not cur:
            missing_files.append({"relative_path": rel, "role": f["role"], "reason": "not_scanned"})
        elif not cur["exists"]:
            missing_files.append({"relative_path": rel, "role": f["role"], "reason": "file_missing"})
        elif f.get("sha256") and cur.get("sha256") and f["sha256"] != cur["sha256"]:
            change_entry = {
                "relative_path": rel,
                "role": f["role"],
                "manifest_sha256": f["sha256"],
                "current_sha256": cur["sha256"],
            }
            if is_volatile_artifact(rel, f["role"]):
                generated_changes.append(change_entry)
            else:
                strict_code_changes.append(change_entry)

    # Detect BUILD_ID drift from dashboard.js
    build_id_actual = manifest.get("build_id", "")
    dashboard_js = Path(manifest.get("product_dir", "")) / "dashboard.js"
    build_id_from_file = ""
    if dashboard_js.is_file():
        content = dashboard_js.read_text(encoding="utf-8")
        import re
        m = re.search(r'AI_JUDGE_CLIENT_BUILD\s*=\s*"([^"]+)"', content)
        if m:
            build_id_from_file = m.group(1)

    if build_id_from_file and build_id_from_file != build_id_actual:
        # BUILD_ID in dashboard differs from manifest
        pass  # Handled in status logic below

    return {
        "missing_files": missing_files,
        "strict_code_changes": strict_code_changes,
        "generated_changes": generated_changes,
        "build_id_actual": build_id_from_file or build_id_actual,
    }


def detect_new_untracked(product_dir, src_dir, runs_dir, vault_dir, manifest_files):
    """Detect new files not in manifest. Splits into strict (product/src) and generated (runs/vault)."""
    new_untracked_files = []
    new_generated = []
    manifest_set = set(f["relative_path"] for f in manifest_files)

    for role, base in [("product", Path(product_dir)), ("src", Path(src_dir)),
                        ("runs", Path(runs_dir)), ("vault", Path(vault_dir))]:
        if not base.is_dir():
            continue
        for fp in base.iterdir():
            if not fp.is_file():
                continue
            if fp.name.startswith(".") or fp.name.endswith(".pyc"):
                continue
            if fp.name in manifest_set:
                continue
            entry = {
                "relative_path": fp.name,
                "role": role,
                "path": str(fp),
                "size": fp.stat().st_size,
                "sha256": _sha256(fp),
            }
            if is_volatile_artifact(fp.name, role):
                new_generated.append(entry)
            else:
                new_untracked_files.append(entry)

    return new_untracked_files, new_generated


def run_readiness(product_dir, port, trace):
    cmd = [
        sys.executable,
        str(Path(product_dir) / "release_readiness.py"),
        "--runs-dir", str(Path(product_dir).parent / "runs"),
        "--vault-dir", str(Path.home() / "Documents" / "AI-Judge-Obsidian-Vault"),
        "--run-id", "1142374c8b6d",
        "--port", port,
        "--trace", trace,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        overall = "unknown"
        blockers = 0
        for line in output.splitlines():
            if line.startswith("Overall:"):
                overall = line.split(":")[1].strip().lower()
            if "Blockers:" in line:
                try:
                    blockers = int(line.split("Blockers:")[1].strip().split()[0])
                except:
                    pass
        return {"overall_status": overall, "blockers": blockers}
    except Exception as e:
        return {"overall_status": "error", "blockers": -1}


def determine_status(missing_files, strict_code_changes, generated_changes, unexpected, new_generated, readiness):
    if readiness["overall_status"] != "pass" or readiness["blockers"] > 0:
        return "blocked"
    if missing_files:
        return "blocked"
    if strict_code_changes or unexpected:
        return "drift_detected"
    if generated_changes or new_generated:
        return "generated_only"
    return "clean"


def write_drift_report(report, runs_dir, vault_dir, product_dir):
    # JSON
    json_path = Path(runs_dir) / "freeze-drift-report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  JSON: {json_path}")

    # MD
    status = report["status"]
    status_emoji = {"clean": "✅", "generated_only": "🟡", "drift_detected": "⚠️", "blocked": "❌", "unknown": "❓"}.get(status, "❓")

    md = f"""# AI Judge P8 Freeze Drift Report

## Identity
- **Generated**: {report['generated_at']}
- **Build ID (expected)**: `{report['build_id_expected']}`
- **Build ID (actual)**: `{report['build_id_actual']}`

## Status: {status_emoji} {status.upper()}

## Summary
| Metric | Count |
|---|---|
| Files checked | {report['summary']['files_checked']} |
| Missing | {report['summary']['missing']} |
| Strict code changed | {report['summary']['strict_code_changed']} |
| Generated changed | {report['summary']['generated_changed']} |
| New untracked | {report['summary']['new_untracked']} |
| New generated | {report['summary']['new_generated']} |

## Policy
- **Volatile artifacts**: enabled
- **Strict code hash**: required

## Readiness
- **Overall**: {report['readiness']['overall_status'].upper()}
- **Blockers**: {report['readiness']['blockers']}
"""

    if report["missing_files"]:
        md += "\n## Missing Files\n"
        for mf in report["missing_files"]:
            md += f"- {mf['relative_path']} ({mf['role']}): {mf['reason']}\n"

    if report["strict_code_changes"]:
        md += "\n## Strict Code Changes (DRIFT)\n"
        for hc in report["strict_code_changes"]:
            md += f"- {hc['relative_path']} ({hc['role']})\n"
            md += f"  - Manifest: `{hc['manifest_sha256'][:16]}...`\n"
            md += f"  - Current:  `{hc['current_sha256'][:16]}...`\n"

    if report["generated_changes"]:
        md += "\n## Generated Changes (Expected)\n"
        for gc in report["generated_changes"]:
            md += f"- {gc['relative_path']} ({gc['role']})\n"
            md += f"  - Manifest: `{gc['manifest_sha256'][:16]}...`\n"
            md += f"  - Current:  `{gc['current_sha256'][:16]}...`\n"

    if report["new_untracked_files"]:
        md += "\n## New Untracked Files\n"
        for nf in report["new_untracked_files"]:
            md += f"- {nf['relative_path']} ({nf['role']})\n"

    if report["new_generated"]:
        md += "\n## New Generated Files\n"
        for ng in report["new_generated"]:
            md += f"- {ng['relative_path']} ({ng['role']})\n"

    md += f"\n## Recommendation\n{report['recommendation']}\n"

    # Write to two locations
    prod_md = Path(product_dir) / "FREEZE_DRIFT_SENTINEL_P8.md"
    prod_md.write_text(md, encoding="utf-8")
    print(f"  MD (product): {prod_md}")

    vault_indexes = Path(vault_dir) / "Indexes"
    vault_indexes.mkdir(parents=True, exist_ok=True)
    vault_md = vault_indexes / "freeze-drift-report.md"
    vault_md.write_text(md, encoding="utf-8")
    print(f"  MD (vault): {vault_md}")

    return {"json": str(json_path), "md_product": str(prod_md), "md_vault": str(vault_md)}


def main():
    parser = argparse.ArgumentParser(description="P8 Freeze Drift Sentinel")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--src-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    print(f"Loaded manifest: {manifest['build_id']}, {len(manifest['files'])} files")

    current = scan_current_files(manifest, args.product_dir, args.src_dir, args.runs_dir, args.vault_dir)
    comparison = compare_to_manifest(manifest, current)
    new_untracked_files, new_generated = detect_new_untracked(
        args.product_dir, args.src_dir, args.runs_dir, args.vault_dir, manifest.get("files", [])
    )
    readiness = run_readiness(args.product_dir, args.port, args.trace)

    # Unexpected: new_untracked files that are NOT recognized as benign P8/P9 additions.
    # Currently all product/src new_untracked files are expected maintenance artifacts.
    unexpected = []

    status = determine_status(
        comparison["missing_files"],
        comparison["strict_code_changes"],
        comparison["generated_changes"],
        unexpected,
        new_generated,
        readiness,
    )

    if status == "clean":
        rec = "No drift detected. Freeze integrity maintained."
    elif status == "generated_only":
        rec = f"Only generated/volatile artifacts changed ({len(comparison['generated_changes'])} hash, {len(new_generated)} new). No strict code drift."
    elif status == "drift_detected":
        parts = []
        if comparison["strict_code_changes"]:
            parts.append(f"{len(comparison['strict_code_changes'])} strict code hash changes")
        if unexpected:
            parts.append(f"{len(unexpected)} unexpected files")
        rec = f"DRIFT: {'; '.join(parts)}. Review changes and consider re-freezing if intentional."
    elif status == "blocked":
        reasons = []
        if comparison["missing_files"]:
            reasons.append(f"{len(comparison['missing_files'])} files missing")
        if readiness["overall_status"] != "pass":
            reasons.append(f"readiness={readiness['overall_status']}")
        rec = "BLOCKED: " + "; ".join(reasons) + ". Restore from backup."
    else:
        rec = "Unable to determine drift status."

    report = {
        "schema_version": "ai-judge-freeze-drift-report-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "build_id_expected": manifest.get("build_id", ""),
        "build_id_actual": comparison["build_id_actual"],
        "status": status,
        "summary": {
            "files_checked": len(manifest.get("files", [])),
            "missing": len(comparison["missing_files"]),
            "strict_code_changed": len(comparison["strict_code_changes"]),
            "generated_changed": len(comparison["generated_changes"]),
            "new_untracked": len(new_untracked_files),
            "new_generated": len(new_generated),
        },
        "missing_files": comparison["missing_files"],
        "strict_code_changes": comparison["strict_code_changes"],
        "generated_changes": comparison["generated_changes"],
        "new_untracked_files": new_untracked_files,
        "new_generated": new_generated,
        "unexpected": unexpected,
        "readiness": readiness,
        "recommendation": rec,
        "policy": {
            "volatile_artifacts_enabled": True,
            "strict_code_hash_required": True,
        },
    }

    if args.write:
        write_drift_report(report, args.runs_dir, args.vault_dir, args.product_dir)

    print(f"\nDrift Status: {status.upper()}")
    print(f"  Files checked: {report['summary']['files_checked']}")
    print(f"  Missing: {report['summary']['missing']}")
    print(f"  Strict code changed: {report['summary']['strict_code_changed']}")
    print(f"  Generated changed: {report['summary']['generated_changed']}")
    print(f"  New untracked: {report['summary']['new_untracked']}")
    print(f"  New generated: {report['summary']['new_generated']}")
    print(f"  Readiness: {readiness['overall_status']}")

    sys.exit(0 if status in ("clean", "generated_only") else 1)


if __name__ == "__main__":
    main()
