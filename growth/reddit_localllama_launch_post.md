# Reddit r/LocalLLaMA Launch Post

Status: ready for publish confirmation

Target:

```text
https://www.reddit.com/r/LocalLLaMA/submit
```

## Title

```text
I made a local-first benchmark and auditor for hallucinated citations in LLM answers
```

## Post

```text
I kept seeing AI answers cite plausible reports, surveys, and papers that were either nonexistent or did not support the claim. I built a narrow local-first tool around that failure mode.

AI Judge Citation Audit takes an AI-generated answer and external evidence, then labels citations as:

verified / weakly_verified / irrelevant / unverifiable / contradicted

It also keeps a Replay Ledger so model text, mentor notes, and external evidence remain separated.

The design rule is: model-mentioned sources do not verify themselves. If the answer cites a URL, that URL is only a candidate source until isolated external evidence supports it.

The basic demo does not need model APIs. The first benchmark has 100 deterministic synthetic cases across the five citation states.

Repo:
https://github.com/reguorier/ai-judge

Live demo:
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

Benchmark:
PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95

What I want from this community: nasty citation hallucination examples, weak-source examples, and suggestions for better benchmark cases.
```

## First 5 Replies

### 1. If someone asks whether this needs model APIs

```text
The core citation audit demo does not need model APIs. It extracts candidate citations, keeps them separate from external evidence, and labels support deterministically. Model-based blind review is a later layer, but I wanted the launch path to be reproducible without API keys.
```

### 2. If someone says existing eval frameworks already do this

```text
Most eval frameworks are broader. This is intentionally narrow: before publishing an AI-generated answer with citations, check whether each citation is supported, weak, irrelevant, unverifiable, or contradicted. The source-isolation rule is the key difference: the answer cannot verify itself by naming a URL.
```

### 3. If someone asks about automatic web search

```text
Network fetch is supported, but it is off by default in the demo so the benchmark remains deterministic. Even with fetch enabled, source existence is not enough; the audit still needs to classify whether the source actually supports the claim.
```

### 4. If someone asks why `unverifiable` exists

```text
`unverifiable` is different from `false`. It means the current isolated evidence is not enough to validate the citation. `contradicted` is reserved for cases where external evidence actively refutes the citation or claim.
```

### 5. If someone asks what benchmark cases are useful

```text
The best cases are AI answers that cite plausible fake papers/reports, real pages that do not support the claim, or sources that contradict the answer. Anonymized examples are fine; I mostly need the failure pattern and expected label.
```

## Publish Checklist

- Confirm Reddit account is logged in and allowed to post in r/LocalLLaMA.
- Confirm current repo README shows the live Space screenshot.
- Submit only after final click-time confirmation.
- Record the Reddit URL in `growth/feedback_log.md`.
- Watch replies for benchmark cases, PDF/Docx demand, and CI workflow demand.
