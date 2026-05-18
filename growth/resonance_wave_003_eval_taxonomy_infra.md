# Resonance Wave 003 - Eval4SD, Taxonomy Exchange, and Trust Infrastructure

Status: organizer_fit_confirmed
Created: 2026-05-18
Last updated: 2026-05-19

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
| W003-001 | P0 | Eval4SD 2026 | Workshop submission | `papers/eval4sd2026/openreview_submission.md` | organizer_support_request_sent |
| W003-002 | P0 | HalluCiteChecker | Research taxonomy exchange | Email draft below | sent_private_log |
| W003-003 | P0 | LegalCiteBench | Legal citation taxonomy exchange | Email draft below | public_issue_posted |
| W003-004 | P1 | Aequis | Legal AI provenance / benchmark collaboration | Email draft below | contact_route_unverified |
| W003-005 | P1 | Ligate | Attestation payload integration | Email draft below | sent_private_log |

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

1. Keep `papers/eval4sd2026/main.tex` on the official ACL review template.
2. Build and inspect the anonymous PDF once a local LaTeX engine is available.
3. Refresh benchmark numbers immediately before PDF export.
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

Continue by waiting for Eval4SD organizer guidance or recovering OpenReview login before opening the Eval4SD submission form. The submission page and "Add: GSCL KONVENS 2026 Workshop Eval4SD Submission" route are live, but OpenReview currently returns "Please Login to proceed." The OpenReview signup confirmation email arrived, activation links were opened, and the profile registration form was completed more than once with a public project URL, independent-researcher history, preferred email, and relevant expertise tags. A subsequent login attempt generated a fresh activation token and sent the account back through the "Complete Registration" flow again, then returned to the public Venues page still showing `Login`. The current blocker is OpenReview account activation/moderation, not packet readiness or venue fit. Do not inspect saved passwords or perform a password reset through automation; use OpenReview support or organizer guidance unless the user takes over the login manually.

Once login is recovered, upload `papers/eval4sd2026/main.pdf` and use `papers/eval4sd2026/openreview_submission.md` for form fields. Stop before the final submit button until action-time confirmation is available. The Eval4SD packet was rechecked on 2026-05-18: the PDF remains anonymous and the full/hard benchmarks both pass at 100%. Eval4SD fit is confirmed by organizer reply: short/position paper is a good fit, and a demo paper with limited evaluation would also work; no further pre-fit check is needed. On 2026-05-19, a support request was sent to Eval4SD organizers asking whether to wait for OpenReview moderation, contact OpenReview support, or use an alternate submission route. Follow up on sent W003-002 and W003-005 only after 3-5 days or if a reply arrives. W003-003 and RAGChecker were checked by `gh issue view` on 2026-05-18 and have no comments yet, so do not post a no-op follow-up. For W003-004, do not guess an unverified email address; retry from a clean DNS/network path or a verified public channel before sending.

Detailed third-party outreach metadata is intentionally kept out of public GitHub. The private local execution ledger lives under `.ai-judge/growth/`.

## Channel Findings

- W003-003 LegalCiteBench: the arXiv PDF and GitHub repository expose a GitHub repository (`Sijia711/LegalCiteBench`) and Hugging Face dataset (`legalcitebench/LegalCiteBench`), but no public email. GitHub Issues are enabled; a public taxonomy-exchange issue was posted at `https://github.com/Sijia711/LegalCiteBench/issues/1`.
- W003-004 Aequis: the public site confirms the fit around provenance, jurisdiction, time, and reproducible legal AI benchmarks. The site exposes collaboration/contact links, but they route through Cloudflare email protection. Local DNS resolves `aequis.io` to `198.18.1.23`, and direct HTTPS attempts fail with `LibreSSL SSL_connect: SSL_ERROR_SYSCALL`; Jina Reader cannot resolve the host. No verified public email or working GitHub organization route has been found, so this remains blocked rather than guessed.
- W003-001 Eval4SD: organizer reply confirmed the topic is a strong workshop fit for research/legal specialized-domain LLM reliability. Recommended path is short/position paper; demo paper with limited evaluation is also acceptable. A concise thank-you reply was sent via QQ Mail on 2026-05-18.
- W003-001 OpenReview: the submission route is live and points to OpenReview. Confirmation emails arrived, activation links were opened, and profile registration was completed repeatedly. Login attempts can trigger another activation/profile-completion loop, then return to a public page that still shows `Login`. Submission is blocked by OpenReview account activation/moderation rather than by the Eval4SD packet. A support-path request was sent to Eval4SD organizers on 2026-05-19 via QQ Mail. OpenReview's automatic profile email says the profile was created and needs moderation, usually less than 1 business day but up to 2 weeks; adding a confirmed company or institutional email can expedite activation. Use the pushed packet and PDF after the account can establish a logged-in session or the organizers provide a backup route. Final submit still needs action-time confirmation.
- W003-003 / W004-002 monitoring: LegalCiteBench issue #1 and RAGChecker issue #38 remain open with no comments as of the latest `gh issue view` check on 2026-05-18.

## Public Links

- LegalCiteBench taxonomy exchange issue: `https://github.com/Sijia711/LegalCiteBench/issues/1`

## Submission Packet

- Eval4SD anonymous LaTeX draft: `papers/eval4sd2026/main.tex`
- Eval4SD anonymous PDF build: `papers/eval4sd2026/main.pdf`
- Eval4SD ACL template files: `papers/eval4sd2026/acl.sty`, `papers/eval4sd2026/acl_natbib.bst`
- Eval4SD bibliography: `papers/eval4sd2026/references.bib`
- Eval4SD checklist: `papers/eval4sd2026/submission_checklist.md`
- Eval4SD pre-submit check: `tools/check_eval4sd_packet.py`
- Eval4SD OpenReview form packet: `papers/eval4sd2026/openreview_submission.md`
- Eval4SD OpenReview JSON packet: `papers/eval4sd2026/openreview_submission.json`
