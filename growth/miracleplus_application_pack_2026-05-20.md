# MiraclePlus Application Pack - AI Judge

Official entry: https://www.miracleplus.com/apply/  
Verified from official page/search snippet: 2026 autumn batch regular application deadline is 2026-06-12 20:00; support email shown as `support@miracleplus.com`. Recheck before final submit.

## One-Sentence Company

AI Judge is evaluation infrastructure for the agent economy: a multi-model jury that audits AI answers, citations, and agent traces before they reach users.

## Chinese Short Pitch

我们在做 AI Agent 时代的质量裁判层。现在每家公司都在把 AI Agent 接进业务流程，但绝大多数团队只知道“模型答了什么”，不知道这个答案有没有证据、不同模型是否互相抄同一个错误、以及最终能不能让人类负责人签字。AI Judge 用多模型席位、引用审计、互评评分和人类裁决，把 AI 输出变成可审计、可复盘、可发布的报告。

## Why Now

1. 2026 年 Agent 应用开始进入真实业务，输出质量和可追责性成为上线门槛。
2. 单模型评分很容易自信但错误；多模型陪审能暴露分歧和证据断点。
3. RAG 和报告生成已经普及，但“引用存在”不等于“引用证明了主张”。
4. 企业会为上线前评测、引用审计、客户交付前门禁付费。

## Problem

AI applications are moving from demos into workflows. The failure mode is no longer just hallucination. It is "real source, unsupported claim" and "confident agent action without reviewable evidence".

## Product

AI Judge sends the same task to model seats, collects answers, extracts claims, audits evidence, runs cross-review, isolates slow/failed seats, and produces a human-signoff verdict. The wedge is citation and claim-support audit; the expansion is agent trace evaluation.

## Demo Narrative For 5 Minutes

1. Input a suspicious AI answer with citations.
2. AI Judge splits claims and sources.
3. Multiple seats judge whether the source proves the claim.
4. Dissent is shown before confidence.
5. Human signs final verdict or rejects publication.

## What Makes It Different

| Common Tool | AI Judge Difference |
|---|---|
| Chatbot comparison | Judges evidence support and dissent, not just preference |
| RAG eval dashboard | Produces human-readable verdicts and replay ledgers |
| Single LLM-as-judge | Uses multiple seats and isolates model/site failures |
| Generic benchmark | Can become a workflow gate before publishing AI output |

## Traction / Evidence To Insert

Use only real numbers before submission:

- GitHub stars: 3 as of 2026-05-20 13:00 Asia/Hong_Kong
- HF Space link: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
- Demo reports: existing `reports/` gallery
- Citation benchmark cases: `citation-bench/`
- Desktop/web run evidence: `ddb4902f3369`, staged council with 8/10 non-Grok valid seats

## 1-Minute Founder Video Script

大家好，我是 [姓名]，我们在做 AI Judge。

今天 AI Agent 最大的问题不是它不会回答，而是它答得很自信，但没人能证明它该不该被相信。一个真实来源可能只说“相关”，模型却写成“导致”；一个 Agent 可能完成了任务，但没有任何可复盘的判断链。

AI Judge 是一个多模型陪审团系统。它让多个模型独立评审同一个答案，抽取主张，审计引用，暴露分歧，最后交给人类签字。我们的切入口是 citation audit，扩展方向是 Agent trace evaluation。

我们希望把 AI Judge 做成 Agent 经济里的质量门禁：每家公司上线 AI Agent 前，都需要一个能回答“这个输出能不能发布”的裁判层。

## Application Answer Drafts

### What are you building?

AI Judge is an open-source evaluation and judgment layer for AI-generated outputs. It uses multiple model seats to review the same answer, checks whether citations actually support claims, highlights dissent, and produces an auditable verdict for human signoff.

### Who are your users?

Initial users are AI agent builders, RAG teams, content/report teams, AI consultants, and startups that ship AI-generated documents or workflows to customers.

### What is the first paid wedge?

Citation Support Audit Sprint: we audit a team's AI-generated reports or RAG outputs, identify unsupported claims, and deliver a verdict report plus a reusable CI/checklist workflow.

### Why will this become a company?

As AI agents move into production, companies need a quality gate that is independent from the model generating the answer. This can expand from citation audit to agent trace evaluation, compliance review, and hosted evaluation infrastructure.

### What is the key risk?

The category can sound broad. We reduce this risk by starting from a narrow, painful, demonstrable wedge: real-source-but-unsupported-claim detection.

## Submission Checklist

| Item | Status |
|---|---|
| Founder video | Draft ready, needs recording |
| Demo URL | HF Space ready, recheck live before submit |
| GitHub repo | Ready, README top improved |
| Deck | Text deck outline ready in this pack; visual export can be generated after user chooses 5-slide or 8-slide format |
| Metrics | Insert current stars / visits / user feedback |
| External submission | Needs user confirmation |
