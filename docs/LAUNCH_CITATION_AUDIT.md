# AI Judge Citation Audit Launch Plan

## Positioning

AI Judge Citation Audit is an open-source, local-first auditor for AI-generated citations. It catches fabricated, weak, irrelevant, unverifiable, and contradicted citations before a report, paper, README, or client deliverable is published.

## User promise

Paste one AI-generated answer, optionally add external evidence, and get:

- citation-level status: `verified`, `weakly_verified`, `irrelevant`, `unverifiable`, `contradicted`
- Certification ID
- Replay Ledger hash
- Evidence Broker source separation
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
