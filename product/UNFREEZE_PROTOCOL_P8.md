# AI Judge P8 Unfreeze Protocol

## When to Use
Any new development after P8 freeze baseline (p8.7-drift-sentinel-e2e-v1) MUST follow this protocol.

## Protocol Steps
1. **Record reason**: Document why unfreeze is needed (e.g., "P9.1: add seat score visualization")
2. **Backup manifest**: Copy current FREEZE_MANIFEST_P8.json to a new version
3. **Create phase**: Assign new phase number (e.g., P9.1) and document expected changes
4. **Record expected files**: List all files you plan to modify before making changes
5. **Make changes**: Implement the new feature or fix
6. **Regression test**: Run regression_harness.py — all checks must pass
7. **Readiness check**: Run release_readiness.py — overall_status must be pass
8. **Drift triage**: If strict_code_changes non-empty, run drift triage to classify as intentional/unexpected
9. **Approval gate**: If all intentional, proceed; if unexpected, fix before continuing
10. **Refresh baseline**: Run freeze_manifest.py to regenerate manifest with new hashes
11. **Archive**: Add new release archive entry documenting the change
12. **Update docs**: Update RELEASE_FREEZE_P8.md with new phase description

## Checklist Template
```
Phase: P9.x
Reason: [description]
Expected changes:
  - [file1]
  - [file2]
Regression: PASS/FAIL
Readiness: PASS/FAIL
Strict code changes: [count, all intentional? Y/N]
New baseline: [yes/no]
Archive entry: [yes/no]
Docs updated: [yes/no]
```

## Safety Rules
- Never skip regression before refreshing baseline
- Never mark unexplained drift as intentional
- Never delete the old manifest before new one is verified
- Always keep backups in /Users/audimacmini/Documents/AI-Judge-Freezes/
