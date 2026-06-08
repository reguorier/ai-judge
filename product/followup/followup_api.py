"""Function API for creating follow-up notes with reasoning-source gating.

P1 fix: if no LLM / search-agent / report_analysis reasoning source exists,
follow-up MUST return status=not_generated, not pretend to generate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from product.followup.followup_reporter import write_followup_note


def _has_reasoning_source(run_dir: Path) -> bool:
    """Check if the run has any substantive reasoning source available.

    Checks for: seat outputs, search agent output, LLM analysis in artifacts.
    """
    # Check for seat outputs / answers
    seat_matrix_path = run_dir / "seat_matrix.json"
    if seat_matrix_path.exists():
        import json
        try:
            sm = json.loads(seat_matrix_path.read_text(encoding="utf-8"))
            seats = sm.get("seats", [])
            for s in seats:
                if s.get("status") in {"valid", "completed", "answered", "success"}:
                    answer = (s.get("answer") or s.get("text") or s.get("summary") or "").strip()
                    if answer:
                        return True
        except Exception:
            pass

    # Check for evidence packet with external sources
    evidence_path = run_dir / "evidence_packet.json"
    if evidence_path.exists():
        import json
        try:
            ep = json.loads(evidence_path.read_text(encoding="utf-8"))
            items = ep.get("evidence_items", [])
            for item in items:
                if item.get("type") in {"external_search", "llm_output", "search_agent_output"}:
                    return True
        except Exception:
            pass

    # Check for final report with substantive body (not meta template)
    report_path = run_dir / "final_report.md"
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        # If report body is non-trivial and not pure meta, count as reasoning source
        if len(text) > 2000 and "AI Judge 产品价值" not in text[:500]:
            return True

    return False


def create_followup(run_dir: Path, prompt: str) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("follow-up prompt is required")

    has_source = _has_reasoning_source(run_dir)

    if not has_source:
        return {
            "status": "not_generated",
            "reason": "followup_reasoning_unavailable",
            "message": "当前 run 没有实质性推理来源（LLM / search-agent / seat_outputs），无法生成追问。",
        }

    return write_followup_note(run_dir, prompt.strip())
