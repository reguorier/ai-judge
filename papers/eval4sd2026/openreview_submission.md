# OpenReview Submission Packet

Venue:

```text
GSCL KONVENS 2026 Workshop Eval4SD
```

OpenReview group:

```text
https://openreview.net/group?id=GSCL.org/KONVENS/2026/Workshop/Eval4SD
```

Submission type:

```text
Short / Position Paper
```

Archival choice:

```text
Archival, if the OpenReview form asks.
```

Reason: the work is not under review elsewhere, the PDF is anonymous, and the venue says proceedings will be published in the ACL Anthology.

## Title

```text
Source-Isolated Citation and Claim-Support Audit for LLM Outputs in Specialized Domains
```

## Abstract

```text
Large language models increasingly produce source-heavy outputs in legal, medical, financial, and scientific workflows. In these domains, citation errors are not merely factual mistakes; they can become publication, compliance, and professional-risk events. We propose source-isolated citation audit: a lightweight protocol that keeps a model's raw answer, external evidence, and audit verdict separate. The protocol prevents model-mentioned sources from verifying themselves, labels citations as verified, weakly_verified, irrelevant, unverifiable, or contradicted, and adds evidence-provenance grades plus reason codes for failed verification. We instantiate the protocol in a deterministic local-first audit system that emits human-readable reports, automation-friendly JSON, certification identifiers, and replay-ledger hashes. A benchmark of 100 deterministic cases and 11 hard cases shows how the protocol handles fabricated sources, real-but-irrelevant sources, contradicted claims, missing evidence, and a hard case where a real source reports association while the model claims causation. We argue that citation-level audit is a practical minimum boundary for deployment, but specialized-domain workflows ultimately require the smaller audit atom of claim-span + source.
```

## Keywords

```text
LLM evaluation, citation verification, claim support, source isolation, legal AI, specialized domains, reproducibility, audit trails
```

## Subject Areas

Use the closest available OpenReview choices:

```text
Metrics and Evaluation Methodology
LLM Benchmarking
Law
Science / Research Writing
```

## PDF

Upload:

```text
papers/eval4sd2026/main.pdf
```

Current PDF checks:

- ACL review style.
- 3 pages.
- Anonymous author line.
- No obvious product, public-repository, demo-platform, email, or personal identity leak in extracted PDF text.
- Benchmarks refreshed by `tools/check_eval4sd_packet.py`.

## Notes For The Submission Form

If the form asks whether this is a demo or system paper, choose the short / position paper route and describe it as:

```text
A short / position paper with a deterministic system artifact and limited evaluation.
```

If the form asks for supplementary material, do not attach public project links for the double-blind review version unless explicitly allowed. Keep public artifact links for camera-ready or non-anonymous supplementary materials.

If the form asks about dual submission:

```text
This work is not under review elsewhere.
```
