---
name: ai-judge
description: >
  Local-first multi-model AI jury system with a v2 scoring engine. Query 9 AI seats,
  score claims with 10 auditable functions, detect bluff risk and echo-chamber
  consensus, and keep final authority with the human.
version: 2.1.0
license: BSL-1.1
homepage: https://github.com/reguorier/ai-judge
tags: [ai, multi-model, jury, verdict, cross-validation, llm, audit, council]
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

## Installation

```bash
# Install via pip
pip install -e .

# Or via Docker
docker pull ghcr.io/reguorier/ai-judge:latest
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
ai-judge score-v2 --demo
```

## Open-Core Boundary

This skill package contains the **public open-core layer**:

| Included (Public) | Not Included (Paid Core) |
|---|---|
| CLI surface, packaging, and `score-v2 --demo` | Production collector engine |
| v2 formula engine and demo pipeline | Production browser/CDP orchestration |
| macOS bridge source code | Managed scoring service/runtime |
| Public documentation and schemas | SaaS license server |
| Docker entrypoint and compose | Team/enterprise integrations |
| BSL 1.1 license terms | Support/SLA layer |
| Prompt templates | Hosted deployment tooling |

Production commands (`jury`, `collect`, `verdict`, `reflect`) require the paid `ai-judge-core` package.

## Related

- [Full Product README](README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Quick Start](docs/QUICKSTART.md)
- [vs llm-council](docs/COMPARISON.md)
