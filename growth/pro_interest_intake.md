# Pro Early Access Intake

Status: ready_after_inbound_interest

Use this when someone replies to the Pro early-access CTA or asks whether batch/PDF/Docx/GitHub PR audit is available.

## First Reply

```text
Thanks. I am validating Pro before building billing infrastructure.

The early-access offer is $49 lifetime for the first 100 users. The first paid workflows are:

- batch Markdown audit
- PDF/Docx parser roadmap access
- GitHub Action advanced mode
- Evidence Broker network mode
- historical Replay Ledger
- exportable Certification ID reports

To make sure I build the right version first, which workflow do you need most?

1. Markdown batch
2. PDF
3. Docx
4. GitHub PR / CI
5. Other

If you want the early slot, reply with "reserve Pro" and the workflow above. I will send manual payment instructions only after confirming the fit.
```

## Manual Payment Fit Check

Ask these before taking payment:

- Is the user auditing their own content or content they are allowed to process?
- Which file type/workflow comes first?
- Do they need local-only mode, network evidence fetching, or CI gating?
- Are they buying early-access software, not legal/medical/financial advice?

## Tracking Commands

```bash
python3 tools/record_pro_interest.py request --workflow markdown-batch --channel email --note "Asked about batch Markdown"
python3 tools/record_pro_interest.py payment_intent --workflow pdf --channel email --note "Asked for payment instructions"
python3 tools/record_pro_interest.py invoice_requested --workflow github-ci --channel email --note "Needs invoice"
python3 tools/record_pro_interest.py paid --workflow markdown-batch --channel manual --amount 49 --note "Manual payment received"
python3 tools/record_pro_interest.py license_sent --workflow markdown-batch --channel email --note "License/setup instructions sent"
```
