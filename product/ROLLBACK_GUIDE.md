# Rollback Guide — AI Judge P8 Release

## When to Roll Back
- Release readiness returns `fail` with unresolved blockers
- Any core API returns 500 after a code change
- Hermes artifacts (hermes-output.json) go missing
- Dashboard fails to load (blank page or JS error)
- Trace smoke test fails (cannot write to trace file)

## What to Roll Back
- `$PRODUCT/` — runtime product files (api_server.py, dashboard.js, dashboard.html, regression_harness.py, release_readiness.py)
- `$SRC/` — source code mirror
- `DASHBOARD_JS_BUILD_KEY` in `regression_harness.py`
- `RELEASE_FREEZE_P8.md` baseline entries

## Prerequisites
- Git repo with tagged baseline: `git tag p8-freeze`
- Backup of current state before rollback

## Safe Rollback Steps

### Step 1: Backup current state
```bash
cp -r "$PRODUCT" "$PRODUCT.bak.$(date +%Y%m%d_%H%M%S)"
```

### Step 2: Restore frozen PRODUCT files
```bash
git checkout p8-freeze -- product/
cp -r product/* "$PRODUCT/"
```

### Step 3: Restore SRC mirror
```bash
git checkout p8-freeze -- ai-judge-skill/product/
cp -r ai-judge-skill/product/* "$SRC/"
```

### Step 4: Restart API server
```bash
kill $(pgrep -f api_server.py)
sleep 2
cd "$PRODUCT" && python3 api_server.py &
```

### Step 5: Verify
```bash
python3 "$PRODUCT/regression_harness.py" \
  --runs-dir "$RUNS" \
  --vault-dir "$VAULT" \
  --run-id "$RUN_ID" \
  --port "$PORT" \
  --trace "$TRACE" \
  --verbose
```

## Post-Rollback Verification Checklist
- [ ] `OVERALL: PASS`
- [ ] `blockers: 0`
- [ ] `curl http://127.0.0.1:8501/api/health` → 200
- [ ] `curl http://127.0.0.1:8501/api/release/readiness` → pass
- [ ] Dashboard loads and shows Release Status PASS

## Important: Never Delete User Data
- **Do NOT** delete `$RUNS/` directory contents
- **Do NOT** delete `$VAULT/` directory contents
- **Do NOT** delete `debug-ui-io-trace.jsonl`
- Rollback only touches PRODUCT and SRC code files
