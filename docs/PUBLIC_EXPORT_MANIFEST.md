# Public Export Manifest

This manifest defines the clean public showcase export. The public repository is
a doorway for product evaluation and demos, not the private source of truth.

## Include

- `README.md`
- `LICENSE`
- `product/landing.html`
- `docs/PUBLIC_PRIVATE_BOUNDARY.md`
- `docs/PUBLIC_EXPORT_MANIFEST.md`
- `docs/TRY_AI_JUDGE_IN_3_MINUTES.md`
- `docs/ARC_AGENT_TRACE_AUDIT.md`
- `docs/CLAIM_SPAN_ROADMAP.md`
- `docs/UNVERIFIABLE_IS_NOT_FALSE.md`
- `docs/GITHUB_CONVERSION_CHECKLIST.md`
- `assets/ai-judge-public-flow.svg`
- `assets/citation-audit-space-output.png`
- `assets/ai-judge-v3-hero.png`
- `citation-bench/citation-bench-100.jsonl`
- `citation-bench/citation-bench-hard-11.jsonl`
- `CONTRIBUTING.md`
- `scripts/verify_public_snapshot.py`
- `.github/ISSUE_TEMPLATE/*`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/public-snapshot.yml`
- `examples/*.md`
- `examples/agent-trace-*.json`
- `reports/citation-batch/*`
- `reports/*-audit.html`
- `reports/*-audit.json`
- `reports/agent-trace-*`

## Exclude

- `core/`
- `product/api_server.py`
- `product/dashboard.*`
- `bridges/`
- `client/`
- `tools/`
- `harness/`
- `desktop/`
- `growth/`
- `papers/`
- `backups/`
- runtime outputs, browser profiles, cookies, screenshots, local logs, private
  operator notes, and generated evidence packs.

## Export Rule

Export by explicit allowlist only. Do not publish from the private engineering
repository with `git add -A`, and do not treat the public repository as a mirror
of private runtime history.
