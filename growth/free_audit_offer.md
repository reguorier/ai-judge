# Free AI Decision Audit Offer

Status: ready for outreach queue

Slot tracker:

- `growth/free_audit_slots.json`
- `growth/free_audit_status.md`
- `tools/record_free_audit_slot.py`

Intake script:

- `growth/free_audit_intake.md`

## Offer

```text
I am offering 3 free AI Decision Audits in exchange for permission to use an anonymized testimonial or public-safe lesson.
```

## Scope

Accepted input:

- one AI-generated memo
- one AI-generated report
- one product plan
- one investment memo
- one README or research note

Output:

- citation-level status table
- Certification ID
- Replay Ledger hash
- evidence gap queue
- short decision-risk note
- optional anonymized public excerpt

## Boundaries

- No legal, medical, or financial advice.
- No private data published without permission.
- Raw answer, external evidence, and verification output remain separate.
- The report does not rewrite the user's memo.

## CTA

```text
Reply with one AI-generated answer or memo and tell me whether it can be anonymized for a public example.
```

## Tracking Commands

```bash
python3 tools/record_free_audit_slot.py --refresh-only
python3 tools/record_free_audit_slot.py F001 --status reserved --contact O001 --case-type memo --permission pending --note "Interested in legal memo citation audit"
```
