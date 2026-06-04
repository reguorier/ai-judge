# AI Judge P8 Maintenance Playbook

## Allowed Maintenance Actions

### 1. Re-run Regression Harness
```bash
python3 /Users/audimacmini/Library/Application Support/AI Judge/runtime/product/regression_harness.py
```
Pass: all 5 checks pass, total_pass=5, total_fail=0, blockers=[]

### 2. Re-run Release Readiness
```bash
python3 /Users/audimacmini/Library/Application Support/AI Judge/runtime/product/release_readiness.py \
  --runs-dir "/Users/audimacmini/Library/Application Support/AI Judge/runtime/runs" \
  --vault-dir "/Users/audimacmini/Documents/AI-Judge-Obsidian-Vault" \
  --run-id "1142374c8b6d" \
  --port "8501" \
  --trace "/Users/audimacmini/Library/Application Support/AI Judge/runtime/debug-ui-io-trace.jsonl"
```
Pass: overall_status=pass, blockers=[]

### 3. Re-run Drift Sentinel
```bash
python3 /Users/audimacmini/Library/Application Support/AI Judge/runtime/product/freeze_drift_sentinel.py \
  --manifest "/Users/audimacmini/Library/Application Support/AI Judge/runtime/runs/FREEZE_MANIFEST_P8.json" \
  --product-dir "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product" \
  --src-dir "/Users/audimacmini/Documents/ai-judge-skill/product" \
  --runs-dir "/Users/audimacmini/Library/Application Support/AI Judge/runtime/runs" \
  --vault-dir "/Users/audimacmini/Documents/AI-Judge-Obsidian-Vault" \
  --port "8501" \
  --trace "/Users/audimacmini/Library/Application Support/AI Judge/runtime/debug-ui-io-trace.jsonl" \
  --write
```
Pass: strict_code_changes=[], unexpected=[], status=clean or generated_only

### 4. Sync Human Gavel
Re-run the gavel sync script if available. Pass: gavel digest has recent entries.

### 5. Rebuild Claim Calibration
Re-run calibration logic for claims. Pass: claim-calibration-index.json updated.

### 6. Regenerate Trust Calibration
Re-run trust calibration. Pass: trust-calibration.json updated.

### 7. Regenerate Decision Intelligence
Re-run decision intelligence analysis. Pass: run-universe.json updated.

### 8. Inspect generated_only Drift
Review generated_changes list in freeze-drift-report.json. These are expected run artifacts and do not block release.

## NOT Allowed
- Modifying core API logic without unfreeze protocol
- Adding new features without P9.x phase tracking
- Bulk file operations on runs/ or vault/
- Manual editing of freeze manifest JSON
