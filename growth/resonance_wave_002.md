# Resonance Wave 002 - Governance, Citation Reliability, and Evidence Provenance

Status: prepared, not_sent
Created: 2026-05-18

This wave is designed to find people who already care about the same boundary Article 11 surfaced:

> A source can be real and relevant without verifying the model's claim.

The ask is not "please promote AI Judge." The ask is: compare failure taxonomies, contribute one hard benchmark case, review the claim-span roadmap, or explore where citation gating should sit before audit trails and attestation layers.

## Send Rules

- Do not send any message from this file without action-time confirmation.
- Lead with the recipient's problem, not AI Judge's feature list.
- Use "source-available under BSL 1.1" unless talking about a subcomponent that is actually OSI-open-source.
- Keep source isolation explicit: raw model answer, isolated external evidence, and audit output remain separate.
- For public forums, reply only where the thread already asks about hallucination, legal AI reliability, provenance, or evaluation methodology.

## Priority Queue

| ID | Priority | Path | Target | Source | Why this fits | First ask | Status |
|---|---:|---|---|---|---|---|---|
| R001 | P0 | Paper / workshop | Eval4SD 2026 | https://eval4sd.github.io/cfp/ | Active CFP for evaluating LLMs in specialized domains; law and evaluation methodology are in scope. | Prepare a short/position paper on source-isolated citation audit and claim-span/source scoring. | draft_paper |
| R002 | P0 | Research peer | LegalCiteBench | https://arxiv.org/abs/2605.10186 | New legal citation reliability benchmark with citation verification, case matching, and correction tasks. | Ask whether AI Judge's source-isolated audit report can map to LegalCiteBench failure categories. | needs_contact |
| R003 | P0 | Research peer | HalluCiteChecker | https://arxiv.org/abs/2604.26835 | Lightweight hallucinated citation detection toolkit for AI-generated scientific writing. | Ask for taxonomy comparison: paper-citation verification vs AI-answer citation audit. | contact_found |
| R004 | P0 | Governance / audit trail | LLMTrust 2026 organizers | https://llmtrust2026.github.io/call-for-papers/ | Workshop explicitly asks for auditable LLM use, evidence, metrics, provenance, and compliance. | Ask whether citation gating before audit trails is useful as a demo artifact or post-workshop note. | needs_contact |
| R005 | P1 | Legal AI infrastructure | Aequis | https://aequis.io/ | Builds legal AI research infrastructure around provenance, jurisdiction, time, and verification. | Ask if AI Judge's claim-span roadmap fits their provenance/citation benchmark layer. | needs_channel |
| R006 | P1 | Attestation infrastructure | Ligate / Themisra / Iris | https://ligate.io/ | Proof-of-prompt and agent attestation stack; AI Judge can be a pre-attestation trust gate. | Ask about a minimal integration: AI Judge audit hash as a receipt payload before attestation. | needs_channel |
| R007 | P1 | Provenance protocol | AEX paper | https://arxiv.org/abs/2603.14283 | AEX separates request-output attestation from transformed-output lineage. | Ask whether AI Judge's Replay Ledger and evidence provenance can align with AEX-style request-output receipts. | needs_contact |
| R008 | P1 | Audit-trail research | Audit Trails for LLMs | https://arxiv.org/abs/2601.20727 | Work frames tamper-evident LLM audit trails and governance records. | Ask if source-isolated citation gates should be one event type before an output enters an audit trail. | needs_contact |
| R009 | P1 | Evaluation workshop | GEM at ACL 2026 | https://gem-workshop.com/ | GEM focuses on evaluation, metrics, human-in-the-loop evaluation, and living benchmarks. | Use as paper positioning reference; deadlines are mostly past, so do not treat as immediate submission. | reference_only |
| R010 | P1 | Agent failure workshop | FAGEN at ICML 2026 | https://fagen-workshop.github.io/ | Trace diagnostics and reproducible failure triggers match AI Judge's replay-ledger framing. | Use as future venue / community reference; current submission deadline has passed. | reference_only |
| R011 | P1 | Public discussion | Reddit legaltech / RAG threads | https://www.reddit.com/r/legaltech/ and https://www.reddit.com/r/Rag/ | Recent threads ask how teams verify AI-assisted legal/compliance research. | Prepare one non-promotional reply asking for hard benchmark cases. | needs_confirmation |

## Paper Path

Best immediate submission target: Eval4SD 2026.

Why:

- Submission deadline is 2026-07-03.
- Short/position papers are allowed.
- Law, medicine, finance, and specialized domains are in scope.
- Metrics and evaluation methodology are explicitly in scope.

Working title:

```text
Source-Isolated Citation Audit for LLM Outputs in Specialized Domains
```

Core claim:

```text
Citation reliability should be evaluated with three separated layers:
raw model answer, isolated external evidence, and audit verdict. A model-cited source is only a candidate until it is supplied, fetched, attested, or notarized outside the model output.
```

Minimum paper contribution:

1. Label taxonomy: verified, weakly_verified, irrelevant, unverifiable, contradicted.
2. `unverifiable` reason codes.
3. Evidence provenance grades.
4. Replay Ledger and Certification ID.
5. Hard benchmark cases, including real-source / overclaimed-causation.
6. Roadmap from citation-level audit to claim-span/source audit.

## Drafts

### R001 - Eval4SD Paper Query

Subject:

```text
Short paper fit: source-isolated citation audit for specialized-domain LLM outputs
```

Body:

```text
Hi Eval4SD organizers,

I am preparing a short/position paper around a source-isolated citation audit protocol for LLM outputs in specialized domains, especially legal and research-writing workflows.

The central idea is narrow: keep the raw model answer, isolated external evidence, and audit verdict separate, then label each citation as verified, weakly_verified, irrelevant, unverifiable, or contradicted. The latest version also records why an item is unverifiable and what provenance level the evidence reached.

Live demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Repo: https://github.com/reguorier/ai-judge
Roadmap: https://github.com/reguorier/ai-judge/blob/main/docs/CLAIM_SPAN_ROADMAP.md

Would this fit Eval4SD as a short/position paper or system description? I am especially interested in feedback on whether the contribution should be framed as evaluation methodology, a legal-domain benchmark artifact, or a reproducible tool demo.

Best,
Reguorier
```

### R002 - LegalCiteBench Benchmark Resonance

Subject:

```text
Mapping source-isolated citation audit to LegalCiteBench failure categories?
```

Body:

```text
Hi LegalCiteBench team,

I read your LegalCiteBench abstract and the focus on citation recovery, citation verification, case matching, and correction in legal LLMs is very close to a narrow tool I am building: AI Judge Citation Audit.

AI Judge is not a replacement benchmark. It is a local, source-isolated audit report for AI-generated answers. It preserves the raw answer, external evidence, and audit verdict separately, then labels citations as verified, weakly_verified, irrelevant, unverifiable, or contradicted. The newest version also separates unverifiable reason codes and evidence provenance.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Claim-span roadmap: https://github.com/reguorier/ai-judge/blob/main/docs/CLAIM_SPAN_ROADMAP.md

Would you be open to a quick taxonomy comparison? I am trying to understand whether AI Judge's labels can map cleanly to LegalCiteBench's legal-citation failure modes, especially cases where a real authority is cited but the generated claim overstates what the authority supports.

Best,
Reguorier
```

### R003 - HalluCiteChecker Research Exchange

Likely contact route:

```text
sakai.yusuke.sr9@is.naist.jp
```

Source: NAIST NLP lab staff page lists Yusuke Sakai and the lab email addresses.

Subject:

```text
Citation hallucination toolkit taxonomy comparison?
```

Body:

```text
Hi HalluCiteChecker team,

I saw your HalluCiteChecker work on detecting and verifying hallucinated citations in AI-generated scientific writing. I am building a complementary tool called AI Judge Citation Audit, focused on source-isolated citation checks for AI-generated answers and reports.

The shared problem is that a plausible citation can be fabricated, partially supported, irrelevant, inaccessible, or contradicted. AI Judge keeps model-mentioned sources as candidates until an external evidence layer supplies, fetches, attests, or notarizes the source.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Repo: https://github.com/reguorier/ai-judge

Would you be open to comparing taxonomies or exchanging one hard benchmark case? I am especially interested in cases that pass basic bibliographic checks but fail claim support.

Best,
Reguorier
```

### R006 - Attestation / Commercial Partnership

Subject:

```text
Citation audit hash before proof-of-prompt attestation?
```

Body:

```text
Hi Ligate team,

I am building AI Judge Citation Audit, a source-available tool that audits AI-generated citations before an answer is reused in reports, memos, or governance logs.

Your attestation stack seems to answer "can this prompt/output/action be witnessed?" AI Judge answers a narrower precondition: "should this cited answer enter a witness chain as trustworthy, unverifiable, or contradicted?"

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Repo: https://github.com/reguorier/ai-judge

Would a minimal integration make sense where AI Judge emits a Certification ID, Replay Ledger hash, citation status counts, and evidence provenance counts as an attestation payload? I am looking for a small commercial or technical wedge, not a large integration.

Best,
Reguorier
```

### R011 - Public Forum Reply Template

Use only after action-time confirmation and only in threads already asking about citation reliability.

```text
One pattern that helped me think about this: do not let the model's citation verify itself.

I am building a small source-isolated citation audit tool around that idea. It keeps the raw AI answer, external evidence, and audit verdict separate, then labels each citation as verified, weakly_verified, irrelevant, unverifiable, or contradicted. The tricky case is when the source is real and relevant but the model overclaims it, for example correlation -> causation.

Demo if useful: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

I am collecting hard benchmark cases, especially legal/compliance examples where the source exists but does not support the exact claim.
```

## Next Automatable Steps

1. Create a 2-4 page Eval4SD short paper draft from `docs/CLAIM_SPAN_ROADMAP.md`, `docs/UNVERIFIABLE_IS_NOT_FALSE.md`, and the hard benchmark.
2. Find reliable contact paths for LegalCiteBench, HalluCiteChecker, Aequis, Ligate, AEX, and Audit Trails authors.
3. Prepare individual email drafts as `.eml` files.
4. Ask for action-time confirmation before each send.
5. If any recipient replies with a benchmark case, keep private notes outside the public repo until anonymization permission is explicit.

Current paper artifacts:

- `docs/PAPER_SEED_SOURCE_ISOLATED_CITATION_AUDIT.md`
- `docs/EVAL4SD_2026_SOURCE_ISOLATED_CITATION_AUDIT_DRAFT.md`
