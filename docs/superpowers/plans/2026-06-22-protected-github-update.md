# Protected GitHub Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update AI Judge's GitHub-facing content while keeping the complete repository private and the commercial core closed.

**Architecture:** Treat the repository as the private source of truth. The README and boundary docs become the reusable public-safe material, while `.gitignore` and verification checks prevent local artifacts from being staged accidentally.

**Tech Stack:** Git, GitHub CLI/API, Markdown docs, generated PNG asset, local grep-based leak checks.

---

### Task 1: Add Protected Publication Boundary

**Files:**
- Create: `docs/PUBLIC_PRIVATE_BOUNDARY.md`
- Modify: `.gitignore`

- [x] **Step 1: Document the boundary**

Create `docs/PUBLIC_PRIVATE_BOUNDARY.md` with the exact public/private split and release checklist.

- [x] **Step 2: Harden ignore rules**

Add local/private artifact patterns for generated run data, Codex notes, release seals, runtime folders, and trace outputs.

### Task 2: Refresh GitHub-Facing README

**Files:**
- Modify: `README.md`
- Add asset: `assets/ai-judge-protected-core-hero.png`

- [x] **Step 1: Replace the hero visual**

Use the generated protected-core hero image.

- [x] **Step 2: Update positioning**

State that AI Judge is a closed-core, private commercial product with public demos and benchmarks.

- [x] **Step 3: Add latest progress**

Summarize v3.8, demo/beta metrics, OpenRouter route, benchmark coverage, and first user wedge.

- [x] **Step 4: Replace open-core language**

Change the previous open-core table into a protected repository boundary table.

### Task 3: Align License Metadata

**Files:**
- Modify: `LICENSE`
- Modify: `pyproject.toml`

- [x] **Step 1: Make the license posture explicit**

Use a proprietary/private notice for current repository contents, with a note that earlier public snapshots may retain their original published terms.

- [x] **Step 2: Align package metadata**

Set `license = {text = "Proprietary"}` while keeping the classifier as `Other/Proprietary License`.

### Task 4: Verify Before Commit/Push

**Files:**
- Read-only verification over repository.

- [ ] **Step 1: Inspect diff**

Run `git diff -- README.md LICENSE pyproject.toml .gitignore docs/PUBLIC_PRIVATE_BOUNDARY.md docs/superpowers/specs/2026-06-22-protected-github-update-design.md docs/superpowers/plans/2026-06-22-protected-github-update.md`.

- [ ] **Step 2: Check old open-source wording in public docs**

Run `rg -n "open-source|open source|open_source" README.md docs/PUBLIC_PRIVATE_BOUNDARY.md docs/LAUNCH_DEMO_KIT.md docs/MICROSOFT_AGENT_ACADEMY.md growth/openrouter_works_with_or_app_draft.yaml`.

- [ ] **Step 3: Check secrets and local artifact patterns in staged files**

Run `git diff --cached --name-only` and then scan staged text for `OPENAI_API_KEY|OPENROUTER_API_KEY|sk-|ghp_|github_pat_|password|token|cookie|private_key|BEGIN .*PRIVATE KEY`.

- [ ] **Step 4: Confirm repository visibility**

Run `gh repo view reguorier/ai-judge --json visibility`.

- [ ] **Step 5: Make repo private before pushing full source**

Run `gh api -X PATCH repos/reguorier/ai-judge -f private=true` after GitHub auth is valid.

### Task 5: Commit and Push

**Files:**
- Stage only the intended docs/image/license/protection files unless repository has already been made private and the user explicitly wants the whole working tree pushed.

- [ ] **Step 1: Stage explicit files**

Run `git add README.md LICENSE pyproject.toml .gitignore assets/ai-judge-protected-core-hero.png docs/PUBLIC_PRIVATE_BOUNDARY.md docs/superpowers/specs/2026-06-22-protected-github-update-design.md docs/superpowers/plans/2026-06-22-protected-github-update.md`.

- [ ] **Step 2: Commit**

Run `git commit -m "docs: protect GitHub-facing AI Judge materials"`.

- [ ] **Step 3: Push**

Run `git push -u origin $(git branch --show-current)` after private visibility is verified.

