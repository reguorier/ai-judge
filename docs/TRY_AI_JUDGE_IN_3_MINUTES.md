# Try AI Judge In 3 Minutes

AI Judge Citation Audit is easiest to understand through one hard boundary:

```text
A source can be real and relevant, but still fail to prove the model's exact claim.
```

This public proof path uses the live demo, static public examples, and benchmark
fixtures. It does not require private source code, model APIs, browser bridges,
or paid accounts.

## 1. Try The Live Demo

Open the Hugging Face Space:

```text
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

Use the built-in suspicious citation sample first. The expected lesson is that
`unverifiable` means insufficient isolated evidence, not automatically false.

## 2. Inspect The Overclaim Boundary

Open the public example:

```text
examples/real-source-overclaimed-causation.md
```

The useful reading pattern is:

```text
overall_status: verified
overall_claim_support: contradicted
support_failure_code: overclaimed_causation
```

That is the core product value. The citation can match, the source can be on
topic, and the exact claim can still fail.

## 3. Inspect The Static Report Gallery

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

## 4. Read The Public Benchmarks

The public benchmark files are static fixtures:

```text
citation-bench/citation-bench-100.jsonl
citation-bench/citation-bench-hard-11.jsonl
```

Current expected snapshot:

| Benchmark | Cases | Expected |
|---|---:|---|
| `citation-bench-100` | 100 | 100 / 100 |
| `citation-bench-hard-11` | 13 | 13 / 13 |

The hard benchmark keeps its legacy filename, but now contains 13 launch cases.
The newest cases include claim-support expectations and failure-code checks.

## 5. Run The Public Snapshot Check

If you cloned this repository, verify the public snapshot without installing
the private runtime:

```bash
python3 scripts/verify_public_snapshot.py
```

Expected output:

```text
public snapshot verified
benchmarks: 100 citation cases, 13 hard claim-support cases
reports: citation batch manifest and artifacts linked
```

The script checks benchmark JSONL parsing, report manifest links, required
public files, local README/HTML links, and the absence of private runtime
directories.

## 6. What To Contribute

The fastest useful contribution is not a feature request. It is one public-safe
hard case.

| Link | Useful input |
|---|---|
| Benchmark case issue form | A fabricated, weak, irrelevant, unverifiable, contradicted, or overclaimed citation case. |
| Boundary issue form | A case where `unverifiable` and `contradicted` are easy to confuse. |
| Workflow request issue form | A real batch/PDF/Docx/CI/report-review workflow that would justify product work. |
| Pull request | A public-safe demo example, docs fix, or benchmark fixture update. |

Please keep private material out of public issues. A sanitized summary is enough.
Read [`CONTRIBUTING.md`](../CONTRIBUTING.md) before publishing examples.

## What This Is Not

- Not a truth oracle.
- Not a legal, medical, financial, or academic authority.
- Not a model answer rewriter.
- Not proof that a source is correct just because it exists.
- Not the private production runtime.

AI Judge preserves the raw answer, model supplements, isolated evidence, and
audit verdicts as separate layers. The judge summarizes, counts, scores, and
shows uncertainty; it does not overwrite the original answer.
