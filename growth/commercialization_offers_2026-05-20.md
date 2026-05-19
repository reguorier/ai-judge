# Commercialization Offers - AI Judge

## Commercial Thesis

The first buyers will not pay for "a council of AIs". They will pay to reduce the risk of publishing or acting on unsupported AI output.

## Buyer Personas

| Persona | Pain | Trigger | Budget Owner |
|---|---|---|---|
| AI agent startup founder | Agent demo works but output quality is hard to prove | Customer pilot / investor demo | Founder / CTO |
| RAG product team | Citations exist but do not prove claims | Enterprise customer asks for evidence | Product / Engineering |
| AI consulting shop | Client deliverables need QA | Before sending reports | Founder / delivery lead |
| Legal / compliance tech builder | Unsupported claims create liability | Audit / review workflow | Product / compliance |
| VC / accelerator analyst | Needs quick technical diligence on AI startups | Batch review / demo day | Partner / analyst |

## Three Minimum Sellable Offers

| Offer | Buyer | Deliverable | Price Hypothesis |
|---|---|---|---|
| Citation Support Audit Sprint | RAG teams, AI consultants | 20-50 outputs audited, evidence gap report, fix checklist | $2,000-$5,000 one-time |
| Agent Output Gate | Agent startups | Agent trace audit template + verdict report + integration advice | $3,000-$8,000 one-time |
| Hosted Team Review | AI teams | Private dashboard, history, team signoff, exportable reports | $299-$1,500/month |

## Open Source / Paid Boundary

| Free / Open | Paid |
|---|---|
| Local citation audit CLI | Hosted team workspace |
| Basic examples and benchmark cases | Private batch audit |
| Single-user desktop app | Team signoff and history |
| Public HF demo | SLA, integrations, custom datasets |
| JSON/HTML reports | Compliance exports and managed review |

## First 30 Customer Profiles

| Segment | Count | Where To Find |
|---|---:|---|
| AI agent startups | 8 | YC directory, Product Hunt, X |
| RAG SaaS products | 6 | GitHub, LangChain/LlamaIndex communities |
| AI consulting shops | 5 | LinkedIn, indie AI agencies |
| Legal/compliance AI tools | 4 | LegalTech lists, GitHub, LinkedIn |
| Open-source eval maintainers | 4 | GitHub / Hugging Face |
| Accelerator / VC analysts | 3 | MiraclePlus/YC/Techstars networks |

## Sales One-Liner

AI Judge catches unsupported AI claims before they become customer-facing output.

## Discovery Questions

1. Do you publish AI-generated reports or answers to customers?
2. Do you need to prove that cited sources actually support generated claims?
3. Do you already have a human review step?
4. What happens when an AI output is wrong but confidently cited?
5. Would a JSON + HTML audit report fit your workflow?

## Pilot Offer Email

Subject: Audit 20 AI-generated outputs for unsupported claims?

Hi [Name], I am building AI Judge, an open-source judge layer for AI outputs. The wedge is citation support: a source can be real and still fail to prove the generated claim.

I am offering a small audit sprint for teams shipping RAG answers, agent outputs, or AI-generated reports: send 20 public-safe outputs, and I will return a claim/source verdict report showing verified, weak, irrelevant, unverifiable, and contradicted claims.

Would this be useful for your current workflow?

## Pricing Validation Path

| Step | Validation |
|---|---|
| Free 3-case audit | See if users send real outputs |
| $500 paid mini-audit | Test willingness to pay |
| $2k sprint | Test consulting wedge |
| Hosted beta | Convert repeat usage |
| Team plan | Validate SaaS boundary |
