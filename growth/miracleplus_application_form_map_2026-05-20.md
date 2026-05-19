# MiraclePlus Application Form Fill Map - AI Judge

Date: 2026-05-20  
Official entry checked in Chrome: `https://www.miracleplus.com/apply/`  
Application portal reached: `https://apply.miracleplus.com/users/sign_up?...`  
Current blocker: account registration is waiting on phone/SMS verification. Codex should not enter OTPs, create the account, or submit the final application without action-time confirmation.

## Source Notes

- Official apply page says the 2026 fall batch is open and the regular application deadline is 2026-06-12 20:00.
- Official apply page lists support contact as `support@miracleplus.com`.
- Official "how to apply" guidance emphasizes concrete, pragmatic answers: target users, what you are building, why now, what is extraordinary about the founders.
- Official FAQ says MiraclePlus reviews application forms directly rather than requiring a BP first; the form itself should be treated as the core artifact.

## Registration State

| Step | Status | Notes |
|---|---|---|
| Open apply page | Done | Page loaded in Chrome. |
| Enter application portal | Done | Portal opened at `apply.miracleplus.com`. |
| Register/login | Blocked | Phone verification / account creation boundary. User must complete OTP and final account creation. |
| Fill application | Ready after login | Use the answer bank below. |
| Final submit | Needs explicit confirmation | External high-stakes application. |

## Core Application Answers

### Company / Project Name

AI Judge

### One-Liner

AI Judge 是 AI Agent 时代的质量裁判层：用多模型陪审、引用审计、证据链和人类签字，判断 AI 输出能不能发布、交付或执行。

### What Are You Building?

我们在做一个面向 AI Agent、RAG 和 AI 生成报告的评测与裁决基础设施。它不是另一个聊天机器人，而是在 AI 输出进入客户、论文、报告、README 或业务流程之前，检查这个输出是否有证据、引用是否真的支撑主张、不同模型是否存在关键分歧，并生成可复盘的 human-signoff verdict。

第一阶段的切入口是 citation support audit：很多系统只检查“引用是否存在”，但真实风险是“来源真实、相关，却不能证明模型写出来的结论”。AI Judge 会把 claim-source pair 拆出来，判定 verified / weakly verified / irrelevant / unverifiable / contradicted，并输出 HTML/JSON 报告。

### Why Now?

2026 年之后，AI Agent 正从 demo 进入业务流程。企业会开始追问三个问题：这个 AI 输出为什么可信？出了错谁负责？能不能在发布前留下一条可审计的判断链？

单模型自评很容易自信但错误；普通 RAG eval 又常常停留在检索指标。AI Judge 的机会在中间：把模型输出变成可审计、可复盘、可交给人类签字的判断结果。

### Target Users

1. 正在把 AI Agent 接入客户工作流的创业团队。
2. 需要向企业客户证明引用有效性的 RAG 产品团队。
3. 用 AI 生成客户报告、法律/咨询/研究 memo 的专业服务团队。
4. 需要快速技术尽调 AI startup 输出质量的投资人/加速器分析师。
5. 做开源 eval / agent benchmark 的开发者社区。

### Pain Point

现在 AI 产品上线前缺一个“输出质量门禁”。团队知道模型答了什么，但不知道：

- 这个答案的关键主张是否被证据支持；
- 引用是否只是看起来相关；
- 多个模型是否在复制同一个错误；
- 哪些分歧必须先暴露给人类负责人；
- 最终判断能不能被追溯和复盘。

### Product Demo Narrative

5 分钟 demo：

1. 输入一个带引用但有风险的 AI 答案。
2. AI Judge 抽取 claim + source。
3. 多个模型席位独立审计 claim-source support。
4. 系统暴露分歧、证据缺口和不可验证项。
5. 输出人类可签字的 verdict report。

一句话演示点：来源存在不等于结论成立。

### Why This Team / Founder

创始人已经把 AI Judge 从命令行、引用审计、桌面端、多网页模型席位、Hugging Face demo、benchmark case、GitHub 开源仓库一路推进到可演示版本。项目的特点不是只有想法，而是已经形成了可运行代码、测试、文档、公开 demo、社媒增长材料和具体商业化假设。

当前仓库：`https://github.com/reguorier/ai-judge`

### Traction To Use Carefully

| Signal | Current State |
|---|---|
| GitHub repo | Public: `https://github.com/reguorier/ai-judge` |
| GitHub stars | 3 as of 2026-05-20 |
| HF demo | `https://huggingface.co/spaces/reguorier/ai-judge-citation-audit` |
| Benchmark | Citation audit cases in `citation-bench/` |
| Desktop/web run | `ddb4902f3369`, staged council result, 8/10 non-Grok valid seats |
| Tests | `37 passed` for product/report state tests |

Important wording: do not claim full consensus from run `ddb4902f3369`; say "staged multi-seat advisory run" because the final machine verdict was `unverified / 0%` due incomplete required seats.

### Business Model

First paid wedge:

- Citation Support Audit Sprint: audit 20-50 AI-generated outputs and return a claim-source verdict report, evidence-gap summary, and publishing checklist. Price hypothesis: USD 2,000-5,000 per sprint.

Expansion:

- Agent Output Gate: audit agent traces before customer pilots. Price hypothesis: USD 3,000-8,000 per pilot.
- Hosted Team Review: private team dashboard, review history, signoff, exportable reports. Price hypothesis: USD 299-1,500/month.

### Competitors / Alternatives

Alternatives include manual human review, RAG eval dashboards, citation checkers, single LLM-as-judge scoring, and model comparison tools.

AI Judge differs because it focuses on claim-source support, model-seat dissent, replayable evidence, and human signoff rather than only preference scores or retrieval metrics.

### What Do You Need From MiraclePlus?

1. Sharp product positioning: citation audit wedge vs broader agent evaluation platform.
2. First 10 design partners from AI Agent / RAG / AI consulting teams.
3. Help turning open-source attention into commercial pilots.
4. Fundraising narrative for AI evaluation infrastructure.
5. Feedback on China/US dual GTM: GitHub/HF/ARC community outside China, MiraclePlus/AI Agent ecosystem inside China.

## 1-Minute Founder Video

大家好，我是刘伟迪，我们在做 AI Judge。

今天 AI Agent 最大的问题不是不会回答，而是它答得很自信，但没人能证明它该不该被相信。一个真实来源可能只说“相关”，模型却写成“导致”；一个 Agent 可能完成了任务，但没有任何可复盘的判断链。

AI Judge 是一个多模型陪审团系统。它让多个模型独立评审同一个答案，抽取主张，审计引用，暴露分歧，最后交给人类签字。我们的切入口是 citation audit，扩展方向是 Agent trace evaluation。

我们希望把 AI Judge 做成 Agent 经济里的质量门禁：每家公司上线 AI Agent 前，都需要一个能回答“这个输出能不能发布”的裁判层。

## Final Submit Guard

Before final submission, verify:

- Founder name, phone, and email are correct.
- Whether company/entity name should be `AI Judge`, `Flywise`, or another legal/operating name.
- Whether to mention current 3-star GitHub baseline or omit early traction number.
- Whether founder video has been recorded.
- Whether all claims about web run are framed as staged advisory, not full consensus.
