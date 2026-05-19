# Agent Trace Verdict Example

This example shows how AI Judge can be positioned for ARC / Agent eval communities: not as a solver, but as an evaluator of an agent attempt.

## Task

An agent is given a grid-reasoning task. It must explore examples, infer the transformation, and produce a final output.

## Agent Trace

```text
Observation 1: Training example A maps a red block to the top-left.
Observation 2: Training example B maps a blue block to the bottom-right.
Hypothesis: Objects move toward the nearest corner matching their color.
Action: Apply rule to test grid.
Final answer: Move the green block to the top-left.
```

## AI Judge Review

| Dimension | Verdict | Reason |
|---|---|---|
| Exploration coverage | Weak | The trace considered color and corner location but did not test whether shape or size mattered. |
| Evidence for final rule | Unverifiable | The trace does not show an example involving a green block. |
| Missed alternatives | High risk | The transformation may depend on object order, not color. |
| Final answer confidence | Low | The final answer applies an unproven extrapolation. |
| Human signoff | Reject | Needs one more hypothesis check before publishing final answer. |

## Why This Matters

Agent benchmark leaderboards often score only final correctness. AI Judge can add a second layer:

- Did the agent explore enough?
- Did the final action follow from observed evidence?
- Which assumptions were untested?
- Would another model-seat dissent before final answer?

## ARC / Agent Eval Community Ask

Would a trace-level evaluator like this help teams compare agent attempts, or would it be noise unless tied to a formal benchmark score?

