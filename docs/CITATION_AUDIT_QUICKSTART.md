# Citation Audit Quickstart

## Run the fake-citation demo

```bash
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md \
  --html reports/fake-citation-audit.html \
  --json reports/fake-citation-audit.json
```

Open `reports/fake-citation-audit.html` in a browser.

## Demo report gallery

| Demo | Input | Report |
|---|---|---|
| Fake citation | [`examples/fake-citation.md`](../examples/fake-citation.md) | [`reports/fake-citation-audit.html`](../reports/fake-citation-audit.html) / [`json`](../reports/fake-citation-audit.json) |
| Product plan without evidence | [`examples/product-no-evidence.md`](../examples/product-no-evidence.md) | [`reports/product-no-evidence-audit.html`](../reports/product-no-evidence-audit.html) / [`json`](../reports/product-no-evidence-audit.json) |
| Sounds smart, low judgment | [`examples/sounds-smart-low-judgment.md`](../examples/sounds-smart-low-judgment.md) | [`reports/sounds-smart-low-judgment-audit.html`](../reports/sounds-smart-low-judgment-audit.html) / [`json`](../reports/sounds-smart-low-judgment-audit.json) |
| Legal memo contradicted | [`examples/legal-memo-contradicted.md`](../examples/legal-memo-contradicted.md) | [`reports/legal-memo-contradicted-audit.html`](../reports/legal-memo-contradicted-audit.html) / [`json`](../reports/legal-memo-contradicted-audit.json) |
| Open-source README irrelevant | [`examples/opensource-readme-irrelevant.md`](../examples/opensource-readme-irrelevant.md) | [`reports/opensource-readme-irrelevant-audit.html`](../reports/opensource-readme-irrelevant-audit.html) / [`json`](../reports/opensource-readme-irrelevant-audit.json) |
| Real source, overclaimed causation | [`examples/real-source-overclaimed-causation.md`](../examples/real-source-overclaimed-causation.md) | [`reports/real-source-overclaimed-causation-audit.html`](../reports/real-source-overclaimed-causation-audit.html) / [`json`](../reports/real-source-overclaimed-causation-audit.json) |
| Real source, overclaimed absolute | [`examples/real-source-overclaimed-absolute.md`](../examples/real-source-overclaimed-absolute.md) | [`reports/real-source-overclaimed-absolute-audit.html`](../reports/real-source-overclaimed-absolute-audit.html) / [`json`](../reports/real-source-overclaimed-absolute-audit.json) |
| Real source, overclaimed quantified effect | [`examples/real-source-overclaimed-quantified.md`](../examples/real-source-overclaimed-quantified.md) | [`reports/real-source-overclaimed-quantified-audit.html`](../reports/real-source-overclaimed-quantified-audit.html) / [`json`](../reports/real-source-overclaimed-quantified-audit.json) |

## Input format

Create a Markdown file:

````markdown
# My Citation Audit

## Question
Does this answer cite evidence that supports the claim?

## AI Answer
The answer text goes here. Source: https://example.com/source

## External Evidence
```json
[
  {
    "url": "https://example.com/source",
    "title": "Source title",
    "snippet": "Evidence snippet that supports or refutes the answer."
  }
]
```
````

## Status labels

| Label | Meaning |
|---|---|
| `verified` | Strong external evidence match and relevant to the answer. |
| `weakly_verified` | Partial or implied source match; useful but not enough for high confidence. |
| `irrelevant` | Source exists but does not support the cited claim. |
| `unverifiable` | Current external evidence is insufficient; this is not the same as false. |
| `contradicted` | External evidence explicitly refutes the citation or claim. |

## Run the benchmark

The Eval4SD minimum experiment is pinned by:

```text
citation-bench/citation-bench-50-manifest.json
```

It fixes five 10-case slices from the deterministic 100-case dataset:
`verified`, `weakly_verified`, `irrelevant`, `unverifiable`, and `contradicted`.

```bash
PYTHONPATH=. python3 tools/run_citation_bench.py --fail-under 0.95
```

The default benchmark has 100 deterministic cases and does not use browser bridges or model APIs.

Run the hard launch set when changing citation extraction, evidence matching, or status classification:

```bash
PYTHONPATH=. python3 tools/run_citation_bench.py \
  --bench citation-bench/citation-bench-hard-11.jsonl \
  --fail-under 0.95
```

The hard set focuses on edge cases that matter in public demos: implied references, plausible but unsupported reports, contradicted sources, sources that exist but do not support the claim, and real sources whose limited findings are overclaimed as causation, absolutes, or inflated percentages.

The overclaimed-support demos are the key governance cases: the citation can stay `verified`, the source can stay `relevant`, and the exact claim can still be `contradicted` because the source supports a weaker proposition than the answer states.

## Run a batch audit

```bash
PYTHONPATH=. python cli/main.py audit-batch "examples/*.md" \
  --out reports/citation-batch \
  --manifest reports/citation-batch/manifest.json
```

The batch run writes one HTML/JSON report per supported Markdown/JSON input, plus a manifest and index page. Unsupported document inputs are visible instead of ignored: PDF, Doc, and Docx files appear under `skipped_inputs` with parser statuses such as `pdf_parser_pending` or `docx_parser_pending`.

Use a stricter input policy in CI when every requested file must be audited:

```bash
PYTHONPATH=. python cli/main.py audit-batch "docs/**/*" \
  --fail-on contradicted,unsupported_input,unmatched_input
```

## Pro path

The free path stays local and single-file. The first Pro value step now has an executable Markdown/JSON batch MVP; Pro early access is reserved for workflows that need stricter CI gating, history, network-backed evidence fetching, or the PDF/Docx parser path:

- [`docs/BATCH_AUDIT_SPEC.md`](BATCH_AUDIT_SPEC.md)
- [`docs/GITHUB_ACTION_CITATION_AUDIT.md`](GITHUB_ACTION_CITATION_AUDIT.md)
- [`docs/PRO_EARLY_ACCESS.md`](PRO_EARLY_ACCESS.md)
- [`docs/DOCUMENT_PARSER_ROADMAP.md`](DOCUMENT_PARSER_ROADMAP.md)
