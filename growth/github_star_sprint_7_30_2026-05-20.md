# GitHub Star Sprint - 7 Days and 30 Days

Goal: convert AI Judge from "interesting local tool" into a star-worthy open-source evaluation layer.

## Success Metrics

| Time | Target |
|---|---|
| 72 hours | README improved, 4 launch drafts ready, 20 outreach targets prepared |
| 7 days | First public launch wave completed after user confirmation |
| 30 days | Repeatable star sources identified: HN, Reddit, HF, X/LinkedIn, targeted DMs |

## 7-Day Sprint

| Day | Action | Asset | Status |
|---|---|---|---|
| D1 | Improve README top positioning | README changed | Done |
| D1 | Add launch tracker | This file | Done |
| D2 | Record or select 30s demo GIF | Use existing `assets/ai-judge-v3-hero.png` + `assets/citation-audit-space-output.png` immediately; record `assets/demo.gif` after next UI pass | Immediate asset selected |
| D2 | Create Show HN post | Draft below | Ready |
| D3 | Create Reddit LocalLLaMA post | Draft below | Ready |
| D3 | Create X thread | Draft below | Ready |
| D4 | Create LinkedIn post | Draft below | Ready |
| D4 | Reach 20 target people | `outreach_targets_20_2026-05-20.csv` | Ready, external send needs confirmation |
| D5 | Push GitHub issues/discussions for case contributions | Existing public issues #2/#3/#4/#5 + README CTA | Ready |
| D6 | Product Hunt prep | tagline + description below | Ready |
| D7 | Review metrics | Current GitHub stars: 3; collect HN/Reddit/HF/X metrics after first confirmed posts | Baseline captured |

## 30-Day Plan

| Week | Theme | Actions |
|---|---|---|
| Week 1 | Make the repo instantly understandable | README, demo GIF, HF Space, launch posts |
| Week 2 | Collect developer critique | HN, Reddit, GitHub Discussions, HF discussion |
| Week 3 | Publish proof cases | 10 real-source unsupported-claim examples |
| Week 4 | Convert attention into leads | Pro audit offer, MiraclePlus/YC memo, 20 warm followups |

## Show HN Draft

Title:

`Show HN: AI Judge - an open-source multi-model jury for AI answers`

Body:

I built AI Judge because the failure mode I keep seeing is not just fake citations. It is when the source is real, relevant, and still does not prove what the AI wrote.

AI Judge sends the same task to multiple model seats, extracts claims, audits citation support, preserves dissent, and produces a human-readable verdict before publication.

The first wedge is citation/claim-support audit. The larger direction is agent trace evaluation: before an agent output reaches a customer, it should survive evidence review and human signoff.

Repo: https://github.com/reguorier/ai-judge  
Live demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit  

I would especially value critique on:

1. Is multi-model judging useful if the evidence chain is visible?
2. What benchmark cases would convince you this is not just another wrapper?
3. Where should the open-source / paid boundary be?

## Reddit Draft - r/LocalLLaMA

Title:

`I made multiple AIs judge the same answer. The disagreement was more useful than the answer.`

Body:

I am building AI Judge, an open-source multi-model jury for AI answers and citations.

The key problem: a model can cite a real source, but overclaim what that source proves. Example: source says "associated with"; model writes "caused by". A normal citation checker may pass it. AI Judge tries to judge the claim-source pair.

It runs multiple model seats, keeps dissent, scores claims, and outputs a human-signoff verdict.

Repo: https://github.com/reguorier/ai-judge  
Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

Would this be useful for local RAG / agent workflows, or is a single strong judge model enough?

## X Thread Draft

1. I am building AI Judge: an open-source jury layer for AI outputs.
2. The scary failure is not "fake source". It is "real source, unsupported claim".
3. Example: source says associated with. Model writes caused by. The citation exists, but the claim is not proven.
4. AI Judge sends the answer to multiple model seats, extracts claims, audits evidence, and preserves dissent before confidence.
5. First wedge: citation support audit. Bigger goal: agent trace evaluation before AI actions reach users.
6. Repo: https://github.com/reguorier/ai-judge. Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

## LinkedIn Draft

Most AI teams already know how to generate outputs. Fewer know how to decide whether those outputs are safe to publish.

AI Judge is an open-source evaluation layer for AI-generated answers, RAG citations, and agent traces. It does not ask only "which model sounded best?" It asks whether the answer has evidence, whether the citation proves the claim, and whether dissent was reviewed before human signoff.

We are starting with citation-support audit because it is concrete: a source can be real and still fail to prove the model's claim.

Looking for AI teams that publish AI-generated reports, memos, RAG answers, or agent outputs and want to test this against real cases.

## Product Hunt Prep

Name: AI Judge  
Tagline: Multi-model jury for AI answers, citations, and agent traces.  
Short description: AI Judge audits whether AI outputs can survive evidence, dissent, and human signoff before publication.  
First comment: We built this because "real source, unsupported claim" is one of the most dangerous AI failure modes. Please try the citation audit demo and send cases that break it.

## GitHub Issues / Discussions To Pin

| Issue | Purpose |
|---|---|
| Hard citation hallucination cases | Invite contributors to submit benchmark cases |
| Real source, unsupported claim | Show unique wedge |
| Agent trace audit examples | Bridge from citation audit to ARC/Agent eval |
| Pro audit intake | Convert professional interest |

## Do Not Do Yet

- Do not buy fake stars.
- Do not spam every AI subreddit with the same post.
- Do not claim full AI Judge council consensus while web run `ddb4902f3369` is marked incomplete.
- Do not lead with "9 AI council" if the demo does not show immediate user value.
