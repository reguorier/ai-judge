# Outreach Batch 002 - Agent Eval / ARC Entry

Status: partially_executed
Created: 2026-05-20

This batch continues the 20-target outreach list after Batch 001. It uses only
verified official channels or public community routes. It avoids guessed private
emails and avoids posting duplicate promotional copy into communities that have
already filtered the launch.

## Targets

| ID | Priority | Target | Verified route | Why this route | Status |
|---|---:|---|---|---|---|
| O006 | P0 | ARC Prize Foundation | `team@arcprize.org` | Official ARC community page says to reach the team by this email or Discord; AI Judge has a credible evaluator-not-solver angle. | sent_2026-05-20 |
| O007 | P0 | Microsoft AutoGen | `autogen@microsoft.com` | Microsoft Research lists this as the AutoGen contact; agent trace evaluation fits AutoGenBench / multi-agent trace debugging. | sent_2026-05-20 |
| O008 | P1 | LangChain / LangGraph community | LangChain Forum | Agent trace audit and post-run evaluation fit LangChain's agent workflow community, but it should be posted as a discussion, not a repo issue. | forum_login_or_post_needed |
| O009 | P1 | LlamaIndex community | Discord / GitHub Discussions | Claim-source audit fits RAG faithfulness and citation-support workflows; use public community route only. | community_login_or_post_needed |
| O010 | P1 | AutoGen GitHub Discussions | GitHub Discussions | Public discussions are active and include audit-trail / agent-memory / evaluation topics. | github_session_needed |

## O006 - ARC Prize

Subject:

```text
Evaluator tooling for ARC-AGI-3 agent traces?
```

Body:

```text
Hi ARC Prize team,

I am building AI Judge, a source-available evaluator layer for AI outputs, citations, and agent traces.

For ARC-AGI-3, I am not pitching it as a solver. The relevant angle is evaluator tooling: given an agent attempt log, can we produce a human-readable verdict on exploration quality, evidence for actions, missed alternatives, and model-seat disagreement?

Repo: https://github.com/reguorier/ai-judge
Agent trace audit note: https://github.com/reguorier/ai-judge/blob/main/docs/ARC_AGENT_TRACE_AUDIT.md
Citation audit demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

Would this kind of trace-audit output be useful to ARC teams comparing agent attempts, or is the current community focus only on solver submissions?

Best,
Reguorier
```

## O007 - AutoGen

Subject:

```text
Trace-audit feedback for AutoGen-style multi-agent runs
```

Body:

```text
Hi AutoGen team,

I am building AI Judge, a small evaluator layer for AI outputs and agent traces.

The closest fit with AutoGen is not another multi-agent runtime. It is a post-run audit: preserve an agent attempt log, score whether actions were supported by evidence, surface missed alternatives, and produce a human-readable verdict before a human signs off.

Repo: https://github.com/reguorier/ai-judge
Agent trace note: https://github.com/reguorier/ai-judge/blob/main/docs/ARC_AGENT_TRACE_AUDIT.md
Example report: https://github.com/reguorier/ai-judge/blob/main/examples/agent-trace-verdict.md

Would this be more useful as an AutoGenBench-style report adapter, a GitHub Action, or a standalone trace-audit format?

Best,
Reguorier
```

## Non-Email Drafts

### LangChain Forum

```text
I am building AI Judge as a post-run evaluator for agent traces: preserve the attempt log, check whether actions were supported by evidence, surface missed alternatives, and keep dissent visible before human signoff.

For LangGraph/LangChain users: would this be more useful as a LangSmith-adjacent report artifact, a CI check, or a standalone Markdown/JSON trace verdict?

Repo: https://github.com/reguorier/ai-judge
Trace note: https://github.com/reguorier/ai-judge/blob/main/docs/ARC_AGENT_TRACE_AUDIT.md
```

### LlamaIndex Community

```text
I am testing AI Judge as a claim-source audit layer for RAG answers: source existence is not enough; the cited source has to support the generated claim.

For LlamaIndex users, would a claim-support verdict be useful as a RAG eval artifact alongside retrieval relevance / faithfulness, or should it remain an external audit report?

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Repo: https://github.com/reguorier/ai-judge
```

## Execution Log

- 2026-05-20: Sent O006 to `team@arcprize.org` from Tencent Enterprise Mail. Mail UI showed `发送成功` and saved to Sent.
- 2026-05-20: Sent O007 to `autogen@microsoft.com` from Tencent Enterprise Mail. Mail UI showed `发送成功` and saved to Sent.
- O008/O009/O010 remain public community routes; do not guess private emails or duplicate removed Reddit-style launch copy.
