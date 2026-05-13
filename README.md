<p align="center">
  <img src="https://img.shields.io/badge/release-3.1.0-purple" alt="v3.1.0">
  <img src="https://img.shields.io/badge/scoring%20engine-v3.0-green" alt="v3.0 scoring engine">
  <img src="https://img.shields.io/badge/functions-14-2ea44f" alt="14 auditable functions">
  <img src="https://img.shields.io/badge/neuro%20signals-4-orange" alt="4 neuro signals">
  <img src="https://img.shields.io/badge/license-BSL%201.1-orange" alt="BSL 1.1">
</p>

<h1 align="center">AI Judge v3.1</h1>
<p align="center"><strong>9 AI models deliberate. 14 functions audit the claims. 4 neuro-cognitive signals expose "sounds smart" vs "is smart". You hold the gavel.</strong></p>
<p align="center">A local-first Codex skill for multi-model evaluation, claim scoring, neuro-cognitive profiling, and human-final verdicts.</p>

---

## v3.1: The Neuro-Cognitive Upgrade

v2 caught "surface performance" — edit friction, jargon inflation, A/B track gaps. **v3.1 goes deeper: distinguishing "sounds smart" from "is smart."**

### Dual Scores

Every evaluation now outputs TWO scores:

| Score | What it measures |
|-------|-----------------|
| `smart_sounding_score` | How confident, fluent, and structured it sounds |
| `judgment_quality_score` | How reliable the actual thinking appears to be |

### 4 Neuro-Cognitive Proxy Signals

| Signal | User-Facing Name | What It Detects |
|--------|-----------------|-----------------|
| Self-Closure | 自我视角闭环 | Whether "I" dominates where perspective-switching is needed |
| Ambiguity Flexibility | 模糊性处理能力 | Side-choosing vs synthesis vs suspended exploration when facing contradiction |
| Recovery After Negative | 反馈恢复模式 | Defensive collapse vs exploratory repair after being challenged |
| Experience Grounding | 经验锚定度 | Concept-driven abstraction vs experience-anchored concrete thinking |

### Hard Truth Mode (L0-L4)

When `smart_sounding >> judgment_quality`, the system automatically escalates:

| Level | Mode | Trigger |
|:-----:|------|---------|
| L0 | Normal | Healthy discussion |
| L1 | Calibration | Mild cognitive gap detected |
| L2 | Judgment-First | Sounds smart but judgment quality is low |
| L3 | Forced Evidence | Repeated defense, no quality improvement |
| L4 | Safety Downgrade | High-risk topics |

**L2 sample output:**
```
═══ 判断优先模式 ═══

smart_sounding: 0.94  |  judgment_quality: 0.70
差距: 24% — 这段输出"听起来聪明"，但不应被直接采信。

认知盲区：
  1. 自我视角闭环：在应引入外部视角处仍以"我"主导。
  2. 模糊性回避：面对矛盾时直接选边，未进行悬置探索。
  3. 概念漂浮：大量抽象词汇缺乏经验锚定。

最小修复动作：
  a. 你的哪个主张可以被证伪？
  b. 哪个反方观点可能是真的？
  c. 你下一步用什么数据验证？
```

### Built-in Protections

- **Heterogeneity Exemption**: When highly deviant cognitive patterns produce genuinely novel ideas, standard penalties are suspended — protecting neurodiversity.
- **Performative Acceptance Detection**: Rewards actual quality improvement, not just saying "you're right, I'll change."
- **Cognitive Sovereignty**: Users can disable deep profiling at any time.

---

## Quick Start

```bash
# V3 Neuro-Cognitive Demo
ai-judge neuro-profile --demo

# Hard Truth Mode Demo
ai-judge hard-truth --demo

# Full V3 Pipeline Demo
ai-judge v3-pipeline --demo

# V3 Smoke Test
PYTHONPATH=. python3 tests/smoke_test_v3.py

# V2 Scoring Demo (still available)
ai-judge score-v2 --demo

# Production commands (require paid core)
ai-judge jury --question "Your question here"
ai-judge collect --run latest
ai-judge verdict --run latest
```

---

## Architecture

```
ai-judge-skill/
├── core/
│   ├── neuro_profiler.py      # V3: 4 neuro-cognitive signal extractors + dual scores
│   ├── hard_truth.py           # V3: L0-L4 judgment-first mode + heterogeneity exemption
│   ├── determinism.py          # V3: L1/L2 consistency + confidence lights + hard truth trigger
│   ├── scoring_v2.py           # V3: 3-gate scoring + dual score pipeline
│   ├── formula_engine.py       # 14 auditable scoring functions
│   ├── anchor_engine.py        # Goal anchoring with taste cards
│   ├── mirror.py               # Thinking fingerprint + growth narrative
│   ├── performance_detect.py   # Process-friction performance detection
│   ├── thinking_log.py         # Fragment collection + 6-role parliament
│   ├── achievement.py          # Metrics + breakthrough detection
│   ├── cold_start.py           # Progressive scaffolding
│   ├── consensus_v2.py         # Diversity radar + clustering
│   ├── peach_projection.py     # Scarcity-based weight allocation
│   ├── hermes_output.py        # Output formatting
│   └── license_validator.py    # License validation
├── cli/main.py                 # Unified CLI (v2 + v3 commands)
├── tests/
│   ├── smoke_test_v2.py        # V2 pipeline smoke test
│   └── smoke_test_v3.py        # V3 full pipeline smoke test
└── README.md
```

---

## Version History

| Version | Date | Key Changes |
|---------|------|------------|
| 1.0 | 2025-11 | Multi-model jury framework |
| 2.0 | 2026-03 | COUNCIL-003: Phase 1 scoring (log_score, allocation_score, bluff detection) |
| 2.1 | 2026-04 | Phase 2 diversity monitoring + Two Peaches weight allocation |
| 3.0 | 2026-05 | V2 Upgrade: determinism engine, goal anchoring, thinking fingerprint, 6-role parliament |
| 3.1 | 2026-05 | **V3 Upgrade: neuro-cognitive signals, dual scores, hard truth mode, heterogeneity exemption** |

---

## License

BSL 1.1 — Source available. Production use requires a license.
