# Document Parser Roadmap

Status: planned, with input visibility implemented

AI Judge Citation Audit now has an executable Markdown/JSON batch layer. PDF and Docx are still parser-roadmap formats, but they are no longer invisible: `ai-judge audit-batch` records them in `skipped_inputs` with a parser status and policy result.

## Current behavior

| Input | Current batch behavior | Policy status |
|---|---|---|
| Markdown / `.md` / `.markdown` | Audited and written as per-file HTML/JSON reports. | Citation and claim-support statuses. |
| JSON | Audited through the same single-file schema. | Citation and claim-support statuses. |
| PDF | Listed in the manifest and index as skipped. | `unsupported_input`, `pdf_parser_pending` |
| Doc / Docx | Listed in the manifest and index as skipped. | `unsupported_input`, `doc_parser_pending` or `docx_parser_pending` |
| Unmatched token | Listed in the manifest and index as skipped. | `unmatched_input` |

Default batch policy warns on unsupported or unmatched inputs. CI can make this strict:

```bash
PYTHONPATH=. python cli/main.py audit-batch "docs/**/*" \
  --fail-on contradicted,unsupported_input,unmatched_input
```

## PDF parser scope

The PDF parser should only move into production when it can preserve enough context for an auditable report:

- page number and text span for each extracted citation candidate
- URL, DOI, title, or bibliography candidate extraction
- extraction confidence and parser warnings
- raw extracted text snapshot hash
- per-page evidence gap tasks when a citation cannot be resolved

## Docx parser scope

The Docx parser should preserve author-facing document structure:

- paragraph anchors for each citation candidate
- hyperlinks, comments, footnotes, and endnotes
- bibliography/reference section extraction
- tracked-change awareness, with unsafe states flagged rather than silently ignored
- raw document snapshot hash and extracted-text hash

## Non-goals

- No silent OCR guesses in the first parser pass.
- No rewriting source documents.
- No claim of PDF/Docx support until parser warnings, anchors, and manifest policy behavior are covered by tests.

## Release gate

Before PDF/Docx audit is advertised as supported, these checks must pass:

1. Unit tests for extraction, anchor stability, and unsupported/partial-parser states.
2. Batch manifest tests proving document parser warnings affect policy status.
3. At least one public-safe PDF fixture and one public-safe Docx fixture with generated reports.
4. Documentation showing how to convert unsupported documents to Markdown/JSON while the parser is still pending.
