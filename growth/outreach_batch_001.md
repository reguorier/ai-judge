# Outreach Batch 001 - Citation Audit Benchmark Cases

Status: ready_to_send, not_sent
Created: 2026-05-18

This batch is designed to get the first real external signal without over-selling. The ask is benchmark cases, feedback on label boundaries, or one anonymized audit candidate. Paid audit or Pro access is introduced only after the recipient shows interest.

## Send Rules

- Send at most 5 first-touch messages per day.
- Personalize the first sentence from the `Why this target` column before sending.
- Record every send, reply, bounce, and objection in `growth/feedback_log.md`.
- Do not claim that AI Judge proves factual truth. It audits citations and keeps model text, mentor additions, and external evidence separate.
- Keep the key boundary visible: `unverifiable` means not enough isolated evidence, not false.

## CRM

| ID | Priority | Segment | Target | Channel | Source | Why this target | First ask | Status |
|---|---:|---|---|---|---|---|---|---|
| O001 | P0 | Legal AI newsletter | Inside Legal AI | `contact@insidelegalai.com` | https://www.insidelegalai.com/contact | Covers AI governance, legal knowledge infrastructure, and defensible AI use in law. | Ask for one anonymized bad-citation case or label-boundary feedback. | ready_to_send |
| O002 | P0 | Legal AI builder | Article 11 AI | `steve@article11.ai` | https://www.article11.ai/services.html | Builds governed AI systems and already publishes legal AI/citation risk material. | Ask whether source-isolated citation audit should be part of governance logs. | ready_to_send |
| O003 | P0 | LLM eval tooling | DeepEval / Confident AI | `dev@confident-ai.com` | https://github.com/confident-ai/deepeval | DeepEval is a large LLM evaluation framework; AI Judge is complementary as a narrow citation-level audit. | Ask for integration/metric-boundary feedback, not promotion. | ready_to_send |
| O004 | P0 | Hallucination tooling | factlens / Javier Marin | `javier@jmarin.info` | https://factlens.dev/ | Works on LLM hallucination detection; likely to understand narrow verification labels. | Ask for one adversarial citation example and comparison feedback. | ready_to_send |
| O005 | P1 | Legal-tech newsletter | LegalTech Digest | Site/newsletter channel | https://www.legaltechdigest.org/ | Tracks legal AI, startups, regulatory updates, and practical adoption. | Ask whether a short citation-hallucination demo would be useful for their readers. | channel_needed |
| O006 | P1 | LLM newsletter | LLM Watch / Pascal Biese | Substack channel | https://www.llmwatch.com/ | Covers LLM research for a large technical audience; hallucination/citation failures are recurring topics. | Ask for benchmark-case contribution or a reply with a memorable failure case. | channel_needed |
| O007 | P1 | Legal AI nonprofit | Free Law Project / AI Aware | Contact form | https://www.aiaware.io/contact | Public legal research reliability audience; search results point to hallucinated legal citations as a focus. | Ask for feedback on `unverifiable` vs `contradicted` in legal workflows. | form_ready |
| O008 | P1 | Legal citation competitor/peer | CaseRead Hallucination Shield | Product contact path | https://www.caseread.ai/ | Runs a legal citation verification tool; useful peer feedback for legal-citation boundaries. | Ask for comparison feedback and one edge case where source retrieval is ambiguous. | channel_needed |
| O009 | P1 | Academic citation risk | HalluCiteChecker authors | Paper/contact lookup needed | https://arxiv.org/abs/2604.26835 | Recent citation-hallucination toolkit; strong fit for benchmark exchange. | Ask for a benchmark cross-check and label taxonomy feedback. | needs_contact |
| O010 | P1 | Citation hallucination research | Rao/Wong/Callison-Burch paper | Paper/contact lookup needed | https://arxiv.org/abs/2604.03173 | Measures hallucinated citation URLs in LLM/deep-research outputs. | Ask whether Replay Ledger + source isolation matches their failure categories. | needs_contact |

## Email Drafts

### O001 - Inside Legal AI

Subject:

```text
Citation audit benchmark cases for legal AI?
```

Body:

```text
Hi Inside Legal AI team,

I am launching AI Judge Citation Audit, an open-source tool for checking AI-generated answers for fabricated, weak, irrelevant, unverifiable, and contradicted citations.

Your work sits exactly at the point where legal AI has to become defensible infrastructure instead of a magic demo. That is the narrow problem this tool is trying to make measurable: before publishing an AI-assisted memo or briefing, keep the original model text separate from external evidence and audit each citation.

Live demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
GitHub: https://github.com/reguorier/ai-judge

I am collecting hard benchmark cases. If you have seen an AI answer cite a real-looking source that did not exist, did not support the claim, or was impossible to verify, I would love to add an anonymized version to the benchmark.

One design detail I would especially value feedback on: AI Judge treats `unverifiable` as "not enough isolated evidence", not "false".

Best,
Reguorier
```

### O002 - Article 11 AI

Subject:

```text
Source-isolated citation audit for governed AI logs
```

Body:

```text
Hi Steve,

I am building AI Judge Citation Audit, an open-source citation-level audit tool for AI-generated answers.

I noticed Article 11 AI's emphasis on governed AI, tamper-evident logging, and legal AI workflows. AI Judge is narrower: it does not try to be a full legal AI system. It preserves the model's original answer, mentor additions, and external evidence as separate layers, then labels each citation as verified, weakly_verified, irrelevant, unverifiable, or contradicted.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Repo: https://github.com/reguorier/ai-judge

Would this kind of source-isolated citation audit be useful as a small governance layer before an answer enters an audit log? I am mainly looking for one hard edge case or a short critique of the label taxonomy.

Best,
Reguorier
```

### O003 - DeepEval / Confident AI

Subject:

```text
Narrow citation-level eval for LLM outputs
```

Body:

```text
Hi Confident AI team,

I am launching AI Judge Citation Audit, a small open-source project focused on one narrow metric: whether citations in an AI-generated answer are fabricated, weak, irrelevant, unverifiable, or contradicted.

DeepEval is much broader, so I am not treating this as a competitor. The intended fit is a small pre-publish or CI check for source-heavy outputs where users need the original model text, evidence, and audit result kept separate.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Repo: https://github.com/reguorier/ai-judge

If you have two minutes, I would value feedback on whether this should stay as an independent CLI/report format, or whether a narrow metric/integration shape would make more sense for eval-framework users.

Best,
Reguorier
```

### O004 - factlens / Javier Marin

Subject:

```text
Citation hallucination edge cases?
```

Body:

```text
Hi Javier,

I am building AI Judge Citation Audit, an open-source tool that checks AI-generated answers at the citation level and preserves a Replay Ledger of the original answer, supplied evidence, and verification outcome.

I saw your work on hallucination detection and thought you might have useful instincts on failure cases. AI Judge deliberately keeps the scope narrow: citation labels are verified, weakly_verified, irrelevant, unverifiable, and contradicted.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Repo: https://github.com/reguorier/ai-judge

I am collecting adversarial benchmark cases. If you have one case where an answer sounds grounded but the source trail breaks, I would love to add an anonymized version or just get your critique of the taxonomy.

Best,
Reguorier
```

### O005 - LegalTech Digest

Subject:

```text
Short legal AI citation-hallucination demo for your readers?
```

Body:

```text
Hi LegalTech Digest team,

I am launching AI Judge Citation Audit, an open-source demo that audits AI-generated answers for citation problems before they are reused in memos, reports, or client-facing drafts.

The legal-tech angle is intentionally practical: the report does not say "the AI is wrong" when evidence is missing. It separates `unverifiable` from `contradicted`, which matters when lawyers or operators need to know whether a claim is merely unsupported or actually refuted.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
GitHub: https://github.com/reguorier/ai-judge

If this fits your audience, I can send a short reproducible example or contribute an anonymized citation-hallucination case study.

Best,
Reguorier
```

### O006 - LLM Watch

Subject:

```text
Benchmark cases for citation hallucinations
```

Body:

```text
Hi Pascal,

I am launching AI Judge Citation Audit, an open-source project focused on one small but measurable LLM failure mode: citations that look plausible but are fabricated, irrelevant, unverifiable, weakly supported, or contradicted by the source.

The tool is intentionally not another general LLM judge. It keeps the original model output, external evidence, and audit result separate so the judge does not "verify hallucination with another hallucination."

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
GitHub: https://github.com/reguorier/ai-judge

I am collecting hard benchmark cases. If you have seen a memorable citation failure in research summaries or deep-research outputs, I would love to add an anonymized case and credit the source/channel if you want.

Best,
Reguorier
```

### O007 - AI Aware / Free Law Project

Subject:

```text
Feedback on legal citation-audit labels
```

Body:

```text
Hi AI Aware team,

I am launching AI Judge Citation Audit, an open-source citation-level audit tool for AI-generated answers.

The core design is conservative: the original model answer is preserved, external evidence is separate, and each citation receives one of five labels: verified, weakly_verified, irrelevant, unverifiable, or contradicted. In legal workflows, I suspect the boundary between `unverifiable` and `contradicted` is especially important.

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Repo: https://github.com/reguorier/ai-judge

Would you be open to sharing one anonymized legal citation hallucination case or critiquing the label boundary? I am trying to build the benchmark around real failure modes, not synthetic examples only.

Best,
Reguorier
```

## Reply Handling

| Reply type | Next action |
|---|---|
| Sends a bad-citation case | Ask permission to anonymize; add to benchmark issue #2 and create a fixture. |
| Asks for PDF/Docx/batch | Log as Pro signal; reply with `docs/BATCH_AUDIT_SPEC.md` and ask which file type matters first. |
| Says tool overlaps with RAG/eval tools | Explain narrow citation-level source isolation; ask which integration would make it useful. |
| Challenges `unverifiable` | Send `docs/UNVERIFIABLE_IS_NOT_FALSE.md`; ask for an example where the label would be misleading. |
| Asks for paid audit | Offer one free anonymized audit for testimonial permission, then quote AI Decision Audit separately. |

## Send Log

Canonical event tracking now lives in `growth/outreach_events.jsonl` and the generated status page `growth/outreach_status.md`.

Example:

```bash
python3 tools/record_outreach_event.py sent O001 --channel qq-mail --note "Sent via Safari QQ Mail"
python3 tools/record_outreach_event.py reply O001 --channel email --note "Asked for PDF batch audit"
python3 tools/record_outreach_event.py pro_signal O001 --channel email --note "Needs batch PDF audit"
```

| Date | Target ID | Channel | Status | Reply | Next action |
|---|---|---|---|---|---|
| TBD | TBD | TBD | not_sent | TBD | TBD |
