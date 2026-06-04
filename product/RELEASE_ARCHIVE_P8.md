# AI Judge × Hermes × Obsidian Release Archive P8

## Release Identity
- **Build ID**: p8.2-release-shortcut-e2e-v1
- **Frozen At**: 2026-06-03
- **Sample Run**: 1142374c8b6d
- **Overall Status**: pass

## Scope
| Phase | Feature | Status |
|-------|---------|--------|
| P0 | Hermes Output (JSON/MD, verdict, seats, output rendering) | Frozen |
| P1 | Hermes Index (claim search, seat listing, multi-run summary) | Frozen |
| P2 | Dashboard Hermes UI (inline rendering, expand/collapse, deep-link) | Frozen |
| P3 | Human Gavel Sync (status, history, stop/resume) | Frozen |
| P4 | Gavel Workbench (multi-run review queue, digest) | Frozen |
| P5 | Claim Calibration (per-run, per-claim, cross-run) | Frozen |
| P6 | Trust Calibration (per-seat scoring, drift detection) | Frozen |
| P7 | Decision Intelligence (needs review, NBA, seat trust drilldown) | Frozen |
| P8 | Regression Harness + Release Status Panel (shortcuts Cmd+Shift+R/M) | Frozen |

## Core API Surface
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/health | GET | Health check |
| /api/judge/<run_id>/verdict | GET | Full verdict JSON |
| /api/runs/<run_id>/index.html | GET | Hermes HTML report |
| /api/runs/<run_id>/hermes-output.json | GET | Raw Hermes output |
| /api/runs/<run_id>/summary | GET | Run summary |
| /api/runs/<run_id>/stop | POST | Stop run |
| /api/runs/<run_id>/resume | POST | Resume run |
| /api/runs/<run_id>/trace | POST | Write trace event |
| /api/runs/<run_id>/events | GET | Read trace events |
| /api/runs | GET | List runs |
| /api/runs/recent | GET | Recent runs |
| /api/runs/universe | GET | Run universe summary |
| /api/hermes/index | GET | Hermes index |
| /api/hermes/seats | GET | Hermes seats |
| /api/gavel/<run_id> | GET | Gavel status |
| /api/gavel/<run_id>/history | GET | Gavel history |
| /api/gavel/digest | GET | Gavel digest |
| /api/claims/calibration | GET | Claims calibration index |
| /api/claims/calibration/<run_id> | GET | Claims calibration for run |
| /api/trust/calibration | GET | Trust calibration |
| /api/trust/seat/<seat_name> | GET | Seat trust detail |
| /api/decision/intelligence | GET | Decision intelligence |
| /api/release/readiness | GET | Release readiness |
| /api/release/regression | POST | Run regression |
| /api/runs/release-readiness | GET | Release readiness Markdown |

## Core Files

### Run Artifacts (per run, e.g. 1142374c8b6d)
- hermes-output.json
- hermes-output.md
- hermes-index.json
- verdict.json
- claims-calibration.json
- gavel-status.json
- gavel-history.jsonl
- trust-calibration.json
- index.html

### Global Files
- runs-index.json
- hermes-global-index.json
- gavel-digest.json
- trust-global-calibration.json
- release-readiness.json

### Vault Indexes
- Indexes/hermes-index.md
- Indexes/claim-calibration.md
- Indexes/run-universe.md
- Indexes/trust-calibration.md
- Indexes/gavel-review-digest.md
- Indexes/release-readiness.md
- Indexes/release-archive-p8.md

## Regression Result
- **Overall**: pass
- **Pass/Fail**: 5/0
- **Blockers**: 0

## Known Limits
- Electron WebView 对 macOS AX API 不可见，UI 按钮点击需人工验收
- Cmd+Shift+R/M 快捷键覆盖 Release Regression/Markdown，需确保 Electron 窗口前台
- unmatched claims 是数据固有状态，非 bug

## Freeze Decision
P8 基线已冻结。所有 P0–P8.3 检查通过，blockers=0，overall_status=pass。可交接运维。
