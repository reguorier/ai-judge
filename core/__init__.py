"""AI Judge Core — Multi-model AI jury package v3.2.0 (Tianfu Agent Migration).

Public modules (this repository):
  - license_validator: Community license shim
  - hermes_output: Hermes-compatible verdict envelope
  - formula_engine: Phase 1 scoring functions (log_score, allocation_score, etc.)
  - scoring_v2: v2.0 claim and jury scoring pipeline + V3 dual scores + V3.2 evidence integration
  - peach_projection: Two Peaches scarcity-based weight allocation

V2 Modules:
  - determinism: L1/L2 consistency engine, confidence lights, human tax, V3 hard_truth trigger
  - anchor_engine: Goal anchoring, taste cards, drift detection
  - cold_start: Progressive scaffolding for new users
  - performance_detect: Process-friction-based performance detection
  - mirror: Thinking fingerprint, growth narrative, dual-channel feedback
  - thinking_log: Fragment collection, question distillation, 6-role parliament
  - achievement: Metrics computation, breakthrough detection, visualization data

V3 Modules:
  - neuro_profiler: 4 neural-cognitive proxy signals (self_closure, ambiguity_flexibility,
    recovery_after_negative, experience_grounding) + smart_sounding/judgment_quality dual scores
  - hard_truth: L0-L4 judgment-first feedback mode, heterogeneity exemption, performative acceptance detection

V3.2 NEW Modules (Tianfu Agent Migration):
  - evidence: Structured evidence objects with source tracing (Tianfu: knowledge-tracing)
  - dissent: Devil's Advocate counterargument generation (Tianfu: Verify phase + Gemini anti-collusion)
  - reasoning_trace: Tree-structured judgment reasoning chain (Tianfu: visualized reasoning)
  - risk_router: Task risk classification and review depth routing (Tianfu: tiered scheduling)

Harness Layer (tests/harness/):
  - harness/runner: Programmatic pipeline execution API
  - harness/benchmark: Golden-dataset testing with pass/fail thresholds
  - harness/regression: Cross-version consistency checking
  - harness/config: YAML-based configuration profiles (default, strict, fast, ci)
  - harness/reporter: Standardized output (JSON, Markdown, HTML)

Production modules (paid core, not in this repository):
  - jury: Session creation and packet generation
  - collect: Browser/CDP answer collection
  - verdict: Claim scoring and consensus detection
  - reflect: Performance trend analysis
"""

__version__ = "3.2.0"
__author__ = "AI Judge Contributors"
__license__ = "BSL-1.1"
