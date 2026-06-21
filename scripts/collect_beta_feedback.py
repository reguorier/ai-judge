#!/usr/bin/env python3
"""
collect_beta_feedback.py

Collects user feedback for Deep Judge beta operations.
Supports interactive collection (prompt-based) and batch import from JSONL/CSV.

Usage:
    python collect_beta_feedback.py --interactive
    python collect_beta_feedback.py --input feedback.jsonl --output collected.jsonl
    python collect_beta_feedback.py --validate feedback.jsonl
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Path to feedback schema and task bank
DEFAULT_RUNTIME = Path.home() / "Library/Application Support/AI Judge/runtime/product"
FEEDBACK_SCHEMA_PATH = DEFAULT_RUNTIME / "beta_ops/beta_user_feedback_schema.json"
TASK_BANK_PATH = DEFAULT_RUNTIME / "beta_ops/beta_task_bank.json"


def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_feedback_entry(entry: dict, task_bank: list[dict]) -> list[str]:
    """Validate a single feedback entry against the schema. Returns list of errors."""
    errors = []
    required_fields = [
        "feedback_id", "task_id", "run_id", "reader_type",
        "can_state_final_answer", "can_state_next_step", "can_explain_why",
        "trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5",
        "confusing_part", "missing_information", "would_use_again", "free_text", "created_at",
    ]
    for field in required_fields:
        if field not in entry:
            errors.append(f"Missing required field: {field}")

    # Validate task_id exists in task bank
    if entry.get("task_id"):
        task_ids = {t["id"] for t in task_bank}
        if entry["task_id"] not in task_ids:
            errors.append(f"Unknown task_id: {entry['task_id']} — not found in task bank")

    # Validate reader_type
    valid_reader_types = ["普通用户", "专业用户", "PM", "创始人"]
    if entry.get("reader_type") and entry["reader_type"] not in valid_reader_types:
        errors.append(f"Invalid reader_type: {entry['reader_type']}. Must be one of {valid_reader_types}")

    # Validate score ranges
    for score_field in ["trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5"]:
        val = entry.get(score_field)
        if val is not None and (not isinstance(val, (int, float)) or val < 1 or val > 5):
            errors.append(f"{score_field} must be 1-5, got: {val}")

    # Validate booleans
    for bool_field in ["can_state_final_answer", "can_state_next_step", "can_explain_why", "would_use_again"]:
        val = entry.get(bool_field)
        if val is not None and not isinstance(val, bool):
            errors.append(f"{bool_field} must be boolean, got: {type(val).__name__}")

    # Validate created_at format (ISO-8601)
    created_at = entry.get("created_at", "")
    if created_at:
        try:
            datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            errors.append(f"Invalid ISO-8601 created_at: {created_at}")

    return errors


def collect_interactive(task_bank: list[dict]) -> dict:
    """Interactive feedback collection from command line."""
    print("=" * 50)
    print("  Deep Judge Beta — Interactive Feedback Collector")
    print("=" * 50)
    print()

    # 1. Select task
    print("Available tasks:")
    for i, t in enumerate(task_bank[:20], 1):
        print(f"  {i:3d}. [{t['id']}] {t['question'][:60]}...")
    print()
    task_idx = input(f"Select task number (1-{min(20, len(task_bank))}): ").strip()
    try:
        idx = int(task_idx) - 1
        task = task_bank[idx]
    except (ValueError, IndexError):
        print("[ERROR] Invalid selection.")
        sys.exit(1)

    feedback = {
        "feedback_id": f"FB-{uuid.uuid4().hex[:8]}",
        "task_id": task["id"],
        "run_id": input("Run ID (or press Enter to skip): ").strip() or f"RUN-{uuid.uuid4().hex[:8]}",
    }

    # 2. Reader type
    print("\nReader types: 1=普通用户 2=专业用户 3=PM 4=创始人")
    rt_map = {"1": "普通用户", "2": "专业用户", "3": "PM", "4": "创始人"}
    rt_choice = input("Select reader type (1-4): ").strip()
    feedback["reader_type"] = rt_map.get(rt_choice, "普通用户")

    # 3. Core questions
    def yn(prompt: str) -> bool:
        ans = input(f"{prompt} (y/n): ").strip().lower()
        return ans.startswith("y")

    print("\n--- Core questions ---")
    feedback["can_state_final_answer"] = yn("Can you state the final answer clearly?")
    feedback["can_state_next_step"] = yn("Can you identify a concrete next step?")
    feedback["can_explain_why"] = yn("Can you explain the reasoning behind the conclusion?")

    # 4. Scores
    print("\n--- Scores (1=worst, 5=best) ---")
    feedback["trust_score_1_to_5"] = int(input("Trust score (1-5): ").strip() or "3")
    feedback["readability_score_1_to_5"] = int(input("Readability score (1-5): ").strip() or "3")
    feedback["actionability_score_1_to_5"] = int(input("Actionability score (1-5): ").strip() or "3")

    # 5. Open text
    print("\n--- Open feedback ---")
    feedback["confusing_part"] = input("What was confusing? (Enter to skip): ").strip()
    feedback["missing_information"] = input("What information was missing? (Enter to skip): ").strip()
    feedback["would_use_again"] = yn("Would you use Deep Judge again?")
    feedback["free_text"] = input("Any other feedback? (Enter to skip): ").strip()

    feedback["created_at"] = datetime.now(timezone.utc).isoformat()

    return feedback


def main():
    parser = argparse.ArgumentParser(description="Deep Judge Beta Feedback Collector")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive feedback collection")
    parser.add_argument("--input", "-f", default=None, help="Input JSONL file to validate/import")
    parser.add_argument("--output", "-o", default=None, help="Output JSONL file to append collected feedback")
    parser.add_argument("--validate", action="store_true", help="Validate input feedback without collecting")
    args = parser.parse_args()

    # Load task bank for validation
    task_bank = []
    if TASK_BANK_PATH.exists():
        task_bank = load_json(TASK_BANK_PATH)
    else:
        print(f"[WARN] Task bank not found at {TASK_BANK_PATH}")

    collected = []

    if args.interactive:
        if not task_bank:
            print("[ERROR] Task bank required for interactive mode.")
            sys.exit(1)
        entry = collect_interactive(task_bank)
        errors = validate_feedback_entry(entry, task_bank)
        if errors:
            print(f"\n[WARN] Validation issues:")
            for e in errors:
                print(f"  - {e}")
        collected.append(entry)
        print(f"\n[OK] Feedback collected: {entry['feedback_id']}")

    elif args.input:
        # Load existing feedback
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"[ERROR] Input file not found: {args.input}")
            sys.exit(1)

        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        if input_path.suffix == ".jsonl":
            records = []
            for line in content.strip().split("\n"):
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"[WARN] Invalid JSONL line: {e}")
        else:
            data = json.loads(content)
            records = data if isinstance(data, list) else [data]

        all_errors = []
        for i, record in enumerate(records):
            errors = validate_feedback_entry(record, task_bank)
            if errors:
                all_errors.append({"index": i, "feedback_id": record.get("feedback_id", ""), "errors": errors})
            else:
                collected.append(record)

        if all_errors:
            print(f"[WARN] {len(all_errors)} records have validation issues:")
            for ae in all_errors[:10]:
                print(f"  Record {ae['index']} ({ae['feedback_id']}):")
                for e in ae["errors"]:
                    print(f"    - {e}")

        print(f"[OK] {len(collected)} valid records loaded")

    # Write output
    if args.output and collected:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in collected:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[OK] {len(collected)} records written to {args.output}")

    sys.exit(0 if collected else 1)


if __name__ == "__main__":
    main()