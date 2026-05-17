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

```bash
PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95
```

The default benchmark has 100 deterministic cases and does not use browser bridges or model APIs.
