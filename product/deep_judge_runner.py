"""Deep Judge reasoning pipeline.

Ensures that deep_judge runs MUST consume real LLM / search-agent / seat_outputs
before returning success. Without at least one substantive reasoning source, the
run MUST fail with deep_judge_no_substantive_reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeepJudgeMetadata:
    """Runtime metadata for a single deep_judge execution."""

    llm_calls: int = 0
    search_agent_calls: int = 0
    seat_outputs_consumed: int = 0
    substantive_sources: list[str] = field(default_factory=list)
    degraded: bool = False


@dataclass
class DeepJudgeResult:
    """Result of a deep_judge reasoning pipeline run."""

    ok: bool
    reason: str = ""
    metadata: DeepJudgeMetadata = field(default_factory=DeepJudgeMetadata)
    search_agent_output: dict[str, Any] | None = None
    legal_analysis: dict[str, Any] | None = None
    seat_outputs: list[dict[str, Any]] = field(default_factory=list)


def _has_content(obj: Any, min_len: int = 50) -> bool:
    """Check that an object has substantive text content."""
    if not obj or not isinstance(obj, dict):
        return False
    text = obj.get("result") or obj.get("markdown") or obj.get("analysis") or obj.get("body") or ""
    return len(str(text).strip()) >= min_len


def _count_substantive_seats(outputs: list[dict[str, Any]]) -> int:
    """Count seats that produced non-empty output."""
    if not outputs:
        return 0
    count = 0
    for o in outputs:
        if not isinstance(o, dict):
            continue
        text = o.get("answer") or o.get("text") or o.get("summary") or ""
        if str(text).strip():
            count += 1
    return count


def run_deep_judge(
    *,
    question: str,
    search_agent_output: dict[str, Any] | None = None,
    legal_analysis: dict[str, Any] | None = None,
    seat_outputs: list[dict[str, Any]] | None = None,
) -> DeepJudgeResult:
    """Execute the deep_judge reasoning gate.

    Returns DeepJudgeResult (ok=True) if at least one substantive source exists.
    Otherwise returns ok=False with reason="deep_judge_no_substantive_reasoning".
    """
    metadata = DeepJudgeMetadata()
    has_source = False

    # ── 1. Search-agent ──
    if _has_content(search_agent_output):
        metadata.search_agent_calls = 1
        metadata.substantive_sources.append("search-agent")
        has_source = True

    # ── 2. Seat outputs ──
    seat_count = _count_substantive_seats(seat_outputs or [])
    if seat_count > 0:
        metadata.seat_outputs_consumed = seat_count
        metadata.substantive_sources.append("seat_outputs")
        metadata.llm_calls += seat_count  # each seat implies an LLM call
        has_source = True

    # ── 3. Legal analysis ──
    if _has_content(legal_analysis):
        metadata.substantive_sources.append("legal_analysis")
        has_source = True

    metadata.degraded = not has_source

    if not has_source:
        return DeepJudgeResult(
            ok=False,
            reason="deep_judge_no_substantive_reasoning",
            metadata=metadata,
        )

    return DeepJudgeResult(
        ok=True,
        metadata=metadata,
        search_agent_output=search_agent_output,
        legal_analysis=legal_analysis,
        seat_outputs=seat_outputs or [],
    )


def build_deep_judge_metadata_block(result: DeepJudgeResult) -> dict[str, Any]:
    """Serialize DeepJudgeMetadata into the summary.json-compatible block."""
    m = result.metadata
    return {
        "deep_judge": {
            "llm_calls": m.llm_calls,
            "search_agent_calls": m.search_agent_calls,
            "seat_outputs_consumed": m.seat_outputs_consumed,
            "substantive_sources": m.substantive_sources,
            "degraded": m.degraded,
        }
    }