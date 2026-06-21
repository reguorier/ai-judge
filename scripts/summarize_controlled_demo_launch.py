#!/usr/bin/env python3
"""summarize_controlled_demo_launch.py — Controlled Demo Launch 汇总脚本

汇总 cohort、registry、feedback、incidents、metrics 并输出 final pass/fail。

用法:
    python scripts/summarize_controlled_demo_launch.py
"""

import json
import os
import sys

BASE = os.path.join(
    os.path.expanduser("~"), "Library", "Application Support", "AI Judge",
    "runtime", "product", "demo_launch"
)

REQUIRED_FILES = [
    f"{BASE}/controlled_demo_cohort.json",
    f"{BASE}/controlled_demo_invitation.md",
    f"{BASE}/controlled_demo_operator_runbook.md",
    f"{BASE}/controlled_demo_run_registry.json",
    f"{BASE}/controlled_demo_feedback.jsonl",
    f"{BASE}/controlled_demo_incidents.jsonl",
    f"{BASE}/controlled_demo_metrics.json",
    f"{BASE}/controlled_demo_patch_backlog.json",
]

SYSTEM_THRESHOLDS = {
    "api_health": "100%",
    "validation_pass": "100%",
    "artifact_pass": ">=95%",
    "error_rate": "<=15%",
    "p0_incident": "0",
    "raw_pii_leak": "0",
    "traceback_secret_exposure": "0",
    "avg_latency_sec": "<=180s",
}

USER_THRESHOLDS = {
    "feedback_coverage": ">=80%",
    "can_state_final_answer": ">=80%",
    "can_state_next_step": ">=80%",
    "can_explain_why": ">=70%",
    "avg_trust_score": ">=3.8",
    "avg_readability_score": ">=3.8",
    "avg_actionability_score": ">=3.8",
    "would_use_again": ">=70%",
}


def check_files() -> dict:
    """Check all required files exist."""
    results = {}
    for f in REQUIRED_FILES:
        exists = os.path.exists(f)
        results[f] = "OK" if exists else "MISSING"
    return results


def load_metrics() -> dict | None:
    """Load metrics file."""
    path = f"{BASE}/controlled_demo_metrics.json"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def load_cohort() -> dict | None:
    """Load cohort file."""
    path = f"{BASE}/controlled_demo_cohort.json"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def validate_metrics(metrics: dict) -> dict:
    """Validate metrics against thresholds."""
    results = {}

    system = metrics.get("system_metrics", {})
    for key, val in system.items():
        if isinstance(val, dict):
            results[f"system.{key}"] = val.get("result", "UNKNOWN")

    user = metrics.get("user_metrics", {})
    for key, val in user.items():
        if isinstance(val, dict):
            results[f"user.{key}"] = val.get("result", "UNKNOWN")

    return results


def main():
    print("=== Controlled Public Demo Launch V1 — Summary ===\n")

    # File check
    print("--- File Inventory ---")
    file_status = check_files()
    all_present = all(v == "OK" for v in file_status.values())
    for f, status in file_status.items():
        print(f"  [{status}] {f}")
    print(f"  Files: {sum(1 for v in file_status.values() if v == 'OK')}/{len(file_status)} present\n")

    if not all_present:
        print("FAIL: missing required files")
        sys.exit(1)

    # Cohort
    cohort = load_cohort()
    if cohort:
        print(f"--- Cohort: {len(cohort)} users ---")
        for u in cohort:
            print(f"  {u['user_id']} | {u['reader_type']} | max_runs={u['max_runs']} | consent={u['consent_confirmed']}")

    # Metrics
    metrics = load_metrics()
    if metrics:
        print(f"\n--- Metrics ---")
        overall = metrics.get("overall_result", "UNKNOWN")
        runtime = metrics.get("runtime_monitoring", {})

        print(f"  Runs: {runtime.get('runs_submitted', '?')} submitted / "
              f"{runtime.get('runs_completed', '?')} completed / "
              f"{runtime.get('runs_failed', '?')} failed")
        print(f"  Incidents: {runtime.get('incident_count', '?')}")

        print(f"\n--- Threshold Validation ---")
        threshold_results = validate_metrics(metrics)
        system_pass = all(v == "PASS" for k, v in threshold_results.items() if k.startswith("system."))
        user_pass = all(v == "PASS" for k, v in threshold_results.items() if k.startswith("user."))

        for key, result in sorted(threshold_results.items()):
            print(f"  [{result}] {key}")

        print(f"\n  System thresholds: {'ALL PASS' if system_pass else 'SOME FAIL'}")
        print(f"  User thresholds:   {'ALL PASS' if user_pass else 'SOME FAIL'}")

        print(f"\n--- Final Result ---")
        print(f"  {overall}")

        if overall == "CONTROLLED_PUBLIC_DEMO_LAUNCH_V1_PASS":
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("\nFAIL: metrics file could not be loaded")
        sys.exit(1)


if __name__ == "__main__":
    main()