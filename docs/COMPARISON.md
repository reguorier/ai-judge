# AI Judge v2 Comparison

AI Judge is not trying to be another answer synthesizer. It is a local-first, human-final evidence workflow with an auditable scoring engine.

## Snapshot

| System | Primary job | Model count | Final owner | Evidence model | Local-first | AI Judge v2 difference |
|---|---|---:|---|---|:---:|---|
| Hermes-compatible skill | Package and replay an agent workflow | N/A | User/host agent | `SKILL.md` procedure | Yes | AI Judge adds a full jury workflow, claim ledger, and scoring engine |
| llm-council | Multi-LLM peer review and chairman synthesis | Configurable | Chairman LLM | Anonymous ranking and peer review | No, API/gateway path | AI Judge keeps the final call human and exposes claim-level scores |
| Perplexity Model Council | Web research with a synthesized answer | 3 | Perplexity synthesizer | Agreement/disagreement summary | No, web product | AI Judge is CLI/Docker/skill packaged and exposes formulas |
| AI Judge v2 | Human-centric verdict workflow | 9 seats | Human | Gates, weights, risk flags, diversity, graph value | Yes | The whole stack is built for inspection |

Sources: [Hermes skills](https://hermes-agent.ai/blog/hermes-agent-skills-guide), [llm-council](https://llm-council.dev/), [Perplexity Model Council](https://www.perplexity.ai/help-center/zh-CN/articles/13641704-%E4%BB%80%E4%B9%88%E6%98%AF-model-council).

## What Changed in v2

| Area | v1 style | v2 style |
|---|---|---|
| Claim score | Multiply five broad dimensions | `allocation_score` with explicit weights |
| Bad claims | Low score after aggregation | `evaluate_bluff_ev` can reject early |
| Abstention | Forced participation | `should_bid` lets weak seats abstain |
| Calibration | Informal confidence read | `log_score` and `brier_score` |
| Seat value | Reliability history | `graph_value_v2`, correctness first |
| Diversity | Agreement count | Variance, clusters, and diversity health |
| Final influence | Broad averaging | `peach_projection(k=2)` scarcity allocation |

## When to Use Which

| Scenario | Better fit |
|---|---|
| You want a quick synthesized answer from multiple APIs | llm-council or Perplexity Model Council |
| You want a reusable agent procedure package | Hermes-compatible skill |
| You need a local-first audit trail for a consequential decision | AI Judge |
| You need claim-level scoring formulas you can inspect | AI Judge v2 |
| You want the model to decide for you | Not AI Judge |

## Human-Final Philosophy

AI Judge deliberately refuses to make the final decision. The machine can gather evidence, flag bluff risk, estimate diversity, and allocate weights. The human still reads the verdict and decides.
