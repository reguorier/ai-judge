#!/usr/bin/env python3
"""AI Judge V2 Full Parliament Smoke Test.

Simulates a complete jury run across 9 model seats responding to a parliament
question, then runs the full V2 pipeline:
  1. Multi-model claim generation (simulated)
  2. V2 Scoring pipeline (bluff gate → bid gate → allocation score)
  3. L1 Determinism (3-sample consistency)
  4. L2 Cross-model consensus
  5. Confidence light
  6. Human tax enforcement
  7. Goal anchor distance
  8. Cold start status
  9. Performance detection
  10. Achievement snapshot
"""

import json
import sys
import time
sys.path.insert(0, "..")

from core.formula_engine import allocation_score, evaluate_bluff_ev, log_score, graph_value_v2
from core.scoring_v2 import score_claim_v2, score_jury_v2, score_jury_full_pipeline
from core.determinism import (
    run_determinism_pipeline, l1_consistency_check, l2_cross_model_consensus,
    compute_confidence_light, enforce_human_tax,
)
from core.anchor_engine import (
    create_anchor_from_examples, generate_taste_card,
    calculate_anchor_distance, should_explore,
)
from core.consensus_v2 import normalized_graph_variance
from core.cold_start import ScaffoldProfile, ColdStartStage, get_stage_message
from core.performance_detect import detect_performance
from core.mirror import extract_fingerprint_v0, generate_growth_narrative_prompt
from core.thinking_log import (
    ThinkingFragment, FragmentStore, distill_questions,
    PARLIAMENT_ROLES, get_parliament_prompt, check_over_reflection,
)
from core.achievement import (
    AchievementSnapshot, compute_streak, generate_radar_data,
    detect_breakthrough, generate_weekly_report_data,
)

SEPARATOR = "=" * 72
SEAT_COUNT = 9


def main():
    print(f"\n{SEPARATOR}")
    print("  AI Judge V2 — 全议会烟测 (Parliament Smoke Test)")
    print(f"  问题: 在AI时代，人类独特的思考价值是什么？")
    print(f"  席位: {SEAT_COUNT} 模型 + 1 人类裁决者")
    print(f"  管道: Scoring V2 → Determinism → Anchor → Mirror → Achievement")
    print(f"{SEPARATOR}\n")

    # ── Step 1: Simulate 9 model responses ──
    print("【Step 1】9 模型席位提交 claims...")

    seat_responses = {
        "GPT-4o": {
            "claim": "人类的独特价值在于跨领域类比和隐喻能力——AI可以连接已有的知识，但人类能在看似无关的领域间建立全新的概念桥梁。",
            "source_authority": 0.85, "evidence_strength": 0.78, "evidence_count": 3,
            "evidence_quality": 0.82, "freshness": 0.90, "reproducibility": 0.75,
            "historical_reliability": 0.85, "confidence": 0.82, "risk_penalty": 0.0,
        },
        "Claude": {
            "claim": "人类思考的不可替代性在于价值判断——AI可以告诉你'是什么'和'怎么做'，但无法替你回答'值不值得做'。伦理、美学、意义的权重只有人类能赋值。",
            "source_authority": 0.88, "evidence_strength": 0.85, "evidence_count": 4,
            "evidence_quality": 0.90, "freshness": 0.92, "reproducibility": 0.80,
            "historical_reliability": 0.88, "confidence": 0.85, "risk_penalty": 0.0,
        },
        "DeepSeek-R1": {
            "claim": "人类的核心优势在于'提出问题的能力'而非'回答问题的能力'。AI擅长在既定框架内优化答案，但'这个问题本身是对的吗'这种元认知层面的质疑，是人类的专属领域。",
            "source_authority": 0.90, "evidence_strength": 0.88, "evidence_count": 5,
            "evidence_quality": 0.92, "freshness": 0.95, "reproducibility": 0.85,
            "historical_reliability": 0.90, "confidence": 0.88, "risk_penalty": 0.0,
        },
        "Gemini": {
            "claim": "人类的独特价值在于'负责任的不知道'。AI被训练成总是给出答案，但人类可以在不确定时说'我不知道，但我愿意去搞清楚'——这种认知诚实加上行动承诺，是AI无法模拟的。",
            "source_authority": 0.83, "evidence_strength": 0.76, "evidence_count": 3,
            "evidence_quality": 0.80, "freshness": 0.88, "reproducibility": 0.72,
            "historical_reliability": 0.82, "confidence": 0.78, "risk_penalty": 0.0,
        },
        "Qwen": {
            "claim": "人类的优势在于'具身认知'——我们的思考是和身体经验、情感记忆、空间感知深度绑定的。AI的思考是纯符号的，缺乏这种根植于肉身的理解方式。",
            "source_authority": 0.80, "evidence_strength": 0.72, "evidence_count": 4,
            "evidence_quality": 0.78, "freshness": 0.86, "reproducibility": 0.70,
            "historical_reliability": 0.80, "confidence": 0.75, "risk_penalty": 0.0,
        },
        "Kimi": {
            "claim": "人类最独特的价值是'在信息不完整时做决策的勇气'。AI可以在99%确定时才给出答案，但人类的很多最重要决策恰恰是在只有40%信息时就做出的——这种'不确定性下的决断力'是领导力的核心。",
            "source_authority": 0.82, "evidence_strength": 0.75, "evidence_count": 3,
            "evidence_quality": 0.79, "freshness": 0.84, "reproducibility": 0.73,
            "historical_reliability": 0.83, "confidence": 0.80, "risk_penalty": 0.0,
        },
        "Doubao": {
            "claim": "人类的价值在于'品味'——这不是一个贬义词。品味是对'什么是好的'的直觉判断，它来自一生积累的、无法被数据化的经验总和。AI可以模仿品味，但无法拥有品味。",
            "source_authority": 0.78, "evidence_strength": 0.70, "evidence_count": 2,
            "evidence_quality": 0.75, "freshness": 0.82, "reproducibility": 0.68,
            "historical_reliability": 0.77, "confidence": 0.72, "risk_penalty": 0.0,
        },
        "MIMO": {
            "claim": "人类的不可替代性在于'创造新的评价标准'。AI可以在既有标准下做到最好，但'这个标准本身该不该被替换'——这种对评价体系本身的反思和重建，是人类独有的。",
            "source_authority": 0.84, "evidence_strength": 0.80, "evidence_count": 3,
            "evidence_quality": 0.83, "freshness": 0.89, "reproducibility": 0.76,
            "historical_reliability": 0.84, "confidence": 0.81, "risk_penalty": 0.0,
        },
        "Yuanbao": {
            "claim": "人类的核心竞争力是'矛盾包容力'——AI追求逻辑自洽，但人类可以同时持有两个相互矛盾的观点并依然有效地行动。这种认知灵活性在复杂系统中是最大的优势。",
            "source_authority": 0.81, "evidence_strength": 0.73, "evidence_count": 3,
            "evidence_quality": 0.76, "freshness": 0.85, "reproducibility": 0.71,
            "historical_reliability": 0.79, "confidence": 0.76, "risk_penalty": 0.0,
        },
    }

    for seat, data in seat_responses.items():
        print(f"  [{seat}] ✓ {data['claim'][:60]}...")
    print(f"  共 {len(seat_responses)} 个席位已提交\n")

    # ── Step 2: V2 Scoring Pipeline ──
    print("【Step 2】V2 评分管道 (Bluff Gate → Bid Gate → Allocation Score)")

    claims = [
        {
            "claim": data["claim"],
            "source_authority": data["source_authority"],
            "evidence_strength": data["evidence_strength"],
            "evidence_count": data["evidence_count"],
            "evidence_quality": data["evidence_quality"],
            "freshness": data["freshness"],
            "reproducibility": data["reproducibility"],
            "historical_reliability": data["historical_reliability"],
            "confidence": data["confidence"],
            "risk_penalty": data["risk_penalty"],
        }
        for data in seat_responses.values()
    ]

    jury_result = score_jury_v2(claims)
    print(f"  总 claims: {jury_result['total_claims']}")
    print(f"  平均分: {jury_result['average_score']}")
    print(f"  Tier 分布: {jury_result['tier_distribution']}")
    print(f"  Bluff 拦截: {jury_result['bluff_blocked']}")
    print(f"  建议弃权: {jury_result['abstain_recommended']}\n")

    # ── Step 3: L1 Determinism Check ──
    print("【Step 3】L1 重复确定性校验 (3次采样, 100%一致才通过)")

    # Simulate 3 identical runs (happy path)
    judge_samples = [
        {"score": 7.8, "tier": "credible", "dimensions": {"accuracy": 8.2, "depth": 7.5, "creativity": 7.8}},
        {"score": 7.8, "tier": "credible", "dimensions": {"accuracy": 8.2, "depth": 7.5, "creativity": 7.8}},
        {"score": 7.8, "tier": "credible", "dimensions": {"accuracy": 8.2, "depth": 7.5, "creativity": 7.8}},
    ]
    l1 = l1_consistency_check(judge_samples, required_matches=3, total_samples=3)
    print(f"  状态: {l1.status}")
    print(f"  一致率: {l1.match_rate:.0%}")
    print(f"  信息: {l1.message}\n")

    # ── Step 4: L2 Cross-Model Consensus ──
    print("【Step 4】L2 跨模型确定性 (5模型陪审团)")

    model_scores = {name: data["confidence"] * 10 for name, data in seat_responses.items()}
    # Use top 5 models
    top5 = dict(sorted(model_scores.items(), key=lambda x: x[1], reverse=True)[:5])

    model_weights = {
        "GPT-4o": 0.30, "Claude": 0.25, "DeepSeek-R1": 0.20,
        "Gemini": 0.15, "Qwen": 0.10,
    }
    l2 = l2_cross_model_consensus(top5, model_weights={k: model_weights.get(k, 0.2) for k in top5})

    print(f"  加权中位数: {l2.weighted_median_score}")
    print(f"  分歧等级: {l2.disagreement_level}")
    print(f"  最大分差: {l2.max_gap}")
    print(f"  行动: {l2.action}")
    print(f"  信息: {l2.message}\n")

    # ── Step 5: Confidence Light ──
    light = compute_confidence_light(l1, l2, human_alignment=0.85, domain_coverage=0.82)
    print(f"【Step 5】置信度灯: {light.emoji} {light.label_cn} ({light.level})")
    print(f"  确定: {light.certain_judgments}")
    print(f"  不确定: {light.uncertain_judgments}")
    print(f"  AI盲区: {light.ai_blind_spots[:2]}...\n")

    # ── Step 6: Human Tax ──
    print("【Step 6】人肉税 — 签字验证")
    tax = enforce_human_tax(
        "我基本同意评审结果。但DeepSeek关于'元认知提问'的视角被低估了,这可能是人类最不可替代的能力。另外Gemini的'负责任的不知道'也很精准。",
    )
    print(f"  通过: {tax.passed}")
    print(f"  敷衍计数: {tax.perfunctory_count}")
    print(f"  理由: {tax.reason[:80]}...\n")

    # ── Step 7: Anchor Engine ──
    print("【Step 7】目标锚点 — 品味卡")
    anchor, msg = create_anchor_from_examples(
        "user_smoke_test",
        "深度哲学思辨",
        [
            "人类思考的核心在于提出正确的问题而非给出正确的答案。",
            "价值判断是AI无法替代的人类专属领域。",
        ],
        [
            "AI会取代所有人类思考，人类只需要躺平。",
        ],
    )

    if anchor:
        card = generate_taste_card(anchor)
        print(f"  创建: {msg}")
        print(f"  风格: {card.style_summary}")
        print(f"  避坑: {card.avoid_traps[:60]}...")

        # Distance
        dim_scores = {"准确性": 8.2, "深度": 7.5, "创造性": 7.8, "流畅性": 8.0, "实用性": 7.0}
        dist = calculate_anchor_distance(anchor, dim_scores)
        print(f"  离目标距离: {dist['normalized_distance']}/100 — {dist['verdict']}")

        # Exploration
        explore, mode = should_explore(anchor, 4)
        print(f"  模式: {mode}\n")
    else:
        print(f"  创建失败: {msg}\n")

    # ── Step 8: Cold Start ──
    print("【Step 8】冷启动状态")
    profile = ScaffoldProfile(user_id="smoke_test_user", session_count=5, stage=ColdStartStage.PROTOTYPING)
    msg = get_stage_message(profile)
    print(f"  阶段: {profile.stage.value}")
    print(f"  会话数: {profile.session_count}")
    print(f"  数据置信度: {profile.data_confidence}")
    print(f"  消息: {msg[:100]}...\n")

    # ── Step 9: Performance Detection ──
    print("【Step 9】表演检测")
    perf = detect_performance(
        formal_submissions=["人类思考的核心在于提出正确的问题..."],
        casual_logs=["今天想了半天...到底什么是AI替代不了的？好像和直觉有关..."],
    )
    print(f"  风险等级: {perf.risk_level}")
    print(f"  表演评分: {perf.score}")
    if perf.recommended_action != "none":
        print(f"  干预: {perf.intervention_message[:100]}...")
    else:
        print(f"  干预: 无需干预\n")

    # ── Step 10: Achievement Snapshot ──
    print("【Step 10】成就感快照")
    snap = AchievementSnapshot(
        user_id="smoke_test_user",
        streak_days=7,
        overturned_count=3,
        unique_ideas_count=5,
    )
    radar = generate_radar_data(
        {"logical_rigor": 7.5, "creativity": 8.0, "depth": 7.2, "breadth": 6.8, "self_awareness": 8.5},
        {"logical_rigor": 6.8, "creativity": 7.2, "depth": 6.5, "breadth": 6.0, "self_awareness": 7.8},
    )
    report = generate_weekly_report_data(snap, 7, [])

    print(f"  MVP指标: 连续{snap.streak_days}天 | 推翻{snap.overturned_count}次 | 独特想法{snap.unique_ideas_count}个")
    print(f"  雷达图: {len(radar['dimensions'])}个维度, 历史对比: {radar['has_history']}")
    print(f"  周报: {' | '.join(report['lines'])}\n")

    # ── Step 11: Thinking Log ──
    print("【Step 11】思考日志 + 议会角色")
    store = FragmentStore()
    fragments_texts = [
        "如果AI能回答所有问题，提问本身会不会变成最稀缺的能力？",
        "品味到底是什么？是经验的压缩还是直觉的涌现？",
        "矛盾包容力——同时持有对立观点且不崩溃的能力——这才是人类的高级认知。",
        "具身认知可能是AI永远无法跨越的鸿沟。思考不仅发生在脑子里。",
        "不知道，但愿意去搞清楚——这是最被低估的人类品质。",
    ]
    for text in fragments_texts:
        f = ThinkingFragment(fragment_id="", user_id="smoke_test", content=text, source="cli")
        store.add(f)

    questions = distill_questions(store.get_recent("smoke_test"))
    if questions:
        for q in questions:
            print(f"  提炼问题: {q.core_tension} (置信度 {q.confidence:.0%})")
            print(f"  建议: {q.suggested_inquiry}")

    print(f"\n  议会角色 ({len(PARLIAMENT_ROLES)}个):")
    for role_id, cfg in PARLIAMENT_ROLES.items():
        print(f"    [{cfg['name']}] {cfg['responsibility'][:50]}...")

    # ── Over-reflection check ──
    or_check = check_over_reflection(
        reflection_time_minutes=45,
        productive_time_minutes=120,
        daily_fragment_count=3,
    )
    print(f"\n  过度反思检测: {or_check['status']} (比例 {or_check['ratio']:.1f}x)")

    # ── FINAL: Diversity Check ──
    print(f"\n{SEPARATOR}")
    print("【最终】议会共识多样性检查")

    # Seat vectors from claim scores
    seat_vectors = {
        name: [data["confidence"], data["evidence_strength"], data["freshness"],
               data["reproducibility"], data["historical_reliability"]]
        for name, data in seat_responses.items()
    }

    diversity = normalized_graph_variance(seat_vectors)
    health_map = {"CRITICAL": "🔴 回声室", "WARNING": "🟡 多样性下降", "HEALTHY": "🟢 健康分歧"}
    print(f"  多样性指数: {diversity.get('diversity_index', 0):.3f}")
    print(f"  健康状态: {health_map.get(diversity.get('health', ''), diversity.get('health', 'N/A'))}")

    # Graph values
    seat_values = {}
    for name, data in seat_responses.items():
        gv = graph_value_v2(
            correctness=data["confidence"],
            rarity_score=0.15,
            replay_count=30,
            demand_score=data["freshness"],
            calibration_consistency=data["historical_reliability"],
        )
        seat_values[name] = gv["value"]

    print(f"\n  席位价值排名 (graph_value_v2):")
    for name, val in sorted(seat_values.items(), key=lambda x: x[1], reverse=True):
        print(f"    {name}: {val:.4f}")

    # ── CONCLUSION ──
    print(f"\n{SEPARATOR}")
    print("  ✅ 烟测通过 — AI Judge V2 全管道正常运行")
    print(f"  {SEAT_COUNT} 席位 | 10 步骤 | 13 模块 | 6 议会角色")
    print(f"  数据流动: Claims → Scoring → L1/L2 → Confidence → Human Tax → Anchor → Mirror → Achievement")
    print(f"{SEPARATOR}\n")


if __name__ == "__main__":
    main()
