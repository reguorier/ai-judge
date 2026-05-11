# AI Judge vs llm-council — Full Comparison

## Summary

| | AI Judge | llm-council (Karpathy) |
|---|---|---|
| **Philosophy** | Human holds final gavel | Chairman LLM decides |
| **Creator** | AI Judge Contributors | Andrej Karpathy |
| **License** | BSL 1.1 → MIT (4 years) | MIT |
| **Stars** | — | ~17,800 |
| **Models** | 9 (desktop + web via CDP/AX) | 4 (OpenRouter API) |
| **Pipeline** | 4 discrete stages (human-in-the-loop) | 3-stage automatic DAG |
| **Privacy** | Local-first (browser sessions) | Via OpenRouter API |
| **Scoring** | 5-dimension claim-level | Anonymous ranking |
| **Audit Trail** | Full traceability chain | Conversation JSON only |
| **Production** | Docker + CI/CD + key mgmt | Not supported |
| **Frontend** | CLI (Web dashboard in roadmap) | React + Vite |
| **Platform** | macOS | Cross-platform |

## Core Differences

### 1. Who Decides?

| llm-council | AI Judge |
|---|---|
| Chairman LLM synthesizes final answer | Human reads verdict and decides |
| Known issue: Chairman over-influence (GitHub Issue #3) | Every stage inspectable; raw answers reviewable before verdict |

### 2. Model Access

| llm-council | AI Judge |
|---|---|
| OpenRouter API (unified facade) | Chrome CDP + Swift desktop bridges |
| API keys required | Existing browser sessions |
| Data through 3rd-party gateway | Data stays local |

### 3. Evaluation

| llm-council | AI Judge |
|---|---|
| Anonymous peer ranking (O(N²)) | 5-dimension claim scoring |
| Chairman synthesis | Ising consensus + memory decay |
| No audit trail | Full traceability |

## When to Use Which

| Scenario | Use |
|----------|-----|
| Quick multi-perspective | llm-council |
| Regulated industry decision | **AI Judge** |
| Academic research | llm-council |
| Enterprise strategy | **AI Judge** |
| Personal curiosity | llm-council |
| Daily professional use | **AI Judge** |
