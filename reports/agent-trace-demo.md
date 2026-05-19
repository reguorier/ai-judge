# AI Judge Agent Trace Audit

Audit ID: `agent-trace-demo-001`
Task ID: `arc-style-demo-001`
Trace status: `weakly_supported`
Human gate: `reject_until_rechecked`
Replay ledger hash: `sha256:a4dcbda7e0202f12a8a187fe98559d81019314e6bc9f98bc3f91189c323e049a`

## Task

Review whether an agent's grid-rule trace is supported enough to trust the final answer.

## Trace Verdict

| Dimension | Verdict |
|---|---|
| Exploration coverage | `partial` |
| Rule support | `unverifiable` |
| Unsupported final tokens | `green` |

## Observed Evidence

- Training example A maps a red block to the top-left corner.
- Training example B maps a blue block to the bottom-right corner.

## Actions

- Apply the color-corner rule to the test grid without checking shape, size, or object order.

## Hypothesis

Objects move toward the nearest corner matching their color.

## Final Answer

Move the green block to the top-left corner.

## Missed Alternatives

- shape-dependent transformation

## Dissent

- `skeptical_reviewer`: The final answer applies tokens not observed in the trace: green
- `method_reviewer`: The trace did not test plausible alternatives: shape-dependent transformation
