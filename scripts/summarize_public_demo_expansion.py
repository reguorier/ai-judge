#!/usr/bin/env python3
"""Public Demo Expansion V1 — Summarizer

Outputs:
    runtime/product/demo_expansion/expansion_metrics.json
    reports/PUBLIC_DEMO_EXPANSION_REPORT.md
    reports/PUBLIC_DEMO_EXPANSION_EXECUTIVE_SUMMARY.md
"""

import json
import sys
import os
from datetime import datetime, timezone

RUNTIME_DIR = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion"
REPORTS_DIR = "/Users/audimacmini/Documents/ai-judge-skill/reports"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_metrics(cohort, assignments, registry, feedbacks, incidents, waitlist):
    total_users = len(cohort)
    external_users = sum(1 for u in cohort if u.get("is_external_user", False))
    external_ratio = external_users / total_users * 100

    total_runs = len(registry)
    completed = sum(1 for r in registry if r["status"] == "completed")
    degraded = sum(1 for r in registry if r["status"] == "degraded")
    failed = sum(1 for r in registry if r["status"] == "failed")
    blocked = sum(1 for r in registry if r["status"] == "blocked")
    success_rate = (completed + degraded) / total_runs * 100

    latencies = [r["latency_sec"] for r in registry if r.get("latency_sec", 0) > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    p0 = sum(1 for i in incidents if i["severity"] == "P0")

    # User metrics from feedbacks
    fb_total = len(feedbacks)
    avg_trust = sum(f["trust_score_1_to_5"] for f in feedbacks) / fb_total if fb_total else 0
    avg_readability = sum(f["readability_score_1_to_5"] for f in feedbacks) / fb_total if fb_total else 0
    avg_actionability = sum(f["actionability_score_1_to_5"] for f in feedbacks) / fb_total if fb_total else 0
    would_use = sum(1 for f in feedbacks if f.get("would_use_again")) / fb_total * 100 if fb_total else 0
    would_rec = sum(1 for f in feedbacks if f.get("would_recommend")) / fb_total * 100 if fb_total else 0
    would_wait = sum(1 for f in feedbacks if f.get("would_join_waitlist")) / fb_total * 100 if fb_total else 0

    # Cohort distribution
    reader_dist = {}
    for u in cohort:
        rt = u.get("reader_type", "unknown")
        reader_dist[rt] = reader_dist.get(rt, 0) + 1

    metrics = {
        "release": "public-demo-expansion-v1.0.0",
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cohort": {
            "total_users": total_users,
            "external_users": external_users,
            "external_ratio": round(external_ratio, 1),
            "distribution": reader_dist,
        },
        "runs": {
            "total": total_runs,
            "completed": completed,
            "degraded": degraded,
            "failed": failed,
            "blocked": blocked,
            "success_rate": round(success_rate, 1),
            "avg_latency_sec": round(avg_latency, 1),
        },
        "incidents": {
            "total": len(incidents),
            "p0": p0,
            "p1": sum(1 for i in incidents if i["severity"] == "P1"),
            "p2": sum(1 for i in incidents if i["severity"] == "P2"),
        },
        "user_metrics": {
            "feedback_total": fb_total,
            "avg_trust": round(avg_trust, 2),
            "avg_readability": round(avg_readability, 2),
            "avg_actionability": round(avg_actionability, 2),
            "would_use_again_pct": round(would_use, 1),
            "would_recommend_pct": round(would_rec, 1),
            "would_join_waitlist_pct": round(would_wait, 1),
        },
        "waitlist": {
            "total": len(waitlist),
            "use_cases": {},
        },
        "thresholds": {
            "system": {
                "p0_incidents_0": "PASS" if p0 == 0 else "FAIL",
                "success_rate_ge_85": "PASS" if success_rate >= 85 else "FAIL",
                "avg_latency_le_180": "PASS" if avg_latency <= 180 else "FAIL",
            },
            "user": {
                "avg_trust_ge_3_8": "PASS" if avg_trust >= 3.8 else "FAIL",
                "avg_readability_ge_3_8": "PASS" if avg_readability >= 3.8 else "FAIL",
                "avg_actionability_ge_3_8": "PASS" if avg_actionability >= 3.8 else "FAIL",
                "would_use_again_ge_70": "PASS" if would_use >= 70 else "FAIL",
                "would_recommend_ge_50": "PASS" if would_rec >= 50 else "FAIL",
                "would_join_waitlist_ge_40": "PASS" if would_wait >= 40 else "FAIL",
            },
        },
    }

    # Waitlist use case distribution
    for w in waitlist:
        uc = w.get("use_case", "other")
        metrics["waitlist"]["use_cases"][uc] = metrics["waitlist"]["use_cases"].get(uc, 0) + 1

    # Determine overall result
    all_pass = all(v == "PASS" for d in metrics["thresholds"].values() for v in d.values())
    metrics["overall_result"] = "PUBLIC_DEMO_EXPANSION_V1_PASS" if all_pass else "PUBLIC_DEMO_EXPANSION_METRICS_FAIL"

    return metrics


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    cohort = load_json(f"{RUNTIME_DIR}/expansion_cohort.json")
    assignments = load_json(f"{RUNTIME_DIR}/expansion_task_assignments.json")
    registry = load_json(f"{RUNTIME_DIR}/expansion_run_registry.json")

    feedback_path = f"{RUNTIME_DIR}/expansion_feedback.jsonl"
    feedbacks = load_jsonl(feedback_path) if os.path.exists(feedback_path) else []

    incidents_path = f"{RUNTIME_DIR}/expansion_incidents.jsonl"
    incidents = load_jsonl(incidents_path) if os.path.exists(incidents_path) else []

    waitlist_path = f"{RUNTIME_DIR}/expansion_waitlist_interest.jsonl"
    waitlist = load_jsonl(waitlist_path) if os.path.exists(waitlist_path) else []

    metrics = compute_metrics(cohort, assignments, registry, feedbacks, incidents, waitlist)

    # Write metrics
    metrics_path = f"{RUNTIME_DIR}/expansion_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"=== Public Demo Expansion V1 Summary ===")
    print(f"Users: {metrics['cohort']['total_users']} ({metrics['cohort']['external_ratio']}% external)")
    print(f"Runs: {metrics['runs']['total']} (success: {metrics['runs']['success_rate']}%)")
    print(f"Trust: {metrics['user_metrics']['avg_trust']} / Readability: {metrics['user_metrics']['avg_readability']} / Actionability: {metrics['user_metrics']['avg_actionability']}")
    print(f"Would recommend: {metrics['user_metrics']['would_recommend_pct']}%")
    print(f"Waitlist: {metrics['user_metrics']['would_join_waitlist_pct']}%")
    print(f"P0 incidents: {metrics['incidents']['p0']}")
    print(f"")
    print(f"Result: {metrics['overall_result']}")
    print(f"Metrics written to: {metrics_path}")


if __name__ == "__main__":
    main()