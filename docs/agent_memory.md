# Agent Memory

This file records project-specific long-term context for AI Judge. Do not store private personal information here. Each memory includes a source: `repo`, `user_instruction`, `inferred`, or `unknown`.

## Long-Term User Preferences

- Avoid generic praise and completion-only responses. Source: user_instruction
- Always report changed files, change reasons, verification commands, verification results, and remaining risk. Source: user_instruction
- Mark uncertain information as `unknown`; do not invent facts. Source: user_instruction
- Separate important conclusions into fact, inference, and recommendation. Source: user_instruction
- For high-risk changes, give a plan before editing. Source: user_instruction
- Do not overwrite existing repository files mechanically when migrating agent rules. Source: user_instruction
- User explicitly wants AI Judge functionality narrowed: no dashboard-first development, no endless UI expansion, and only basic functional surfaces. Core value must be expressed in auditable report output. Source: user_instruction
- User clarified the final product vision: AI Judge should have operation controls and user-visible progress, but must not pile up interface surfaces; perceived value lands in the final report. Source: user_instruction

## Project Long-Term Goals

- AI Judge is a local-first source-isolated claim-support gate for AI-generated answers. Source: repo
- AI Judge is report-first, not dashboard-first; the value is in claim-level evidence, dissent, traceability, source/citation audit, claim-support/overclaim detection, and the human-final gate. Source: user_instruction
- The current v3.8.0 wedge is citation audit: prove whether isolated evidence supports the exact generated claim span before publication. Source: repo
- The product should expose the evidence, weak spots, dissent, traceability, and next falsifiable action so a human can make the final decision. Source: repo
- The repository supports Python CLI/core, product dashboard/API, web-seat bridges, Tauri/React UI references, GitHub Actions, Docker packaging, and HTML/JSON/Markdown reports. Source: repo

## Current Stage Decisions

- `AGENTS.md` is the primary Codex/agent entrypoint. Source: user_instruction
- Codex must read `docs/agent_memory.md` and `docs/runbook.md` before work. Source: user_instruction
- `reports/` remains the AI Judge product report output directory. Source: repo
- `artifacts/` is for agent work evidence, acceptance reports, screenshots, and decision records. Source: user_instruction
- Agent infrastructure self-check is `python3 scripts/agent_check.py`. Source: repo
- Dashboard/workbench surfaces are optional internal/operator aids only; do not expand them unless they directly support report generation, verification, or operator safety. Source: user_instruction
- A future client-first direction may provide a minimal local client for input, mode selection, run control, final report viewing, follow-up, export, and archive; do not implement it without an explicit scoped task and verification plan. Source: user_instruction
- GitHub Actions publish workflow gates Docker publishing behind harness, v3.2 smoke, and citation-bench checks. Source: repo

## Historical Pitfalls

- A cited source can exist and still fail to support the exact generated claim. Source: repo
- Model-mentioned sources are candidate sources, not proof; source isolation matters. Source: repo
- Web-seat runs must not silently degrade into local synthetic answers when calibration, login, quota, or DOM readiness fails. Source: repo
- The repository currently has many pre-existing uncommitted changes; do not revert or normalize unrelated dirty files. Source: repo
- Dashboard/workbench and bridge work is easy to overreach; keep the report pipeline primary and preserve publish gates, recovery traces, and human-final decision points. Source: inferred

## Disabled Approaches

- Do not implement a Chrome plugin unless the repository has an explicit scoped plan for it. Source: user_instruction
- Do not connect to external Claude services as a shortcut. Source: user_instruction
- Do not run publish/release/Docker push/signing/paid automation/outreach commands without explicit approval. Source: repo
- Do not claim PDF/DOCX support unless parser warnings, anchors, and manifest policy behavior are covered by tests. Source: repo
- Do not add billing infrastructure until demand criteria in docs justify it. Source: repo

## Common Acceptance Standards

- Agent governance: `python3 scripts/agent_check.py`. Source: repo
- Smoke checks: `PYTHONPATH=. python3 tests/smoke_test_v3_2.py`, `PYTHONPATH=. python3 tests/smoke_test_v3.py`, `PYTHONPATH=. python3 tests/smoke_test_council_004.py`. Source: repo
- Harness: `PYTHONPATH=. python3 tests/run_harness.py`. Source: repo
- Citation benchmark: `PYTHONPATH=. python3 tools/run_citation_bench.py --fail-under 0.95`. Source: repo
- Frontend checks, when touching `frontend/`: `npm run lint`, `npm run typecheck`, and build if release readiness is claimed. Source: repo
- Product/API verification should include real endpoint or browser evidence when behavior changes, not only static checks. Source: inferred

## Open Questions

- Which existing uncommitted changes are intentional release work versus local scratch? Source: unknown
- Whether `reports/` should be pruned, versioned, or treated as generated output for future releases. Source: unknown
