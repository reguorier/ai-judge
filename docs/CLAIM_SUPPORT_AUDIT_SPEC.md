# Claim Support Audit Spec

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
| Claim support | Does the source prove the claim span? | `claim_support=contradicted` |

The key design choice is that these statuses can disagree without overwriting each other.

## MVP Rules

The implemented deterministic MVP catches three high-signal overclaim families:

```text
claim span contains causal language
+ matched source contains association/correlation language
+ source disclaims or does not establish causation
= support_failure_code: overclaimed_causation

claim span contains absolute language
+ matched source is limited, partial, sampled, or caveated
= support_failure_code: overclaimed_absolute

claim span states a larger percentage effect than the matched source
+ claim percentage exceeds source percentage by more than 5 points
= support_failure_code: overclaimed_quantified_effect
```

Example:

```json
{
  "claim_span": "The AI review program caused a 22% reduction in churn.",
  "citation_status": "verified",
  "source_relevance": "relevant",
  "claim_support": "contradicted",
  "support_failure_code": "overclaimed_causation"
}
```

## Why This Solves The Hard Boundary

The original citation can stay `verified` because the URL/source really matched. The source can stay `relevant` because it discusses the same topic. The exact claim can still be `contradicted` because the model upgraded association into causation.

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
