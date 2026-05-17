# Sample AI Decision Audit Report

Case: `examples/product-no-evidence.md`

## Executive summary

The submitted product recommendation argues for a three-month rewrite and claims large reliability gains, but the cited evidence does not independently verify the defect-reduction claim.

AI Judge Citation Audit labels the key citation as:

```text
unverifiable
```

This is not a claim that the recommendation is false. It means the current isolated evidence is insufficient for a publishable decision memo.

## Audit result

| Field | Value |
|---|---|
| Input | `examples/product-no-evidence.md` |
| HTML report | `reports/product-no-evidence-audit.html` |
| JSON report | `reports/product-no-evidence-audit.json` |
| Trust gate | `needs_more_evidence` |
| Required action | Add external source, experiment result, customer support data, or rollback evidence. |

## Decision risk

The recommendation has three separate risks:

1. The cited source is a model-mentioned candidate source, not isolated evidence.
2. The claim is quantitative enough to influence roadmap scope.
3. The proposed rewrite cost is high relative to the evidence supplied.

## What a paid audit would add

- Batch audit across all supporting docs.
- Evidence Broker fetch mode for cited URLs.
- Replay Ledger history across revisions.
- Reviewer packet for decision owners.
- Certification report export for stakeholders.

## Safe next step

Do not approve the rewrite from this memo alone. Ask for one of:

- defect trend data
- incident postmortems
- customer complaint sample
- experiment or benchmark result
- source document that directly supports the expected reduction
