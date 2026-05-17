# Free AI Decision Audit Intake

Status: ready_to_send_after_interest

Use this only after a recipient replies with interest, asks for help, or shares a likely citation-quality problem. Do not ask for private documents in public threads.

## Intake Message

```text
Happy to run one free AI Decision Audit.

Please send only material you are allowed to share. A safe input is one AI-generated answer, memo, report excerpt, README, or product plan where the cited evidence matters.

Helpful fields:

1. What decision or claim does the AI answer support?
2. Which citations or sources should be checked?
3. Do you already have external evidence files/links, or should the audit mark missing evidence as `unverifiable`?
4. Can I publish an anonymized lesson or testimonial if the output is useful?

Boundaries:

- I will not publish private data without explicit permission.
- I will preserve the raw model answer instead of rewriting it.
- `unverifiable` means "not enough isolated evidence", not "false".
- This is not legal, medical, or financial advice.
```

## Acceptance Criteria

Accept the case if all are true:

- The user voluntarily supplied or linked the AI-generated text.
- The case has at least one citation, source, evidence claim, or measurable assertion.
- The public-safe version can remove names, companies, private URLs, and sensitive facts.
- The expected output can fit one short AI Decision Audit report.

Decline or request a safer excerpt if any are true:

- The content includes confidential client data, medical data, legal matter details, financial account data, private personal data, or credentials.
- The sender asks for advice instead of audit output.
- The task requires proving truth from scratch rather than auditing supplied claims and evidence.

## Slot Workflow

1. Reserve an open slot:

```bash
python3 tools/record_free_audit_slot.py F001 --status reserved --contact O001 --case-type memo --permission pending --note "Interested in legal memo citation audit"
```

2. Mark input received:

```bash
python3 tools/record_free_audit_slot.py F001 --status input_received --contact O001 --case-type memo --permission pending --note "Input received, private details excluded"
```

3. Mark audit complete:

```bash
python3 tools/record_free_audit_slot.py F001 --status audit_complete --contact O001 --case-type memo --permission pending --report reports/anonymized-example-audit.html --note "Report delivered"
```

4. Mark testimonial permission:

```bash
python3 tools/record_free_audit_slot.py F001 --status testimonial_granted --contact O001 --case-type memo --permission granted --report reports/anonymized-example-audit.html --note "Anonymized quote approved"
```
