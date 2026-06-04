# AI Judge P8.17 Product Version Drift Decision

## Decision
**refresh_baseline** — both strict changes are intentional PRODUCT_VERSION alignment from P8.16.

## Audit

| # | Path | Role | Old Version | New Version | Reason | Decision |
|---|------|------|-------------|-------------|--------|----------|
| 1 | api_server.py | product | 3.8.0-P2.6-RC1 | 3.8.0-p8.7-drift-sentinel-e2e-v1 | P8.16 Runtime Build Alignment | intentional |
| 2 | api_server.py | src | 3.8.0-P2.6-RC1 | 3.8.0-p8.7-drift-sentinel-e2e-v1 | P8.16 SRC sync | intentional |

## Summary
- **intentional_count**: 2
- **unexpected_count**: 0
- **decision**: refresh_baseline
