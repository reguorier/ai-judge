# SeT-LLM 2026 Abstract Variant

Status: draft, not submitted
Target route: https://openreview.net/group?id=KDD.org/2026/Workshop/SeT_LLM
Contact route: OpenReview route only; no verified public email in this pass
Last refreshed: 2026-05-19

## Working Title

```text
Source Isolation as a Trust Boundary for LLM-Generated Evidence
```

## Draft Abstract

```text
Trustworthy LLM systems require more than plausible citations or a coherent
chain of reasoning. When a model-generated answer names a source, downstream
systems can accidentally use the model's own text as evidence for that source,
creating a self-verification loop. We define source isolation as a trust
boundary for LLM-generated evidence. The protocol separates the raw model
answer, independently collected external evidence, and audit verdict metadata.
It then evaluates citation existence, source relevance, and exact claim support
as separate states. AI Judge Citation Audit implements this protocol as a
local-first audit layer that emits HTML reports, deterministic JSON,
certification IDs, replay-ledger hashes, and support-failure codes. The key
security failure is not only fabricated evidence, but provenance poisoning:
real or plausible sources are treated as supporting claims they do not support.
We demonstrate the protocol on deterministic and hard-case benchmarks covering
unverifiable sources, irrelevant sources, contradicted claims, and real-source
overclaims.
```

## Fit Rationale

- The security/trust framing is "do not let model text verify model text."
- Source isolation becomes a concrete trust boundary for LLM evidence handling.
- The replay ledger and certification hash give this route more than an essay:
  there is a reproducible artifact.

## Next Action

Use this if OpenReview access recovers before the SeT-LLM window. Otherwise keep
it as a reusable security/trust abstract for the next CFP.
