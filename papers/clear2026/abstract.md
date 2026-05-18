# CLEAR 2026 Abstract Variant

Status: draft, not submitted
Target route: https://clear-ws.github.io/2026/
Contact route: `themis.xanthopoulou@umu.se`
Last refreshed: 2026-05-19

## Working Title

```text
Real Citation, Wrong Proposition: Source-Isolated Claim-Support Audit for Legal LLM Outputs
```

## Position

Legal and compliance-facing LLM systems need a distinction that ordinary
citation validation often hides: a real case, statute, paper, or regulation can
be cited correctly while the generated legal proposition is not supported by
that authority.

## Draft Abstract

```text
Legal LLM failures are often discussed as citation hallucination, but a harder
failure remains after bibliographic validation succeeds: the cited authority is
real and topically relevant, while the generated proposition overstates or
misstates what the authority supports. We propose source-isolated claim-support
audit for legal and compliance-facing LLM outputs. The protocol keeps three
layers separate: the raw model answer, independently collected external
evidence, and audit verdict metadata. It reports citation existence, source
relevance, and exact claim support independently, with failure codes for cases
such as causation overclaims, absolute overclaims, and quantified overclaims.
AI Judge Citation Audit instantiates the protocol as a local-first tool that
emits human-readable reports, automation-friendly JSON, certification IDs, and
replay-ledger hashes. We present a deterministic benchmark and hard cases
showing why a verified citation should not be treated as a verified legal
conclusion. The work is intended as a practical audit layer for legal NLP,
computational law, and governance workflows that must preserve evidence
provenance.
```

## Fit Rationale

- CLEAR is a strong route for the legal/computational-law framing.
- The contribution is not "another legal chatbot"; it is a reusable audit atom:
  claim span plus source.
- The paper can reuse the public hard cases without exposing private outreach
  or third-party email content.

## Next Action

Prepare a short paper outline from the Eval4SD packet and send the CLEAR
fit-check draft from `growth/submission_council_2026.md` only after action-time
confirmation.
