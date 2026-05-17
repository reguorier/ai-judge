# Show HN Launch Post: AI Judge Citation Audit

Status: ready for publish confirmation

Target:

```text
https://news.ycombinator.com/submit
```

## Title

```text
Show HN: AI Judge - open-source citation auditor for AI-generated answers
```

## URL

```text
https://github.com/reguorier/ai-judge
```

## First Comment

```text
I built AI Judge Citation Audit because LLM answers increasingly include citations that look real enough to pass a quick read but fail once you separate the model text from external evidence.

The tool is intentionally narrow: paste an AI-generated answer, optionally provide external evidence, and it labels each citation as verified, weakly_verified, irrelevant, unverifiable, or contradicted. It also produces a Certification ID, Replay Ledger hash, and HTML/JSON report.

The important design choice is source isolation: a URL mentioned by the model is treated as a candidate source, not proof. It only upgrades when supplied or fetched as external evidence.

Repo:
https://github.com/reguorier/ai-judge

Hard benchmark cases:
https://github.com/reguorier/ai-judge/issues/2

Live Space:
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

Demo command:
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md --html reports/fake-citation-audit.html --json reports/fake-citation-audit.json

Benchmark:
PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95

I would especially like benchmark cases that fool current LLM citation checks.
```

## Why HN Should Care

- It is narrow enough to try in 60 seconds.
- It has a deterministic benchmark instead of a vague "AI safety" claim.
- It makes a concrete distinction between `unverifiable` and `contradicted`.
- It asks for hard cases, which gives technical readers a clear way to engage.

## Publish Checklist

- Confirm the GitHub README hero screenshot renders.
- Confirm the Hugging Face Space is still running.
- Submit title + repo URL on HN only after click-time confirmation.
- Add the first comment immediately after the post is live.
- Record HN URL in `growth/feedback_log.md`.

## Likely HN Replies

If someone says "this is just regex":

```text
The launch version intentionally keeps the core citation labels deterministic, but the valuable part is not just extraction. It keeps model-mentioned sources separate from external evidence, classifies support strength, seals a Replay Ledger, and produces auditable reports. The model cannot cite a URL and have that URL automatically verify its own claim.
```

If someone says "why not just fetch the URL?":

```text
Fetching is useful, but it is not enough. A fetched page can exist and still be irrelevant, weakly related, or contradicted by the claim. That is why the labels separate source existence from relevance and claim support.
```

If someone asks whether this is a business:

```text
The open-source wedge is citation-level audit. The paid direction, if demand exists, is batch audit for Markdown/PDF/Docx, historical Replay Ledger, and CI/report export for teams that publish AI-generated research or client documents.
```
