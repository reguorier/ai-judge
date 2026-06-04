# Three-Block Governance Packet

Status: public-safe packet format
Created: 2026-05-23 HKT

This packet is the handoff format for Article 11-style governance review. It is
not a sales deck and not a rewritten answer. It preserves the raw generated
answer, the isolated evidence layer, and the AI Judge audit output as separate
objects.

## Rule

Do not let a model-generated citation become evidence for itself.

A source can be real, accessible, and relevant while still failing to support
the exact generated claim. The packet therefore reports citation health and
claim support separately.

## Block 1: Raw Model Answer

The raw answer is copied unchanged from the AI system under review.

Required fields:

```json
{
  "block": "raw_model_answer",
  "answer_id": "answer-001",
  "question": "What did the cited source prove?",
  "answer_text": "The Stanford 2026 study proved that AI review caused a 22% reduction in churn [1].",
  "model_label": "model_under_audit",
  "captured_at": "2026-05-23T00:00:00Z"
}
```

Handling:

- Preserve unsupported, overclaimed, or fabricated text.
- Do not rewrite the answer inside the audit packet.
- Do not merge source text into the answer block.

## Block 2: Isolated Evidence

The evidence block contains only evidence admitted into the audit layer.

Required fields:

```json
{
  "block": "isolated_evidence",
  "evidence_id": "EVID-001",
  "source_label": "Primary source or page title",
  "source_url": "https://example.org/source",
  "provenance": "fetched",
  "evidence_text": "The source reports an association and explicitly disclaims causation.",
  "captured_at": "2026-05-23T00:00:00Z"
}
```

Allowed provenance labels:

| Provenance | Meaning |
|---|---|
| `model_candidate` | The model mentioned the source; not trusted yet |
| `user_supplied` | A human or external system pasted evidence |
| `fetched` | AI Judge or an evidence broker fetched the source |
| `independently_attested` | A trusted independent layer attested the source |
| `notarized` | Evidence is bound to an external witness or ledger |

Handling:

- A `user_supplied` source may support audit work, but it is not the same trust object as `fetched`, `independently_attested`, or `notarized`.
- A missing or inaccessible source should stay `unverifiable`, not be converted into `false`.
- A real but irrelevant source should not upgrade claim support.

## Block 3: AI Judge Audit Output

The audit block records what AI Judge concluded from Block 1 and Block 2.

Required fields:

```json
{
  "block": "ai_judge_audit_output",
  "audit_id": "citation-audit-001",
  "citation_status": "verified",
  "source_relevance": "relevant",
  "claim_support_status": "contradicted",
  "support_failure_code": "overclaimed_causation",
  "reason": "The source reports association, while the model answer claims causation.",
  "replay_ledger_hash": "sha256:...",
  "generated_at": "2026-05-23T00:00:00Z"
}
```

Two-layer label:

| Layer | Question | Example |
|---|---|---|
| Citation health | Does the cited source exist and match the citation? | `verified` |
| Claim support | Does the source support the exact generated claim span? | `contradicted` |

## Public-Safe Demo Cases

### Fabricated Citation

Input:

```text
examples/fake-citation.md
```

Reports:

```text
reports/fake-citation-audit.html
reports/fake-citation-audit.json
```

Use:

- Demonstrates why `unverifiable` is not automatically `false`.
- Shows the source-isolation boundary before writing into a ledger.

### Real Source, Overclaimed Causation

Input:

```text
examples/real-source-overclaimed-causation.md
```

Reports:

```text
reports/real-source-overclaimed-causation-audit.html
reports/real-source-overclaimed-causation-audit.json
```

Use:

- Demonstrates Article 11's hard edge case.
- Keeps `citation_status=verified` separate from `claim_support_status=contradicted`.

Regenerate:

```bash
python3 cli/main.py audit examples/real-source-overclaimed-causation.md \
  --html reports/real-source-overclaimed-causation-audit.html \
  --json reports/real-source-overclaimed-causation-audit.json \
  --md reports/real-source-overclaimed-causation-audit.md \
  --run-id governance-real-source-overclaimed-causation
```

## Send Protocol

When a reviewer asks for the packet, send only:

1. Block 1 raw answer.
2. Block 2 isolated evidence.
3. Block 3 audit output.

Do not add private correspondence, hidden chain-of-thought, or a marketing
claim. If a private reply contributes a benchmark idea, anonymize it first and
ask permission before publishing any identifying detail.
