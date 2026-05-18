# Resonance Wave 003 - Eval4SD, Taxonomy Exchange, and Trust Infrastructure

Status: prepared, not_sent
Created: 2026-05-18

This wave is research-first and infrastructure-first. It is not a commercial ad campaign.

Core thesis:

```text
A real citation only proves that a source exists and can be matched. It does not prove that the model's conclusion follows from that source.
```

AI Judge's next public wedge is the `claim-span + source` audit layer: citation verification, source relevance, and exact claim support are reported separately.

## Send Rules

- Do not send or submit anything from this file without action-time confirmation.
- Lead with taxonomy exchange, benchmark cases, or minimal integration.
- Keep third-party private replies out of public GitHub unless anonymized permission is explicit.
- Preserve source isolation: raw answer, mentor supplement, and external evidence remain separate.

## Priority Queue

| ID | Priority | Target | Route | Asset | Status |
|---|---:|---|---|---|---|
| W003-001 | P0 | Eval4SD 2026 | Workshop submission | `docs/EVAL4SD_2026_SOURCE_ISOLATED_CITATION_AUDIT_DRAFT.md` | draft_ready |
| W003-002 | P0 | HalluCiteChecker | Research taxonomy exchange | Email draft below | ready_for_confirmation |
| W003-003 | P0 | LegalCiteBench | Legal citation taxonomy exchange | Email draft below | needs_contact |
| W003-004 | P1 | Aequis | Legal AI provenance / benchmark collaboration | Email draft below | ready_for_confirmation |
| W003-005 | P1 | Ligate | Attestation payload integration | Email draft below | ready_for_confirmation |

## Technical Anchor

Implemented asset:

```text
core/claim_support.py
```

Report fields:

```text
claim_support_audit.items[].citation_status
claim_support_audit.items[].source_relevance
claim_support_audit.items[].claim_support
claim_support_audit.items[].support_failure_code
claim_support_audit.claim_support_hash
```

Hard benchmark behavior:

```text
The source can be verified and relevant while the claim is contradicted:

citation_status = verified
source_relevance = relevant
claim_support = contradicted
support_failure_code = overclaimed_causation
```

## W003-001 - Eval4SD Submission Plan

Immediate next action:

1. Convert the current draft into a 4-page short/position paper.
2. Add a compact method figure: Raw Answer -> Evidence Broker -> Citation Verification -> Claim Support Audit -> Replay Ledger.
3. Add one table for `citation-bench-100`, one table for `citation-bench-hard-11`, and one row for overclaimed causation.
4. Submit only after action-time confirmation.

Working title:

```text
Source-Isolated Citation and Claim-Support Audit for LLM Outputs in Specialized Domains
```

## W003-002 - HalluCiteChecker Taxonomy Exchange

Subject:

```text
Taxonomy exchange: citation hallucination vs claim-support failure
```

Body:

```text
Hi HalluCiteChecker team,

I saw your HalluCiteChecker work on detecting and verifying hallucinated citations in AI-generated scientific writing. I am building a complementary source-isolated audit tool, AI Judge Citation Audit, that focuses on AI-generated answers and reports.

The overlap is citation reliability. The distinction I am trying to make explicit is:

1. citation_status: does the source exist and match isolated evidence?
2. source_relevance: is the source related to the generated claim?
3. claim_support: does the source support the exact claim span?

The hard case is a real and relevant source that reports association while the model states causation. AI Judge now emits `citation_status=verified`, `source_relevance=relevant`, but `claim_support=contradicted` with `support_failure_code=overclaimed_causation`.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Spec: https://github.com/reguorier/ai-judge/blob/main/docs/CLAIM_SUPPORT_AUDIT_SPEC.md

Would you be open to comparing taxonomies or exchanging one hard benchmark case? I am especially interested in cases that pass bibliographic checks but fail exact claim support.

Best,
Reguorier
```

## W003-003 - LegalCiteBench Taxonomy Exchange

Subject:

```text
Mapping LegalCiteBench failures to source-isolated claim support?
```

Body:

```text
Hi LegalCiteBench team,

I read your LegalCiteBench abstract and the focus on citation recovery, citation verification, case matching, and correction in legal LLMs is very close to a narrow tool I am building: AI Judge Citation Audit.

AI Judge is not trying to replace a legal benchmark. It is a local audit report that preserves raw model answers, isolated external evidence, and audit verdicts separately. The newest layer separates source matching from exact claim support:

- citation_status: verified / weakly_verified / irrelevant / unverifiable / contradicted
- source_relevance: relevant / weakly_relevant / irrelevant / unknown
- claim_support: supported / partially_supported / unsupported / contradicted / unknown

The motivating case is where a real authority is cited, but the generated legal proposition overstates what the authority supports.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Spec: https://github.com/reguorier/ai-judge/blob/main/docs/CLAIM_SUPPORT_AUDIT_SPEC.md

Would you be open to a quick taxonomy comparison? I am trying to map AI Judge's support-failure codes to legal citation failure modes, especially real-citation / wrong-proposition cases.

Best,
Reguorier
```

## W003-004 - Aequis Collaboration

Subject:

```text
Claim-span/source audit for legal AI provenance benchmarks?
```

Body:

```text
Hi Aequis team,

I saw that Aequis is building legal AI research infrastructure around benchmarks, datasets, provenance, jurisdiction, and time. I am building a small complementary tool called AI Judge Citation Audit.

The narrow problem it targets is the gap between a real citation and a supported legal/research claim. A source can be valid and relevant while the AI-generated proposition overclaims it. AI Judge now reports citation verification, source relevance, and claim support separately.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Spec: https://github.com/reguorier/ai-judge/blob/main/docs/CLAIM_SUPPORT_AUDIT_SPEC.md

Would a minimal collaboration make sense around one England & Wales-style benchmark case where the source exists but the generated claim fails support? I am looking for a concrete taxonomy/protocol exchange first, not a large integration.

Best,
Reguorier
```

## W003-005 - Ligate Integration

Subject:

```text
AI citation audit hash as a pre-attestation trust gate?
```

Body:

```text
Hi Ligate team,

I am building AI Judge Citation Audit, a source-available tool that audits AI-generated citations and claim support before an answer is reused in reports, memos, or governance logs.

My read of Ligate/Themisra/Iris is that your stack answers: can this prompt, output, or agent action be witnessed and replayed? AI Judge answers a prior question: should this cited answer enter a witness chain as supported, unverifiable, or contradicted?

The latest AI Judge report emits:

- Certification ID
- Replay Ledger hash
- citation status counts
- evidence provenance counts
- claim-support hash
- support failure codes such as `overclaimed_causation`

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Spec: https://github.com/reguorier/ai-judge/blob/main/docs/CLAIM_SUPPORT_AUDIT_SPEC.md

Would a minimal integration make sense where AI Judge produces a pre-attestation payload for `themisra.proof-of-prompt/v1` or an adjacent receipt schema?

Best,
Reguorier
```

## Next Automatable Step

Generate `.eml` drafts for W003-002, W003-004, and W003-005, then ask for action-time confirmation before sending. For W003-003, first find a reliable public contact route or wait until the authors publish one.
