# AI Judge P8 Freeze Drift Report

## Identity
- **Generated**: 2026-06-03T14:13:07.028578+00:00
- **Build ID (expected)**: `p8.7-drift-sentinel-e2e-v1`
- **Build ID (actual)**: `p8.7-drift-sentinel-e2e-v1`

## Status: ⚠️ DRIFT_DETECTED

## Summary
| Metric | Count |
|---|---|
| Files checked | 47 |
| Missing | 0 |
| Strict code changed | 5 |
| Generated changed | 8 |
| New untracked | 27 |
| New generated | 8 |

## Policy
- **Volatile artifacts**: enabled
- **Strict code hash**: required

## Readiness
- **Overall**: PASS
- **Blockers**: 0

## Strict Code Changes (DRIFT)
- dashboard.js (product)
  - Manifest: `dc5d43468179f42e...`
  - Current:  `d726aeb4acc4ed12...`
- api_server.py (src)
  - Manifest: `1b557b8adcbf6484...`
  - Current:  `ce7a678da295b460...`
- dashboard.js (src)
  - Manifest: `dc5d43468179f42e...`
  - Current:  `d726aeb4acc4ed12...`
- regression_harness.py (src)
  - Manifest: `971c637de25e2339...`
  - Current:  `d507ee3b1ea04acd...`
- RELEASE_FREEZE_P8.md (src)
  - Manifest: `e7e4d4ca3105d3b2...`
  - Current:  `5ad2e957cfa0fdfe...`

## Generated Changes (Expected)
- release-readiness.json (runs)
  - Manifest: `9c2591c46e77e9c4...`
  - Current:  `be54a1988fb8431c...`
- hermes-index.json (runs)
  - Manifest: `2a2c2fcc4bd9d604...`
  - Current:  `feaf471dfb84276c...`
- run-universe.json (runs)
  - Manifest: `1ce6b888777ddf8a...`
  - Current:  `e9341acd3bd567bd...`
- trust-calibration.json (runs)
  - Manifest: `04d96c257f89fb29...`
  - Current:  `803a3587102eb9aa...`
- claim-calibration-index.json (runs)
  - Manifest: `e23a6b7becf965cb...`
  - Current:  `b35be6b8c42f30c0...`
- Indexes/release-readiness.md (vault)
  - Manifest: `acb24bc920fddca1...`
  - Current:  `b50953b7ecaffb8d...`
- Indexes/claim-calibration.md (vault)
  - Manifest: `09bb1a90cf45d9f3...`
  - Current:  `dce8f43841cc8f32...`
- Indexes/gavel-review-digest.md (vault)
  - Manifest: `671db625c4045fd8...`
  - Current:  `6987e94aba148fcd...`

## New Untracked Files
- MANUAL_DRIFT_REVIEW_P8.md (product)
- VOLATILE_ARTIFACT_POLICY_P8.md (product)
- drift_quarantine.py (product)
- RESTORE_DRILL_P8.md (product)
- DRIFT_QUARANTINE_P8.md (product)
- drift_triage.py (product)
- __init__.py (product)
- freeze_drift_sentinel.py (product)
- restore_drill.py (product)
- freeze_manifest.py (product)
- DRIFT_TRIAGE_P8.md (product)
- FREEZE_MANIFEST_P8.md (product)
- ai-judge-icon.png (product)
- FREEZE_DRIFT_SENTINEL_P8.md (product)
- MANUAL_DRIFT_REVIEW_P8.md (src)
- drift_quarantine.py (src)
- RESTORE_DRILL_P8.md (src)
- DRIFT_QUARANTINE_P8.md (src)
- drift_triage.py (src)
- __init__.py (src)
- freeze_drift_sentinel.py (src)
- restore_drill.py (src)
- freeze_manifest.py (src)
- DRIFT_TRIAGE_P8.md (src)
- FREEZE_MANIFEST_P8.md (src)
- ai-judge-icon.png (src)
- FREEZE_DRIFT_SENTINEL_P8.md (src)

## New Generated Files
- manual-drift-review-p8.json (runs)
- trust-calibration.md (runs)
- freeze-drift-report.json (runs)
- FREEZE_MANIFEST_P8.json (runs)
- drift-triage-p8.json (runs)
- run-universe.md (runs)
- drift-quarantine-p8.json (runs)
- restore-drill-p8.json (runs)

## Recommendation
DRIFT: 5 strict code hash changes; 27 new untracked files. Review changes and consider re-freezing if intentional.
