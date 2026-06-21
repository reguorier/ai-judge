#!/usr/bin/env python3
"""Generate installer payload manifest with hashes."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FILES = [
    "product/client_api.py",
    "product/api_server.py",
    "product/dashboard.html",
    "product/dashboard.js",
    "core/web_jury.py",
    "core/werewolf_executor.py",
    "core/werewolf_game.py",
    "bridges/web_seat_bridge.py",
    "bridges/chrome_fixed_tab_bridge.py",
    "bridges/chrome_cdp_bridge.py",
    "data/web_seats.json",
]

EXCLUDED_PATTERNS = [
    ".git/",
    "__pycache__/",
    ".pytest_cache/",
    "node_modules/",
    "dist/",
    "build/",
    "runtime/runs/",
    "*.log",
    "*.token",
    "*.key",
    "*.pem",
    ".env",
    "secrets*",
    "private*",
    "*.pyc",
    "*.pyo",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def git_info(root: Path) -> dict:
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=root, text=True
        ).strip()
    except Exception:
        branch = "unknown"
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    return {"branch": branch, "commit": commit}


def file_size(path: Path) -> int:
    return path.stat().st_size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-root", required=True)
    parser.add_argument("--canonical-root", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload_root = Path(args.payload_root)
    canonical_root = Path(args.canonical_root)
    git = git_info(canonical_root)

    # Find all files in payload (relative to payload root)
    included_files = []
    hashes = {}
    runtime_root_rel = "Users/Shared/AI Judge/runtime"

    for f in sorted(payload_root.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(payload_root))
        included_files.append(rel)
        try:
            hashes[rel] = sha256(f)
        except Exception:
            hashes[rel] = "ERROR"

    # Check required files
    required_status = {}
    for req in REQUIRED_FILES:
        target_rel = f"{runtime_root_rel}/{req}"
        present = target_rel in included_files
        required_status[req] = {
            "present": present,
            "size": file_size(payload_root / target_rel) if present else 0,
        }

    manifest = {
        "source_commit": git["commit"],
        "source_branch": git["branch"],
        "source_version": args.version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_root": "/Users/Shared/AI Judge/runtime",
        "total_files": len(included_files),
        "required_files": required_status,
        "included_files": included_files,
        "excluded_patterns": EXCLUDED_PATTERNS,
        "hashes": hashes,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as fh:
        json.dump(manifest, fh, indent=2)

    # Print summary
    missing = [k for k, v in required_status.items() if not v["present"]]
    if missing:
        print(f"MISSING REQUIRED FILES: {missing}")
        sys.exit(1)
    else:
        print(f"All {len(REQUIRED_FILES)} required files present")
        for req in REQUIRED_FILES:
            sz = required_status[req]["size"]
            print(f"  OK {req} ({sz} bytes)")
    print(f"Total payload files: {len(included_files)}")


if __name__ == "__main__":
    main()
