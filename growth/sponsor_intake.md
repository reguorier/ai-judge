# Sponsor Intake

Status: ready_after_inbound_interest

Use this when someone asks how to support AI Judge, fund benchmark work, or sponsor a specific citation-audit workflow.

## First Reply

```text
Thanks for offering to support AI Judge.

Current support options:

- $5/month equivalent: Benchmark Supporter
- $19/month equivalent: Pro Backer
- $99/month equivalent: Decision Audit Sponsor
- one-time support: sponsor one benchmark/report task

GitHub Sponsors is not enabled yet, so the current path is manual: tell me the tier or task you want to support, and I will send the appropriate payment/setup instructions after confirming the fit.

What your support funds:

- citation hallucination benchmark cases
- public demo reports
- GitHub Action citation-audit workflow
- Evidence Broker and Replay Ledger work
- anonymized AI Decision Audit examples
```

## Boundaries

- Do not accept sponsorship for legal, medical, financial, or private-data advice.
- Do not promise feature delivery dates before the roadmap is confirmed.
- Keep benchmark cases public-safe and permissioned.
- Record sponsor interest before sending payment instructions.

## Tracking Commands

```bash
python3 tools/record_sponsor_event.py sponsor_request --tier benchmark-supporter --channel email --note "Asked how to support benchmark work"
python3 tools/record_sponsor_event.py tier_selected --tier pro-backer --channel email --note "Wants to sponsor batch audit"
python3 tools/record_sponsor_event.py payment_intent --tier decision-audit-sponsor --channel email --note "Asked for payment path"
python3 tools/record_sponsor_event.py paid --tier benchmark-supporter --channel manual --amount 5 --note "Manual support received"
```
