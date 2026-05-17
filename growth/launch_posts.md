# AI Judge Citation Audit Launch Posts

## Hacker News

Title:

```text
Show HN: AI Judge - open-source citation auditor for AI-generated answers
```

First comment:

```text
I built AI Judge Citation Audit because LLM answers increasingly include citations that look real enough to pass a quick read but fail once you separate the model text from external evidence.

The tool is intentionally narrow: paste an AI-generated answer, optionally provide external evidence, and it labels each citation as verified, weakly_verified, irrelevant, unverifiable, or contradicted. It also produces a Certification ID, Replay Ledger hash, and HTML/JSON report.

The important design choice is source isolation: a URL mentioned by the model is treated as a candidate source, not proof. It only upgrades when supplied or fetched as external evidence.

Repo: https://github.com/reguorier/ai-judge
Live Space: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Demo command:
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md --html reports/fake-citation-audit.html --json reports/fake-citation-audit.json

I would especially like benchmark cases that fool current LLM citation checks.
```

## Reddit r/LocalLLaMA

Title:

```text
I made a local-first benchmark and auditor for hallucinated citations in LLM answers
```

Post:

```text
I kept seeing AI answers cite plausible reports, surveys, and papers that were either nonexistent or did not support the claim. I built a narrow local-first tool around that failure mode.

AI Judge Citation Audit takes an AI-generated answer and external evidence, then labels citations as verified / weakly_verified / irrelevant / unverifiable / contradicted. It also keeps a Replay Ledger so model text, mentor notes, and external evidence remain separated.

It does not need model APIs for the basic demo. The first benchmark has 100 synthetic cases across verified, weak, irrelevant, unverifiable, and contradicted citations.

Repo: https://github.com/reguorier/ai-judge
Live demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

What I want from this community: nasty citation hallucination examples and suggestions for better benchmark cases.
```

## HuggingFace Community

Title:

```text
AI Judge Citation Audit: a tiny benchmark + Space for hallucinated citations
```

Post:

```text
I am launching AI Judge Citation Audit, a local-first citation auditor for AI-generated answers.

The Space lets you paste an answer and external evidence. The audit separates model-cited candidate sources from supplied/fetched evidence, then returns citation-level status labels and a report.

The benchmark starts small on purpose: 100 deterministic cases, no model API required. I am looking for community cases that expose fake citations, irrelevant references, and claims that sound sourced but are not actually supported.

GitHub: https://github.com/reguorier/ai-judge
Space: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```

## V2EX

Title:

```text
做了一个本地优先的 AI 引用审计器，专门抓 AI 回答里的假引用和无关引用
```

Post:

```text
最近 AI 回答越来越喜欢带引用，但很多引用只是“看起来像证据”。我把 AI Judge 收窄成了一个更具体的工具：Citation Audit。

它做一件事：把 AI 原文、模型提到的候选来源、外部证据分开，然后给每条引用打状态：

verified / weakly_verified / irrelevant / unverifiable / contradicted

重点是 unverifiable 不是 false，只是当前没有外部证据能验证。模型自己提到的 URL 也不能直接给自己作证。

Repo: https://github.com/reguorier/ai-judge
在线 demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
本地 demo:
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md --html reports/fake-citation-audit.html

欢迎丢一些你见过的 AI 假引用案例，我想把 benchmark 做扎实。
```

## X Thread

```text
I built AI Judge Citation Audit: an open-source tool that catches fabricated, weak, irrelevant, unverifiable, and contradicted citations in AI-generated answers.

The key rule: model-mentioned sources do not verify themselves.

Paste answer -> add evidence -> get citation-level audit + Certification ID + Replay Ledger.

GitHub: https://github.com/reguorier/ai-judge
Live demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
```
