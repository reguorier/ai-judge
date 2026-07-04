#!/usr/bin/env python3
"""AI Judge Client: minimal report-first local entrypoint.

This command intentionally avoids dashboard behavior. It submits a run, prints a
compact status, and points the user to the generated final report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from client.notification import notify
from client.report_viewer import report_summary
from client.run_submitter import submit_api, submit_direct
from product.run_orchestrator import archive_client_run, followup_client_run, get_client_report

DEFAULT_SMOKE_QUESTION = "请判断当前 AI Judge 是否应该继续开发 Dashboard？"


def _claim_source_counts(run: dict) -> dict:
    for candidate in (run.get("claim_source_support"), run.get("claim_support_audit"), run):
        if isinstance(candidate, dict) and isinstance(candidate.get("support_verdict_counts"), dict):
            return {
                "counts": candidate.get("support_verdict_counts") or {},
                "overall": candidate.get("overall_support_verdict", ""),
                "pass_rate": candidate.get("claim_support_pass_rate", 0.0),
            }
    return {"counts": {}, "overall": "", "pass_rate": 0.0}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal report-first AI Judge client")
    parser.add_argument("--question", default="", help="Question to judge")
    parser.add_argument("--mode", default="deep_judge", help="quick_judge, deep_judge, ops_check, prediction_pool, simulation_game")
    parser.add_argument("--api-base", default="", help="Optional local API base, e.g. http://127.0.0.1:8501")
    parser.add_argument("--no-auto-complete", action="store_true", help="Create a running backend state without generating final report")
    parser.add_argument("--followup", default="", help="Write a follow-up note for the generated run")
    parser.add_argument("--archive", action="store_true", help="Archive generated final report, falling back to local pending")
    parser.add_argument("--smoke", action="store_true", help="Run a deterministic local smoke flow")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    question = args.question or (DEFAULT_SMOKE_QUESTION if args.smoke else "")
    if not question.strip():
        print("ERROR: --question is required unless --smoke is used", file=sys.stderr)
        return 2
    if args.api_base:
        response = submit_api(args.api_base, question, args.mode, auto_complete=not args.no_auto_complete)
        run = response.get("run") or response
    else:
        run = submit_direct(question, args.mode, auto_complete=not args.no_auto_complete)
    print(notify("AI Judge", run.get("human_status", "run submitted")))
    print(report_summary(run))
    if run.get("noise_score") is not None:
        print(
            "noise: "
            f"{run.get('noise_score')}/100 "
            f"level={run.get('noise_level', 'unknown')} "
            f"action={run.get('noise_recommended_action', 'unknown')}"
        )
    claim_source = _claim_source_counts(run)
    if claim_source["counts"]:
        counts = claim_source["counts"]
        print(
            "claim_source_support: "
            f"overall={claim_source.get('overall') or 'unknown'} "
            f"pass_rate={claim_source.get('pass_rate', 0.0)} "
            f"supported={counts.get('supported', 0)} "
            f"unsupported_by_cited_source={counts.get('unsupported_by_cited_source', 0)} "
            f"contradicted={counts.get('contradicted', 0)} "
            f"not_enough_evidence={counts.get('not_enough_evidence', 0)}"
        )
    if run.get("status") == "completed":
        report = get_client_report(str(run["run_id"]))
        print(f"final_report.md: {report.get('final_report_path')}")
        print(f"final_report.html: {report.get('html_report_path')}")
    if args.followup:
        followup = followup_client_run(str(run["run_id"]), args.followup)
        if followup.get("followup_path"):
            print(f"followup: {followup['followup_path']}")
        else:
            print(
                "followup: not_generated "
                f"reason={followup.get('reason', 'unknown')} "
                f"message={followup.get('message', '')}"
            )
    if args.archive:
        try:
            archive = archive_client_run(str(run["run_id"]))
        except Exception as exc:
            print(f"archive: not_generated reason={type(exc).__name__} message={exc}")
        else:
            print(f"archive: {archive.get('archive_path', '')}")
    if args.smoke:
        print("[PASS] client can start")
        print("[PASS] client can submit run")
        print("[PASS] dashboard not required for user flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
