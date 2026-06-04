#!/usr/bin/env python3
"""
P8 Release Freeze & Regression Harness
一键回归测试脚本 — 验证 P0–P7.3 全链路功能稳定

用法:
    python3 regression_harness.py \
        --runs-dir "$RUNS" \
        --vault-dir "$VAULT" \
        --run-id "$RUN_ID" \
        --port "$PORT" \
        --trace "$TRACE" \
        --verbose
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

# ── Constants ────────────────────────────────────────────────────────────────
DASHBOARD_JS_BUILD_KEY = "p8.7-drift-sentinel-e2e-v1"
API_BASE = None  # set dynamically from --port

EXPECTED_RUN_FILES = [
    "verdict.json",
    "verdict.md",
    "trace.json",
    "index.html",
    "hermes-output.json",
    "hermes-output.md",
    "obsidian-run-note.md",
    "human-gavel.json",
    "human-gavel.md",
    "human-gavel-history.jsonl",
    "claim-calibration.json",
    "claim-calibration.md",
]

EXPECTED_GLOBAL_FILES = [
    "hermes-index.json",
    "claim-calibration-index.json",
    "run-universe.json",
    "trust-calibration.json",
]

EXPECTED_VAULT_FILES = [
    "hermes-index.md",
    "claim-calibration.md",
    "run-universe.md",
    "trust-calibration.md",
    "gavel-review-digest.md",
]


def _api_get(path: str, timeout: int = 15) -> tuple[int, dict]:
    """HTTP GET, returns (status_code, parsed_json or empty dict)."""
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                body = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = {"_raw_length": len(raw)}
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"_error": str(e)}


def _api_post(path: str, payload: dict, timeout: int = 10) -> tuple[int, dict]:
    """HTTP POST, returns (status_code, parsed_json)."""
    url = f"{API_BASE}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"_error": str(e)}


# ── Checkers ─────────────────────────────────────────────────────────────────

def check_files(runs_dir: str, vault_dir: str, run_id: str) -> dict:
    """Verify expected file artifacts exist."""
    results: dict = {
        "ok": True,
        "run_files": {},
        "global_files": {},
        "vault_files": {},
        "blockers": [],
        "warnings": [],
    }
    run_dir = Path(runs_dir) / run_id
    runs_path = Path(runs_dir)
    vault_indexes = Path(vault_dir) / "Indexes"

    for fname in EXPECTED_RUN_FILES:
        fp = run_dir / fname
        exists = fp.is_file()
        results["run_files"][fname] = exists
        if not exists:
            results["ok"] = False
            results["blockers"].append(f"Missing run file: {fp}")

    for fname in EXPECTED_GLOBAL_FILES:
        fp = runs_path / fname
        exists = fp.is_file()
        results["global_files"][fname] = exists
        if not exists:
            results["ok"] = False
            results["blockers"].append(f"Missing global file: {fp}")

    for fname in EXPECTED_VAULT_FILES:
        fp = vault_indexes / fname
        exists = fp.is_file()
        results["vault_files"][fname] = exists
        if not exists:
            results["ok"] = False
            results["warnings"].append(f"Missing vault file: {fp}")

    return results


def check_apis(run_id: str) -> dict:
    """Verify all core API endpoints return HTTP 200."""
    tests: list[tuple[str, str, str]] = [
        ("GET",  "/api/health",                        "health"),
        ("GET",  f"/api/judge/{run_id}/verdict",       "verdict"),
        ("GET",  f"/api/runs/{run_id}/index.html",      "run_index_html"),
        ("GET",  f"/api/runs/{run_id}/hermes-output.json", "hermes_output"),
        ("GET",  "/api/hermes/index",                  "hermes_index"),
        ("GET",  "/api/hermes/seats",                  "hermes_seats"),
        ("GET",  f"/api/gavel/{run_id}",               "gavel_status"),
        ("GET",  f"/api/gavel/{run_id}/history",       "gavel_history"),
        ("GET",  "/api/gavel/digest",                  "gavel_digest"),
        ("GET",  "/api/claims/calibration",            "claims_calibration"),
        ("GET",  f"/api/claims/calibration/{run_id}",  "claims_calibration_run"),
        ("GET",  "/api/runs/universe",                 "runs_universe"),
        ("GET",  "/api/trust/calibration",             "trust_calibration"),
        ("GET",  "/api/trust/seat/gemini",             "trust_seat_gemini"),
        ("GET",  "/api/decision/intelligence",         "decision_intelligence"),
    ]

    results: dict = {
        "ok": True,
        "endpoints": {},
        "blockers": [],
    }

    for method, path, label in tests:
        if method == "GET":
            status, body = _api_get(path)
        else:
            status, body = _api_post(path, {})
        results["endpoints"][label] = {
            "status": status,
            "ok": status == 200,
        }
        if status != 200:
            results["ok"] = False
            results["blockers"].append(
                f"API {label} ({method} {path}) returned {status}"
            )

    return results


def check_dashboard_build(product_dir: str) -> dict:
    """Verify BUILD_ID in dashboard.js contains the expected version tag."""
    results: dict = {
        "ok": False,
        "build_id": "",
        "blockers": [],
    }
    dash_path = Path(product_dir) / "dashboard.js"
    if not dash_path.is_file():
        results["blockers"].append(f"dashboard.js not found at {dash_path}")
        return results

    content = dash_path.read_text(encoding="utf-8")
    # Extract BUILD_ID from const assignment
    for line in content.splitlines():
        if "AI_JUDGE_CLIENT_BUILD" in line:
            # e.g. const AI_JUDGE_CLIENT_BUILD = "p7.2-di-shortcut-e2e-v1";
            parts = line.split('"')
            if len(parts) >= 3:
                results["build_id"] = parts[1]
            break

    if not results["build_id"]:
        results["blockers"].append("Could not extract BUILD_ID from dashboard.js")
        return results

    if DASHBOARD_JS_BUILD_KEY in results["build_id"]:
        results["ok"] = True
    else:
        results["blockers"].append(
            f"BUILD_ID '{results['build_id']}' does not contain expected key '{DASHBOARD_JS_BUILD_KEY}'"
        )

    return results


def check_trace(trace_path_str: str) -> dict:
    """Perform trace smoke: POST a test event, verify it lands in trace file."""
    results: dict = {
        "ok": False,
        "posted": False,
        "found_in_file": False,
        "blockers": [],
    }
    trace_file = Path(trace_path_str)

    # POST test event
    status, body = _api_post("/api/trace", {"event": "p8_regression_smoke", "ok": True})
    results["posted"] = (status == 200)
    results["api_status"] = status
    if not results["posted"]:
        results["blockers"].append(f"POST /api/trace returned {status}")
        return results

    # Wait a beat for FS flush
    time.sleep(0.3)

    # Check file
    if not trace_file.is_file():
        results["blockers"].append(f"Trace file not found: {trace_file}")
        return results

    try:
        with open(trace_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    if evt.get("event") == "p8_regression_smoke":
                        results["found_in_file"] = True
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        results["blockers"].append(f"Error reading trace file: {e}")
        return results

    if results["found_in_file"]:
        results["ok"] = True
    else:
        results["blockers"].append("Trace event not found in file after POST")

    return results


def check_sample_run(run_id: str) -> dict:
    """Quick sanity check that the sample run has a valid verdict."""
    results: dict = {
        "ok": False,
        "has_verdict": False,
        "blockers": [],
    }
    status, body = _api_get(f"/api/judge/{run_id}/verdict")
    if status == 200 and body:
        results["has_verdict"] = True
        results["ok"] = True
    else:
        results["blockers"].append(f"Sample run {run_id} verdict API returned {status}")
    return results


# ── Orchestrator ─────────────────────────────────────────────────────────────

def run_regression(
    runs_dir: str,
    vault_dir: str,
    run_id: str,
    port: int,
    trace_path: str,
    verbose: bool = False,
) -> dict:
    global API_BASE
    API_BASE = f"http://127.0.0.1:{port}"

    results: dict = {
        "schema_version": "ai-judge-regression-harness-v1",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "checks": {},
        "overall_ok": True,
        "blockers": [],
        "warnings": [],
    }

    def _run_check(name: str, fn, *args):
        if verbose:
            print(f"  [{name}] ...", end=" ", flush=True)
        try:
            r = fn(*args)
        except Exception as e:
            r = {"ok": False, "blockers": [str(e)]}
        results["checks"][name] = r
        if not r.get("ok", False):
            results["overall_ok"] = False
            results["blockers"].extend(r.get("blockers", []))
        results["warnings"].extend(r.get("warnings", []))
        if verbose:
            status = "PASS" if r.get("ok") else "FAIL"
            print(status)
            for b in r.get("blockers", []):
                print(f"    BLOCKER: {b}")
            for w in r.get("warnings", []):
                print(f"    WARNING: {w}")

    if verbose:
        print("P8 Regression Harness")
        print(f"  RUNS:  {runs_dir}")
        print(f"  VAULT: {vault_dir}")
        print(f"  RUNID: {run_id}")
        print(f"  PORT:  {port}")
        print(f"  TRACE: {trace_path}")
        print()

    _run_check("files", check_files, runs_dir, vault_dir, run_id)
    _run_check("apis", check_apis, run_id)
    _run_check("dashboard_build", check_dashboard_build,
               str(Path(runs_dir).parent / "product"))
    _run_check("trace", check_trace, trace_path)
    _run_check("sample_run", check_sample_run, run_id)

    return results


def main():
    parser = argparse.ArgumentParser(description="P8 Release Regression Harness")
    parser.add_argument("--runs-dir", required=True, help="Path to runs directory")
    parser.add_argument("--vault-dir", required=True, help="Path to Obsidian vault")
    parser.add_argument("--run-id", required=True, help="Sample run ID to check")
    parser.add_argument("--port", type=int, required=True, help="API server port")
    parser.add_argument("--trace", required=True, help="Path to debug-ui-io-trace.jsonl")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    result = run_regression(
        runs_dir=args.runs_dir,
        vault_dir=args.vault_dir,
        run_id=args.run_id,
        port=args.port,
        trace_path=args.trace,
        verbose=args.verbose,
    )

    print()
    print("=" * 60)
    print("OVERALL:", "PASS" if result["overall_ok"] else "FAIL")
    print(f"Blockers: {len(result['blockers'])}")
    for b in result["blockers"]:
        print(f"  - {b}")
    if result["warnings"]:
        print(f"Warnings: {len(result['warnings'])}")
        for w in result["warnings"]:
            print(f"  - {w}")

    sys.exit(0 if result["overall_ok"] else 1)


if __name__ == "__main__":
    main()
