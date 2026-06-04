# Operator Guide — AI Judge P8 Release

## How to Run Regression

```bash
# Step 1: Run regression harness
python3 regression_harness.py \
  --runs-dir "$RUNS" \
  --vault-dir "$VAULT" \
  --run-id "$RUN_ID" \
  --port "$PORT" \
  --trace "$TRACE" \
  --verbose

# Step 2: Generate readiness report
python3 release_readiness.py \
  --runs-dir "$RUNS" \
  --vault-dir "$VAULT" \
  --run-id "$RUN_ID" \
  --port "$PORT" \
  --trace "$TRACE"
```

## How to Check Release Status

### Via Dashboard
Open AI Judge Desktop → Dashboard → Release Status panel.
Green PASS badge = all clear. Red FAIL badge = check blockers.

### Via API
```bash
curl -s http://127.0.0.1:8501/api/release/readiness | python3 -m json.tool
```

### Via Shortcut
In Dashboard: Cmd+Shift+R to re-run regression.

## How to Interpret Blockers

| Blocker Type | Meaning | Action |
|-------------|---------|--------|
| BUILD_ID mismatch | dashboard.js BUILD_ID ≠ baseline | Update baseline per P8.3 process |
| API 500/404 | Core endpoint broken | Check api_server.py logs, restart server |
| Missing artifact | Expected file not in RUNS or Vault | Check file generation pipeline |
| Trace smoke fail | Trace file unwritable or POST trace fails | Check disk, file permissions |
| Sample run incomplete | Run missing hermes-output.json | Re-run sample or pick new sample run |

## How to Refresh Baseline
1. Confirm current BUILD_ID in `dashboard.js`: `grep AI_JUDGE_CLIENT_BUILD dashboard.js`
2. Update `DASHBOARD_JS_BUILD_KEY` in `regression_harness.py` to match
3. Update `RELEASE_FREEZE_P8.md` with new build and P8.3 baseline section
4. Run regression: all checks must pass
5. Run release_readiness.py to regenerate reports
6. **Never bypass a failing check to force pass**

## How to Sync Gavel / Claim / Trust
- Gavel: `curl http://127.0.0.1:8501/api/gavel/<run_id>`
- Claims: `curl http://127.0.0.1:8501/api/claims/calibration`
- Trust: `curl http://127.0.0.1:8501/api/trust/calibration`

## Quick Troubleshooting

### Dashboard won't load
```bash
kill $(pgrep -f api_server.py)
cd /path/to/product && python3 api_server.py &
# In Electron: Cmd+R to refresh, Cmd+Shift+R hard refresh
```

### API server not responding
```bash
curl http://127.0.0.1:8501/api/health | python3 -m json.tool
# Expected: {"status":"ok"}
```

## P9 Maintenance Control Center

### Overview
The P9.2 Maintenance Control Center aggregates 8 operational actions into a single floating panel in the Dashboard UI. Access it via the Dashboard wrench icon or Cmd+Shift+O.

### Actions

| Action | Method | Endpoint | Purpose |
|---|---|---|---|
| Release Readiness | GET | /api/release/readiness | Full readiness check |
| Regression | POST | /api/release/regression | Smoke test harness |
| Drift Check | POST | /api/release/drift/check | Freeze drift sentinel |
| Restore Drill | POST | /api/release/restore-drill | Dry-run restore from freeze backup |
| Gavel Sync All | POST | /api/gavel/sync-all | Sync all human gavel decisions |
| Claim Calibration Rebuild | POST | /api/claims/calibration/rebuild-all | Rebuild claim calibration index |
| Trust Calibration Refresh | POST | /api/trust/calibration/refresh | Refresh trust calibration |
| Decision Intelligence Refresh | POST | /api/decision/intelligence/refresh | Refresh decision intelligence |

### How to Run via Dashboard
1. Open AI Judge Desktop
2. Navigate to Dashboard
3. Click Maintenance wrench icon or press Cmd+Shift+O
4. Click any action button to execute
5. Trace records maintenance_action_clicked and maintenance_action_result automatically

### How to Run via CLI
```bash
# Run all 8 via Python
python3 -c "
import subprocess, json
ACTIONS = [
    ('release_readiness',             'GET',  '/api/release/readiness'),
    ('regression',                    'POST', '/api/release/regression'),
    ('drift_check',                   'POST', '/api/release/drift/check'),
    ('restore_drill',                 'POST', '/api/release/restore-drill'),
    ('gavel_sync_all',                'POST', '/api/gavel/sync-all'),
    ('claim_calibration_rebuild_all', 'POST', '/api/claims/calibration/rebuild-all'),
    ('trust_calibration_refresh',     'POST', '/api/trust/calibration/refresh'),
    ('decision_intelligence_refresh', 'POST', '/api/decision/intelligence/refresh'),
]
for kind, method, url in ACTIONS:
    cmd = ['curl', '-s', 'http://127.0.0.1:8501' + url]
    if method == 'POST': cmd += ['-X', 'POST', '-H', 'Content-Type: application/json', '-d', '{}']
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f'{kind}: {\"PASS\" if r.returncode == 0 else \"FAIL\"}')
"
```

### Keyboard Shortcuts
| Shortcut | Action |
|---|---|
| Cmd+Shift+O | Open/close Maintenance panel |
| Cmd+Shift+R | Release readiness |
| Cmd+Shift+V | Gavel sync all |
| Cmd+Shift+L | Claim calibration rebuild |

### Trace Verification
```bash
grep "maintenance_action" debug-ui-io-trace.jsonl | tail -20
# Expect: 16 lines (8 clicked + 8 result) per full run
```

## P10 Maintenance UX and Embedded Operator Guide

### Maintenance Groups
Dashboard now displays three collapsible maintenance groups:
- **Release Health** (4 actions): Readiness, Regression, Drift Check, Restore Drill
- **Human Review** (2 actions): Gavel Sync All, Claim Calibration Rebuild
- **Trust & Intelligence** (2 actions): Trust Calibration, Decision Intelligence Refresh

Each group can be toggled (expand/collapse), emitting `maintenance_group_toggled` trace events.

### Operator Guide Panel (Cmd+Shift+U)
Embedded operator documentation accessible from Dashboard sidebar:
- Operator Guide
- Regression Checklist
- Stop Line Protocol
- Unfreeze Protocol
- Runbook

Opens via keyboard shortcut `Cmd+Shift+U` or Operator Guide card entry. Emits `operator_guide_opened` and `operator_doc_opened` trace events.

### Operator Docs API
- `GET /api/operator/docs` — list 5 available operator documents with metadata
- `GET /api/operator/doc/<doc_id>` — read specific operator document by ID
- Whitelist-enforced; path traversal blocked with 400

### Keyboard Shortcuts
| Shortcut | Action |
|---|---|
| Cmd+Shift+U | Open Operator Guide panel |
| Cmd+Shift+Y | Toggle a maintenance group |

### Trace Events
```bash
grep "operator_doc_opened\|operator_guide_opened\|maintenance_group_toggled" debug-ui-io-trace.jsonl | tail -20
```
