# Pre-Attestation Receipt Schema

AI Judge should sit before an attestation, notarization, or proof-of-prompt
system. Its job is not to notarize truth. Its job is to decide whether a cited
model answer is safe enough to enter a witness chain as `supported`,
`weakly_supported`, `unverifiable`, or `contradicted`.

This receipt schema is the minimal integration payload for provenance systems
such as Ligate/Themisra-style proof-of-prompt stacks, legal AI audit trails, or
future AgentFi certification assets.

## Boundary

AI Judge keeps three source layers separate:

| Layer | Stored as | Rule |
|---|---|---|
| Raw model answer | `raw_answer_hash` | Never rewritten by the judge. |
| Mentor supplement | `mentor_supplement_hash` | Advisory only; cannot verify itself. |
| External evidence | `source_layer_hash` | Only this layer can support or contradict claims. |

The receipt can be attested, but the attestation only proves that the audit ran
and produced this payload. It does not prove that every claim is true.

## Required Fields

| Field | Type | Description |
|---|---|---|
| `schema` | string | Fixed value: `ai_judge.pre_attestation_receipt.v1`. |
| `receipt_id` | string | Stable ID derived from the canonical receipt payload. |
| `run_id` | string | Product run ID or replay ID. |
| `certification_id` | string | Existing AI Judge certification ID, when available. |
| `created_at` | string | ISO-8601 timestamp. |
| `question_hash` | string | Hash of the user question or decision prompt. |
| `raw_answer_hash` | string | Hash of the original model answer bundle. |
| `mentor_supplement_hash` | string/null | Hash of mentor additions, if present. |
| `source_layer_hash` | string | Hash of isolated external evidence items. |
| `citation_audit_hash` | string | Hash of citation-level verification output. |
| `claim_support_hash` | string | Hash of claim-span/source support output. |
| `replay_ledger_hash` | string | Hash of the replay ledger. |
| `overall_verdict` | string | `supported`, `weakly_supported`, `unverifiable`, or `contradicted`. |
| `citation_counts` | object | Counts for `verified`, `weakly_verified`, `irrelevant`, `unverifiable`, and `contradicted`. |
| `claim_support_counts` | object | Counts for `supported`, `partially_supported`, `unsupported`, `contradicted`, and `unknown`. |
| `failure_codes` | array | Claim-support failure codes, such as `overclaimed_causation`. |
| `source_isolation` | object | Flags showing raw answer, mentor supplement, and external evidence were kept separate. |
| `attestation_policy` | object | What downstream attesters may and may not claim. |

## Example

```json
{
  "schema": "ai_judge.pre_attestation_receipt.v1",
  "receipt_id": "ajr_8b7f4e8c6d2a",
  "run_id": "59cc3e957bc6",
  "certification_id": "cert_20260519_001",
  "created_at": "2026-05-19T05:30:00Z",
  "question_hash": "sha256:...",
  "raw_answer_hash": "sha256:...",
  "mentor_supplement_hash": "sha256:...",
  "source_layer_hash": "sha256:...",
  "citation_audit_hash": "sha256:...",
  "claim_support_hash": "sha256:...",
  "replay_ledger_hash": "sha256:...",
  "overall_verdict": "unverifiable",
  "citation_counts": {
    "verified": 4,
    "weakly_verified": 2,
    "irrelevant": 1,
    "unverifiable": 3,
    "contradicted": 1
  },
  "claim_support_counts": {
    "supported": 3,
    "partially_supported": 2,
    "unsupported": 2,
    "contradicted": 1,
    "unknown": 3
  },
  "failure_codes": [
    "overclaimed_causation",
    "missing_claim_evidence"
  ],
  "source_isolation": {
    "raw_answer_preserved": true,
    "mentor_supplement_separate": true,
    "external_evidence_separate": true,
    "judge_rewrote_answer": false
  },
  "attestation_policy": {
    "may_attest": [
      "audit execution",
      "input and output hashes",
      "source-isolated verdict",
      "replay ledger identity"
    ],
    "must_not_claim": [
      "the model answer is true",
      "unverifiable means false",
      "mentor supplement is external proof"
    ]
  }
}
```

## Verdict Mapping

| Inputs | Receipt verdict |
|---|---|
| All critical citations verified and all critical claim spans supported. | `supported` |
| Mixed verified and weakly verified citations, with no contradictions. | `weakly_supported` |
| Missing external evidence for critical claims. | `unverifiable` |
| Any critical source contradicts the claim or catches an overclaim. | `contradicted` |

When in doubt, downgrade to `unverifiable`. This is a routing signal for human
review or evidence gathering, not an accusation of falsehood.

## Downstream Integration Contract

A downstream attestation layer can store the receipt and sign its hashes:

1. AI Judge preserves the raw answer, mentor supplement, and external evidence
   as separate payloads.
2. AI Judge produces citation verification and claim-support hashes.
3. AI Judge emits the pre-attestation receipt.
4. The provenance system signs the receipt hash and stores replay metadata.
5. Any later verifier can replay the audit from the isolated layers and compare
   the receipt hash.

This keeps the Grand Judge role narrow: summarize, count, score, and route. It
does not let a model use its own fluent answer as evidence.
