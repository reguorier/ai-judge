# Production Evaluation Fidelity Appendix

Date: 2026-05-19

This appendix turns the failed parts of the web-seat council run into research
evidence. The failure mode is not "the product is useless." The useful finding
is narrower:

> Real browser collection is part of evaluation fidelity. A production evaluator
> must record stale pages, placeholders, quota limits, model-mode drift, and
> missing captures instead of silently replacing them with local simulations.

## Web-Seat Run Receipt

The 2026-05-19 full-channel council attempted 13 enabled web seats.

| Seat | Capture result | Product implication |
|---|---|---|
| Claude | Complete structured answer | Valid raw seat response. |
| Kimi | Partial answer, downgraded model | Record mode drift and degraded-model status. |
| MiMo | Partial answer | Preserve partial output and missing prefix. |
| DeepSeek | Expert mode/deep/search verified, no capturable answer | Mode verification is separate from answer capture. |
| Gemini | Placeholder retained | Placeholder text must fail extraction. |
| ChatGPT | Placeholder retained | "Thinking complete" is not answer completion. |
| Qwen | Stale older task answer | Trace IDs must reject stale answers. |
| Grok | Asked for content instead of answering | Provider state can invalidate a run. |
| Yuanbao | Placeholder retained | Prompt submission is not answer generation. |
| MiniMax | Placeholder retained | Empty/placeholder answer must not count as a seat. |
| Zhipu | Stale older answer | Stale task contamination must be visible. |
| Wenxin | Editor/history state | Page mode can block answer generation. |
| Doubao | Super mode verified, placeholder retained | Model mode and answer readiness are different checks. |

## Methodological Use

For Eval4SD and EMNLP-style system papers, this receipt supports one claim:

> API-only evaluation can hide product-surface failure modes that matter when
> users rely on actual model webpages.

It does not prove that web collection is always better than APIs. It proves that
production collection needs explicit state accounting:

1. prompt written;
2. send action accepted;
3. mode verified;
4. trace ID present;
5. answer start marker present;
6. answer end marker present;
7. placeholder removed;
8. answer belongs to the current trace;
9. provider quota or page error recorded;
10. raw answer preserved without local substitution.

## Product Rule

AI Judge should score a web-seat run as incomplete unless the captured answer
passes the current-trace and non-placeholder gates. A failed seat can still be
valuable evidence, but only as a failure receipt, not as a vote.

## Paper Angle

This appendix can support a secondary paper:

`Lessons from Building a Browser-Collected Multi-Model Jury for Auditable AI Decisions`

The paper should position failures as reproducibility constraints:

- model mode drift;
- stale task contamination;
- hidden provider quota;
- slow generation versus genuine failure;
- placeholder capture;
- page state mismatch;
- inability to distinguish submitted prompt from answered prompt without trace gates.

