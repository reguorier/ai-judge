# Outreach Queue

Status: ready for send queue, not sent

The first outreach batch asks for benchmark cases, not payment. Payment is introduced only after interest.

## Target list

| # | Segment | Target type | Why they might care | Ask |
|---:|---|---|---|---|
| 1 | AI newsletter | Newsletter author covering LLM reliability | Readers see citation hallucinations. | Request a benchmark case. |
| 2 | AI newsletter | Research roundup curator | Publishes source-heavy AI summaries. | Ask for fake citation examples. |
| 3 | Legal-tech | Legal AI builder | Citations matter in memos and diligence. | Ask for anonymized bad citation pattern. |
| 4 | Legal-tech | Contract review startup | Needs source traceability. | Ask if Docx/PDF audit is useful. |
| 5 | Research ops | University lab manager | AI paper drafts contain references. | Ask for benchmark contribution. |
| 6 | Research ops | Independent researcher | Publishes AI-assisted essays. | Ask for unverifiable examples. |
| 7 | Devtools | CI/testing maintainer | GitHub Action integration is concrete. | Ask whether CI report format fits. |
| 8 | Devtools | LLM eval framework maintainer | Complementary narrow benchmark. | Ask for comparison feedback. |
| 9 | VC | Analyst producing memos | Investment memos are citation-heavy. | Offer free audit of one memo. |
| 10 | VC | Scout or angel | Needs quick falsification of AI research. | Ask for one fake-source case. |
| 11 | AI safety | Hallucination researcher | Citation hallucination is measurable. | Ask for edge-case benchmark. |
| 12 | AI safety | Red-team community organizer | Needs public reproducible cases. | Ask for adversarial examples. |
| 13 | Open-source | README/docs maintainer | AI-generated docs can cite nonexistent APIs. | Ask for README citation failure. |
| 14 | Open-source | Maintainer using AI docs | Wants CI guardrail. | Ask whether GitHub Action helps. |
| 15 | Product ops | PM writing AI-assisted specs | Specs include claims and metrics. | Ask for product-no-evidence case. |
| 16 | Product ops | Growth analyst | Reports cite benchmarks. | Ask for unsupported benchmark claim. |
| 17 | Journalism | Data journalist | Source quality matters. | Ask for citation misuse pattern. |
| 18 | Journalism | Fact-checker | Distinguishes unverifiable from false. | Ask for label feedback. |
| 19 | Education | AI writing instructor | Students submit AI-cited work. | Ask for classroom use case. |
| 20 | Education | Librarian / research skills lead | Teaches citation evaluation. | Ask for benchmark cases. |

## Email 1 template

```text
Subject: Open-source citation audit for AI-generated answers

Hi {{name}},

I am launching AI Judge Citation Audit, a local-first tool that checks AI-generated answers for fabricated, weak, irrelevant, unverifiable, and contradicted citations.

The narrow use case is simple: before publishing an AI-generated report, README, paper draft, or client memo, run the citations through an audit that keeps model text and external evidence separate.

Live demo:
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

GitHub:
https://github.com/reguorier/ai-judge

I am collecting hard benchmark cases. If you have seen an AI answer invent or misuse a citation, I would love to add an anonymized version to the benchmark.

Best,
Reguorier
```

## Follow-up template

```text
Subject: Example report: unverifiable is not false

Hi {{name}},

One design detail that matters: AI Judge does not mark missing evidence as false.

It returns `unverifiable` when the audit cannot validate a citation from isolated external evidence. It returns `contradicted` only when supplied evidence explicitly refutes the citation or claim.

That distinction is useful when reviewing AI-generated work because it separates "we cannot trust this yet" from "this is wrong."

If useful, I can run one anonymized AI answer through the audit and send back the HTML/JSON report.
```
