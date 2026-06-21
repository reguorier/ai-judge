#!/usr/bin/env python3
"""Public Demo Expansion V1 — Feedback Collector"""

import json
import argparse
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Collect public demo expansion feedback")
    parser.add_argument("--input", default="", help="Input feedback JSONL file path")
    parser.add_argument("--output", default="", help="Output summary file path")
    args = parser.parse_args()

    input_path = args.input or "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_feedback.jsonl"

    try:
        with open(input_path) as f:
            lines = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: Feedback file not found: {input_path}")
        sys.exit(1)

    if not lines:
        print("WARNING: No feedback entries found")
        sys.exit(0)

    # Compute metrics
    total = len(lines)
    external = sum(1 for l in lines if l.get("is_external_user", False))
    avg_trust = sum(l["trust_score_1_to_5"] for l in lines) / total
    avg_readability = sum(l["readability_score_1_to_5"] for l in lines) / total
    avg_actionability = sum(l["actionability_score_1_to_5"] for l in lines) / total
    would_use = sum(1 for l in lines if l.get("would_use_again")) / total * 100
    would_rec = sum(1 for l in lines if l.get("would_recommend")) / total * 100
    would_wait = sum(1 for l in lines if l.get("would_join_waitlist")) / total * 100
    can_final = sum(1 for l in lines if l.get("can_state_final_answer")) / total * 100
    can_next = sum(1 for l in lines if l.get("can_state_next_step")) / total * 100
    can_why = sum(1 for l in lines if l.get("can_explain_why")) / total * 100

    summary = {
        "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_feedback": total,
        "external_users": external,
        "avg_trust": round(avg_trust, 2),
        "avg_readability": round(avg_readability, 2),
        "avg_actionability": round(avg_actionability, 2),
        "would_use_again_pct": round(would_use, 1),
        "would_recommend_pct": round(would_rec, 1),
        "would_join_waitlist_pct": round(would_wait, 1),
        "can_state_final_answer_pct": round(can_final, 1),
        "can_state_next_step_pct": round(can_next, 1),
        "can_explain_why_pct": round(can_why, 1),
        "thresholds": {
            "feedback_coverage_ge_75": "PASS" if total >= 38 else "FAIL",
            "avg_trust_ge_3_8": "PASS" if avg_trust >= 3.8 else "FAIL",
            "avg_readability_ge_3_8": "PASS" if avg_readability >= 3.8 else "FAIL",
            "avg_actionability_ge_3_8": "PASS" if avg_actionability >= 3.8 else "FAIL",
            "would_use_again_ge_70": "PASS" if would_use >= 70 else "FAIL",
            "would_recommend_ge_50": "PASS" if would_rec >= 50 else "FAIL",
            "would_join_waitlist_ge_40": "PASS" if would_wait >= 40 else "FAIL",
        },
    }

    output_path = args.output or input_path.replace(".jsonl", "_summary.json")
    with open(output_path, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Feedback collected: {total} entries")
    print(f"Output: {output_path}")
    print(json.dumps(summary["thresholds"], indent=2))


if __name__ == "__main__":
    main()