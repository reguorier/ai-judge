# Eval4SD 2026 Draft

Working title:

```text
Source-Isolated Citation Audit for LLM Outputs in Specialized Domains
```

Submission target:

```text
Eval4SD 2026 Short / Position Paper
Deadline: 2026-07-03
```

## Abstract

Large language models increasingly produce source-heavy outputs in legal, medical, financial, and scientific workflows. In these domains, citation errors are not merely factual mistakes; they can become publication, compliance, and professional-risk events. We propose source-isolated citation audit: a lightweight protocol that keeps a model's raw answer, external evidence, and audit verdict separate. The protocol prevents model-mentioned sources from verifying themselves, labels each citation as `verified`, `weakly_verified`, `irrelevant`, `unverifiable`, or `contradicted`, and adds reason codes for unverifiable cases plus provenance grades for evidence. We instantiate the protocol in AI Judge Citation Audit, a local-first tool that emits human-readable HTML reports, automation-friendly JSON, Certification IDs, and Replay Ledger hashes. A deterministic benchmark shows how the protocol handles fabricated sources, real-but-irrelevant sources, contradicted claims, missing evidence, and a hard case where a real source reports correlation while the model claims causation. We argue that citation-level audit is a useful minimum viable boundary, but specialized-domain workflows ultimately require the smaller audit atom of `claim-span + source`.

## 1. Motivation

LLM evaluation often collapses several distinct questions:

1. Does the source exist?
2. Is the source related to the topic?
3. Does the source support the exact generated claim?
4. Was the evidence independently fetched, user-supplied, attested, or merely mentioned by the model?
5. Should the answer be allowed into a report, memo, audit trail, or compliance record?

In specialized domains, collapsing these questions creates avoidable risk. A citation can be real and on-topic while still failing to support the model's claim. The most compact example is correlation versus causation: the cited source may report an association and explicitly disclaim causality, while the model states that the source proves a causal effect. Calling that source "verified" overstates trust; calling it "irrelevant" hides that it was still highly related. The audit output needs to separate source relevance, claim support, and evidence provenance.

## 2. Source-Isolated Citation Audit

The central rule is:

```text
A model-mentioned source is a candidate, not evidence.
```

AI Judge separates the audit into three layers:

| Layer | Description |
|---|---|
| Raw answer | The original model output. It is preserved and not rewritten by the judge. |
| External evidence | User-supplied, fetched, attested, or notarized evidence objects. |
| Audit verdict | Citation labels, reason codes, provenance counts, Certification ID, and Replay Ledger hash. |

This design avoids using a second model to certify the first model's hallucination. It also makes failed evidence retrieval different from contradiction.

## 3. Labels

| Label | Meaning |
|---|---|
| `verified` | Strong external evidence match and relevant to the answer. |
| `weakly_verified` | Partial or implied support, or insufficient anchor precision for high confidence. |
| `irrelevant` | Source exists, but does not support the cited claim or context. |
| `unverifiable` | Current isolated evidence is insufficient; this is not the same as false. |
| `contradicted` | External evidence explicitly refutes the citation or related claim. |

## 4. Unverifiable Reason Codes

`unverifiable` is intentionally broad at the user-facing level, but the system records why the audit could not verify the citation:

| Reason code | Meaning |
|---|---|
| `no_citation` | The answer did not provide a checkable citation. |
| `missing_external_evidence` | No isolated evidence matched the citation. |
| `candidate_not_fetched` | The source was only mentioned by the model and has not been independently fetched or supplied. |
| `fetch_error` | Retrieval failed; this is not proof that the source is fake. |
| `retrieval_blocked` | Access was blocked or permission-gated. |
| `weak_match` | Some evidence matched, but not strongly enough to verify the citation. |

## 5. Evidence Provenance

Evidence provenance is a first-class part of the audit:

| Provenance | Meaning |
|---|---|
| `model_candidate` | A source mentioned by the model. It cannot verify itself. |
| `user_supplied` | Evidence supplied by a user or external workflow. |
| `fetched` | Evidence fetched by the Evidence Broker from the cited URL. |
| `independently_attested` | Evidence with an external attestation or witness ID. |
| `notarized` | Evidence tied to a witness hash, ledger hash, or notarized record. |

## 6. Implementation

AI Judge Citation Audit is implemented as a local-first Python CLI plus a Hugging Face Space demo. It does not require model APIs for the deterministic citation audit path.

Outputs:

- HTML report
- JSON report
- Certification ID
- Replay Ledger hash
- Citation status counts
- Claim-support status counts
- Source-relevance counts
- Support-failure reason codes
- Unverifiable reason counts
- Evidence provenance counts

The current implementation includes a deterministic claim-support audit block for a narrow but important failure family: a real and relevant source that reports association while the model states causation. In that case, AI Judge can emit `citation_status=verified`, `source_relevance=relevant`, and `claim_support=contradicted` with `support_failure_code=overclaimed_causation`.

The public demo is available at:

```text
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

The repository is:

```text
https://github.com/reguorier/ai-judge
```

## 7. Benchmark

The current deterministic benchmark has two layers:

| Benchmark | Scope |
|---|---|
| `citation-bench-100` | Broad deterministic cases across the five labels. |
| `citation-bench-hard-11` | Hard launch cases for public demos and regression checks. |

The hard set includes:

| Failure family | Example |
|---|---|
| Fabricated source | A plausible named report is not found in isolated evidence. |
| Real but irrelevant source | The URL exists, but the content supports a different topic. |
| Contradicted source | External evidence explicitly refutes the generated claim. |
| Missing / blocked / unfetched evidence | The correct next action is retry or evidence request, not declaring falsehood. |
| Real source, overclaimed support | The source reports correlation; the model claims causation. |

Current command:

```bash
PYTHONPATH=. python tools/run_citation_bench.py \
  --bench citation-bench/citation-bench-hard-11.jsonl \
  --fail-under 0.95
```

Recent result:

```text
11 / 11 passed
accuracy = 1.0
```

## 8. Why Specialized Domains Need Claim-Span + Source

Citation-level audit is the minimum viable product boundary. It is not enough for legal, medical, policy, or financial workflows.

A single citation can cover multiple claims:

- one clause is supported,
- another clause is silent,
- a third clause is contradicted.

The next audit atom should therefore be:

```text
claim-span + source
```

Example:

```json
{
  "claim_span": "The AI review program caused a 22% reduction in churn.",
  "source_id": "EVID-001",
  "citation_status": "verified",
  "source_relevance": "relevant",
  "claim_support": "contradicted",
  "support_failure_code": "overclaimed_causation",
  "support_reason": "The source reports association and explicitly disclaims causation."
}
```

This representation lets the source be real while the model's claim support fails.

## 9. Limitations

- The tool audits citation support, not complete factual truth.
- User-supplied evidence is useful but weaker than independently attested evidence.
- Deterministic matching can miss subtle semantic support failures without claim-span scoring.
- Network fetching creates reproducibility, access, and paywall issues.
- The current system is source-available under BSL 1.1, not OSI open source.

## 10. Planned Evaluation

For the Eval4SD submission, add:

1. Full benchmark table for `citation-bench-100`.
2. Hard benchmark table for `citation-bench-hard-11`.
3. One legal memo compound-claim case.
4. One scientific citation case inspired by hallucinated-paper verification.
5. Ablation: candidate-only source vs user-supplied evidence vs fetched evidence.

## 11. Related Work To Cite

- LegalCiteBench studies citation reliability in legal language models and includes citation retrieval, completion, error detection, case matching, verification, and correction.
- HalluCiteChecker studies hallucinated citation detection and verification in AI-generated scientific writing.
- LLMTrust 2026 frames trustworthy LLM systems around auditable use, evidence, metrics, provenance, and compliance.
- Eval4SD explicitly invites work on LLM benchmarking, domain research replication, and evaluation methodology in specialized domains.
- AEX provides a narrow attestation framing for request-output and output-lineage provenance at the LLM API boundary.
- LLM audit-trail work frames tamper-evident ledgers as sociotechnical accountability infrastructure.

## 12. One-Sentence Contribution

AI Judge shows that before an LLM answer enters a report, benchmark, or audit trail, its citations should be source-isolated, reason-coded, and provenance-labeled instead of being judged by another model alone.
