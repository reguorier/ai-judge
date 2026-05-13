#!/usr/bin/env python3
"""AI Judge — Unified CLI entry point v3.1.0.

Usage:
    ai-judge license status
    ai-judge jury --question "Is this pricing competitive?"
    ai-judge collect --run latest
    ai-judge verdict --run latest
    ai-judge reflect --date 2026-05-09
    ai-judge list
    ai-judge score-v2 --demo          # Phase 1 scoring demo
    ai-judge score-v2 --claims-file path/to/claim-ledger.json

    # V3.0 commands:
    ai-judge determinism --demo       # Run determinism pipeline demo
    ai-judge anchor create --name "My Style" --pos ex1.txt --neg ex2.txt
    ai-judge cold-start status        # Check cold start stage
    ai-judge mirror --user-id <id>    # Generate thinking fingerprint report
    ai-judge log add "fragment text"  # Add thinking fragment
    ai-judge log distill              # Distill questions from fragments
    ai-judge achievement --user-id <id> # Show achievement snapshot

    # V3.1 commands:
    ai-judge neuro-profile --demo     # 4 neuro-cognitive proxy signals + dual scores
    ai-judge hard-truth --demo        # L0-L4 judgment-first feedback
    ai-judge v3-pipeline --demo       # Full determinism + neuro + hard truth pipeline
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ROOT = Path(os.environ.get("AI_JUDGE_ROOT", Path.home() / ".ai-judge"))


def _check_license_or_exit() -> None:
    """Gate: refuse any production command without a valid license."""
    from core.license_validator import validate_license

    status = validate_license()
    if not status.valid:
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
        sys.exit(1)


def _run_paid_core(command: str, args: argparse.Namespace) -> int:
    """Delegate production behavior to the paid core package."""
    try:
        from ai_judge_core import commands  # type: ignore[import-untyped]
    except ImportError:
        print(json.dumps({
            "ok": False,
            "error": "paid_core_missing",
            "message": (
                "Production commands require the paid ai-judge-core package. "
                "Install it to run jury, collect, verdict, and reflect commands."
            ),
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    runner = getattr(commands, command, None)
    if runner is None:
        print(json.dumps({
            "ok": False,
            "error": "command_missing",
            "message": f"Paid core does not expose command '{command}'.",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    return int(runner(args))


def cmd_license(args: argparse.Namespace) -> int:
    """License management."""
    from core.license_validator import activate_license, validate_license

    action = getattr(args, "license_action", "status")
    if action == "activate":
        key = args.key or os.environ.get("LICENSE_KEY", "")
        if not key:
            print("Error: --key required, or set LICENSE_KEY", file=sys.stderr)
            return 2
        status = activate_license(key)
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
        return 0 if status.valid else 1
    else:
        status = validate_license()
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
        return 0 if status.valid else 1


def cmd_jury(args: argparse.Namespace) -> int:
    """Create a jury session."""
    _check_license_or_exit()
    return _run_paid_core("jury", args)


def cmd_collect(args: argparse.Namespace) -> int:
    """Collect answers from AI seats."""
    _check_license_or_exit()
    return _run_paid_core("collect", args)


def cmd_verdict(args: argparse.Namespace) -> int:
    """Generate auditable verdict."""
    _check_license_or_exit()
    return _run_paid_core("verdict", args)


def cmd_reflect(args: argparse.Namespace) -> int:
    """Generate daily reflection log."""
    _check_license_or_exit()
    return _run_paid_core("reflect", args)


def cmd_list(args: argparse.Namespace) -> int:
    """List recent jury runs."""
    _check_license_or_exit()
    return _run_paid_core("list_runs", args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-judge",
        description="Multi-model AI jury system — 9 models deliberate, you hold the gavel.",
    )
    sub = parser.add_subparsers(dest="command")

    # license
    lic = sub.add_parser("license", help="License management")
    lic_sub = lic.add_subparsers(dest="license_action")
    act = lic_sub.add_parser("activate", help="Activate a license key")
    act.add_argument("--key", help="License key (or set LICENSE_KEY env var)")
    act.set_defaults(func=cmd_license)
    st = lic_sub.add_parser("status", help="Check license status")
    st.set_defaults(func=cmd_license)

    # jury
    j = sub.add_parser("jury", help="Create a jury session")
    j.add_argument("--question", required=True, help="The question for the jury")
    j.set_defaults(func=cmd_jury)

    # collect
    c = sub.add_parser("collect", help="Collect answers from AI seats")
    c.add_argument("--run", help="Run ID (default: latest)")
    c.set_defaults(func=cmd_collect)

    # verdict
    v = sub.add_parser("verdict", help="Generate auditable verdict")
    v.add_argument("--run", help="Run ID (default: latest)")
    v.set_defaults(func=cmd_verdict)

    # reflect
    r = sub.add_parser("reflect", help="Generate daily reflection log")
    r.add_argument("--date", help="Date in YYYY-MM-DD (default: today)")
    r.set_defaults(func=cmd_reflect)

    # list
    lc = sub.add_parser("list", help="List recent jury runs")
    lc.set_defaults(func=cmd_list)

    # score-v2 (Phase 1 scoring)
    sv2 = sub.add_parser("score-v2", help="Score claims using v2.0 Phase 1 formulas")
    sv2.add_argument("--claims-file", help="Path to claim-ledger.json")
    sv2.add_argument("--demo", action="store_true", help="Run a scoring demo with sample claims")
    sv2.set_defaults(func=cmd_score_v2)

    # ── V2 Commands ──

    # determinism
    det = sub.add_parser("determinism", help="Run determinism pipeline (L1 + L2 + confidence + human tax)")
    det.add_argument("--demo", action="store_true", help="Run determinism pipeline demo")
    det.set_defaults(func=cmd_determinism)

    # anchor
    anc = sub.add_parser("anchor", help="Goal anchor management")
    anc_sub = anc.add_subparsers(dest="anchor_action")
    anc_create = anc_sub.add_parser("create", help="Create a new goal anchor from examples")
    anc_create.add_argument("--name", required=True, help="Anchor name")
    anc_create.add_argument("--user-id", default="default", help="User ID")
    anc_create.add_argument("--pos", action="append", help="Positive example text (repeatable)")
    anc_create.add_argument("--neg", action="append", help="Negative example text (repeatable)")
    anc_create.set_defaults(func=cmd_anchor)
    anc_status = anc_sub.add_parser("status", help="Show anchor status and drift")
    anc_status.add_argument("--user-id", default="default", help="User ID")
    anc_status.set_defaults(func=cmd_anchor)

    # cold-start
    cs = sub.add_parser("cold-start", help="Cold start stage management")
    cs.add_argument("action", choices=["status", "advance"], nargs="?", default="status")
    cs.add_argument("--user-id", default="default", help="User ID")
    cs.set_defaults(func=cmd_cold_start)

    # mirror
    mir = sub.add_parser("mirror", help="Thinking mirror — fingerprint and growth narrative")
    mir.add_argument("--user-id", required=True, help="User ID")
    mir.set_defaults(func=cmd_mirror)

    # log (thinking fragments)
    log = sub.add_parser("log", help="Thinking log — fragment management")
    log_sub = log.add_subparsers(dest="log_action")
    log_add = log_sub.add_parser("add", help="Add a thinking fragment")
    log_add.add_argument("content", help="Fragment text")
    log_add.add_argument("--user-id", default="default", help="User ID")
    log_add.add_argument("--source", default="cli", choices=["hotkey", "browser_clip", "chat_log", "voice", "cli"])
    log_add.set_defaults(func=cmd_log)
    log_distill = log_sub.add_parser("distill", help="Distill questions from fragments")
    log_distill.add_argument("--user-id", default="default", help="User ID")
    log_distill.set_defaults(func=cmd_log)

    # achievement
    ach = sub.add_parser("achievement", help="Achievement metrics and visualization data")
    ach.add_argument("--user-id", required=True, help="User ID")
    ach.set_defaults(func=cmd_achievement)

    # ── V3 Commands ──

    # neuro-profile
    np = sub.add_parser("neuro-profile", help="V3: Run neuro-cognitive profiling on text")
    np.add_argument("--text", help="Text to profile")
    np.add_argument("--text-file", help="File containing text to profile")
    np.add_argument("--demo", action="store_true", help="Run demo with sample texts")
    np.set_defaults(func=cmd_neuro_profile)

    # hard-truth
    ht = sub.add_parser("hard-truth", help="V3: Run hard truth mode simulation")
    ht.add_argument("--demo", action="store_true", help="Run hard truth demo")
    ht.set_defaults(func=cmd_hard_truth)

    # v3-pipeline (full V3)
    v3 = sub.add_parser("v3-pipeline", help="V3: Run full V3 pipeline (determinism + neuro + hard truth)")
    v3.add_argument("--demo", action="store_true", help="Run full V3 pipeline demo")
    v3.set_defaults(func=cmd_v3_pipeline)

    return parser


def cmd_score_v2(args: argparse.Namespace) -> int:
    """Run Phase 1 scoring on claims."""
    import json

    if args.demo:
        sample_claims = [
            {"claim": "Market timing is favorable due to Q3 demand", "source_authority": 0.85, "evidence_strength": 0.78, "evidence_count": 3, "evidence_quality": 0.90, "freshness": 0.92, "reproducibility": 0.80, "historical_reliability": 0.88, "confidence": 0.82, "risk_penalty": 0.0},
            {"claim": "Pricing should be aggressive", "source_authority": 0.60, "evidence_strength": 0.35, "evidence_count": 0, "evidence_quality": 0.20, "freshness": 0.70, "reproducibility": 0.40, "historical_reliability": 0.55, "confidence": 0.95, "risk_penalty": 0.05},
            {"claim": "Currency risk is higher than projected", "source_authority": 0.90, "evidence_strength": 0.85, "evidence_count": 4, "evidence_quality": 0.92, "freshness": 0.95, "reproducibility": 0.88, "historical_reliability": 0.85, "confidence": 0.78, "risk_penalty": 0.0, "known_outcome": True},
            {"claim": "Regulatory compliance requires 6-8 weeks", "source_authority": 0.75, "evidence_strength": 0.70, "evidence_count": 2, "evidence_quality": 0.75, "freshness": 0.88, "reproducibility": 0.72, "historical_reliability": 0.80, "confidence": 0.75, "risk_penalty": 0.0},
            {"claim": "Trust me, this market will 10x", "source_authority": 0.15, "evidence_strength": 0.10, "evidence_count": 0, "evidence_quality": 0.05, "freshness": 0.50, "reproducibility": 0.05, "historical_reliability": 0.20, "confidence": 0.99, "risk_penalty": 0.10},
        ]

        from core.scoring_v2 import score_jury_full_pipeline
        from core.consensus_v2 import diversity_alert_pipeline

        # Simulated seat vectors (9 seats × 5 claim dimensions)
        seat_vectors = {
            "Gemini":    [0.85, 0.60, 0.90, 0.75, 0.50],
            "ChatGPT":   [0.82, 0.55, 0.88, 0.72, 0.45],
            "DeepSeek":  [0.88, 0.65, 0.92, 0.78, 0.30],
            "Qwen":      [0.80, 0.58, 0.87, 0.73, 0.48],
            "Kimi":      [0.83, 0.62, 0.89, 0.76, 0.40],
            "Grok":      [0.70, 0.50, 0.82, 0.68, 0.55],
            "Yuanbao":   [0.84, 0.59, 0.90, 0.74, 0.47],
            "MiMo":      [0.78, 0.56, 0.86, 0.70, 0.52],
            "Doubao":    [0.81, 0.61, 0.88, 0.75, 0.49],
        }

        seat_performance = {
            "Gemini":    {"correctness": 0.88, "calibration_consistency": 0.82, "rarity_score": 0.15, "replay_count": 45, "demand_score": 0.7},
            "ChatGPT":   {"correctness": 0.85, "calibration_consistency": 0.78, "rarity_score": 0.12, "replay_count": 52, "demand_score": 0.8},
            "DeepSeek":  {"correctness": 0.90, "calibration_consistency": 0.85, "rarity_score": 0.22, "replay_count": 38, "demand_score": 0.6},
            "Qwen":      {"correctness": 0.82, "calibration_consistency": 0.75, "rarity_score": 0.10, "replay_count": 30, "demand_score": 0.5},
            "Kimi":      {"correctness": 0.86, "calibration_consistency": 0.80, "rarity_score": 0.18, "replay_count": 41, "demand_score": 0.65},
            "Grok":      {"correctness": 0.75, "calibration_consistency": 0.65, "rarity_score": 0.30, "replay_count": 25, "demand_score": 0.55},
            "Yuanbao":   {"correctness": 0.84, "calibration_consistency": 0.77, "rarity_score": 0.14, "replay_count": 35, "demand_score": 0.6},
            "MiMo":      {"correctness": 0.80, "calibration_consistency": 0.72, "rarity_score": 0.08, "replay_count": 28, "demand_score": 0.5},
            "Doubao":    {"correctness": 0.83, "calibration_consistency": 0.76, "rarity_score": 0.11, "replay_count": 33, "demand_score": 0.55},
        }

        result = score_jury_full_pipeline(sample_claims, seat_vectors, seat_performance)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.claims_file:
        from pathlib import Path

        path = Path(args.claims_file)
        if not path.exists():
            print(f"Error: {args.claims_file} not found", file=sys.stderr)
            return 1
        claims = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(claims, list):
            claims = claims.get("claim_ledger", claims.get("claims", []))
        from core.scoring_v2 import score_jury_v2

        result = score_jury_v2(claims)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("Usage: ai-judge score-v2 --demo | --claims-file <path>", file=sys.stderr)
    return 2


# ── V2 Command Handlers ──

def cmd_determinism(args: argparse.Namespace) -> int:
    """Run determinism pipeline demo."""
    from core.determinism import (
        l1_consistency_check,
        l2_cross_model_consensus,
        compute_confidence_light,
        enforce_human_tax,
        run_determinism_pipeline,
    )

    if not args.demo:
        print("Usage: ai-judge determinism --demo", file=sys.stderr)
        return 2

    # Simulate 3 judge samples with slight variation
    samples = [
        {"score": 7.5, "dimensions": {"accuracy": 8.0, "depth": 7.0, "creativity": 7.5}},
        {"score": 7.5, "dimensions": {"accuracy": 8.0, "depth": 7.0, "creativity": 7.5}},
        {"score": 7.5, "dimensions": {"accuracy": 8.0, "depth": 7.0, "creativity": 7.5}},
    ]

    # Multi-model scores
    model_scores = {
        "GPT-4o": 7.5,
        "Claude": 7.0,
        "DeepSeek-R1": 8.0,
        "Qwen": 7.2,
        "Selene": 7.8,
    }

    result = run_determinism_pipeline(
        judge_samples=samples,
        model_scores=model_scores,
        human_reason="我认为评分基本准确，但创造性维度可能被低估，因为我的目标场景更看重新颖性而非规范性。",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_anchor(args: argparse.Namespace) -> int:
    """Goal anchor management."""
    from core.anchor_engine import create_anchor_from_examples, generate_taste_card

    user_id = getattr(args, "user_id", "default")
    action = getattr(args, "anchor_action", "status")

    if action == "create":
        name = args.name
        pos = args.pos or []
        neg = args.neg or []
        anchor, msg = create_anchor_from_examples(user_id, name, pos, neg)

        if anchor is None:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False, indent=2))
            return 1

        card = generate_taste_card(anchor)
        print(json.dumps({
            "ok": True,
            "message": msg,
            "anchor": anchor.to_dict(),
            "taste_card": {
                "style": card.style_summary,
                "avoid": card.avoid_traps,
                "distance": card.current_distance,
                "weights": card.dimension_weights,
            },
        }, ensure_ascii=False, indent=2))
        return 0

    # status
    print(json.dumps({
        "ok": True,
        "message": f"User {user_id}: no active anchor loaded. Use 'ai-judge anchor create' to set one.",
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_cold_start(args: argparse.Namespace) -> int:
    """Cold start stage check."""
    from core.cold_start import (
        ScaffoldProfile,
        ColdStartStage,
        get_stage_message,
    )

    user_id = getattr(args, "user_id", "default")
    action = getattr(args, "action", "status")

    # In production, load profile from storage
    profile = ScaffoldProfile(
        user_id=user_id,
        stage=ColdStartStage.OBSERVING,
        session_count=2,
    )

    msg = get_stage_message(profile)
    print(json.dumps({
        "user_id": user_id,
        "stage": profile.stage.value,
        "session_count": profile.session_count,
        "data_confidence": profile.data_confidence,
        "message": msg,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_mirror(args: argparse.Namespace) -> int:
    """Generate thinking mirror report."""
    from core.mirror import extract_fingerprint_v0, generate_growth_narrative_prompt

    user_id = args.user_id

    # Placeholder sessions
    sessions = [
        {"output": "我认为这个问题的核心在于激励机制的错配..."},
        {"output": "从另一个角度看，也许问题不在于技术，而在于..."},
    ]

    fingerprint = extract_fingerprint_v0(user_id, sessions)
    prompt = generate_growth_narrative_prompt(user_id, fingerprint, None, sessions)

    print(json.dumps({
        "user_id": user_id,
        "fingerprint": fingerprint.to_dict(),
        "growth_narrative_prompt_preview": prompt[:300] + "...",
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    """Thinking log management."""
    from core.thinking_log import (
        ThinkingFragment,
        FragmentStore,
        distill_questions,
    )

    user_id = getattr(args, "user_id", "default")
    action = getattr(args, "log_action", "distill")

    store = FragmentStore()  # In production, backed by SQLite

    if action == "add":
        content = args.content
        source = getattr(args, "source", "cli")
        fragment = ThinkingFragment(
            fragment_id="",
            user_id=user_id,
            content=content,
            source=source,
        )
        store.add(fragment)
        print(json.dumps({
            "ok": True,
            "fragment_id": fragment.fragment_id,
            "word_count": fragment.word_count,
            "message": f"碎片已记录（{fragment.word_count} 字）。",
        }, ensure_ascii=False, indent=2))
        return 0

    # distill
    fragments = store.get_recent(user_id)
    if len(fragments) < 5:
        print(json.dumps({
            "ok": True,
            "message": f"需要至少 5 条碎片才能提炼问题（当前 {len(fragments)} 条）。",
        }, ensure_ascii=False, indent=2))
        return 0

    questions = distill_questions(fragments)
    print(json.dumps({
        "ok": True,
        "fragment_count": len(fragments),
        "distilled_questions": [
            {"tension": q.core_tension, "confidence": q.confidence, "inquiry": q.suggested_inquiry}
            for q in questions
        ],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_achievement(args: argparse.Namespace) -> int:
    """Show achievement snapshot."""
    from core.achievement import (
        AchievementSnapshot,
        compute_streak,
        generate_weekly_report_data,
    )

    user_id = args.user_id

    # Placeholder data
    snapshot = AchievementSnapshot(
        user_id=user_id,
        streak_days=7,
        overturned_count=3,
        unique_ideas_count=5,
    )

    streak = compute_streak([time.time() - i * 86400 for i in range(7)])
    report = generate_weekly_report_data(snapshot, streak, [])

    print(json.dumps({
        "user_id": user_id,
        "snapshot": snapshot.to_dict(),
        "weekly_report": report,
    }, ensure_ascii=False, indent=2))
    return 0


# ── V3 Command Handlers ──

def cmd_neuro_profile(args: argparse.Namespace) -> int:
    """Run neuro-cognitive profiling on text."""
    from core.neuro_profiler import compute_neuro_profile

    if args.demo:
        texts = [
            # Sample 1: "聊起来聪明" — conceptually fluent but self-closed
            (
                "strategy",
                "我认为这个方案的核心在于底层逻辑的重构。"
                "我一直觉得AI时代的核心竞争力就是认知架构的升级。"
                "毫无疑问，我们需要通过多模型协同构建可信智能决策闭环。"
                "这肯定是未来方向，不用讨论。"
            ),
            # Sample 2: "真正聪明" — grounded, handles ambiguity
            (
                "strategy",
                "我让9个模型分别答同一个价格验证问题，结果4个模型把截图当官方证据。"
                "我后来把prompt改成'无最终支付页不得计入真值'，错误率才下降。"
                "但我不确定这个方案在海外市场是否适用，需要实际测试。"
                "如果反过来想，也许问题不在模型，而在我们对'证据'的定义本身需要区分场景。"
            ),
        ]

        for i, (ctx, text) in enumerate(texts, 1):
            profile = compute_neuro_profile(text, task_context=ctx)
            print(f"\n--- Sample {i} ---")
            print(f"Text: {text[:80]}...")
            print(f"  smart_sounding: {profile['smart_sounding_score']:.3f}")
            print(f"  judgment_quality: {profile['judgment_quality_score']:.3f}")
            print(f"  gap: {profile['smart_vs_judgment_gap']:.3f} ({profile['gap_label']})")
            print(f"  risks: {profile['cognitive_risk_flags']}")
            sig = profile['signals']
            print(f"  self_closure: {sig['self_closure']['label']} ({sig['self_closure']['self_closure_score']:.3f})")
            print(f"  ambiguity: {sig['ambiguity_flexibility']['label']} ({sig['ambiguity_flexibility']['ambiguity_flexibility_score']:.3f})")
            print(f"  grounding: {sig['experience_grounding']['label']} ({sig['experience_grounding']['experience_grounding_score']:.3f})")
        return 0

    text = ""
    if args.text:
        text = args.text
    elif args.text_file:
        from pathlib import Path
        text = Path(args.text_file).read_text(encoding="utf-8")
    else:
        print("Usage: ai-judge neuro-profile --text '...' | --text-file <path> | --demo", file=sys.stderr)
        return 2

    profile = compute_neuro_profile(text)
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


def cmd_hard_truth(args: argparse.Namespace) -> int:
    """Run hard truth mode simulation."""
    from core.neuro_profiler import compute_neuro_profile
    from core.hard_truth import determine_mode, generate_hard_truth_output

    if not args.demo:
        print("Usage: ai-judge hard-truth --demo", file=sys.stderr)
        return 2

    # Simulate a "smart-sounding but shallow" text
    text = (
        "我认为这个方案的核心在于底层逻辑的重构。"
        "我一直觉得AI时代的核心竞争力就是认知架构的升级。"
        "毫无疑问，我们需要通过多模型协同构建可信智能决策闭环。"
        "这肯定是未来方向，不用讨论。"
        "本质上就是要打造一个全链路的智能系统。"
    )

    profile = compute_neuro_profile(text, task_context="strategy")
    mode = determine_mode(profile)

    print(f"Mode: L{mode['mode_level']} {mode['mode_name']}")
    print(f"Trigger: {mode['trigger_reason']}")
    print()

    if mode["hard_truth_active"]:
        output = generate_hard_truth_output(profile, text)
        print(output)
    else:
        print("No hard truth intervention needed.")

    return 0


def cmd_v3_pipeline(args: argparse.Namespace) -> int:
    """Run full V3 pipeline demo."""
    from core.neuro_profiler import compute_neuro_profile
    from core.determinism import run_full_v3_pipeline
    from core.hard_truth import generate_hard_truth_output, determine_mode

    if not args.demo:
        print("Usage: ai-judge v3-pipeline --demo", file=sys.stderr)
        return 2

    # Simulate the "smart-sounding" text through full V3 pipeline
    text = (
        "我认为这个方案的核心在于底层逻辑的重构。"
        "我一直觉得AI时代的核心竞争力就是认知架构的升级。"
        "毫无疑问，我们需要通过多模型协同构建可信智能决策闭环。"
    )

    # Step 1: Neuro profile
    profile = compute_neuro_profile(text, task_context="strategy")

    # Step 2: Simulated judge samples
    samples = [
        {"score": 8.2, "tier": "credible"},
        {"score": 8.2, "tier": "credible"},
        {"score": 8.2, "tier": "credible"},
    ]

    # Step 3: Full V3 pipeline
    model_scores = {"GPT": 8.2, "Claude": 7.8, "DeepSeek": 8.5}
    v3_result = run_full_v3_pipeline(
        judge_samples=samples,
        model_scores=model_scores,
        human_reason="评分基本准确，但我的论证确实存在自我视角闭环的问题。",
        neuro_profile=profile,
    )

    print(json.dumps({
        "pipeline": "V3 Full",
        "confidence": v3_result.get("confidence_light", {}).get("label", "N/A"),
        "dual_scores": v3_result.get("dual_scores", {}),
        "risks": v3_result.get("cognitive_risk_flags", []),
        "hard_truth": v3_result.get("hard_truth_mode", {}),
    }, ensure_ascii=False, indent=2))

    # If hard truth active, print the output
    if v3_result.get("hard_truth_mode", {}).get("active"):
        print("\n" + generate_hard_truth_output(profile, text))

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
