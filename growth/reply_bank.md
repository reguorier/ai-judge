# AI Judge Citation Audit Reply Bank

## "How is this different from Ragas/DeepEval/Giskard/Phoenix?"

AI Judge Citation Audit is narrower. It is not trying to replace general LLM evaluation, observability, or red teaming. It focuses on the publish-before-trust moment: an AI answer contains citations, and you need to know which citations are externally supported, weak, irrelevant, unverifiable, or contradicted. The source-isolation rule is the main difference: model-cited URLs are candidates, not proof.

## "Why is unverifiable not false?"

Because absence of supplied evidence is not contradiction. `unverifiable` means the audit did not find enough isolated external evidence to validate the citation. It becomes `contradicted` only when external evidence explicitly refutes the citation or related claim.

## "Can it fetch URLs automatically?"

Yes, the Evidence Broker supports network fetches, but the default demo keeps network off so the benchmark is deterministic. Use `--allow-network` when you want the broker to fetch cited URLs.

## "Does this use a judge model?"

The citation audit path does not need a judge model for its core status labels. It uses deterministic evidence matching plus Replay Ledger sealing. Blind cross-validation packets exist for a later model-review round, but the launch demo intentionally avoids model APIs.

## "Can it audit PDFs or Word documents?"

The executable batch version audits Markdown/JSON. If PDF/Docx files are included in a batch, they are recorded as `unsupported_input` with `pdf_parser_pending` or `docx_parser_pending` so they are not silently treated as audited. Full PDF/Docx audit is the planned Pro parser path because it needs page/paragraph anchors, parser warnings, export formats, and better error handling.

## "Can I use it in CI?"

Yes. The repo includes a composite GitHub Action at `.github/actions/citation-audit`. It can run single-file or batch Markdown/JSON audit inputs and upload HTML/JSON reports plus the batch manifest as artifacts. Strict CI can fail on `unsupported_input` or `unmatched_input` when every requested file must be audited.

## "What should I contribute?"

The highest-value contribution is benchmark cases: real examples where an AI answer cites a plausible but fake source, a real source that does not support the claim, or a source that contradicts the answer.
