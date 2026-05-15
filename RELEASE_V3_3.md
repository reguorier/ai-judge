# AI Judge v3.3.0 — COUNCIL-004 Release Notes

## Overview

v3.3.0 adds COUNCIL-004 Phase 1: fixed persona seats and lightweight evidence trace tooling. The goal is to make multi-model agreement more inspectable: each seat has a stable judging posture, and shared citation sources can be flagged before the human treats agreement as independent confirmation.

The release is additive. Existing v2 scoring, v3.1 cognitive proxy demos, Hard Truth Mode, v3.2 evidence/dissent/reasoning-tree demos, harness tests, and open-core boundaries remain intact.

## New in v3.3.0

### `core/seat_personas.py` — Fixed Persona Seats

- Defines 9 stable seat cards: Gemini, ChatGPT, DeepSeek, Qwen, Kimi, Grok, Yuanbao, MiMo, and Doubao.
- Each card includes MBTI-style mode, risk preference, cognitive bias, ideology, strengths, weaknesses, and jury prompt injection.
- Adds helpers for listing seats, fetching one persona, and rendering a dispatch prompt.

### `core/evidence_trace.py` — L1/L2/L3 Evidence Trace

- L1 detects explicit citations such as URLs, DOI strings, arXiv IDs, and named paper-style references.
- L2 detects implied citations such as "according to X report" or Chinese source-report phrasing.
- L3 flags claims with no citation support.
- Cross-model contamination scanning detects sources shared by 3+ seats and warns about pseudo-consensus.

## CLI Commands

```bash
ai-judge seats --list
ai-judge seats --show grok

ai-judge trace --demo
ai-judge trace --claim "According to the 2025 IMF report, global debt reached $300T"
ai-judge trace --claims-file path/to/claim-ledger.json
```

## Updated Modules

- `cli/main.py`: adds `seats` and `trace` subcommands.
- `core/__init__.py`: documents COUNCIL-004 modules and bumps metadata to `3.3.0`.
- `README.md`, `SKILL.md`, `docs/QUICKSTART.md`, and `product/landing.html`: surface the new persona and trace workflow.

## Quick Demo

```bash
python3 cli/main.py seats --list
python3 cli/main.py seats --show grok
python3 cli/main.py trace --demo
python3 cli/main.py trace --claim "根据2025年IMF报告，全球债务达到300万亿"
```

Expected behavior:

- `seats --list` returns all 9 persona summaries.
- `seats --show grok` returns Grok's ENTP-style skeptical seat card and prompt injection.
- `trace --demo` reports shared source contamination for repeated IMF/Nature-style references.
- `trace --claim ...` classifies evidence trace level as L1, L2, or L3.

## Release Package

- Repository target: `https://github.com/reguorier/ai-judge`
- Public release files include the COUNCIL-004 core modules, CLI commands, docs, product page, and tests.
