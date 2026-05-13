# AI Judge Promotion Kit

## One-liner

AI Judge is a local-first AI jury and evaluation harness that catches the gap between answers that sound smart and answers that survive auditable judgment.

## Short description

AI Judge turns one question into a structured jury session. Multiple AI seats answer independently, their claims pass through auditable scoring, and v3.1 adds golden benchmark cases, regression checks, Hard Truth Mode, and CI-backed harness reports. It is built for developers and researchers who want stronger evidence from AI systems without handing the final decision to another model.

## Links

- GitHub: https://github.com/reguorider-gif/ai-judge
- v3.1 release: https://github.com/reguorider-gif/ai-judge/releases/tag/v3.1.0
- Install in Codex: `$skill-installer install https://github.com/reguorider-gif/ai-judge`
- Quickstart: https://github.com/reguorider-gif/ai-judge/blob/main/docs/QUICKSTART.md
- Architecture: https://github.com/reguorider-gif/ai-judge/blob/main/docs/ARCHITECTURE.md
- Discussions: https://github.com/reguorider-gif/ai-judge/discussions
- Public roadmap issues: https://github.com/reguorider-gif/ai-judge/issues

## Hacker News

Title:

```text
Show HN: AI Judge - catch AI answers that sound smart but fail judgment
```

First comment draft:

```text
I built AI Judge because I kept running into the same trust problem: one model gives a fluent answer, another model gives a different fluent answer, and the hard part is still deciding which claims actually deserve confidence.

The project turns a question into a jury session. Multiple AI seats answer independently, then AI Judge produces a claim-level ledger, bluff-risk gates, consensus notes, graph-value estimates, and an auditable verdict package. v3.1 also adds a harness layer: golden benchmark cases, regression checks, and a GitHub Actions workflow so changes can be evaluated continuously.

The important design choice is that the final decision stays with the human. AI Judge is not trying to be another black-box judge model; it is meant to make model disagreement, weak evidence, and overconfident reasoning easier to inspect.

Repo: https://github.com/reguorider-gif/ai-judge

I would especially like feedback on the harness format, the human-in-the-loop verdict flow, and what benchmark cases should be added next.
```

## Reddit

Title:

```text
I built a local-first multi-model "AI jury" skill for Codex
```

Post draft:

```text
I wanted a workflow where several AI models answer the same question independently, but the final decision is still mine rather than another LLM's ranking.

AI Judge creates a jury-style run: multiple seats answer, claims are broken into a ledger, bluff risk and calibration are scored, consensus and disagreement are surfaced, and the output is an auditable verdict package. v3.1 adds golden benchmark cases, regression tests, a generated harness report, and GitHub Actions CI.

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
AI Judge is a local-first multi-model deliberation system for people who want stronger evidence from AI. Ask one question, collect independent answers from multiple AI seats, run their claims through auditable scoring functions, and receive a verdict package while keeping the final decision human. v3.1 adds golden benchmarks, regression checks, and CI-backed harness reports.
```

## Directory listing

Name: AI Judge

Category: AI agents, developer tools, LLM evaluation, Codex skills

Description:

```text
AI Judge is a local-first Codex skill and CLI for multi-model deliberation and evaluation. It routes one question through multiple AI seats, records independent answers, scores claims with auditable formulas, generates a verdict package with human final authority, and ships v3.1 harness checks for golden benchmarks, regressions, and CI reports.
```

Tags:

```text
ai-agents, agent-skills, codex, llm, multi-agent, local-first, developer-tools, ai-safety, python, macos
```

## Differentiation

Against Hermes Skill:

```text
Hermes-style workflows are strong at producing polished agent outputs. AI Judge focuses on the layer after generation: claim auditing, disagreement inspection, benchmark regression, and whether the answer deserves trust.
```

Against generic LLM council workflows:

```text
Most LLM councils stop at voting, ranking, or consensus prose. AI Judge adds auditable scoring formulas, hard-truth failure modes, neuro-profile signals, golden benchmark fixtures, and CI regression checks.
```

Against Perplexity-style model committees:

```text
Perplexity-style committees are optimized for answer discovery and synthesis. AI Judge is optimized for decision hygiene: evidence ledgers, bluff-risk gates, reproducible harness results, and human final authority.
```

## Chinese launch copy

Title:

```text
我做了一个 AI Judge：专门抓“看起来很聪明但经不起判断”的 AI 回答
```

Post:

```text
AI Judge 是一个本地优先的多模型评审 skill/CLI。它不是再训练一个“裁判模型”，而是让多个 AI seat 独立回答同一个问题，再把回答拆成 claim ledger，用可审计评分函数、共识/分歧检查、bluff-risk gate、Hard Truth Mode 和 v3.1 的 golden benchmark/regression harness 去判断答案到底靠不靠谱。

我想解决的问题很简单：AI 回答越来越流畅，但人真正需要的是“我该不该信它，以及哪里不该信”。所以 AI Judge 的最后一票仍然保留给人，它只是把证据、分歧、风险和回归测试摊开。

GitHub: https://github.com/reguorider-gif/ai-judge
欢迎试用、提 issue，尤其欢迎提供容易骗过 LLM 的 benchmark case。
```

## Submission tracker

- ForgeIndex: submitted on 2026-05-13 with v3.1 release link.
- GitHub Discussions: enabled, with roadmap, benchmark-call, and next-evaluation prompts live.
- GitHub issues: public roadmap items opened for Qwen/Ollama demo, launch demo, HTML verdict exports, directory submissions, and MiMo jury seat.
- Next directory targets: OSS AI Hub, AgentsTide, Exgentic Open Agent Leaderboard.
- Next community targets: Show HN, Product Hunt, Reddit r/LocalLLaMA, V2EX, 即刻/小红书/Bilibili demo.
