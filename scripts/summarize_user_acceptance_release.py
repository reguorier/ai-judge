#!/usr/bin/env python3
"""Summarize user acceptance release results into a JSON report.

Usage:
    python summarize_user_acceptance_release.py
        --total 12 --passed 12 --failed 0
        [--avg-decision-brief 88.5] [--avg-professional 82.1]
        [--avg-latency 46.2] [--output summary.json]

Output:
    JSON release summary with all required fields.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def build_summary(
    tasks_total: int,
    tasks_passed: int,
    tasks_failed: int = 0,
    avg_decision_brief_score: float = 0.0,
    avg_professional_review_score: float = 0.0,
    avg_latency_sec: float = 0.0,
    failure_recovery_passed: bool = False,
    artifact_validation_passed: bool = False,
    aj_report_v1_validation_passed: bool = False,
    human_feedback_sample_size: int = 0,
    human_feedback_avg_trust_score: Optional[float] = None,
) -> Dict[str, Any]:
    """Build the release summary dict."""
    return {
        "release": "deep-judge-user-acceptance-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tasks_total": tasks_total,
        "tasks_passed": tasks_passed,
        "tasks_failed": tasks_failed,
        "pass_rate_pct": round(tasks_passed / max(tasks_total, 1) * 100, 1),
        "avg_decision_brief_score": round(avg_decision_brief_score, 1),
        "avg_professional_review_score": round(avg_professional_review_score, 1),
        "avg_latency_sec": round(avg_latency_sec, 1),
        "failure_recovery_passed": failure_recovery_passed,
        "artifact_validation_passed": artifact_validation_passed,
        "aj_report_v1_validation_passed": aj_report_v1_validation_passed,
        "human_feedback": {
            "sample_size": human_feedback_sample_size,
            "avg_trust_score": human_feedback_avg_trust_score,
        },
        "thresholds": {
            "decision_brief_score_min": 80,
            "professional_review_score_min": 75,
            "tasks_total_min": 12,
        },
        "overall_pass": (
            tasks_total >= 12
            and tasks_passed == tasks_total
            and avg_decision_brief_score >= 80
            and avg_professional_review_score >= 75
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize deep_judge user acceptance release."
    )
    parser.add_argument("--total", type=int, required=True, help="Total tasks")
    parser.add_argument("--passed", type=int, required=True, help="Passed tasks")
    parser.add_argument("--failed", type=int, default=0, help="Failed tasks")
    parser.add_argument(
        "--avg-decision-brief", type=float, default=0.0,
        help="Average decision brief score"
    )
    parser.add_argument(
        "--avg-professional", type=float, default=0.0,
        help="Average professional review score"
    )
    parser.add_argument(
        "--avg-latency", type=float, default=0.0,
        help="Average latency in seconds"
    )
    parser.add_argument(
        "--failure-recovery-passed", action="store_true",
        help="Failure recovery suite passed"
    )
    parser.add_argument(
        "--artifact-validation-passed", action="store_true",
        help="Artifact validation passed"
    )
    parser.add_argument(
        "--aj-report-v1-passed", action="store_true",
        help="AJ Report V1 validation passed"
    )
    parser.add_argument(
        "--human-sample-size", type=int, default=0,
        help="Human feedback sample size"
    )
    parser.add_argument(
        "--human-avg-trust", type=float, default=None,
        help="Average human trust score"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--results", type=str, default=None,
        help="Path to results JSON file (unused placeholder)"
    )

    args = parser.parse_args()

    summary = build_summary(
        tasks_total=args.total,
        tasks_passed=args.passed,
        tasks_failed=args.failed,
        avg_decision_brief_score=args.avg_decision_brief,
        avg_professional_review_score=args.avg_professional,
        avg_latency_sec=args.avg_latency,
        failure_recovery_passed=args.failure_recovery_passed,
        artifact_validation_passed=args.artifact_validation_passed,
        aj_report_v1_validation_passed=args.aj_report_v1_passed,
        human_feedback_sample_size=args.human_sample_size,
        human_feedback_avg_trust_score=args.human_avg_trust,
    )

    output = json.dumps(summary, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Summary written to {args.output}")
    else:
        print(output)

    # Exit with appropriate code
    if summary["overall_pass"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()