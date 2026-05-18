# Eval4SD 2026 Submission Packet

Target: First Workshop on Evaluating LLMs for Specialized Domains (Eval4SD), co-located with KONVENS 2026.

Confirmed from the public CFP on 2026-05-18:

- Short and position papers: up to 4 pages plus references.
- Format: ACL template.
- Review: double-blind via OpenReview.
- Submission deadline: 2026-07-03, 23:59 CEST.
- Scope fit: LLM benchmarking, domain research replication, metrics and evaluation methodology.

## Files

| File | Purpose |
|---|---|
| `main.tex` | Anonymous short-paper source. |
| `references.bib` | Initial verified bibliography from arXiv, Eval4SD, and related public sources. |
| `submission_checklist.md` | Final pre-submit gate. |

## Current Positioning

The paper should be submitted as a short / position paper, not a full benchmark paper. The strongest claim is narrow:

```text
Citation existence, source relevance, and exact claim support must be audited as separate layers.
```

The hard example is the real-source / overclaimed-causation case:

```text
citation_status = verified
source_relevance = relevant
claim_support = contradicted
support_failure_code = overclaimed_causation
```

## Build Notes

Use the official ACL template before final submission. This directory intentionally keeps the current draft anonymous and self-contained, but does not vendor `acl.sty`.

Suggested local flow once the ACL template is added:

```bash
cd papers/eval4sd2026
latexmk -pdf main.tex
```

Do not include GitHub, Hugging Face, author names, or private correspondence in the double-blind PDF. Public artifact links can be restored for a non-archival version, camera-ready, or appendix if the review policy allows it.
