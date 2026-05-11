# AI Judge Architecture

## System Overview

```mermaid
graph TD
    U["👤 Your Question"] --> J["⚖️ Stage 1: jury<br/>Create session, 9 seats"]
    J --> C["🔍 Stage 2: collect<br/>Parallel model query"]
    C --> V["📊 Stage 3: verdict<br/>Cross-validate + score"]
    V --> R["📝 Stage 4: reflect<br/>Daily insights"]
    R --> H["👤 You Decide"]

    style U fill:#cba6f7,color:#000
    style H fill:#a6e3a1,color:#000
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

## Cross-Validation Engine

```mermaid
graph TD
    A["9 Raw Answers"] --> CD["Claim Decomposition"]
    CD --> SA["Source Authority"]
    CD --> SE["Evidence Strength"]
    CD --> SF["Freshness"]
    CD --> SR["Reproducibility"]
    CD --> SH["Historical Reliability"]
    SA & SE & SF & SR & SH --> IS["Ising Consensus Detection"]
    IS --> MD["Memory Decay Tracking"]
    MD --> OUT["verdict.md + audit-trail.json"]
```

## Data Flow

```
~/.ai-judge/runs/YYYY-MM-DD-NNN/
├── task-status.json       # Session metadata
├── answers.md             # 9 raw model answers
├── claim-ledger.json      # Claim decomposition + 5-dim scores
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
