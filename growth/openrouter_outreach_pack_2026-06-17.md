# OpenRouter Outreach Pack - AI Judge

Status: executed_initial_outreach
Created: 2026-06-17
Last updated: 2026-06-18 01:33 HKT

## Execution Log

2026-06-18 01:19 HKT:

- Sent formatted QQ Mail outreach from `Flywise-ace <598615675@qq.com>` to `support@openrouter.ai`.
- Subject: `AI Judge x OpenRouter: multi-model audit benchmark + possible integration`.
- OpenRouter Zendesk auto-reply received: ticket `#31295`.

2026-06-18 01:31 HKT:

- Sent a short routing clarification to `support@openrouter.ai`.
- Subject: `Re: [Support] AI Judge x OpenRouter benchmark / partnership route [#31295]`.
- OpenRouter Zendesk opened a separate auto-reply ticket: `#31297`.

2026-06-18 01:45 HKT:

- Created AI Judge GitHub issue `#10`: `Add OpenRouter BYOK integration and prepare Works With OR submission`.
- URL: `https://github.com/reguorier/ai-judge/issues/10`.
- Purpose: track the OpenRouter BYOK integration and docs required before any Works With OpenRouter PR.

2026-06-18 02:12 HKT:

- Canceled Codex heartbeat automation `openrouter-follow-up-check` at user request.
- Retried Discord after login. The session is logged in as `reguorider`, but Discord requires phone verification before accepting the OpenRouter invite or posting.

Route findings:

- `https://openrouter.ai/enterprise/form` currently exposes no fillable sales form in the loaded page and points users to `Visit Support`.
- `https://openrouter.ai/support` exposes `Create Ticket`, `Email Support`, and `Join Discord`; the email route successfully created Zendesk tickets.
- Discord invite loads and Safari is logged in as `reguorider`, but Discord now requires phone verification before accepting the OpenRouter invite or posting.
- `Works with OpenRouter` points to `https://github.com/OpenRouterTeam/awesome-openrouter`. The contribution rules require the app to already use OpenRouter for model access and allow users to bring their own OpenRouter API key, so do not submit AI Judge there until an OpenRouter-backed integration/docs page exists. AI Judge issue `#10` now tracks this prerequisite.

## Goal

Reach OpenRouter with a clear, non-spammy collaboration ask:

1. Compare OpenRouter Fusion and AI Judge on shared benchmark cases.
2. Explore AI Judge as an audit/report layer on top of OpenRouter model routing.
3. Request bulk/community/research credits or discounted invoiced credits for a public benchmark.
4. Submit AI Judge to Works with OpenRouter after an OpenRouter API integration is visible.

## Best Contact Routes

| Priority | Route | URL | Purpose | Notes |
|---:|---|---|---|---|
| P0 | Enterprise / Contact Sales | https://openrouter.ai/enterprise | Bulk credits, partnership, dedicated engineering contact | Enterprise page mentions invoiced billing and bulk credits. Support FAQ says no standard volume discounts, so frame as exceptional research/community benchmark. |
| P0 | Support ticket | https://openrouter.zendesk.com/hc/en-us/requests/new?ticket_form_id=41705079656219 | Route the partnership request to the right person | Use if enterprise form does not fit or if we need billing/credits follow-up. |
| P1 | Discord | https://discord.com/invite/openrouter | Ask community/team who handles app ecosystem and benchmarking | Keep short; do not paste a long pitch. |
| P1 | X | https://twitter.com/openrouter | Public/lightweight intro or ask for best contact | Best after the support/enterprise route is submitted. |
| P1 | Works with OpenRouter PR | https://github.com/OpenRouterTeam/awesome-openrouter | Directory listing after integration | Requirements include OpenRouter API usage, BYOK support, public landing page, logo, and traction/notability. |
| P2 | GitHub issue in awesome-openrouter | https://github.com/OpenRouterTeam/awesome-openrouter/issues | Ask submission question if PR path is unclear | Use only if we have a concrete integration/listing question. |

## Positioning

Short version:

AI Judge is a local-first citation-audit and decision-audit layer for LLM outputs. OpenRouter solves model access, routing, fallback, and billing; AI Judge adds claim-level evidence audit, dissent preservation, reasoning traces, Meta-Judge model weighting, and human-final report gates.

Why OpenRouter might care:

- It gives OpenRouter a sharper reliability story beyond "more models behind one API".
- It creates a benchmark/demo showing OpenRouter as the model access layer for multi-model audit workflows.
- It can become a "Works with OpenRouter" app in the research/productivity category.
- It may generate visible examples around Fusion vs source-isolated audit, without positioning Fusion as a failure.

Do not claim:

- That AI Judge proves factual truth.
- That OpenRouter/Fusion is unsafe.
- That we already have official OpenRouter partnership.
- That a discount is guaranteed.

## Main Enterprise / Partnership Email

Subject:

```text
AI Judge x OpenRouter: multi-model audit benchmark + possible integration
```

Body:

```text
Hi OpenRouter team,

I am building AI Judge, a local-first citation-audit and decision-audit layer for LLM outputs.

OpenRouter already solves the part we do not want to rebuild: unified model access, provider routing, fallback, billing, and enterprise controls. AI Judge focuses on the layer above that: claim-level evidence checks, source-isolated citation audit, dissent preservation, model-seat comparison, Meta-Judge weighting, and a human-final report gate before an AI-generated answer is reused in a memo, report, README, or client-facing workflow.

Project:
https://github.com/reguorier/ai-judge

Live citation-audit demo:
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

I would love to explore one of three lightweight paths:

1. A small comparison benchmark: OpenRouter Fusion vs AI Judge report-first audit on 10-20 citation/claim-support cases.
2. An integration path where AI Judge uses OpenRouter as the model access/routing layer, then contributes an auditable HTML/JSON report on top.
3. A community/research credit arrangement for running multi-model reliability benchmarks publicly, with OpenRouter credited as the model infrastructure layer.

The intent is collaborative, not competitive. Fusion is great for fast multi-model synthesis; AI Judge is narrower and stricter around evidence isolation, overclaim detection, dissent, and human-final publication gates.

If this is interesting, who is the best person to speak with about app ecosystem, benchmarks, or bulk/community credits?

Best,
Reguorier
AI Judge
```

## Contact Sales Form Draft

Use this for the enterprise/contact-sales form.

```text
Company / Project:
AI Judge

Website / Repo:
https://github.com/reguorier/ai-judge

Product:
Local-first citation-audit and decision-audit layer for LLM outputs. AI Judge creates auditable HTML/JSON reports with claim-level evidence status, source isolation, dissent, model-seat comparison, Meta-Judge weighting, and human-final publication gates.

Use case:
We want to evaluate OpenRouter as the model access/routing layer for AI Judge, and run a small public benchmark comparing multi-model synthesis with source-isolated audit reports.

Request:
1. Discuss OpenRouter API integration for AI Judge.
2. Explore whether AI Judge can become a Works with OpenRouter app after integration.
3. Ask whether bulk/community/research credits or invoiced credits are possible for a public reliability benchmark.

Estimated usage:
Initial benchmark: 10-20 cases x 5-10 models, then repeated evaluation runs as the audit protocol improves. If the integration works, ongoing usage would come from users bringing their own OpenRouter API key.

Why OpenRouter:
OpenRouter already provides unified model access, provider routing, fallback, billing, and enterprise/privacy controls. AI Judge does not want to rebuild model access; it wants to add an auditable decision/report layer on top.
```

## Discord Short Message

```text
Hi OpenRouter team/community - quick question: who is the best person to contact about app ecosystem or reliability benchmark collaborations?

I am building AI Judge, a local-first citation/decision audit layer for LLM outputs:
https://github.com/reguorier/ai-judge

OpenRouter would be a natural model access layer for us. We are interested in a lightweight benchmark/integration: OpenRouter routing/Fusion for model collection, AI Judge for claim-level evidence audit, dissent, Meta-Judge weighting, and human-final HTML/JSON reports.

I do not want to spam the wrong channel. Should this go through enterprise/contact sales, a GitHub issue, or someone specific?
```

## X / LinkedIn DM

```text
Hi OpenRouter team - I am building AI Judge, a local-first citation/decision audit layer for LLM outputs.

OpenRouter seems like the right model access/routing layer for us. Would you be open to a small benchmark or integration conversation? The fit: OpenRouter handles models + fallback; AI Judge adds source-isolated evidence audit, dissent, Meta-Judge weighting, and human-final reports.

Repo: https://github.com/reguorier/ai-judge
Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

Who is the best person/channel for this?
```

## GitHub Issue / PR Positioning

Do this only after AI Judge has a visible OpenRouter integration page or docs.

Potential Works with OpenRouter entry:

```yaml
name: "AI Judge"
description: "Local-first citation and decision audit layer for LLM outputs. Use OpenRouter models for multi-seat judging, then generate source-isolated HTML/JSON reports with evidence status, dissent, and human-final gates."
url: "https://github.com/reguorier/ai-judge"
docs: "https://github.com/reguorier/ai-judge#openrouter"
tags:
  - research
  - productivity
open_source: "https://github.com/reguorier/ai-judge"
date_added: "2026-06-17"
```

Needed before PR:

- OpenRouter API key setup docs added in `docs/OPENROUTER.md`.
- BYOK support path added through `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` / OpenRouter app attribution config.
- Add public logo file.
- Add one OpenRouter-backed demo report.

Status update 2026-06-18 02:40 HKT:

- Added OpenRouter-specific env aliases to the existing OpenAI-compatible FDJP provider.
- Added optional Fusion request mode with `OPENROUTER_MODEL=openrouter/fusion` and `OPENROUTER_FORCE_FUSION=1`.
- Added request-shape tests for app attribution headers and provider override behavior.
- Added `docs/OPENROUTER.md` as the public BYOK/Fusion setup page.

## Proposed Comparison Benchmark

Benchmark framing:

```text
Not "which product wins?"
Better: "What is each layer good at?"
```

Cases:

1. Fabricated citation.
2. Real citation, irrelevant to claim.
3. Real source supports weaker claim than the model says.
4. Contradicted claim.
5. Missing evidence / unverifiable.
6. Multi-model consensus from same contaminated source.
7. High-confidence but low-evidence recommendation.
8. Time-sensitive market/legal/policy claim requiring source freshness.
9. Long report with mixed valid and invalid claims.
10. Agent trace where tool result does not support final answer.

Outputs to compare:

- Fusion: synthesis, consensus, contradictions, unique viewpoints.
- AI Judge: claim-level status, evidence provenance, dissent, overclaim detection, human-final report gate.

Suggested deliverable:

- Blog/report: "Model routing plus audit layer: OpenRouter x AI Judge reliability benchmark."
- Public-safe dataset with 10-20 cases.
- Reproducible scripts if OpenRouter credits/API access are available.

## Follow-Up Sequence

Day 0:

- Submit enterprise/contact form with the main message.
- Join Discord and ask for the right contact, not a full pitch.

Day 3:

- If no answer, create support ticket asking where partnership/benchmark requests go.

Day 5-7:

- Send X/LinkedIn short note.

After response:

- Offer a 15-minute demo.
- Send a one-page comparison table.
- Ask for either (a) technical integration feedback, (b) benchmark credits, or (c) permission to submit Works with OpenRouter listing after integration.
