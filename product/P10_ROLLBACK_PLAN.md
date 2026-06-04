# P10 Rollback Plan

**Generated**: 2026-06-04T05:03:22Z
**Build ID**: p8.7-drift-sentinel-e2e-v1

## Rollback Scope

Only revert files modified in P10.2:

- dashboard.js — revert P10.2 UI modifications
- dashboard.html — revert P10.2 HTML modifications
- api_server.py — revert any thin doc-reading wrappers added in P10.2

## Exclusions (Do NOT Rollback)

- P0-P9 data artifacts (runs/, vault/)
- P0-P9 operator documentation
- P10.0/P10.1 planning documents

## Rollback Procedure

1. Restore dashboard.js and dashboard.html from pre-P10.2 backup
2. Remove any thin API wrappers from api_server.py
3. Run: release_readiness, freeze_drift_sentinel, regression
4. Verify all 8 maintenance actions still work
5. Confirm drift returns to generated_only

## Safety

- No P0-P9 data products are affected
- No runs/vault deletions during rollback
