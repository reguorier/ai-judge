# Try AI Judge In 3 Minutes

AI Judge Citation Audit is easiest to understand through one hard boundary:

```text
A source can be real and relevant, but still fail to prove the model's exact claim.
```

This quick proof path uses deterministic local examples. It does not require model
APIs, browser bridges, or paid accounts.

## 1. Try The Live Demo

Open the Hugging Face Space:

```text
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

Use the built-in suspicious citation sample first. The expected lesson is that
`unverifiable` means insufficient isolated evidence, not false.

## 2. Run One Local Audit

```bash
PYTHONPATH=. python3 cli/main.py audit examples/real-source-overclaimed-causation.md \
  --html reports/real-source-overclaimed-causation-audit.html \
  --json reports/real-source-overclaimed-causation-audit.json
```

Expected result:

```text
overall_status: verified
overall_claim_support: contradicted
support_failure_code: overclaimed_causation
```

That is the core product value. The citation can match, the source can be on
topic, and the exact claim can still fail.

## 3. Inspect The Eight-Example Gallery

Open:

```text
reports/citation-batch/index.html
```

The gallery covers:

| Demo family | What it proves |
|---|---|
| Fake citation | A plausible source name is not proof. |
| Product plan without evidence | A confident recommendation can lack support. |
| Low-judgment investor prose | Fluent writing can hide missing sources. |
| Legal memo contradicted | External evidence can directly refute a claim. |
| Real but irrelevant source | A URL can exist and still support the wrong topic. |
| Overclaimed causation | Association is not causation. |
| Overclaimed absolute | A limited pilot is not "all/no false negatives." |
| Overclaimed quantified effect | A 12% finding is not a 95% reduction. |

## 4. Run The Benchmarks

```bash
PYTHONPATH=. python3 tools/run_citation_bench.py --fail-under 0.95
PYTHONPATH=. python3 tools/run_citation_bench.py \
  --bench citation-bench/citation-bench-hard-11.jsonl \
  --fail-under 0.95
```

Current expected snapshot:

| Benchmark | Cases | Expected |
|---|---:|---|
| `citation-bench-100` | 100 | 100 / 100 |
| `citation-bench-hard-11` | 13 | 13 / 13 |

The hard benchmark keeps its legacy filename, but now contains 13 launch cases.
The newest cases include claim-support expectations and failure-code checks.

## 5. What To Contribute

The fastest useful contribution is not a feature request. It is one public-safe
hard case.

| Link | Useful input |
|---|---|
| https://github.com/reguorier/ai-judge/issues/2 | A fabricated, weak, irrelevant, unverifiable, contradicted, or overclaimed citation case. |
| https://github.com/reguorier/ai-judge/issues/3 | A boundary case where `unverifiable` and `contradicted` are easy to confuse. |
| https://github.com/reguorier/ai-judge/issues/4 | A real batch/PDF/Docx/CI workflow that would justify Pro work. |
| https://github.com/reguorier/ai-judge/issues/5 | A public-safe demo example that deserves an HTML/JSON audit report. |

Please keep private material out of public issues. A sanitized summary is enough.

## What This Is Not

- Not a truth oracle.
- Not a legal, medical, financial, or academic authority.
- Not a model answer rewriter.
- Not proof that a source is correct just because it exists.

AI Judge preserves the raw answer, mentor/model supplements, isolated evidence,
and audit verdicts as separate layers. The judge summarizes, counts, scores, and
shows uncertainty; it does not overwrite the original answer.
