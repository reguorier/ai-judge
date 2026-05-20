# AI Judge Agent Trace Audit

Audit ID: `agent-trace-demo-001`
Task ID: `arc-style-demo-001`
Trace status: `weakly_supported`
Human gate: `reject_until_rechecked`
Replay ledger hash: `sha256:c422611c1bd9392b417de24fa502f17ff8a7d51e39d9c1684259b78237c16109`

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

- No missed alternatives detected.

## Dissent

- `skeptical_reviewer`: The final answer applies tokens not observed in the trace: green
