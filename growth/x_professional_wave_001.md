# X Professional Wave 001 - Citation Audit Review Funnel

Status: ready_for_action_time_confirmation
Created: 2026-05-18

This wave is not a broad product ad. Its job is to convert X attention into specific GitHub actions from people who understand LLM eval, RAG, legal AI, research ops, open-source maintainers, and AI product governance.

## Operating Rule

Do not ask people to "check it out" in a vague way. Ask for one concrete contribution:

- submit a hard citation benchmark case
- critique the `unverifiable` / `contradicted` boundary
- map claim-span/source support to their eval taxonomy
- describe a batch Markdown/PDF/Docx workflow
- run the demo and file one issue

Primary link:

```text
https://github.com/reguorier/ai-judge
```

Live demo:

```text
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

Contribution links:

```text
Benchmark cases: https://github.com/reguorier/ai-judge/issues/2
Unverifiable vs contradicted: https://github.com/reguorier/ai-judge/issues/3
Batch/PDF/Docx demand: https://github.com/reguorier/ai-judge/issues/4
Demo gallery examples: https://github.com/reguorier/ai-judge/issues/5
```

## Target Audiences

| Segment | What to ask for | Best CTA |
|---|---|---|
| LLM eval builders | taxonomy critique | "Does this map cleanly to your factuality labels?" |
| RAG platform teams | faithfulness boundary cases | "Where would you label real-source/unsupported-claim?" |
| Legal AI teams | real authority / wrong proposition cases | "Can you share a sanitized example?" |
| Research ops / paper reviewers | citation audit examples | "Try one AI-generated paper paragraph." |
| Open-source maintainers | README / docs citation cases | "Run the demo on a generated README citation." |
| AI governance teams | audit trail and replay ledger critique | "What would you need before trusting this in review?" |
| Companies with document workflows | paid workflow demand | "Markdown, PDF, Docx, PR comments, or historical ledger first?" |

## Main Thread Draft

Post 1:

```text
I am looking for professional feedback on AI Judge Citation Audit.

The hard problem is not just fake citations.

It is when the source is real, relevant, and still does not prove the model's claim.

Example: source says "associated with"; model writes "caused by".
```

Post 2:

```text
AI Judge keeps these separate:

1. citation_status: does the source match external evidence?
2. source_relevance: is the source on-topic?
3. claim_support: does the source support the exact claim span?

A real citation should not automatically become a verified conclusion.
```

Post 3:

```text
The current demo returns:

- verified
- weakly_verified
- irrelevant
- unverifiable
- contradicted

Plus Certification ID, Replay Ledger, evidence provenance, HTML report, JSON report.

Live demo:
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

Post 4:

```text
If you build LLM eval, RAG eval, legal AI, AI governance, research tooling, or citation-heavy products:

I want your hardest sanitized failure case.

Benchmark issue:
https://github.com/reguorier/ai-judge/issues/2
```

Post 5:

```text
If you disagree with the label taxonomy, even better.

The most useful critique is:

"This should not be unverifiable; it should be contradicted because..."

or

"This source is real but only partially supports the claim because..."

Boundary issue:
https://github.com/reguorier/ai-judge/issues/3
```

Post 6:

```text
For companies:

I am intentionally not building billing first.

I want to know which workflow would make this useful:

- batch Markdown
- PDF reports/papers
- Docx/Word memos
- GitHub PR comments
- CI gate
- historical Replay Ledger

Workflow issue:
https://github.com/reguorier/ai-judge/issues/4
```

Post 7:

```text
Repo:
https://github.com/reguorier/ai-judge

The ask is simple:

Try the Space, run one local demo, or file one hard benchmark case.

I am especially interested in legal/research/RAG cases where the citation exists but the conclusion does not follow.
```

## Standalone Posts

### Legal AI / Research Citation CTA

```text
Legal AI and research-tool people:

What is your best sanitized example of a real citation that does not support the generated proposition?

I am collecting hard cases for AI Judge Citation Audit:
https://github.com/reguorier/ai-judge/issues/2

The boundary: source exists != claim proven.
```

### RAG / Eval Taxonomy CTA

```text
RAG/eval builders:

How would you label this?

Citation exists. Source is relevant. Source says correlation. Generated answer claims causation.

AI Judge labels it: verified source, relevant source, contradicted claim.

Does that map to your taxonomy?
https://github.com/reguorier/ai-judge/issues/3
```

### Company Workflow CTA

```text
If your company publishes AI-assisted reports, memos, papers, docs, or PRDs:

Would citation audit be useful as:

1. batch Markdown
2. PDF audit
3. Docx audit
4. GitHub PR comment
5. CI gate

I am collecting real workflows before building Pro:
https://github.com/reguorier/ai-judge/issues/4
```

### Open-Source Maintainer CTA

```text
Open-source maintainers:

If an AI generates a README with citations, badges, benchmark claims, or security claims, how do you verify them before merging?

AI Judge Citation Audit produces HTML/JSON reports for that exact pre-publish moment:
https://github.com/reguorier/ai-judge
```

### Benchmark Challenge CTA

```text
Challenge for LLM people:

Send me one public-safe AI answer where the citations look convincing but fail under source isolation.

Fake source, irrelevant source, unverifiable source, or real source / wrong claim all count.

Issue form:
https://github.com/reguorier/ai-judge/issues/new/choose
```

## Reply Templates

Use these only where directly relevant. Do not spam unrelated threads.

### Reply: citation hallucination thread

```text
This is exactly the failure mode I am trying to make benchmarkable.

I built AI Judge Citation Audit around source isolation: model-mentioned sources are candidates, not proof.

If you have a sanitized case, I would love to add it:
https://github.com/reguorier/ai-judge/issues/2
```

### Reply: RAG faithfulness thread

```text
One boundary I am testing:

source retrieval can succeed while exact claim support fails.

AI Judge separates source match, relevance, and claim support so "real source" does not become "proven answer."

How would you map this to RAG faithfulness labels?
https://github.com/reguorier/ai-judge/issues/3
```

### Reply: legal AI thread

```text
For legal AI, the hard case seems to be real authority / wrong proposition rather than purely fake citations.

I am collecting sanitized examples for that exact label boundary:
https://github.com/reguorier/ai-judge/issues/2
```

### Reply: AI governance thread

```text
This is why AI Judge preserves raw answer, external evidence, and audit verdict separately.

The judge does not rewrite the answer; it emits a Certification ID, Replay Ledger, and citation/claim-support labels.

I would value governance critique here:
https://github.com/reguorier/ai-judge
```

### Reply: document workflow / enterprise thread

```text
I am trying not to guess the Pro roadmap.

If batch citation audit matters to your workflow, the useful signal is file type + volume + desired output:
Markdown, PDF, Docx, PR comments, CI, CSV/SARIF/HTML/JSON.

Collecting that here:
https://github.com/reguorier/ai-judge/issues/4
```

## Target Accounts And Organizations To Watch

These are not automatic mention targets. Use them for manual search, relevant replies, and careful quote-posting only when the thread is already about citation hallucination, RAG faithfulness, legal AI reliability, or LLM evaluation.

| Segment | Targets |
|---|---|
| LLM eval / observability | Ragas, DeepEval / Confident AI, Giskard, Arize Phoenix, LangSmith, Weave / Weights & Biases |
| RAG / agent frameworks | LangChain, LlamaIndex, Haystack, DSPy |
| Legal AI / legal research | LegalBench, LegalCiteBench authors, legal AI newsletters, law-tech founders |
| Research / paper tooling | Semantic Scholar, arXiv-adjacent tool builders, paper-review workflow builders |
| AI governance / provenance | Article 11, audit trail / attestation / provenance startups, policy-eval researchers |
| Open-source maintainers | README/doc quality, security docs, benchmark repo maintainers |

## Posting Sequence

1. Post main thread.
2. Wait at least 30 minutes.
3. Post one standalone CTA for the highest-priority segment: RAG/eval or legal AI.
4. Search X for 5 relevant threads and draft replies; post only if directly relevant.
5. Log each public URL in `growth/feedback_log.md` and update `growth/metrics_dashboard.md`.
6. If a reply contains a case, ask permission before converting it into a benchmark fixture.

## Success Metrics

| Metric | Target |
|---|---:|
| Useful X replies | 5 |
| GitHub issue comments/new issues | 3 |
| New benchmark cases | 3 |
| Pro workflow comments | 2 |
| Stars attributed to X wave | 20 |

## Current Blockers

- `twitter-cli` cannot read browser cookies because macOS Keychain access is not granted to the terminal.
- Public X posts/replies need action-time confirmation before clicking Post/Reply.
