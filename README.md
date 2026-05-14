<p align="center">
  <img src="https://img.shields.io/badge/release-3.2.0-purple" alt="v3.2.0">
  <img src="https://img.shields.io/badge/evidence-traced-2ea44f" alt="evidence traced">
  <img src="https://img.shields.io/badge/dissent-before%20confidence-orange" alt="dissent before confidence">
  <img src="https://img.shields.io/badge/reasoning-tree%20ready-38bdf8" alt="reasoning tree ready">
  <img src="https://img.shields.io/badge/local--first-macOS%20%2B%20Docker-black" alt="local-first">
  <img src="https://img.shields.io/badge/license-BSL%201.1-blue" alt="BSL 1.1">
</p>

<p align="center">
  <img src="assets/ai-judge-v3-hero.png" alt="AI Judge v3.2 product overview" width="960">
</p>

<h1 align="center">AI Judge v3.2</h1>
<p align="center"><strong>9 AI seats deliberate. Evidence is traced. Dissent challenges weak claims. A reasoning tree shows why. You hold the gavel.</strong></p>
<p align="center">A local-first Codex skill and CLI for multi-model evaluation, claim scoring, auditable reasoning, judgment-quality profiling, and human-final verdicts.</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#demo-result">Demo Result</a> ·
  <a href="docs/LAUNCH_DEMO_KIT.md">Launch Demo Kit</a> ·
  <a href="#what-v32-adds">What v3.2 Adds</a> ·
  <a href="#how-it-differs">Comparison</a> ·
  <a href="RELEASE_V3_2.md">Release Notes</a>
</p>

---

## Why People Notice It

Most AI comparison tools answer: **which model sounded best?**
AI Judge v3.2 asks a harder question: **which answer can show its evidence, survive dissent, and explain the path to judgment?**

It separates polished language from actual thinking quality, then gives the human a compact evidence package instead of another black-box synthesis.

## 30-Second Product Tour

<p align="center">
  <img src="assets/ai-judge-v3.2-tianfu-stack.svg" alt="AI Judge v3.2 evidence and reasoning stack" width="900">
</p>

| Step | What happens | Why it matters |
|---:|---|---|
| 1 | 9 AI seats answer independently | Avoids one-model monologue bias |
| 2 | Claims enter the v2 scoring lane | Bluff, calibration, evidence, diversity, and graph value are auditable |
| 3 | Evidence objects attach sources | Tool, rule, harness, and precedent evidence become inspectable |
| 4 | Dissent challenges weak support | The system argues against itself before raising confidence |
| 5 | Reasoning tree renders the path | Facts, evidence, rules, dissent, and conclusion become visible |
| 6 | Human reads the evidence and decides | AI supports judgment, but does not replace it |

```mermaid
flowchart LR
    Q["Question"] --> J["9 AI Seats"]
    J --> C["Claim Ledger"]
    C --> S["10 Scoring Functions"]
    C --> E["Evidence Objects"]
    E --> R["Risk Router"]
    R --> X["Dissent Agent"]
    X --> T["Reasoning Tree"]
    C --> N["4 Cognitive Proxy Signals"]
    N --> H["Hard Truth Mode L0-L4"]
    S --> D["Diversity + Graph Value"]
    D --> P["Peach Projection"]
    T --> V["Human Verdict"]
    H --> V
    P --> V
```

## What v3.2 Adds

<p align="center">
  <img src="assets/ai-judge-v3.2-reasoning-tree.svg" alt="AI Judge v3.2 reasoning tree visualization" width="900">
</p>

| Layer | What it does | User-visible output |
|---|---|---|
| Evidence objects | Gives each claim a source-backed evidence bundle | `tool_result`, `rule_match`, `harness_result`, `precedent` |
| Dissent agent | Challenges weak evidence, single-source support, and overconfidence | Counterarguments and required checks |
| Reasoning tree | Turns the verdict path into expandable JSON/UI nodes | Facts -> Evidence -> Rules -> Dissent -> Conclusion |
| Risk router | Chooses review depth by sensitive surface and diff shape | `full_jury`, `standard_dissent`, `standard`, `fast_check` |
| Enhanced confidence | Adds evidence strength and dissent penalty to confidence lights | More honest low/medium/high confidence |

The full product package also adds a TypeScript reasoning-tree UI under `frontend/` and a Rust reference engine under `rust-engine/`.

## Launch Assets

AI Judge now includes a ready-to-record launch and hackathon demo pack:

| Asset | Use it for |
|---|---|
| [`product/demo-video.html`](product/demo-video.html) | Auto-playing 90-second launch demo source for screen recording |
| [`Record-AI-Judge-Demo.command`](Record-AI-Judge-Demo.command) | One-click macOS recorder for the 90-second launch demo |
| [`Record-Microsoft-Agent-Academy.command`](Record-Microsoft-Agent-Academy.command) | One-click macOS recorder for the five-minute Microsoft submission video |
| [`docs/RECORDING_GUIDE.md`](docs/RECORDING_GUIDE.md) | Exact recording workflow and screen order |
| [`docs/LAUNCH_DEMO_KIT.md`](docs/LAUNCH_DEMO_KIT.md) | Voiceover, shot list, Product Hunt copy, Show HN copy, Chinese short post |
| [`docs/MICROSOFT_AGENT_ACADEMY.md`](docs/MICROSOFT_AGENT_ACADEMY.md) | Microsoft Agent Academy submission positioning and answers |
| [`assets/microsoft-agent-academy-architecture.svg`](assets/microsoft-agent-academy-architecture.svg) | Architecture diagram for hackathon submissions |
| [`examples/microsoft_agent_academy/copilot_cowork_packet.md`](examples/microsoft_agent_academy/copilot_cowork_packet.md) | Copilot/Cowork demo prompt, sample output, and AI Judge evaluation packet |

## v3.1 Foundation

| Layer | What it does | User-visible output |
|---|---|---|
| Dual scores | Separates fluent confidence from judgment quality | `smart_sounding_score` and `judgment_quality_score` |
| Self-closure | Detects when the answer stays trapped in one viewpoint | 自我视角闭环 |
| Ambiguity flexibility | Checks whether contradiction is explored or prematurely closed | 模糊性处理能力 |
| Recovery after negative feedback | Distinguishes repair from defensiveness | 反馈恢复模式 |
| Experience grounding | Rewards concrete tests, cases, and lived evidence | 经验锚定度 |
| Hard Truth Mode | Escalates when style outruns judgment | L0-L4 feedback levels |
| Heterogeneity exemption | Protects unusual but genuinely novel reasoning | Neurodiversity-friendly safeguard |

These are **textual proxy signals**, not medical or diagnostic claims. They help the user inspect reasoning behavior in the output.

## Core Signals at a Glance

| Signal | Good pattern | Risk pattern | Example output |
|---|---|---|---|
| Self-closure | Brings in outside viewpoints | Keeps returning to one self-centered frame | `self_reference_closure` |
| Ambiguity flexibility | Suspends, tests, and integrates contradictions | Chooses a side too quickly | `low_flexibility_choose_side` |
| Recovery after negative feedback | Uses challenge as new evidence | Defends, collapses, or performs agreement | `defensive_recovery` |
| Experience grounding | Names concrete data, cases, tests, and constraints | Floats in jargon and abstraction | `conceptual_fluency_without_grounding` |

## Demo Result

Reproducible local smoke tests:

```bash
PYTHONPATH=. python3 tests/smoke_test_v3_2.py
PYTHONPATH=. python3 tests/smoke_test_v3.py
```

Observed v3.2 demo behavior:

| Fixture | Risk route | Evidence | Dissent | Result |
|---|---|---:|---|---|
| Security/payment checkout change | `full_jury` | 3 items | triggered | Reasoning tree exportable |

Observed v3.1 demo behavior:

| Fixture | Smart-sounding | Judgment quality | Result |
|---|---:|---:|---|
| Shallow strategic jargon | 0.937 | 0.695 | L2 判断优先, hard truth active |
| Evidence-grounded reasoning | 0.879 | 0.913 | L0 普通反馈 |
| Full pipeline | steady confidence | exportable verdict | hard truth triggers when needed |

Example Hard Truth output:

```text
═══ 判断优先模式 ═══

smart_sounding: 0.94 | judgment_quality: 0.70
差距: 24% — 这段输出「听起来聪明」，但不应被直接采信。

最小修复动作：
  a. 你的哪个主张可以被证伪？
  b. 哪个反方观点可能是真的？
  c. 你下一步用什么数据或实验来验证？
```

## Quick Start

```bash
# Run full harness test suite (benchmark + regression + smoke)
PYTHONPATH=. python3 tests/run_harness.py

# V3.1 neuro-cognitive demo
python3 cli/main.py neuro-profile --demo

# Hard Truth Mode
python3 cli/main.py hard-truth --demo

# Full V3.1 pipeline
python3 cli/main.py v3-pipeline --demo

# V3.2 evidence + dissent + reasoning tree pipeline
python3 cli/main.py v3.2-pipeline --demo
PYTHONPATH=. python3 tests/smoke_test_v3_2.py

# V2 scoring remains available
python3 cli/main.py score-v2 --demo
```

## Harness Engineering

The `harness/` layer provides systematic, reproducible pipeline execution:

| Module | Purpose |
|--------|---------|
| `harness/runner.py` | Programmatic API for all pipeline operations |
| `harness/benchmark.py` | Golden-dataset testing with pass/fail thresholds |
| `harness/regression.py` | Cross-version consistency detection |
| `harness/config.py` | YAML-based profiles (default, strict, fast, ci) |
| `harness/reporter.py` | JSON, Markdown, and HTML output |

```python
from harness import AIJudgeHarness
h = AIJudgeHarness(config="ci")
result = h.run_full_v3("Your analysis text here")
print(result.passed, result.data)
```

CI runs `tests/run_harness.py` on every push and PR. Docker build is gated on harness passing.

```bash
ai-judge jury --question "Your question here"
ai-judge collect --run latest
ai-judge verdict --run latest
```

## v2 to v3.2

| Area | v2 | v3.1 | v3.2 |
|---|---|---|---|
| Claim quality | 10 scoring functions, bluff gates, diversity radar | Same, plus judgment-quality profiling | Same, plus evidence object tracing |
| Model value | `graph_value_v2` and Two Peaches allocation | Same, now informed by cognitive risk flags | Same, now routed by risk depth and dissent |
| Human role | Final verdict owner | Final verdict owner, with clearer blind-spot feedback | Final verdict owner, with visible reasoning path |
| Failure mode caught | Unsupported confidence and echo-chamber consensus | Unsupported confidence, echo chambers, performative intelligence | Unsupported evidence, missing dissent, hidden risk surfaces |
| Main new command | `score-v2 --demo` | `neuro-profile`, `hard-truth`, `v3-pipeline` | `v3.2-pipeline --demo` |

## How It Differs

| System | Primary job | Final owner | What AI Judge v3.2 adds |
|---|---|---|---|
| Hermes-compatible skill | Package an agent workflow | User/host agent | Full jury workflow, scoring engine, judgment profiling, and auditable reasoning |
| llm-council | Peer review and chairman synthesis | Chairman LLM | Human-final decision, claim ledger, dissent, and local-first CLI/Docker package |
| Perplexity Model Council | Web model comparison and synthesis | Perplexity synthesizer | Inspectable formulas, reasoning-tree artifacts, and local workflow |
| AI Judge v3.2 | Evidence workflow for consequential decisions | Human | Scoring, diversity, graph value, hard truth, evidence tracing, dissent, and risk routing |

## Repository Map

```text
ai-judge/
├── README.md
├── RELEASE_V3.md
├── SKILL.md
├── Publish-AI-Judge-V3.command
├── core/
│   ├── neuro_profiler.py      # 4 proxy signals + dual scores
│   ├── hard_truth.py          # L0-L4 judgment-first feedback
│   ├── determinism.py         # consistency + confidence lights + v3 pipeline
│   ├── scoring_v2.py          # v2 scoring plus v3/v3.2 bridge
│   ├── evidence.py            # v3.2 structured evidence objects
│   ├── dissent.py             # v3.2 Devil's Advocate challenge
│   ├── reasoning_trace.py     # v3.2 reasoning tree builder
│   ├── risk_router.py         # v3.2 risk-based review depth
│   ├── formula_engine.py      # 10 auditable scoring formulas
│   ├── anchor_engine.py       # goal anchoring and taste cards
│   ├── mirror.py              # thinking fingerprint and growth narrative
│   └── ...
├── cli/main.py                # unified CLI
├── frontend/                  # TypeScript reasoning-tree UI components
├── rust-engine/               # Rust reference implementation
├── tests/smoke_test_v3.py
├── product/landing.html
├── Dockerfile
└── docker-compose.yml
```

## Open-Core Boundary

| Public in this repo | Paid/private runtime |
|---|---|
| CLI surface and v2/v3/v3.2 demos | Production browser/CDP collector |
| Scoring formulas, cognitive proxy functions, evidence/dissent demo | Managed multi-model runtime |
| Codex/Hermes-compatible `SKILL.md` | SaaS license server |
| Docker, schemas, docs, examples | Team deployment and support layer |
| Swift bridge source | Hosted integrations |

## Documentation

| Document | Purpose |
|---|---|
| [RELEASE_V3_2.md](RELEASE_V3_2.md) | v3.2 release notes and Tianfu migration notes |
| [RELEASE_V3.md](RELEASE_V3.md) | v3.1 release notes and migration notes |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Setup and first demos |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/COMPARISON.md](docs/COMPARISON.md) | Comparison with other council-style tools |
| [docs/v3.2-source/](docs/v3.2-source/) | Full-package source discussion, technical spec, and roadmap |
| [product/landing.html](product/landing.html) | Product landing page |

## License

BSL 1.1. Source available. Production use requires a license.
