#!/usr/bin/env python3
"""Public Demo Expansion V1 — Runtime Monitor

Usage:
    python monitor_public_demo_expansion.py --once
    python monitor_public_demo_expansion.py --interval 60
"""

import json
import argparse
import time
import sys
from datetime import datetime, timezone


REGISTRY_PATH = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_run_registry.json"
INCIDENTS_PATH = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_incidents.jsonl"


def load_registry():
    try:
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_incidents():
    try:
        with open(INCIDENTS_PATH) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def get_metrics():
    runs = load_registry()
    incidents = load_incidents()

    completed = sum(1 for r in runs if r["status"] == "completed")
    failed = sum(1 for r in runs if r["status"] == "failed")
    degraded = sum(1 for r in runs if r["status"] == "degraded")
    blocked = sum(1 for r in runs if r["status"] == "blocked")

    latencies = [r["latency_sec"] for r in runs if r.get("latency_sec", 0) > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    p0_incidents = sum(1 for i in incidents if i["severity"] == "P0")

    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs_submitted": len(runs),
        "runs_completed": completed,
        "runs_failed": failed,
        "runs_degraded": degraded,
        "runs_blocked": blocked,
        "avg_latency_sec": round(avg_latency, 1),
        "p0_incidents": p0_incidents,
        "rate_limit_hits": sum(1 for r in runs if r.get("rate_limited")),
        "safety_blocks": sum(1 for r in runs if r.get("safety_blocked")),
        "pii_redactions": sum(1 for r in runs if r.get("pii_redacted")),
        "validation_failures": sum(1 for r in runs if r["status"] in ("completed", "degraded") and not r.get("validation_ok", True)),
        "artifact_failures": sum(1 for r in runs if r["status"] == "failed" and not r.get("validation_ok", False)),
    }


def check_alerts(metrics):
    alerts = []
    if metrics["p0_incidents"] > 0:
        alerts.append("ALERT: P0 incident detected!")
    if metrics["runs_submitted"] > 0:
        error_rate = (metrics["runs_failed"] + metrics["runs_blocked"]) / metrics["runs_submitted"] * 100
        if error_rate > 20:
            alerts.append(f"ALERT: Error rate {error_rate:.1f}% exceeds 20%!")
    if metrics["validation_failures"] > 0:
        alerts.append(f"ALERT: {metrics['validation_failures']} validation failures!")
    if metrics["pii_redactions"] > metrics["safety_blocks"]:
        alerts.append("ALERT: PII redactions exceed safety blocks — possible PII leak!")
    return alerts


def main():
    parser = argparse.ArgumentParser(description="Monitor public demo expansion runtime")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds")
    args = parser.parse_args()

    if args.once:
        metrics = get_metrics()
        print(json.dumps(metrics, indent=2))
        alerts = check_alerts(metrics)
        if alerts:
            print("\n=== ALERTS ===")
            for a in alerts:
                print(a)
        return

    print(f"Starting monitor (interval={args.interval}s)...")
    try:
        while True:
            metrics = get_metrics()
            print(json.dumps(metrics))
            alerts = check_alerts(metrics)
            for a in alerts:
                print(a, file=sys.stderr)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")


if __name__ == "__main__":
    main()