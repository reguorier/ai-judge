# AI Judge Growth Playbook

Status: conditional go
Score: 81/100
Last refreshed: 2026-05-19

AI Judge should not be sold first as a broad AI assistant or a full automated judge.
The narrow wedge is stronger:

```text
An open citation and claim-support audit protocol for AI-generated answers.
```

The product earns trust by preserving three layers separately:

1. Raw model answer.
2. Mentor or model supplement.
3. External evidence and audit verdicts.

The judge summarizes, counts, scores, and exposes uncertainty. It does not rewrite
the original answer and it does not use a model's own citation as proof.

## Current Position

Proceed, but only with verification gates.

| Dimension | Current judgment |
|---|---|
| Product clarity | Good enough for a narrow citation-audit wedge. |
| Research credibility | Promising through Eval4SD, LegalCiteBench, HalluCiteChecker, and RAGChecker taxonomy exchange. |
| Public proof | Live Hugging Face Space, GitHub demos, benchmark cases, and reproducible reports exist. |
| Commercial readiness | Too early for a full SaaS; keep Pro capture ready and sell only after demand appears. |
| Main risk | Confusing real citation existence with exact claim support. |

## Core Thesis

A real source does not prove the model's claim.

AI Judge separates:

| Layer | Question | Output examples |
|---|---|---|
| Citation status | Does the source exist or match isolated evidence? | `verified`, `weakly_verified`, `unverifiable` |
| Source relevance | Is the source about the right topic? | `relevant`, `weakly_relevant`, `irrelevant` |
| Claim support | Does the source prove the exact generated claim span? | `supported`, `unsupported`, `contradicted` |

This avoids the most dangerous Grand Judge failure mode: using hallucinated or
overclaimed evidence to validate another hallucination.

## Execution Phases

### Phase 1: Trust Baseline

- Keep citation audit MVP narrow and deterministic.
- Show `verified`, `weakly_verified`, `irrelevant`, `unverifiable`, and `contradicted` clearly.
- Preserve Certification ID and Replay Ledger.
- Keep Hugging Face Space and local CLI demos runnable.
- Explain that `unverifiable` means insufficient isolated evidence, not false.

### Phase 2: Research Credibility

- Submit the Eval4SD short or position paper once OpenReview account access or a backup route is available.
- Continue taxonomy exchange with LegalCiteBench, HalluCiteChecker, and RAGChecker.
- Keep the paper focused on source isolation and claim-support audit, not a full AI judging system.
- Use the hard case: a real source reports association while the model claims causation.

### Phase 3: Professional Feedback

- Use GitHub issues, X, Zhihu, and direct outreach to collect benchmark cases.
- Ask for examples before asking for money.
- Convert every useful objection into one of:
  - benchmark fixture
  - demo report
  - docs clarification
  - Pro requirement

### Phase 4: Monetization

Do not build billing infrastructure before demand.

Keep these offers ready:

| Offer | Trigger |
|---|---|
| AI Decision Audit report | A user wants a one-off review of an AI-generated memo, investment note, legal memo, or product plan. |
| Pro Batch Audit | At least three users ask for repository, PDF, Docx, or CI batch workflows. |
| GitHub Action / API | A team wants repeatable checks in documentation or review pipelines. |
| Sponsor path | A user wants to support the protocol without buying a workflow. |

## Stop / Go Rule

Continue Pro only if at least one signal appears inside the tracking window:

- 100 GitHub stars.
- 20 distinct users run the demo, star, comment, reply, or ask for help.
- 3 users request batch/PDF/GitHub Action Pro workflows.
- 1 user pays, asks for an invoice, or requests a scoped audit.

If none happen, pause monetization and improve proof quality instead.

## Next Best Action

The next best action is not more generic launch posting.

Priority order:

1. Recover Eval4SD submission path or get organizer backup guidance.
2. Turn the real-source / unsupported-claim boundary into more public demos.
3. Ask professional users for anonymized hard cases.
4. Improve GitHub conversion docs and quickstart clarity.
5. Keep Pro capture ready, but do not overbuild billing.

