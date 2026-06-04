# AI Judge P8 Stop-Line Rules

## Prohibited Actions
- Do NOT modify dashboard.js without re-running regression_harness.py
- Do NOT change BUILD_ID without refreshing the baseline
- Do NOT delete files from runs/ or vault/ directories
- Do NOT mark unknown drift as intentional without drift triage
- Do NOT perform UI acceptance without trace capture
- Do NOT modify core API routes without re-running release_readiness.py

## Stop-Line Conditions
The following conditions trigger a STOP:
- **readiness fail**: overall_status != pass
- **blockers present**: blockers list non-empty
- **strict_code_changes**: non-empty and undocumented
- **unexpected drift**: unexpected list non-empty
- **core API failure**: 500 or 404 on /api/release/* endpoints
- **trace smoke fail**: missing or empty trace after run
- **missing artifacts**: sample run missing verdict.json or trace

## Stop-Line Protocol
1. Halt all development
2. Run full regression + readiness + drift checks
3. Document findings in a new drift triage report
4. Do not proceed until all stop-line conditions are cleared
5. Any bypass requires explicit authorization and documentation
