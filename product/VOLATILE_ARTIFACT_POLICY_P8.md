# AI Judge P8 Volatile Artifact Policy

## Policy
- **strict_code** (product/src .py/.js/.html): SHA256 exact match required
- **generated** (runs/vault reports, indexes, traces): existence + schema check only, no hash stability required

## Generated Artifact Allowlist
- release-readiness.json/md
- release-archive-p8.json/md
- restore-drill-p8.json/md
- FREEZE_MANIFEST_P8.json/md
- freeze-drift-report.json/md
- drift-triage-p8.json/md
- drift-quarantine-p8.json/md
- manual-drift-review-p8.json/md
- debug-ui-io-trace.jsonl
- hermes-index.json
- run-universe.json
- trust-calibration.json
- claim-calibration-index.json
- gavel-review-digest.md
- regression results

## Status Rules
| strict_code_changes | generated_changes | status |
|---|---|---|
| empty | empty | clean |
| empty | non-empty | generated_only |
| non-empty | any | drift_detected |
| N/A + readiness fail | N/A | blocked |
