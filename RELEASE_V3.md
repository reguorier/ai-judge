# AI Judge v3.1.0 — Release Notes

![AI Judge v3.1 cognitive map](assets/ai-judge-v3-cognitive-map.svg)

## Overview

v3.1.0 adds the **Neuro-Cognitive Signal Layer** — a suite of 4 textual proxy signals that distinguish "sounds smart" from "is smart." This is built on top of v3.0.0's V2 upgrades (determinism engine, goal anchoring, thinking fingerprint, 6-role parliament).

## New in v3.1.0

### 2 New Core Modules

- **`core/neuro_profiler.py`** — 4 signal extractors:
  - `detect_self_closure()` — Self-reference closure ("自我视角闭环")
  - `detect_ambiguity_flexibility()` — Ambiguity handling ("模糊性处理能力")
  - `detect_recovery_after_negative()` — Recovery pattern ("反馈恢复模式")
  - `detect_experience_grounding()` — Experience anchoring ("经验锚定度")
  - `compute_neuro_profile()` — Full profile + dual scores

- **`core/hard_truth.py`** — Judgment-first feedback:
  - `determine_mode()` — L0-L4 escalation logic
  - `generate_hard_truth_output()` — Structured blind spot exposure
  - `check_heterogeneity_exemption()` — Neurodiversity protection
  - `detect_performative_acceptance()` — Anti-performative response detection

### Updated Modules

- **`core/scoring_v2.py`** — Added `compute_v3_dual_scores()` bridging V2 scoring with V3 profiling
- **`core/determinism.py`** — Added `run_full_v3_pipeline()` integrating neuro profile + hard truth
- **`core/__init__.py`** — Bumped to 3.1.0, documented all V3 modules
- **`cli/main.py`** — 3 new commands: `neuro-profile`, `hard-truth`, `v3-pipeline`

### New Test

- **`tests/smoke_test_v3.py`** — 6-test suite covering all V3 signals, modes, and pipeline

## Design Principles

1. **No brain-region names in user output.** Signal names use plain language (e.g., "模糊性处理能力" not "ACC灵活性").
2. **Signals are proxies, not diagnoses.** All output states "based on text patterns" not "your brain is X."
3. **User sovereignty.** Deep profiling can be disabled. Data is local-first.
4. **Heterogeneity exemption.** Extremely deviant but novel outputs are protected from standard penalties.

## Technical Notes

- All signal functions are dependency-free (no external ML libraries required)
- Dual scores (`smart_sounding_score`, `judgment_quality_score`) are computed from the 4 proxy signals
- Hard truth mode triggers automatically when gap > 0.30 between scores
- Performative acceptance detection compares stated acknowledgment vs actual quality improvement
- Backward compatible with all v2.x and v3.0.x code

## Migration

No breaking changes. All v2 and v3.0 commands continue to work. The V3 pipeline is additive — add `neuro_profile=` parameter to `run_full_v3_pipeline()` to enable.

## Verification

```bash
python3 cli/main.py neuro-profile --demo
python3 cli/main.py hard-truth --demo
python3 cli/main.py v3-pipeline --demo
PYTHONPATH=. python3 tests/smoke_test_v3.py
```

Expected: 6/6 tests pass, shallow text triggers L2 hard truth, deep text stays L0.

## Release Package

- Repository target: `https://github.com/reguorider-gif/ai-judge`
- Archive asset: `ai-judge-v3.1.0-release.tar.gz`
- Double-click helper: `Publish-AI-Judge-V3.command`
