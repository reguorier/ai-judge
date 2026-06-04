# Artifacts

This directory stores Codex/agent work evidence for AI Judge. It does not replace `reports/`, which stores product-generated AI Judge audit reports.

## What Belongs Here

- Agent audit reports.
- Acceptance reports.
- Smoke or harness output summaries.
- Before/after notes.
- UI screenshots and screenshot notes.
- Design specs.
- Decision records.
- Verification logs.

## Naming

Use:

- `artifacts/YYYYMMDD-task-name/`

Recommended files:

- `report.md`: human-readable summary, scope, decisions, and conclusions.
- `evidence.md`: source observations, commands, file references, screenshots, and raw facts.
- `verification.log`: command outputs and exit codes.
- `screenshots/`: UI/page evidence when applicable.

## Rules

- Do not fabricate tests, screenshots, report files, deployments, or business outcomes.
- Distinguish fact, inference, and recommendation for important conclusions.
- Mark uncertain information as `unknown`.
- Keep generated AI Judge product audit outputs in `reports/`.
