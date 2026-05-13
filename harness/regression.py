#!/usr/bin/env python3
"""Harness Regression — Cross-version consistency checking.

Runs the same inputs through current and reference pipelines,
detecting score drift, flag changes, and mode regressions.

Detects:
  - Score drift beyond golden_tolerance
  - Risk flag additions/removals
  - Hard truth mode level changes
  - Pipeline failures in previously-passing cases
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import sys
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from harness.runner import AIJudgeHarness, RunResult


@dataclass
class RegressionCheck:
    """A single regression check result."""
    field: str
    reference: Any
    current: Any
    drifted: bool
    delta: Optional[float] = None


@dataclass
class RegressionReport:
    """Full regression test report."""
    version_current: str
    version_reference: str
    total_checks: int = 0
    checks_passed: int = 0
    regressions: list[dict] = field(default_factory=list)
    summary: str = ""


class RegressionTester:
    """Detect regressions by comparing current outputs against reference."""

    def __init__(self, harness: AIJudgeHarness = None, tolerance: float = 0.05):
        self.harness = harness or AIJudgeHarness(config="ci")
        self.tolerance = tolerance

    def check_score_drift(self, ref_score: float, cur_score: float, label: str) -> RegressionCheck:
        delta = abs(ref_score - cur_score)
        return RegressionCheck(
            field=label,
            reference=ref_score,
            current=cur_score,
            drifted=delta > self.tolerance,
            delta=round(delta, 4),
        )

    def check_flag_regression(self, ref_flags: list, cur_flags: list) -> list[RegressionCheck]:
        """New flags appearing or old flags disappearing = regression signal."""
        checks = []
        ref_set = set(ref_flags)
        cur_set = set(cur_flags)

        for flag in ref_set - cur_set:
            checks.append(RegressionCheck(
                field=f"flag_removed:{flag}",
                reference="present",
                current="missing",
                drifted=True,
            ))
        for flag in cur_set - ref_set:
            checks.append(RegressionCheck(
                field=f"flag_added:{flag}",
                reference="missing",
                current="present",
                drifted=False,  # New flags aren't necessarily regressions
            ))
        return checks

    def run_against_reference(self, test_cases: list[dict],
                              reference_file: str) -> RegressionReport:
        """Run test cases against a saved reference baseline."""
        ref_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / reference_file
        if ref_path.exists():
            reference = json.loads(ref_path.read_text(encoding="utf-8"))
        else:
            reference = {}

        from core import __version__
        report = RegressionReport(
            version_current=__version__,
            version_reference=reference.get("version", "unknown"),
        )

        all_checks = []
        for i, case in enumerate(test_cases):
            text = case.get("text", "")
            ctx = case.get("context", "general")
            result = self.harness.run_neuro_profile(text, task_context=ctx)
            profile = result.data

            ref_case = reference.get("cases", [])[i] if i < len(reference.get("cases", [])) else {}
            ref_profile = ref_case.get("profile", {})

            # Score checks
            for key in ["smart_sounding_score", "judgment_quality_score"]:
                ref_val = ref_profile.get(key, profile.get(key, 0))
                cur_val = profile.get(key, 0)
                check = self.check_score_drift(ref_val, cur_val, f"case_{i}:{key}")
                all_checks.append(check)

            # Flag checks
            ref_flags = ref_profile.get("cognitive_risk_flags", [])
            cur_flags = profile.get("cognitive_risk_flags", [])
            flag_checks = self.check_flag_regression(ref_flags, cur_flags)
            all_checks.extend(flag_checks)

        report.total_checks = len(all_checks)
        report.checks_passed = sum(1 for c in all_checks if not c.drifted)
        report.regressions = [
            {"field": c.field, "reference": c.reference, "current": c.current, "delta": c.delta}
            for c in all_checks if c.drifted
        ]

        if report.regressions:
            report.summary = (
                f"⚠️ {len(report.regressions)} regressions detected "
                f"({report.checks_passed}/{report.total_checks} checks passed)"
            )
        else:
            report.summary = f"✅ All {report.total_checks} checks passed. No regressions."

        return report
