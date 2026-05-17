# Citation Audit Pro Early Access

## Offer

AI Judge Citation Audit Pro is a $49 lifetime early-access offer for the first 100 users.

It is for people who need to audit more than one answer or document at a time.

## Included

- batch Markdown audit
- Evidence Broker network fetch mode
- historical Replay Ledger
- GitHub Action advanced mode
- exportable Certification ID reports
- PDF/Docx parser roadmap access

## Manual purchase path

Until a payment provider is connected:

1. User emails `reguorider@gmail.com`.
2. User states the primary workflow: Markdown, PDF, Docx, GitHub PR, or other.
3. User receives manual payment instructions.
4. First users get a manual early-access license key or private setup support.

Landing page:

```text
product/pro_early_access.html
```

Demand tracking:

```text
growth/pro_interest_events.jsonl
growth/pro_interest_status.md
tools/record_pro_interest.py
growth/pro_interest_intake.md
```

Record inbound interest:

```bash
python3 tools/record_pro_interest.py request --workflow markdown-batch --channel email --note "Asked about batch Markdown"
python3 tools/record_pro_interest.py payment_intent --workflow pdf --channel email --note "Asked for payment instructions"
python3 tools/record_pro_interest.py paid --workflow markdown-batch --channel manual --amount 49 --note "Manual payment received"
```

## Stop condition

Do not build custom billing infrastructure until at least one of these is true:

- one purchase
- three Pro requests
- one launch post drives more than 20 trial runs
