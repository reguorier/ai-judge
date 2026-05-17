# AI Judge 30-Day Autopilot Execution Table

This is the execution track for turning the Citation Audit launch into public proof, usage, and a first paid signal. It assumes the product stays narrow: citation-level verification, source isolation, Certification ID, Replay Ledger, and reproducible reports.

## Current Public Assets

| Asset | Status | URL or command |
|---|---|---|
| Hugging Face Space | Live, default demo verified | https://huggingface.co/spaces/reguorier/ai-judge-citation-audit |
| GitHub release | Live | https://github.com/reguorier/ai-judge/releases/tag/v3.6.0 |
| Local demo | Live | `PYTHONPATH=. python cli/main.py audit examples/fake-citation.md --html reports/fake-citation-audit.html --json reports/fake-citation-audit.json` |
| Benchmark | Live | `PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95` |
| Launch copy | Drafted | `growth/launch_posts.md` |
| Hugging Face post | Ready for confirmation | `growth/huggingface_community_post.md` |
| Show HN post | Ready for confirmation | `growth/show_hn_launch_post.md` |
| Feedback log | Started | `growth/feedback_log.md` |
| Reply bank | Drafted | `growth/reply_bank.md` |
| Email sequence | Drafted | `growth/email_sequence.md` |

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
| 19 | Draft outreach email to 20 likely users: AI newsletters, legal-tech, research ops, devtools. | Outreach queue ready. |
| 20 | Create landing section for Pro early access and manual payment instructions. | First paid signal can be captured. |
| 21 | Update README with feedback-driven FAQ. | Common objections answered publicly. |

## Days 22-30: Ask For Money Or Stop

| Day | Automated action | Success signal |
|---:|---|---|
| 22 | Send first warm outreach batch after confirmation. | 5 replies or 1 call target. |
| 23 | Offer 3 free AI Decision Audits for testimonial use. | Testimonials pipeline starts. |
| 24 | Add one real anonymized audit report if permission exists. | Trust proof increases. |
| 25 | Launch Pro early-access page at $49 lifetime for first 100 users. | Payment intent is testable. |
| 26 | Add GitHub Sponsors copy and README sponsor section. | Donation path exists. |
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
