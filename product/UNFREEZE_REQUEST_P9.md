# P9 Unfreeze Request

## Reason for Unfreeze
No concrete feature request yet. This P9.0 only opens the governance gate and does not authorize coding. The unfreeze is requested to establish the P9 governance framework so that future operational intelligence, maintenance UX, or controlled extensions can be scoped under formal review before any code change occurs.

## Proposed P9 Theme
Operational Intelligence / Maintenance UX / Controlled Extensions

## Frozen Baseline
- **Build ID**: p8.7-drift-sentinel-e2e-v1
- **Product Version**: 3.8.0-p8.7-drift-sentinel-e2e-v1
- **Manifest**: FREEZE_MANIFEST_P8.json (47 files)
- **Readiness**: PASS (5/5, 0 blockers)
- **Drift**: generated_only (strict_code_changes=0, unexpected=0)
- **Operator Seal**: FINAL_OPERATOR_SEAL_P8.md (Go/No-Go: GO)

## Allowed Change Boundary
- Add new P9 documentation (md, json, py scripts)
- Add new P9 feature modules that do not modify P0-P8 core
- Extend dashboard with P9-only UI components (no existing component modification)
- Add new API routes under a `/p9/` prefix (no existing route modification)
- Extend RUNS data with new P9 subdirectories

## Forbidden Without New Approval
- Modify P0-P8 core modules (api_server.py, dashboard.js, freeze_drift_sentinel.py, etc.)
- Change BUILD_ID or refresh freeze manifest
- Delete or alter runs/ or vault/ data
- Modify existing API schema or routes
- Bypass trace-based UI acceptance
- Mark unknown drift as intentional without triage

## Entry Decision
PENDING — to be determined by P9.0 entry gate evaluation.
