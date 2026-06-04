#!/usr/bin/env python3
"""Run local launch-readiness checks for the compressed AI Judge growth plan.

This script is intentionally local-only: it checks files, copy, and the
deterministic citation benchmark. It does not post, send mail, open browsers, or
call external services.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-05-23"
REPORT_PATH = ROOT / "growth" / f"launch_readiness_report_{DATE}.md"
BENCH_PATH = ROOT / "growth" / f"launch_readiness_bench_result_{DATE}.json"


@dataclass
class Check:
    name: str
    status: str
    detail: str


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def exists_check(relative_path: str) -> Check:
    path = ROOT / relative_path
    if path.exists():
        return Check(relative_path, "pass", "exists")
    return Check(relative_path, "fail", "missing")


def contains_check(relative_path: str, needles: list[str]) -> list[Check]:
    path = ROOT / relative_path
    if not path.exists():
        return [Check(f"{relative_path} contains {needle}", "fail", "file missing") for needle in needles]
    text = path.read_text(encoding="utf-8")
    return [
        Check(
            f"{relative_path} contains {needle}",
            "pass" if needle in text else "fail",
            "found" if needle in text else "not found",
        )
        for needle in needles
    ]


def run_benchmark() -> tuple[Check, dict]:
    command = [
        sys.executable,
        "tools/run_citation_bench.py",
        "--fail-under",
        "0.95",
        "--output",
        str(BENCH_PATH),
    ]
    started = time.perf_counter()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    elapsed = round(time.perf_counter() - started, 3)

    result: dict = {
        "elapsed_seconds": elapsed,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }
    if BENCH_PATH.exists():
        try:
            result.update(json.loads(BENCH_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            result["json_error"] = str(exc)

    if completed.returncode == 0 and result.get("accuracy", 0) >= 0.95:
        return Check("citation benchmark", "pass", f"accuracy={result.get('accuracy')} elapsed={elapsed}s"), result
    return Check(
        "citation benchmark",
        "fail",
        f"returncode={completed.returncode} accuracy={result.get('accuracy')} elapsed={elapsed}s",
    ), result


def render_report(checks: list[Check], bench: dict) -> str:
    passed = sum(1 for check in checks if check.status == "pass")
    failed = sum(1 for check in checks if check.status == "fail")

    lines = [
        "# AI Judge Launch Readiness Report",
        "",
        f"Generated: {DATE}",
        "",
        "## Summary",
        "",
        f"- Passed checks: {passed}",
        f"- Failed checks: {failed}",
        f"- Benchmark accuracy: {bench.get('accuracy', 'not_run')}",
        f"- Benchmark elapsed seconds: {bench.get('elapsed_seconds', 'not_run')}",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")

    lines.extend(
        [
            "",
            "## Compressed Execution Decision",
            "",
            "Ship-readiness work should stay local and deterministic until platform gates clear.",
            "",
            "Safe next automated actions:",
            "",
            "- Re-run this script after README/docs/copy changes.",
            "- Re-run the citation benchmark after code changes.",
            "- Refresh growth queue/status files from local artifacts.",
            "",
            "Manual gates:",
            "",
            "- Hacker News: current account has a Show HN/site submission restriction recorded in growth logs.",
            "- Reddit: previous r/LocalLLaMA launch post was removed; do not repost the same text.",
            "- OpenReview/CMT/Product Hunt: stop at login, captcha, upload, payment, or final-submit.",
            "- Email/social/GitHub external actions: stop before final send/post/comment unless explicitly confirmed.",
            "",
            "## Benchmark Result File",
            "",
            f"- `{BENCH_PATH.relative_to(ROOT)}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    required_files = [
        "README.md",
        "docs/TRY_AI_JUDGE_IN_3_MINUTES.md",
        "docs/THREE_BLOCK_GOVERNANCE_PACKET.md",
        "growth/show_hn_launch_post.md",
        "growth/reddit_localllama_launch_post.md",
        "growth/huggingface_community_post.md",
        "growth/commercialization_offers_2026-05-20.md",
        "growth/cost_latency_baseline_2026-05-23.md",
        "growth/prospect_backlog_30_2026-05-23.csv",
        "growth/cold_start_email_templates_2026-05-23.md",
        "growth/outreach_batch_004_candidates_2026-05-23.md",
        "spaces/citation-audit/README.md",
        "citation-bench/citation-bench-100.jsonl",
        "tools/run_citation_bench.py",
    ]

    checks: list[Check] = [exists_check(path) for path in required_files]
    checks.extend(
        contains_check(
            "README.md",
            [
                "Source-isolated claim-support gate",
                "A source can exist and still fail to support the exact generated claim.",
                "Hugging Face Space",
                "citation-bench/citation-bench-100.jsonl",
            ],
        )
    )
    checks.extend(
        contains_check(
            "spaces/citation-audit/README.md",
            [
                "Runs without model APIs or browser bridges.",
                "Real source, unsupported causal claim",
            ],
        )
    )
    checks.extend(
        contains_check(
            "growth/show_hn_launch_post.md",
            [
                "Show HN:",
                "First Comment",
                "Likely HN Replies",
            ],
        )
    )
    checks.extend(
        contains_check(
            "growth/reddit_localllama_launch_post.md",
            [
                "LocalLLaMA",
                "First 5 Replies",
                "unverifiable",
            ],
        )
    )
    checks.extend(
        contains_check(
            "growth/commercialization_offers_2026-05-20.md",
            [
                "Citation Support Audit Sprint",
                "Open Source / Paid Boundary",
                "Pricing Validation Path",
            ],
        )
    )
    checks.extend(
        contains_check(
            "growth/cost_latency_baseline_2026-05-23.md",
            [
                "Benchmark accuracy",
                "0.128s",
                "model-free",
            ],
        )
    )
    checks.extend(
        contains_check(
            "growth/prospect_backlog_30_2026-05-23.csv",
            [
                "P030",
                "Legal RAG",
                "GitHub issue",
            ],
        )
    )
    checks.extend(
        contains_check(
            "growth/cold_start_email_templates_2026-05-23.md",
            [
                "Investor / Accelerator",
                "Conference / Workshop Organizer",
                "Legal / Compliance Researcher",
            ],
        )
    )

    benchmark_check, benchmark_result = run_benchmark()
    checks.append(benchmark_check)

    REPORT_PATH.write_text(render_report(checks, benchmark_result) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print(f"Wrote {BENCH_PATH.relative_to(ROOT)}")
    print(benchmark_check.detail)

    failed = [check for check in checks if check.status == "fail"]
    if failed:
        print("Failed checks:")
        for check in failed:
            print(f"- {check.name}: {check.detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
