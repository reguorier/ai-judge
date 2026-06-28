# AI Judge Public / Private Boundary

AI Judge is a closed-core commercial project. The private repository is the engineering source of truth. The public repository is a showcase and evaluation doorway unless the owner explicitly publishes a separate public-safe package.

## Public-Safe Material

These items may be reused in a public README, landing page, investor update, demo gallery, or partner brief after a quick privacy review:

- Product positioning and screenshots that do not expose implementation internals.
- Live demo links, especially the citation-audit Hugging Face Space.
- Sanitized benchmark descriptions and aggregate metrics.
- Synthetic examples under `examples/` and benchmark cases that contain no private user facts.
- Public architecture descriptions at the level of workflow, contract, and trust boundary.
- Public docs that say "closed-core", "private", or "public demo" accurately.

## Private Material

These must stay private unless the owner gives explicit written approval for a specific release:

- `core/`, `product/`, `bridges/`, `client/`, and runtime orchestration code.
- Browser/CDP bridge code, fixed-tab automation, web-seat adapters, and model-seat collection logic.
- Local run outputs, raw seat transcripts, legal case payloads, user-submitted facts, browser captures, cookies, screenshots, and logs.
- Growth/outreach drafts containing contact details, private emails, or partnership notes.
- Codex work plans, release seals, local acceptance artifacts, and generated runtime evidence.
- API keys, tokens, credentials, license keys, proxy settings, and private environment files.

## Current Public Message

Use this short description for GitHub profile text, public pages, and partner notes:

> AI Judge is a closed-core, local-first trust layer for AI-generated outputs. It audits whether citations and isolated sources actually support the exact claims in a model answer, preserves dissent and provenance, and generates human-final HTML/JSON/Markdown reports before the answer is reused in a memo, README, report, or client workflow.

## Release Checklist

Before making any branch, repo, release, page, or artifact public:

1. Confirm the target repository or branch is intended to be public.
2. Stage files by explicit path. Do not use `git add -A`.
3. Run a secret scan over staged text.
4. Run a privacy scan for `artifacts/`, `runtime/`, `growth/`, `CODEX_`, `RELEASE_SEAL_`, and case-specific payload names.
5. Search public docs for stale public-source wording and replace it with "closed-core", "private", or "public demo" as appropriate.
6. Re-check generated images for third-party logos or text artifacts.
