#!/usr/bin/env python3
"""Run the Citation Hallucination Benchmark.

The benchmark is intentionally small and deterministic so it can run in a
GitHub Action without model APIs or browser bridges.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.citation_audit import run_citation_audit


def load_cases(path: str | Path) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_benchmark(path: str | Path) -> dict:
    rows = []
    for case in load_cases(path):
        verdict = run_citation_audit(
            title=f"Benchmark {case['id']}",
            question=case["question"],
            answer=case["answer"],
            external_evidence=case.get("external_evidence") or [],
            run_id=f"bench-{case['id'].lower()}",
            generated_at="2026-05-16T00:00:00+00:00",
        )
        actual = verdict["summary"]["overall_status"]
        expected = case["expected_status"]
        rows.append({
            "id": case["id"],
            "category": case["category"],
            "expected": expected,
            "actual": actual,
            "passed": actual == expected,
        })
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    by_category: dict[str, dict[str, int]] = {}
    for row in rows:
        category = row["category"]
        bucket = by_category.setdefault(category, {"passed": 0, "total": 0})
        bucket["total"] += 1
        bucket["passed"] += int(row["passed"])
    return {
        "schema": "citation_bench.result.v1",
        "benchmark": str(path),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "by_category": by_category,
        "failures": [row for row in rows if not row["passed"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AI Judge citation benchmark")
    parser.add_argument("--bench", default="citation-bench/citation-bench-100.jsonl")
    parser.add_argument("--output", default="")
    parser.add_argument("--fail-under", type=float, default=0.95)
    args = parser.parse_args()
    result = run_benchmark(args.bench)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0 if result["accuracy"] >= args.fail_under else 1


if __name__ == "__main__":
    raise SystemExit(main())
