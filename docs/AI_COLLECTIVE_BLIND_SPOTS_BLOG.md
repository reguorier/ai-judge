# 9 AI Answers Can Still Share One Blind Spot: Citations That Verify Themselves

Multi-model consensus feels reassuring. If nine systems independently produce a similar answer, it is tempting to treat the overlap as evidence.

But consensus is not truth if every model shares the same weak assumption.

The specific blind spot AI Judge Citation Audit targets is simple:

> A source mentioned by a model is not proof. It is only a candidate source until isolated external evidence supports it.

That rule sounds small, but it changes how AI-generated reports, README files, legal memos, and research drafts should be reviewed before publication.

## The Impressive Failure Mode

Modern AI answers often fail in a polished way. They do not merely say something unsupported; they wrap the unsupported claim in the shape of evidence:

- a plausible institute
- a realistic report title
- a URL with the right words
- a benchmark name
- a confident comparison against human experts

If several models repeat the same kind of citation, the error can look like convergence. In reality, it may be source contamination: the same unsupported reference pattern flowing through multiple answers.

AI Judge's broader council architecture is built around this risk. The judge should summarize, score, and preserve disagreement. It should not let one model's invented citation become another model's evidence.

## The Four Layers That Must Stay Separate

Citation audit starts by separating four layers:

| Layer | What it contains | Why it must stay separate |
|---|---|---|
| Raw model answer | The original AI-generated text | The judge must not rewrite away the evidence problem. |
| Model-mentioned candidate sources | URLs, paper titles, reports, institutions named by the answer | These are claims about evidence, not evidence itself. |
| External evidence | Supplied or fetched evidence outside the answer | Only this layer can upgrade a citation. |
| Verification output | Status labels, Certification ID, Replay Ledger | The audit trail must be replayable. |

The maximum-risk failure is "using hallucination to verify hallucination." Source isolation is the guardrail against that.

## Why `unverifiable` Is Not `false`

Most public fact-checking language pushes toward a binary: true or false.

Citation audit needs a third state.

`unverifiable` means the current external evidence is insufficient. It does not mean the claim has been disproven. It means the answer should not be published as supported yet.

That distinction matters:

- `unverifiable`: evidence is missing or too weak
- `irrelevant`: the source exists but does not support the claim
- `contradicted`: external evidence actively refutes the claim

Overcalling `false` is its own reliability bug. A useful judge should be able to say "I do not know yet" without pretending that uncertainty is a verdict.

## Five Demo Failures

The current demo gallery is deliberately small and reproducible. It does not need model APIs or browser bridges.

| Demo | Failure mode | Report |
|---|---|---|
| Fake citation | Plausible institution, no isolated support | [`fake-citation-audit.html`](../reports/fake-citation-audit.html) |
| Product plan without evidence | Confident roadmap, unsupported defect-reduction claim | [`product-no-evidence-audit.html`](../reports/product-no-evidence-audit.html) |
| Sounds smart, low judgment | Impressive memo language, weak source support | [`sounds-smart-low-judgment-audit.html`](../reports/sounds-smart-low-judgment-audit.html) |
| Legal memo contradicted | Cited benchmark directly warns against the answer | [`legal-memo-contradicted-audit.html`](../reports/legal-memo-contradicted-audit.html) |
| Open-source README irrelevant | URL exists, but source content is unrelated | [`opensource-readme-irrelevant-audit.html`](../reports/opensource-readme-irrelevant-audit.html) |

The labels are intentionally narrow:

```text
verified
weakly_verified
irrelevant
unverifiable
contradicted
```

The point is not to replace a human editor, lawyer, researcher, or maintainer. The point is to force the evidence problem into view before the work is published.

## Why the Launch Is Deterministic First

The first version is not a full Grand Judge.

That is on purpose.

A citation audit baseline should be reproducible before it becomes clever. The launch path:

- runs locally
- produces HTML and JSON reports
- emits a Certification ID
- keeps a Replay Ledger
- includes a 100-case benchmark
- includes a hard 10-case launch benchmark
- does not require model API keys

Once this evidence layer is trustworthy, model cross-review becomes more useful. Without source isolation, model cross-review can become a very fluent way to launder unsupported claims.

## What Comes Next

The most useful next contribution is not praise. It is hard cases.

Good benchmark cases include:

- plausible fake papers or reports
- real sources that do not support the stated claim
- sources that partially support a weaker claim
- stale or superseded sources
- external evidence that contradicts the answer
- AI answers that sound sourced but collapse under inspection

Submit cases here:

https://github.com/reguorier/ai-judge/issues/2

The live demo is here:

https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

The repository is here:

https://github.com/reguorier/ai-judge

The core rule is the product:

> Model-mentioned sources do not verify themselves.
