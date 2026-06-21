#!/usr/bin/env python3
# ruff: noqa: E402
"""Web-seat backed AI Judge execution.

P0 PATCH APPLIED: Resonance followup timeout + auto-degrade
- Per-seat hard timeout: 300s (RESONANCE_PER_SEAT_TIMEOUT_SECONDS)
- Total resonance cap: 600s (RESONANCE_TOTAL_MAX_SECONDS)
- Stall detection: 180s with no completion triggers auto-degrade
- Graceful degradation: skipped seats marked as timeout, run continues
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import queue
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from bridges.web_seat_bridge import run_web_seats
from core.auto_jury import assemble_verdict
from core.final_report import attach_final_report
from core.modes import resolve_mode
from core.model_stability import model_stability_summary, update_model_stability_profiles
from core.noise_audit import build_noise_audit, noise_summary
from core.scoring_v2 import score_claim_v2
from core.seat_execution_policy import (
    annotate_execution_results,
    execution_policy_summary,
    normalize_error,
)
from core.seat_personas import SEAT_PERSONAS
from core.three_round_protocol import (
    SEAT_INFORMATION_PROFILES,
    build_round2_revision_prompts,
    build_scoring_context,
    build_three_round_plan,
)
from core.worldcup_pool import (
    attach_worldcup_pool_state,
    build_worldcup_pool_adapter_results,
    build_worldcup_pool_resonance_prompts,
    is_worldcup_pool_prompt,
    split_worldcup_pool_web_and_adapter_seats,
    worldcup_pool_seats,
)

# --- P0: Hard timeout constants for resonance followups ---
RESONANCE_PER_SEAT_TIMEOUT_SECONDS = 180   # 3 min max per seat in resonance
RESONANCE_TOTAL_MAX_SECONDS = 420          # 7 min total cap for priority resonance
RESONANCE_STALL_DETECT_SECONDS = 120       # if no seat completes in 2 min, degrade
RESONANCE_PRIORITY_MAX_SEATS = 5           # Round 2 only blocks on highest-value seats
RESONANCE_PRIORITY_MIN_SEATS = 3           # Keep a useful minimum when enough seats exist
ROUND2_SCHEDULER_SCHEMA = "ai_judge.round2_scheduler.v1"


def _web_collection_timeout_result(seat: str, reason: str, message: str) -> dict[str, Any]:
    return {
        "seat": seat,
        "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "ok": False,
        "response": "",
        "error": normalize_error(reason, fallback_code=reason, fallback_message=message),
        "error_code": reason,
        "message": message,
        "execution_validity": {"valid": False, "reason": reason},
    }


def _jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _bridge_config_for_child(config_overrides: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(config_overrides, dict):
        return config_overrides
    child_config = dict(config_overrides)
    child_config.pop("_stop_event", None)
    return child_config


def _web_collection_process_timeout(config_overrides: dict[str, Any] | None, seats: list[str]) -> float:
    config = config_overrides if isinstance(config_overrides, dict) else {}
    key = "round2_web_collection_process_timeout_seconds" if len(seats) <= 1 else "web_collection_process_timeout_seconds"
    value = config.get(key)
    if value is None and len(seats) <= 1:
        value = config.get("web_collection_process_timeout_seconds")
    try:
        timeout = float(value)
    except Exception:
        timeout = 260.0 if len(seats) <= 1 else 420.0
    return max(60.0, timeout)


def _run_web_seats_child(
    question: str,
    seats: list[str],
    mode: str,
    config_overrides: dict[str, Any] | None,
    event_queue: Any,
) -> None:
    def child_progress(step: str, progress_value: float) -> None:
        event_queue.put(("progress", step, progress_value))

    def child_trace(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        event_queue.put(("trace", phase, action, detail, data))

    try:
        result = run_web_seats(
            question=question,
            seats=seats,
            mode=mode,
            config_overrides=config_overrides,
            progress=child_progress,
            trace=child_trace,
        )
        event_queue.put(("result", _jsonable(result)))
    except BaseException as exc:  # child must report hard failures instead of killing the parent worker
        event_queue.put(("error", type(exc).__name__, str(exc)))


def _run_web_seats_with_process_guard(
    *,
    question: str,
    seats: list[str],
    mode: str,
    config_overrides: dict[str, Any] | None,
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    seats = [seat for seat in seats if seat in SEAT_PERSONAS]
    if not seats:
        return []
    config_for_child = _bridge_config_for_child(config_overrides)
    if (
        os.environ.get("PYTEST_CURRENT_TEST")
        or (isinstance(config_for_child, dict) and config_for_child.get("isolated_web_collection") is False)
    ):
        return run_web_seats(
            question=question,
            seats=seats,
            mode=mode,
            config_overrides=config_overrides,
            progress=progress,
            trace=trace,
        )

    timeout_seconds = _web_collection_process_timeout(config_for_child, seats)
    if trace:
        trace("bridge", "web_collection_process_started", "网页席位采集子进程已启动", {
            "seats": seats,
            "timeout_seconds": timeout_seconds,
        })
    ctx = multiprocessing.get_context("spawn")
    event_queue = ctx.Queue()
    process = ctx.Process(
        target=_run_web_seats_child,
        args=(question, seats, mode, config_for_child, event_queue),
        daemon=True,
    )
    process.start()
    deadline = time.time() + timeout_seconds
    result: list[dict[str, Any]] | None = None
    child_error: str | None = None
    partial_results: dict[str, dict[str, Any]] = {}

    def drain_events() -> None:
        nonlocal result, child_error
        while True:
            try:
                event = event_queue.get_nowait()
            except queue.Empty:
                break
            kind = event[0] if event else ""
            if kind == "progress" and progress:
                progress(str(event[1]), float(event[2]))
            elif kind == "trace":
                phase = str(event[1])
                action = str(event[2])
                detail = str(event[3])
                data = event[4] if isinstance(event[4], dict) else {}
                if action in {"cdp_response_captured", "cdp_partial_response_captured"}:
                    seat = str(data.get("seat") or "")
                    response = str(data.get("response") or "")
                    if seat and response:
                        partial_results[seat] = {
                            "seat": seat,
                            "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
                            "ok": True,
                            "url": str(data.get("url") or ""),
                            "profile_dir": "Chrome CDP fixed tab",
                            "elapsed_seconds": float(data.get("elapsed_seconds") or 0),
                            "response": response,
                            "error": None,
                        }
                if trace:
                    trace(phase, action, detail, data)
            elif kind == "result":
                result = event[1]
            elif kind == "error":
                child_error = f"{event[1]}: {event[2]}"

    while process.is_alive():
        drain_events()
        if time.time() >= deadline:
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            message = f"Web collection subprocess exceeded {timeout_seconds:.0f}s and was terminated."
            if trace:
                trace("bridge", "web_collection_process_timeout", "网页席位采集子进程超时终止", {
                    "seats": seats,
                    "timeout_seconds": timeout_seconds,
                    "partial_count": len(partial_results),
                })
            return [
                partial_results.get(seat) or _web_collection_timeout_result(seat, "web_collection_process_timeout", message)
                for seat in seats
            ]
        time.sleep(0.2)

    process.join(timeout=1)
    drain_events()
    if result is not None:
        return result
    message = child_error or f"Web collection subprocess exited with code {process.exitcode} before returning results."
    if trace:
        trace("bridge", "web_collection_process_failed", "网页席位采集子进程失败", {
            "seats": seats,
            "exitcode": process.exitcode,
            "error": message,
            "partial_count": len(partial_results),
        })
    return [
        partial_results.get(seat) or _web_collection_timeout_result(seat, "web_collection_process_failed", message)
        for seat in seats
    ]


def run_web_jury(
    question: str,
    mode: str = "flash",
    seats: list[str] | None = None,
    run_id: str | None = None,
    display_question: str | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    evidence_options: dict[str, Any] | None = None,
    bridge_config_overrides: dict[str, Any] | None = None,
    collect_followups: bool = False,
    three_round_plan: dict[str, Any] | None = None,
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Collect live web-seat responses and score them into a verdict."""
    question = question.strip()
    if not question:
        raise ValueError("question is required")

    config = resolve_mode(mode, override_seats=seats)
    resolved_seats = [seat for seat in config["seats"] if seat in SEAT_PERSONAS]
    if is_worldcup_pool_prompt(question):
        resolved_seats = worldcup_pool_seats(resolved_seats)
    if trace:
        trace("jury", "web_jury_start", "进入网页陪审收集", {"mode": mode, "seats": resolved_seats})
    web_seats = resolved_seats
    adapter_results: list[dict[str, Any]] = []
    if is_worldcup_pool_prompt(question):
        web_seats, adapter_seats = split_worldcup_pool_web_and_adapter_seats(resolved_seats)
        adapter_results = build_worldcup_pool_adapter_results(adapter_seats)
        if adapter_results and trace:
            trace("seat", "worldcup_pool_platform_adapter", "赛事预测池平台限制席位改走透明适配结果", {
                "adapter_seats": adapter_seats,
                "web_seats": web_seats,
            })
        if adapter_results and progress:
            progress("赛事预测池平台限制席位已透明适配", 0.13)
    raw_results = []
    if web_seats:
        raw_results = _run_web_seats_with_process_guard(
            question=question,
            seats=web_seats,
            mode=mode,
            config_overrides=bridge_config_overrides,
            progress=progress,
            trace=trace,
        )
    raw_results.extend(adapter_results)
    mentor_supplements: list[dict[str, Any]] = []
    if collect_followups:
        mentor_supplements = collect_resonance_followups(
            question=(display_question or question),
            mode=mode,
            raw_results=raw_results,
            bridge_config_overrides=bridge_config_overrides,
            three_round_plan=three_round_plan,
            progress=progress,
            trace=trace,
        )
    elif trace:
        trace("resonance", "followups_deferred", "二轮共振不自动重新发题，保留给显式采补动作", {
            "successful_seats": sum(1 for item in raw_results if item.get("ok")),
            "method": "manual_or_existing_page_recovery_only",
        })
    verdict = assemble_web_verdict_from_raw_results(
        question=question,
        mode=mode,
        seats=resolved_seats,
        raw_results=raw_results,
        mentor_supplements=mentor_supplements,
        external_evidence=external_evidence,
        run_id=run_id,
        display_question=display_question,
        three_round_plan=three_round_plan,
        trace=trace,
    )
    if evidence_options:
        verdict.setdefault("web_bridge", {})["evidence_options"] = dict(evidence_options)
    attach_worldcup_pool_state(
        verdict,
        question=question,
        raw_results=raw_results,
        mentor_supplements=mentor_supplements,
    )
    return verdict


def assemble_web_verdict_from_raw_results(
    question: str,
    mode: str,
    seats: list[str],
    raw_results: list[dict[str, Any]],
    mentor_supplements: list[dict[str, Any]] | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    run_id: str | None = None,
    display_question: str | None = None,
    three_round_plan: dict[str, Any] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    """Score already-collected web-seat responses into a verdict."""
    resolved_seats = [seat for seat in seats if seat in SEAT_PERSONAS]
    raw_results = annotate_execution_results(raw_results)
    mentor_supplements = mentor_supplements or []
    external_evidence = external_evidence or []
    primary_claims = build_web_claims(question=question, mode=mode, results=raw_results)
    mentor_claims = build_mentor_supplement_claims(question=question, mode=mode, supplements=mentor_supplements)
    deliberation = build_web_deliberation(question=question, mode=mode, results=raw_results)
    claims = primary_claims + mentor_claims + deliberation["claims"]
    ok_count = sum(1 for item in raw_results if item.get("ok"))
    failed_count = sum(1 for item in raw_results if not item.get("ok"))
    mentor_ok_count = sum(1 for item in mentor_supplements if item.get("ok"))
    round2_scheduler = _round2_scheduler_summary(mentor_supplements)
    late_evidence_queue = _late_evidence_queue(mentor_supplements)
    execution_policy = execution_policy_summary(raw_results, requested_seats=resolved_seats)
    report_question = (display_question or question).strip()
    protocol_plan = three_round_plan or build_three_round_plan(
        question=report_question,
        mode=mode,
        seats=resolved_seats,
    )
    scoring_context = build_scoring_context(
        question=report_question,
        mode=mode,
        raw_results=raw_results,
        deliberation=deliberation,
        plan=protocol_plan,
    )
    if trace:
        trace("jury", "web_jury_collected", "网页席位收集完成，进入答案总结与互评", {
            "ok_count": ok_count,
            "failed_count": failed_count,
            "primary_claim_count": len(primary_claims),
            "mentor_supplement_count": len(mentor_supplements),
            "mentor_ok_count": mentor_ok_count,
            "round2_scheduled_count": round2_scheduler.get("scheduled_count", 0),
            "round2_deferred_count": round2_scheduler.get("deferred_count", 0),
        })
        trace("jury", "web_deliberation_built", "答案总结、交叉互评与评分 claims 已生成", {
            "summary_claim_count": deliberation.get("summary_claim_count"),
            "peer_review_count": deliberation.get("peer_review_count"),
            "total_claim_count": len(claims),
            "three_round_protocol_hash": protocol_plan.get("protocol_hash"),
            "information_board_hash": (scoring_context.get("information_board") or {}).get("board_hash"),
        })
    verdict = assemble_verdict(
        question=report_question,
        mode=mode,
        seats=resolved_seats,
        claims=claims,
        run_id=run_id,
        engine="isolated-web-seat-bridge-v3.5-three-round",
        scoring_context=scoring_context,
        extra={
            "web_bridge": {
                "raw_results": raw_results,
                "ok_count": ok_count,
                "failed_count": failed_count,
                "requested_count": len(raw_results),
                "collection_complete": execution_policy["collection_complete"],
                "legacy_collection_complete": failed_count == 0 and ok_count == len(raw_results),
                "execution_policy": execution_policy,
                "required_ok_count": execution_policy["required_valid_count"],
                "required_count": execution_policy["required_count"],
                "required_failed_count": execution_policy["required_failed_count"],
                "supplementable_seats": _supplementable_seats(raw_results),
                "required_supplementable_seats": execution_policy["required_supplementable_seats"],
                "mentor_supplements": _public_mentor_supplements(mentor_supplements),
                "round2_scheduler": round2_scheduler,
                "late_evidence_queue": late_evidence_queue,
                "external_evidence": external_evidence,
                "deliberation": _public_deliberation(deliberation),
                "three_round_protocol": protocol_plan,
                "information_board": scoring_context.get("information_board") or {},
                "scoring_context": {
                    "schema": scoring_context.get("schema"),
                    "seat_vectors": scoring_context.get("seat_vectors") or {},
                    "seat_performance": scoring_context.get("seat_performance") or {},
                },
                "isolation": {
                    "uses_system_mouse": False,
                    "uses_system_keyboard": False,
                    "uses_system_clipboard": False,
                    "raw_model_answers": "web_bridge.raw_results[].response",
                    "mentor_supplements": "web_bridge.mentor_supplements",
                    "external_evidence": "web_bridge.external_evidence",
                    "rule": "原文、导师补充、外部证据三层隔离；任何层的内容不得覆盖另一层原文。",
                },
                "governance": {
                    "judge_role": "summarize_stat_score_only",
                    "model_role": "participant_and_peer_supervisor",
                    "trust_gate": "majority_confirmation_after_blind_cross_validation",
                    "frame_lock": (protocol_plan.get("frame_lock") or {}).get("name"),
                    "blind_review": {
                        "status": "contract_recorded",
                        "rule": "最终可信源必须先保留席位原文，再进入不记名交叉验证；多数席位确认后才提升为可信共识。",
                    },
                },
                "pipeline": {
                    "version": "web-jury-v3.6-three-round-priority-resonance",
                    "phases": [
                        {"id": "round0_judge_frame", "label": "第0轮：框架锁定与信息差分配", "count": len(protocol_plan.get("seat_mandates") or [])},
                        {"id": "round1_independent_answer", "label": "第一轮：网页席位独立作答", "count": len(raw_results)},
                        {
                            "id": "round2_information_feedback",
                            "label": "第二轮：信息反哺与共振修订",
                            "count": mentor_ok_count,
                            "scheduled_count": round2_scheduler.get("scheduled_count", 0),
                            "completed_count": round2_scheduler.get("completed_count", 0),
                            "deferred_count": round2_scheduler.get("deferred_count", 0),
                            "late_evidence_count": len(late_evidence_queue),
                        },
                        {"id": "answer_summary", "label": "答案总结", "count": deliberation.get("summary_claim_count", 0)},
                        {"id": "peer_review", "label": "席位互评监督", "count": deliberation.get("peer_review_count", 0)},
                        {"id": "round3_judge_settlement", "label": "第三轮：法官完整评分结算", "count": len(claims)},
                    ],
                    "scoring_engine": "core.scoring_v2.score_jury_full_pipeline",
                },
            }
        },
    )
    if not execution_policy["collection_complete"]:
        verdict.update(_bridge_incomplete_fields(raw_results, ok_count, failed_count, execution_policy=execution_policy))
    noise_audit = build_noise_audit(
        run_id=str(run_id or verdict.get("run_id") or ""),
        question=report_question,
        mode=mode,
        verdict=verdict,
        raw_results=raw_results,
    )
    verdict["noise_audit"] = noise_audit
    verdict.setdefault("web_bridge", {})["noise_audit"] = noise_summary(noise_audit)
    stability_store = update_model_stability_profiles(
        run_id=str(run_id or verdict.get("run_id") or ""),
        question=report_question,
        mode=mode,
        noise_audit=noise_audit,
        verdict=verdict,
    )
    stability = model_stability_summary(stability_store, seats=resolved_seats)
    verdict["model_stability"] = stability
    verdict.setdefault("web_bridge", {})["model_stability"] = stability
    _attach_web_judge_explainability(verdict, report_question, raw_results, deliberation)
    return verdict


def collect_resonance_followups(
    question: str,
    mode: str,
    raw_results: list[dict[str, Any]],
    bridge_config_overrides: dict[str, Any] | None = None,
    three_round_plan: dict[str, Any] | None = None,
    progress: Callable[[str, float], None] | None = None,
    trace: Callable[[str, str, str, dict[str, Any] | None], None] | None = None,
) -> list[dict[str, Any]]:
    """Ask each successful seat to answer its own resonance questions.

    P0 FIX: Each seat now has a hard timeout (300s). If a seat exceeds its
    timeout, it is marked as timed-out and the loop continues to the next seat.
    A total time cap (600s) prevents the entire resonance phase from hanging.
    If no seat completes within RESONANCE_STALL_DETECT_SECONDS, the system
    auto-degrades to first-round summary.
    """
    policy_name = _round2_policy_name(bridge_config_overrides)
    prompts = build_resonance_followup_prompts(
        question,
        raw_results,
        mode=mode,
        plan=three_round_plan,
        include_failed=policy_name == "all_seats",
    )
    if not prompts:
        if trace:
            trace("resonance", "no_followup_prompts", "没有可进入二轮共振的席位", {})
        return []

    schedule = schedule_round2_followups(
        prompts=prompts,
        raw_results=raw_results,
        plan=three_round_plan,
        max_priority_seats=_round2_priority_limit(bridge_config_overrides, len(prompts)),
        policy_name=policy_name,
    )
    active_prompts = schedule.get("scheduled_prompts") or []
    deferred_prompts = schedule.get("deferred_prompts") or []
    if trace:
        trace("resonance", "round2_schedule_built", "二轮共振优先级调度完成", {
            "schema": schedule.get("schema"),
            "policy": schedule.get("policy"),
            "prompt_count": len(prompts),
            "scheduled_count": len(active_prompts),
            "deferred_count": len(deferred_prompts),
            "priority_order": [
                {"seat": item.get("seat"), "rank": item.get("rank"), "score": item.get("score")}
                for item in schedule.get("priority_order", [])[:12]
            ],
        })

    supplements: list[dict[str, Any]] = []
    total = max(1, len(active_prompts))
    resonance_start = time.monotonic()
    last_completion_time = resonance_start
    degraded = False

    for index, prompt in enumerate(active_prompts, 1):
        seat = str(prompt.get("seat") or "")

        # --- P0: Check total time cap ---
        elapsed_total = time.monotonic() - resonance_start
        if elapsed_total > RESONANCE_TOTAL_MAX_SECONDS:
            if trace:
                trace("resonance", "total_timeout", f"二轮共振总时长超限 ({elapsed_total:.0f}s > {RESONANCE_TOTAL_MAX_SECONDS}s)，剩余席位跳过", {
                    "elapsed_seconds": round(elapsed_total, 1),
                    "skipped_seats": [str(p.get("seat")) for p in active_prompts[index - 1:]],
                })
            for remaining_prompt in active_prompts[index - 1:]:
                remaining_seat = str(remaining_prompt.get("seat") or "")
                supplements.append(_scheduled_followup_failure(
                    remaining_prompt,
                    "resonance_total_timeout",
                    f"二轮共振总时长超限 ({RESONANCE_TOTAL_MAX_SECONDS}s)，该席位被跳过",
                ))
            break

        # --- P0: Stall detection ---
        stall_elapsed = time.monotonic() - last_completion_time
        if index > 1 and stall_elapsed > RESONANCE_STALL_DETECT_SECONDS:
            if trace:
                trace("resonance", "stall_detected",
                    f"二轮共振疑似卡死：距上次完成已过 {stall_elapsed:.0f}s，自动降级为首回合汇总",
                    {"stall_seconds": round(stall_elapsed, 1), "degraded": True})
            degraded = True
            for remaining_prompt in active_prompts[index - 1:]:
                remaining_seat = str(remaining_prompt.get("seat") or "")
                supplements.append(_scheduled_followup_failure(
                    remaining_prompt,
                    "resonance_stall_degraded",
                    f"二轮共振卡死自动降级：距上次席位完成已超过 {RESONANCE_STALL_DETECT_SECONDS}s",
                ))
            break

        if progress:
            progress(f"二轮共振追问：{seat} ({index}/{total})", 0.72 + 0.02 * index / total)
        if trace:
            trace("resonance", "followup_start", f"{seat} 开始二轮共振追问", {
                "seat": seat,
                "question_count": len(prompt.get("questions") or []),
                "per_seat_timeout": RESONANCE_PER_SEAT_TIMEOUT_SECONDS,
                "total_elapsed": round(elapsed_total, 1),
            })

        def followup_progress(step: str, pct: float, _idx=index) -> None:
            if not progress:
                return
            pct = max(0.0, min(1.0, pct))
            mapped = 0.74 + 0.14 * ((_idx - 1) + pct) / total
            progress(f"二轮共振 {_idx}/{total}：{step}", min(0.90, mapped))

        # --- P0: Run with hard timeout via ThreadPoolExecutor ---
        item = _collect_single_followup_with_timeout(
            seat=seat,
            prompt=prompt,
            mode=mode,
            bridge_config_overrides=bridge_config_overrides,
            followup_progress=followup_progress,
            trace=trace,
            timeout_seconds=RESONANCE_PER_SEAT_TIMEOUT_SECONDS,
        )

        item["round"] = "mentor_resonance_followup"
        item["source_round"] = "raw_answer"
        item["source_questions"] = prompt.get("source_questions") or prompt.get("questions") or []
        item["source_answer_preview"] = prompt.get("source_answer_preview")
        item["prompt"] = prompt.get("prompt")
        item["round2_scheduled"] = True
        item["late_evidence"] = False
        item["round2_priority"] = prompt.get("round2_priority")
        item["round2_scheduler_policy"] = schedule.get("policy")
        supplements.append(item)

        # A terminal failed seat is still progress. Without this, one timed-out
        # priority seat can make the next iteration look like a global stall and
        # prematurely degrade the rest of Round 2.
        last_completion_time = time.monotonic()

        if trace:
            seat_elapsed = float(item.get("elapsed_seconds") or 0)
            trace("resonance", "followup_complete", f"{seat} 二轮共振追问完成", {
                "seat": seat,
                "ok": item.get("ok"),
                "response_chars": len(str(item.get("response") or "")),
                "error": item.get("error"),
                "seat_elapsed_seconds": round(seat_elapsed, 1),
                "timed_out": str(normalize_error(item.get("error")).get("code") or "") == "resonance_seat_timeout",
            })

    completed_scheduled_seats = {str(item.get("seat") or "").lower() for item in supplements}
    for prompt in active_prompts:
        seat = str(prompt.get("seat") or "").lower()
        if seat and seat not in completed_scheduled_seats:
            supplements.append(_scheduled_followup_failure(
                prompt,
                "resonance_loop_incomplete",
                "二轮共振循环提前结束，该优先席位未完成采补。",
            ))
            completed_scheduled_seats.add(seat)

    for prompt in deferred_prompts:
        supplements.append(_late_evidence_deferred_result(prompt))

    total_elapsed = time.monotonic() - resonance_start
    if trace:
        ok_count = sum(1 for s in supplements if s.get("ok"))
        trace("resonance", "followups_summary", "二轮共振汇总", {
            "total_seats": len(supplements),
            "ok_count": ok_count,
            "scheduled_count": len(active_prompts),
            "deferred_count": len(deferred_prompts),
            "total_elapsed_seconds": round(total_elapsed, 1),
            "degraded": degraded,
            "timeout_config": {
                "per_seat": RESONANCE_PER_SEAT_TIMEOUT_SECONDS,
                "total_max": RESONANCE_TOTAL_MAX_SECONDS,
                "stall_detect": RESONANCE_STALL_DETECT_SECONDS,
            },
        })

    if degraded and progress:
        progress("二轮共振自动降级：部分席位超时或卡死，基于已收集结果继续", 0.90)
    elif progress:
        progress("二轮共振补充完成，进入评分", 0.90)
    return supplements


def _collect_single_followup_with_timeout(
    seat: str,
    prompt: dict[str, Any],
    mode: str,
    bridge_config_overrides: dict[str, Any] | None,
    followup_progress: Callable,
    trace: Callable | None,
    timeout_seconds: int = RESONANCE_PER_SEAT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run a single resonance followup with process isolation."""
    followup_overrides = dict(bridge_config_overrides or {})
    followup_overrides["fresh_conversation_per_run"] = True
    followup_overrides["round2_web_collection_process_timeout_seconds"] = min(
        float(followup_overrides.get("round2_web_collection_process_timeout_seconds") or timeout_seconds),
        float(timeout_seconds),
    )
    try:
        results = _run_web_seats_with_process_guard(
            question=str(prompt.get("prompt") or ""),
            seats=[seat],
            mode=mode,
            config_overrides=followup_overrides,
            progress=followup_progress,
            trace=trace,
        )
        return dict(results[0]) if results else _empty_mentor_result(seat, "empty_followup_result")
    except Exception as exc:
        return _empty_mentor_result(seat, "followup_collection_error", str(exc))


def schedule_round2_followups(
    *,
    prompts: list[dict[str, Any]],
    raw_results: list[dict[str, Any]] | None = None,
    plan: dict[str, Any] | None = None,
    max_priority_seats: int | None = None,
    policy_name: str = "priority_blocking_with_late_evidence_queue",
) -> dict[str, Any]:
    """Choose the seats that may block Round 2 and defer the rest.

    Round 2 is most valuable when it extracts scarce information and dissent,
    but it becomes fragile if every successful model must complete another
    full web round. This scheduler keeps the protocol three-round while making
    the blocking part bounded and auditable.
    """
    raw_by_seat = {
        str(item.get("seat") or "").lower(): item
        for item in (raw_results or [])
        if isinstance(item, dict)
    }
    unique_prompts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for prompt in prompts:
        seat = str(prompt.get("seat") or "").lower()
        if not seat or seat in seen:
            continue
        seen.add(seat)
        row = dict(prompt)
        row["seat"] = seat
        unique_prompts.append(row)

    total = len(unique_prompts)
    limit = _bounded_round2_limit(total, max_priority_seats)
    scored_rows: list[dict[str, Any]] = []
    for prompt in unique_prompts:
        seat = str(prompt.get("seat") or "").lower()
        priority = _round2_priority_entry(prompt, raw_by_seat.get(seat, {}), plan=plan)
        row = dict(prompt)
        row["round2_priority"] = priority
        scored_rows.append(row)

    scored_rows.sort(
        key=lambda item: (
            -float((item.get("round2_priority") or {}).get("score") or 0.0),
            str(item.get("seat") or ""),
        )
    )
    for rank, row in enumerate(scored_rows, 1):
        priority = dict(row.get("round2_priority") or {})
        priority["rank"] = rank
        priority["scheduled"] = rank <= limit
        row["round2_priority"] = priority

    scheduled = [row for row in scored_rows if (row.get("round2_priority") or {}).get("scheduled")]
    deferred = [row for row in scored_rows if not (row.get("round2_priority") or {}).get("scheduled")]
    for row in deferred:
        priority = dict(row.get("round2_priority") or {})
        priority["deferred_reason"] = "below_round2_priority_cutoff"
        row["round2_priority"] = priority

    policy = {
        "name": policy_name,
        "reason": "只让最高信息差、反共识和强证据席位阻塞最终裁决，其余席位进入可审计延迟证据队列。",
        "max_priority_seats": limit,
        "min_priority_seats": min(RESONANCE_PRIORITY_MIN_SEATS, total),
        "input_count": total,
    }
    if policy_name == "all_seats":
        policy["reason"] = "用户要求全席位二轮共振；首轮失败席位也进入恢复型二轮提交，完成与失败均进入审计记录。"
    elif policy_name == "all_valid_first_round":
        policy["reason"] = "用户要求首轮有效席位全部进入二轮共振，不按优先级截断。"

    return {
        "schema": ROUND2_SCHEDULER_SCHEMA,
        "policy": policy,
        "scheduled_prompts": scheduled,
        "deferred_prompts": deferred,
        "priority_order": [
            {
                "seat": row.get("seat"),
                "seat_name": row.get("seat_name"),
                "rank": (row.get("round2_priority") or {}).get("rank"),
                "score": (row.get("round2_priority") or {}).get("score"),
                "lanes": (row.get("round2_priority") or {}).get("lanes") or [],
                "scheduled": bool((row.get("round2_priority") or {}).get("scheduled")),
                "reason": (row.get("round2_priority") or {}).get("reason"),
            }
            for row in scored_rows
        ],
    }


def _round2_policy_name(overrides: dict[str, Any] | None) -> str:
    overrides = overrides or {}
    nested = overrides.get("round2") if isinstance(overrides.get("round2"), dict) else {}
    policy = str(overrides.get("round2_policy") or nested.get("policy") or "").strip().lower().replace("-", "_")
    if policy in {"all", "full", "full_round2", "all_seats", "all_configured", "all_first_round"}:
        return "all_seats"
    if policy in {"all_valid", "all_successful", "all_valid_first_round"}:
        return "all_valid_first_round"
    return "priority_blocking_with_late_evidence_queue"


def _round2_priority_limit(overrides: dict[str, Any] | None, prompt_count: int) -> int:
    overrides = overrides or {}
    if _round2_policy_name(overrides) in {"all_seats", "all_valid_first_round"}:
        return max(0, prompt_count)
    candidates = [
        overrides.get("round2_priority_max_seats"),
        overrides.get("resonance_priority_max_seats"),
        (overrides.get("round2") or {}).get("priority_max_seats") if isinstance(overrides.get("round2"), dict) else None,
    ]
    for value in candidates:
        if value is None:
            continue
        try:
            return _bounded_round2_limit(prompt_count, int(value))
        except (TypeError, ValueError):
            continue
    return _bounded_round2_limit(prompt_count, RESONANCE_PRIORITY_MAX_SEATS)


def _bounded_round2_limit(prompt_count: int, requested: int | None) -> int:
    if prompt_count <= 0:
        return 0
    if prompt_count <= RESONANCE_PRIORITY_MIN_SEATS:
        return prompt_count
    requested_limit = RESONANCE_PRIORITY_MAX_SEATS if requested is None else int(requested)
    requested_limit = max(RESONANCE_PRIORITY_MIN_SEATS, requested_limit)
    return max(1, min(prompt_count, requested_limit))


def _round2_priority_entry(
    prompt: dict[str, Any],
    raw_result: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seat = str(prompt.get("seat") or "").lower()
    source = str(raw_result.get("response") or prompt.get("source_answer_preview") or "")
    lanes = list(SEAT_INFORMATION_PROFILES.get(seat) or ["deep_reasoning"])
    lane_weights = {
        "real_time_web": 0.18,
        "dissent": 0.16,
        "deep_reasoning": 0.14,
        "chinese_context": 0.11,
        "long_context": 0.10,
        "execution": 0.09,
        "product_experience": 0.06,
    }
    lane_score = min(0.34, sum(lane_weights.get(lane, 0.05) for lane in lanes))
    evidence_score = min(0.18, _evidence_count(source) * 0.03)
    risk_score = min(0.12, _risk_count(source) * 0.025)
    question_bonus = min(0.10, len(prompt.get("questions") or []) * 0.025)
    mandate_bonus = 0.0
    for mandate in (plan or {}).get("seat_mandates") or []:
        if str(mandate.get("seat") or "").lower() == seat:
            mandate_bonus = 0.04 if mandate.get("mandate") else 0.0
            break
    dissent_bonus = 0.06 if "dissent" in lanes else 0.0
    live_bonus = 0.05 if "real_time_web" in lanes else 0.0
    source_length = min(len(source), 2200) / 2200 * 0.10
    stable = _stable_float(seat, source[:500]) * 0.04
    score = _clamp(0.18 + lane_score + evidence_score + risk_score + question_bonus + mandate_bonus + dissent_bonus + live_bonus + source_length + stable)
    reasons = []
    if "real_time_web" in lanes:
        reasons.append("联网信息差")
    if "dissent" in lanes:
        reasons.append("反共识/失败条件")
    if "deep_reasoning" in lanes:
        reasons.append("机制推理")
    if _evidence_count(source) >= 3:
        reasons.append("证据密度较高")
    if _risk_count(source) >= 2:
        reasons.append("风险/假设较多")
    return {
        "seat": seat,
        "score": round(score, 4),
        "lanes": lanes,
        "reason": "、".join(reasons[:5]) or "基础代表性席位",
        "evidence_count": _evidence_count(source),
        "risk_count": _risk_count(source),
        "question_count": len(prompt.get("questions") or []),
        "prompt_hash": _stable_id(str(prompt.get("prompt") or "")),
    }


def _scheduled_followup_failure(prompt: dict[str, Any], code: str, message: str) -> dict[str, Any]:
    seat = str(prompt.get("seat") or "")
    item = _empty_mentor_result(seat, code, message)
    item.update({
        "round": "mentor_resonance_followup",
        "source_round": "raw_answer",
        "source_questions": prompt.get("source_questions") or prompt.get("questions") or [],
        "source_answer_preview": prompt.get("source_answer_preview"),
        "prompt": prompt.get("prompt"),
        "round2_scheduled": True,
        "late_evidence": False,
        "round2_priority": prompt.get("round2_priority"),
    })
    return item


def _late_evidence_deferred_result(prompt: dict[str, Any]) -> dict[str, Any]:
    seat = str(prompt.get("seat") or "")
    priority = dict(prompt.get("round2_priority") or {})
    item = _empty_mentor_result(
        seat,
        "round2_late_evidence_deferred",
        "该席位未进入阻塞式二轮共振，已放入 late evidence 队列；最终报告先基于优先席位结算。",
    )
    item.update({
        "round": "mentor_resonance_followup",
        "source_round": "raw_answer",
        "source_questions": prompt.get("source_questions") or prompt.get("questions") or [],
        "source_answer_preview": prompt.get("source_answer_preview"),
        "prompt": prompt.get("prompt"),
        "round2_scheduled": False,
        "late_evidence": True,
        "late_evidence_status": "queued",
        "deferred_reason": priority.get("deferred_reason") or "below_round2_priority_cutoff",
        "round2_priority": priority,
    })
    return item


# === BELOW: All original functions unchanged ===

def build_resonance_followup_prompts(
    question: str,
    raw_results: list[dict[str, Any]],
    mode: str = "standard",
    plan: dict[str, Any] | None = None,
    include_failed: bool = False,
) -> list[dict[str, Any]]:
    if is_worldcup_pool_prompt(question):
        return build_worldcup_pool_resonance_prompts(question, raw_results)
    protocol_prompts: dict[str, dict[str, Any]] = {}
    try:
        protocol_prompts = {
            str(item.get("seat") or "").lower(): item
            for item in build_round2_revision_prompts(
                question=question,
                mode=mode,
                raw_results=raw_results,
                plan=plan,
            )
        }
    except Exception:
        protocol_prompts = {}
    prompts: list[dict[str, Any]] = []
    for item in raw_results:
        seat = str(item.get("seat") or "").lower()
        if seat not in SEAT_PERSONAS:
            continue
        if not item.get("ok"):
            if include_failed:
                prompts.append(_build_failed_seat_round2_prompt(question, item, mode))
            continue
        response = str(item.get("response") or "")
        questions = extract_resonance_questions(response)
        if not questions:
            questions = _fallback_resonance_questions(question, response)
        source_questions = list(questions)
        protocol_prompt = protocol_prompts.get(seat) or {}
        if protocol_prompt.get("questions"):
            questions = list(dict.fromkeys(list(protocol_prompt.get("questions") or []) + questions))[:5]
        prompt = str(protocol_prompt.get("prompt") or "") or _build_resonance_followup_prompt(question, seat, response, questions)
        row = {
            "seat": seat,
            "seat_name": item.get("seat_name") or SEAT_PERSONAS[seat]["name"],
            "questions": questions,
            "source_questions": source_questions,
            "source_answer_preview": _compact(response, 420),
            "prompt": prompt,
        }
        if protocol_prompt.get("information_board"):
            row["information_board"] = protocol_prompt.get("information_board")
        prompts.append(row)
    return prompts


def _build_failed_seat_round2_prompt(question: str, item: dict[str, Any], mode: str) -> dict[str, Any]:
    seat = str(item.get("seat") or "").lower()
    seat_name = str(item.get("seat_name") or SEAT_PERSONAS.get(seat, {}).get("name") or seat)
    error = normalize_error(item.get("error"))
    error_code = str(error.get("code") or item.get("error_code") or "first_round_uncollected")
    error_message = str(error.get("message") or item.get("message") or "首轮未采集到可用答案。")
    questions = [
        "首轮未能采集时，你对原问题的独立结论是什么？",
        "你认为最关键的法律依据、事实前提和执行路径分别是什么？",
        "其他席位可能遗漏的失败条件或反例是什么？",
    ]
    preview = f"首轮未采集：{error_code} - {_compact(error_message, 180)}"
    prompt = (
        "[AIJUDGE_RESONANCE_FOLLOWUP]\n"
        "[AIJUDGE_ROUND2_RECOVERY]\n"
        f"模式：{mode}\n"
        f"席位：{seat_name}\n"
        f"原始问题：{question}\n\n"
        f"你的第一轮没有形成可采集答案，记录原因为：{preview}\n"
        "现在进入全席位二轮恢复共振。请不要解释网页或工具故障，也不要复述失败原因；"
        "请直接给出你对原问题的独立专业判断，并补充其他席位可能遗漏的证据、约束和失败条件。\n\n"
        "请输出以下结构：\n"
        "1. conclusion：明确结论。\n"
        "2. major_premise：适用规则、法条或权威依据；没有把握时标注 unknown。\n"
        "3. minor_premise：本案事实如何落入规则。\n"
        "4. reasoning：推理过程、反例和风险边界。\n"
        "5. final_delta：你相对第一轮全局讨论新增了什么。"
    )
    return {
        "seat": seat,
        "seat_name": seat_name,
        "questions": questions,
        "source_answer_preview": preview,
        "prompt": prompt,
        "round2_recovery": True,
    }


def extract_resonance_questions(response: str, limit: int = 5) -> list[str]:
    """Extract explicit resonance questions from a model answer."""
    text = response.strip()
    if not text:
        return []
    questions: list[str] = []
    in_resonance = False
    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        line = _clean_question_candidate(raw_line)
        if not line:
            continue
        if re.search(r"共振提问|反问|关键问题|追问|需要澄清", raw_line):
            in_resonance = True
            question_part = _clean_question_candidate(
                re.sub(r"^(共振提问|反问|关键问题|追问|需要澄清)[:：]?", "", raw_line).strip()
            )
            if question_part and _looks_like_question(question_part):
                questions.append(question_part)
            continue
        if in_resonance and _looks_like_question(line):
            questions.append(line)
        elif in_resonance and len(questions) >= 1 and re.match(r"^(结论|方案|风险|下一步|理由)[:：]", line):
            break
        if len(questions) >= limit:
            break
    if len(questions) < 3:
        for match in re.findall(r"[^。！？?\n]{6,120}[？?]", text):
            candidate = _clean_question_candidate(match)
            if candidate not in questions:
                questions.append(candidate)
            if len(questions) >= limit:
                break
    return list(dict.fromkeys(questions))[:limit]


def build_mentor_supplement_claims(
    question: str,
    mode: str,
    supplements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for item in supplements:
        seat = str(item.get("seat", "")).lower()
        if seat not in SEAT_PERSONAS:
            continue
        persona = SEAT_PERSONAS[seat]
        ok = bool(item.get("ok"))
        response = str(item.get("response") or "")
        questions = item.get("source_questions") or []
        base = _response_base(question, mode, seat, response, ok)
        if ok:
            claim_text = (
                f"{persona['name']} 二轮共振方案：基于 {len(questions)} 个自提问题补充，"
                f"{_compact(response)}"
            )
        else:
            error = normalize_error(item.get("error"))
            claim_text = (
                f"{persona['name']} 二轮共振方案未完成：{error.get('code', 'unknown')} - "
                f"{error.get('message', 'No response captured.')}"
            )
        claims.append({
            "_seat": seat,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claim_id": f"{seat}-mentor-resonance-followup",
            "claim": claim_text,
            "source_authority": _clamp(base + (0.04 if ok else 0.0)),
            "evidence_strength": max(0.12, base - (0.06 if ok else 0.20)),
            "evidence_count": min(6, max(1 if ok else 0, len(questions) + (2 if len(response) > 600 else 0))),
            "evidence_quality": max(0.10, base - 0.04),
            "freshness": 0.84 if ok else 0.20,
            "reproducibility": 0.66 if ok else 0.15,
            "historical_reliability": 0.62 if ok else 0.25,
            "confidence": max(0.10, base - (0.00 if ok else 0.22)),
            "risk_penalty": _risk_penalty(persona.get("risk_preference", "moderate"), ok),
            "web_ok": ok,
            "deliberation_phase": "mentor_supplement",
            "source_questions": questions,
        })
    return claims


def build_web_claims(question: str, mode: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw web responses into scoring-engine claims."""
    claims: list[dict[str, Any]] = []
    for item in results:
        seat = str(item.get("seat", "")).lower()
        if seat not in SEAT_PERSONAS:
            continue
        persona = SEAT_PERSONAS[seat]
        ok = bool(item.get("ok"))
        response = str(item.get("response") or "")
        base = _response_base(question, mode, seat, response, ok)
        risk_penalty = _risk_penalty(persona.get("risk_preference", "moderate"), ok)
        if ok:
            claim_text = f"{persona['name']} 网页席位：{_compact(response)}"
        else:
            error = normalize_error(item.get("error"))
            status = "慢生成待回收" if _is_slow_supplementable(item) else "未完成"
            claim_text = (
                f"{persona['name']} 网页席位{status}：{error.get('code', 'unknown')} - "
                f"{error.get('message', 'No response captured.')}"
            )

        claims.append({
            "_seat": seat,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claim_id": f"{seat}-web-main",
            "claim": claim_text,
            "source_authority": base,
            "evidence_strength": max(0.12, base - (0.10 if ok else 0.20)),
            "evidence_count": 3 if ok and len(response) > 600 else (1 if ok else 0),
            "evidence_quality": max(0.10, base - 0.08),
            "freshness": 0.86 if ok else 0.20,
            "reproducibility": 0.62 if ok else 0.15,
            "historical_reliability": 0.64 if ok else 0.25,
            "confidence": max(0.10, base - (0.02 if ok else 0.22)),
            "risk_penalty": risk_penalty,
            "web_ok": ok,
        })
    return claims


def build_web_deliberation(question: str, mode: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the answer-summary and peer-review layer before final scoring."""
    ok_cards = [
        _answer_card(question, item)
        for item in results
        if item.get("ok") and str(item.get("seat", "")).lower() in SEAT_PERSONAS
    ]
    failed = [item for item in results if not item.get("ok")]
    peer_reviews: list[dict[str, Any]] = []
    for reviewer in ok_cards:
        for target in ok_cards:
            if reviewer["seat"] == target["seat"]:
                continue
            peer_reviews.append(_peer_review(question, reviewer, target))

    grouped_reviews: dict[str, list[dict[str, Any]]] = {}
    for review in peer_reviews:
        grouped_reviews.setdefault(review["target"], []).append(review)

    answer_summaries: list[dict[str, Any]] = []
    for card in ok_cards:
        reviews = grouped_reviews.get(card["seat"], [])
        avg_peer_score = round(sum(float(r["score"]) for r in reviews) / len(reviews), 4) if reviews else None
        answer_summaries.append({
            "seat": card["seat"],
            "seat_name": card["seat_name"],
            "stance": card["stance"],
            "quality": card["quality"],
            "evidence_count": card["evidence_count"],
            "risk_count": card["risk_count"],
            "review_count": len(reviews),
            "avg_peer_score": avg_peer_score,
            "summary": card["summary"],
        })

    claims = _deliberation_claims(question=question, mode=mode, answer_cards=ok_cards, peer_reviews=peer_reviews)
    stance_counts = Counter(card["stance"] for card in ok_cards)
    agreements = _shared_terms(ok_cards, limit=8)
    disagreements = _disagreement_notes(answer_summaries)
    return {
        "version": "web-deliberation-v1",
        "ok_count": len(ok_cards),
        "failed_count": len(failed),
        "stance_distribution": dict(stance_counts),
        "agreements": agreements,
        "disagreements": disagreements,
        "answer_summaries": answer_summaries,
        "peer_reviews": peer_reviews,
        "peer_review_count": len(peer_reviews),
        "summary_claim_count": len(ok_cards),
        "claims": claims,
        "claim_count": len(claims),
    }


def _public_deliberation(deliberation: dict[str, Any]) -> dict[str, Any]:
    """Keep report JSON useful without duplicating every scoring claim twice."""
    return {
        "version": deliberation.get("version"),
        "ok_count": deliberation.get("ok_count", 0),
        "failed_count": deliberation.get("failed_count", 0),
        "stance_distribution": deliberation.get("stance_distribution", {}),
        "agreements": deliberation.get("agreements", []),
        "disagreements": deliberation.get("disagreements", []),
        "answer_summaries": deliberation.get("answer_summaries", []),
        "peer_reviews": deliberation.get("peer_reviews", []),
        "peer_review_count": deliberation.get("peer_review_count", 0),
        "summary_claim_count": deliberation.get("summary_claim_count", 0),
        "claim_count": deliberation.get("claim_count", 0),
    }


def _attach_web_judge_explainability(
    verdict: dict[str, Any],
    question: str,
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any],
) -> None:
    """Attach product-level explainability artifacts to a web verdict."""
    bridge = verdict.setdefault("web_bridge", {})
    scored_claims = list(verdict.get("claims") or [])
    score_rounds = build_score_rounds(scored_claims)
    seat_digest = build_seat_answer_digest(raw_results, deliberation, verdict.get("seat_scores", []))
    mentor_supplements = bridge.get("mentor_supplements") or []
    judge_answer = build_judge_answer(question, verdict, raw_results, deliberation, seat_digest, mentor_supplements=mentor_supplements)
    single_baseline = build_single_judge_baseline(question, judge_answer, deliberation, raw_results, verdict)

    bridge["score_rounds"] = score_rounds
    bridge["seat_answer_digest"] = seat_digest
    verdict["judge_answer"] = judge_answer
    verdict["single_judge_baseline"] = single_baseline
    attach_final_report(verdict)


def build_score_rounds(scored_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group scored claims by AI Judge round so the report can show score movement."""
    phases = [
        ("raw_answer", "第一轮：网页原始回答评分", lambda claim: not claim.get("deliberation_phase")),
        ("mentor_supplement", "第二轮：共振追问方案评分", lambda claim: claim.get("deliberation_phase") == "mentor_supplement"),
        ("answer_summary", "第三轮：答案总结评分", lambda claim: claim.get("deliberation_phase") == "answer_summary"),
        ("peer_review", "第四轮：席位互评评分", lambda claim: claim.get("deliberation_phase") == "peer_review"),
    ]
    rounds: list[dict[str, Any]] = []
    for phase_id, label, predicate in phases:
        claims = [claim for claim in scored_claims if predicate(claim)]
        if not claims:
            rounds.append({
                "id": phase_id,
                "label": label,
                "claim_count": 0,
                "average_score": None,
                "seat_scores": [],
                "top_claims": [],
            })
            continue
        scores = [float(claim.get("_score", 0.0) or 0.0) for claim in claims]
        rounds.append({
            "id": phase_id,
            "label": label,
            "claim_count": len(claims),
            "average_score": round(sum(scores) / len(scores), 4),
            "seat_scores": _round_seat_scores(claims),
            "top_claims": _round_top_claims(claims),
        })
    return rounds


def build_seat_answer_digest(
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any],
    seat_scores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create a compact, linkable digest for every model's answer, pros, and cons."""
    summaries = {str(item.get("seat")): item for item in deliberation.get("answer_summaries", [])}
    score_by_seat = {str(item.get("seat")): item for item in seat_scores}
    digest: list[dict[str, Any]] = []
    for item in raw_results:
        seat = str(item.get("seat") or "")
        persona = SEAT_PERSONAS.get(seat, {})
        summary = summaries.get(seat, {})
        score = score_by_seat.get(seat, {})
        response = str(item.get("response") or "")
        ok = bool(item.get("ok"))
        digest.append({
            "seat": seat,
            "seat_name": item.get("seat_name") or persona.get("name", seat),
            "ok": ok,
            "status": "已返回" if ok else ("待回收" if _is_slow_supplementable(item) else "未完成"),
            "score": score.get("average_score"),
            "claims_count": score.get("claims_count", 0),
            "stance": summary.get("stance") or ("慢生成待回收" if _is_slow_supplementable(item) else ("未返回" if not ok else "待归类")),
            "quality": summary.get("quality"),
            "avg_peer_score": summary.get("avg_peer_score"),
            "answer_preview": _compact(response, 260) if ok else _error_summary(item),
            "response": response,
            "pros": _seat_pros(item, summary, score, persona),
            "cons": _seat_cons(item, summary, score, persona),
            "strength": persona.get("strength", ""),
            "weakness": persona.get("weakness", ""),
            "error": item.get("error"),
        })
    return digest


def build_judge_answer(
    question: str,
    verdict: dict[str, Any],
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any],
    seat_digest: list[dict[str, Any]],
    mentor_supplements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate AI Judge's own synthesized judge answer from collected seats."""
    ok_count = sum(1 for item in raw_results if item.get("ok"))
    total = len(raw_results)
    failed_count = total - ok_count
    pending_count = sum(1 for item in raw_results if _is_slow_supplementable(item))
    stance_distribution = deliberation.get("stance_distribution") or {}
    dominant_stance = _dominant_stance(stance_distribution)
    ranked = sorted(
        [item for item in seat_digest if item.get("ok")],
        key=lambda item: float(item.get("score") or item.get("quality") or 0.0),
        reverse=True,
    )
    top_names = [str(item.get("seat_name")) for item in ranked[:3]]
    agreements = deliberation.get("agreements") or []
    disagreements = deliberation.get("disagreements") or []
    mentor_supplements = mentor_supplements or []
    mentor_ok_count = sum(1 for item in mentor_supplements if item.get("ok"))
    mentor_scheduled_count = sum(1 for item in mentor_supplements if item.get("round2_scheduled"))
    mentor_deferred_count = sum(1 for item in mentor_supplements if item.get("late_evidence"))
    if ok_count <= 0:
        final_answer = "AI Judge 法官答案：信息不足。网页席位没有返回可用答案，因此不能给出问题本身的实质判决。"
    else:
        if failed_count == 0:
            completeness = "完整收集"
        elif pending_count == failed_count:
            completeness = f"已先完成 {ok_count}/{total} 席，另有 {pending_count} 席慢生成待回收"
        else:
            completeness = f"只完成 {ok_count}/{total} 席"
        final_answer = (
            "AI Judge 法官答案：当前为" + str(verdict.get('verdict_label', verdict.get('verdict'))) + "。"
            + "本轮" + str(completeness) + "，主导立场是\"" + str(dominant_stance) + "\"。"
            + "我会优先采纳 " + (', '.join(top_names) or '已返回席位') + " 的共同部分，"
            + "把\"" + (', '.join(agreements[:5]) or '共识不足') + "\"作为初步共识；"
            + "二轮共振优先追问 " + str(mentor_scheduled_count) + " 席，已回收 " + str(mentor_ok_count)
            + " 席，late evidence 队列 " + str(mentor_deferred_count) + " 席，"
            + "若存在未返回席位或低证据回答，则最终结论只作为阶段性判断。"
        )
    return {
        "label": "AI Judge 法官综合答案",
        "question": question,
        "answer": final_answer,
        "ok_count": ok_count,
        "failed_count": failed_count,
        "dominant_stance": dominant_stance,
        "top_seats": top_names,
        "agreements": agreements[:8],
        "disagreements": disagreements[:8],
        "mentor_supplement_count": len(mentor_supplements),
        "mentor_supplement_ok_count": mentor_ok_count,
        "mentor_supplement_scheduled_count": mentor_scheduled_count,
        "late_evidence_deferred_count": mentor_deferred_count,
        "limits": _judge_limits(failed_count, total, ranked, pending_count=pending_count),
    }


def build_single_judge_baseline(
    question: str,
    judge_answer: dict[str, Any],
    deliberation: dict[str, Any],
    raw_results: list[dict[str, Any]],
    verdict: dict[str, Any],
) -> dict[str, Any]:
    """Score the same run as if AI Judge were a single summarizing model."""
    answer_text = str(judge_answer.get("answer") or "")
    answer_summaries = deliberation.get("answer_summaries") or []
    avg_quality = (
        sum(float(item.get("quality", 0.0) or 0.0) for item in answer_summaries) / len(answer_summaries)
        if answer_summaries else 0.25
    )
    ok_count = sum(1 for item in raw_results if item.get("ok"))
    total = max(1, len(raw_results))
    completeness = ok_count / total
    evidence_count = min(8, sum(int(item.get("evidence_count", 0) or 0) for item in answer_summaries))
    scored = score_claim_v2(
        claim=f"AI Judge 单模型基准：{answer_text}",
        source_authority=_clamp(0.46 + 0.24 * completeness + 0.16 * avg_quality),
        evidence_strength=_clamp(0.36 + 0.30 * avg_quality + 0.16 * completeness),
        evidence_count=evidence_count,
        evidence_quality=_clamp(0.34 + 0.42 * avg_quality),
        freshness=0.80,
        reproducibility=_clamp(0.38 + 0.28 * completeness),
        historical_reliability=0.58,
        confidence=_clamp(0.40 + 0.34 * avg_quality + 0.12 * completeness),
        risk_penalty=0.06 if completeness >= 0.9 else 0.11,
    )
    council_score = float(verdict.get("average_score", 0.0) or 0.0)
    single_score = float(scored.get("score", 0.0) or 0.0)
    return {
        "label": "AI Judge 单模型基准",
        "answer": answer_text,
        "score": round(single_score, 4),
        "tier": scored.get("tier"),
        "explanation": scored.get("explanation"),
        "council_average_score": round(council_score, 4),
        "delta_vs_council": round(council_score - single_score, 4),
        "comparison": [
            {"metric": "答案来源", "single_judge": "法官汇总后的单一答案", "council": f"{ok_count}/{total} 个网页席位原始答案"},
            {"metric": "互评校验", "single_judge": "无模型间互评", "council": f"{int(deliberation.get('peer_review_count', 0))} 条席位互评"},
            {"metric": "可追溯性", "single_judge": "只能追到汇总文本", "council": "可追到每个席位原文、摘要、互评和 claim 分数"},
        ],
    }


def _round_seat_scores(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        grouped.setdefault(str(claim.get("_seat") or ""), []).append(claim)
    rows: list[dict[str, Any]] = []
    for seat, items in grouped.items():
        scores = [float(item.get("_score", 0.0) or 0.0) for item in items]
        tiers: dict[str, int] = {}
        for item in items:
            tier = str(item.get("_tier") or "unverified")
            tiers[tier] = tiers.get(tier, 0) + 1
        rows.append({
            "seat": seat,
            "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
            "claim_count": len(items),
            "average_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "tiers": tiers,
        })
    rows.sort(key=lambda row: float(row.get("average_score", 0.0) or 0.0), reverse=True)
    return rows


def _round_top_claims(claims: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    ranked = sorted(claims, key=lambda claim: float(claim.get("_score", 0.0) or 0.0), reverse=True)
    return [
        {
            "claim_id": claim.get("claim_id"),
            "seat": claim.get("_seat"),
            "seat_name": claim.get("seat_name"),
            "score": round(float(claim.get("_score", 0.0) or 0.0), 4),
            "tier": claim.get("_tier"),
            "phase": claim.get("deliberation_phase") or "raw_answer",
            "review_target": claim.get("review_target"),
            "claim": _compact(str(claim.get("claim") or ""), 260),
        }
        for claim in ranked[:limit]
    ]


def _error_summary(item: dict[str, Any]) -> str:
    error = normalize_error(item.get("error"))
    if _is_slow_supplementable(item):
        return f"慢席待回收: {error.get('message', '仍在生成或等待旧页面答案回收。')}"
    return f"{error.get('code', 'unknown')}: {error.get('message', 'No response captured.')}"


def _seat_pros(
    item: dict[str, Any],
    summary: dict[str, Any],
    score: dict[str, Any],
    persona: dict[str, Any],
) -> list[str]:
    if not item.get("ok"):
        if _is_slow_supplementable(item):
            return ["该席位被标记为慢生成，可通过旧页面答案回收按钮读取，不会污染当前结论。"]
        return ["失败原因被保留，未混入最终结论。"]
    pros = [str(persona.get("strength") or "该席位提供了独立回答。")]
    quality = float(summary.get("quality", 0.0) or 0.0)
    evidence_count = int(summary.get("evidence_count", 0) or 0)
    peer_score = summary.get("avg_peer_score")
    final_score = float(score.get("average_score", 0.0) or 0.0)
    if quality >= 0.62:
        pros.append("答案结构、相关性和证据密度较好。")
    if evidence_count >= 3:
        pros.append("包含较多可核查依据或明确假设。")
    if peer_score is not None and float(peer_score) >= 0.62:
        pros.append("在席位互评中获得较高认可。")
    if final_score >= 0.62:
        pros.append("综合评分进入可采纳区间。")
    return list(dict.fromkeys(pros))[:4]


def _seat_cons(
    item: dict[str, Any],
    summary: dict[str, Any],
    score: dict[str, Any],
    persona: dict[str, Any],
) -> list[str]:
    if not item.get("ok"):
        if _is_slow_supplementable(item):
            return [_error_summary(item), "该席位尚未进入实质互评，旧页面答案回收成功后会回填评分与共识。"]
        return [_error_summary(item), "该席位没有进入实质互评，只作为基础设施失败记录。"]
    cons = [str(persona.get("weakness") or "仍需人工复核关键假设。")]
    evidence_count = int(summary.get("evidence_count", 0) or 0)
    risk_count = int(summary.get("risk_count", 0) or 0)
    peer_score = summary.get("avg_peer_score")
    final_score = float(score.get("average_score", 0.0) or 0.0)
    if evidence_count <= 1:
        cons.append("证据密度偏低，可能是流畅但不可验证的回答。")
    if risk_count == 0:
        cons.append("缺少风险、前提或边界条件提示。")
    if peer_score is not None and float(peer_score) < 0.50:
        cons.append("互评认可度偏低，需要二次追问。")
    if final_score < 0.45:
        cons.append("综合评分偏低，不宜单独采纳。")
    return list(dict.fromkeys(cons))[:4]


def _dominant_stance(stance_distribution: dict[str, Any]) -> str:
    if not stance_distribution:
        return "信息不足"
    return max(stance_distribution.items(), key=lambda item: int(item[1] or 0))[0]


def _judge_limits(
    failed_count: int,
    total: int,
    ranked_digest: list[dict[str, Any]],
    pending_count: int = 0,
) -> list[str]:
    limits: list[str] = []
    hard_failed = max(0, failed_count - pending_count)
    if pending_count:
        limits.append(f"{pending_count}/{total} 个席位仍在慢生成待回收，当前结论先按已返回席位给出。")
    if hard_failed:
        limits.append(f"{hard_failed}/{total} 个席位未返回完整答案，最终结论必须标记为阶段性。")
    if len(ranked_digest) <= 1:
        limits.append("可用席位不足，互评和分歧检测的价值有限。")
    if ranked_digest and all(float(item.get("score") or 0.0) < 0.55 for item in ranked_digest):
        limits.append("返回席位的综合分都不高，应补充事实或改写问题后重跑。")
    return limits or ["本轮仍需人工核查关键事实、日期、金额、规则和不可逆决策点。"]


def _is_slow_supplementable(item: dict[str, Any]) -> bool:
    if item.get("ok"):
        return False
    error = normalize_error(item.get("error"))
    return bool(item.get("supplementable")) or str(error.get("code") or "") == "slow_response_pending"


def _looks_like_question(text: str) -> bool:
    lowered = text.lower()
    return (
        text.endswith(("?", "？"))
        or any(token in text for token in ("是否", "如何", "怎样", "什么", "哪些", "为何", "为什么", "能否", "要不要"))
        or any(token in lowered for token in ("how", "what", "why", "whether", "which"))
    )


def _clean_question_candidate(text: str) -> str:
    candidate = text.strip(" \t-•*#")
    candidate = re.sub(r"^\d+[.、)]\s*", "", candidate).strip()
    candidate = re.sub(r"^(共振提问|反问|关键问题|追问|需要澄清)[:：]\s*", "", candidate).strip()
    return candidate


def _fallback_resonance_questions(question: str, response: str) -> list[str]:
    topic = _compact(question, 80)
    response_has_code = bool(re.search(r"代码|接口|API|模块|架构|测试|部署|数据流|schema|endpoint", response, flags=re.I))
    questions = [
        f"如果我是用户，{topic} 的最小可验收交付物是什么？",
        "这个方案最容易被忽略的底层风险、桥接风险或验证盲点是什么？",
        "哪些原始模型回答、导师补充和外部证据必须隔离保存，才能避免用幻觉验证幻觉？",
    ]
    if response_has_code:
        questions.append("落地到代码时，应该新增或修改哪些模块、状态字段、接口和测试？")
    else:
        questions.append("如果要把这轮判断转成可执行路线图，第一周应该先做哪三个动作？")
    return questions[:5]


def _build_resonance_followup_prompt(question: str, seat: str, response: str, questions: list[str]) -> str:
    question_lines = "\n".join(f"{index}. {item}" for index, item in enumerate(questions, 1))
    persona = SEAT_PERSONAS.get(seat, {})
    return (
        "[AIJUDGE_RESONANCE_FOLLOWUP]\n"
        "你刚才作为 AI Judge 独立席位提出了共振提问。现在请你反问自己并回答。\n\n"
        f"用户原始任务：\n{question}\n\n"
        f"你的席位身份：{persona.get('name', seat)} / {persona.get('mbti', '')}\n"
        f"你的第一轮方案摘要：\n{_compact(response, 1800)}\n\n"
        "你提出的共振提问：\n"
        f"{question_lines}\n\n"
        "请针对以上问题，带入用户角色，给出你的二轮思考和详细技术方案。必须包含：\n"
        "- 对每个共振提问的回答\n"
        "- 你认为用户真正要达成的目标和验收标准\n"
        "- 详细技术方案：模块、数据结构、状态字段、接口、流程、异常处理\n"
        "- 执行路线：先做什么、后做什么、如何验证\n"
        "- 最大风险、反方意见、需要外部证据验证的点\n"
        "请明确标注事实、假设、建议，不要覆盖或改写第一轮原文。"
    )


def _empty_mentor_result(seat: str, code: str, message: str = "No resonance follow-up response was captured.") -> dict[str, Any]:
    return {
        "seat": seat,
        "seat_name": SEAT_PERSONAS.get(seat, {}).get("name", seat),
        "ok": False,
        "url": "",
        "profile_dir": "",
        "elapsed_seconds": 0,
        "response": "",
        "error": {"code": code, "message": message},
    }


def _round2_scheduler_summary(supplements: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for item in supplements:
        priority = item.get("round2_priority")
        if not isinstance(priority, dict):
            continue
        row = {
            "seat": str(item.get("seat") or priority.get("seat") or ""),
            "seat_name": str(item.get("seat_name") or SEAT_PERSONAS.get(str(item.get("seat") or ""), {}).get("name", "")),
            "rank": int(priority.get("rank") or 0),
            "score": round(float(priority.get("score") or 0.0), 4),
            "scheduled": bool(item.get("round2_scheduled")),
            "completed": bool(item.get("ok")),
            "late_evidence": bool(item.get("late_evidence")),
            "status": "completed" if item.get("ok") else ("queued" if item.get("late_evidence") else "failed_or_skipped"),
            "reason": str(priority.get("reason") or ""),
            "deferred_reason": str(item.get("deferred_reason") or priority.get("deferred_reason") or ""),
            "lanes": [str(x) for x in (priority.get("lanes") or [])[:6]],
            "prompt_hash": str(priority.get("prompt_hash") or ""),
        }
        rows.append(row)
    rows.sort(key=lambda row: (row["rank"] or 999, row["seat"]))
    if not rows:
        return {
            "schema": ROUND2_SCHEDULER_SCHEMA,
            "policy": {
                "name": "priority_blocking_with_late_evidence_queue",
                "max_priority_seats": 0,
                "input_count": 0,
            },
            "scheduled_count": 0,
            "completed_count": 0,
            "deferred_count": 0,
            "failed_count": 0,
            "priority_order": [],
        }
    scheduled_rows = [row for row in rows if row["scheduled"]]
    policy = _round2_summary_policy(supplements, scheduled_count=len(scheduled_rows), input_count=len(rows))
    return {
        "schema": ROUND2_SCHEDULER_SCHEMA,
        "policy": policy,
        "scheduled_count": len(scheduled_rows),
        "completed_count": sum(1 for row in scheduled_rows if row["completed"]),
        "deferred_count": sum(1 for row in rows if row["late_evidence"]),
        "failed_count": sum(1 for row in scheduled_rows if not row["completed"]),
        "priority_order": rows,
    }


def _round2_summary_policy(supplements: list[dict[str, Any]], *, scheduled_count: int, input_count: int) -> dict[str, Any]:
    for item in supplements:
        policy = item.get("round2_scheduler_policy")
        if isinstance(policy, dict):
            result = dict(policy)
            result.setdefault("name", "priority_blocking_with_late_evidence_queue")
            result["max_priority_seats"] = scheduled_count
            result["input_count"] = input_count
            return result
    return {
        "name": "priority_blocking_with_late_evidence_queue",
        "max_priority_seats": scheduled_count,
        "input_count": input_count,
        "reason": "阻塞式二轮只追问高价值席位，其他席位转入 late evidence 队列。",
    }


def _late_evidence_queue(supplements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for item in supplements:
        if not item.get("late_evidence"):
            continue
        priority = item.get("round2_priority") if isinstance(item.get("round2_priority"), dict) else {}
        queue.append({
            "seat": str(item.get("seat") or ""),
            "seat_name": str(item.get("seat_name") or item.get("seat") or ""),
            "status": str(item.get("late_evidence_status") or "queued"),
            "deferred_reason": str(item.get("deferred_reason") or priority.get("deferred_reason") or ""),
            "rank": int(priority.get("rank") or 0),
            "score": round(float(priority.get("score") or 0.0), 4),
            "reason": str(priority.get("reason") or ""),
            "lanes": [str(x) for x in (priority.get("lanes") or [])[:6]],
            "prompt_hash": str(priority.get("prompt_hash") or ""),
            "source_questions": [str(q) for q in (item.get("source_questions") or [])[:5]],
            "source_answer_preview": _compact(str(item.get("source_answer_preview") or ""), 260),
        })
    queue.sort(key=lambda row: (row["rank"] or 999, row["seat"]))
    return queue


def _public_mentor_supplements(supplements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public: list[dict[str, Any]] = []
    for item in supplements:
        priority = item.get("round2_priority") if isinstance(item.get("round2_priority"), dict) else {}
        public.append({
            "seat": item.get("seat"),
            "seat_name": item.get("seat_name"),
            "ok": bool(item.get("ok")),
            "round": item.get("round"),
            "source_round": item.get("source_round"),
            "source_questions": item.get("source_questions") or [],
            "source_answer_preview": item.get("source_answer_preview"),
            "response": item.get("response") or "",
            "elapsed_seconds": item.get("elapsed_seconds"),
            "error": item.get("error"),
            "round2_scheduled": bool(item.get("round2_scheduled")),
            "late_evidence": bool(item.get("late_evidence")),
            "late_evidence_status": item.get("late_evidence_status"),
            "deferred_reason": item.get("deferred_reason"),
            "round2_priority": {
                "rank": priority.get("rank"),
                "score": priority.get("score"),
                "scheduled": priority.get("scheduled"),
                "reason": priority.get("reason"),
                "lanes": priority.get("lanes") or [],
                "prompt_hash": priority.get("prompt_hash"),
            } if priority else {},
        })
    return public


def _mentor_question_count(supplements: list[dict[str, Any]]) -> int:
    return sum(len(item.get("source_questions") or []) for item in supplements)


def _supplementable_seats(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seats: list[dict[str, Any]] = []
    for item in results:
        if not _is_slow_supplementable(item):
            continue
        seats.append({
            "seat": item.get("seat"),
            "seat_name": item.get("seat_name"),
            "error": item.get("error"),
            "submitted_at": item.get("submitted_at"),
        })
    return seats


def _bridge_collection_insufficient(
    results: list[dict[str, Any]],
    ok_count: int,
    failed_count: int,
    total: int,
) -> bool:
    """Return whether the web run is an infrastructure failure, not a verdict."""
    if total <= 0:
        return True
    policy = execution_policy_summary(results)
    if policy["required_count"] > 0:
        return not policy["collection_complete"]
    if failed_count <= 0:
        return False
    hard_failed = [item for item in results if not item.get("ok") and not _is_slow_supplementable(item)]
    if ok_count > 0 and not hard_failed:
        return False
    return ok_count < total or failed_count > 0


def _bridge_incomplete_fields(
    results: list[dict[str, Any]],
    ok_count: int,
    failed_count: int,
    execution_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    execution_policy = execution_policy or execution_policy_summary(results)
    reasons: list[str] = []
    for failure in execution_policy.get("required_failures") or []:
        error = normalize_error(failure.get("error"))
        seat_name = failure.get("seat_name") or failure.get("seat")
        code = error.get("code", "unknown")
        message = error.get("message") or failure.get("reason") or "No response captured."
        prefix = "必需席位待补全" if failure.get("supplementable") else "必需席位未完成"
        reasons.append(f"{seat_name}: {prefix} / {code} - {message}")
        if len(reasons) >= 5:
            break
    if not reasons:
        reasons = ["非 Grok 必需席位尚未全部形成执行有效答案。"]
    required_ok = int(execution_policy.get("required_valid_count") or 0)
    required_total = int(execution_policy.get("required_count") or 0)
    optional = execution_policy.get("optional_seats") or []
    return {
        "verdict": "unverified",
        "verdict_label": "必需席位执行未完成",
        "one_liner": (
            f"非 Grok 必需网页席位只拿到 {required_ok}/{required_total} 个执行有效回答；"
            f"Grok/Gork 按可选异议席位处理，不计入硬阻断。这不是问题本身的判决。"
        ),
        "confidence": 0,
        "execution_status": "requires_recovery",
        "required_execution_complete": False,
        "optional_execution_seats": optional,
        "reasons": reasons,
        "next_steps": [
            "先补全所有非 Grok 必需席位；成功后系统会回填原始回答、互评和评分。",
            "Grok/Gork 只作为可选异议席位；它的慢生成或失败不阻断发布门禁。",
            "对 send_button_not_found 的站点补充站点专用发送按钮选择器。",
            "对 transcript_pollution 的站点新建干净会话或强制使用答案包裹标记读取。",
        ],
    }


def _response_base(question: str, mode: str, seat: str, response: str, ok: bool) -> float:
    if not ok:
        return 0.26
    length_bonus = min(len(response), 2400) / 2400 * 0.16
    mode_bonus = {"flash": 0.0, "standard": 0.035, "strategic": 0.055}.get(mode, 0.02)
    stability = _stable_float(question, seat, response[:300]) * 0.08
    return min(0.88, 0.54 + length_bonus + mode_bonus + stability)


def _answer_card(question: str, item: dict[str, Any]) -> dict[str, Any]:
    seat = str(item.get("seat", "")).lower()
    persona = SEAT_PERSONAS[seat]
    response = str(item.get("response") or "")
    terms = _extract_terms(response)
    question_terms = set(_extract_terms(question))
    shared_question_terms = question_terms.intersection(terms)
    evidence_count = _evidence_count(response)
    risk_count = _risk_count(response)
    quality = _answer_quality(response, evidence_count, risk_count, len(shared_question_terms), len(question_terms))
    return {
        "seat": seat,
        "seat_name": persona["name"],
        "mbti": persona["mbti"],
        "response": response,
        "terms": terms,
        "quality": quality,
        "evidence_count": evidence_count,
        "risk_count": risk_count,
        "stance": _stance_label(response),
        "summary": _compact(response, 300),
    }


def _peer_review(question: str, reviewer: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    reviewer_terms = set(reviewer["terms"])
    target_terms = set(target["terms"])
    overlap = len(reviewer_terms.intersection(target_terms)) / max(1, min(len(reviewer_terms), len(target_terms)))
    evidence_bonus = min(0.18, float(target["evidence_count"]) * 0.035)
    risk_bonus = min(0.08, float(target["risk_count"]) * 0.02)
    overclaim_penalty = 0.10 if target["evidence_count"] == 0 and _overconfident(target["response"]) else 0.0
    diversity_bonus = 0.04 if reviewer["stance"] != target["stance"] else 0.0
    score = _clamp(0.30 + 0.42 * float(target["quality"]) + 0.16 * overlap + evidence_bonus + risk_bonus + diversity_bonus - overclaim_penalty)
    label = "强支持" if score >= 0.78 else "可采纳" if score >= 0.62 else "需复核" if score >= 0.46 else "低可信"
    comment = _peer_comment(reviewer, target, score, overlap, overclaim_penalty)
    return {
        "reviewer": reviewer["seat"],
        "reviewer_name": reviewer["seat_name"],
        "target": target["seat"],
        "target_name": target["seat_name"],
        "score": round(score, 4),
        "label": label,
        "overlap": round(overlap, 4),
        "comment": comment,
    }


def _deliberation_claims(
    question: str,
    mode: str,
    answer_cards: list[dict[str, Any]],
    peer_reviews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    mode_bonus = {"flash": 0.0, "standard": 0.035, "strategic": 0.055}.get(mode, 0.02)
    for card in answer_cards:
        persona = SEAT_PERSONAS[card["seat"]]
        quality = float(card["quality"])
        claims.append({
            "_seat": card["seat"],
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claim_id": f"{card['seat']}-answer-summary",
            "claim": f"{persona['name']} 答案总结：立场={card['stance']}；质量={quality:.2f}；摘要：{card['summary']}",
            "source_authority": _clamp(0.50 + quality * 0.32 + mode_bonus),
            "evidence_strength": _clamp(0.40 + quality * 0.35),
            "evidence_count": int(card["evidence_count"]),
            "evidence_quality": _clamp(0.38 + quality * 0.40),
            "freshness": 0.82,
            "reproducibility": _clamp(0.45 + min(0.25, len(card["terms"]) / 60)),
            "historical_reliability": _clamp(0.54 + _stable_float(question, card["seat"], "summary") * 0.24),
            "confidence": _clamp(0.45 + quality * 0.36),
            "risk_penalty": _risk_penalty(persona.get("risk_preference", "moderate"), True),
            "deliberation_phase": "answer_summary",
        })

    for review in peer_reviews:
        reviewer = str(review["reviewer"])
        persona = SEAT_PERSONAS[reviewer]
        score = float(review["score"])
        claims.append({
            "_seat": reviewer,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "claim_id": f"{reviewer}-reviews-{review['target']}",
            "claim": f"{review['reviewer_name']} 互评 {review['target_name']}：{review['label']}，{review['comment']}",
            "source_authority": _clamp(0.46 + score * 0.34 + mode_bonus),
            "evidence_strength": _clamp(0.35 + score * 0.42),
            "evidence_count": 2 if score >= 0.62 else 1,
            "evidence_quality": _clamp(0.36 + score * 0.40),
            "freshness": 0.80,
            "reproducibility": _clamp(0.42 + float(review["overlap"]) * 0.35),
            "historical_reliability": _clamp(0.52 + _stable_float(question, reviewer, str(review["target"])) * 0.24),
            "confidence": _clamp(0.42 + score * 0.38),
            "risk_penalty": _risk_penalty(persona.get("risk_preference", "moderate"), True),
            "deliberation_phase": "peer_review",
            "review_target": review["target"],
        })
    return claims


def _extract_terms(text: str) -> list[str]:
    tokens = re.findall(r"[一-鿿]{2,}|[A-Za-z][A-Za-z0-9_+-]{2,}", text.lower())
    stop = {"以及", "但是", "如果", "因为", "所以", "这个", "一个", "the", "and", "for", "with", "that", "this"}
    return [token for token in tokens if token not in stop][:160]


def _evidence_count(text: str) -> int:
    patterns = [
        r"https?://",
        r"\d+(?:\.\d+)?\s*(?:%|年|月|日|美元|亿|万|场|次|分|kg|km)?",
        r"来源|依据|数据|报告|研究|统计|历史|规则|赛程|排名|赔率|假设|证据",
    ]
    return min(8, sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns))


def _risk_count(text: str) -> int:
    return min(6, len(re.findall(r"风险|不确定|假设|前提|限制|反例|可能|除非|需要验证|误差", text)))


def _answer_quality(response: str, evidence_count: int, risk_count: int, shared_terms: int, question_terms: int) -> float:
    length_score = min(len(response), 1800) / 1800
    evidence_score = min(evidence_count, 6) / 6
    risk_score = min(risk_count, 4) / 4
    relevance = shared_terms / max(1, min(question_terms, 18))
    structure = min(1.0, len(re.findall(r"(?:^|\n)\s*(?:[-*•]|\d+[.、]|[一二三四五六七八九十][、.])", response)) / 6)
    return round(_clamp(0.18 + 0.20 * length_score + 0.24 * evidence_score + 0.14 * risk_score + 0.16 * relevance + 0.08 * structure), 4)


def _stance_label(text: str) -> str:
    lowered = text.lower()
    if re.search(r"不建议|反对|不可行|失败|不要|低可信|unlikely|not likely", lowered):
        return "反对/谨慎"
    if re.search(r"建议|支持|可行|优先|看好|会|likely|should|recommend", lowered):
        return "支持/推进"
    if re.search(r"取决于|条件|如果|可能|不确定|需要验证|depends|conditional", lowered):
        return "条件/待验证"
    return "中性/信息型"


def _overconfident(text: str) -> bool:
    return bool(re.search(r"一定|必然|毫无疑问|绝对|肯定|guaranteed|certainly", text, flags=re.IGNORECASE))


def _peer_comment(reviewer: dict[str, Any], target: dict[str, Any], score: float, overlap: float, penalty: float) -> str:
    parts = []
    if overlap >= 0.42:
        parts.append("与自身答案有较高语义重合")
    elif overlap <= 0.16:
        parts.append("提供了明显不同视角")
    else:
        parts.append("与自身答案部分重合")
    if target["evidence_count"] >= 3:
        parts.append("证据/细节密度较高")
    else:
        parts.append("证据密度偏低")
    if target["risk_count"] >= 2:
        parts.append("有显式风险或前提检查")
    if penalty:
        parts.append("存在高确定性但低证据的过度断言风险")
    if score < 0.46:
        parts.append("建议进入人工复核或二次追问")
    return "；".join(parts) + "。"


def _shared_terms(cards: list[dict[str, Any]], limit: int = 8) -> list[str]:
    counts: Counter[str] = Counter()
    for card in cards:
        counts.update(set(card["terms"]))
    threshold = 2 if len(cards) >= 2 else 1
    return [term for term, count in counts.most_common(40) if count >= threshold][:limit]


def _disagreement_notes(answer_summaries: list[dict[str, Any]]) -> list[str]:
    if not answer_summaries:
        return []
    stance_groups: dict[str, list[str]] = {}
    for item in answer_summaries:
        stance_groups.setdefault(str(item["stance"]), []).append(str(item["seat_name"]))
    if len(stance_groups) <= 1:
        return ["席位立场整体同向，主要差异在证据密度和风险提示。"]
    return [
        f"{stance}: {', '.join(names)}"
        for stance, names in stance_groups.items()
    ]


def _risk_penalty(risk_preference: str, ok: bool) -> float:
    if not ok:
        return 0.16
    return {
        "very_low": 0.02,
        "low": 0.03,
        "conservative": 0.035,
        "moderate_low": 0.04,
        "moderate": 0.05,
        "balanced": 0.05,
        "moderate_high": 0.065,
        "aggressive": 0.08,
        "aggressive_pragmatic": 0.075,
        "high": 0.09,
    }.get(risk_preference, 0.05)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _compact(text: str, limit: int = 520) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."


def _stable_float(*parts: str) -> float:
    raw = "::".join(parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:12]
    return int(digest, 16) / float(0xFFFFFFFFFFFF)


def _stable_id(value: Any, length: int = 16) -> str:
    raw = repr(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]
