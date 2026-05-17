# Anonymized Audit Permission Request

Status: ready for Day 24 use

Use this only after someone voluntarily shares an AI-generated answer, memo, README, or report.

## Permission Ask

```text
Thanks for sharing this example.

Can I use an anonymized version as a public AI Judge Citation Audit example?

I would remove names, company details, private URLs, and sensitive facts. The public version would only show:

- the AI-generated answer pattern
- citation-level verification labels
- the Replay Ledger / Certification ID format
- what evidence was missing or contradicted

I will not publish private data, private documents, or identifying context without your explicit approval.
```

## If Permission Is Granted

Create:

- `examples/anonymized-<topic>.md`
- `reports/anonymized-<topic>-audit.html`
- `reports/anonymized-<topic>-audit.json`
- a short note in `growth/feedback_log.md`

## If Permission Is Not Granted

Keep only the lesson:

```text
Pattern observed: <one-sentence anonymized pattern>
Action: add synthetic benchmark case that captures the failure mode without private details.
```
