"""FDJP LLM response parser with anti-hallucination guards.

Handles:
1. Valid JSON
2. JSON wrapped in Markdown fences
3. Missing fields
4. Missing dimensions
5. Non-numeric confidence
6. Invalid status values
7. Overlong text
8. LLM-fabricated evidence_refs
9. Unsupported evidence ref detection (anti-hallucination)
10. Unsupported finding ratio tracking
"""

from __future__ import annotations

import json
import re
from typing import Any

from product.fdjp.constants import DIMENSIONS

VALID_STATUSES = {"pass", "warning", "blocker", "insufficient"}
UNSUPPORTED_EVIDENCE_REF = "UNSUPPORTED_EVIDENCE_REF"
MAX_CLAIM_LENGTH = 2000
MAX_SUMMARY_LENGTH = 2000
MAX_RISK_LENGTH = 1000
MAX_ACTION_LENGTH = 500

# Required fields for each LLM finding (anti-hallucination)
REQUIRED_FINDING_FIELDS = [
    "dimension", "claim", "claim_type", "confidence",
    "evidence_refs", "risk_if_wrong", "action_impact",
]


class LLMParseResult:
    """Container for parsed LLM output."""

    __slots__ = (
        "success",
        "dimensions",
        "insights",
        "errors",
        "raw_length",
        "schema_version",
        "unsupported_evidence_count",
        "total_evidence_refs",
        "unsupported_ratio",
        "parse_warnings",
    )

    def __init__(self):
        self.success: bool = False
        self.dimensions: dict[str, dict[str, Any]] = {}
        self.insights: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.raw_length: int = 0
        self.schema_version: str = ""
        self.unsupported_evidence_count: int = 0
        self.total_evidence_refs: int = 0
        self.unsupported_ratio: float = 0.0
        self.parse_warnings: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "dimensions": self.dimensions,
            "insights": self.insights,
            "errors": self.errors,
            "raw_length": self.raw_length,
            "schema_version": self.schema_version,
            "unsupported_evidence_count": self.unsupported_evidence_count,
            "total_evidence_refs": self.total_evidence_refs,
            "unsupported_ratio": self.unsupported_ratio,
            "parse_warnings": self.parse_warnings,
        }


def parse_llm_response(
    raw: str,
    valid_refs: set[str] | None = None,
) -> LLMParseResult:
    """Parse raw LLM response into a structured LLMParseResult.

    Applies all anti-hallucination and validation guards.

    Args:
        raw: Raw LLM response string.
        valid_refs: Set of valid reference IDs (seat_id, evidence_id, claim_id,
                    answer indices) that evidence_refs can reference.
    """
    result = LLMParseResult()
    result.raw_length = len(raw)

    if valid_refs is None:
        valid_refs = set()

    if not raw.strip():
        result.errors.append("FDJP_LLM_EMPTY_RESPONSE")
        return result

    # Step 1: Extract JSON from possible markdown fence
    json_text = _extract_json(raw)
    if json_text is None:
        result.errors.append("FDJP_LLM_JSON_EXTRACT_FAILED")
        return result

    # Step 2: Parse JSON with repair
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        # Try repair
        repaired = _repair_json(json_text)
        if repaired is not None:
            try:
                data = json.loads(repaired)
                result.parse_warnings.append("FDJP_LLM_JSON_REPAIRED")
            except json.JSONDecodeError:
                result.errors.append("FDJP_LLM_JSON_PARSE_FAILED")
                return result
        else:
            result.errors.append("FDJP_LLM_JSON_PARSE_FAILED")
            return result

    if not isinstance(data, dict):
        result.errors.append("FDJP_LLM_NOT_DICT")
        return result

    # Step 3: Extract schema version
    result.schema_version = str(data.get("schema_version", ""))

    # Step 4: Parse dimensions
    dims_raw = data.get("dimensions", {})
    if not isinstance(dims_raw, dict):
        result.errors.append("FDJP_LLM_DIMENSIONS_NOT_DICT")
        return result

    for dim in DIMENSIONS:
        dim_data = dims_raw.get(dim)
        if not isinstance(dim_data, dict):
            result.dimensions[dim] = _default_insufficient_dim(dim)
            result.errors.append(f"FDJP_LLM_DIM_MISSING: {dim}")
            continue

        parsed = _parse_dimension(dim, dim_data, valid_refs)

        # Collect evidence validation stats
        result.total_evidence_refs += parsed.get("_evidence_ref_total", 0)
        result.unsupported_evidence_count += parsed.get("_unsupported_ref_count", 0)

        result.dimensions[dim] = parsed

        # Collect dimension-level errors
        for err in parsed.get("_parse_errors", []):
            result.errors.append(f"FDJP_LLM_DIM_ERROR: {dim}: {err}")

    # Compute unsupported ratio
    if result.total_evidence_refs > 0:
        result.unsupported_ratio = round(
            result.unsupported_evidence_count / result.total_evidence_refs, 4
        )

    # Step 5: Parse insights
    insights_raw = data.get("insights", [])
    if isinstance(insights_raw, list):
        for item in insights_raw:
            if isinstance(item, dict):
                result.insights.append({
                    "type": str(item.get("type", "unknown")),
                    "target": str(item.get("target", "")),
                    "placement": str(item.get("placement", "after_conclusion")),
                    "text": str(item.get("text", ""))[:2000],
                    "weight": _safe_float(item.get("weight"), 0.5),
                    "source": str(item.get("source", "llm")),
                })

    # Success if at least 3/5 dimensions were parsed with content
    dims_with_content = sum(
        1 for d in DIMENSIONS
        if result.dimensions.get(d, {}).get("status", "insufficient") != "insufficient"
    )
    if dims_with_content >= 3 and not any(
        e.startswith("FDJP_LLM_JSON_PARSE_FAILED")
        or e.startswith("FDJP_LLM_JSON_EXTRACT_FAILED")
        for e in result.errors
    ):
        result.success = True

    return result


def _extract_json(raw: str) -> str | None:
    """Extract JSON string from raw text, stripping markdown fences."""
    # Try raw first
    stripped = raw.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    # Try markdown fence ```json ... ```
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Try to find first { and last }
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start:end + 1]

    return None


def _repair_json(text: str) -> str | None:
    """Attempt limited JSON repair.

    Allowed repairs:
    - Remove trailing commas before } or ]
    - Extract first JSON object

    Forbidden:
    - Guessing missing fields
    - Fabricating evidence_refs
    """
    repaired = text.strip()

    # Fix trailing commas before } or ]
    repaired = re.sub(r",\s*(\}|\])", r"\1", repaired)

    # Fix trailing commas at end of file
    repaired = re.sub(r",\s*$", "", repaired)

    # Try to extract first JSON object
    start = repaired.find("{")
    if start < 0:
        return None

    # Find matching closing brace
    depth = 0
    end = -1
    for i in range(start, len(repaired)):
        if repaired[i] == "{":
            depth += 1
        elif repaired[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end > start:
        return repaired[start:end + 1]

    return None


def _parse_dimension(
    dim: str,
    data: dict[str, Any],
    valid_refs: set[str],
) -> dict[str, Any]:
    """Parse and validate a single dimension from LLM output."""
    errors: list[str] = []

    status = str(data.get("status", "")).strip().lower()
    if status not in VALID_STATUSES:
        errors.append(f"invalid_status: {status}")
        status = "insufficient"

    claim = str(data.get("claim", ""))[:MAX_CLAIM_LENGTH]
    confidence = _safe_float(data.get("confidence"), 0.0)

    # Validate evidence_refs (anti-hallucination)
    evidence_refs = data.get("evidence_refs", [])
    if isinstance(evidence_refs, str):
        evidence_refs = [evidence_refs]
    if not isinstance(evidence_refs, list):
        evidence_refs = []

    # Validate each evidence_ref against known valid references
    validated_refs: list[str] = []
    unsupported_count = 0
    for ref in evidence_refs[:20]:
        ref_str = str(ref)[:200]
        if _is_valid_reference(ref_str, valid_refs):
            validated_refs.append(ref_str)
        else:
            validated_refs.append(f"UNSUPPORTED_EVIDENCE_REF:{ref_str}")
            unsupported_count += 1

    evidence_ref_total = len(validated_refs)

    reasoning = str(data.get("reasoning_summary", ""))[:MAX_SUMMARY_LENGTH]
    risk = str(data.get("risk_if_wrong", ""))[:MAX_RISK_LENGTH]
    action = str(data.get("action_impact", ""))[:MAX_ACTION_LENGTH]

    blocker_id = data.get("blocker_id")
    if blocker_id is not None and not isinstance(blocker_id, str):
        blocker_id = str(blocker_id)
    warning_id = data.get("warning_id")
    if warning_id is not None and not isinstance(warning_id, str):
        warning_id = str(warning_id)

    # If insufficient, override confidence to max 0.59
    if status == "insufficient":
        confidence = min(confidence, 0.59)

    # Detect fabricated evidence_refs (simplistic: warn if >10 refs)
    if evidence_ref_total > 10:
        errors.append("suspicious_evidence_ref_count")

    # Record unsupported refs as errors
    if unsupported_count > 0:
        errors.append(f"unsupported_evidence_refs: {unsupported_count}/{evidence_ref_total}")

    return {
        "dimension": dim,
        "status": status,
        "claim": claim,
        "confidence": round(confidence, 4),
        "evidence_refs": validated_refs,
        "reasoning_summary": reasoning,
        "risk_if_wrong": risk,
        "action_impact": action,
        "blocker_id": blocker_id,
        "warning_id": warning_id,
        "source": "llm",
        "_parse_errors": errors,
        "_evidence_ref_total": evidence_ref_total,
        "_unsupported_ref_count": unsupported_count,
    }


def _is_valid_reference(ref: str, valid_refs: set[str]) -> bool:
    """Check if an evidence_ref is valid (references known seat/evidence/claim).

    A ref is valid if:
    - It matches a known seat_id, evidence_id, or claim_id
    - It references a raw_results answer index
    - The ref is empty (no ref = valid, just no evidence)
    """
    if not ref or not ref.strip():
        return True

    ref_lower = ref.strip().lower()

    # Check exact match
    if ref_lower in valid_refs:
        return True

    # Check prefix match (e.g., "seat.deepseek" matches "seat.deepseek.output")
    for valid in valid_refs:
        if ref_lower.startswith(valid) or valid.startswith(ref_lower):
            return True

    # Accept answer index patterns like "answer_0", "raw_results[0]"
    if re.match(r"^(answer|raw_results?)\[?\d+\]?$", ref_lower):
        return True

    # Accept verdict/seat references
    if re.match(r"^(verdict\.|seat\.)", ref_lower):
        # These are standard prefixes we expect but can't validate without full context
        return True

    return False


def _default_insufficient_dim(dim: str) -> dict[str, Any]:
    """Return a safe insufficient default for a missing dimension."""
    return {
        "dimension": dim,
        "status": "insufficient",
        "claim": f"{dim}: LLM 未返回该维度分析",
        "confidence": 0.25,
        "evidence_refs": [],
        "reasoning_summary": "LLM 输出中该维度缺失",
        "risk_if_wrong": "维度缺失意味着无法评估该维度的风险",
        "action_impact": "",
        "blocker_id": None,
        "warning_id": None,
        "source": "llm",
        "_parse_errors": ["missing_from_llm_output"],
        "_evidence_ref_total": 0,
        "_unsupported_ref_count": 0,
    }


def _safe_float(value: Any, default: float) -> float:
    """Coerce value to float, clamping to [0, 1]."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN check
        return default
    return max(0.0, min(1.0, v))


def build_valid_refs_set(
    seats: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> set[str]:
    """Build a set of valid reference identifiers from seats and evidence.

    Args:
        seats: List of seat output dicts.
        evidence: List of evidence dicts.

    Returns:
        Set of lowercase reference strings.
    """
    refs: set[str] = set()

    # Add seat references
    for i, seat in enumerate(seats):
        seat_id = seat.get("seat_id", seat.get("seat", f"seat_{i}"))
        if seat_id:
            refs.add(str(seat_id).lower())
            refs.add(f"seat.{str(seat_id).lower()}")

    # Add evidence references
    for i, ev in enumerate(evidence):
        ev_id = ev.get("evidence_id", ev.get("id", f"evidence_{i}"))
        if ev_id:
            refs.add(str(ev_id).lower())

    # Add answer index references
    for i in range(len(seats)):
        refs.add(f"answer_{i}")
        refs.add(f"answer[{i}]")
        refs.add(f"raw_results[{i}]")
        refs.add(f"raw_result_{i}")

    # Add verdict references
    refs.add("verdict.conclusion")
    refs.add("verdict.inferences")

    return refs