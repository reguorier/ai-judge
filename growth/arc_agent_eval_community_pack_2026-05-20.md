# ARC / Agent Eval Community Pack

Goal: enter the ARC / agent evaluation conversation as an evaluator and trace-audit layer, not as a solver.

## Positioning

AI Judge should not claim it will win ARC-AGI-3 as a solver. The credible angle is:

> AI Judge evaluates agent attempts: exploration traces, evidence for actions, model disagreement, and human-readable failure modes.

## ARC Entry Path

| Item | Action |
|---|---|
| Official competition | Recheck https://arcprize.org/competitions/2026/arc-agi-3 |
| Technical docs | Recheck https://docs.arcprize.org/ |
| First contribution | Build a small "agent trace verdict" demo on a public ARC-style task |
| Community ask | Ask whether evaluator tooling is useful to teams comparing agents |
| GitHub angle | Publish `examples/agent-trace-verdict.md` and link from README |

## Minimum Evaluator Demo

Input:

- Agent attempt log
- Actions taken
- Observations
- Final answer / task result

AI Judge output:

- Exploration quality
- Evidence for chosen action
- Missed alternatives
- Model-seat disagreement
- Human-readable verdict

## Outreach Message To ARC Community

Hi [Name], I am building AI Judge, an open-source multi-model jury for auditing AI outputs. For ARC-AGI-3, I am not trying to pitch it as a solver. I am testing whether it can help evaluate agent attempts: exploration traces, action justification, missed alternatives, and evidence-backed failure modes. Would evaluator tooling like this be useful to ARC teams, or is the community focused only on solver submissions right now?

## Agent Eval Targets

| Community | Why | First Ask |
|---|---|---|
| ARC Prize | Frontier agent evaluation | "Would trace judging help teams compare attempts?" |
| LangChain | Agent workflow ecosystem | "Should agent outputs carry an audit verdict?" |
| LlamaIndex | RAG/citation workflows | "Can claim-source audit plug into RAG eval?" |
| AutoGen | Multi-agent debate | "Can AI Judge score multi-agent discussions?" |
| Hugging Face | Demo and benchmark distribution | "Try the Space and submit hard cases." |
| Papers with Code | Later benchmark discoverability | "Index once benchmark/paper is stable." |

## 72-Hour ARC Tasks

| Task | Output | Status |
|---|---|---|
| Write evaluator memo | This file | Done |
| Create agent trace example | `examples/agent-trace-verdict.md` | Done |
| Create executable trace fixture | `examples/agent-trace-demo.json`, `examples/agent-trace-supported.json`, `examples/agent-trace-partial.json` | Done |
| Create report renderer | `tools/render_agent_trace_report.py` | Done |
| Create ARC community post | Draft above | Ready |
| Add README sentence | Top positioning updated | Done |
| Identify 5 ARC contacts | in outreach CSV | Done |

## What Not To Claim

- Do not claim AI Judge solves ARC-AGI-3.
- Do not claim official ARC partnership.
- Do not claim full benchmark validity without a reproducible trace dataset.

## Best Claim

AI Judge can make agent failures inspectable. That is useful even before it becomes a benchmark scorer.
