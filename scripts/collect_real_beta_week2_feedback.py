#!/usr/bin/env python3
"""collect_real_beta_week2_feedback.py — 收集并校验 Week 2 外部用户反馈"""
import argparse
import json
import sys


def validate_feedback(entry: dict, run_registry: list[dict], roster: list[dict]) -> list[str]:
    errors = []

    # Required fields
    required = [
        "feedback_id", "week", "task_id", "run_id", "user_id",
        "reader_type", "is_external_user", "can_state_final_answer",
        "can_state_next_step", "can_explain_why",
        "trust_score_1_to_5", "readability_score_1_to_5",
        "actionability_score_1_to_5", "confusing_part",
        "missing_information", "would_use_again", "free_text", "created_at"
    ]
    for field in required:
        if field not in entry:
            errors.append(f"{entry.get('feedback_id', '?')}: missing field '{field}'")

    if errors:
        return errors

    # user_id must exist in roster
    roster_ids = {u["user_id"] for u in roster}
    if entry["user_id"] not in roster_ids:
        errors.append(f"{entry['feedback_id']}: user_id '{entry['user_id']}' not in roster")

    # is_external_user must be true
    if not entry["is_external_user"]:
        errors.append(f"{entry['feedback_id']}: is_external_user must be true for Week 2")

    # Score ranges (only validate if not null — failed tasks may have null)
    for field in ["trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5"]:
        val = entry.get(field)
        if val is not None:
            if not isinstance(val, (int, float)) or val < 1 or val > 5:
                errors.append(f"{entry['feedback_id']}: {field} must be 1-5, got {val}")

    # run_id/task_id must exist in registry
    registry_runs = {(r["run_id"], r["task_id"]) for r in run_registry}
    if (entry["run_id"], entry["task_id"]) not in registry_runs:
        errors.append(f"{entry['feedback_id']}: run_id/task_id ({entry['run_id']}/{entry['task_id']}) not in registry")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Collect and validate Week 2 beta feedback")
    parser.add_argument("--input", required=True, help="Path to feedback.jsonl")
    args = parser.parse_args()

    # Load dependencies
    runtime = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops"
    with open(f"{runtime}/beta_week2_user_roster.json") as f:
        roster = json.load(f)
    with open(f"{runtime}/beta_week2_run_registry.json") as f:
        run_registry = json.load(f)

    # Load feedback
    feedback = []
    with open(args.input) as f:
        for line in f:
            line = line.strip()
            if line:
                feedback.append(json.loads(line))

    print(f"Total feedback entries: {len(feedback)}")

    # Validate each entry
    all_errors = []
    for entry in feedback:
        errs = validate_feedback(entry, run_registry, roster)
        all_errors.extend(errs)

    # Check: each completed run has at least one feedback
    completed_runs = {r["run_id"] for r in run_registry if r["status"] in ("completed", "degraded")}
    feedbacked_runs = {e["run_id"] for e in feedback}
    missing_feedback = completed_runs - feedbacked_runs

    # Summary
    n_scored = sum(1 for e in feedback if e["trust_score_1_to_5"] is not None)
    n_failed = sum(1 for e in feedback if e["trust_score_1_to_5"] is None)
    avg_trust = sum(e["trust_score_1_to_5"] for e in feedback if e["trust_score_1_to_5"] is not None) / max(n_scored, 1)

    print(f"Entries with scores: {n_scored}")
    print(f"Entries without scores (failed): {n_failed}")
    print(f"Average trust score: {avg_trust:.2f}")
    print(f"Validation errors: {len(all_errors)}")
    if all_errors:
        for err in all_errors:
            print(f"  ERROR: {err}")

    if missing_feedback:
        print(f"WARNING: {len(missing_feedback)} completed/degraded runs have no feedback")
        for rid in missing_feedback:
            print(f"  Missing: {rid}")

    if all_errors:
        print("VALIDATION_FAILED")
        sys.exit(1)
    else:
        print("FEEDBACK_COLLECTION_PASS")


if __name__ == "__main__":
    main()