# AI Judge v2 Architecture

## System Overview

```mermaid
flowchart LR
    Q["User question"] --> S["9 independent seats"]
    S --> L["Claim ledger"]
    L --> G1["Gate 1: bluff EV"]
    G1 --> G2["Gate 2: should bid"]
    G2 --> G3["Gate 3: allocation score"]
    G3 --> D["Diversity radar"]
    D --> V["Graph value"]
    V --> P["Peach projection"]
    P --> H["Human verdict"]
```

## Model Access Layer

```mermaid
graph LR
    subgraph "Access Methods"
        CDP["Chrome CDP :9223"]
        AX["macOS Accessibility API"]
    end
    subgraph "Web Models"
        W1[Gemini] & W2[ChatGPT] & W3[DeepSeek]
        W4[Kimi] & W5[Grok] & W6[Yuanbao]
    end
    subgraph "Desktop Apps"
        D1[Gemini.app] & D2[Qwen.app] & D3[Doubao.app]
    end
    CDP --> W1 & W2 & W3 & W4 & W5 & W6
    AX --> D1 & D2 & D3
```

## v2 Scoring Engine

```mermaid
graph TD
    C["Claim"] --> B["evaluate_bluff_ev"]
    B --> BID["should_bid"]
    BID --> A["allocation_score"]
    A --> CAL["log_score + brier_score"]
    CAL --> VOI["calculate_voi"]
    VOI --> RISK["half_kelly_cap + cheat_ev"]
    RISK --> OUT["claim score + tier + explanation"]
```

The public engine lives in `core/formula_engine.py` and `core/scoring_v2.py`. It is intentionally small enough to audit.

## Consensus Layer

`core/consensus_v2.py` estimates diversity health, clusters similar seats, and computes `graph_value_v2`. `core/peach_projection.py` then allocates primary weight to the top seats while keeping a floor for minority signals.

## Data Flow

```
~/.ai-judge/runs/YYYY-MM-DD-NNN/
├── task-status.json       # Session metadata
├── answers.md             # 9 raw model answers
├── claim-ledger.json      # Claim decomposition + v2 score components
├── verdict.md             # Human-readable verdict
├── feature-ledger.json    # Seat performance trends
├── audit-trail.json       # Full traceability chain
└── hermes-output.json     # Hermes delivery envelope
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| CLI | Python 3.11+ (argparse) |
| Web Automation | Chrome DevTools Protocol |
| Desktop Automation | Swift + macOS Accessibility API |
| Data Format | JSON, Markdown |
| Packaging | pip, Docker |
| CI/CD | GitHub Actions |
