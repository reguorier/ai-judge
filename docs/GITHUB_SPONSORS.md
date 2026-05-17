# GitHub Sponsors Copy

## Short description

```text
Support AI Judge, an open-source citation auditor that catches fabricated, weak, irrelevant, unverifiable, and contradicted citations in AI-generated answers.
```

## Sponsor tiers

### $5/month - Benchmark Supporter

Helps maintain citation hallucination benchmark cases and public demo reports.

### $19/month - Pro Backer

Supports batch audit, GitHub Action integration, and Evidence Broker development.

### $99/month - Decision Audit Sponsor

Funds real-world citation audit examples, anonymized reports, and documentation for teams that publish AI-generated work.

## README copy

```markdown
## Support

AI Judge Citation Audit is open source. Sponsorship helps maintain benchmark cases, demo reports, and CI integrations for citation-quality review.

Sponsor or request Pro early access:

- GitHub Sponsors: coming soon
- Pro Early Access: product/pro_early_access.html
- Contact: reguorider@gmail.com
```

## Current status

GitHub Sponsors is not enabled for the account yet. Until it is enabled, use the manual sponsor path and record every signal in:

```text
growth/sponsor_events.jsonl
growth/sponsor_status.md
tools/record_sponsor_event.py
growth/sponsor_intake.md
```

## Manual sponsor path

```text
Subject: AI Judge sponsorship

Hi,

I want to support AI Judge Citation Audit.

Tier or task:
- Benchmark Supporter
- Pro Backer
- Decision Audit Sponsor
- one-time benchmark/report support

What I want to fund:

```

Record the signal:

```bash
python3 tools/record_sponsor_event.py sponsor_request --tier benchmark-supporter --channel email --note "Asked how to support benchmark work"
python3 tools/record_sponsor_event.py paid --tier benchmark-supporter --channel manual --amount 5 --note "Manual support received"
```

## Enable GitHub Sponsors later

Only after the account is accepted into GitHub Sponsors:

1. Uncomment the `github: [reguorier]` line in `.github/FUNDING.yml`.
2. Replace "GitHub Sponsors: coming soon" in README with the live sponsor link.
3. Record `payment_intent` or `paid` events in `growth/sponsor_events.jsonl` when sponsors arrive.
