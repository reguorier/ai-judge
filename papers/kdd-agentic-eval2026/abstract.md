# KDD Agentic AI Evaluation Abstract Variant

Status: draft, not submitted
Target route: https://openreview.net/group?id=KDD.org/2026/Workshop/Agentic_AI_Evaluation_and_Trustworthiness
Contact route: OpenReview route only in this pass
Last refreshed: 2026-05-19

## Working Title

```text
Replayable Evidence Audits for Agentic AI Evaluation
```

## Draft Abstract

```text
Agentic AI evaluation increasingly needs to inspect not only whether an answer
looks correct, but whether the evidence trail behind that answer can be replayed
and audited. We present AI Judge Citation Audit, a source-isolated audit layer
for agent-generated outputs. The system keeps raw answer text, external
evidence, and audit verdict metadata separate, preventing agent text from
serving as evidence for itself. It reports citation existence, source relevance,
and exact claim support independently, then emits certification IDs,
replay-ledger hashes, and claim-support hashes for downstream verification. A
deterministic benchmark and hard-case suite show how agent outputs can cite real
sources while still making unsupported, contradicted, or overclaimed
conclusions. We argue that replayable evidence audit should be treated as a
precondition for trusting source-heavy agent outputs in research, legal,
financial, and governance workflows.
```

## Fit Rationale

- This route is strongest if AI Judge is framed as evaluation infrastructure
  for agents rather than a standalone citation checker.
- Replay ledger, certification ID, and claim-support hash are concrete artifact
  hooks for trustworthiness.

## Next Action

Recheck the OpenReview deadline and requirements, then expand this into a
short system/demo note if the route is still open.
