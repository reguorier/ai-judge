---
name: ai-judge
description: >
  Local-first multi-model AI jury system with v3.2 evidence tracing and dissent.
  Query 9 AI seats, score claims with auditable functions, detect bluff risk and
  echo-chamber consensus, profile cognitive proxy signals, render reasoning trees,
  and keep final authority with the human.
version: 3.2.0
license: BSL-1.1
homepage: https://github.com/reguorider-gif/ai-judge
tags: [ai, multi-model, jury, verdict, cross-validation, llm, audit, council, hard-truth, evidence, dissent, reasoning-tree]
platforms: [macOS]
dependencies: [python3.11, chrome, docker]
---

# AI Judge — Skill Package

## What This Skill Does

Installs the AI Judge multi-model deliberation system as a Hermes-compatible skill. Once installed, you can:

- `ai-judge jury --question "..."` — Create a jury session with 9 AI seats
- `ai-judge collect --run latest` — Collect independent answers from all seats
- `ai-judge verdict --run latest` — Generate auditable verdict with evidence scoring
- `ai-judge reflect --date YYYY-MM-DD` — Daily performance reflection
- `ai-judge score-v2 --demo` — Run the public v2 scoring-engine demo
- `ai-judge neuro-profile --demo` — Run the v3.1 cognitive proxy demo
- `ai-judge hard-truth --demo` — Preview L0-L4 judgment-first feedback
- `ai-judge v3-pipeline --demo` — Run the full v3.1 pipeline
- `ai-judge v3.2-pipeline --demo` — Run evidence + dissent + reasoning-tree demo

## Installation

```bash
# Install via pip
pip install -e .

# Or via Docker
docker pull ghcr.io/reguorider-gif/ai-judge:latest
```

## Requirements

- macOS (required for desktop app bridges)
- Python 3.11+
- Google Chrome with remote debugging enabled (port 9223)
- Active License Key for production use

## Quick Test

```bash
ai-judge license status
ai-judge --help
ai-judge v3-pipeline --demo
ai-judge v3.2-pipeline --demo
```

## Open-Core Boundary

This skill package contains the **public open-core layer**:

| Included (Public) | Not Included (Paid Core) |
|---|---|
| CLI surface, packaging, and v2/v3/v3.2 demos | Production collector engine |
| v2 formula engine, v3 cognitive proxy demos, v3.2 evidence/dissent demo | Production browser/CDP orchestration |
| macOS bridge source code | Managed scoring service/runtime |
| Public documentation and schemas | SaaS license server |
| TypeScript UI components and Rust reference engine | Managed desktop app distribution |
| Docker entrypoint and compose | Team/enterprise integrations |
| BSL 1.1 license terms | Support/SLA layer |
| Prompt templates | Hosted deployment tooling |

Production commands (`jury`, `collect`, `verdict`, `reflect`) require the paid `ai-judge-core` package.

## Related

- [Full Product README](README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Quick Start](docs/QUICKSTART.md)
- [v3.2 Release Notes](RELEASE_V3_2.md)
- [vs llm-council](docs/COMPARISON.md)
