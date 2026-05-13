"""AI Judge Harness v1.0 — Systematic evaluation, benchmarking, and CI integration.

The harness layer wraps AI Judge's core modules into reproducible pipelines:
  - runner:      Programmatic pipeline execution (scoring, neuro, hard-truth, full V3)
  - benchmark:   Golden-dataset testing with pass/fail thresholds
  - regression:  Cross-version consistency checking
  - config:      YAML-based configuration profiles
  - reporter:    Standardized output (JSON, Markdown, HTML summary)

Usage:
    from harness import AIJudgeHarness
    h = AIJudgeHarness(config="default")
    result = h.run_v3_pipeline(text="...")
    h.report(result, format="markdown")
"""

__version__ = "1.0.0"
