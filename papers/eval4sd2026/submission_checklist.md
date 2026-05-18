# Eval4SD Submission Checklist

## Before PDF Build

- [x] Replace the generic formatting with the official ACL template files.
- [x] Build and inspect the anonymous PDF snapshot.
- [x] Keep author line anonymous for review.
- [x] Remove direct product, GitHub, Hugging Face, and private-contact identifiers from the submitted PDF snapshot.
- [x] Prepare OpenReview title, abstract, keywords, subject areas, and PDF path.
- [x] Choose archival route unless the OpenReview form requires a different option.
- [ ] Add any accepted taxonomy feedback from LegalCiteBench, RAGChecker, or HalluCiteChecker only if it can be cited publicly.

## Evidence Gate

- [ ] Run `PYTHONPATH=. python tools/check_eval4sd_packet.py`.
- [ ] Run `PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95`.
- [ ] Run `PYTHONPATH=. python tools/run_citation_bench.py --bench citation-bench/citation-bench-hard-11.jsonl --fail-under 0.95`.
- [ ] Regenerate the overclaimed-causation JSON report if the claim-support code changes.
- [ ] Confirm the paper's benchmark numbers match the latest command output.

## Submission Metadata

- Title: Source-Isolated Citation and Claim-Support Audit for LLM Outputs in Specialized Domains
- Type: Short / Position Paper
- Page budget: 4 pages plus references
- Deadline: 2026-07-03 23:59 CEST
- Venue: Eval4SD 2026
- Route: OpenReview
- Group: https://openreview.net/group?id=GSCL.org/KONVENS/2026/Workshop/Eval4SD
- Prepared form packet: `papers/eval4sd2026/openreview_submission.md`
- Prepared JSON packet: `papers/eval4sd2026/openreview_submission.json`

## Do Not Submit If

- The paper still claims full factual truth certification.
- `unverifiable` is described as false rather than insufficient isolated evidence.
- Raw model answer, external evidence, and audit verdict are collapsed into one trusted text.
- Private outreach or third-party correspondence is quoted or identifiable.
