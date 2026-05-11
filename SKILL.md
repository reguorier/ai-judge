---
name: ai-judge
description: >
  Multi-model AI jury system. Query 9 frontier models simultaneously, cross-validate 
  their answers across 5 dimensions, and produce auditable verdicts with human final 
  authority. Local-first, macOS-native, BSL-licensed.
version: 2.0.0
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
```

## Open-Core Boundary

This skill package contains the **public open-core layer**:

| Included (Public) | Not Included (Paid Core) |
|---|---|
| CLI surface and packaging | Production collector engine |
| macOS bridge source code | Browser/CDP automation runtime |
| Public documentation and schemas | Claim scoring engine implementation |
| Docker entrypoint and compose | License validator (private) |
| BSL 1.1 license terms | SaaS license server |
| Prompt templates | Team/enterprise integrations |

Production commands (`jury`, `collect`, `verdict`, `reflect`) require the paid `ai-judge-core` package.

## Related

- [Full Product README](README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Quick Start](docs/QUICKSTART.md)
- [vs llm-council](docs/COMPARISON.md)
