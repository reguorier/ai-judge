# AI Judge Launch Demo Kit

This kit is the one-step source for the 90-second launch demo, Product Hunt assets, Show HN post, and hackathon submission copy.

## Demo Page

Open locally:

```bash
open product/demo-video.html
```

Record the browser window at 1920x1080. The page auto-advances through a 90-second story and is designed to work as a silent demo with subtitles or as a narrated screen recording.

## 90-Second Voiceover

```text
AI answers can sound right and still fail judgment.

AI Judge is an open-source, local-first evaluation harness for developers who need more than another confident model response.

Instead of asking one model to judge another, AI Judge turns the answer into a jury workflow.

Multiple AI seats answer independently. Their claims are broken into a ledger. Then the output is scored with auditable formulas for evidence, calibration, disagreement, bluff risk, diversity, graph value, and judgment quality.

Version 3.2 adds the auditability layer: evidence objects, dissent challenges, risk routing, and reasoning-tree artifacts. So every important judgment can show why it deserves confidence.

For the Microsoft Agent Academy lane, a Copilot or Cowork agent can draft a plan, answer, or review. AI Judge then checks whether it is grounded, which claims are unsupported, whether the confidence is calibrated, and what falsifiable test should happen next.

The key design choice is simple: the AI does not take the gavel. The human keeps the final decision, but now sees the evidence, weak spots, disagreement, dissent, and reasoning path.

AI Judge is open source, local-first, and ready to run today.

Clone the repo, run the harness, add your own failure cases, and help define what trustworthy agent judgment should look like.
```

## Shot List

| Time | Visual | Voiceover beat |
|---:|---|---|
| 0-15s | Problem statement and risky model answer | Smart-sounding answers can still fail judgment |
| 15-30s | Jury workflow | Not another judge model, but a human-final judgment workflow |
| 30-45s | Evidence and reasoning tree | v3.2 adds evidence objects, dissent, risk routing, and traceable reasoning |
| 45-60s | Microsoft demo lane | Copilot/Cowork output enters AI Judge for verdicting |
| 60-75s | Hard Truth Mode | Expose confidence vs judgment-quality gaps |
| 75-90s | Repo and command | Open-source, local-first, ready to test |

## Product Hunt

Tagline:

```text
AI answers enter a jury. You keep the gavel.
```

Maker comment:

```text
I built AI Judge because model comparison often stops at "which answer sounded better?"

AI Judge asks a different question: which answer survives evidence, disagreement, calibration, and reproducible tests?

It turns one question into a human-final jury workflow. Multiple AI seats answer independently, claims are broken into an evidence ledger, auditable scoring functions inspect the result, and v3.2 adds evidence objects, dissent checks, risk routing, and a reasoning tree.

The final decision intentionally stays with the human. The goal is not to replace judgment with another black-box judge model; it is to make the weak spots visible before you trust an answer.

I would love feedback on the benchmark format and what real-world failure cases AI Judge should add next.
```

Gallery asset suggestions:

```text
1. Hero screenshot: README hero or product/demo-video.html opening frame
2. Architecture: assets/ai-judge-v3.2-tianfu-stack.svg
3. Reasoning tree: assets/ai-judge-v3.2-reasoning-tree.svg
4. Harness proof: harness-report.html
```

## Show HN

Title:

```text
Show HN: AI Judge - an open-source jury for evaluating AI answers
```

Post:

```text
I built AI Judge to catch a failure mode I keep seeing: an AI answer can be fluent, confident, and still not deserve trust.

AI Judge turns one question into a jury-style evaluation workflow. Multiple AI seats answer independently, their claims are broken into a ledger, and the result is scored with auditable formulas for evidence, calibration, bluff risk, disagreement, diversity, and judgment quality.

v3.2 adds the auditability layer: evidence objects, dissent challenges, risk routing, and reasoning-tree artifacts.

The final verdict stays with the human. AI Judge is meant to expose weak evidence and overconfident reasoning, not become another opaque judge model.

Repo: https://github.com/reguorider-gif/ai-judge
Demo page: product/demo-video.html in the repo

I would especially like feedback on what benchmark cases should be added and whether claim-level evaluation is the right interface for real decisions.
```

## 30-Second Short Video Script

```text
AI answers are getting smoother, but smooth is not the same as trustworthy.

AI Judge turns an AI answer into a jury workflow: independent seats, claim ledger, auditable scoring, disagreement checks, and a human-final verdict.

v3.2 adds evidence objects, dissent checks, risk routing, and reasoning trees.

The point is not to let AI take the gavel. The point is to help humans see what should and should not be trusted.

Try it on GitHub: reguorider-gif/ai-judge.
```

## Chinese Short Post

```text
AI Judge v3.2 已经上线。

它解决的不是“再让一个 AI 当裁判”，而是把 AI 回答拆成 claim ledger，再用可审计评分函数、证据对象、异议挑战、风险路由、推理树和 Hard Truth Mode 判断：这个答案到底该不该信。

核心原则：最后一票仍然是人。AI Judge 只负责把证据缺口、过度自信、分歧、异议和可验证下一步摊开。

GitHub: https://github.com/reguorider-gif/ai-judge
欢迎提交容易骗过 LLM 的真实案例。
```
