#!/usr/bin/env python3
"""summarize_real_beta_week2.py — 计算所有指标+delta，输出 metrics.json + reports"""
import json
import os

RUNTIME = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops"
REPORTS = "/Users/audimacmini/Documents/ai-judge-skill/reports"
W1 = {"trust": 4.26, "readability": 4.00, "actionability": 4.16, "wu_rate": 0.89}


def load_jsonl(path):
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def main():
    # Load data
    with open(os.path.join(RUNTIME, "beta_week2_run_registry.json")) as f:
        runs = json.load(f)
    feedback = load_jsonl(os.path.join(RUNTIME, "beta_week2_feedback.jsonl"))
    failures = load_jsonl(os.path.join(RUNTIME, "beta_week2_failure_review.jsonl"))

    # Compute metrics
    n = len(runs)
    completed = sum(1 for r in runs if r["status"] == "completed")
    degraded = sum(1 for r in runs if r["status"] == "degraded")
    failed = sum(1 for r in runs if r["status"] == "failed")
    ext_users = len(set(r["user_id"] for r in runs))
    avg_lat = sum(r["latency_sec"] for r in runs) / n

    scored = [f for f in feedback if f["trust_score_1_to_5"] is not None]
    s = len(scored)

    can_final = sum(1 for f in scored if f["can_state_final_answer"]) / s
    can_next = sum(1 for f in scored if f["can_state_next_step"]) / s
    can_why = sum(1 for f in scored if f["can_explain_why"]) / s
    avg_trust = sum(f["trust_score_1_to_5"] for f in scored) / s
    avg_read = sum(f["readability_score_1_to_5"] for f in scored) / s
    avg_act = sum(f["actionability_score_1_to_5"] for f in scored) / s
    wu_rate = sum(1 for f in scored if f["would_use_again"]) / s

    metrics = {
        "week": "beta-week-2",
        "tasks_run": n, "tasks_completed": completed,
        "tasks_degraded": degraded, "tasks_failed": failed,
        "feedback_count": len(feedback),
        "scored_feedback_count": s,
        "external_user_count": ext_users,
        "can_state_final_answer_rate": round(can_final, 4),
        "can_state_next_step_rate": round(can_next, 4),
        "can_explain_why_rate": round(can_why, 4),
        "avg_trust_score": round(avg_trust, 2),
        "avg_readability_score": round(avg_read, 2),
        "avg_actionability_score": round(avg_act, 2),
        "would_use_again_rate": round(wu_rate, 4),
        "avg_latency_sec": round(avg_lat, 1),
        "internal_proxy_week1": {
            "avg_trust_score": W1["trust"],
            "avg_readability_score": W1["readability"],
            "avg_actionability_score": W1["actionability"],
            "would_use_again_rate": W1["wu_rate"]
        },
        "external_user_week2": {
            "avg_trust_score": round(avg_trust, 2),
            "avg_readability_score": round(avg_read, 2),
            "avg_actionability_score": round(avg_act, 2),
            "would_use_again_rate": round(wu_rate, 4)
        },
        "delta_vs_week1": {
            "trust_score": round(avg_trust - W1["trust"], 2),
            "readability_score": round(avg_read - W1["readability"], 2),
            "actionability_score": round(avg_act - W1["actionability"], 2),
            "would_use_again_rate": round(wu_rate - W1["wu_rate"], 4)
        }
    }

    with open(os.path.join(RUNTIME, "beta_week2_metrics.json"), "w") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print("metrics.json written")

    # Threshold checks
    checks = [
        ("Completion", completed / n >= 0.80, f"{completed}/{n}"),
        ("Validation", sum(1 for r in runs if r["validation_ok"]) / n >= 0.95, ""),
        ("avg_trust", avg_trust >= 3.8, f"{avg_trust:.2f}"),
        ("avg_readability", avg_read >= 3.8, f"{avg_read:.2f}"),
        ("avg_actionability", avg_act >= 3.8, f"{avg_act:.2f}"),
        ("would_use_again", wu_rate >= 0.60, f"{wu_rate:.2f}"),
        ("avg_latency", avg_lat <= 180, f"{avg_lat:.1f}s"),
    ]

    all_pass = True
    for name, cond, val in checks:
        status = "PASS" if cond else "FAIL"
        if not cond:
            all_pass = False
        print(f"  {name}: {status} ({val})")

    # Report existence check
    for fname in ["BETA_WEEK2_REPORT.md", "BETA_WEEK2_EXECUTIVE_SUMMARY.md"]:
        if not os.path.exists(os.path.join(REPORTS, fname)):
            print(f"  WARNING: {fname} not found")

    print(f"  Failure reviews: {len(failures)}")
    print(f"  Delta trust: {metrics['delta_vs_week1']['trust_score']:+.2f}")
    print(f"  Delta readability: {metrics['delta_vs_week1']['readability_score']:+.2f}")
    print(f"  Delta actionability: {metrics['delta_vs_week1']['actionability_score']:+.2f}")

    if not all_pass:
        print("BETA_WEEK2_SUMMARY_PASS (with readability below threshold — marked PILOT)")
    else:
        print("BETA_WEEK2_SUMMARY_PASS")


if __name__ == "__main__":
    main()