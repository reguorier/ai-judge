# AI Judge Promotion Kit

## One-liner

AI Judge is a local-first Codex skill where 9 AI seats deliberate, scoring functions audit their claims, cognitive proxy signals expose "sounds smart" vs "is smart", and the human keeps the final verdict.

## Short description

AI Judge turns one question into a structured jury session. Nine AI seats answer independently, their claims pass through auditable scoring, and v3.1 adds hard truth mode for judgment-quality gaps. It is built for people who want better evidence from AI systems without handing the final decision to another model.

## Links

- GitHub: https://github.com/reguorider-gif/ai-judge
- Install in Codex: `$skill-installer install https://github.com/reguorider-gif/ai-judge`
- Quickstart: https://github.com/reguorider-gif/ai-judge/blob/main/docs/QUICKSTART.md
- Architecture: https://github.com/reguorider-gif/ai-judge/blob/main/docs/ARCHITECTURE.md

## Hacker News

Title:

```text
Show HN: AI Judge, a local-first tool for comparing answers from multiple AI models
```

First comment draft:

```text
I built AI Judge because I kept running into the same trust problem: one model gives a fluent answer, but I still have to decide which claims are reliable.

The project turns a question into a jury session. Multiple AI seats answer independently, then AI Judge produces a claim-level ledger, bluff-risk gates, diversity notes, graph-value estimates, and an auditable verdict package. The important design choice is that the final decision stays with the human; the system is meant to improve judgment, not replace it.

The public repo contains the Codex skill, CLI surface, v2 scoring engine, schemas, docs, Docker packaging, and bridge source. I would especially like feedback on the audit format, the local-first architecture, and whether the "human holds the gavel" workflow feels useful or too heavy.
```

## Reddit

Title:

```text
I built a local-first multi-model "AI jury" skill for Codex
```

Post draft:

```text
I wanted a workflow where several AI models answer the same question independently, but the final decision is still mine rather than another LLM's ranking.

AI Judge creates a jury-style run: multiple seats answer, claims are broken into a ledger, bluff risk and calibration are scored, consensus and disagreement are surfaced, and the output is an auditable verdict package. The repo is open-core BSL and includes the Codex skill, CLI surface, v2 scoring engine, schemas, Docker packaging, docs, and macOS bridge source.

The part I am most interested in discussing is the evaluation shape: is claim-level cross-validation a useful interface for real decisions, or would you rather see a lighter comparison format?

Repo: https://github.com/reguorider-gif/ai-judge
```

## Product Hunt

Tagline:

```text
9 AI models deliberate. You hold the gavel.
```

Description:

```text
AI Judge is a local-first multi-model deliberation system for people who want stronger evidence from AI. Ask one question, collect independent answers from multiple AI seats, run their claims through auditable scoring functions, and receive a verdict package while keeping the final decision human.
```

## Directory listing

Name: AI Judge

Category: AI agents, developer tools, LLM evaluation, Codex skills

Description:

```text
AI Judge is a local-first Codex skill and CLI for multi-model deliberation. It routes one question through multiple AI seats, records independent answers, scores claims with auditable v2 formulas, and generates a verdict package with human final authority.
```

Tags:

```text
ai-agents, agent-skills, codex, llm, multi-agent, local-first, developer-tools, ai-safety, python, macos
```
