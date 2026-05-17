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

## Failure policy

Launch behavior is report-first:

- `contradicted` should fail strict CI.
- `unverifiable` should warn first, because it means evidence is missing, not false.
- `irrelevant` should usually fail for publishable docs.
- `weakly_verified` should require reviewer attention.

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
