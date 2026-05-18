# Eval4SD 2026 Submission Packet

Target: First Workshop on Evaluating LLMs for Specialized Domains (Eval4SD), co-located with KONVENS 2026.

Confirmed from the public CFP on 2026-05-18:

- Short and position papers: up to 4 pages plus references.
- Format: ACL template.
- Review: double-blind via OpenReview.
- Submission deadline: 2026-07-03, 23:59 CEST.
- Scope fit: LLM benchmarking, domain research replication, metrics and evaluation methodology.

Organizer fit reply on 2026-05-18:

- The topic is a strong fit for the workshop.
- Short / position paper is appropriate.
- Demo paper with limited evaluation would also work.
- No further pre-fit check is needed; proceed to submission.

## Files

| File | Purpose |
|---|---|
| `main.tex` | Anonymous short-paper source. |
| `main.pdf` | Current anonymous ACL review PDF build. |
| `acl.sty` | Official ACL style file from `acl-org/acl-style-files`. |
| `acl_natbib.bst` | Official ACL bibliography style from `acl-org/acl-style-files`. |
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

The paper now uses the official ACL review style via:

```latex
\usepackage[review]{acl}
```

Suggested local flow:

```bash
cd papers/eval4sd2026
tectonic main.tex
```

Before any PDF build or OpenReview upload, run:

```bash
python tools/check_eval4sd_packet.py
```

Current build snapshot:

- Built with `tectonic main.tex` on 2026-05-18.
- PDF length: 3 pages.
- Extracted PDF text check found no `reguorier`, `github.com`, `huggingface`, `AI Judge`, or email-address identity leaks.

Do not include GitHub, Hugging Face, author names, or private correspondence in the double-blind PDF. Public artifact links can be restored for a non-archival version, camera-ready, or appendix if the review policy allows it.
