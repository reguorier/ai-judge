# P9 Operator Seal

## Current Baseline
- Build ID: p8.7-drift-sentinel-e2e-v1
- Product Version: 3.8.0-p8.7-drift-sentinel-e2e-v1
- Readiness: PASS
- Drift: generated_only
- Strict Code: 0
- Unexpected: 0

## P9 Scope Completed
- P9.0 Unfreeze Gate
- P9.1 Scope Definition
- P9.2 Maintenance Control Center
- P9.3 Post-Implementation Triage
- P9.4 Baseline Refresh

## Maintenance Control Center
- release_readiness
- regression
- drift_check
- restore_drill
- gavel_sync_all
- claim_calibration_rebuild_all
- trust_calibration_refresh
- decision_intelligence_refresh

## Operator Boundary

### Allowed Actions
- Run Maintenance Control Center (all 8 actions)
- Re-run readiness/regression/drift via scripts or API
- Sync gavel via /api/gavel/sync-all
- Rebuild claim calibration via /api/claims/calibration/rebuild-all
- Restore dry-run via /api/release/restore-drill
- Inspect generated-only drift
- Read release-readiness / freeze-drift-report
- Restart API server if needed

### Forbidden Actions
- Modify core code without unfreeze protocol (must start at P10)
- Change BUILD_ID without refreshing baseline
- Delete files from runs/ or vault/
- Bypass trace capture on acceptance
- Forge clean/pass status in reports
- Mark unexpected drift as intentional without full triage
- Modify P0-P9 schema
- Skip entry gate for next unfreeze

## Final Decision
**GO** — P9 baseline is ready for operator handoff.
