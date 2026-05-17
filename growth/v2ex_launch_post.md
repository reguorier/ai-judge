# V2EX Launch Post

Status: ready for publish queue

Target:

```text
https://www.v2ex.com/new
```

## Title

```text
做了一个本地优先的 AI 引用审计器，专门抓 AI 回答里的假引用和无关引用
```

## Post

```text
最近 AI 回答越来越喜欢带引用，但很多引用只是“看起来像证据”。我把 AI Judge 收窄成了一个更具体的工具：Citation Audit。

它做一件事：把 AI 原文、模型提到的候选来源、外部证据分开，然后给每条引用打状态：

verified / weakly_verified / irrelevant / unverifiable / contradicted

重点是 unverifiable 不是 false，只是当前没有外部证据能验证。模型自己提到的 URL 也不能直接给自己作证。

在线 demo：
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

Repo：
https://github.com/reguorier/ai-judge

困难样例征集：
https://github.com/reguorier/ai-judge/issues/2

本地 demo：
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md --html reports/fake-citation-audit.html

Benchmark：
PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95

欢迎丢一些你见过的 AI 假引用案例，我想把 benchmark 做扎实。
```

## Reply Handles

- 如果被问和 RAG eval 区别：这是发布前引用审计，不是通用 RAG 质量评估。
- 如果被问为什么不是 false：没有证据不等于反证。
- 如果被问是否联网：默认关联网保证 benchmark 可复现，需要时可开 Evidence Broker fetch。
- 如果被问是否能做 PDF/Docx：这是 Pro 方向，先收集真实工作流。
