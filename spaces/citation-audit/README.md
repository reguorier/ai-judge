---
title: Ai Judge Citation Audit
emoji: 🚀
colorFrom: yellow
colorTo: green
sdk: gradio
sdk_version: 4.44.1
python_version: "3.11"
app_file: app.py
pinned: false
short_description: source-isolated citation and claim-support audit for AI answers
---

# AI Judge Citation Audit Space

This HuggingFace Space is the public self-serve demo for AI Judge Citation Audit.

## What it demonstrates

- Separates submitted AI text from external evidence.
- Labels citations as `verified`, `weakly_verified`, `irrelevant`, `unverifiable`, or `contradicted`.
- Shows why an item is `unverifiable`: missing evidence, unfetched model candidate, fetch error, blocked retrieval, weak match, or no citation.
- Shows evidence provenance: model candidate, user-supplied, fetched, independently attested, or notarized.
- Separates citation status from claim support, including the real-source / overclaimed-causation case.
- Preserves Certification ID, Replay Ledger hash, and Evidence Broker summary.
- Runs without model APIs or browser bridges.

## Launch checklist

1. Create a new HuggingFace Space named `ai-judge-citation-audit`.
2. Select Gradio as the SDK.
3. Upload this folder plus the repository `core/` package, or deploy from the full GitHub repository with this folder as the Space root.
4. Pin the Space README to the GitHub repository: `https://github.com/reguorier/ai-judge`.

## Demo prompts

The Space includes two built-in examples:

- Fabricated Stanford-style citation: expected `unverifiable`, not false.
- Real source, unsupported causal claim: expected citation `verified`, source `relevant`, claim support `contradicted`.
