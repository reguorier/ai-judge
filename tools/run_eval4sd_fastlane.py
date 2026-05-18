#!/usr/bin/env python3
"""Run the compressed Eval4SD readiness lane.

This command is intentionally boring: it does not submit anything, publish
anything, or touch browser sessions. It only checks the anonymous submission
packet and deterministic citation benchmarks, then writes a small receipt that
can be referenced from growth, HN, or paper-prep work.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "papers" / "eval4sd2026" / "fastlane_status.json"
DEFAULT_MD = ROOT / "papers" / "eval4sd2026" / "fastlane_status.md"


def run_step(name: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    parsed: Any = None
    if result.returncode == 0:
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "name": name,
        "command": " ".join(command),
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "parsed": parsed,
        "output": result.stdout.strip(),
    }


def summarize_benchmark(step: dict[str, Any]) -> str:
    parsed = step.get("parsed") or {}
    if not parsed:
        return "not parsed"
    return (
        f"{parsed.get('passed', '-')}/{parsed.get('total', '-')} passed, "
        f"accuracy {parsed.get('accuracy', '-')}"
    )


def build_receipt(steps: list[dict[str, Any]]) -> dict[str, Any]:
    packet = next((step for step in steps if step["name"] == "packet"), {})
    packet_parsed = packet.get("parsed") or {}
    ready = all(step["passed"] for step in steps)
    return {
        "schema": "eval4sd.fastlane.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready_for_form_fill": ready,
        "does_not_submit": True,
        "anonymous_packet": packet_parsed.get("anonymous") is True,
        "paper": packet_parsed.get("paper", "papers/eval4sd2026/main.tex"),
        "pdf": packet_parsed.get("pdf", "papers/eval4sd2026/main.pdf"),
        "openreview_packet": packet_parsed.get(
            "openreview_packet",
            "papers/eval4sd2026/openreview_submission.json",
        ),
        "steps": steps,
        "next_manual_gate": (
            "OpenReview account access or organizer backup route; final submission still requires action-time confirmation."
        ),
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    rows = []
    for step in receipt["steps"]:
        if step["name"] in {"bench-100", "hard-13"}:
            detail = summarize_benchmark(step)
        elif step["name"] == "packet":
            parsed = step.get("parsed") or {}
            benchmarks = parsed.get("benchmarks", {})
            detail = (
                f"anonymous={parsed.get('anonymous', '-')}; "
                f"full={benchmarks.get('full', {}).get('passed', '-')}/"
                f"{benchmarks.get('full', {}).get('total', '-')}; "
                f"hard={benchmarks.get('hard', {}).get('passed', '-')}/"
                f"{benchmarks.get('hard', {}).get('total', '-')}"
            )
        else:
            detail = "passed" if step["passed"] else "failed"
        status = "PASS" if step["passed"] else "FAIL"
        rows.append(f"| {step['name']} | {status} | `{step['command']}` | {detail} |")

    return "\n".join(
        [
            "# Eval4SD Fastlane Status",
            "",
            f"Generated: `{receipt['generated_at']}`",
            "",
            f"Ready for form fill: **{receipt['ready_for_form_fill']}**",
            "",
            "This receipt does not submit the paper, send emails, publish posts, or solve CAPTCHA.",
            "",
            "| Step | Status | Command | Detail |",
            "|---|---|---|---|",
            *rows,
            "",
            "## Submission Assets",
            "",
            f"- Paper source: `{receipt['paper']}`",
            f"- PDF: `{receipt['pdf']}`",
            f"- OpenReview packet: `{receipt['openreview_packet']}`",
            "",
            "## Manual Gate",
            "",
            receipt["next_manual_gate"],
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Eval4SD compressed readiness lane.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    parser.add_argument("--markdown-output", default=str(DEFAULT_MD))
    args = parser.parse_args()

    steps = [
        run_step(
            "packet",
            [sys.executable, "tools/check_eval4sd_packet.py"],
        ),
        run_step(
            "bench-100",
            [sys.executable, "tools/run_citation_bench.py", "--fail-under", "0.95"],
        ),
        run_step(
            "hard-13",
            [
                sys.executable,
                "tools/run_citation_bench.py",
                "--bench",
                "citation-bench/citation-bench-hard-11.jsonl",
                "--fail-under",
                "0.95",
            ],
        ),
    ]
    receipt = build_receipt(steps)

    json_path = Path(args.json_output)
    md_path = Path(args.markdown_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(receipt), encoding="utf-8")

    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["ready_for_form_fill"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
