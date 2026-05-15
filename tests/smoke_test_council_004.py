#!/usr/bin/env python3
"""AI Judge COUNCIL-004 smoke test.

Checks fixed seat personas and lightweight evidence trace behavior:
  1. All 9 persona seats are present
  2. Seat detail and prompt rendering work
  3. Single-claim L1/L2/L3 trace levels are classified
  4. Shared source contamination is detected across seats
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from core.evidence_trace import detect_shared_sources, trace_claim
from core.seat_personas import get_persona, list_seats, render_jury_prompt


def main() -> None:
    seats = list_seats()
    assert len(seats) == 9
    assert {seat["name"] for seat in seats} >= {"Gemini", "ChatGPT", "DeepSeek", "Grok"}

    grok = get_persona("grok")
    assert grok is not None
    assert grok["mbti"] == "ENTP"
    assert "jury_prompt_injection" in grok

    prompt = render_jury_prompt("grok", "Should we trust this market forecast?")
    assert prompt is not None
    assert "[SYSTEM]" in prompt
    assert "[QUESTION] Should we trust this market forecast?" in prompt

    l1 = trace_claim("See https://example.com/report for the market forecast.", "l1")
    assert l1["trace_level"] == "L1"
    assert l1["explicit_refs"] == 1

    l2 = trace_claim("According to the 2025 IMF report, global debt reached $300T.", "l2")
    assert l2["trace_level"] == "L2"
    assert l2["implied_refs"] >= 1

    l3 = trace_claim("This market will probably compound faster than expected.", "l3")
    assert l3["trace_level"] == "L3"

    contamination = detect_shared_sources({
        "Gemini": ["According to the 2025 IMF report, global debt reached $300T."],
        "ChatGPT": ["According to the 2025 IMF report, debt consolidation is urgent."],
        "DeepSeek": ["According to the 2025 IMF report, debt-to-GDP context is missing."],
    })
    assert contamination["contaminated_sources"] >= 1
    assert contamination["contamination_details"][0]["seat_count"] == 3

    print("AI Judge COUNCIL-004 smoke test passed")


if __name__ == "__main__":
    main()
