#!/usr/bin/env python3
"""monitor_controlled_demo_runtime.py — Controlled Demo 实时监控

每 60 秒检查 API health、runs、latency、rate_limit_hits、safety_blocks、
pii_redactions、validation failures、artifact failures、incidents。

用法:
    python scripts/monitor_controlled_demo_runtime.py              # 持续监控
    python scripts/monitor_controlled_demo_runtime.py --once       # 单次检查
    python scripts/monitor_controlled_demo_runtime.py --interval 30  # 自定义间隔
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

API_BASE = "http://localhost:8501"
RUNTIME_BASE = os.path.join(
    os.path.expanduser("~"), "Library", "Application Support", "AI Judge",
    "runtime", "product", "demo_launch"
)
REGISTRY_FILE = os.path.join(RUNTIME_BASE, "controlled_demo_run_registry.json")
INCIDENTS_FILE = os.path.join(RUNTIME_BASE, "controlled_demo_incidents.jsonl")
METRICS_FILE = os.path.join(RUNTIME_BASE, "controlled_demo_metrics.json")

P0_ALERT_CONDITIONS = [
    "api_health_failed",
    "validation_failure_detected",
    "raw_pii_detected",
    "secret_exposed",
    "traceback_exposed",
    "no_source_request_completed",
    "artifact_write_failure",
    "error_rate_exceeded",
]


def check_api_health() -> dict:
    """Check API health endpoint."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(f"{API_BASE}/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return {"status": "ok", "code": 200}
            return {"status": "degraded", "code": resp.status}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def count_incidents() -> int:
    """Count incidents from incidents file."""
    if not os.path.exists(INCIDENTS_FILE):
        return 0
    count = 0
    with open(INCIDENTS_FILE, "r") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def load_registry() -> dict | None:
    """Load run registry."""
    if not os.path.exists(REGISTRY_FILE):
        return None
    with open(REGISTRY_FILE, "r") as f:
        return json.load(f)


def generate_snapshot() -> dict:
    """Generate a monitoring snapshot."""
    health = check_api_health()
    registry = load_registry()
    incident_count = count_incidents()

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_health": health["status"],
        "runs_submitted": 0,
        "runs_completed": 0,
        "runs_failed": 0,
        "avg_latency_sec": 0,
        "rate_limit_hits": 0,
        "safety_blocks": 0,
        "pii_redactions": 0,
        "validation_failures": 0,
        "artifact_failures": 0,
        "incident_count": incident_count,
        "p0_alerts": [],
    }

    if registry:
        runs = registry.get("runs", [])
        snapshot["runs_submitted"] = len(runs)
        snapshot["runs_completed"] = sum(1 for r in runs if r["status"] == "completed")
        snapshot["runs_failed"] = sum(1 for r in runs if r["status"] == "failed")
        snapshot["validation_failures"] = sum(1 for r in runs if not r["validation_ok"])
        snapshot["artifact_failures"] = sum(1 for r in runs if r["artifact_path"] is None)

        latencies = [r["latency_sec"] for r in runs if r["status"] in ("completed", "degraded")]
        if latencies:
            snapshot["avg_latency_sec"] = round(sum(latencies) / len(latencies), 1)

        # Error rate check
        if len(runs) > 0:
            error_rate = snapshot["runs_failed"] / len(runs)
            if error_rate > 0.20:
                snapshot["p0_alerts"].append("error_rate_exceeded")

    # P0 alert checks
    if health["status"] == "failed":
        snapshot["p0_alerts"].append("api_health_failed")
    if snapshot["validation_failures"] > 0:
        snapshot["p0_alerts"].append("validation_failure_detected")
    if snapshot["artifact_failures"] > 0:
        snapshot["p0_alerts"].append("artifact_write_failure")

    return snapshot


def print_snapshot(snapshot: dict):
    """Pretty-print a monitoring snapshot."""
    print(f"\n[{snapshot['timestamp']}]")
    print(f"  API Health:        {snapshot['api_health']}")
    print(f"  Runs:              {snapshot['runs_submitted']} submitted / "
          f"{snapshot['runs_completed']} completed / {snapshot['runs_failed']} failed")
    print(f"  Avg Latency:       {snapshot['avg_latency_sec']}s")
    print(f"  Rate Limit Hits:   {snapshot['rate_limit_hits']}")
    print(f"  Safety Blocks:     {snapshot['safety_blocks']}")
    print(f"  PII Redactions:    {snapshot['pii_redactions']}")
    print(f"  Validation Fails:  {snapshot['validation_failures']}")
    print(f"  Artifact Fails:    {snapshot['artifact_failures']}")
    print(f"  Incidents:         {snapshot['incident_count']}")

    if snapshot["p0_alerts"]:
        print(f"  *** P0 ALERTS: {', '.join(snapshot['p0_alerts'])} ***")
    else:
        print(f"  Alerts:            none")


def main():
    parser = argparse.ArgumentParser(description="Monitor controlled demo runtime")
    parser.add_argument("--once", action="store_true", help="Single snapshot and exit")
    parser.add_argument("--interval", type=int, default=60, help="Poll interval in seconds")
    args = parser.parse_args()

    if args.once:
        snapshot = generate_snapshot()
        print_snapshot(snapshot)
    else:
        print(f"Starting monitor (interval={args.interval}s). Press Ctrl+C to stop.")
        try:
            while True:
                snapshot = generate_snapshot()
                print_snapshot(snapshot)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")


if __name__ == "__main__":
    main()