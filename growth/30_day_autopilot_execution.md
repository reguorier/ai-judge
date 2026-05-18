# AI Judge 30-Day Autopilot Execution Table

This is the execution track for turning the Citation Audit launch into public proof, usage, and a first paid signal. It assumes the product stays narrow: citation-level verification, source isolation, Certification ID, Replay Ledger, and reproducible reports.

## Current Public Assets

| Asset | Status | URL or command |
|---|---|---|
| Hugging Face Space | Live, sample switcher prepared | https://huggingface.co/spaces/reguorier/ai-judge-citation-audit |
| GitHub release | Live signed artifact v3.6.0; source/docs v3.7.0 | https://github.com/reguorier/ai-judge/releases/tag/v3.6.0 |
| Local demo | Live | `PYTHONPATH=. python cli/main.py audit examples/fake-citation.md --html reports/fake-citation-audit.html --json reports/fake-citation-audit.json` |
| Benchmark | Live | `PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95` |
| Launch copy | Drafted | `growth/launch_posts.md` |
| Hugging Face post | Blocked by hCaptcha, draft retained | `growth/huggingface_community_post.md` |
| Show HN post | Blocked by current account restriction, draft retained | `growth/show_hn_launch_post.md` |
| Reddit r/LocalLLaMA post | Posted, then removed by moderation | `growth/reddit_localllama_launch_post.md` |
| Feedback log | Started | `growth/feedback_log.md` |
| Reply bank | Drafted | `growth/reply_bank.md` |
| Email sequence | Drafted | `growth/email_sequence.md` |
| Demo report gallery | Live | `docs/CITATION_AUDIT_QUICKSTART.md`, `docs/LAUNCH_CITATION_AUDIT.md` |
| GitHub issue queue | Live | https://github.com/reguorier/ai-judge/issues/2 |
| V2EX post | Abandoned until invite/activation exists | `growth/v2ex_launch_post.md` |
| Zhihu long-form post | Live | https://zhuanlan.zhihu.com/p/2039446444000665819 |
| X / short thread | Live | https://x.com/liuweidi2/status/2055973517779521750 |
| X professional review wave | Posted, cleanup pending | `growth/x_professional_wave_001.md` |
| Quote-card layouts | Ready | `product/social_quote_cards.html` |
| Blog draft | Ready | `docs/AI_COLLECTIVE_BLIND_SPOTS_BLOG.md` |
| Blog outline | Archived planning aid | `docs/AI_COLLECTIVE_BLIND_SPOTS_BLOG_OUTLINE.md` |
| Hard benchmark | Added | `PYTHONPATH=. python tools/run_citation_bench.py --bench citation-bench/citation-bench-hard-11.jsonl --fail-under 0.95` |
| Batch audit MVP | Implemented | `ai-judge audit-batch`, `core/citation_batch.py`, `docs/BATCH_AUDIT_SPEC.md` |
| GitHub Action batch mode | Implemented | `.github/actions/citation-audit/action.yml`, `.github/workflows/citation-audit.yml`, `docs/GITHUB_ACTION_CITATION_AUDIT.md` |
| AI Decision Audit sample | Ready | `docs/AI_DECISION_AUDIT_SAMPLE.md` |
| Outreach queue | Batch 001 partly sent, follow-ups gated | `growth/outreach_batch_001.md`, `growth/outreach_mailto_links.md`, `growth/outreach_status.md` |
| Free audit offer | Ready | `growth/free_audit_offer.md` |
| Free audit slots | Ready | `growth/free_audit_slots.json`, `growth/free_audit_status.md` |
| Anonymized audit permission | Ready | `growth/anonymized_audit_permission_request.md` |
| Pro early-access page | Ready | `product/pro_early_access.html` |
| Pro interest tracker | Ready | `growth/pro_interest_status.md`, `tools/record_pro_interest.py` |
| GitHub Sponsors copy | Manual sponsor path ready | `docs/GITHUB_SPONSORS.md`, `.github/FUNDING.yml`, `growth/sponsor_status.md` |
| Unverifiable explainer | Ready | `docs/UNVERIFIABLE_IS_NOT_FALSE.md` |
| Metrics dashboard | Ready | `growth/metrics_dashboard.md` |
| Day 30 decision memo | Ready | `growth/day30_decision.md` |
| Follow-up queue | Ready for confirmation | `growth/followup_queue.md` |
| Resonance Wave 002 | Prepared, not sent | `growth/resonance_wave_002.md`, `docs/PAPER_SEED_SOURCE_ISOLATED_CITATION_AUDIT.md`, `docs/EVAL4SD_2026_SOURCE_ISOLATED_CITATION_AUDIT_DRAFT.md` |
| Claim-support audit | Implemented MVP | `core/claim_support.py`, `docs/CLAIM_SUPPORT_AUDIT_SPEC.md` |
| Resonance Wave 003 | Eval4SD OpenReview packet pushed / profile activation pending / taxonomy issues posted | `growth/resonance_wave_003_eval_taxonomy_infra.md`, `papers/eval4sd2026/openreview_submission.md` |
| Resonance Wave 004 | RAGChecker taxonomy issue posted | `growth/resonance_wave_004_refchecker_claim_audit.md` |

## Rules

- The public promise is citation audit, not full Grand Judge automation.
- `unverifiable` must be explained as "not enough isolated evidence", not "false".
- Model text, mentor additions, and external evidence stay separate.
- Public posts ask for benchmark cases first, not money first.
- Any final external send/post action needs a final click-time confirmation.

## Days 1-7: Make It Easy To Try

| Day | Automated action | Success signal |
|---:|---|---|
| 1 | Add live Space link to README, launch plan, posts, and email sequence. | A new visitor can try the Space before installing. |
| 2 | Produce one screenshot/GIF from the Space default audit and add it to README/social kit. | README has visual proof of output. |
| 3 | Publish/prepare Hugging Face Community post from `growth/launch_posts.md`. | First public feedback loop starts. |
| 4 | Prepare Show HN post and first comment with Space + repo + benchmark ask. | HN launch is one confirmation away. |
| 5 | Prepare Reddit r/LocalLLaMA post and 5 reply-bank answers. | Reddit launch is one confirmation away. |
| 6 | Create three reproducible demo report pages from the examples and link them from docs. | Users can inspect reports without running code. |
| 7 | Create GitHub issues labelled `good first benchmark case` and `citation audit feedback`. | Contributors know how to help. |

## Days 8-14: Launch To Communities

| Day | Automated action | Success signal |
|---:|---|---|
| 8 | Publish Hugging Face Community post after confirmation. | 1 public thread exists on HF. |
| 9 | Publish Show HN after confirmation. | HN feedback collected. |
| 10 | Publish r/LocalLLaMA after confirmation. | Reddit feedback collected. |
| 11 | Publish V2EX Chinese post after confirmation. | Chinese dev feedback collected. |
| 12 | Package X/short-post thread and 3 quote-card screenshots. | Short-form launch ready. |
| 13 | Create a "9 AI collective blind spot" blog outline using current examples. | Blog draft ready. |
| 14 | Summarize all feedback into `growth/feedback_log.md`. | Roadmap is driven by real objections. |

## Days 15-21: Convert Feedback Into Proof

| Day | Automated action | Success signal |
|---:|---|---|
| 15 | Add 10 contributed or synthetic hard citation cases. | Benchmark improves. |
| 16 | Add batch audit design spec for Markdown/PDF/Docx. | Paid feature has exact scope. |
| 17 | Add GitHub Action usage example with a failing fake citation fixture. | CI value is obvious. |
| 18 | Build a sample "AI Decision Audit" report from `product-no-evidence`. | Service offer has a concrete deliverable. |
| 19 | Convert outreach from generic segments into a real first-send batch for legal AI, eval tooling, hallucination tooling, and research targets. | `growth/outreach_batch_001.md` exists with target-specific drafts and status fields. |
| 20 | Create landing section for Pro early access and manual payment instructions. | First paid signal can be captured. |
| 21 | Update README with feedback-driven FAQ. | Common objections answered publicly. |

## Days 22-30: Ask For Money Or Stop

| Day | Automated action | Success signal |
|---:|---|---|
| 22 | Send first warm outreach batch from `growth/outreach_batch_001.md` through the available mailbox/channel. | 5 replies or 1 call target. |
| 23 | Offer 3 free AI Decision Audits for testimonial use, tracked by slot state. | `growth/free_audit_status.md` shows open/reserved/completed/testimonial slots. |
| 24 | Add one real anonymized audit report if permission exists. | Trust proof increases. |
| 25 | Launch Pro early-access page at $49 lifetime for first 100 users, with structured workflow-intent tracking. | `growth/pro_interest_status.md` can count requests, payment intent, invoices, paid events, and license sends. |
| 26 | Add GitHub Sponsors copy, README sponsor section, and manual sponsor-intent tracking until GitHub Sponsors is enabled. | `growth/sponsor_status.md` can count sponsor requests, tier selection, payment intent, and paid events. |
| 27 | Follow up with interested users after confirmation. | Paid/feedback signal gathered. |
| 28 | Publish "unverifiable is not false" explainer. | Core concept becomes memorable. |
| 29 | Compile metrics: stars, Space visits, replies, issues, emails, paid signals. | Stop/go data exists. |
| 30 | Decide: continue Pro, pivot demo story, or pause monetization. | No vague momentum. |

## Stop/Go Thresholds

Continue building Pro only if at least one is true by Day 30:

- 100 GitHub stars.
- 20 distinct users run the demo, star, open an issue, reply, or ask for help.
- 3 users request batch/PDF/GitHub Action Pro features.
- 1 user pays or asks for an invoice.

If none are true, pause monetization and improve the demo story before adding more features.

## Completion Snapshot

Automated and reversible work is complete through Day 30:

- Public copy is drafted for Hugging Face, Show HN, Reddit, V2EX, Zhihu, short-form posts, replies, and follow-ups.
- The demo package includes six reproducible reports, the default 100-case benchmark, and a hard 11-case launch benchmark.
- Pro demand capture is ready through `product/pro_early_access.html`, `docs/PRO_EARLY_ACCESS.md`, `docs/GITHUB_SPONSORS.md`, and `.github/FUNDING.yml`.
- Paid-feature scope is constrained to batch audit, GitHub Action batch mode, history ledger, and network-backed Evidence Broker.
- Stop/go evaluation is centralized in `growth/metrics_dashboard.md` and `growth/day30_decision.md`.

External launch follow-up status:

- X is live: https://x.com/liuweidi2/status/2055973517779521750
- Zhihu is live: https://zhuanlan.zhihu.com/p/2039446444000665819
- Reddit r/LocalLLaMA was posted, then removed by moderation: https://www.reddit.com/r/LocalLLaMA/comments/1tfohfv/
- Hacker News is blocked by the current Show HN account restriction page: https://news.ycombinator.com/showlim
- V2EX is logged in but abandoned for this launch cycle because no activation code is available: https://www.v2ex.com/invite/activate
- Hugging Face Community is logged in and email-confirmed, but discussion creation is blocked by repeated hCaptcha challenges: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit/discussions/new
- Direct outreach Batch 001 is prepared with real targets and tailored drafts: `growth/outreach_batch_001.md`

GitHub issues #2-#5 are live, v3.7.0 source/docs are pushed, and the next automated public action should favor replies to relevant conversations, low-friction GitHub improvements, and direct outreach rather than repeated reposting of the same launch copy.

Research-first next wave:

- Eval4SD short/position paper path is the priority venue; the anonymous LaTeX/PDF packet and OpenReview form packet now live in `papers/eval4sd2026/`, and the actual upload is blocked only by pending OpenReview profile activation.
- HalluCiteChecker and LegalCiteBench are the priority taxonomy-exchange targets.
- Aequis and Ligate are the priority infrastructure/commercial-collaboration targets.
- The technical wedge is claim-span/source audit: citation verification, source relevance, and exact claim support are separated so "real source" does not become "proven conclusion."
- RAGChecker is now the active claim-level / RAG-faithfulness taxonomy route because RefChecker is archived/read-only.
