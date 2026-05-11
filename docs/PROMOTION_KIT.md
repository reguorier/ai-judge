# AI Judge Promotion Kit

## One-liner

AI Judge is a local-first Codex skill that lets 9 AI models deliberate independently, cross-validates their claims, and leaves the final verdict to the human.

## Short description

AI Judge turns one question into a structured jury session. Nine AI seats answer independently, their claims are cross-validated across five dimensions, and the output is an auditable verdict package. It is built for people who want better evidence from AI systems without handing the final decision to another model.

## Links

- GitHub: https://github.com/reguorier/ai-judge
- Install in Codex: `$skill-installer install https://github.com/reguorier/ai-judge`
- Quickstart: https://github.com/reguorier/ai-judge/blob/main/docs/QUICKSTART.md
- Architecture: https://github.com/reguorier/ai-judge/blob/main/docs/ARCHITECTURE.md

## Hacker News

Title:

```text
Show HN: AI Judge, a local-first tool for comparing answers from multiple AI models
```

First comment draft:

```text
I built AI Judge because I kept running into the same trust problem: one model gives a fluent answer, but I still have to decide which claims are reliable.

The project turns a question into a jury session. Multiple AI seats answer independently, then AI Judge produces a claim-level ledger, consensus notes, and an auditable verdict package. The important design choice is that the final decision stays with the human; the system is meant to improve judgment, not replace it.

The public repo contains the Codex skill, CLI surface, schemas, docs, Docker packaging, and bridge source. I would especially like feedback on the audit format, the local-first architecture, and whether the "human holds the gavel" workflow feels useful or too heavy.
```

## Reddit

Title:

```text
I built a local-first multi-model "AI jury" skill for Codex
```

Post draft:

```text
I wanted a workflow where several AI models answer the same question independently, but the final decision is still mine rather than another LLM's ranking.

AI Judge creates a jury-style run: multiple seats answer, claims are broken into a ledger, consensus and disagreement are surfaced, and the output is an auditable verdict package. The repo is open-core BSL and includes the Codex skill, CLI surface, schemas, Docker packaging, docs, and macOS bridge source.

The part I am most interested in discussing is the evaluation shape: is claim-level cross-validation a useful interface for real decisions, or would you rather see a lighter comparison format?

Repo: https://github.com/reguorier/ai-judge
```

## Product Hunt

Tagline:

```text
9 AI models deliberate. You hold the gavel.
```

Description:

```text
AI Judge is a local-first multi-model deliberation system for people who want stronger evidence from AI. Ask one question, collect independent answers from multiple AI seats, cross-validate claims, and receive an auditable verdict package while keeping the final decision human.
```

## Directory listing

Name: AI Judge

Category: AI agents, developer tools, LLM evaluation, Codex skills

Description:

```text
AI Judge is a local-first Codex skill and CLI for multi-model deliberation. It routes one question through multiple AI seats, records independent answers, cross-validates claims, and generates an auditable verdict package with human final authority.
```

Tags:

```text
ai-agents, agent-skills, codex, llm, multi-agent, local-first, developer-tools, ai-safety, python, macos
```
