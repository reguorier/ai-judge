# Resonance Wave 004 - RefChecker Claim Audit Mapping

Status: partially_posted
Created: 2026-05-18
Last updated: 2026-05-18

This wave targets a precise technical overlap:

```text
RefChecker decomposes responses into claim triplets and predicts entailment, neutral, or contradiction against references.
AI Judge preserves citation verification, source relevance, and exact claim support as separate audit fields.
```

The collaboration question is whether AI Judge's source-isolated `claim_support_audit.items[]` can map cleanly into RefChecker's triplet-level factuality labels without collapsing verified citations into supported conclusions.

## Target

| ID | Target | Route | Status |
|---|---|---|---|
| W004-001 | RefChecker | GitHub public issue | blocked_archived_read_only |
| W004-002 | RAGChecker | GitHub public issue | public_issue_posted |

## Draft

Title:

```text
Taxonomy comparison: triplet entailment vs source-isolated citation/claim support
```

Body:

~~~text
Hi RefChecker team,

I am building a small complementary source-isolated audit tool called AI Judge Citation Audit. RefChecker's triplet-level framing is very close to the claim-support layer I am adding, so I wanted to ask whether a taxonomy mapping would be useful.

AI Judge keeps three outputs separate:

- citation_status: whether a cited source can be matched in isolated evidence
- source_relevance: whether the source is on-topic for the claim
- claim_support: whether the source supports the exact generated claim span

The hard case is where a source is real and relevant, but the model overstates what it proves:

citation_status = verified
source_relevance = relevant
claim_support = contradicted
support_failure_code = overclaimed_causation

Example: a reference reports association/correlation, while the generated answer states causation.

My read is that this should map to a RefChecker-style contradiction at the claim/triplet level, while keeping source existence and relevance as separate metadata. That distinction is useful for citation-heavy legal, scientific, and policy outputs because "real citation" should not become "proven conclusion."

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Spec: https://github.com/reguorier/ai-judge/blob/main/docs/CLAIM_SUPPORT_AUDIT_SPEC.md
Eval4SD draft: https://github.com/reguorier/ai-judge/blob/main/docs/EVAL4SD_2026_SOURCE_ISOLATED_CITATION_AUDIT_DRAFT.md

Would you be open to a small taxonomy comparison around:

1. RefChecker triplet labels vs AI Judge `claim_support`
2. handling `Neutral` / not-enough-evidence vs AI Judge `unverifiable`
3. preserving citation/source metadata separately from claim factuality

No integration ask yet; I am trying to make the benchmark vocabulary precise before adding more moving parts.

Best,
Reguorier
~~~

## Why This Target

RefChecker already treats claim-level checking as the core unit, and its public README explicitly discusses claim triplets, entailment, neutral, contradiction, localization, and limitations around granularity. That makes it a better match than generic launch channels for the current AI Judge wedge.

## Route Update

`amazon-science/RefChecker` is archived, so GitHub rejected new issue creation with `Repository was archived so is read-only`. The same research line has an active successor route at `amazon-science/RAGChecker`, which is not archived and has Issues enabled. The next post should target RAGChecker with the same taxonomy question framed as RAG faithfulness / retrieved-context support rather than RefChecker maintenance.

Public issue posted:

```text
https://github.com/amazon-science/RAGChecker/issues/38
```
