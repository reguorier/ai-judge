# 9 AI Collective Blind Spots: Blog Outline

## Working title

```text
9 AI answers can still share one blind spot: citations that verify themselves
```

## Thesis

Multi-model consensus does not automatically create truth. If every model treats a cited URL, paper title, or institution name as evidence merely because it appears in an answer, the council can amplify a hallucination instead of catching it.

AI Judge Citation Audit narrows the problem to a testable rule: model-mentioned sources are candidate sources, not proof.

## Structure

1. The impressive failure mode
   - Several AI systems can produce fluent agreement.
   - Agreement is not evidence if the same unsupported citation flows through every answer.

2. The source-contamination problem
   - Raw model answer
   - Mentor supplement
   - External evidence
   - Verification output
   - These must stay separate.

3. Why `unverifiable` is a useful status
   - Missing evidence is not contradiction.
   - `false` is too strong without refuting evidence.
   - `unverifiable` is the honest publish-risk label.

4. Three demo failures
   - Fake citation: plausible institution, no isolated support.
   - Product plan without evidence: confident roadmap, no defect-reduction proof.
   - Sounds smart, low judgment: impressive memo language, weak source support.

5. Why deterministic launch first
   - No model API required.
   - Benchmark can run in CI.
   - The product earns trust before adding model cross-review.

6. What comes next
   - Hard benchmark cases from the community.
   - Batch Markdown/PDF/Docx audit.
   - GitHub Action report artifacts.
   - Blind model cross-validation only after source isolation.

## Call to action

Send citation failure cases:

- fake paper/report
- real source, wrong claim
- stale source
- contradicted source
- high-confidence AI answer with unverifiable support

Space: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

Repo: https://github.com/reguorier/ai-judge
