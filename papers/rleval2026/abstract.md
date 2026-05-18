# RLEval 2026 Abstract Variant

Status: draft, not submitted
Target route: https://rl-eval.github.io/
Contact route: `rl-eval@googlegroups.com`
Last refreshed: 2026-05-19

## Working Title

```text
A Source-Isolated Trust Gate for Agentic LLM Outputs
```

## Position

Agentic systems increasingly produce answers, reports, and decisions that cite
external evidence. Evaluation often scores the final answer or the agent trace,
but a smaller trust boundary is needed before the output is reused: does the
cited source exist, is it relevant, and does it support the exact claim span?

## Draft Abstract

```text
Agentic LLM systems increasingly produce source-heavy outputs that are reused in
reports, memos, and downstream decision workflows. Existing evaluation pipelines
often collapse several distinct states into a single correctness or faithfulness
score: a cited source may exist, it may be topically relevant, and yet it may not
support the exact claim made by the agent. We propose a source-isolated trust
gate for agentic LLM outputs. The protocol preserves three layers separately:
the raw agent answer, independently collected external evidence, and audit
verdict metadata. It reports citation existence, source relevance, and exact
claim support as separate fields, then emits replay-ledger and certification
hashes for downstream review. We instantiate the protocol in AI Judge Citation
Audit, a local-first system with deterministic JSON and HTML reports. A 100-case
deterministic benchmark plus 13 hard cases demonstrates failure modes where a
real source is irrelevant, contradicted, unverifiable, or overclaimed by the
agent. We argue that agent evaluation should include this smaller trust gate
before treating source-heavy outputs as decision-ready.
```

## Fit Rationale

- RLEval is a better route if the paper is framed as agent-output evaluation
  methodology rather than only citation checking.
- AI Judge contributes a reproducible trust gate that can sit before broader
  reward, benchmark, or human-review stages.
- The hard case maps well to agent evaluation: a retrieved or cited source can
  be real while the agent conclusion still overclaims it.

## Next Action

Prepare the OpenReview packet if the account recovers, or send the fit-check
draft from `growth/submission_council_2026.md` after action-time confirmation.
