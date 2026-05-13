#!/usr/bin/env python3
"""Harness Runner — Programmatic pipeline execution for AI Judge.

Single entry point for all pipeline operations. Wraps core modules
into reproducible, configurable runs with standardized output.

Usage:
    from harness import AIJudgeHarness
    h = AIJudgeHarness(config="default")
    result = h.score_text("Some claim text")
    result = h.run_neuro_profile("Some thinking text")
    result = h.run_full_v3("text", human_reason="...")
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import sys
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from harness.config import HarnessConfig, load_config


@dataclass
class RunResult:
    """Standardized result from any harness pipeline run."""
    run_id: str
    pipeline: str
    config_profile: str
    elapsed_ms: float
    passed: bool
    data: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class AIJudgeHarness:
    """Programmatic harness for AI Judge pipeline execution."""

    def __init__(self, config: str = "default", overrides: Optional[dict] = None):
        self.cfg = load_config(config, overrides)
        self._run_counter = 0

    def _run_id(self) -> str:
        self._run_counter += 1
        return f"run_{int(time.time())}_{self._run_counter:04d}"

    def _wrap(self, pipeline: str, data: dict, elapsed: float,
              errors: list = None, warnings: list = None) -> RunResult:
        passed = data.get("passed", True)
        if errors:
            passed = False
        return RunResult(
            run_id=self._run_id(),
            pipeline=pipeline,
            config_profile=self.cfg.profile,
            elapsed_ms=round(elapsed * 1000, 1),
            passed=passed,
            data=data,
            errors=errors or [],
            warnings=warnings or [],
        )

    # ── V2 Scoring ──

    def score_claims(self, claims: list[dict]) -> RunResult:
        """Run V2 claim scoring on a claim list."""
        from core.scoring_v2 import score_jury_v2

        t0 = time.time()
        try:
            result = score_jury_v2(claims)
            passed = result.get("average_score", 0) >= self.cfg.score_pass_threshold
            result["passed"] = passed
            return self._wrap("v2_scoring", result, time.time() - t0)
        except Exception as e:
            return self._wrap("v2_scoring", {}, time.time() - t0, errors=[str(e)])

    # ── V3 Neuro Profile ──

    def run_neuro_profile(self, text: str, task_context: str = "general",
                          conflict_context: dict = None) -> RunResult:
        """Run V3 neuro-cognitive profiling on text."""
        from core.neuro_profiler import compute_neuro_profile

        t0 = time.time()
        try:
            profile = compute_neuro_profile(text, task_context, conflict_context)

            # Check thresholds
            warnings = []
            sig = profile.get("signals", {})
            sc = sig.get("self_closure", {})
            af = sig.get("ambiguity_flexibility", {})

            if sc.get("self_closure_score", 0) > self.cfg.neuro_self_closure_warn:
                warnings.append(f"self_closure high: {sc['self_closure_score']:.2f}")
            if af.get("ambiguity_flexibility_score", 0) < self.cfg.neuro_ambiguity_warn:
                warnings.append(f"ambiguity low: {af['ambiguity_flexibility_score']:.2f}")

            gap = profile.get("smart_vs_judgment_gap", 0)
            if gap > self.cfg.ss_jq_gap_critical:
                warnings.append(f"ss/jq gap critical: {gap:.0%}")

            profile["passed"] = len(warnings) == 0
            return self._wrap("v3_neuro_profile", profile, time.time() - t0, warnings=warnings)
        except Exception as e:
            return self._wrap("v3_neuro_profile", {}, time.time() - t0, errors=[str(e)])

    # ── V3 Hard Truth ──

    def run_hard_truth(self, neuro_profile: dict) -> RunResult:
        """Determine hard truth mode from neuro profile."""
        from core.hard_truth import determine_mode, generate_hard_truth_output

        t0 = time.time()
        try:
            mode = determine_mode(neuro_profile)
            output = ""
            if mode.get("hard_truth_active"):
                text = neuro_profile.get("signals", {}).get("_original_text", "")
                output = generate_hard_truth_output(neuro_profile, text)

            result = {
                "mode": mode,
                "hard_truth_output": output[:500] if output else None,
                "passed": mode["mode_level"] < 2,  # L2+ is "not passed" in CI
            }
            return self._wrap("v3_hard_truth", result, time.time() - t0)
        except Exception as e:
            return self._wrap("v3_hard_truth", {}, time.time() - t0, errors=[str(e)])

    # ── Full V3 Pipeline ──

    def run_full_v3(self, text: str, human_reason: str = "",
                    task_context: str = "general",
                    model_scores: dict = None) -> RunResult:
        """Run the complete V3 pipeline: scoring + determinism + neuro + hard truth."""
        from core.neuro_profiler import compute_neuro_profile
        from core.determinism import run_full_v3_pipeline
        from core.scoring_v2 import score_jury_v2

        t0 = time.time()
        try:
            # Step 1: Neuro profile
            profile = compute_neuro_profile(text, task_context=task_context)

            # Step 2: Simulated judge samples (in production, these come from real runs)
            # For harness, we use the neuro profile's scores as proxy
            jq = profile.get("judgment_quality_score", 0.5)
            samples = [
                {"score": jq * 10, "tier": "credible"},
                {"score": jq * 10, "tier": "credible"},
                {"score": jq * 10, "tier": "credible"},
            ]

            # Step 3: Full V3 pipeline
            model_scores = model_scores or {"GPT": jq * 10, "Claude": jq * 10 * 0.95}
            result = run_full_v3_pipeline(
                judge_samples=samples,
                model_scores=model_scores,
                human_reason=human_reason or "Harness automated run.",
                neuro_profile=profile,
            )

            passed = (
                result.get("verdict_exportable", False)
                and not (result.get("hard_truth_mode", {}).get("active", False))
            )
            result["passed"] = passed

            return self._wrap("v3_full_pipeline", result, time.time() - t0)
        except Exception as e:
            return self._wrap("v3_full_pipeline", {}, time.time() - t0, errors=[str(e)])

    # ── Batch Runner ──

    def run_batch(self, texts: list[dict]) -> list[RunResult]:
        """Run a batch of texts through the full V3 pipeline."""
        results = []
        for item in texts:
            text = item.get("text", "")
            ctx = item.get("context", "general")
            reason = item.get("human_reason", "")
            result = self.run_full_v3(text, human_reason=reason, task_context=ctx)
            results.append(result)
        return results
