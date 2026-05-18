# Day 30 Stop / Go Decision

Status: active decision template
Last refreshed: 2026-05-18 22:04 HKT

## Inputs

Primary source files:

- `growth/metrics_dashboard.md`
- `growth/outreach_status.md`
- `growth/free_audit_status.md`
- `growth/pro_interest_status.md`
- `growth/sponsor_status.md`

| Signal | Threshold | Actual | Pass |
|---|---:|---:|---|
| GitHub stars | 100 | 3 | No |
| Distinct users / replies / issues | 20 | 5 open repo issues + 2 substantive external replies + 2 taxonomy issues pending | Not yet |
| Pro requests | 3 | 0 | No |
| Paid users, invoice requests, or manual sponsor support | 1 | 0 | No |

## Pro signal interpretation

- `request`: counts toward Pro requests.
- `payment_intent`: counts as stronger than request, but not paid.
- `invoice_requested`: counts toward the paid/invoice threshold.
- `paid`: counts toward paid users and paid total.
- `license_sent`: confirms fulfillment after payment.

## Decision options

### Continue Pro

Choose this if at least one threshold is met.

Next actions:

- build batch Markdown audit
- wire Pro license checks
- connect Lemon Squeezy or Stripe Payment Links
- publish PDF/Docx parser roadmap

### Pivot demo story

Choose this if there is attention but no Pro intent.

Next actions:

- publish stronger "9 AI collective blind spots" blog
- add 20 harder benchmark cases
- create more visual before/after examples
- compare against RAG eval tools

### Pause monetization

Choose this if there is no meaningful usage signal.

Next actions:

- stop building billing
- improve one killer demo
- focus on GitHub Action and benchmark quality

## Default decision

If unsure, choose Pivot Demo Story. It preserves learning without pretending there is paid demand.

## Current Lean

As of 2026-05-18, the strongest signal is not paid demand yet. The strongest signal is research/community fit around the claim-span/source boundary:

- Eval4SD organizer fit is positive.
- Article 11 / governance feedback produced the real-source-overclaimed-causation benchmark case.
- LegalCiteBench and RAGChecker taxonomy issues are live and awaiting replies.

Keep monetization capture available, but spend the next automatable cycle on submission completion, benchmark credibility, and reply conversion before adding billing complexity.
