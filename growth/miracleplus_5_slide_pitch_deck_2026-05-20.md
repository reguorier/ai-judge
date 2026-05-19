# MiraclePlus 5-Slide Pitch Deck - AI Judge

Purpose: short application/interview deck for MiraclePlus 2026 Fall Batch.  
Format: 5 slides, no decorative fluff, each slide has one claim and one proof object.  
Repo: `https://github.com/reguorier/ai-judge`

## Slide 1 - The Agent Economy Needs A Judge Layer

**Claim title:** AI Agent adoption is creating a new quality gate: can this output be trusted before it reaches a user?

**Proof object:** Three-step workflow diagram.

```text
AI agent / RAG / report generator
        -> evidence and dissent audit
        -> human-signoff verdict
```

**Speaker note:** AI teams already know how to generate. The new bottleneck is deciding whether the generated output is safe to publish, deliver, or act on.

## Slide 2 - The Pain Is Not Fake Citations; It Is Unsupported Claims

**Claim title:** A source can be real, relevant, and still fail to prove the AI's claim.

**Proof object:** Claim-source verdict table.

| AI output failure | What normal tools see | What AI Judge checks |
|---|---|---|
| Fake source | Citation missing | `unverifiable` |
| Real but irrelevant source | Citation exists | `irrelevant` |
| Real source, overstated claim | Citation exists | `weakly_verified` / `contradicted` |
| Agent action without trace | Task completed | evidence gap + human review |

**Speaker note:** This is the wedge. We are not competing to be another model wrapper; we judge whether a model's claim actually survives evidence.

## Slide 3 - Product: Multi-Model Jury + Evidence Ledger + Human Gavel

**Claim title:** AI Judge turns model output into an auditable decision package.

**Proof object:** Product stack.

```text
Input answer
  -> claim extraction
  -> citation/evidence audit
  -> multi-seat dissent
  -> verdict report
  -> human signoff
```

**Current assets:**

- Public repo: `https://github.com/reguorier/ai-judge`
- HF demo: `https://huggingface.co/spaces/reguorier/ai-judge-citation-audit`
- Benchmark cases: `citation-bench/`
- Desktop/web run: `ddb4902f3369`, staged 8/10 required non-Grok seats
- Tests: `37 passed` for product/report state tests

**Speaker note:** The current version is already working as a citation-audit and report-generation system. The web-seat layer still needs reliability hardening, which is why we frame it as staged council output when seats are incomplete.

## Slide 4 - First Commercial Wedge

**Claim title:** Teams will pay first for pre-publication audit, not for "AI council" as a novelty.

**Proof object:** Offer ladder.

| Offer | Buyer | Deliverable | Price hypothesis |
|---|---|---|---|
| Citation Support Audit Sprint | RAG teams / AI consultants | 20-50 outputs audited + verdict report | USD 2k-5k |
| Agent Output Gate | Agent startups | Trace audit + go/no-go report | USD 3k-8k |
| Hosted Team Review | AI product teams | Private dashboard + review history + export | USD 299-1.5k/mo |

**Speaker note:** The wedge is service-like first because it forces us to learn real customer failure cases. The platform becomes stronger as those cases become benchmark fixtures.

## Slide 5 - Why MiraclePlus, Why Now

**Claim title:** AI Judge fits the 2026 AI infra window: every serious AI workflow will need a quality gate.

**Proof object:** 90-day execution roadmap.

| Phase | Goal | Output |
|---|---|---|
| Days 1-30 | Public credibility | GitHub stars, HF demo usage, HN/Reddit/ARC feedback |
| Days 31-60 | Design partners | 10 real audit cases from RAG/agent teams |
| Days 61-90 | Paid pilots | 3 audit sprints or agent-output gate pilots |

**Ask:** MiraclePlus helps compress product positioning, design partner access, China AI infra network, and investor narrative.

**Speaker note:** The core thesis is simple: as AI agents become workers, someone has to judge their work.

## Design Direction

- Use a restrained technical deck, not a decorative startup pitch.
- Color system: deep ink `#0B1020`, electric blue `#2563EB`, audit green `#16A34A`, warning amber `#F59E0B`, paper white `#F8FAFC`.
- Prefer diagrams, verdict tables, and proof rails over stock imagery.
- Do not use fake logos or invented customer metrics.
