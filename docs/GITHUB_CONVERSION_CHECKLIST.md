# GitHub Conversion Checklist

This checklist keeps the public GitHub repository focused on product
understanding, runnable proof, and useful contribution loops.

## Repository Metadata

Use this public description:

```text
Source-isolated claim-support audit for AI-generated answers.
```

Use this homepage:

```text
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

Suggested topics:

```text
ai-safety, llm-evaluation, citation-audit, claim-verification,
hallucination-detection, ai-agents, developer-tools, local-first,
source-isolation, human-in-the-loop
```

Avoid topics that point visitors toward the old product shape unless the public
page again supports that claim directly.

## First-Visit Path

A GitHub visitor should be able to do four things without asking the owner:

1. Open the live Hugging Face demo.
2. Read the 3-minute proof.
3. Inspect one hard overclaim case.
4. Open a structured public-safe issue.

The README, landing page, and issue templates now all route visitors through
that path.

## Weekly Maintenance Loop

Run this once per week during launch experiments:

```bash
python3 scripts/verify_public_snapshot.py
gh repo view reguorier/ai-judge --json stargazerCount,forkCount,issues,repositoryTopics,description,homepageUrl
gh issue list -R reguorier/ai-judge --state open --limit 20
```

Then check:

- Did any issue include a reusable public benchmark case?
- Did visitors ask for batch audit, CI, PDF, Docx, or report-review workflows?
- Did the live demo still load?
- Did README links still resolve locally?
- Did the repository description still match the current product wedge?

## Why Stars Were Weak

The old public surface mixed several product stories: local jury, macOS app,
multi-model seats, closed-core runtime, and citation audit. That made it hard
for a stranger to know what to try or why to star.

The fix is a narrower promise:

```text
A real source can still fail to support the exact generated claim.
```

Everything public should reinforce that promise with a demo, a hard case, or a
contribution path.

## Owner Rule

Do not publish private runtime code to get more stars. If a visitor needs proof,
add a public-safe example, report, benchmark case, or live demo path instead.
