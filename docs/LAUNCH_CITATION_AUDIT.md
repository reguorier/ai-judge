# AI Judge Citation Audit Launch Plan

## Positioning

AI Judge Citation Audit is a source-available, local-first auditor for AI-generated citations. It catches fabricated, weak, irrelevant, unverifiable, and contradicted citations before a report, paper, README, or client deliverable is published.

## User promise

Paste one AI-generated answer, optionally add external evidence, and get:

- citation-level status: `verified`, `weakly_verified`, `irrelevant`, `unverifiable`, `contradicted`
- `unverifiable` reason codes for missing evidence, fetch failures, blocked retrieval, and unfetched model candidates
- evidence provenance grades: `model_candidate`, `user_supplied`, `fetched`, `independently_attested`, `notarized`
- Certification ID
- Replay Ledger hash
- Evidence Broker source separation

The current MVP is citation-level. The legal/audit roadmap moves toward `claim-span + source`, so a real citation can be separated from an overclaimed model assertion.
- HTML and JSON report artifacts

## Live self-serve demo

Hugging Face Space:

```text
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

The Space runs the citation audit path without requiring model APIs or browser bridges. The default sample is intentionally suspicious and should return `unverifiable`, not `verified`.

## 60-second local demo

```bash
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md \
  --html reports/fake-citation-audit.html \
  --json reports/fake-citation-audit.json
```

## Three launch demos

| Demo | Input | Report | Story |
|---|---|---|---|
| Fake citation | [`examples/fake-citation.md`](../examples/fake-citation.md) | [`reports/fake-citation-audit.html`](../reports/fake-citation-audit.html) / [`json`](../reports/fake-citation-audit.json) | The model cites a plausible institution but the isolated evidence does not verify the named report. |
| Product plan without evidence | [`examples/product-no-evidence.md`](../examples/product-no-evidence.md) | [`reports/product-no-evidence-audit.html`](../reports/product-no-evidence-audit.html) / [`json`](../reports/product-no-evidence-audit.json) | The model recommends a three-month rewrite without evidence for the promised defect reduction. |
| Sounds smart, low judgment | [`examples/sounds-smart-low-judgment.md`](../examples/sounds-smart-low-judgment.md) | [`reports/sounds-smart-low-judgment-audit.html`](../reports/sounds-smart-low-judgment-audit.html) / [`json`](../reports/sounds-smart-low-judgment-audit.json) | The answer sounds like investor prose but fails to ground the key memo and moat claims. |
| Legal memo contradicted | [`examples/legal-memo-contradicted.md`](../examples/legal-memo-contradicted.md) | [`reports/legal-memo-contradicted-audit.html`](../reports/legal-memo-contradicted-audit.html) / [`json`](../reports/legal-memo-contradicted-audit.json) | The cited benchmark directly warns against the answer's unsupervised legal-review claim. |
| Open-source README irrelevant | [`examples/opensource-readme-irrelevant.md`](../examples/opensource-readme-irrelevant.md) | [`reports/opensource-readme-irrelevant-audit.html`](../reports/opensource-readme-irrelevant-audit.html) / [`json`](../reports/opensource-readme-irrelevant-audit.json) | The URL exists but points to editor key-map material, not the claimed PDF audit API. |

## Public launch queue

| Channel | Copy |
|---|---|
| Hugging Face Community | [`growth/huggingface_community_post.md`](../growth/huggingface_community_post.md) |
| Show HN | [`growth/show_hn_launch_post.md`](../growth/show_hn_launch_post.md) |
| Reddit r/LocalLLaMA | [`growth/reddit_localllama_launch_post.md`](../growth/reddit_localllama_launch_post.md) |
| V2EX | [`growth/v2ex_launch_post.md`](../growth/v2ex_launch_post.md) |
| Zhihu / Chinese long-form | [`growth/zhihu_launch_post.md`](../growth/zhihu_launch_post.md) |
| X / short thread | [`growth/x_short_thread.md`](../growth/x_short_thread.md) |
| Quote cards | [`product/social_quote_cards.html`](../product/social_quote_cards.html) |
| Blog draft | [`docs/AI_COLLECTIVE_BLIND_SPOTS_BLOG.md`](AI_COLLECTIVE_BLIND_SPOTS_BLOG.md) |
| Blog outline | [`docs/AI_COLLECTIVE_BLIND_SPOTS_BLOG_OUTLINE.md`](AI_COLLECTIVE_BLIND_SPOTS_BLOG_OUTLINE.md) |
| Follow-up queue | [`growth/followup_queue.md`](../growth/followup_queue.md) |

## Conversion assets

| Asset | Role |
|---|---|
| [`docs/PRO_EARLY_ACCESS.md`](PRO_EARLY_ACCESS.md) | $49 lifetime early-access offer and manual purchase path |
| [`product/pro_early_access.html`](../product/pro_early_access.html) | Static Pro page for self-serve interest |
| [`docs/BATCH_AUDIT_SPEC.md`](BATCH_AUDIT_SPEC.md) | Paid feature scope: batch Markdown first, PDF/Docx later |
| [`docs/GITHUB_ACTION_CITATION_AUDIT.md`](GITHUB_ACTION_CITATION_AUDIT.md) | CI integration story for docs and PRs |
| [`docs/AI_DECISION_AUDIT_SAMPLE.md`](AI_DECISION_AUDIT_SAMPLE.md) | Sample report for the audit-service offer |
| [`growth/free_audit_offer.md`](../growth/free_audit_offer.md) | Free audit offer for testimonial collection |
| [`growth/anonymized_audit_permission_request.md`](../growth/anonymized_audit_permission_request.md) | Day-24 template for turning a real shared case into a public-safe report |
| [`growth/outreach_targets.md`](../growth/outreach_targets.md) | 20-target outreach list |
| [`docs/GITHUB_SPONSORS.md`](GITHUB_SPONSORS.md) | Sponsor tiers and README copy |
| [`growth/metrics_dashboard.md`](../growth/metrics_dashboard.md) | Day-30 stop/go tracking |

## Benchmark expansion

```bash
PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95
PYTHONPATH=. python tools/run_citation_bench.py \
  --bench citation-bench/citation-bench-hard-11.jsonl \
  --fail-under 0.95
```

## Public contribution funnel

| Issue | Purpose |
|---|---|
| https://github.com/reguorier/ai-judge/issues/2 | Collect hard citation hallucination benchmark cases. |
| https://github.com/reguorier/ai-judge/issues/3 | Improve the boundary between `unverifiable` and `contradicted`. |
| https://github.com/reguorier/ai-judge/issues/4 | Validate batch Markdown/PDF/Docx Pro demand before implementation. |
| https://github.com/reguorier/ai-judge/issues/5 | Add more public-safe examples to the demo gallery. |

## Growth targets

These are operating targets, not promises:

- Day 0: public Space live and verified with the default `unverifiable` sample.
- Day 7: public README, demo reports, benchmark, GitHub Action, Space link, and launch copy ready.
- Day 14: Show HN, Reddit, HuggingFace Community, V2EX, Zhihu, X thread published.
- Day 30: first self-serve Pro sale or a clear stop/go signal from activation data.

## Stop/go signal

Continue building Pro only if at least one of these happens within 30 days:

- 100 GitHub stars.
- 20 distinct users run the demo or ask for help.
- 3 users request batch/PDF/GitHub Action Pro features.
- 1 user pays for early access.

If none happen, pause monetization and focus on a better demo story.
