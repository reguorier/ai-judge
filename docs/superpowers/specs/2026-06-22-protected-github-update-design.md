# Protected GitHub Update Design

## Goal

Update the AI Judge GitHub presence with the latest local project progress while protecting the commercial core. The existing `reguorier/ai-judge` repository should become the private full engineering repository. Public-facing material should describe the product, demo, benchmarks, and traction without publishing proprietary runtime code or local artifacts.

## Approved Approach

Use a two-layer publication model:

1. Private full repository: push the current local repository to `reguorier/ai-judge` after the repository visibility is changed to private.
2. Public-safe surface: maintain public materials that can be copied into a landing repo, README, pitch, or demo page without exposing proprietary implementation details.

The README should clearly state that AI Judge is not open source. Public demos and benchmark artifacts may be shared, but the core runtime, browser/CDP bridge, production orchestration, model-seat automation, and business workflow code remain closed-core.

## Content Updates

The GitHub-facing materials should emphasize:

- Source-isolated claim-support audit for AI-generated answers.
- Report-first workflow: HTML/JSON/Markdown audit reports before publication.
- Human-final gate, Replay Ledger, Evidence Broker, dissent preservation, provenance tracking, and overclaim detection.
- v3.8 client-first product direction, local-first macOS/runtime packaging, and optional OpenRouter BYOK/Fusion route.
- Current validation signals: public demo expansion, external beta, readability patch, citation benchmark, and legal/compliance demand.
- Protection boundary: public docs/demos/benchmarks vs private runtime/core.

## Safety Rules

- Do not use `git add -A`.
- Do not push until repository visibility is private or the staged diff is public-safe only.
- Keep local runtime outputs, artifacts, browser captures, outreach drafts, personal/legal case payloads, and generated run data out of public surfaces.
- Run explicit checks for secrets, private artifacts, and old "open-source" wording before claiming the update is ready.
- If GitHub authentication is unavailable, finish the local commit and report the exact reauthentication step needed.

## Image Asset

Generate a new README hero that communicates AI Judge's closed-core audit posture without third-party logos. Save it under `assets/ai-judge-protected-core-hero.png` and use it in README.

