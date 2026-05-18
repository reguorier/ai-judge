# Claim-Span Roadmap

Citation-level audit is the MVP. It answers a useful first question:

> Does the cited source exist in an isolated evidence layer, and does it support the answer well enough to publish?

Legal, policy, and audit workflows need a smaller atom:

> claim-span + source

## Why citation-level is not enough

One citation can cover several claims:

- a source verifies one clause,
- is silent on a second clause,
- and contradicts a third clause.

A single citation verdict cannot represent that cleanly. A real and relevant source can still fail to support the model's exact claim. The hard benchmark includes this boundary: a source reports correlation, while the generated answer claims causation.

## Target data model

```json
{
  "claim_span": "The AI review program caused a 22% reduction in churn.",
  "source_id": "EVID-001",
  "support_status": "contradicted",
  "support_reason": "The source reports association and explicitly disclaims causation.",
  "citation_status": "verified",
  "source_provenance": "fetched"
}
```

The source can be verified while the claim support is contradicted. AI Judge should keep those two facts separate.

## Planned stages

1. Keep citation-level verification as the stable public MVP.
2. Add claim-span extraction for source-heavy answers.
3. Score each claim-span against each cited source.
4. Show a two-layer report: citation health and claim support.
5. Expose the claim-span report to batch audit, CI, and governance-ledger workflows.

## Non-goal

AI Judge should not rewrite the answer to make the claim safe. It should preserve the raw answer, label the support failure, and let the human or upstream author decide what to change.
