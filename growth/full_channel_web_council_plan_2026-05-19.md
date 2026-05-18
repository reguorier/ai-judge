# AI Judge Full-Channel Web Council Plan

Date: 2026-05-19

This plan replaces the old 30-day heartbeat autopilot. The next operating mode is not an unattended hourly automation. It is a source-isolated execution loop:

1. Run web-seat AI Judge councils for strategy.
2. Keep each raw seat answer separate.
3. Verify dates, contact routes, and requirements against external sources.
4. Execute only actions that do not publish, send, submit, or solve CAPTCHA without action-time confirmation.

## Web Council Receipt

The current web-seat run was attempted against 13 enabled seats. It was a real web-seat run, not a local persona simulation.

| Seat | Result | Usable Signal |
|---|---|---|
| Claude | Complete | Strong structured plan: research identity first, Eval4SD and HN/GitHub proof kit as the primary wedge, Product Hunt after live demo proof, commercial competitions only if pitch assets can be completed quickly. |
| Kimi | Partial | Useful timing view: HN/Product Hunt/community first for attention, but Kimi was downgraded to a fast model because of compute shortage. |
| MiMo | Partial | Useful execution emphasis: confirm Eval4SD page, improve Hugging Face demo, make a public growth checklist. |
| Qwen | Stale/invalid | Captured an older short-video strategy run, not the current submission-growth task. |
| DeepSeek | Failed capture | Expert mode, deep thinking, and search were manually verified, but the current prompt did not produce a capturable answer. |
| Gemini | Failed capture | Page retained the prompt/placeholder and did not return a current answer. |
| ChatGPT | Invalid placeholder | Current run showed the answer marker placeholder rather than a usable answer. |
| Grok | Failed/no answer | Page asked for content instead of answering the current prompt. |
| Yuanbao | Invalid placeholder | Prompt marker was present, but no answer replaced the placeholder. |
| MiniMax | Invalid placeholder | Prompt marker was present, but no answer replaced the placeholder. |
| Zhipu | Stale/invalid | Captured an older TikTok/visual strategy answer, not the current task. |
| Wenxin | Invalid/editor state | Page stayed in edit/history mode with placeholder content. |
| Doubao | Invalid placeholder | Super mode was manually verified, but no current answer replaced the placeholder. |

Conclusion: the bridge still cannot be treated as publication-grade. The plan below uses only the valid/partial web-seat signals plus independently checked external sources.

## Final Direction

AI Judge should not launch first as a broad commercial app. The sharpest wedge is:

> An open-source source-isolated AI decision audit protocol that catches when real sources are used to overclaim model conclusions.

This turns Steve Sonza / Article 11's hard case into the product thesis:

> A real citation can prove relevance without proving the model's claim. AI Judge should audit claim-span/source support, not just citation existence.

That is the thread connecting research, GitHub growth, and eventual paid audits.

## Priority Matrix

| Priority | Path | Status | Deadline / Timing | Contact / Submission Route | Required Assets | AI Judge Angle | Decision |
|---|---|---|---|---|---|---|---|
| P0 | Eval4SD @ KONVENS 2026 | Verified | 2026-07-03 23:59 CEST | OpenReview; eval4sd-organizers@googlegroups.com | 4-page short/position paper, ACL template, demo link, small benchmark | Source-isolated claim support audit for specialized domains | Do now |
| P0 | EMNLP 2026 Industry Track | Verified | 2026-06-16 AoE | OpenReview; emnlp2026-industry-track@googlegroups.com | 6-page industry paper, reproducible system description | Real-world deployment lessons for browser/web-seat AI evaluation and citation audit | Prepare fallback/parallel abstract |
| P1 | KDD Agentic AI Evaluation and Trustworthiness Workshop | Verified but tight | 2026-06-01 AoE | OpenReview; kdd-ws-agentic-eval@amazon.com | 9-page ACM PDF, anonymous | Multi-agent evaluation, post-market monitoring, model evolution risk | Only submit if 3-day paper sprint is acceptable |
| P1 | KDD SeT-LLM 2026 | Verified but tight | 2026-06-01 AoE | OpenReview | 4-page ACM PDF | Trustworthy assurance, uncertainty, auditing, legal/high-stakes use cases | Short system paper possible |
| P1 | Discover Computing special issue: LLMs as Evaluators | Verified | 2026-07-31 | Springer collection; contact Javier Parapar, javier.parapar@udc.es | Journal article | Longer version after Eval4SD: protocol + benchmark + error taxonomy | Start after Eval4SD draft |
| P1 | Hacker News Show HN | Verified | Self-timed | Direct HN submit | Try-without-signup demo, GitHub README, first comment | "AI answers enter a jury; human keeps the gavel" | Launch after demo survives fresh-user test |
| P1 | Hugging Face Space | Already live | Continuous | HF Space page/community when CAPTCHA-free | Stable demo, example reports, dataset card | Immediate tryable proof for HN/Eval4SD | Keep improving |
| P2 | Product Hunt | Verified | Self-scheduled | Product Hunt New Product flow | Polished screenshots, demo video, tagline, maker comment | Consumer-friendly story: "9 AIs cross-examine each other" | Delay until demo and social proof exist |
| P2 | BetaList | Verified | 2-4 weeks before Product Hunt | BetaList submission form | Own-domain working website, private/early beta positioning | Pre-launch waitlist and early feedback | Use as PH warmup |
| P2 | RAISE the STAKES 2026 | Needs check | 2026-06-10 in milestone section; page footer also says closes July 1 | Dealum application from RAISE page | Legal entity, 2-person team, pitch deck, short video | AI accountability infrastructure | Conditional; verify the Dealum form before investing pitch-deck time |
| P2 | The Rundown AI / Supertools | Verified route | Continuous | Tool submission form / newsletter feature form | Tool page, demo link, concise value prop | "A public AI audit tool for checking model claims" | Submit after demo copy is clean |
| P3 | TLDR AI | Verified route for sponsorship, not editorial pitch | Continuous | advertise.tldr.tech | Paid/native ad budget or sponsorship inquiry | Developer-facing trust tooling | Do not prioritize without budget |
| P3 | Ben's Bites | Verified publication existence, no email verified | Continuous | Substack/social route | Founder story + AI builder framing | Solo builder, open-source AI accountability | Draft only; do not invent contact email |
| P3 | Latent Space | Verified publication existence, no direct email verified here | Continuous | Substack/social route | Deep technical post | Browser collection, claim support, calibration | Pitch after paper preprint |
| P3 | Import AI | Verified publication existence, no direct pitch email verified here | Continuous | Substack/blog route | Research summary | Evaluation methodology and governance | Pitch after arXiv/preprint |

## Research Track: Paper Portfolio

### Paper A: Eval4SD Short / Position Paper

Working title:

`Source-Isolated Claim Support Audit for Specialized-Domain LLM Outputs`

Core claim:

AI outputs often cite real and relevant sources while overclaiming what those sources prove. AI Judge separates raw answer, mentor supplement, external evidence, and final verdict so that citation existence, source relevance, and exact claim support are scored separately.

Minimum experiment:

| Dataset Slice | Count | Purpose |
|---|---:|---|
| Fake citation | 10 | Does validator catch nonexistent source patterns? |
| Real but irrelevant source | 10 | Does relevance classification work? |
| Real source, overclaimed causality | 10 | Steve Sonza / Article 11 hard case |
| Real source, quantified overclaim | 10 | Numbers not supported by source |
| Sounds-smart / low-judgment answer | 10 | Separate rhetoric from support |

Outputs:

1. Claim-span table.
2. Citation-level labels: verified, weakly_verified, irrelevant, unverifiable, contradicted.
3. Claim-support labels: supports, partially_supports, related_only, does_not_support, contradicts, no_evidence.
4. Replay ledger with raw answer, mentor supplement, external evidence, verdict, timestamp, certification hash.

### Paper B: EMNLP Industry Track

Working title:

`Lessons from Building a Browser-Collected Multi-Model Jury for Auditable AI Decisions`

Core claim:

Real web products are not the same as API-only evaluation. Browser collection exposes practical reliability issues: model mode selection, slow answers, quota limits, stale pages, placeholder answers, and capture failures. These are not engineering noise; they are part of production evaluation fidelity.

Use the current council failure receipt as a research asset, not an embarrassment.

### Paper C: Discover Computing Journal Extension

Working title:

`From Citation Existence to Claim Support: A Source-Isolated Protocol for LLM-as-Evaluator Systems`

Expansion over Eval4SD:

1. Larger benchmark.
2. Inter-annotator agreement.
3. Calibration metrics from `answer_certification.py`.
4. UI/ledger reproducibility.
5. Human-final verdict analysis.

## Commercial / Growth Track

### Launch Order

1. Hugging Face demo reliability pass.
2. GitHub README proof kit.
3. Eval4SD draft/preprint page.
4. Hacker News Show HN.
5. Newsletter pitches.
6. Product Hunt only after HN + paper proof.
7. RAISE only if pitch assets and eligibility are ready.

### HN Positioning

Title:

`Show HN: AI Judge - an open-source jury for checking AI claims`

First comment skeleton:

```text
I built AI Judge because I kept seeing AI answers cite real sources while claiming more than the sources actually proved.

It turns one AI answer into a human-final audit flow:
- raw model answer stays unchanged
- cited sources are checked separately
- claim spans are classified against source support
- multiple web-model seats can disagree or ask resonance questions
- the final result gets a replay ledger and certification hash

The current limitation is also part of the project: web-model collection is messy. Some providers time out, some pages keep stale answers, and real source support is not the same as factual truth.

I would love feedback on the protocol and the failure cases.
```

### Product Hunt Positioning

Delay until the demo feels self-explanatory.

Tagline candidates:

1. `AI answers enter a jury. You keep the gavel.`
2. `Check whether AI claims are actually supported.`
3. `A source-isolated audit trail for AI answers.`

Avoid:

1. "Eliminates hallucination."
2. "Truth engine."
3. "Fully automated AI judge."

## Four Resonance Questions

Use these as the next AI Judge jury input:

1. Which paper should be the anchor: Eval4SD claim-support audit, EMNLP browser-collection system paper, or Discover Computing journal extension?
2. What is the smallest benchmark that proves the key insight without pretending to solve all factuality?
3. For HN/Product Hunt, should the first hook be "9 AIs deliberate" or "real citations can still overclaim"? Which creates more qualified GitHub stars?
4. What public artifact would make a skeptical researcher or legal-tech founder willing to collaborate: dataset, protocol spec, demo report, or certification hash?

## 30 / 60 / 90 Day Plan

### Days 1-7

1. Freeze the source-isolation spec.
2. Add 50-case benchmark manifest.
3. Improve Hugging Face demo with 3 sample cases.
4. Turn current web-council failure receipt into a "production evaluation fidelity" appendix.
5. Draft Eval4SD abstract and related work.

### Days 8-14

1. Complete Eval4SD 4-page draft.
2. Run benchmark through current CLI/HF demo.
3. Add two human annotation passes if possible.
4. Publish an anonymized demo report.
5. Prepare HN first comment but do not post yet.

### Days 15-30

1. Submit Eval4SD if OpenReview account is active or organizers provide a backup route.
2. Submit EMNLP Industry Track only if the system paper is coherent by June 10.
3. Post Show HN after demo passes fresh-user test.
4. Submit to The Rundown AI tool form.
5. Open 3 collaboration issues: Legal citation benchmark exchange, RAG citation support taxonomy, provenance receipt integration.

### Days 31-60

1. Expand benchmark to 100 cases.
2. Draft Discover Computing journal version.
3. Prepare Product Hunt assets if HN conversion is healthy.
4. Build claim-span/source UI in the dashboard.
5. Run 5 free AI Decision Audit reports and request permission for anonymized testimonials.

### Days 61-90

1. Submit Discover Computing.
2. Convert the best audit cases into public demo cards.
3. Add paid Pro intake only after 3+ external users have run the demo without handholding.
4. Start legal/provenance partnership outreach using a concrete receipt schema, not a generic pitch.
5. Re-run full web-seat council with a fixed capture validator.

## Scoring

| Dimension | Score | Reason |
|---|---:|---|
| Research publication feasibility | 84/100 | Eval4SD and Discover Computing are strongly aligned with specialized-domain LLM evaluation and LLM-as-evaluator framing. |
| GitHub star growth feasibility | 76/100 | HN + HF demo + research credibility can work, but only if the demo is tryable without setup pain. |
| Commercial feasibility in 90 days | 52/100 | Paid audits are plausible, but only after external proof and 3-5 real use cases. |
| Product Hunt feasibility now | 45/100 | Product is not yet polished enough for a broad maker audience. |
| RAISE feasibility now | 38/100 | Deadline/closing language is internally inconsistent on the official page, and eligibility requires a registered entity and team. |

Final recommendation:

Treat AI Judge as a research-backed trust artifact first, then as a product. The first public promise should be narrow:

`AI Judge checks whether an AI answer's claims are actually supported by its cited sources.`

## Source Ledger

Verified external sources used for this plan:

1. Eval4SD official site: https://eval4sd.github.io/
2. Eval4SD CFP mirror with deadline/contact: https://list.elra.info/mailman3/hyperkitty/list/corpora%40list.elra.info/thread/36PQFXPGXUWWNRHTZB3XB7UGCSNETECC/
3. Discover Computing LLM-as-Evaluator CFP: https://www.aclweb.org/portal/content/cfp-special-issue-large-language-models-evaluators-computing-opportunities-challenges-and
4. RAISE the STAKES 2026: https://www.raisesummit.com/startup-competition
5. HN Show HN guidelines: https://news.ycombinator.com/showhn.html
6. Product Hunt featuring guidelines: https://help.producthunt.com/en/articles/9883485-product-hunt-featuring-guidelines
7. Product Hunt launch guide: https://www.producthunt.com/launch
8. BetaList submission guidelines: https://betalist.com/criteria
9. KDD Agentic AI Evaluation and Trustworthiness workshop: https://kdd-eval-workshop.github.io/agenticai-evaluation-kdd2026/
10. KDD SeT-LLM workshop: https://secure-and-trustworthy-llm.github.io/
11. EMNLP 2026 Industry Track: https://2026.emnlp.org/calls/industry_track/
12. NeurIPS 2026 Evaluations & Datasets Track: https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets
13. The Rundown AI tool submission page: https://www.rundown.ai/submit
14. Ben's Bites Substack: https://www.bensbites.com/
15. Import AI about page: https://jack-clark.net/about/
