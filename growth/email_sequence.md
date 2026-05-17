# AI Judge Citation Audit Email Sequence

## Audience

Developers, researchers, newsletter writers, legal-tech builders, and AI product teams who publish AI-generated analysis with citations.

## Email 1: Launch

Subject:

```text
Open-source citation audit for AI-generated answers
```

Body:

```text
Hi {{name}},

I am launching AI Judge Citation Audit, a local-first tool that checks AI-generated answers for fabricated, weak, irrelevant, unverifiable, and contradicted citations.

The narrow use case is simple: before you publish an AI-generated report, README, paper draft, or client memo, run the citations through an audit that keeps model text and external evidence separate.

Repo: https://github.com/reguorier/ai-judge
Live demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Demo:
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md --html reports/fake-citation-audit.html

I am collecting hard benchmark cases. If you have seen an AI answer invent or misuse a citation, I would love to add an anonymized version to the benchmark.

Best,
{{sender}}
```

## Email 2: Follow-up after interest

Subject:

```text
Example report: unverifiable is not false
```

Body:

```text
Hi {{name}},

One design detail that matters: AI Judge does not mark missing evidence as false.

It returns `unverifiable` when the audit cannot validate a citation from isolated external evidence. It returns `contradicted` only when supplied evidence explicitly refutes the citation or claim.

That distinction is useful when reviewing AI-generated work because it separates "we cannot trust this yet" from "this is wrong."

If you want to test it, send me one AI answer with citations or run the local demo:
PYTHONPATH=. python cli/main.py audit examples/product-no-evidence.md --html reports/product-no-evidence-audit.html

Browser demo:
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

## Email 3: Pro early access

Subject:

```text
Early access: batch citation audit
```

Body:

```text
Hi {{name}},

I am opening a small early-access group for Citation Audit Pro.

Planned Pro features:
- batch Markdown/PDF/Docx audit
- historical Replay Ledger
- Evidence Broker network fetches
- GitHub Action advanced mode
- exportable Certification ID reports

The early price will be $49 lifetime for the first 100 users. I am only sending this to people who have already shown interest in citation auditing.

If that would be useful, reply with the file type you most need audited first: Markdown, PDF, Docx, or GitHub PRs.
```
