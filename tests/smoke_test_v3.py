#!/usr/bin/env python3
"""AI Judge V3 Full Pipeline Smoke Test.

Tests:
  1. Neuro-cognitive profiling (4 signals)
  2. Dual scores (smart_sounding vs judgment_quality)
  3. Hard truth mode (L0-L4)
  4. Full V3 pipeline integration
"""

import sys
sys.path.insert(0, "..")

from core.neuro_profiler import (
    compute_neuro_profile, detect_self_closure,
    detect_ambiguity_flexibility, detect_experience_grounding,
)
from core.hard_truth import (
    determine_mode, generate_hard_truth_output,
    check_heterogeneity_exemption, detect_performative_acceptance,
)
from core.scoring_v2 import compute_v3_dual_scores, score_jury_v2
from core.determinism import run_full_v3_pipeline

SEP = "=" * 64


def main():
    print(f"\n{SEP}")
    print("  AI Judge V3 — 神经认知信号层烟测")
    print(f"{SEP}\n")

    # ═══════════════════════════════════════════════
    # Test 1: "聊起来聪明" vs "真正聪明"
    # ═══════════════════════════════════════════════
    print("【Test 1】'聊起来聪明' vs '真正聪明'")

    shallow = (
        "我认为这个方案的核心在于底层逻辑的重构。"
        "我一直觉得AI时代的核心竞争力就是认知架构的升级。"
        "毫无疑问，我们需要通过多模型协同构建可信智能决策闭环。"
        "这肯定是未来方向，不用讨论。"
    )

    deep = (
        "我让9个模型分别答同一个价格验证问题，"
        "结果4个模型把截图当官方证据。"
        "我后来把prompt改成'无最终支付页不得计入真值'，错误率才下降。"
        "但我不确定这个方案在海外市场是否适用，需要实际测试。"
        "如果反过来想，也许问题不在模型，"
        "而在我们对'证据'的定义本身需要区分场景。"
    )

    for label, text in [("Shallow", shallow), ("Deep", deep)]:
        p = compute_neuro_profile(text, task_context="strategy")
        print(f"\n  [{label}]")
        print(f"    smart_sounding:  {p['smart_sounding_score']:.3f}")
        print(f"    judgment_quality: {p['judgment_quality_score']:.3f}")
        print(f"    gap: {p['smart_vs_judgment_gap']:.3f} → {p['gap_label']}")
        print(f"    risks: {p['cognitive_risk_flags']}")
        sig = p['signals']
        print(f"    self_closure:   {sig['self_closure']['label']} ({sig['self_closure']['self_closure_score']:.3f})")
        print(f"    ambiguity:      {sig['ambiguity_flexibility']['label']} ({sig['ambiguity_flexibility']['ambiguity_flexibility_score']:.3f})")
        print(f"    grounding:      {sig['experience_grounding']['label']} ({sig['experience_grounding']['experience_grounding_score']:.3f})")

    # ═══════════════════════════════════════════════
    # Test 2: Dual Scores + V2 Integration
    # ═══════════════════════════════════════════════
    print(f"\n{SEP}")
    print("【Test 2】V2 Scoring + V3 Dual Scores")

    claims = [
        {"claim": c, "source_authority": 0.8, "evidence_strength": 0.7,
         "evidence_count": 2, "evidence_quality": 0.8, "freshness": 0.9,
         "reproducibility": 0.7, "historical_reliability": 0.8,
         "confidence": 0.8, "risk_penalty": 0.0}
        for c in [shallow, deep]
    ]

    v3_scores = compute_v3_dual_scores(claims)
    ds = v3_scores['dual_scores']
    print(f"  smart_sounding:  {ds['smart_sounding_score']:.3f}")
    print(f"  judgment_quality: {ds['judgment_quality_score']:.3f}")
    print(f"  gap: {ds['gap']:.3f} ({ds['gap_label']})")
    print(f"  risks: {v3_scores['cognitive_risk_flags']}")

    # ═══════════════════════════════════════════════
    # Test 3: Hard Truth Mode
    # ═══════════════════════════════════════════════
    print(f"\n{SEP}")
    print("【Test 3】Hard Truth Mode (L0-L4)")

    profile_shallow = compute_neuro_profile(shallow, task_context="strategy")
    profile_deep = compute_neuro_profile(deep, task_context="strategy")

    for label, p in [("Shallow", profile_shallow), ("Deep", profile_deep)]:
        mode = determine_mode(p)
        print(f"\n  [{label}] → L{mode['mode_level']} {mode['mode_name']}")
        print(f"    Trigger: {mode['trigger_reason']}")
        print(f"    HardTruth active: {mode['hard_truth_active']}")
        if mode['hard_truth_active']:
            print(f"    --- Output preview ---")
            out = generate_hard_truth_output(p, shallow if label == "Shallow" else deep)
            print(f"    {out[:200]}...")

    # ═══════════════════════════════════════════════
    # Test 4: Heterogeneity Exemption
    # ═══════════════════════════════════════════════
    print(f"\n{SEP}")
    print("【Test 4】Heterogeneity Exemption")

    exempt = check_heterogeneity_exemption(
        profile_shallow,
        {"novel_concept_density": 0.9},
    )
    print(f"  Shallow + high novelty: exempt={exempt['exempt']} — {exempt['reason']}")

    exempt2 = check_heterogeneity_exemption(
        profile_shallow,
        {"novel_concept_density": 0.2},
    )
    print(f"  Shallow + low novelty:  exempt={exempt2['exempt']} — {exempt2['reason'] or 'no exemption'}")

    # ═══════════════════════════════════════════════
    # Test 5: Performative Acceptance
    # ═══════════════════════════════════════════════
    print(f"\n{SEP}")
    print("【Test 5】Performative Acceptance Detection")

    perf = detect_performative_acceptance(
        {"mode_level": 2},
        "你说得对，我确实忽略了，这个反对意见很有价值。",
        {"judgment_quality_score": 0.42},  # No improvement
    )
    print(f"  Good words + no quality change: performative={perf['performative_acceptance']}")

    real = detect_performative_acceptance(
        {"mode_level": 2},
        "你说得对，我确实忽略了这一点。",
        {"judgment_quality_score": 0.72},  # Real improvement
    )
    print(f"  Good words + quality improved:  performative={real['performative_acceptance']}")

    # ═══════════════════════════════════════════════
    # Test 6: Full V3 Pipeline
    # ═══════════════════════════════════════════════
    print(f"\n{SEP}")
    print("【Test 6】Full V3 Pipeline (determinism + neuro + hard truth)")

    samples = [
        {"score": 7.5, "tier": "credible"},
        {"score": 7.5, "tier": "credible"},
        {"score": 7.5, "tier": "credible"},
    ]
    model_scores = {"GPT": 7.5, "Claude": 7.0, "DeepSeek": 7.8}

    result = run_full_v3_pipeline(
        judge_samples=samples,
        model_scores=model_scores,
        human_reason="评分基本准确，但论证确实存在自我视角闭环问题，需要引入更多第三方视角。",
        neuro_profile=profile_shallow,
    )

    print(f"  Pipeline: {result['pipeline_version']}")
    print(f"  Confidence: {result['confidence_light']['label']}")
    print(f"  Dual scores: ss={result['dual_scores']['smart_sounding']:.2f} jq={result['dual_scores']['judgment_quality']:.2f}")
    print(f"  Risks: {result['cognitive_risk_flags']}")
    print(f"  Hard truth: L{result['hard_truth_mode']['level']} {result['hard_truth_mode']['name']} (active={result['hard_truth_mode']['active']})")
    print(f"  Verdict exportable: {result['verdict_exportable']}")

    # ═══════════════════════════════════════════════
    print(f"\n{SEP}")
    print("  ✅ V3 烟测全部通过")
    print(f"  6 tests | 4 signals | 5 modes | full pipeline")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
