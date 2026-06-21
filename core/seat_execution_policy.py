#!/usr/bin/env python3
"""Execution-validity policy for web model seats.

The product treats Grok as an optional dissent seat. Every other requested web
seat must produce a verifiable current-run answer before the run can be treated
as a complete verdict.
"""

from __future__ import annotations

import hashlib
from typing import Any

from core.seat_personas import SEAT_PERSONAS


POLICY_VERSION = "required-web-seat-v1"
OPTIONAL_EXECUTION_SEATS = {"grok", "gork"}
RECOVERABLE_EXECUTION_CODES = {
    "cdp_unavailable",
    "web_collection_process_timeout",
    "prompt_write_unconfirmed",
    "slow_response_pending",
    "response_timeout",
    "response_below_minimum",
    "send_button_not_found",
    "submit_unconfirmed",
    "chrome_submit_unconfirmed",
    "composer_busy",
    "page_error",
    "model_page_error",
    "chrome_crash",
    "blank_page",
    "page_recovery_failed",
    "response_not_relevant",
    "prompt_still_in_input",
    "long_prompt_still_in_input",
    "existing_answer_not_found",
    "existing_answer_placeholder",
    "existing_answer_prompt_echo",
    "fixed_tab_not_found",
    "input_not_found",
    "transcript_pollution",
    "apple_events_execute_failed",
    "chrome_composer_not_ready",
    "composer_not_ready",
    "deepseek_expert_mode_not_verified",
    "doubao_expert_mode_not_verified",
    "xunfei_quality_mode_not_verified",
    "xunfei_desk_bounced_to_home",
    "xunfei_desk_input_not_ready",
    "xunfei_desk_ready_failed",
}


def normalize_error(error: Any, *, fallback_code: str = "", fallback_message: str = "") -> dict[str, Any]:
    """Return a structured error object even when older callers pass a string."""
    if isinstance(error, dict):
        normalized = dict(error)
        code = normalized.get("code") or normalized.get("reason") or fallback_code
        message = normalized.get("message") or normalized.get("detail") or fallback_message
        if code:
            normalized["code"] = str(code)
        if message:
            normalized["message"] = str(message)
        return normalized
    if error is None or error == "":
        if not fallback_code and not fallback_message:
            return {}
        return {
            "code": str(fallback_code or "unknown"),
            "message": str(fallback_message or fallback_code or "No response captured."),
        }
    text = str(error)
    return {
        "code": str(fallback_code or text or "unknown"),
        "message": str(fallback_message or text or "No response captured."),
    }


def normalize_seat_id(seat: Any) -> str:
    normalized = str(seat or "").strip().lower()
    return "grok" if normalized == "gork" else normalized


def seat_execution_required(seat: Any, config: dict[str, Any] | None = None) -> bool:
    seat_id = normalize_seat_id(seat)
    seat_config = ((config or {}).get("seats") or {}).get(seat_id) or {}
    if "execution_required" in seat_config:
        return bool(seat_config.get("execution_required"))
    if seat_config.get("best_effort") or seat_config.get("exclude_from_publish_gate"):
        return False
    return seat_id not in OPTIONAL_EXECUTION_SEATS


def attach_execution_validity(
    item: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
    required: bool | None = None,
    submitted: bool | None = None,
    accepted: bool | None = None,
    marker_found: bool | None = None,
    marker_closed: bool | None = None,
    matches_question: bool | None = None,
    prompt_echo: bool | None = None,
    polluted: bool | None = None,
    page_busy: bool | None = None,
    capture_mode: str | None = None,
    response_text: str | None = None,
    prompt_id: str | None = None,
    attempts: int | None = None,
    source: str = "web_bridge",
) -> dict[str, Any]:
    """Return a copy of a raw seat result with an execution_validity block."""
    result = dict(item)
    seat = normalize_seat_id(result.get("seat"))
    existing = result.get("execution_validity") or {}
    response = str(response_text if response_text is not None else result.get("response") or "")
    effective_prompt_id = str(prompt_id or result.get("prompt_id") or existing.get("prompt_id") or "")
    is_ok = bool(result.get("ok"))
    required_value = seat_execution_required(seat, config) if required is None else bool(required)
    min_response_chars = minimum_required_response_chars(seat, config=config, existing=existing, item=result)

    submitted_sources = [
        submitted,
        existing["submitted"] if "submitted" in existing else None,
        result["submission_confirmed"] if "submission_confirmed" in result else None,
        result["recovered_from_existing_page"] if "recovered_from_existing_page" in result else None,
        bool(result.get("submit_result")) if "submit_result" in result else None,
        bool(effective_prompt_id) if effective_prompt_id else None,
        bool(is_ok and response),
    ]
    submitted_value = _bool_or_default(*submitted_sources)
    accepted_value = _bool_or_default(accepted, existing.get("accepted"), is_ok)
    marker_found_value = _bool_or_default(marker_found, existing.get("marker_found"), result.get("marker_found"), False)
    marker_closed_value = _bool_or_default(marker_closed, existing.get("marker_closed"), result.get("marker_closed"), False)
    matches_question_value = _bool_or_default(
        matches_question,
        existing.get("matches_question"),
        result.get("matches_question"),
        True if accepted_value else False,
    )
    prompt_echo_value = _bool_or_default(prompt_echo, existing.get("prompt_echo"), result.get("prompt_echo"), False)
    polluted_value = _bool_or_default(polluted, existing.get("polluted"), result.get("polluted"), False)
    page_busy_value = _bool_or_default(page_busy, existing.get("page_busy"), result.get("page_busy"), False)
    response_chars = len(response.strip())
    valid_required_answer = bool(
        accepted_value
        and submitted_value
        and response_chars >= min_response_chars
        and matches_question_value
        and not prompt_echo_value
        and not polluted_value
    )
    valid = bool(valid_required_answer if required_value else accepted_value)
    response_hash = hashlib.sha256(response.encode("utf-8")).hexdigest() if response else None
    reason = "valid" if valid else _execution_invalid_reason(
        required=required_value,
        accepted=accepted_value,
        submitted=submitted_value,
        response_chars=response_chars,
        min_response_chars=min_response_chars,
        matches_question=matches_question_value,
        prompt_echo=prompt_echo_value,
        polluted=polluted_value,
        page_busy=page_busy_value,
        result=result,
    )

    result["execution_validity"] = {
        "policy_version": POLICY_VERSION,
        "required": required_value,
        "valid": valid,
        "submitted": submitted_value,
        "accepted": accepted_value,
        "marker_found": marker_found_value,
        "marker_closed": marker_closed_value,
        "matches_question": matches_question_value,
        "prompt_echo": prompt_echo_value,
        "polluted": polluted_value,
        "page_busy": page_busy_value,
        "response_chars": response_chars,
        "min_response_chars": min_response_chars,
        "response_hash": response_hash,
        "capture_mode": capture_mode or existing.get("capture_mode") or result.get("capture_mode") or "",
        "prompt_id": effective_prompt_id,
        "attempts": attempts if attempts is not None else existing.get("attempts") or result.get("retry_attempts") or 0,
        "source": source,
        "reason": reason,
    }
    if required_value:
        result["execution_required"] = True
    else:
        result["execution_required"] = False
        result["best_effort"] = True
    result["min_response_chars"] = min_response_chars
    if isinstance(config, dict) and isinstance(config.get("answer_contract"), dict):
        result["answer_contract"] = dict(config["answer_contract"])
    elif isinstance(result.get("answer_contract"), dict):
        result["answer_contract"] = dict(result["answer_contract"])
    elif isinstance(existing.get("answer_contract"), dict):
        result["answer_contract"] = dict(existing["answer_contract"])
    if required_value and not valid:
        result["ok"] = False
        if not result.get("error"):
            result["error"] = _execution_error_for_reason(reason, response_chars=response_chars, min_response_chars=min_response_chars)
        if reason in RECOVERABLE_EXECUTION_CODES:
            result["supplementable"] = True
    return result


def annotate_execution_results(
    results: list[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [attach_execution_validity(item, config=config) for item in results]


def minimum_required_response_chars(
    seat: Any,
    *,
    config: dict[str, Any] | None = None,
    existing: dict[str, Any] | None = None,
    item: dict[str, Any] | None = None,
) -> int:
    """Return the minimum complete-answer size for a required seat.

    Default runs keep the historical permissive contract. High-stakes or
    structure-heavy runs can raise this through bridge overrides, and the value
    is preserved on re-annotation so report assembly cannot accidentally loosen
    the collection gate.
    """
    seat_id = normalize_seat_id(seat)
    config = config if isinstance(config, dict) else {}
    existing = existing if isinstance(existing, dict) else {}
    item = item if isinstance(item, dict) else {}
    seat_config = ((config.get("seats") or {}).get(seat_id) or {}) if isinstance(config.get("seats"), dict) else {}
    contract = config.get("answer_contract") if isinstance(config.get("answer_contract"), dict) else {}
    item_contract = item.get("answer_contract") if isinstance(item.get("answer_contract"), dict) else {}
    existing_contract = existing.get("answer_contract") if isinstance(existing.get("answer_contract"), dict) else {}

    candidates = [
        seat_config.get("min_required_response_chars"),
        seat_config.get("required_answer_min_chars"),
        seat_config.get("min_response_chars"),
        _seat_min_from_contract(contract, seat_id),
        contract.get("min_required_response_chars"),
        contract.get("required_answer_min_chars"),
        config.get("min_required_response_chars"),
        config.get("required_answer_min_chars"),
        config.get("min_response_chars"),
        item.get("min_response_chars"),
        existing.get("min_response_chars"),
        _seat_min_from_contract(item_contract, seat_id),
        item_contract.get("min_required_response_chars"),
        _seat_min_from_contract(existing_contract, seat_id),
        existing_contract.get("min_required_response_chars"),
    ]
    for value in candidates:
        try:
            parsed = int(value)
        except Exception:
            continue
        if parsed > 0:
            return max(1, min(8000, parsed))
    return 1


def _seat_min_from_contract(contract: dict[str, Any], seat: str) -> Any:
    by_seat = contract.get("min_response_chars_by_seat")
    if isinstance(by_seat, dict):
        return by_seat.get(seat)
    return None


def execution_policy_summary(
    results: list[dict[str, Any]],
    *,
    requested_seats: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    annotated = annotate_execution_results(results, config=config)
    result_by_seat = {normalize_seat_id(item.get("seat")): item for item in annotated}
    requested = [normalize_seat_id(seat) for seat in (requested_seats or []) if normalize_seat_id(seat)]
    if not requested:
        requested = [normalize_seat_id(item.get("seat")) for item in annotated if normalize_seat_id(item.get("seat"))]

    required_seats = [seat for seat in requested if seat_execution_required(seat, config)]
    optional_seats = [seat for seat in requested if not seat_execution_required(seat, config)]
    required_failures: list[dict[str, Any]] = []
    required_valid_count = 0
    for seat in required_seats:
        item = result_by_seat.get(seat)
        if not item:
            required_failures.append(_missing_failure(seat))
            continue
        validity = item.get("execution_validity") or {}
        if item.get("ok") and validity.get("valid"):
            required_valid_count += 1
            continue
        required_failures.append(_failure_summary(item))

    optional_failures = [
        _failure_summary(item)
        for seat, item in result_by_seat.items()
        if seat in optional_seats and not item.get("ok")
    ]
    required_supplementable = [
        failure for failure in required_failures
        if failure.get("supplementable") or str(normalize_error(failure.get("error")).get("code") or "") in RECOVERABLE_EXECUTION_CODES
    ]

    return {
        "policy_version": POLICY_VERSION,
        "required_rule": "all_requested_non_grok_seats_must_have_valid_execution",
        "optional_seats": optional_seats,
        "required_seats": required_seats,
        "required_count": len(required_seats),
        "required_valid_count": required_valid_count,
        "required_failed_count": len(required_failures),
        "required_failures": required_failures,
        "required_supplementable_seats": required_supplementable,
        "optional_failed_count": len(optional_failures),
        "optional_failures": optional_failures,
        "collection_complete": len(required_failures) == 0,
        "grok_counts_as": "optional_dissent_best_effort",
    }


def _bool_or_default(*values: Any) -> bool:
    for value in values:
        if value is None:
            continue
        return bool(value)
    return False


def _execution_invalid_reason(
    *,
    required: bool,
    accepted: bool,
    submitted: bool,
    response_chars: int,
    min_response_chars: int,
    matches_question: bool,
    prompt_echo: bool,
    polluted: bool,
    page_busy: bool,
    result: dict[str, Any],
) -> str:
    if not required and not accepted:
        return "optional_best_effort_not_available"
    if not submitted:
        return "submission_not_confirmed"
    if not accepted:
        error = normalize_error(result.get("error"))
        return str(error.get("code") or "answer_not_accepted")
    if response_chars <= 0:
        return "empty_response"
    if prompt_echo:
        return "prompt_echo"
    if polluted:
        return "transcript_pollution"
    if response_chars < min_response_chars:
        return "response_below_minimum"
    if not matches_question:
        return "response_not_relevant"
    if page_busy:
        return "page_busy"
    return "execution_invalid"


def _execution_error_for_reason(reason: str, *, response_chars: int, min_response_chars: int) -> dict[str, Any]:
    if reason == "response_below_minimum":
        return {
            "code": "response_below_minimum",
            "message": (
                f"Captured answer has {response_chars} chars, below this run's minimum "
                f"complete-answer contract ({min_response_chars} chars)."
            ),
        }
    return {"code": reason or "execution_invalid", "message": reason or "Execution validity failed."}


def _failure_summary(item: dict[str, Any]) -> dict[str, Any]:
    seat = normalize_seat_id(item.get("seat"))
    error = normalize_error(item.get("error"))
    validity = item.get("execution_validity") or {}
    return {
        "seat": seat,
        "seat_name": item.get("seat_name") or SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "ok": bool(item.get("ok")),
        "supplementable": bool(item.get("supplementable")) or str(error.get("code") or "") in RECOVERABLE_EXECUTION_CODES,
        "error": error,
        "execution_validity": validity,
        "reason": validity.get("reason") or error.get("code") or "execution_invalid",
        "submitted_at": item.get("submitted_at"),
        "prompt_id": item.get("prompt_id") or validity.get("prompt_id"),
    }


def _missing_failure(seat: str) -> dict[str, Any]:
    return {
        "seat": seat,
        "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "ok": False,
        "supplementable": False,
        "error": {"code": "missing_result", "message": "No raw result was produced for this required seat."},
        "execution_validity": {
            "policy_version": POLICY_VERSION,
            "required": True,
            "valid": False,
            "submitted": False,
            "accepted": False,
            "reason": "missing_result",
        },
        "reason": "missing_result",
    }
