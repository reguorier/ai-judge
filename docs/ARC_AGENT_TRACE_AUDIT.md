# ARC / Agent Trace Audit

AI Judge should not be presented as an ARC-AGI solver. The stronger and more credible position is evaluator tooling: a way to inspect whether an agent attempt has enough evidence, exploration, dissent, and replayability before the final answer is trusted.

## Positioning

ARC-style tasks expose a gap in ordinary evaluation. Final-answer accuracy is necessary, but it does not show why an agent succeeded or failed. A trace can look coherent while hiding an untested assumption, skipping a counterexample, or applying a rule that was never observed in training examples.

AI Judge can sit beside solver attempts as a trace verdict layer:

| Layer | Question |
|---|---|
| Exploration coverage | Did the agent inspect enough examples and alternatives? |
| Rule support | Does the proposed rule follow from observed evidence? |
| Missed alternatives | Which plausible hypotheses were not tested? |
| Dissent | Would another model-seat object to the rule or final action? |
| Replay ledger | Can a human replay the trace, evidence, verdict, and final decision? |

## Minimal Verdict Format

```json
{
  "task_id": "arc-style-demo-001",
  "trace_status": "weakly_supported",
  "exploration_coverage": "partial",
  "rule_support": "unverifiable",
  "missed_alternatives": [
    "shape-dependent transformation",
    "object-order transformation",
    "size-dependent transformation"
  ],
  "dissent": [
    {
      "seat": "skeptical_reviewer",
      "claim": "The trace applies the color rule to a green object without evidence that green was observed."
    }
  ],
  "human_gate": "reject_until_rechecked"
}
```

## Example

See [`examples/agent-trace-verdict.md`](../examples/agent-trace-verdict.md) for a small ARC-style trace review. The example is deliberately simple: it shows the product wedge, not a formal benchmark claim.

Executable demo fixture:

- Input: [`examples/agent-trace-demo.json`](../examples/agent-trace-demo.json)
- Renderer: [`tools/render_agent_trace_report.py`](../tools/render_agent_trace_report.py)

```bash
python tools/render_agent_trace_report.py examples/agent-trace-demo.json \
  --json reports/agent-trace-demo.json \
  --md reports/agent-trace-demo.md \
  --html reports/agent-trace-demo.html \
  --audit-id agent-trace-demo-001
```

## Community Ask

The first ARC / Agent eval community ask should be narrow:

```text
I am building AI Judge as an evaluator for agent traces, not as a solver. The goal is to expose failure modes in exploration coverage, rule support, missed alternatives, dissent, and replayability. Would trace-level verdicts like this help teams compare agent attempts, or would they only be useful if tied to a formal benchmark score?
```

## Guardrails

- Do not claim AI Judge solves ARC-AGI-3.
- Do not claim any official ARC relationship.
- Do not present a single toy trace as benchmark evidence.
- Do use the trace verdict as a conversation starter with ARC, agent eval, and LLM-as-judge communities.

## Next Build Step

The first implementation step is now a small `agent-trace.json` fixture plus a report renderer that mirrors citation audit structure:

1. raw trace
2. extracted claims / rules
3. observed evidence
4. missed alternatives
5. dissent notes
6. human gate
7. replay hash

That keeps the citation-audit wedge and the agent-eval wedge consistent: both are about source isolation, claim support, dissent, and human signoff before publication.

The next useful step is to convert several real solver attempts into anonymized trace fixtures and compare trace verdicts against final-answer correctness.
