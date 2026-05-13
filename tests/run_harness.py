#!/usr/bin/env python3
"""AI Judge Harness — Full test suite runner.

Runs: benchmark, regression, and full pipeline smoke tests
through the harness layer. Exit code 0 = all pass.
"""

import json
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root))

from harness.runner import AIJudgeHarness
from harness.benchmark import GoldenBenchmark
from harness.regression import RegressionTester
from harness.reporter import (
    benchmark_to_markdown, regression_to_markdown,
    full_report_to_html, to_json,
)


def main():
    print("=" * 64)
    print("  AI Judge Harness — Full Test Suite")
    print("=" * 64)

    harness = AIJudgeHarness(config="ci")
    all_passed = True

    # ═══ Benchmark ═══
    print("\n[1/3] Golden Benchmark Suite...")
    bm = GoldenBenchmark(harness)
    suite = bm.run_suite("neuro_v3")
    print(benchmark_to_markdown(suite))
    if suite.pass_rate < 1.0:
        all_passed = False

    # ═══ Regression ═══
    print("\n[2/3] Regression Check...")
    rt = RegressionTester(harness)
    cases = bm.load_fixture("neuro_v3")
    report = rt.run_against_reference(cases, "baseline_v3.json")
    print(regression_to_markdown(report))
    if report.regressions:
        all_passed = False
        # Save current as new baseline for next run
        baseline = {
            "version": report.version_current,
            "cases": [],
        }
        for case in cases:
            result = harness.run_neuro_profile(case["text"], task_context=case.get("context", "general"))
            baseline["cases"].append({"profile": result.data})
        fixture_dir = Path(__file__).resolve().parent / "fixtures"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "baseline_v3.json").write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("  Baseline updated for next run.")

    # ═══ Smoke ═══
    print("\n[3/3] Full V3 Pipeline Smoke...")
    shallow = "我认为这个方案的核心在于底层逻辑的重构。我一直觉得AI时代的核心竞争力就是认知架构的升级。毫无疑问，我们需要通过多模型协同构建可信智能决策闭环。"
    deep = "我让9个模型分别答同一个问题，结果4个把截图当证据。后来改prompt才修复。但海外市场是否适用需要测试。如果反过来想，也许问题不在模型。"

    for label, text in [("Shallow", shallow), ("Deep", deep)]:
        result = harness.run_full_v3(text)
        print(f"  [{label}] passed={result.passed} | ss={result.data.get('dual_scores', {}).get('smart_sounding', 0):.2f} jq={result.data.get('dual_scores', {}).get('judgment_quality', 0):.2f}")
        if not result.passed and label == "Deep":
            all_passed = False

    # ═══ HTML Report ═══
    html = full_report_to_html([suite], report)
    report_path = Path(__file__).resolve().parents[1] / "harness-report.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"\n  HTML report: {report_path}")

    # ═══ Final ═══
    print(f"\n{'=' * 64}")
    if all_passed:
        print("  ✅ ALL CHECKS PASSED")
    else:
        print("  ❌ SOME CHECKS FAILED")
    print(f"{'=' * 64}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
