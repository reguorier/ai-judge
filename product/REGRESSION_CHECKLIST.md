# Regression Checklist — AI Judge P8

## Pre-flight
- [ ] API server running on port 8501
- [ ] Dashboard accessible at http://127.0.0.1:8501
- [ ] AI Judge Desktop app open and showing Dashboard

## Build & Artifacts
- [ ] `dashboard.js` BUILD_ID matches `p8.2-release-shortcut-e2e-v1`
- [ ] Sample run (1142374c8b6d) files present in RUNS
- [ ] Vault Indexes all present (hermes, claim, trust, universe, gavel, release-readiness)

## API (15+ endpoints)
- [ ] `GET /api/health` → 200
- [ ] `GET /api/runs` → 200
- [ ] `GET /api/runs/recent` → 200
- [ ] `GET /api/runs/universe` → 200
- [ ] `GET /api/judge/1142374c8b6d/verdict` → 200
- [ ] `GET /api/runs/1142374c8b6d/index.html` → 200
- [ ] `GET /api/runs/1142374c8b6d/hermes-output.json` → 200
- [ ] `GET /api/hermes/index` → 200
- [ ] `GET /api/hermes/seats` → 200
- [ ] `GET /api/gavel/1142374c8b6d` → 200
- [ ] `GET /api/gavel/1142374c8b6d/history` → 200
- [ ] `GET /api/gavel/digest` → 200
- [ ] `GET /api/claims/calibration` → 200
- [ ] `GET /api/trust/calibration` → 200
- [ ] `GET /api/decision/intelligence` → 200

## Trace
- [ ] `POST /api/trace` → 200, smoke event written to trace file

## Release Readiness
- [ ] `GET /api/release/readiness` → `overall_status: pass`
- [ ] `POST /api/release/regression` → `ok: true`
- [ ] `blockers: []`
- [ ] `pass_count: 5`, `fail_count: 0`

## Dashboard UI
- [ ] Release Status panel visible with PASS badge
- [ ] Cmd+Shift+R triggers regression and writes trace
- [ ] Cmd+Shift+M opens Readiness Markdown and writes trace

## Operator Docs
- [ ] `RELEASE_ARCHIVE_P8.md` exists
- [ ] `OPERATOR_GUIDE.md` exists
- [ ] `ROLLBACK_GUIDE.md` exists
- [ ] `REGRESSION_CHECKLIST.md` exists (this file)
- [ ] `release-archive-p8.json` in RUNS
- [ ] `release-archive-p8.md` in Vault/Indexes

## P9 Maintenance Control Center
- [ ] Maintenance Control Center visible (wrench icon in Dashboard)
- [ ] 8 maintenance actions available (Release Readiness, Regression, Drift Check, Restore Drill, Gavel Sync All, Claim Calibration Rebuild, Trust Calibration Refresh, Decision Intelligence Refresh)
- [ ] Each action triggers maintenance_action_clicked trace event
- [ ] Each action writes maintenance_action_result trace event
- [ ] Release Readiness → overall_status: pass
- [ ] Regression → PASS, blockers: []
- [ ] Drift Check → strict_code_changes: 0, unexpected: []
- [ ] Gavel Sync All → returns errors: 0
- [ ] Claim Calibration Rebuild → returns errors: []
- [ ] All 8 actions return ok: true or documented status
- [ ] Cmd+Shift+O opens Maintenance panel

## P10 Maintenance UX + Operator Guide Addendum
- [ ] Maintenance groups visible (Release Health / Human Review / Trust & Intelligence)
- [ ] Each group toggles expand/collapse on click
- [ ] Operator Guide panel opens (Cmd+Shift+U or card entry)
- [ ] Operator Docs API: `GET /api/operator/docs` → 200 with 5 docs
- [ ] Operator Docs API: `GET /api/operator/doc/operator_guide` → 200
- [ ] Operator Docs API: `GET /api/operator/doc/regression_checklist` → 200
- [ ] Operator Docs API: `GET /api/operator/doc/stop_line` → 200
- [ ] Operator Docs API: `GET /api/operator/doc/unfreeze_protocol` → 200
- [ ] Operator Docs API: `GET /api/operator/doc/runbook` → 200
- [ ] Path traversal blocked: `GET /api/operator/doc/../secrets` → 400
- [ ] `operator_guide_opened` trace event exists
- [ ] `operator_doc_opened` trace event exists (for each doc)
- [ ] `maintenance_group_toggled` trace event exists
- [ ] Readiness = pass (5/5, 0 blockers)
- [ ] Drift = generated_only (strict=0)
