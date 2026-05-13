# Microsoft Agent Academy Submission Pack

This pack positions AI Judge for a Microsoft Agent Academy Hackathon submission. The public requirement page emphasizes a working agent that uses at least one Microsoft product, a short demo video, and an architecture overview.

Official target:

```text
https://microsoft.github.io/agent-academy/events/hackathon/
```

## Submission Angle

AI Judge is the reliability and evaluation layer for Microsoft agent workflows.

Instead of only showing a Copilot/Cowork agent completing a task, the demo shows the more important production question: should the output be trusted?

## Project Summary

```text
AI Judge is an open-source, local-first evaluation harness for Microsoft agent outputs. A Copilot/Cowork agent drafts a plan, answer, or code-review recommendation; AI Judge converts that output into a claim ledger, scores it with auditable formulas, checks disagreement and calibration risk, runs v3.1 benchmark/regression harnesses, and returns a human-final verdict package.
```

## Microsoft Product Lane

Primary lane:

```text
Copilot/Cowork style agent workflow
```

Fallback lane:

```text
GitHub Copilot / GitHub Actions workflow
```

Use the fallback only if a Microsoft Copilot Studio or Copilot Cowork environment is not available. The fallback is weaker for judging, but still connects AI Judge to a Microsoft-owned developer workflow through GitHub and CI.

## Demo Scenario

Prompt to the Microsoft agent:

```text
Draft a migration plan for adding AI evaluation gates to a multi-agent coding workflow. Include risks, acceptance criteria, and a rollout plan.
```

AI Judge task:

```text
Evaluate the Microsoft agent's plan. Identify unsupported claims, missing tests, overconfident assumptions, hidden risk, and the smallest falsifiable next step.
```

Expected demo result:

```text
AI Judge finds which claims are evidence-backed, which are only plausible, which risks are under-tested, and what a human should verify before accepting the agent plan.
```

## Architecture Overview

Use this image in the submission:

```text
assets/microsoft-agent-academy-architecture.svg
```

Architecture narrative:

```text
The Microsoft agent produces a plan or answer. AI Judge ingests the output, extracts claims into an evidence ledger, applies auditable scoring functions and judgment-quality proxy signals, runs harness checks, and returns a human-final verdict with confidence gaps and next repair actions.
```

## Five-Minute Demo Structure

| Time | Segment | Content |
|---:|---|---|
| 0:00-0:30 | Problem | Agent answers can be fluent without being trustworthy |
| 0:30-1:15 | Microsoft agent | Show Copilot/Cowork producing a plan |
| 1:15-2:15 | AI Judge run | Feed the plan into AI Judge and produce verdict output |
| 2:15-3:15 | Harness proof | Show golden benchmark, regression checks, and HTML report |
| 3:15-4:15 | Architecture | Show the Microsoft agent -> claim ledger -> scoring -> human verdict flow |
| 4:15-5:00 | Why it wins | Local-first, auditable, human-final, open-source, useful beyond the demo |

## Application Answers

Project name:

```text
AI Judge for Microsoft Agent Reliability
```

Short description:

```text
An open-source evaluation harness that turns Microsoft agent outputs into auditable, human-final verdicts.
```

Long description:

```text
AI Judge is a local-first evaluation harness for agent reliability. In the Microsoft Agent Academy demo, a Copilot/Cowork agent drafts a plan or answer, then AI Judge turns that output into an evidence ledger, scores it with auditable formulas, checks calibration and disagreement risk, runs v3.1 benchmark/regression gates, and returns a human-final verdict package.

The project addresses a practical production problem: agents can sound confident while hiding unsupported claims, missing tests, or weak reasoning. AI Judge does not replace the human with another opaque judge model. It exposes the evidence, weak spots, and next falsifiable actions so the human can make a better final decision.
```

What makes it original:

```text
Most agent demos focus on task completion. AI Judge focuses on trust after task completion: claim auditing, disagreement inspection, bluff-risk detection, benchmark regression, Hard Truth Mode, and human-final verdicts. It is a meta-agent layer that can improve reliability across many Microsoft agent workflows.
```

Technical implementation:

```text
Python CLI, Codex skill entrypoint, Docker/Docker Compose, GitHub Actions CI, golden benchmark fixtures, regression checks, HTML harness reports, auditable scoring functions, judgment-quality proxy signals, and Microsoft agent output packets.
```

Impact:

```text
Agent builders get a repeatable way to inspect output quality before deployment. Teams can compare competing agent plans, record failure cases, add benchmark fixtures, and publish evidence-backed verdict reports. The result is better trust hygiene for Microsoft agent workflows.
```

## Submission Checklist

- [x] Public repo: https://github.com/reguorider-gif/ai-judge
- [x] v3.1 release: https://github.com/reguorider-gif/ai-judge/releases/tag/v3.1.0
- [x] Harness report: `harness-report.html`
- [x] 90-second demo page: `product/demo-video.html`
- [x] Architecture image: `assets/microsoft-agent-academy-architecture.svg`
- [x] Copilot/Cowork packet: `examples/microsoft_agent_academy/copilot_cowork_packet.md`
- [x] Recording guide: `docs/RECORDING_GUIDE.md`
- [x] One-click launch recorder: `Record-AI-Judge-Demo.command`
- [x] One-click Microsoft submission recorder: `Record-Microsoft-Agent-Academy.command`
- [ ] Actual Microsoft agent recording
- [ ] Final video export under five minutes
- [ ] Submit on the official Microsoft form

## Honest Blocker

The final hackathon submission should not be sent until there is a recorded Microsoft product touchpoint. The repo is now ready for that step, but the strongest submission needs one visible Copilot/Cowork/Copilot Studio/GitHub Copilot scene in the demo video.
