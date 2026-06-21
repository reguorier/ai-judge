#!/usr/bin/env python3
"""collect_controlled_demo_feedback.py — Controlled Demo 反馈采集脚本

用法:
    python scripts/collect_controlled_demo_feedback.py --input runtime/product/demo_launch/controlled_demo_feedback.jsonl
"""

import argparse
import json
import sys
from datetime import datetime, timezone


REQUIRED_FIELDS = [
    "feedback_id", "user_id", "run_id", "task_id", "reader_type",
    "is_external_user", "can_state_final_answer", "can_state_next_step",
    "can_explain_why", "trust_score_1_to_5", "readability_score_1_to_5",
    "actionability_score_1_to_5", "would_use_again", "confusing_part",
    "free_text", "created_at"
]


def validate_feedback(entry: dict) -> list[str]:
    """Validate a single feedback entry, return list of issues."""
    issues = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            issues.append(f"missing field: {field}")
            continue

    # Score range validation (nullable for failed runs)
    for score_field in ["trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5"]:
        val = entry.get(score_field)
        if val is not None:
            if not isinstance(val, (int, float)) or val < 1 or val > 5:
                issues.append(f"{score_field} out of range: {val}")

    return issues


def collect(input_path: str) -> dict:
    """Read and validate feedback file, return summary."""
    entries = []
    issues = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entry_issues = validate_feedback(entry)
                if entry_issues:
                    issues.append({"line": line_no, "feedback_id": entry.get("feedback_id", "?"), "issues": entry_issues})
                entries.append(entry)
            except json.JSONDecodeError as e:
                issues.append({"line": line_no, "error": str(e)})

    # Calculate statistics (exclude null-score entries — failed runs)
    scored = [e for e in entries if e.get("trust_score_1_to_5") is not None]
    external = [e for e in entries if e.get("is_external_user")]

    summary = {
        "file": input_path,
        "total_entries": len(entries),
        "scored_entries": len(scored),
        "external_entries": len(external),
        "coverage_pct": round(len(scored) / max(len(entries), 1) * 100, 1),
        "validation_issues": len(issues),
        "issue_details": issues if issues else "none",
        "scores": {
            "avg_trust": round(sum(e["trust_score_1_to_5"] for e in scored) / max(len(scored), 1), 2),
            "avg_readability": round(sum(e["readability_score_1_to_5"] for e in scored) / max(len(scored), 1), 2),
            "avg_actionability": round(sum(e["actionability_score_1_to_5"] for e in scored) / max(len(scored), 1), 2),
        },
        "would_use_again_pct": round(
            sum(1 for e in scored if e.get("would_use_again")) / max(len(scored), 1) * 100, 1
        ),
        "can_state_final_answer_pct": round(
            sum(1 for e in scored if e.get("can_state_final_answer")) / max(len(scored), 1) * 100, 1
        ),
        "can_state_next_step_pct": round(
            sum(1 for e in scored if e.get("can_state_next_step")) / max(len(scored), 1) * 100, 1
        ),
        "can_explain_why_pct": round(
            sum(1 for e in scored if e.get("can_explain_why")) / max(len(scored), 1) * 100, 1
        ),
    }

    return summary


def main():
    parser = argparse.ArgumentParser(description="Collect controlled demo feedback")
    parser.add_argument("--input", required=True, help="Path to feedback JSONL file")
    args = parser.parse_args()

    try:
        summary = collect(args.input)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()