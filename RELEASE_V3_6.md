# AI Judge v3.6.0

AI Judge v3.6 turns the Evidence OS foundation into a self-serve Citation Audit launch edition.

## Highlights

- New `ai-judge audit` CLI for Markdown/JSON citation audits.
- Standalone HTML, Markdown, and JSON audit report export.
- 100-case deterministic Citation Hallucination Benchmark.
- Three launch demos: fake citation, unsupported product rewrite, and sounds-smart/low-judgment analysis.
- GitHub composite action for CI citation audits.
- HuggingFace Space source for a public paste-and-audit demo.
- Launch posts, reply bank, and email sequences for automated growth execution.

## Commands

```bash
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md \
  --html reports/fake-citation-audit.html \
  --json reports/fake-citation-audit.json

PYTHONPATH=. python tools/run_citation_bench.py
```

## Validation

- `python -m pytest tests/test_citation_audit.py`
- `python tools/run_citation_bench.py --fail-under 0.95`
- Full regression suite before release.
