# AI Judge Submission Council 2026

Status: active execution plan
Created: 2026-05-19
Last refreshed: 2026-05-19 03:44 HKT

This file records a source-isolated "model council" for finding the next
research, commercial, and community routes for AI Judge Citation Audit.

Method:

- Raw user goal: find more submission and collaboration paths that can create
  research credibility, commercial demand, and GitHub attention.
- Mentor council: nine AI Judge seat personas generated distinct routes and
  risks from their assigned cognitive roles.
- External evidence: only public venue pages, CFPs, OpenReview groups, GitHub
  issues, and verified public contact routes are used below.

Do not treat this as final authorization to send emails, submit forms, or post
public messages. Prepare packets automatically, then stop at the final external
action unless the user gives action-time confirmation.

## Council Verdict

Recommended posture:

```text
Pursue a research-first wedge, not a broad commercial launch.
The strongest current claim is: citation existence, source relevance, and exact
claim support must be audited separately.
```

Best near-term bundle:

1. Eval4SD remains the primary paper route because the organizer already
   confirmed fit and the paper packet is ready.
2. RLEval / KDD Agentic AI Evaluation are the best adjacent routes if the frame
   shifts from "citation audit" to "agent-output trust gate".
3. CLEAR and legal-NLP routes are the best legal/research credibility channels,
   especially for real-citation / wrong-proposition cases.
4. SeT-LLM is the best safety/security route if the paper is reframed as a
   secure-and-trustworthy LLM output audit protocol.
5. Commercial outreach should stay narrow: evaluation platforms, legal AI
   provenance vendors, and RAG/agent observability tools. Lead with one hard
   benchmark case or one receipt schema, not a sales pitch.

## Nine-Seat Model Council

| Seat | Primary lens | Concrete route | What to produce next | Main risk |
|---|---|---|---|---|
| Gemini / INTJ | Authority and source verification | Eval4SD, CLEAR, LegalCiteBench, NLLP watch | A clean taxonomy table mapping citation existence, relevance, and claim support | Over-indexing on formal venues while missing user adoption |
| ChatGPT / ESTJ | Product packaging and consensus | GitHub README, HF Space, proof kit, buyer-facing audit sample | One-page Decision Audit report template with before/after screenshots | Looks useful but lacks repeated external usage |
| DeepSeek / INTP | Mechanism and metric design | RLEval, KDD Agentic AI Evaluation, SeT-LLM | A formal claim-span/source metric spec and hard-case benchmark appendix | Too abstract if not tied to a demo |
| Qwen / ISFJ | Compliance and cautious validation | CLEAR, AI/open-government, legal AI workshops | Risk language: unverifiable is not false; real source is not proven conclusion | Conservative wording may reduce launch energy |
| Kimi / ENFP | Narrative and community spread | X, Zhihu, blog, HF discussion, GitHub issues | "9 AI collective blind spots" essay tied to a reproducible hard case | Narrative can outrun evidence if not ledger-backed |
| Grok / ENTP | Adversarial blind spots | RAGChecker, LegalCiteBench, hallucination benchmarks | Three adversarial cases: causation overclaim, absolute overclaim, numeric overclaim | May sound too negative if framed as attack |
| Yuanbao / ISTJ | SOP and certification | Certification hash, Replay Ledger, GitHub Action | Submission checklist and repeatable audit SOP for papers/reports | Process can feel heavy for first-time users |
| MiMo / INFJ | Ethics and public good | Social-impact/governance routes, open standards, academic artifact | Public protocol framing: keep raw model answer, mentor supplement, external evidence separate | Values framing without technical novelty |
| Doubao / ENTJ | Execution and MVP | 72-hour paper sprint, 2-week second wave, monthly demo cadence | A scheduled execution board with P0/P1/P2 targets and stop/go metrics | Too many parallel routes without pruning |

## Active Submission And Collaboration Matrix

| Priority | Route | Contact / submission path | Deadline status | Best AI Judge angle | Next automatable action |
|---|---|---|---|---|---|
| P0 | Eval4SD 2026, KONVENS | `eval4sd-organizers@googlegroups.com`; OpenReview group | CFP page lists July 03, 2026 AOE; OpenReview account moderation is the blocker | Source-isolated citation and claim-support audit for specialized-domain LLMs | Keep the packet ready, update hard-case count to 13, monitor organizer/OpenReview reply, submit only after final confirmation |
| P0 | RLEval 2026 | OpenReview; CFP contact listed as `rl-eval@googlegroups.com` | May 20, 2026 AOE | Agent-output evaluation: before an agent answer is trusted, verify citation/source/claim support | Prepare a 1-page fit-check and abstract variant; send only after action-time confirmation |
| P0 | CLEAR 2026 | `themis.xanthopoulou@umu.se`; OpenReview | May 20, 2026 AOE | Computational law evidence audit: real legal source does not prove generated legal proposition | Prepare a legal framing abstract and reuse the claim-support hard cases |
| P1 | KDD Agentic AI Evaluation and Trustworthiness | OpenReview group | OpenReview route active; use venue page for current dates | Trust gate for agentic outputs, replay ledger, certification hash, and source-isolated evidence | Prepare a system-demo abstract; do not submit until route/date are rechecked |
| P1 | SeT-LLM 2026 | OpenReview group; no verified email found in public search | June 01, 2026 AOE in OpenReview listing | Secure and trustworthy LLM output audit with source isolation and replayability | Prepare a security/trust version of the abstract; use OpenReview if account recovers |
| P1 | AI & Open Government 2026 | Public site exposes organizer/contact route, exact email not verified in this pass | Current CFP appears past for 2026 direct submission; monitor future workshop cycles | Auditable AI-generated public-sector and policy memos | Add as relationship/2027 route, not current primary target |
| P2 | NLLP / Natural Legal Language Processing | Historical workshop contact: `nllp-2025@googlegroups.com`; 2026 route not verified | 2026 route not found in this pass | Legal citation failure taxonomy and wrong-proposition benchmark cases | Watch for 2026/2027 CFP; prepare a taxonomy exchange note |
| P2 | GEM benchmark workshop | Public site and ACL Member Portal pages | 2026 submission window appears closed | Metric and benchmark artifact if reopened or for later cycle | Keep as long-term benchmark-community target |
| P2 | IAIT 2026 | `info@iait-conf.org` | Full-paper deadline appears past; workshop proposal deadline close/past | AI auditing, compliance, and governance tool | Monitor 2027 or ask whether late demo/workshop route exists only after confirmation |
| P2 | Stanford CustomEval / FutureLaw / Co-Data | `customevals@law.stanford.edu`; `codexfuturelaw@law.stanford.edu`; `leelevin@law.upenn.edu` | Current listed events are past | Relationship building around legal AI evidence and custom evals | Send no blanket pitch; prepare one hard-case benchmark exchange per contact |
| P2 | DeepEval / Confident AI | `dev@confident-ai.com` already used in prior outreach | Follow-up only after 3-5 days or reply | Add claim-support audit as a pre-eval plugin/check | Wait for reply; no duplicate send |
| P2 | LegalCiteBench and RAGChecker | GitHub issues already posted | Open, no reply in latest check | Taxonomy exchange for real-citation / unsupported-claim failures | Monitor issues; follow up only with a new case or maintainer reply |
| P3 | Aequis | Public route remains unverified due Cloudflare/TLS/DNS issues | Blocked | Legal AI provenance and jurisdiction-aware benchmark infrastructure | Do not guess email; retry verified contact route later |
| P3 | Ligate | Private route already used in prior outreach | Follow-up only after 3-5 days or reply | AI Judge audit hash as a pre-attestation receipt | Wait; prepare receipt-schema sketch locally |

## Paper Variants To Build

| Variant | Target | Working title | Reuse from current packet | Missing piece |
|---|---|---|---|---|
| V1 Specialized-domain evaluation | Eval4SD | Source-Isolated Citation and Claim-Support Audit for LLM Outputs in Specialized Domains | Current paper, benchmark, proof kit | OpenReview access or backup route |
| V2 Agent evaluation | RLEval / KDD Agentic AI Evaluation | A Source-Isolated Trust Gate for Agentic LLM Outputs | Replay Ledger, certification ID, claim-support hash | One agent-output example and evaluation framing |
| V3 Legal evidence audit | CLEAR / NLLP | Real Citation, Wrong Proposition: Claim-Support Audit for Legal LLM Outputs | Legal-citation taxonomy, Article 11 hard case, LegalCiteBench issue | A legal-domain example that is public and non-private |
| V4 Security/trust protocol | SeT-LLM | Source Isolation as a Trust Boundary for LLM-Generated Evidence | Source isolation spec, hashes, SOP | Threat model: model self-verification and provenance poisoning |
| V5 Public-sector governance | AI & Open Government / IAIT | Replayable Evidence Audits for AI-Generated Policy and Research Memos | Certification hash, unverifiable explainer | Public-sector scenario and stakeholder language |

## Draft Outreach Snippets

These are drafts only. Do not send without action-time confirmation.

### RLEval Fit Check

```text
Subject: Fit check: source-isolated trust gate for agentic LLM evaluation?

Hi RLEval organizers,

I am preparing a short system/position note around AI Judge Citation Audit, a
local-first audit protocol for LLM and agent outputs. The narrow contribution is
to separate three states that are often collapsed in evaluation reports:

1. whether a cited source exists,
2. whether it is relevant to the generated claim, and
3. whether it supports the exact claim span.

The hard case is a real source that reports association while the model or
agent states causation. The audit keeps the raw answer, external evidence, and
verdict metadata separate, then emits a replay ledger and certification hash.

Would this fit RLEval better as a short position/system note on evaluation
methodology for agentic outputs, or is it outside the workshop scope?

Best,
Reguorier
```

### CLEAR Fit Check

```text
Subject: Fit check: legal citation audit where real source != supported proposition

Hi CLEAR organizers,

I am preparing a short paper/demo around source-isolated citation audit for LLM
outputs. The motivating legal hard case is when a generated answer cites a real
authority, but the proposition overstates what the authority actually supports.

The protocol reports citation existence, source relevance, and exact claim
support separately, preserving raw model answer, external evidence, and audit
verdict metadata in separate layers.

Would a short system/position paper on this failure mode fit CLEAR?

Best,
Reguorier
```

### SeT-LLM Fit Check

```text
Subject: Fit check: source isolation as a trust boundary for LLM evidence

Hi SeT-LLM organizers,

I am preparing a short system/position note about preventing LLM outputs from
verifying their own cited evidence. The protocol keeps raw answer, external
evidence, and audit verdicts separate, then emits replay-ledger and
certification hashes for downstream review.

The core threat model is "using hallucination to verify hallucination": a model
mentions a plausible source, and a later system treats that mention as evidence.
The audit instead checks citation existence, relevance, and exact claim support
as separate states.

Would this fit SeT-LLM as a secure/trustworthy LLM evaluation artifact?

Best,
Reguorier
```

## 72-Hour Execution Plan

### Day 0-1

- Refresh Eval4SD packet to hard 13/13 and keep OpenReview fields ready.
- Create RLEval and CLEAR one-page abstracts from the current Eval4SD paper.
- Check QQ Mail for Eval4SD/OpenReview reply before any duplicate support ask.

### Day 1-2

- If OpenReview account recovers, prepare Eval4SD form and stop before final
  submit.
- If not recovered, continue with non-OpenReview assets: legal abstract,
  agent-eval abstract, and public proof-kit issue links.
- Prepare but do not send RLEval/CLEAR fit-check emails unless confirmed.

### Day 2-3

- Add one public, non-private legal/policy hard case if a source can be cited
  without exposing third-party correspondence.
- Write a one-page receipt-schema note for Ligate-style attestation:
  `audit_hash`, `claim_support_hash`, `source_layer_hash`, `raw_answer_hash`,
  `verdict`, `failure_codes`.
- Update metrics and stop/go dashboard with submission-route status.

## Continuing Cadence

Daily:

- Check Eval4SD/OpenReview reply, GitHub issue replies, and taxonomy issue
  replies.
- Record any reply with `tools/record_outreach_event.py`.
- Do not post no-op follow-ups.

Twice weekly:

- Convert one external objection into one benchmark case or documentation patch.
- Prepare one venue-specific abstract variant.

Weekly:

- Pick the single highest-probability submission route for that week.
- Run the benchmark and packet checks before any final submission.
- Update the public proof kit and metrics dashboard.

Stop/go:

- Keep building research credibility if at least one credible reviewer,
  organizer, maintainer, or professional user engages with a hard case.
- Push commercial offers only when a user asks for repeated audits, batch mode,
  GitHub Action integration, or invoice/payment details.

## Sources Used

- Eval4SD CFP: https://eval4sd.github.io/cfp/
- Eval4SD OpenReview group: https://openreview.net/group?id=GSCL.org/KONVENS/2026/Workshop/Eval4SD
- RLEval 2026: https://rl-eval.github.io/
- CLEAR 2026: https://clear-ws.github.io/2026/
- KDD Agentic AI Evaluation OpenReview: https://openreview.net/group?id=KDD.org/2026/Workshop/Agentic_AI_Evaluation_and_Trustworthiness
- SeT-LLM OpenReview: https://openreview.net/group?id=KDD.org/2026/Workshop/SeT_LLM
- GEM Workshop: https://gem-workshop.com/
- IAIT 2026: https://www.iait-conf.org/2026/
- NLLP Workshop: https://nllpw.org/workshop/
- Stanford FutureLaw 2026: https://conferences.law.stanford.edu/futurelaw2026
- Co-Data Evidence-Driven Legal AI: https://co-data.github.io/
