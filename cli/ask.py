#!/usr/bin/env python3
"""AI Judge ask — one-command jury pipeline.

Usage:
  ai-judge ask "Is this pricing competitive?"
  ai-judge ask "Compare Tesla vs BYD 2025 financial risk" --seats Gemini DeepSeek Grok
  ai-judge ask "..." --output /path/to/run  --format markdown

The ask command automates the full pipeline:
  1. Render jury prompts for each selected seat
  2. Output prompts (for user to send to LLMs) or accept pre-collected responses
  3. Score via core.scoring_v2.score_jury_v2
  4. Generate verdict summary

Without --responses, it prints the jury dispatch prompts.
With --responses <file.json>, it scores the collected responses and produces a verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

# Project root (ai-judge-skill/) — add to path so imports work from any cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.seat_personas import SEAT_PERSONAS, list_seats, render_jury_prompt


# ─── Render phase ────────────────────────────────────────

def render_jury_prompts(question: str, seats: list[str] | None = None) -> dict[str, Any]:
    """Generate jury dispatch prompts for each seat.

    Args:
        question: The question to ask the jury.
        seats: List of seat names (case-insensitive). None = all 9 seats.

    Returns:
        {seats: [...], prompts: {seat_name: prompt_text}, question: str}
    """
    if seats is None:
        seat_names = list(SEAT_PERSONAS.keys())
    else:
        seat_names = [s.lower() for s in seats]
        # Validate
        unknown = [s for s in seat_names if s not in SEAT_PERSONAS]
        if unknown:
            print(f"Warning: unknown seats: {unknown}. Available: {list(SEAT_PERSONAS.keys())}")

    prompts = {}
    for name in seat_names:
        if name in SEAT_PERSONAS:
            prompt = render_jury_prompt(name, question)
            prompts[name] = prompt or f"# {SEAT_PERSONAS[name]['name']} ({SEAT_PERSONAS[name]['mbti']})\n\n{question}"

    return {
        "question": question,
        "seats": seat_names,
        "prompts": prompts,
    }


# ─── Collect phase ────────────────────────────────────────

def load_responses(path: str) -> dict[str, Any]:
    """Load pre-collected jury responses from a JSON file.

    Expected format:
    {
      "question": "...",
      "responses": {
        "gemini": {
          "claims": [
            {"claim": "...", "source_authority": 0.8, "evidence_strength": 0.7, ...}
          ]
        },
        ...
      }
    }
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def collect_to_claims(response_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert collected responses into the claims format expected by score_jury_v2."""
    claims = []
    for seat_name, resp in response_data.get("responses", {}).items():
        for claim in resp.get("claims", []):
            claim["_seat"] = seat_name
            claims.append(claim)
    return claims


# ─── Verdict phase ────────────────────────────────────────

def produce_verdict(claims: list[dict[str, Any]], question: str) -> dict[str, Any]:
    """Score the claims and produce a verdict."""
    from core.scoring_v2 import score_jury_v2

    result = score_jury_v2(claims)

    # Build summary
    summary_parts = []
    verdict = result.get("final_verdict", "conditional")
    credible = result.get("tier_counts", {}).get("credible", 0)
    total = len(claims)
    avg_score = result.get("aggregate_mean", 0)

    summary_parts.append(f"## AI Judge Verdict: {verdict.upper()}")
    summary_parts.append(f"\n**Question**: {question}")
    summary_parts.append(f"\n**Claims scored**: {total} | Credible: {credible} | Aggregate mean: {avg_score:.3f}")

    if result.get("abstain_count", 0) > 0:
        summary_parts.append(f" | Abstains: {result['abstain_count']}")

    summary_parts.append(f"\n\n**Recommendation**: {_verdict_advice(verdict, avg_score)}")

    return {
        "question": question,
        "verdict": verdict,
        "summary": "".join(summary_parts),
        "scores": result,
        "claims": claims,
    }


def _verdict_advice(verdict: str, avg_score: float) -> str:
    """Human-readable verdict advice."""
    if verdict == "credible" and avg_score >= 0.7:
        return "High-confidence consensus. The jury finds the claims well-supported. Proceed with standard review."
    elif verdict == "credible":
        return "Moderate confidence. Claims passed basic gates but have room for stronger evidence."
    elif verdict == "conditional":
        return "Conditional acceptance. Some claims need additional verification before action."
    elif verdict == "rejected":
        return "Claims rejected or insufficient evidence. Do not rely on these claims without independent verification."
    else:
        return "Inconclusive. Consider rephrasing the question or adding more seats to break the deadlock."


# ─── Output formatters ────────────────────────────────────

def format_prompts_for_display(jury_data: dict[str, Any]) -> str:
    """Format rendered prompts for terminal display."""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"AI Judge Jury Dispatch — {len(jury_data['seats'])} seats")
    lines.append(f"{'='*60}")
    lines.append(f"\nQuestion: {jury_data['question']}\n")

    for seat_name in jury_data["seats"]:
        persona = SEAT_PERSONAS.get(seat_name, {})
        lines.append(f"{'─'*60}")
        lines.append(f"Seat: {persona.get('name', seat_name)} ({persona.get('mbti', '?')})")
        lines.append(f"Risk: {persona.get('risk_preference', '?')} | Style: {persona.get('strength', '?')}")
        lines.append(f"{'─'*60}")
        lines.append(jury_data["prompts"].get(seat_name, "(no prompt)"))
        lines.append("")

    lines.append(f"{'='*60}")
    lines.append("Send each prompt to the corresponding model.")
    lines.append("Collect responses into a JSON file, then run:")
    lines.append("  ai-judge ask --responses collected.json")
    lines.append(f"{'='*60}\n")

    return "\n".join(lines)


def format_verdict_markdown(verdict_data: dict[str, Any]) -> str:
    """Format verdict as Markdown report."""
    lines = [verdict_data["summary"], ""]

    # Per-claim breakdown
    lines.append("### Claim Breakdown\n")
    lines.append("| # | Seat | Claim | Score | Tier |")
    lines.append("|---|------|-------|-------|------|")

    for i, claim in enumerate(verdict_data.get("claims", [])[:20], 1):
        text = claim.get("claim", "")[:60].replace("|", "\\|")
        seat = claim.get("_seat", "?")
        score = claim.get("_score", "N/A")
        tier = claim.get("_tier", "?")
        if isinstance(score, float):
            score = f"{score:.3f}"
        lines.append(f"| {i} | {seat} | {text} | {score} | {tier} |")

    lines.append(f"\n*Total: {len(verdict_data.get('claims', []))} claims*\n")

    # Evidence trace summary
    lines.append("### Evidence Trace")
    lines.append("Run `ai-judge trace --demo` for full cross-model contamination report.\n")

    return "\n".join(lines)


# ─── Main command ─────────────────────────────────────────

def cmd_ask(args: argparse.Namespace) -> int:
    """Run the ask command."""
    question = args.question

    # Resolve mode configuration
    mode = getattr(args, 'mode', 'flash') or 'flash'
    from core.modes import resolve_mode, JURY_MODES
    config = resolve_mode(mode)

    # Parse seats (mode default or explicit override)
    seats = None
    if args.seats:
        seats = [s.strip().lower() for s in args.seats.split(",")]
    else:
        seats = config["seats"]

    mode_emoji = JURY_MODES[mode]["emoji"]
    mode_name = JURY_MODES[mode]["name"]
    print(f"\n{mode_emoji} Mode: {mode_name} ({len(seats)} seats)")
    print(f"   {' '.join(s.upper() for s in seats)}\n")

    # v3.4 default path: run a complete local automatic verdict.
    if not args.responses and not getattr(args, "render_prompts", False):
        from core.auto_jury import format_verdict_markdown, run_auto_jury

        run_id = uuid.uuid4().hex[:12]
        verdict_data = run_auto_jury(question=question, mode=mode, seats=seats, run_id=run_id)

        out_dir = Path(args.output) if args.output else Path("ai-judge-run") / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / "verdict.md"
        json_path = out_dir / "verdict.json"
        md_path.write_text(format_verdict_markdown(verdict_data), encoding="utf-8")
        json_path.write_text(json.dumps(verdict_data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        print(verdict_data["one_liner"])
        print(f"Confidence: {verdict_data['confidence']}%")
        print(f"Verdict: {md_path}")
        print(f"Scores:  {json_path}")

        if hasattr(args, "notify") and args.notify:
            from bridges.notification_gateway import generate_secure_view_url, notify_verdict_ready
            notify_verdict_ready(
                run_id=run_id,
                mode=mode,
                verdict=verdict_data.get("verdict", "conditional"),
                score=verdict_data.get("average_score", 0),
                summary=verdict_data.get("one_liner", ""),
                view_url=generate_secure_view_url(run_id),
                channels=[args.notify],
            )
        return 0

    # Legacy path: render prompts for manual external model collection.
    if not args.responses:
        jury_data = render_jury_prompts(question, seats)
        print(format_prompts_for_display(jury_data))

        # Save prompts to file if --output specified
        if args.output:
            out_dir = Path(args.output)
            out_dir.mkdir(parents=True, exist_ok=True)
            prompts_file = out_dir / "jury_prompts.json"
            prompts_file.write_text(json.dumps(jury_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Prompts saved to: {prompts_file}")

        return 0

    # Path: score collected responses
    response_data = load_responses(args.responses)
    claims = collect_to_claims(response_data)

    if not claims:
        print("Error: No claims found in response file.", file=sys.stderr)
        return 1

    verdict_data = produce_verdict(claims, question)

    # Output
    out_dir = Path(args.output) if args.output else Path("ai-judge-run")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write verdict.md
    md_path = out_dir / "verdict.md"
    md_path.write_text(format_verdict_markdown(verdict_data), encoding="utf-8")
    print(f"Verdict: {md_path}")

    # Write verdict.json
    json_path = out_dir / "verdict.json"
    json_path.write_text(json.dumps(verdict_data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Scores:  {json_path}")

    # Print summary to stdout
    print(f"\n{verdict_data['summary']}")

    # Notification
    if hasattr(args, 'notify') and args.notify:
        from bridges.notification_gateway import notify_verdict_ready
        notify_verdict_ready(
            run_id=verdict_data.get("run_id", "unknown"),
            mode=mode,
            verdict=verdict_data.get("verdict", "unknown"),
            score=verdict_data.get("aggregate_mean", verdict_data.get("average_score", 0)),
            channels=[args.notify],
        )

    return 0


# ─── CLI registration (called from cli/main.py) ───────────

def register_ask_parser(subparsers) -> None:
    """Register the 'ask' subcommand with argparse subparsers."""
    p = subparsers.add_parser("ask", help="One-command jury pipeline (render → score → verdict)")
    p.add_argument("question", help="The question for the jury")
    p.add_argument("--mode", "-m", choices=["flash", "standard", "strategic"],
                   default="flash", help="Jury mode: flash (3 seats/30s), standard (5 seats/2min), strategic (9 seats/5-10min)")
    p.add_argument("--seats", help="Comma-separated seat names (overrides mode default)")
    p.add_argument("--output", "-o", help="Output directory for verdict files")
    p.add_argument("--responses", "-r", help="Path to pre-collected responses JSON (skip prompt phase)")
    p.add_argument("--render-prompts", action="store_true",
                   help="Legacy mode: only render prompts for manual model collection")
    p.add_argument("--notify", choices=["console", "desktop", "email", "webhook", "feishu", "wecom"],
                   help="Notification channel for verdict completion")
    p.add_argument("--format", choices=["markdown", "text"], default="markdown", help="Output format")
    p.set_defaults(func=cmd_ask)


# ─── Standalone test ──────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Judge v3.4 ask")
    parser.add_argument("question", help="The question for the jury")
    parser.add_argument("--mode", "-m", choices=["flash", "standard", "strategic"], default="flash")
    parser.add_argument("--seats", help="Comma-separated seat names (overrides mode default)")
    parser.add_argument("--output", "-o", help="Output directory for verdict files")
    parser.add_argument("--responses", "-r", help="Path to pre-collected responses JSON")
    parser.add_argument("--render-prompts", action="store_true", help="Only render manual dispatch prompts")
    parser.add_argument("--notify", choices=["console", "desktop", "email", "webhook", "feishu", "wecom"])
    parser.add_argument("--format", choices=["markdown", "text"], default="markdown")
    sys.exit(cmd_ask(parser.parse_args()))
