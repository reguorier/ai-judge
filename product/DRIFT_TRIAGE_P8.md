# AI Judge P8 Drift Triage Report

## Identity
- **Old Build**: `p8.2-release-shortcut-e2e-v1`
- **New Build**: `p8.7-drift-sentinel-e2e-v1`

## Decision: REFRESH

## Summary
| Category | Count |
|---|---|
| Intentional | 24 |
| Generated | 16 |
| Unexpected | 0 |

## Intentional Changes
- api_server.py (product): P8.7 intentional change
- dashboard.js (product): P8.7 intentional change
- dashboard.html (product): P8.7 intentional change
- api_server.py (src): P8.7 intentional change (SRC sync)
- dashboard.js (src): P8.7 intentional change (SRC sync)
- dashboard.html (src): P8.7 intentional change (SRC sync)
- MANUAL_DRIFT_REVIEW_P8.md (product): P8.7 new file
- drift_quarantine.py (product): P8.7 new file
- DRIFT_QUARANTINE_P8.md (product): P8.7 new file
- drift_triage.py (product): P8.7 new file
- __init__.py (product): P8.7 new file
- freeze_drift_sentinel.py (product): P8.7 new file
- DRIFT_TRIAGE_P8.md (product): P8.7 new file
- ai-judge-icon.png (product): P8.7 new file
- FREEZE_DRIFT_SENTINEL_P8.md (product): P8.7 new file
- drift_quarantine.py (src): P8.7 new file (SRC sync)
- DRIFT_QUARANTINE_P8.md (src): P8.7 new file (SRC sync)
- drift_triage.py (src): P8.7 new file (SRC sync)
- __init__.py (src): P8.7 new file (SRC sync)
- freeze_drift_sentinel.py (src): P8.7 new file (SRC sync)
- DRIFT_TRIAGE_P8.md (src): P8.7 new file (SRC sync)
- ai-judge-icon.png (src): P8.7 new file (SRC sync)
- FREEZE_DRIFT_SENTINEL_P8.md (src): P8.7 new file (SRC sync)
- BUILD_ID (meta): P8.7 intentional: p8.2-release-shortcut-e2e-v1 → p8.7-drift-sentinel-e2e-v1

## Generated Artifacts
- release-readiness.json (runs): runtime generated artifact
- hermes-index.json (runs): runtime generated artifact
- run-universe.json (runs): runtime generated artifact
- trust-calibration.json (runs): runtime generated artifact
- claim-calibration-index.json (runs): runtime generated artifact
- Indexes/release-readiness.md (vault): runtime generated artifact
- Indexes/claim-calibration.md (vault): runtime generated artifact
- Indexes/gavel-review-digest.md (vault): runtime generated artifact
- RESTORE_DRILL_P8.md (product): runtime generated artifact
- restore_drill.py (product): runtime generated artifact
- freeze_manifest.py (product): runtime generated artifact
- FREEZE_MANIFEST_P8.md (product): runtime generated artifact
- RESTORE_DRILL_P8.md (src): runtime generated artifact
- restore_drill.py (src): runtime generated artifact
- freeze_manifest.py (src): runtime generated artifact
- FREEZE_MANIFEST_P8.md (src): runtime generated artifact

## Action
Baseline refresh performed: freeze manifest regenerated, regression harness BUILD_ID updated, readiness re-run.
