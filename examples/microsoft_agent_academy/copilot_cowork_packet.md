# Copilot/Cowork Demo Packet for AI Judge

Use this packet to create the Microsoft Agent Academy demo scene. The goal is to show a Microsoft agent producing a plausible plan, then AI Judge evaluating whether the plan deserves trust.

## Microsoft Agent Prompt

```text
You are a Microsoft Copilot/Cowork agent helping a software team add evaluation gates to a multi-agent coding workflow.

Draft a migration plan that includes:
1. the architecture change,
2. risks,
3. acceptance criteria,
4. rollout steps,
5. what evidence the team should collect before trusting the new workflow.

Keep the answer concise but specific.
```

## Example Microsoft Agent Output

```text
We should add an evaluation gate after each agent produces a code change. The gate will run automated tests, score the output for correctness, and block risky changes before merge.

Architecture:
- Agent produces a patch.
- CI runs tests and lint.
- AI Judge reviews the agent's reasoning, assumptions, and risk.
- The human maintainer gets a verdict report before merging.

Risks:
- False positives may slow developers down.
- Evaluation scoring may miss subtle issues.
- The gate may be hard to tune for different repositories.

Acceptance criteria:
- CI passes on every pull request.
- The evaluation report identifies unsupported claims and missing tests.
- Developers can override the verdict with a reason.
- The team records recurring failure cases as benchmark fixtures.

Rollout:
- Start with advisory reports only.
- Add benchmark cases from real failures.
- Turn on blocking only for high-risk changes.
- Review the false-positive rate weekly.

Evidence to collect:
- Regression pass rate.
- Number of useful verdict findings.
- Override rate.
- Developer feedback.
```

## AI Judge Evaluation Prompt

```text
Evaluate the Microsoft agent output below.

Focus on:
1. Which claims are evidence-backed?
2. Which claims are plausible but unsupported?
3. What could fail in production?
4. Does the plan include falsifiable acceptance criteria?
5. What is the smallest next test before trusting this plan?

Return:
- claim ledger,
- unsupported claims,
- judgment-quality score,
- hard-truth level,
- human-final recommendation.
```

## Expected AI Judge Verdict

```text
Verdict: revise before trust.

Why:
- The plan is structurally sound but makes unsupported claims about scoring correctness and blocking risky changes.
- It includes useful rollout steps, but lacks thresholds for false positives, override review, and what qualifies as "high-risk."
- It names metrics but does not define minimum acceptable values.

Smallest falsifiable next test:
Run AI Judge on 10 historical agent/code-review failures. The gate is useful only if it catches at least 7 of 10 known failures while producing no more than 2 false positives on known-good changes.
```

## CLI Demo Commands

From repo root:

```bash
PYTHONPATH=. python3 tests/run_harness.py
python3 cli/main.py hard-truth --demo
python3 cli/main.py v3-pipeline --demo
```

## Narration Beat

```text
The Microsoft agent completed the task. AI Judge answers the next production question: should we trust it?
```
