# Citation Audit Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a self-serve Citation Audit launch edition that can generate demos, run a benchmark, support CI, and prepare a fully automated Pro checkout funnel.

**Architecture:** Add a narrow `core.citation_audit` facade over Evidence Broker and Grand Judge, expose it through `ai-judge audit`, then wrap the same entrypoint with GitHub Action and HuggingFace Space assets. Keep browser bridges out of the launch path so the demo is deterministic.

**Tech Stack:** Python stdlib, existing AI Judge core modules, pytest, GitHub Actions composite action, Gradio Space source.

---

### Task 1: Core Citation Audit Facade

**Files:**
- Create: `core/citation_audit.py`
- Test: `tests/test_citation_audit.py`

- [x] Add Markdown/JSON audit input loader.
- [x] Add `run_citation_audit()` orchestration over Evidence Broker and Grand Judge.
- [x] Add HTML, Markdown, and JSON report renderers.
- [x] Verify user-supplied evidence can validate citations.
- [x] Verify model-mentioned candidate sources cannot self-verify.

### Task 2: CLI and Demo Reports

**Files:**
- Modify: `cli/main.py`
- Create: `examples/fake-citation.md`
- Create: `examples/product-no-evidence.md`
- Create: `examples/sounds-smart-low-judgment.md`
- Create: `reports/*.html`
- Create: `reports/*.json`

- [x] Add `ai-judge audit <input> --html --json --md`.
- [x] Generate three deterministic launch reports.
- [x] Keep network fetching off by default.

### Task 3: Benchmark and CI

**Files:**
- Create: `citation-bench/citation-bench-100.jsonl`
- Create: `tools/run_citation_bench.py`
- Create: `.github/actions/citation-audit/action.yml`
- Create: `.github/workflows/citation-audit.yml`
- Modify: `.github/workflows/publish.yml`

- [x] Add 100 deterministic cases across five citation statuses.
- [x] Add benchmark runner with accuracy threshold.
- [x] Add reusable GitHub Action.
- [x] Add workflow artifacts for reports and benchmark result.

### Task 4: Launch and Monetization Assets

**Files:**
- Modify: `README.md`
- Modify: `product/landing.html`
- Create: `docs/LAUNCH_CITATION_AUDIT.md`
- Create: `docs/CITATION_AUDIT_QUICKSTART.md`
- Create: `docs/PRO_AUTOMATION.md`
- Create: `growth/launch_posts.md`
- Create: `growth/reply_bank.md`
- Create: `growth/email_sequence.md`
- Create: `product/checkout_config.example.json`
- Create: `spaces/citation-audit/*`

- [x] Reposition repository around Citation Audit.
- [x] Add launch copy, reply bank, and email sequence.
- [x] Add HuggingFace Space source.
- [x] Add Lemon Squeezy checkout configuration placeholder.

### Task 5: Verification

- [x] Run Python compile check.
- [x] Run 61 targeted tests.
- [x] Run 100-case citation benchmark.
- [x] Run frontend JavaScript syntax check.
- [x] Restart local API server and verify v3.6 health.
