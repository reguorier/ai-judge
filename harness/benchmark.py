#!/usr/bin/env python3
"""Harness Benchmark — Golden-dataset testing with pass/fail thresholds.

Loads golden fixture files, runs them through the harness, and
compares results against known-good baselines.

Golden dataset format (tests/fixtures/golden_*.json):
    [
      {
        "id": "case_001",
        "label": "shallow_strategic_jargon",
        "text": "...",
        "context": "strategy",
        "expected": {
          "smart_sounding_min": 0.80,
          "judgment_quality_max": 0.75,
          "gap_min": 0.15,
          "risk_flags_contains": ["self_reference_closure"],
          "hard_truth_level_min": 1
        }
      }
    ]
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
class BenchmarkResult:
    """Result of a single benchmark case."""
    case_id: str
    label: str
    passed: bool
    checks: list[dict] = field(default_factory=list)
    actual: dict = field(default_factory=dict)
    expected: dict = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Full benchmark suite result."""
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    cases: list[BenchmarkResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / max(1, self.total)


class GoldenBenchmark:
    """Run AI Judge against golden datasets and verify expected behavior."""

    def __init__(self, harness: AIJudgeHarness = None):
        self.harness = harness or AIJudgeHarness(config="ci")

    def load_fixture(self, name: str) -> list[dict]:
        """Load a golden fixture file."""
        fixture_dir = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
        path = fixture_dir / f"golden_{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Fixture not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def run_case(self, case: dict) -> BenchmarkResult:
        """Run a single benchmark case and verify expectations."""
        text = case["text"]
        ctx = case.get("context", "general")
        expected = case.get("expected", {})

        # Run neuro profile
        result = self.harness.run_neuro_profile(text, task_context=ctx)
        profile = result.data

        checks = []
        ss = profile.get("smart_sounding_score", 0)
        jq = profile.get("judgment_quality_score", 0)
        gap = profile.get("smart_vs_judgment_gap", 0)
        flags = profile.get("cognitive_risk_flags", [])

        # Check smart_sounding minimum
        if "smart_sounding_min" in expected:
            ok = ss >= expected["smart_sounding_min"]
            checks.append({"check": "smart_sounding_min", "passed": ok,
                          "expected": f">= {expected['smart_sounding_min']}", "actual": round(ss, 3)})

        # Check judgment_quality maximum
        if "judgment_quality_max" in expected:
            ok = jq <= expected["judgment_quality_max"]
            checks.append({"check": "judgment_quality_max", "passed": ok,
                          "expected": f"<= {expected['judgment_quality_max']}", "actual": round(jq, 3)})

        # Check gap minimum
        if "gap_min" in expected:
            ok = gap >= expected["gap_min"]
            checks.append({"check": "gap_min", "passed": ok,
                          "expected": f">= {expected['gap_min']}", "actual": round(gap, 3)})

        # Check risk flags
        if "risk_flags_contains" in expected:
            for flag in expected["risk_flags_contains"]:
                ok = flag in flags
                checks.append({"check": f"risk_flag:{flag}", "passed": ok,
                              "expected": "present", "actual": "present" if ok else "missing"})

        # Check hard truth level
        if "hard_truth_level_min" in expected:
            from core.hard_truth import determine_mode
            mode = determine_mode(profile)
            level = mode.get("mode_level", 0)
            ok = level >= expected["hard_truth_level_min"]
            checks.append({"check": "hard_truth_level", "passed": ok,
                          "expected": f">= {expected['hard_truth_level_min']}", "actual": level})

        all_passed = all(c["passed"] for c in checks)

        return BenchmarkResult(
            case_id=case.get("id", "unknown"),
            label=case.get("label", ""),
            passed=all_passed,
            checks=checks,
            actual={"ss": round(ss, 3), "jq": round(jq, 3), "gap": round(gap, 3), "flags": flags},
            expected=expected,
        )

    def run_suite(self, fixture_name: str) -> BenchmarkSuite:
        """Run a full benchmark suite from a fixture file."""
        cases = self.load_fixture(fixture_name)
        suite = BenchmarkSuite(name=fixture_name, total=len(cases))

        for case in cases:
            br = self.run_case(case)
            suite.cases.append(br)
            if br.passed:
                suite.passed += 1
            else:
                suite.failed += 1

        return suite
