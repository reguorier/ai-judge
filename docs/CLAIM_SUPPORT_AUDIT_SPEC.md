# Claim Support Audit Spec

Status: frozen MVP contract as of 2026-05-19.

This document is the source-isolation contract for the Eval4SD fastlane and the
public citation-audit demo. Implementation details may improve, but the trust
boundary below should not be relaxed without a new benchmark row and a migration
note.

AI Judge now separates three questions that are often collapsed:

1. Did the cited source enter an isolated evidence layer?
2. Is the source relevant to the answer?
3. Does the source support the exact generated claim?

This matters because a real source is not the same as a proven conclusion. A source can say "A is associated with B" while the model writes "A caused B." That should not be marked as a trustworthy claim.

## Output Layers

| Layer | Question | Example output |
|---|---|---|
| Citation verification | Can the source be matched? | `citation_status=verified` |
| Source relevance | Is the source on-topic? | `source_relevance=relevant` |
| Claim support | Does the source prove the claim span? | `claim_support=unsupported` |
| Claim-source verdict | What RAG-eval artifact should be aggregated? | `support_verdict=unsupported_by_cited_source` |

The key design choice is that these statuses can disagree without overwriting each other.

## First-Class RAG Eval Contract

AI Judge now exposes a stricter per-claim, per-source verdict contract:

| `support_verdict` | Meaning |
|---|---|
| `supported` | The cited or matched source span supports the concrete generated claim. |
| `contradicted` | The source explicitly refutes the generated claim. |
| `not_enough_evidence` | The system lacks a matched source span or enough isolated evidence to judge support. |
| `unsupported_by_cited_source` | The source exists and may be relevant, but it does not support this exact claim. |

This is not a replacement for retrieval relevance or coarse faithfulness. It is
the stricter citation-level layer that catches local failures: association
becoming causation, scoped populations becoming universal claims, ranges being
reported as exact values, and hedged findings becoming certain recommendations.

## Frozen Trust Boundary

The MVP must preserve these invariants:

| Invariant | Required behavior |
|---|---|
| Raw-answer preservation | The system may quote or score the submitted answer, but must not rewrite it into the final truth source. |
| Source isolation | Model-mentioned citations are candidates until matched against external evidence. |
| Claim-support separation | Citation status, source relevance, and exact claim support can disagree. |
| Unverifiable semantics | `unverifiable` means insufficient isolated evidence, not false. |
| Human-final verdict | The judge summarizes, scores, and records; it does not become an authority that certifies reality by itself. |
| Replayability | Reports must include deterministic IDs, reason codes, and replay-ledger hashes where available. |

## MVP Rules

The implemented deterministic MVP catches three high-signal overclaim families:

```text
claim span contains causal language
+ matched source contains association/correlation language
+ source disclaims or does not establish causation
= support_failure_code: overclaimed_causation
= claim_support: unsupported

claim span contains absolute language
+ matched source is limited, partial, sampled, or caveated
= support_failure_code: overclaimed_absolute
= claim_support: unsupported

claim span states a larger percentage effect than the matched source
+ claim percentage exceeds source percentage by more than 5 points
= support_failure_code: overclaimed_quantified_effect
= claim_support: unsupported

claim span applies a source scoped to adults/subsets to all patients/users
= support_failure_code: overclaimed_scope
= claim_support: unsupported
= support_verdict: unsupported_by_cited_source

claim span removes a hedge such as "may reduce" and states "reduces"
= support_failure_code: overclaimed_hedge
= claim_support: unsupported
= support_verdict: unsupported_by_cited_source

claim span reports one endpoint of a source range as a precise value
= support_failure_code: overclaimed_range_endpoint
= claim_support: unsupported
= support_verdict: unsupported_by_cited_source
```

Example:

```json
{
  "claim_span": "The AI review program caused a 22% reduction in churn.",
  "citation_status": "verified",
  "source_relevance": "relevant",
  "claim_support": "unsupported",
  "support_verdict": "unsupported_by_cited_source",
  "support_failure_code": "overclaimed_causation",
  "claim_support_pass_rate": 0.0,
  "retrieved2response": "non_entailment"
}
```

## Why This Solves The Hard Boundary

The original citation can stay `verified` because the URL/source really matched. The source can stay `relevant` because it discusses the same topic. The exact claim can still be `unsupported` because the model upgraded association into causation.

`contradicted` is reserved for evidence that explicitly refutes the claim or citation, such as externally supplied evidence marked `contradicts=true`. For RAGChecker-style aggregate faithfulness, both `unsupported` and `contradicted` reduce to `retrieved2response=non_entailment`, while AI Judge keeps the richer audit status for debugging.

For regression tracking, use `claim_support_pass_rate` and
`support_verdict_counts` next to retrieval relevance and faithfulness. Keep the
per-claim audit items for debugging; a single aggregate score is not enough to
explain which claim failed and why.

That prevents the Grand Judge from using hallucinated or overclaimed reasoning to verify another hallucination. The judge remains a summarizer, statistician, and scorer, not a rewriting authority.

## Roadmap

| Phase | Scope | Product value |
|---|---|---|
| 1 | Deterministic high-risk patterns: causation, absolutes, quantified claims. | Catch obvious "real source, wrong conclusion" failures. |
| 2 | Claim-span extraction across compound paragraphs. | Audit one citation that supports one clause but not another. |
| 3 | Source-support matrix: each claim span against each cited source. | Legal/research memo audit with precise support gaps. |
| 4 | Blind model review only after source isolation. | Models can critique claim support but cannot self-certify sources. |
| 5 | Attested report payloads. | Replay Ledger hash + claim-support hash can enter Ligate/Aequis-style provenance infrastructure. |

## Non-Goals

- Do not rewrite the answer.
- Do not treat `unverifiable` as false.
- Do not let the model's own citation become proof.
- Do not merge raw answer, mentor supplement, and external evidence into one blob.
