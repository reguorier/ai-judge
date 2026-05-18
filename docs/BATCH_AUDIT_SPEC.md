# Batch Citation Audit Spec

## Goal

Batch Citation Audit turns the single-file launch demo into a Pro workflow for teams that publish AI-generated research, client memos, README files, and investment or product analysis.

The first paid promise is not "full Grand Judge". It is repeatable source-isolated citation audit at file or repository scale.

## Supported inputs

| Input | MVP behavior | Later behavior |
|---|---|---|
| Markdown | Parse headings and links, run one audit per document or section. | Section-level Certification IDs and PR comments. |
| JSON | Existing citation audit schema. | Batch manifest with per-file policy. |
| PDF | Reported as `unsupported_input` with `pdf_parser_pending`; not silently audited. | Extract text, page anchors, URLs, and references. |
| Docx | Reported as `unsupported_input` with `docx_parser_pending`; not silently audited. | Extract paragraphs, hyperlinks, comments, and bibliography. |
| GitHub PR | Use changed Markdown files. | SARIF/Check Run annotations. |

## CLI shape

```bash
ai-judge audit-batch docs/**/*.md \
  --out reports/citation-batch \
  --manifest reports/citation-batch/manifest.json \
  --fail-on contradicted \
  --warn-on unverifiable
```

Implemented MVP:

```bash
PYTHONPATH=. python cli/main.py audit-batch examples/*.md \
  --out reports/citation-batch \
  --manifest reports/citation-batch/manifest.json
```

The command accepts files, directories, or glob patterns. It writes one HTML and JSON report per supported input, plus `manifest.json` and `index.html`. If a batch includes PDF, Doc, Docx, or an unmatched token, the manifest records a skipped input with `unsupported_input` or `unmatched_input` instead of silently passing over it.

Launch proof artifact:

- Batch index: `reports/citation-batch/index.html`
- Manifest: `reports/citation-batch/manifest.json`
- GitHub Action batch mode: `.github/actions/citation-audit/action.yml`

## Output

```text
reports/citation-batch/
  manifest.json
  index.html
  file-001.html
  file-001.json
  file-002.html
  file-002.json
```

Manifest fields:

- `batch_id`
- `generated_at`
- `input_count`
- `supported_count`
- `skipped_count`
- `failed_count`
- `warning_count`
- `certification_ids`
- `replay_ledger_hashes`
- `policy`
- `results[]` with per-file status, claim support, trust gate, report paths, hashes, and policy result
- `skipped_inputs[]` with unsupported or unmatched inputs, parser status, reason, and policy result

## Trust rules

- Raw document text is preserved.
- Model-mentioned links remain candidate sources until verified.
- External evidence is recorded as its own layer.
- `unverifiable` does not block by default; `contradicted` can block CI.
- Unsupported PDF/Docx inputs are visible in the manifest and index page, and can fail CI with `--fail-on unsupported_input`.
- Network fetch is explicit and logged.

## Pro boundaries

Free tier:

- single Markdown/JSON audit
- 100-case benchmark
- local HTML/JSON report

Pro:

- batch manifests
- history ledger
- Evidence Broker network mode
- GitHub Action advanced mode
- PDF/Docx parser roadmap

## Non-goals

- No automatic rewriting of user documents.
- No hidden judge model deciding truth.
- No silent network fetch in deterministic benchmark mode.
