# AI Judge P8 Freeze Manifest

## Identity
- **Schema**: ai-judge-freeze-manifest-p8-v1
- **Build ID**: `p8.7-drift-sentinel-e2e-v1`
- **Freeze Label**: p8-freeze
- **Generated**: 2026-06-04T12:44:23.628329+00:00

## Verification: ✅ PASS
- **Files**: 47/47 present, 0 missing
- **Algorithm**: sha256
- **Backup**: /Users/audimacmini/Documents/AI-Judge-Freezes/p8-freeze-20260604_124423

## Readiness
- **Overall Status**: PASS
- **Blockers**: 0

## File Inventory

| Relative Path | Role | Size | SHA256 |
|---|---|---|---|
| api_server.py | product | 276364 | 23ab30d1fe17c301... |
| dashboard.js | product | 728604 | fdf07dfc9956063b... |
| dashboard.html | product | 482297 | 362b2a0fc3083a63... |
| hermes_output_layer.py | product | 15888 | 0474f96ccc2b99e3... |
| hermes_index_layer.py | product | 17658 | d8f1df78a4e6efe1... |
| human_gavel_layer.py | product | 34803 | c91ad4b3fc21cf35... |
| claim_calibration_layer.py | product | 19322 | 909b0e41360a701d... |
| run_universe_layer.py | product | 7611 | b8115a8492d43c3b... |
| trust_calibration_layer.py | product | 12310 | 726ef9f0224e1108... |
| regression_harness.py | product | 12706 | d507ee3b1ea04acd... |
| release_readiness.py | product | 7170 | a439d1cf76d4cf93... |
| release_archive.py | product | 5350 | 300332bcc5855a67... |
| RELEASE_ARCHIVE_P8.md | product | 3413 | 0791822c8a92a8dc... |
| OPERATOR_GUIDE.md | product | 6326 | a969ab8402b03dbc... |
| ROLLBACK_GUIDE.md | product | 1905 | ec64e4103738c9f6... |
| REGRESSION_CHECKLIST.md | product | 3593 | af325b4a23d160c8... |
| RELEASE_FREEZE_P8.md | product | 3984 | 5ad2e957cfa0fdfe... |
| api_server.py | src | 276364 | 23ab30d1fe17c301... |
| dashboard.js | src | 728604 | fdf07dfc9956063b... |
| dashboard.html | src | 482297 | 362b2a0fc3083a63... |
| hermes_output_layer.py | src | 15888 | 0474f96ccc2b99e3... |
| hermes_index_layer.py | src | 17658 | d8f1df78a4e6efe1... |
| human_gavel_layer.py | src | 34803 | c91ad4b3fc21cf35... |
| claim_calibration_layer.py | src | 19322 | 909b0e41360a701d... |
| run_universe_layer.py | src | 7611 | b8115a8492d43c3b... |
| trust_calibration_layer.py | src | 12310 | 726ef9f0224e1108... |
| regression_harness.py | src | 12706 | d507ee3b1ea04acd... |
| release_readiness.py | src | 7170 | a439d1cf76d4cf93... |
| release_archive.py | src | 5350 | 300332bcc5855a67... |
| RELEASE_ARCHIVE_P8.md | src | 3413 | 0791822c8a92a8dc... |
| OPERATOR_GUIDE.md | src | 6326 | a969ab8402b03dbc... |
| ROLLBACK_GUIDE.md | src | 1905 | ec64e4103738c9f6... |
| REGRESSION_CHECKLIST.md | src | 3593 | af325b4a23d160c8... |
| RELEASE_FREEZE_P8.md | src | 3984 | 5ad2e957cfa0fdfe... |
| release-readiness.json | runs | 3327 | 0267cd8583549260... |
| release-archive-p8.json | runs | 1711 | b3546b5edc4119c6... |
| hermes-index.json | runs | 112282 | 090ac1047b24ab98... |
| run-universe.json | runs | 53240 | d13428b2a80d8698... |
| trust-calibration.json | runs | 5752 | f6fd6bd67f118248... |
| claim-calibration-index.json | runs | 29577 | 6e0941e2e19f1662... |
| Indexes/release-readiness.md | vault | 2305 | adcddd07b621bdca... |
| Indexes/release-archive-p8.md | vault | 1414 | 25c86644c0151be5... |
| Indexes/run-universe.md | vault | 12078 | ce316385837d8b35... |
| Indexes/trust-calibration.md | vault | 887 | b0234e8928bb28f0... |
| Indexes/claim-calibration.md | vault | 6548 | ea74084547e83814... |
| Indexes/hermes-index.md | vault | 4559 | 048a596e8233d2e4... |
| Indexes/gavel-review-digest.md | vault | 1452 | 8ca4b7beadac2630... |

## Recovery Note
Backup snapshot at `{manifest['backup_dir']}` contains code + release docs. Runs and Vault data directories are NOT included — those must be preserved separately.
