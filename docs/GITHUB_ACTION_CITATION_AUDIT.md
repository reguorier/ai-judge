# GitHub Action Citation Audit Example

AI Judge includes a composite action at `.github/actions/citation-audit`.

## Minimal PR check

```yaml
name: Citation Audit

on:
  pull_request:
    paths:
      - "**/*.md"
      - "examples/**"
      - "citation-bench/**"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  citation-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/citation-audit
        with:
          input: examples/fake-citation.md
          output-html: reports/fake-citation-audit.html
          output-json: reports/fake-citation-audit.json
          allow-network: "false"
```

## Batch PR check

Use batch mode when a repository has many Markdown audit fixtures or generated AI answers:

```yaml
name: Citation Batch Audit

on:
  pull_request:
    paths:
      - "**/*.md"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  citation-batch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/citation-audit
        with:
          mode: batch
          input: "examples/*.md"
          output-dir: reports/citation-batch
          manifest: reports/citation-batch/manifest.json
          fail-on: contradicted
          warn-on: unverifiable,weakly_verified,irrelevant,partially_supported,unsupported,unsupported_input,unmatched_input
          artifact-name: ai-judge-citation-batch
```

For demo-only workflows that intentionally include contradicted examples, set `fail-on: ""` so the reports upload without failing CI.

## Failure policy

Launch behavior is report-first:

- `contradicted` should fail strict CI.
- `unverifiable` should warn first, because it means evidence is missing, not false.
- `irrelevant` should usually fail for publishable docs.
- `weakly_verified` should require reviewer attention.
- `unsupported_input` and `unmatched_input` should fail strict document workflows when every requested file must be audited.

## Example PR fixture

Use `examples/fake-citation.md` as the intentionally suspicious fixture. It should produce:

```text
overall_status: unverifiable
trust_gate: needs_more_evidence
```

That is expected. The goal is to show that the report preserves the issue rather than inventing confidence.

## Artifact contract

The action uploads:

- HTML report
- JSON report
- batch directory and manifest in batch mode

Downstream CI can parse:

```json
{
  "summary": {
    "overall_status": "unverifiable",
    "certification_id": "CITE-...",
    "replay_ledger_hash": "..."
  }
}
```

Batch manifests use `citation_audit_batch.v1` and include per-file report paths, Certification IDs, Replay Ledger hashes, trust gates, warning counts, failure counts, supported/skipped counts, and skipped input details.

PDF, Doc, and Docx files appear in `skipped_inputs` with parser statuses such as `pdf_parser_pending` or `docx_parser_pending`; unmatched globs appear as `unmatched_input`. To make CI fail when a requested document was not audited, include those statuses in `fail-on`:

```yaml
fail-on: contradicted,unsupported_input,unmatched_input
```
