#!/usr/bin/env python3
"""AI Judge — Unified CLI entry point v2.1.0.

Usage:
    ai-judge license status
    ai-judge jury --question "Is this pricing competitive?"
    ai-judge collect --run latest
    ai-judge verdict --run latest
    ai-judge reflect --date 2026-05-09
    ai-judge list
    ai-judge score-v2 --demo          # Phase 1 scoring demo
    ai-judge score-v2 --claims-file path/to/claim-ledger.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
