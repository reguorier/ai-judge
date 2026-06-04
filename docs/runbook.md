# Agent Runbook

This runbook defines AI Judge work modes for Codex and other agents: `quick`, `deep`, and `verify`.

## Mode Selection

- Use `quick` for narrow docs/config/script changes with low product risk.
- Use `deep` for citation logic, bridge behavior, dashboard flows, data contracts, automation, deployment, release gates, or cross-module changes.
- Use `verify` when the task is to prove a claim, inspect drift, or re-check readiness without adding features.

If unsure, choose the more conservative mode and mark unknowns.

## quick

Steps:

1. Read `AGENTS.md`, `docs/agent_memory.md`, this runbook, and files directly related to the task.
2. Inspect `git status --short` before editing.
3. Make the smallest reversible patch.
4. Run `python3 scripts/agent_check.py`.
5. Run one focused command tied to the touched area:
   - Docs-only: `python3 scripts/agent_check.py` plus link/path checks.
   - Citation audit: targeted pytest or `PYTHONPATH=. python cli/main.py audit ...`.
   - Product dashboard: focused `pytest tests/test_product_state.py -q` or relevant endpoint/browser check.
   - Frontend: `npm run lint` or `npm run typecheck` from `frontend/`.
6. Report changed files, reason, command output, and remaining risk.

## deep

Use for architecture, data, automation, deployment, core scoring, web-seat collection, product dashboard, and publish gates.

Steps:

1. Audit first. Separate fact, inference, and unknown.
2. Provide option A/B with risk and rollback notes.
3. Select one minimal implementation path.
4. Preserve evidence in `artifacts/YYYYMMDD-task-name/evidence.md`.
5. Preserve verification output in `artifacts/YYYYMMDD-task-name/verification.log`.
6. Run the strongest relevant acceptance set:
   - Python behavior: focused `pytest`, then broader `pytest` or `PYTHONPATH=. python3 tests/run_harness.py` when risk warrants.
   - Citation benchmark: `PYTHONPATH=. python3 tools/run_citation_bench.py --fail-under 0.95`.
   - Smoke: `PYTHONPATH=. python3 tests/smoke_test_v3_2.py`, `PYTHONPATH=. python3 tests/smoke_test_v3.py`, or `PYTHONPATH=. python3 tests/smoke_test_council_004.py`.
   - Product dashboard/API: endpoint checks such as `/api/health`, `/api/product/capabilities`, `/api/benchmarks/summary`, plus browser/screenshot evidence for UI behavior.
   - Frontend package: `npm run lint`, `npm run typecheck`, and `npm run build` if build readiness is claimed.
   - Release/publish: do not run release, publish, signing, or Docker push commands without explicit approval.
7. Report pass/fail/unknown with evidence.

## verify

Use for important conclusion review.

Rules:

- Do not add features.
- Do not perform unrelated refactors.
- Do not treat static checks as real runtime behavior.
- Do not treat a git commit or build artifact as proof of product success.

Steps:

1. Read `AGENTS.md`, `docs/agent_memory.md`, this runbook, relevant docs, relevant code, relevant tests, and relevant artifacts.
2. Run `git status --short`.
3. Re-run `python3 scripts/agent_check.py`.
4. Re-run focused tests or smoke commands matching the claim.
5. Check drift between README/docs, CI workflows, and actual commands.
6. Output `pass`, `fail`, or `unknown`.

## Evidence Rules

- `deep` and `verify` should produce auditable summaries and evidence, not hidden chain-of-thought.
- Important tasks belong under `artifacts/YYYYMMDD-task-name/`.
- Product-generated audit outputs remain under `reports/`.
- If a command is too long-running, network-dependent, destructive, or release-like, list it and explain why it was not run.
