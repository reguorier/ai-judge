# Zhihu / Chinese Long-Form Launch Post

Status: ready for publish queue

## Title

```text
我做了一个 AI 引用审计工具：专门抓“看起来有来源，但其实不能证明”的回答
```

## Post

```text
这次我没有做一个“哪个模型更聪明”的评测，而是先做了一个更窄的问题：

AI 生成的回答里，每一个引用到底能不能被外部证据验证？

项目叫 AI Judge Citation Audit：
https://github.com/reguorier/ai-judge

在线 demo：
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

它输出五类结果：

1. verified：引用和外部证据强匹配，且相关。
2. weakly_verified：能弱匹配，但缺少 URL、DOI、页码等精确锚点。
3. irrelevant：来源可能存在，但不支持当前问题。
4. unverifiable：当前证据不足，不能确认。注意，这不是 false。
5. contradicted：外部证据明确反驳。

我认为这里最关键的设计不是分类器本身，而是隔离：

- 模型原文
- 模型自己提到的候选来源
- 外部证据
- 审计输出

这四层必须分开。否则最大的风险就是“用幻觉验证幻觉”。

现在它还不是完整的 Grand Judge，也不是自动事实核查平台。当前 MVP 只做引用验证，目标是在报告、论文草稿、README、产品方案、投资 memo 发布前，先抓出最危险的 citation 问题。

本地跑法：

PYTHONPATH=. python cli/main.py audit examples/fake-citation.md \
  --html reports/fake-citation-audit.html \
  --json reports/fake-citation-audit.json

Benchmark：

PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95

我现在最需要的不是点赞，而是困难样例：

- AI 编出来的论文/报告/标准
- 来源是真的，但根本不支持结论
- 来源和结论相互矛盾
- 回答读起来很专业，但证据链一查就塌

如果你遇到过这种 AI 引用问题，可以把可匿名化的样例发我，我会加入公开 benchmark。
```

## First Comment

```text
设计原则补充：

`unverifiable` 不是 `false`。它只表示当前隔离外部证据不足。

这是为了避免 AI Judge 过度审判。一个审计工具应该说清楚“不知道”的边界，而不是把“不知道”伪装成“错”。
```
