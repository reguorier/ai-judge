# Contributing To AI Judge Public Cases

AI Judge is closed-core. This public repository accepts public-safe examples,
benchmark cases, issue feedback, docs fixes, and showcase improvements.

The best contribution is a small failure case that makes the support boundary
clear:

- a fabricated or unverifiable citation,
- a real source that is irrelevant to the generated claim,
- a source that contradicts the generated answer,
- a real source that supports only a weaker claim,
- a batch, PDF, Docx, CI, or report-review workflow that would make the product
  more useful.

## Public-Safe Rule

Do not include private or regulated material in issues or pull requests:

- customer facts,
- raw transcripts,
- browser screenshots,
- credentials,
- cookies,
- API keys,
- private emails,
- legal case payloads,
- local run outputs,
- generated evidence packs.

A sanitized summary is enough. If the case depends on private material, describe
the shape of the failure without publishing the source material.

## Good Benchmark Case Format

Use this shape in an issue or pull request:

```text
Question:
What claim was the AI answer trying to support?

Generated answer:
The short answer text, including the citation or source claim.

Source or evidence:
Public URL, public excerpt, or sanitized evidence summary.

Expected result:
verified / weakly_verified / irrelevant / unverifiable / contradicted

Why:
One or two sentences explaining the gap.
```

For overclaim cases, include the narrower statement the source actually
supports. For example: "The source shows association, but the answer claims
causation."

## Pull Request Checklist

Before opening a pull request:

```bash
python3 scripts/verify_public_snapshot.py
```

Then confirm:

- The case is public-safe.
- The expected label is explicit.
- Links are public and stable enough for a demo.
- No private runtime, browser, client, bridge, growth, or local artifact files
  are included.
- The public/private boundary in `docs/PUBLIC_PRIVATE_BOUNDARY.md` still holds.

## What Not To Contribute

Do not add production runtime code, browser automation, model-seat adapters,
customer workflows, account-specific traces, private growth notes, or
commercial orchestration logic to this repository.
