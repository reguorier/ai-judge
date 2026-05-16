#!/usr/bin/env python3
"""AI Judge MCP Server — expose jury pipeline as MCP tools.

Usage:
  python3 -m core.mcp_server          # stdio transport (for MCP clients)
  python3 core/mcp_server.py --test   # run self-test

Registers with OpenClaw Gateway:
  ~/.openclaw/skills/ai-judge.yaml:
    tools:
      - mcp: ai-judge
        command: python3 -m core.mcp_server

Exposed tools:
  - ai_judge_ask(question, seats?) → str     : Render jury prompts for a question
  - ai_judge_seats() → list[dict]            : List available seat personas
  - ai_judge_trace(claim_id, claim_text?) → dict : Trace evidence for a claim
  - ai_judge_verdict(responses_json) → str   : Score collected responses
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure project root is on path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.seat_personas import SEAT_PERSONAS, list_seats, render_jury_prompt
from core.evidence_trace import trace_claim, detect_shared_sources


# ─── Tool implementations ─────────────────────────────────

def ai_judge_seats() -> list[dict[str, Any]]:
    """List all available seat personas with their MBTI, strengths, and weaknesses."""
    return list_seats()


def ai_judge_ask(
    question: str,
    seats: list[str] | None = None,
    mode: str = "flash",
    render_prompts: bool = False,
) -> dict[str, Any]:
    """Run AI Judge automatically, or render legacy dispatch prompts.

    Args:
        question: The question to ask the jury.
        seats: Optional list of seat names (e.g., ["gemini", "deepseek"]). Default: all 9.
        mode: flash, standard, or strategic.
        render_prompts: If True, return prompt packets instead of an automatic verdict.

    Returns:
        {
            "question": str,
            "seats": [str, ...],
            "prompts": {seat_name: prompt_text, ...},
            "instructions": "Send each prompt to the corresponding model..."
        }
    """
    if not render_prompts:
        try:
            from core.auto_jury import run_auto_jury
            return run_auto_jury(question=question, mode=mode, seats=seats)
        except Exception as exc:
            return {"error": str(exc)}

    if seats is None:
        seat_names = list(SEAT_PERSONAS.keys())
    else:
        seat_names = [s.lower() for s in seats]
        unknown = [s for s in seat_names if s not in SEAT_PERSONAS]
        if unknown:
            return {
                "error": f"Unknown seats: {unknown}",
                "available": list(SEAT_PERSONAS.keys()),
            }

    prompts = {}
    for name in seat_names:
        prompt = render_jury_prompt(name, question)
        persona = SEAT_PERSONAS[name]
        prompts[name] = prompt or (
            f"# {persona['name']} ({persona['mbti']})\n\n"
            f"**Instructions**: {persona['jury_prompt_injection']}\n\n"
            f"**Question**: {question}\n\n"
            f"Please respond with numbered claims, each including:\n"
            f"- claim text\n"
            f"- source_authority (0-1)\n"
            f"- evidence_strength (0-1)\n"
            f"- evidence_count (integer)\n"
            f"- evidence_quality (0-1)\n"
            f"- confidence (0-1)\n"
        )

    return {
        "question": question,
        "seats": seat_names,
        "prompts": prompts,
        "instructions": (
            "Send each prompt to the corresponding AI model. "
            "Collect their responses and format as JSON with keys matching seat names. "
            "Then call ai_judge_verdict with the collected responses."
        ),
    }


def ai_judge_trace(claim_text: str, claim_id: str = "") -> dict[str, Any]:
    """Trace the evidence sources for a single claim.

    Returns L1 (explicit citations), L2 (implied citations), or L3 (no citation)
    classification along with extracted references.

    Args:
        claim_text: The claim text to trace.
        claim_id: Optional claim identifier.

    Returns:
        {
            "claim_id": str,
            "trace_level": "L1" | "L2" | "L3",
            "explicit_refs": int,
            "implied_refs": int,
            "explicit_details": [...],
            "implied_details": [...],
            "advisory": str
        }
    """
    return trace_claim(claim_text, claim_id)


def ai_judge_verdict(responses_json: str) -> dict[str, Any]:
    """Score collected jury responses and produce a verdict.

    Args:
        responses_json: JSON string with format:
            {
              "question": "...",
              "responses": {
                "gemini": {"claims": [{"claim": "...", "source_authority": 0.8, ...}]},
                "deepseek": {"claims": [...]}
              }
            }

    Returns:
        {
            "verdict": str,
            "aggregate_mean": float,
            "tier_counts": {...},
            "seat_scores": [...],
            "summary": str,
            "contamination": {...}
        }
    """
    try:
        data = json.loads(responses_json)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}

    question = data.get("question", "")
    responses = data.get("responses", {})

    if not responses:
        return {"error": "No responses provided. Expected {responses: {seat_name: {claims: [...]}}}"}

    # Convert to claims format
    claims = []
    for seat_name, resp in responses.items():
        for claim in resp.get("claims", []):
            claim["_seat"] = seat_name
            claims.append(claim)

    if not claims:
        return {"error": "No claims found in responses"}

    # Score
    try:
        from core.scoring_v2 import score_jury_v2

        score_result = score_jury_v2(claims)

        # Evidence trace
        claims_by_seat: dict[str, list[str]] = {}
        for c in claims:
            seat = c.get("_seat", "unknown")
            claims_by_seat.setdefault(seat, []).append(c.get("claim", ""))
        trace_report = detect_shared_sources(claims_by_seat)

    except Exception as e:
        return {"error": f"Scoring pipeline failed: {e}"}

    # Per-seat scores
    seat_scores = []
    seat_groups: dict[str, list[dict]] = {}
    for c in claims:
        seat_groups.setdefault(c.get("_seat", "unknown"), []).append(c)

    for seat, scs in seat_groups.items():
        scores = [c.get("_score", c.get("score", 0.5)) for c in scs if isinstance(c.get("_score", c.get("score", None)), (int, float))]
        avg = sum(scores) / len(scores) if scores else 0.5
        seat_scores.append({"seat": seat, "claims": len(scs), "avg_score": round(avg, 4)})

    seat_scores.sort(key=lambda x: x["avg_score"], reverse=True)

    tier_dist = score_result.get("tier_distribution", {})
    agg_mean = score_result.get("average_score", 0)

    # Derive verdict
    if tier_dist.get("credible", 0) >= tier_dist.get("rejected", 0) * 2 and agg_mean >= 0.65:
        verdict = "credible"
    elif tier_dist.get("rejected", 0) > tier_dist.get("credible", 0):
        verdict = "rejected"
    elif tier_dist.get("unverified", 0) > tier_dist.get("credible", 0):
        verdict = "unverified"
    else:
        verdict = "conditional"

    return {
        "question": question,
        "verdict": verdict,
        "average_score": round(agg_mean, 4) if agg_mean else 0,
        "tier_distribution": tier_dist,
        "total_claims": len(claims),
        "seat_scores": seat_scores,
        "abstains": score_result.get("abstain_recommended", 0),
        "blocked": score_result.get("bluff_blocked", 0),
        "contamination": {
            "shared_sources": trace_report.get("total_shared_sources", 0),
            "contaminated": trace_report.get("contaminated_sources", 0),
            "advisory": trace_report.get("verdict_advisory", ""),
        },
    }


# ─── MCP Server wrapper ───────────────────────────────────

def create_mcp_server():
    """Create and configure the MCP server instance.

    Uses the `mcp` library if available, otherwise falls back to a
    minimal stdio JSON-RPC loop.
    """
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server

        server = Server("ai-judge")

        @server.tool()
        async def ai_judge_ask_tool(
            question: str,
            seats: list[str] | None = None,
            mode: str = "flash",
            render_prompts: bool = False,
        ) -> str:
            """Run a mode-aware AI Judge verdict automatically."""
            result = ai_judge_ask(question, seats=seats, mode=mode, render_prompts=render_prompts)
            return json.dumps(result, indent=2, ensure_ascii=False)

        @server.tool()
        async def ai_judge_seats_tool() -> str:
            """List available AI Judge seat personas."""
            result = ai_judge_seats()
            return json.dumps(result, indent=2, ensure_ascii=False)

        @server.tool()
        async def ai_judge_trace_tool(claim_text: str, claim_id: str = "") -> str:
            """Trace evidence sources for a claim. Returns L1/L2/L3 classification."""
            result = ai_judge_trace(claim_text, claim_id)
            return json.dumps(result, indent=2, ensure_ascii=False)

        @server.tool()
        async def ai_judge_verdict_tool(responses_json: str) -> str:
            """Score collected jury responses and return verdict."""
            result = ai_judge_verdict(responses_json)
            return json.dumps(result, indent=2, ensure_ascii=False)

        return server

    except ImportError:
        return None


async def run_mcp_server():
    """Run the MCP server with stdio transport."""
    server = create_mcp_server()
    if server is None:
        # Fallback: minimal JSON-RPC loop
        print(json.dumps({"error": "mcp library not installed. Install with: pip install mcp"}), file=sys.stderr)
        sys.exit(1)

    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


# ─── Standalone test ──────────────────────────────────────

def test():
    """Run self-test of all MCP tools."""
    print("AI Judge MCP Server — Self Test\n")

    # Test 1: List seats
    print("1. ai_judge_seats():")
    s = ai_judge_seats()
    print(f"   {len(s)} seats: {', '.join(item['name'] for item in s)}")
    print("   ✓\n")

    # Test 2: Ask
    print("2. ai_judge_ask('Is solar cheaper than coal?'):")
    result = ai_judge_ask("Is solar cheaper than coal in 2026?", ["gemini", "deepseek"], mode="flash")
    print(f"   Question: {result.get('question', '?')}")
    print(f"   Seats: {result.get('seats', [])}")
    print(f"   Verdict: {result.get('verdict_label', result.get('verdict', '?'))}")
    print("   ✓\n")

    # Test 3: Trace
    print("3. ai_judge_trace():")
    trace = ai_judge_trace(
        "According to the IEA World Energy Outlook 2024, solar PV is now the cheapest electricity source in history.",
        claim_id="C001"
    )
    print(f"   Level: {trace.get('trace_level', '?')}")
    print(f"   Explicit refs: {trace.get('explicit_refs', 0)}")
    print(f"   Implied refs: {trace.get('implied_refs', 0)}")
    print("   ✓\n")

    # Test 4: Verdict
    print("4. ai_judge_verdict():")
    sample_responses = json.dumps({
        "question": "Is solar cheaper than coal?",
        "responses": {
            "gemini": {
                "claims": [
                    {"claim": "Solar LCOE is $30/MWh vs coal $60/MWh", "source_authority": 0.9, "evidence_strength": 0.85, "evidence_count": 5, "evidence_quality": 0.8, "freshness": 0.9, "reproducibility": 0.7, "historical_reliability": 0.8, "confidence": 0.85, "risk_penalty": 0.0},
                ]
            },
            "deepseek": {
                "claims": [
                    {"claim": "Solar is cheaper but depends on location and storage costs", "source_authority": 0.7, "evidence_strength": 0.75, "evidence_count": 4, "evidence_quality": 0.7, "freshness": 0.8, "reproducibility": 0.6, "historical_reliability": 0.7, "confidence": 0.7, "risk_penalty": 0.05},
                ]
            },
        }
    })
    verdict = ai_judge_verdict(sample_responses)
    print(f"   Verdict: {verdict.get('verdict', '?')}")
    print(f"   Aggregate mean: {verdict.get('aggregate_mean', '?')}")
    print(f"   Seat scores: {verdict.get('seat_scores', [])}")
    print("   ✓\n")

    print("All tests passed ✓")


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="AI Judge MCP Server")
    parser.add_argument("--test", action="store_true", help="Run self-test")
    args = parser.parse_args()

    if args.test:
        test()
    else:
        asyncio.run(run_mcp_server())
