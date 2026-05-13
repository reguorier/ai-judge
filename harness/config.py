#!/usr/bin/env python3
"""Harness Config — YAML-based configuration profiles for AI Judge pipelines.

Supports:
  - Named profiles (default, strict, fast, ci)
  - Override via environment variables (AI_JUDGE_*)
  - Determinism parameters (temperature, samples, seed)
  - Score thresholds for pass/fail
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class HarnessConfig:
    """Configuration for an AI Judge harness run."""
    profile: str = "default"

    # Determinism
    l1_samples: int = 3
    l1_required_matches: int = 3
    l1_strict_mode: bool = True

    # Scoring thresholds
    score_pass_threshold: float = 0.50
    jq_pass_threshold: float = 0.50
    ss_jq_gap_warn: float = 0.20
    ss_jq_gap_critical: float = 0.30

    # Confidence
    confidence_cap: float = 0.95

    # Human tax
    human_tax_min_chars: int = 20

    # Neuro profile
    neuro_enabled: bool = True
    neuro_self_closure_warn: float = 0.60
    neuro_ambiguity_warn: float = 0.35

    # Hard truth
    hard_truth_enabled: bool = True

    # Reporting
    output_format: str = "json"  # json, markdown, html
    verbose: bool = False

    # Golden dataset
    golden_tolerance: float = 0.05  # Acceptable score drift from golden


# ── Pre-built profiles ──

PROFILES: dict[str, dict[str, Any]] = {
    "default": {},
    "strict": {
        "l1_samples": 5,
        "l1_required_matches": 5,
        "score_pass_threshold": 0.70,
        "jq_pass_threshold": 0.65,
    },
    "fast": {
        "l1_samples": 2,
        "l1_required_matches": 2,
        "neuro_enabled": False,
        "hard_truth_enabled": False,
    },
    "ci": {
        "l1_samples": 3,
        "l1_required_matches": 3,
        "verbose": False,
        "output_format": "json",
        "golden_tolerance": 0.03,
    },
}


def load_config(profile: str = "default", overrides: Optional[dict] = None) -> HarnessConfig:
    """Load a named profile with optional overrides and env-var injection."""
    base = PROFILES.get(profile, PROFILES["default"]).copy()
    if overrides:
        base.update(overrides)

    # Environment variable overrides (AI_JUDGE_*)
    env_map = {
        "AI_JUDGE_L1_SAMPLES": ("l1_samples", int),
        "AI_JUDGE_SCORE_THRESHOLD": ("score_pass_threshold", float),
        "AI_JUDGE_JQ_THRESHOLD": ("jq_pass_threshold", float),
        "AI_JUDGE_SS_JQ_GAP": ("ss_jq_gap_critical", float),
        "AI_JUDGE_NEURO_ENABLED": ("neuro_enabled", lambda x: x.lower() == "true"),
        "AI_JUDGE_HARD_TRUTH": ("hard_truth_enabled", lambda x: x.lower() == "true"),
    }
    for env_var, (field, cast) in env_map.items():
        val = os.environ.get(env_var)
        if val is not None:
            base[field] = cast(val)

    return HarnessConfig(profile=profile, **base)
