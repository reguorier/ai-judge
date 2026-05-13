#!/usr/bin/env python3
"""Harness Reporter — Standardized output formatting.

Supports: JSON, Markdown, HTML summary reports.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from harness.runner import RunResult
from harness.benchmark import BenchmarkSuite
from harness.regression import RegressionReport


def to_json(data: Any, pretty: bool = True) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2 if pretty else None, default=str)


def run_result_to_markdown(result: RunResult) -> str:
    """Format a single run result as markdown."""
    lines = [
        f"## Run: {result.run_id}",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Pipeline | {result.pipeline} |",
        f"| Config | {result.config_profile} |",
        f"| Elapsed | {result.elapsed_ms}ms |",
        f"| Passed | {'✅' if result.passed else '❌'} |",
    ]

    if result.errors:
        lines.append(f"| Errors | {len(result.errors)} |")
        for e in result.errors:
            lines.append(f"|   | {e[:100]} |")

    if result.warnings:
        lines.append(f"| Warnings | {len(result.warnings)} |")
        for w in result.warnings[:5]:
            lines.append(f"|   | {w[:100]} |")

    lines.append("")
    return "\n".join(lines)


def benchmark_to_markdown(suite: BenchmarkSuite) -> str:
    """Format benchmark suite as markdown."""
    lines = [
        f"# Benchmark: {suite.name}",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total cases | {suite.total} |",
        f"| Passed | {suite.passed} ✅ |",
        f"| Failed | {suite.failed} ❌ |",
        f"| Pass rate | {suite.pass_rate:.0%} |",
        f"",
    ]

    if suite.cases:
        lines.append("| Case | Label | Result | Checks |")
        lines.append("|------|-------|--------|--------|")
        for c in suite.cases:
            status = "✅" if c.passed else "❌"
            failed = sum(1 for ch in c.checks if not ch["passed"])
            lines.append(f"| {c.case_id} | {c.label} | {status} | {len(c.checks) - failed}/{len(c.checks)} |")

    lines.append("")
    return "\n".join(lines)


def regression_to_markdown(report: RegressionReport) -> str:
    """Format regression report as markdown."""
    lines = [
        f"# Regression Test",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Current version | {report.version_current} |",
        f"| Reference version | {report.version_reference} |",
        f"| Checks passed | {report.checks_passed}/{report.total_checks} |",
        f"| Regressions | {len(report.regressions)} |",
        f"",
        f"**{report.summary}**",
        f"",
    ]

    if report.regressions:
        lines.append("| Field | Reference | Current | Delta |")
        lines.append("|-------|-----------|---------|-------|")
        for r in report.regressions[:20]:
            lines.append(f"| {r['field']} | {r['reference']} | {r['current']} | {r.get('delta', '-')} |")

    lines.append("")
    return "\n".join(lines)


def full_report_to_html(
    benchmark_suites: list[BenchmarkSuite],
    regression_report: Optional[RegressionReport] = None,
) -> str:
    """Generate a standalone HTML summary report."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    passed_all = all(s.pass_rate == 1.0 for s in benchmark_suites)

    rows = ""
    for suite in benchmark_suites:
        color = "#2ea44f" if suite.pass_rate == 1.0 else "#cf222e"
        rows += f"""
        <tr>
            <td>{suite.name}</td>
            <td>{suite.total}</td>
            <td>{suite.passed}</td>
            <td>{suite.failed}</td>
            <td style="color:{color};font-weight:bold">{suite.pass_rate:.0%}</td>
        </tr>"""

    reg_section = ""
    if regression_report and regression_report.regressions:
        reg_rows = "".join(
            f"<tr><td>{r['field']}</td><td>{r['reference']}</td><td>{r['current']}</td></tr>"
            for r in regression_report.regressions[:10]
        )
        reg_section = f"""
        <h2>Regressions</h2>
        <table><tr><th>Field</th><th>Reference</th><th>Current</th></tr>
        {reg_rows}
        </table>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>AI Judge Harness Report</title>
<style>
body{{font-family:-apple-system,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;background:#0d1117;color:#c9d1d9}}
h1{{color:#58a6ff}}table{{width:100%;border-collapse:collapse;margin:16px 0}}
th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #30363d}}
th{{background:#161b22}}tr:hover{{background:#161b22}}
.pass{{color:#2ea44f}}.fail{{color:#cf222e}}
</style></head>
<body>
<h1>AI Judge Harness Report</h1>
<p>Generated: {timestamp} | Status: <span class="{'pass' if passed_all else 'fail'}">{'ALL PASSED' if passed_all else 'ISSUES FOUND'}</span></p>
<h2>Benchmark Suites</h2>
<table><tr><th>Suite</th><th>Total</th><th>Passed</th><th>Failed</th><th>Rate</th></tr>
{rows}
</table>
{reg_section}
</body></html>"""
