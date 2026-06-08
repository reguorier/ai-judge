"""
PATCH: P2 — Answer decontamination utilities
Apply to: bridges/web_seat_bridge.py (add as import + call)
Location: /Users/audimacmini/Documents/ai-judge-skill/bridges/web_seat_bridge.py

This module provides functions to clean transcript pollution and
ensure only the latest assistant response is captured.

=== USAGE ===

In chrome_cdp_bridge.py or chrome_fixed_tab_bridge.py, after extracting
the response text, call:

    from core.answer_decontamination import clean_transcript_response
    cleaned = clean_transcript_response(raw_response, seat=seat_id, prompt_sent=prompt_text)
"""

from __future__ import annotations

import re
from typing import Any


def clean_transcript_response(
    raw_response: str,
    seat: str = "",
    prompt_sent: str = "",
    min_response_chars: int = 50,
) -> dict[str, Any]:
    """Clean a raw transcript response to remove pollution.

    P2 FIX: Handles transcript_pollution by:
    1. Extracting only the LAST assistant message (not historical)
    2. Removing the prompt echo if it appears in the response
    3. Detecting placeholder/template responses

    Returns:
        {
            "cleaned": str,           # Cleaned response text
            "is_polluted": bool,      # Whether pollution was detected
            "pollution_type": str,    # Type of pollution detected
            "original_length": int,   # Original response length
            "cleaned_length": int,    # Cleaned response length
        }
    """
    original_length = len(raw_response)
    cleaned = raw_response.strip()

    # Step 1: Remove prompt echo
    if prompt_sent and len(prompt_sent) > 20:
        # Check if the prompt appears verbatim in the response
        prompt_first_100 = prompt_sent[:100].strip()
        if prompt_first_100 and prompt_first_100 in cleaned:
            # Find the last occurrence of the prompt and take everything after
            last_idx = cleaned.rfind(prompt_first_100)
            if last_idx >= 0:
                cleaned = cleaned[last_idx + len(prompt_first_100):].strip()

    # Step 2: Detect and remove multiple conversation turns
    # Look for patterns like "Human:" / "Assistant:" / "User:" / "AI:" that indicate
    # the response includes historical conversation
    turn_markers = [
        r"\n(?:Human|User|用户|提问者)[:：]",
        r"\n(?:Assistant|AI|回答|回复|模型)[:：]",
        r"\n\[AIJUDGE_",
    ]
    turn_positions = []
    for pattern in turn_markers:
        for match in re.finditer(pattern, cleaned):
            turn_positions.append(match.start())

    if turn_positions:
        # Take only the content after the last "Assistant/AI" marker
        # Find the last assistant-like marker
        assistant_markers = [
            r"\n(?:Assistant|AI|回答|回复|模型)[:：]",
            r"\n\[AIJUDGE_",
        ]
        last_assistant_pos = 0
        for pattern in assistant_markers:
            for match in re.finditer(pattern, cleaned):
                last_assistant_pos = max(last_assistant_pos, match.end())
        if last_assistant_pos > 0:
            cleaned = cleaned[last_assistant_pos:].strip()

    # Step 3: Detect placeholder responses
    pollution_type = "none"
    if len(cleaned) < min_response_chars:
        pollution_type = "too_short"
    elif re.match(r"^(好的|OK|ok|没问题|明白了|收到)[.。！!，,\s]*$", cleaned):
        pollution_type = "acknowledgment_only"
    elif cleaned.startswith("Loading") or cleaned.startswith("加载中"):
        pollution_type = "loading_placeholder"
    elif "[object Object]" in cleaned:
        pollution_type = "js_error"

    return {
        "cleaned": cleaned,
        "is_polluted": pollution_type != "none" or len(cleaned) < original_length * 0.5,
        "pollution_type": pollution_type,
        "original_length": original_length,
        "cleaned_length": len(cleaned),
    }


def extract_latest_assistant_message(text: str) -> str | None:
    """Extract only the latest assistant message from a multi-turn transcript.

    Looks for the last assistant turn marker and returns everything after it
    until the next turn marker or end of text.
    """
    # Common assistant markers across different platforms
    markers = [
        # ChatGPT-style
        r"data-message-author-role=['\"]assistant['\"]",
        # Generic
        r"\n(?:Assistant|AI|回复|回答)[:：]\s*",
        # AI Judge resonance markers
        r"\n\[AIJUDGE_RESONANCE_FOLLOWUP\]",
    ]

    last_pos = -1
    for pattern in markers:
        for match in re.finditer(pattern, text):
            last_pos = max(last_pos, match.end())

    if last_pos < 0:
        return text if text.strip() else None

    remaining = text[last_pos:].strip()

    # Trim at next user turn if present
    next_user = re.search(r"\n(?:Human|User|用户|提问者)[:：]", remaining)
    if next_user:
        remaining = remaining[:next_user.start()].strip()

    return remaining if remaining else None
