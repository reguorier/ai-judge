# Xiaomi MiMo 100T Application Draft - AI Judge

Status: prepared, not submitted
Page observed: `https://100t.xiaomimimo.com/`

## Guardrail

Do not submit automatically. This form sends personal email, project claims,
links, and optional proof files to a third party. Fill/submit only after explicit
confirmation.

## Recommended Checkbox Choices

AI development / Agent tools:

- Codex
- Claude Code
- Cursor or Windsurf if currently used
- Other, if the form allows describing AI Judge's web-seat automation

Base model families:

- Claude series
- GPT series
- Gemini series
- DeepSeek series
- Doubao series
- MiniMax series
- Other, for Qwen/Kimi/Grok/Yuanbao web seats if needed
- MiMo series, only if the application is explicitly about testing MiMo in AI
  Judge rather than claiming current heavy usage

## 04 Project Description Draft

我正在构建 AI Judge，一个面向 AI Agent、RAG 输出和引用密集型报告的评测与裁判层。项目的核心痛点是：现在很多 AI 系统可以快速生成答案，但团队很难判断这些答案能否被发布、交付或执行。尤其是 citation / source 场景里，模型经常引用真实来源，但把“相关”写成“导致”，或者把有限证据夸大成确定结论。AI Judge 的目标不是再做一个聊天机器人，而是在答案进入用户之前，提供一个可审计、可复盘、有人类签字的质量门禁。

当前系统已经实现了多模型席位、网页席位回收、引用审计、claim-support 审计、Replay Ledger、Certification ID、HTML/JSON 报告、macOS 桌面端和 Hugging Face 在线 demo。典型流程是：输入一个 AI 生成答案或 Agent 执行轨迹，系统保留原始回答，分离外部证据层，抽取引用和主张，再让多个模型席位从不同角度评审，最后输出可解释的判定和下一步人工复核建议。最近我还把 ARC / Agent eval 的方向扩展成 Agent Trace Audit，用来审查 Agent 是否探索充分、规则是否有证据、是否遗漏替代假设。

我希望申请 MiMo token 用于批量评测中文/英文多席位判断、Agent trace verdict、引用审计和模型互评稳定性。AI Judge 对模型的需求不是单轮聊天，而是长链任务：同一问题需要多个席位独立回答、互评、生成结构化 verdict，再把结果落到本地报告和桌面端工作台里。MiMo 的长上下文和推理能力可以帮助我测试更多中文真实案例、社媒内容审核、创业申请材料审查和 Agent 输出质量门禁。

## 05 Proof Links

Use links first; upload files only if the form requires them.

- GitHub: https://github.com/reguorier/ai-judge
- Live demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
- Agent Trace Audit doc: https://github.com/reguorier/ai-judge/blob/main/docs/ARC_AGENT_TRACE_AUDIT.md
- Agent trace demo report: https://github.com/reguorier/ai-judge/blob/main/reports/agent-trace-demo.html
- 3-minute proof kit: https://github.com/reguorier/ai-judge/blob/main/docs/TRY_AI_JUDGE_IN_3_MINUTES.md

## Submit Boundary

Before submitting, verify:

- Email is the intended mailbox for MiMo account/review results.
- Tool/model checkboxes match actual usage.
- No claim implies official ARC, OpenReview, MiMo, or MiraclePlus partnership.
- Optional files are under the stated size limit and do not expose private
  browser sessions, mail, passwords, tokens, or personal data.
