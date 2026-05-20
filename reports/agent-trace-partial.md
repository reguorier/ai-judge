# AI Judge Agent Trace Audit

Audit ID: `agent-trace-partial-001`
Task ID: `arc-style-partial-001`
Trace status: `partially_supported`
Human gate: `needs_human_review`
Replay ledger hash: `sha256:ee98e348096dcc1c3eefe0d6c2fec3c5d2d42a1421d18a562f8fe585976ce284`

## Task

Review whether a trace has enough evidence to trust a blue-object transformation.

## Trace Verdict

| Dimension | Verdict |
|---|---|
| Exploration coverage | `partial` |
| Rule support | `supported` |
| Unsupported final tokens | `none` |

## Observed Evidence

- Training example A maps a blue block to the bottom-right corner.
- Training example B maps another blue block to the bottom-right corner.
- Training example C shows the shape stays constant during the move.

## Actions

- Apply the blue-block rule to the test grid, but do not check whether size or object order changes the rule.

## Hypothesis

Blue blocks move to the bottom-right corner.

## Final Answer

Move the blue block to the bottom-right corner.

## Missed Alternatives

- size-dependent transformation
- object-order transformation

## Dissent

- `method_reviewer`: The trace did not test plausible alternatives: size-dependent transformation, object-order transformation
