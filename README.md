<p align="center">
  <img src="https://img.shields.io/badge/release-3.8-public%20showcase-0a66c2" alt="AI Judge v3.8 public showcase">
  <a href="https://huggingface.co/spaces/reguorier/ai-judge-citation-audit"><img src="https://img.shields.io/badge/HuggingFace-citation%20audit%20live-087a68" alt="Hugging Face citation audit live"></a>
  <img src="https://img.shields.io/badge/claim--support-overclaim%20aware-9a6500" alt="claim support and overclaim aware">
  <img src="https://img.shields.io/badge/core-closed--core-17202a" alt="closed-core">
  <img src="https://img.shields.io/badge/public-demo%20%2B%20benchmarks-9a6500" alt="public demo and benchmarks">
</p>

<p align="center">
  <img src="assets/ai-judge-public-flow.svg" alt="AI Judge public audit flow" width="960">
</p>

<h1 align="center">AI Judge</h1>
<p align="center"><strong>Source-isolated claim-support audit for AI-generated answers.</strong></p>
<p align="center">AI Judge checks whether citations and isolated sources actually support the exact claims a model answer made before that answer is reused in a report, memo, README, paper, or agent workflow.</p>
<p align="center"><strong>Live demo:</strong> <a href="https://huggingface.co/spaces/reguorier/ai-judge-citation-audit">huggingface.co/spaces/reguorier/ai-judge-citation-audit</a></p>

<p align="center">
  <a href="https://huggingface.co/spaces/reguorier/ai-judge-citation-audit">Live Citation Audit</a> ·
  <a href="docs/TRY_AI_JUDGE_IN_3_MINUTES.md">3-Minute Proof</a> ·
  <a href="product/landing.html">Public Showcase Page</a> ·
  <a href="docs/PUBLIC_PRIVATE_BOUNDARY.md">Public / Private Boundary</a> ·
  <a href="docs/ARC_AGENT_TRACE_AUDIT.md">Agent Trace Audit</a>
</p>

---

## What This Public Repo Is

This repository is the public-facing doorway for AI Judge: product positioning, public demos, sanitized examples, benchmark descriptions, and a lightweight explanation of the trust protocol.

The private repository remains the engineering source of truth for the production runtime. Browser/CDP bridge code, model-seat orchestration, local operator flows, customer facts, raw transcripts, generated evidence packs, and commercial workflow code are not part of the public surface.

## What You Can Understand In 60 Seconds

AI Judge is not another chatbot wrapper. It is a review layer around generated answers:

- **Source isolation:** keep model text, model-mentioned sources, supplied evidence, fetched evidence, and audit result separate.
- **Claim-support audit:** check whether the source supports the exact claim span, not just a nearby topic.
- **Overclaim detection:** catch cases where a real source supports a weaker statement than the model asserted.
- **Dissent before confidence:** preserve blockers and uncertainty before a final confidence label.
- **Human-final report:** produce HTML, JSON, and Markdown artifacts for review instead of silently rewriting the answer.

## The Core Claim

```text
A source can be real and relevant, but still fail to prove the model's exact claim.
```

AI Judge is built around that boundary. It preserves the raw model answer, isolates evidence, audits claim support, keeps dissent visible, and produces a human-final report package instead of silently rewriting the answer.

## Try It First

Start with the public demo:

```text
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

Then read the short deterministic path:

```text
docs/TRY_AI_JUDGE_IN_3_MINUTES.md
```

The public proof path covers fake citations, weak support, irrelevant sources, contradicted claims, and overclaims where a real source supports a weaker proposition than the model answer asserted.

<p align="center">
  <img src="assets/citation-audit-space-output.png" alt="AI Judge citation audit public demo output" width="960">
</p>

The screenshot above shows the public demo output: citation status, isolated evidence, failure reason, and report artifacts. The production browser/runtime orchestration that powers private workflows stays outside this repository.

## Current Product Direction

The latest private line is report-first and closed-core:

| Layer | Public message |
|---|---|
| Source-isolated audit | Separate model text, model-mentioned sources, supplied evidence, fetched evidence, and audit result. |
| Claim-support gate | Check whether evidence supports the exact claim span, not just a related topic. |
| Overclaim detection | Identify causation, absolute, and quantified-effect overreach when evidence supports less than the answer asserts. |
| Dissent before confidence | Preserve blockers and disagreements before raising a final label. |
| Human-final reports | Generate HTML, JSON, and Markdown artifacts for review and signoff. |
| Agent trace audit | Explain source and tool-use gaps in agent-style workflows with sanitized public examples. |
| Local-first runtime | Keep production orchestration, browser sessions, model seats, and operator controls private. |

## Public Materials

| Public-safe asset | Purpose |
|---|---|
| `product/landing.html` | The current public showcase page. |
| `docs/TRY_AI_JUDGE_IN_3_MINUTES.md` | Fast proof path for the citation-audit wedge. |
| `citation-bench/citation-bench-100.jsonl` | Deterministic public citation cases. |
| `citation-bench/citation-bench-hard-11.jsonl` | Hard overclaim and claim-support cases. |
| `examples/` | Sanitized examples for public explanation. |
| `docs/PUBLIC_PRIVATE_BOUNDARY.md` | The publication boundary for future updates. |
| `docs/PUBLIC_EXPORT_MANIFEST.md` | The allowlist for clean public exports. |

## What Stays Private

- `core/`, `product/`, `bridges/`, `client/`, and runtime orchestration code in the private source of truth.
- Browser/CDP bridge internals, fixed-tab automation, web-seat adapters, and model-seat collection logic.
- Local run outputs, raw seat transcripts, legal case payloads, customer facts, browser captures, screenshots, cookies, and logs.
- Growth/outreach drafts with contact details, private emails, or partnership notes.
- Credentials, API keys, proxy settings, private environment files, and generated evidence packs.

## Public Boundary

AI Judge is a closed-core commercial product with public demos and benchmarks. Public materials should describe the workflow and the trust boundary accurately, without implying that the production runtime is public source.

Before publishing any branch, release, or artifact, read [`docs/PUBLIC_PRIVATE_BOUNDARY.md`](docs/PUBLIC_PRIVATE_BOUNDARY.md).

## Useful Links

- [Live Hugging Face Space](https://huggingface.co/spaces/reguorier/ai-judge-citation-audit)
- [3-Minute Proof](docs/TRY_AI_JUDGE_IN_3_MINUTES.md)
- [Public Showcase Page](product/landing.html)
- [Claim Span Roadmap](docs/CLAIM_SPAN_ROADMAP.md)
- [Agent Trace Audit](docs/ARC_AGENT_TRACE_AUDIT.md)
- [Public Export Manifest](docs/PUBLIC_EXPORT_MANIFEST.md)
