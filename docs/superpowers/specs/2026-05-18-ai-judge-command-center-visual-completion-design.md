# AI Judge Command Center Visual Completion Design

## Goal

把现有 `AI Judge v3.6.1 Command Center` 从“状态总览”补齐成可操作的桌面审计工作台，覆盖最终方案中的任务详情、导师门禁、网页桥接健康、证据链、COUNCIL-004 席位人格、发布硬门禁和报告出口。

## Scope

本轮只改桌面网页界面：

- `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.html`
- `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js`

不改 API 协议、不改 Swift 壳、不改桥接后端、不改现有未提交测试文件。

## Design

首页保留为 Command Center，但把静态任务表升级为可以点击的任务详情。右侧 Inspector 展示当前任务的阶段、阻断项、下一步动作、桥接健康和通知状态，让用户知道应该去哪一个页面处理。

请求录入页继续承载导师预检，但增加 Mentor Gate Checklist，使“先帮我想清楚”不只是开关，而是明确的清晰度、风险、复杂度、路由和确认状态。

证据审查页从静态文案升级为 Reasoning Tree。它从当前判词、理由、下一步、网页席位原始结果和执行轨迹中生成 claim -> evidence -> dissent/blocker -> action 的审查树；没有判词时展示可执行的等待态。

模型对比页保留现有专业版 arena，并补充 COUNCIL-004 席位人格和 L1/L2/L3 追踪面板：每个席位显示 MBTI、强项、通道、健康、最近证据和风险标签。

发布门禁从 4 项扩展到硬性 checklist：判词生成、导师确认、席位覆盖、网页回收、证据链、分歧处理、风险披露、审计日志、人工确认。通过状态由当前 verdict、bridge、trace 和人工确认共同计算。

## Acceptance

- 页面加载时没有 JavaScript 语法错误。
- 任务中心能切换选中任务并同步 Inspector。
- 无判词、运行中、有判词三种状态都能渲染证据树和发布门禁。
- 简约版仍保持摘要，专业版显示更多诊断。
- 所有新增 UI 在桌面宽度下不破坏当前布局。
