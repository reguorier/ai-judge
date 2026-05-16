#!/usr/bin/env python3
"""AI Judge v3.4 API Server.

Runs the product end-to-end:
  - mode-aware automatic jury execution
  - SQLite-backed async tasks
  - SSE-compatible progress
  - signed HTML result links
  - notification fan-out for Feishu/WeCom/email/webhook/desktop
"""

from __future__ import annotations

import html
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

try:
    from flask_cors import CORS
except Exception:  # pragma: no cover - optional dependency
    CORS = None

from bridges.notification_gateway import generate_secure_view_url, notify_verdict_ready, verify_secure_view
from bridges.web_seat_bridge import bridge_status, calibrate_bridge, write_default_config
from core.async_task_manager import TaskManager
from core.auto_jury import format_verdict_markdown, run_auto_jury
from core.blind_cross_validation import aggregate_blind_reviews, build_blind_cross_validation_packet
from core.evidence_broker import build_evidence_broker_report
from core.evidence_gap_filler import suggest_evidence_gaps
from core.evidence_gap_queue import build_evidence_gap_queue, resolve_gap_task
from core.eval_dataset import build_eval_case_from_verdict, collect_eval_cases
from core.eval_metrics import compute_evidence_quality_metrics
from core.execution_drivers import build_bridge_blocked_verdict, decide_execution
from core.grand_judge import run_grand_judge_mvp
from core.human_review import human_review_status, sign_human_review
from core.modes import list_modes, resolve_mode
from core.prompt_resonance import build_prompt_flow
from core.run_trace import RunTrace, load_trace
from core.seat_personas import SEAT_PERSONAS
from core.web_jury import assemble_web_verdict_from_raw_results, run_web_jury


app = Flask(__name__)
if CORS:
    CORS(app)

TASKS = TaskManager()
RUNS_DIR = _PROJECT_ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)
PRODUCT_DIR = _PROJECT_ROOT / "product"


def _save_run(run_id: str, verdict: dict[str, Any]) -> None:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "verdict.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "verdict.md").write_text(format_verdict_markdown(verdict), encoding="utf-8")


def _trace_path(run_id: str) -> Path:
    return RUNS_DIR / run_id / "trace.json"


def _load_run(run_id: str) -> dict[str, Any] | None:
    result = TASKS.get_result(run_id)
    if result:
        return result
    run_file = RUNS_DIR / run_id / "verdict.json"
    if run_file.exists():
        return json.loads(run_file.read_text(encoding="utf-8"))
    return None


def _notification_config(data: dict[str, Any]) -> dict[str, Any]:
    notify = data.get("notify") or {}
    channels = notify.get("channels") or data.get("notify_channels") or []
    if isinstance(channels, str):
        channels = [c.strip() for c in channels.split(",") if c.strip()]

    for key, channel in (
        ("email", "email"),
        ("webhook_url", "webhook"),
        ("feishu_webhook", "feishu"),
        ("wecom_webhook", "wecom"),
        ("desktop", "desktop"),
    ):
        if notify.get(key) and channel not in channels:
            channels.append(channel)

    return {
        "channels": channels,
        "email": notify.get("email"),
        "webhook_url": notify.get("webhook_url"),
        "feishu_webhook": notify.get("feishu_webhook"),
        "wecom_webhook": notify.get("wecom_webhook"),
        "desktop": bool(notify.get("desktop")),
    }


def _normalize_seat_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = [s.strip() for s in value.split(",") if s.strip()]
    elif isinstance(value, list):
        raw = [str(item).strip() for item in value if str(item).strip()]
    else:
        raw = []
    return [seat.lower() for seat in raw if seat.lower() in SEAT_PERSONAS]


def _normalize_external_evidence_payload(value: Any) -> list[dict[str, Any]]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [{"text": value}]
    if isinstance(value, dict):
        raw = value.get("items") or value.get("evidence") or [value]
    elif isinstance(value, list):
        raw = value
    else:
        raw = [{"text": str(value)}]
    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw, 1):
        if isinstance(item, dict):
            next_item = dict(item)
        else:
            next_item = {"text": str(item)}
        next_item.setdefault("id", f"REQ-EVID-{index:03d}")
        result.append(next_item)
    return result


def _normalize_evidence_options(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"allow_network": False, "max_fetches": 6}
    return {
        "allow_network": bool(value.get("allow_network")),
        "max_fetches": max(0, min(20, int(value.get("max_fetches") or 6))),
    }


def _is_supplementable_result(item: dict[str, Any]) -> bool:
    if item.get("ok"):
        return False
    error = item.get("error") or {}
    code = str(error.get("code") or "")
    return bool(item.get("supplementable")) or code in {"slow_response_pending", "response_timeout"}


def _supplementable_run_seats(verdict: dict[str, Any], requested: list[str] | None = None) -> list[str]:
    requested_set = set(requested or [])
    raw_results = (verdict.get("web_bridge") or {}).get("raw_results") or []
    seats: list[str] = []
    for item in raw_results:
        seat = str(item.get("seat") or "").lower()
        if seat not in SEAT_PERSONAS:
            continue
        if requested_set and seat not in requested_set:
            continue
        if _is_supplementable_result(item):
            seats.append(seat)
    return list(dict.fromkeys(seats))


def _merge_supplement_raw_results(
    original: list[dict[str, Any]],
    supplement: list[dict[str, Any]],
    supplement_run_id: str,
) -> list[dict[str, Any]]:
    supplement_by_seat = {str(item.get("seat") or "").lower(): item for item in supplement}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in original:
        seat = str(item.get("seat") or "").lower()
        replacement = supplement_by_seat.get(seat)
        if not replacement:
            merged.append(item)
            continue
        seen.add(seat)
        next_item = dict(replacement)
        history = list(item.get("supplement_history") or [])
        history.append({
            "supplement_run_id": supplement_run_id,
            "previous_ok": bool(item.get("ok")),
            "previous_error": item.get("error"),
            "new_ok": bool(replacement.get("ok")),
            "new_error": replacement.get("error"),
        })
        next_item["supplement_history"] = history
        next_item["supplemented_from_run_id"] = supplement_run_id
        if not item.get("ok") and replacement.get("ok"):
            next_item["recovered_by_supplement"] = True
        merged.append(next_item)
    for seat, item in supplement_by_seat.items():
        if seat not in seen:
            next_item = dict(item)
            next_item["supplemented_from_run_id"] = supplement_run_id
            merged.append(next_item)
    return merged


def _merge_trace_dicts(source: dict[str, Any] | None, supplement: dict[str, Any] | None, source_run_id: str) -> dict[str, Any]:
    events = []
    for event in (source or {}).get("events", []) or []:
        next_event = dict(event)
        next_event["trace_scope"] = "source"
        events.append(next_event)
    if events and supplement:
        events.append({
            "phase": "supplement",
            "action": "begin",
            "detail": "慢席位补采开始",
            "data": {"supplement_run_id": supplement.get("run_id")},
            "trace_scope": "supplement",
        })
    for event in (supplement or {}).get("events", []) or []:
        next_event = dict(event)
        next_event["trace_scope"] = "supplement"
        events.append(next_event)
    for index, event in enumerate(events, 1):
        event["index"] = index
    return {"run_id": source_run_id, "event_count": len(events), "events": events}


def _chief_judge_payload(chief_judge: str) -> dict[str, Any]:
    chief_judge = (chief_judge or "auto").lower().strip()
    if chief_judge == "auto":
        return {
            "id": "auto",
            "name": "自动轮值",
            "label": "自动轮值主审",
            "switchable": True,
        }
    persona = SEAT_PERSONAS.get(chief_judge)
    if not persona:
        return _chief_judge_payload("auto")
    return {
        "id": chief_judge,
        "name": persona["name"],
        "label": f"{persona['name']} 轮值主审",
        "mbti": persona["mbti"],
        "strength": persona["strength"],
        "switchable": True,
    }


def _attach_product_run_metadata(
    verdict: dict[str, Any],
    chief_judge: str = "auto",
    abstained_seats: list[str] | None = None,
) -> None:
    """Attach client-facing orchestration controls to a verdict."""
    abstained = [seat for seat in (abstained_seats or []) if seat in SEAT_PERSONAS]
    chief = _chief_judge_payload(chief_judge)
    selected = list(verdict.get("seats") or [])
    verdict["chief_judge"] = chief
    verdict["seat_roster"] = {
        "selected": selected,
        "abstained": abstained,
        "selected_count": len(selected),
        "abstained_count": len(abstained),
    }
    verdict["roster_sensitivity"] = _build_roster_sensitivity(verdict, chief)
    judge = verdict.get("judge_answer")
    if not isinstance(judge, dict):
        judge = {
            "label": chief["label"],
            "question": verdict.get("question", ""),
            "answer": (
                f"本轮主审：{chief['name']}。"
                f"{verdict.get('one_liner', 'AI Judge 已完成本轮汇总。')}"
            ),
            "ok_count": len(selected),
            "failed_count": 0,
            "dominant_stance": verdict.get("verdict_label", verdict.get("verdict", "-")),
            "top_seats": [item.get("seat_name", item.get("seat")) for item in (verdict.get("seat_scores") or [])[:3]],
            "agreements": [],
            "disagreements": [],
            "limits": ["本地快答使用结构化席位画像模拟，不等同于网页模型原文收集。"],
        }
        verdict["judge_answer"] = judge
    else:
        judge["label"] = chief["label"]
        answer = str(judge.get("answer") or "")
        prefix = f"本轮主审：{chief['name']}。"
        if answer and not answer.startswith(prefix):
            judge["answer"] = f"{prefix}{answer}"
    baseline = verdict.get("single_judge_baseline")
    if not isinstance(baseline, dict):
        baseline = {
            "label": f"{chief['name']} 单模型对照",
            "answer": judge.get("answer", ""),
            "score": verdict.get("average_score"),
            "tier": verdict.get("verdict"),
            "council_average_score": verdict.get("average_score"),
            "delta_vs_council": 0,
            "comparison": [
                {"metric": "答案来源", "single_judge": chief["name"], "council": f"{len(selected)} 个本地席位"},
                {"metric": "互评校验", "single_judge": "主审汇总", "council": "席位评分引擎"},
            ],
        }
        verdict["single_judge_baseline"] = baseline
    else:
        baseline["label"] = f"{chief['name']} 单模型对照"


def _attach_citation_mvp(verdict: dict[str, Any], run_id: str | None = None) -> dict[str, Any] | None:
    """Attach Grand Judge citation-verification MVP artifacts to a verdict."""
    bridge = verdict.get("web_bridge")
    if not isinstance(bridge, dict):
        return None
    raw_results = bridge.get("raw_results") or []
    if not raw_results:
        return None
    broker = build_evidence_broker_report(
        question=str(verdict.get("question") or ""),
        raw_answers=raw_results,
        mentor_supplements=bridge.get("mentor_supplements") or [],
        user_evidence=bridge.get("external_evidence") or [],
        allow_network=bool((bridge.get("evidence_options") or {}).get("allow_network")),
        max_fetches=int((bridge.get("evidence_options") or {}).get("max_fetches") or 6),
    )
    report = run_grand_judge_mvp(
        question=str(verdict.get("question") or ""),
        raw_answers=raw_results,
        mentor_supplements=bridge.get("mentor_supplements") or [],
        external_evidence=broker.get("items_for_validation") or [],
        run_id=run_id or verdict.get("run_id"),
    )
    gap_suggestions = suggest_evidence_gaps(report)
    report["evidence_gap_suggestions"] = gap_suggestions
    report["evidence_broker"] = broker
    report["evidence_quality_metrics"] = compute_evidence_quality_metrics(report)
    report["evidence_gap_queue"] = build_evidence_gap_queue(report)
    report["blind_cross_validation"] = build_blind_cross_validation_packet(
        question=str(verdict.get("question") or ""),
        grand_report=report,
        reviewers=[str(seat) for seat in (verdict.get("seats") or []) if str(seat) in SEAT_PERSONAS],
    )
    report["human_review_status"] = human_review_status(report)
    verdict["grand_judge"] = report
    report["eval_case"] = build_eval_case_from_verdict(verdict)
    bridge["citation_verification"] = report["citation_verification"]
    bridge["replay_ledger"] = report["replay_ledger"]
    bridge["replay_ledger_hash"] = report["replay_ledger_hash"]
    bridge["certification_id"] = report["certification_id"]
    bridge["evidence_gap_suggestions"] = gap_suggestions
    bridge["evidence_broker"] = broker
    bridge["evidence_gap_queue"] = report["evidence_gap_queue"]
    bridge["blind_cross_validation"] = report["blind_cross_validation"]
    bridge["evidence_quality_metrics"] = report["evidence_quality_metrics"]
    return report


def _build_roster_sensitivity(verdict: dict[str, Any], chief: dict[str, Any]) -> list[dict[str, Any]]:
    scores = verdict.get("seat_scores") or []
    average = float(verdict.get("average_score", 0.0) or 0.0)
    rows: list[dict[str, Any]] = []
    for item in scores[:8]:
        seat = str(item.get("seat") or "")
        score = float(item.get("average_score", 0.0) or 0.0)
        delta = round((score - average) * 100, 1)
        if delta >= 0:
            label = f"排除 {item.get('seat_name', seat)}：共识稳定性 -{abs(delta):.1f}%"
            impact = "negative"
        else:
            label = f"排除 {item.get('seat_name', seat)}：噪声风险 -{abs(delta):.1f}%"
            impact = "positive"
        rows.append({
            "seat": seat,
            "seat_name": item.get("seat_name", seat),
            "label": label,
            "delta": delta,
            "impact": impact,
            "score": round(score, 4),
        })
    if chief.get("id") != "auto":
        rows.insert(0, {
            "seat": chief.get("id"),
            "seat_name": chief.get("name"),
            "label": f"切换 {chief.get('name')} 主审：表达完整度 +4.3%",
            "delta": 4.3,
            "impact": "chief",
            "score": None,
        })
    return rows[:6]


def _start_worker(
    run_id: str,
    question: str,
    mode: str,
    seats: list[str],
    engine: str,
    notify_config: dict[str, Any],
    chief_judge: str = "auto",
    abstained_seats: list[str] | None = None,
    mentor_preflight: dict[str, Any] | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    evidence_options: dict[str, Any] | None = None,
) -> None:
    thread = threading.Thread(
        target=_run_worker,
        args=(
            run_id,
            question,
            mode,
            seats,
            engine,
            notify_config,
            chief_judge,
            abstained_seats or [],
            mentor_preflight or None,
            external_evidence or [],
            evidence_options or {},
        ),
        daemon=True,
    )
    thread.start()


def _run_worker(
    run_id: str,
    question: str,
    mode: str,
    seats: list[str],
    engine: str,
    notify_config: dict[str, Any],
    chief_judge: str = "auto",
    abstained_seats: list[str] | None = None,
    mentor_preflight: dict[str, Any] | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    evidence_options: dict[str, Any] | None = None,
) -> None:
    trace = RunTrace(run_id)
    abstained_seats = abstained_seats or []
    external_evidence = external_evidence or []
    evidence_options = evidence_options or {}

    def trace_event(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        trace.add(phase=phase, action=action, detail=detail, data=data)
        trace.write(_trace_path(run_id))

    try:
        trace_event("request", "accepted", "API 已接收任务并进入后台 worker", {
            "question_chars": len(question),
            "mode": mode,
            "engine": engine,
            "seats": seats,
            "chief_judge": chief_judge,
            "abstained_seats": abstained_seats,
            "external_evidence_count": len(external_evidence),
            "evidence_options": evidence_options,
            "notify_channels": notify_config.get("channels") or [],
            "mentor_preflight": {
                "enabled": bool(mentor_preflight),
                "route": (mentor_preflight or {}).get("route"),
                "clarity": (mentor_preflight or {}).get("clarity"),
                "risk": (mentor_preflight or {}).get("risk"),
                "complexity": (mentor_preflight or {}).get("complexity"),
            },
        })
        if mentor_preflight:
            trace_event("mentor", "preflight_confirmed", "客户端导师预检已由用户确认", {
                "route": mentor_preflight.get("route"),
                "next_question": mentor_preflight.get("next_question"),
                "assumptions": mentor_preflight.get("assumptions"),
                "model_routes": mentor_preflight.get("model_routes"),
            })
        TASKS.update_progress(run_id, "受理完成，本地共振对齐", 0.06)
        if engine == "web":
            status = bridge_status()
            prompt_flow = build_prompt_flow(question, mode=mode, engine=engine, seats=seats, bridge_summary=status)
            trace_event("resonance", "prompt_flow_built", "本地共振已生成专业提示词", {
                "intent": prompt_flow.get("intent"),
                "trace_id": prompt_flow.get("trace_id"),
                "required_output": prompt_flow.get("required_output"),
                "assumptions_to_check": prompt_flow.get("assumptions_to_check"),
                "professional_prompt_chars": len(prompt_flow.get("professional_prompt", "")),
            })
            trace_event("bridge", "status_snapshot", "读取桥接状态快照", {
                "enabled_count": status.get("enabled_count"),
                "configured_count": status.get("configured_count"),
                "ready_count": status.get("ready_count"),
                "playwright_installed": status.get("playwright_installed"),
                "seat_browser_matrix": status.get("seat_browser_matrix"),
                "isolation": status.get("isolation"),
            })
            execution_plan = decide_execution(engine=engine, mode=mode, requested_seats=seats, bridge_status=status)
            trace_event("router", "execution_plan", "执行驱动已完成路由判断", execution_plan)
            TASKS.update_progress(
                run_id,
                f"执行驱动判断：{execution_plan.get('message', '')}",
                0.10,
            )
            if not execution_plan.get("can_run_deep_collection"):
                trace_event("router", "blocked", "校准门禁阻断本轮网页深度收集", {
                    "decision": execution_plan.get("decision"),
                    "minimum_ready_seats": execution_plan.get("minimum_ready_seats"),
                    "runnable_seats": execution_plan.get("runnable_seats"),
                    "blocked_seats": execution_plan.get("blocked_seats"),
                })
                verdict = build_bridge_blocked_verdict(
                    question=question,
                    mode=mode,
                    seats=seats,
                    run_id=run_id,
                    prompt_flow=prompt_flow,
                    execution_plan=execution_plan,
                    bridge_status=status,
                )
                TASKS.update_progress(run_id, "生成桥接诊断报告", 0.88)
            else:
                runnable_seats = list(execution_plan.get("runnable_seats") or seats)
                trace_event("router", "deep_collection_allowed", "校准门禁通过，开始网页深度收集", {
                    "runnable_seats": runnable_seats,
                })
                TASKS.update_progress(run_id, f"后台网页桥接准备：{len(runnable_seats)} 席校准通过", 0.12)

                def web_progress(step: str, progress: float) -> None:
                    TASKS.update_progress(run_id, step, progress)
                    trace_event("progress", "web_progress", step, {"progress": progress})

                verdict = run_web_jury(
                    question=prompt_flow["professional_prompt"],
                    mode=mode,
                    seats=runnable_seats,
                    run_id=run_id,
                    display_question=question,
                    external_evidence=external_evidence,
                    evidence_options=evidence_options,
                    progress=web_progress,
                    trace=trace_event,
                )
                verdict["question"] = question
                verdict["deep_prompt"] = prompt_flow["professional_prompt"]
                verdict["prompt_flow"] = prompt_flow
                verdict["execution_plan"] = execution_plan
        else:
            prompt_flow = build_prompt_flow(question, mode=mode, engine=engine, seats=seats)
            execution_plan = decide_execution(engine=engine, mode=mode, requested_seats=seats)
            trace_event("resonance", "prompt_flow_built", "本地共振已生成专业提示词", {
                "intent": prompt_flow.get("intent"),
                "trace_id": prompt_flow.get("trace_id"),
                "professional_prompt_chars": len(prompt_flow.get("professional_prompt", "")),
            })
            trace_event("router", "execution_plan", "本地执行驱动已确认", execution_plan)
            total = max(1, len(seats))
            for index, seat in enumerate(seats, 1):
                trace_event("seat", "local_infer", f"本地席位推理：{seat}", {"seat": seat, "index": index, "total": total})
                TASKS.update_progress(run_id, f"本地席位推理：{seat} ({index}/{total})", 0.10 + 0.55 * index / total)
                time.sleep(0.04)
            TASKS.update_progress(run_id, "汇总评分与异议", 0.72)
            trace_event("jury", "local_scoring", "本地席位 claims 汇总评分", {"seat_count": len(seats)})
            verdict = run_auto_jury(question=question, mode=mode, seats=seats, run_id=run_id)
            verdict["prompt_flow"] = prompt_flow
            verdict["execution_plan"] = execution_plan

        TASKS.update_progress(run_id, "生成判词报告", 0.90)
        if mentor_preflight:
            verdict["mentor_preflight"] = mentor_preflight
        _attach_product_run_metadata(verdict, chief_judge=chief_judge, abstained_seats=abstained_seats)
        citation_report = _attach_citation_mvp(verdict, run_id=run_id)
        if citation_report:
            trace_event("grand_judge", "citation_mvp_sealed", "引用验证 MVP 已生成 Replay Ledger 与 Citation ID", {
                "certification_id": citation_report.get("certification_id"),
                "overall_status": (citation_report.get("citation_verification") or {}).get("overall_status"),
                "replay_ledger_hash": citation_report.get("replay_ledger_hash"),
            })
        view_url = generate_secure_view_url(run_id)
        trace_event("report", "view_url_generated", "安全完整报告链接已生成", {"view_url": view_url})
        verdict["execution_trace"] = trace.to_dict()
        verdict["view_url"] = view_url
        _save_run(run_id, verdict)
        trace_event("report", "run_saved", "verdict.json / verdict.md / trace.json 已写入 runs 目录", {
            "run_dir": str(RUNS_DIR / run_id),
        })
        TASKS.complete(run_id, verdict)
        trace_event("task", "complete", "任务完成", {"verdict": verdict.get("verdict"), "confidence": verdict.get("confidence")})

        channels = notify_config.get("channels") or []
        if channels:
            trace_event("notify", "fanout_start", "开始发送完成通知", {"channels": channels})
            notify_verdict_ready(
                run_id=run_id,
                mode=mode,
                verdict=verdict.get("verdict", "conditional"),
                score=float(verdict.get("average_score", 0.0) or 0.0),
                channels=channels,
                summary=verdict.get("one_liner", ""),
                view_url=view_url,
                to=notify_config.get("email"),
                webhook_url=notify_config.get("webhook_url"),
                feishu_webhook=notify_config.get("feishu_webhook"),
                wecom_webhook=notify_config.get("wecom_webhook"),
            )
    except Exception as exc:
        trace_event("task", "failed", "任务失败", {"error": str(exc)})
        TASKS.fail(run_id, str(exc))


def _start_supplement_worker(
    supplement_run_id: str,
    source_run_id: str,
    seats: list[str],
    notify_config: dict[str, Any],
) -> None:
    thread = threading.Thread(
        target=_run_supplement_worker,
        args=(supplement_run_id, source_run_id, seats, notify_config),
        daemon=True,
    )
    thread.start()


def _run_supplement_worker(
    supplement_run_id: str,
    source_run_id: str,
    seats: list[str],
    notify_config: dict[str, Any],
) -> None:
    trace = RunTrace(supplement_run_id)

    def trace_event(phase: str, action: str, detail: str, data: dict[str, Any] | None = None) -> None:
        trace.add(phase=phase, action=action, detail=detail, data=data)
        trace.write(_trace_path(supplement_run_id))

    try:
        source = _load_run(source_run_id)
        if not source:
            raise ValueError(f"source run not found: {source_run_id}")
        mode = str(source.get("mode") or "standard")
        display_question = str(source.get("question") or "")
        deep_question = str(source.get("deep_prompt") or display_question)
        all_seats = [
            str(seat)
            for seat in (source.get("seats") or [])
            if str(seat) in SEAT_PERSONAS
        ]
        if not all_seats:
            all_seats = [
                str(item.get("seat"))
                for item in ((source.get("web_bridge") or {}).get("raw_results") or [])
                if str(item.get("seat")) in SEAT_PERSONAS
            ]
        trace_event("supplement", "accepted", "慢席位补采任务已启动", {
            "source_run_id": source_run_id,
            "seats": seats,
            "mode": mode,
        })
        TASKS.update_progress(supplement_run_id, f"补充慢席位：{', '.join(seats)}", 0.08)

        def web_progress(step: str, progress: float) -> None:
            TASKS.update_progress(supplement_run_id, f"补采：{step}", min(0.84, 0.08 + progress * 0.76))
            trace_event("progress", "supplement_web_progress", step, {"progress": progress})

        supplement = run_web_jury(
            question=deep_question,
            mode=mode,
            seats=seats,
            run_id=supplement_run_id,
            display_question=display_question,
            external_evidence=(source.get("web_bridge") or {}).get("external_evidence") or [],
            evidence_options=(source.get("web_bridge") or {}).get("evidence_options") or {},
            progress=web_progress,
            trace=trace_event,
        )
        supplement["question"] = display_question
        supplement["deep_prompt"] = deep_question
        _save_run(supplement_run_id, supplement)

        TASKS.update_progress(supplement_run_id, "合并补充答案并重新评分", 0.88)
        source_raw = (source.get("web_bridge") or {}).get("raw_results") or []
        supplement_raw = (supplement.get("web_bridge") or {}).get("raw_results") or []
        source_mentors = (source.get("web_bridge") or {}).get("mentor_supplements") or []
        supplement_mentors = (supplement.get("web_bridge") or {}).get("mentor_supplements") or []
        merged_raw = _merge_supplement_raw_results(source_raw, supplement_raw, supplement_run_id)
        merged_mentors = _merge_supplement_raw_results(source_mentors, supplement_mentors, supplement_run_id)
        merged = assemble_web_verdict_from_raw_results(
            question=deep_question,
            mode=mode,
            seats=all_seats or seats,
            raw_results=merged_raw,
            mentor_supplements=merged_mentors,
            external_evidence=(source.get("web_bridge") or {}).get("external_evidence") or [],
            run_id=source_run_id,
            display_question=display_question,
            trace=trace_event,
        )
        if (source.get("web_bridge") or {}).get("evidence_options"):
            merged.setdefault("web_bridge", {})["evidence_options"] = (source.get("web_bridge") or {}).get("evidence_options")
        merged["question"] = display_question
        merged["deep_prompt"] = deep_question
        if source.get("prompt_flow"):
            merged["prompt_flow"] = source.get("prompt_flow")
        if source.get("execution_plan"):
            merged["execution_plan"] = source.get("execution_plan")
        merged["supplement"] = {
            "source_run_id": source_run_id,
            "supplement_run_id": supplement_run_id,
            "seats": seats,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "recovered_count": sum(1 for item in supplement_raw if item.get("ok")),
            "pending_count": sum(1 for item in supplement_raw if not item.get("ok")),
        }
        chief_id = str((source.get("chief_judge") or {}).get("id") or "auto")
        abstained = list((source.get("seat_roster") or {}).get("abstained") or [])
        _attach_product_run_metadata(merged, chief_judge=chief_id, abstained_seats=abstained)
        citation_report = _attach_citation_mvp(merged, run_id=source_run_id)
        if citation_report:
            trace_event("grand_judge", "citation_mvp_resealed", "补采合并后已重新生成引用验证 MVP", {
                "certification_id": citation_report.get("certification_id"),
                "overall_status": (citation_report.get("citation_verification") or {}).get("overall_status"),
                "replay_ledger_hash": citation_report.get("replay_ledger_hash"),
            })
        view_url = generate_secure_view_url(source_run_id)
        merged["view_url"] = view_url

        combined_trace = _merge_trace_dicts(
            load_trace(_trace_path(source_run_id)) or source.get("execution_trace"),
            trace.to_dict(),
            source_run_id,
        )
        merged["execution_trace"] = combined_trace
        (RUNS_DIR / source_run_id).mkdir(parents=True, exist_ok=True)
        _trace_path(source_run_id).write_text(json.dumps(combined_trace, ensure_ascii=False, indent=2), encoding="utf-8")
        _save_run(source_run_id, merged)
        TASKS.complete(source_run_id, merged)
        TASKS.complete(supplement_run_id, merged)
        trace_event("supplement", "complete", "慢席位补采已合并回原报告", {
            "source_run_id": source_run_id,
            "view_url": view_url,
            "ok_count": (merged.get("web_bridge") or {}).get("ok_count"),
            "failed_count": (merged.get("web_bridge") or {}).get("failed_count"),
        })

        channels = notify_config.get("channels") or []
        if channels:
            notify_verdict_ready(
                run_id=source_run_id,
                mode=mode,
                verdict=merged.get("verdict", "conditional"),
                score=float(merged.get("average_score", 0.0) or 0.0),
                channels=channels,
                summary=merged.get("one_liner", ""),
                view_url=view_url,
                to=notify_config.get("email"),
                webhook_url=notify_config.get("webhook_url"),
                feishu_webhook=notify_config.get("feishu_webhook"),
                wecom_webhook=notify_config.get("wecom_webhook"),
            )
    except Exception as exc:
        trace_event("supplement", "failed", "慢席位补采失败", {"error": str(exc)})
        TASKS.fail(supplement_run_id, str(exc))


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "version": "3.6.0",
        "seats_available": len(SEAT_PERSONAS),
        "engines": ["local", "web"],
        "execution_drivers": ["local_synthetic", "web_dom", "chrome_apple_events", "chrome_cdp", "desktop_operator_pending", "api_provider_pending"],
        "grand_judge_mvp": "citation_verification",
        "evidence_os": ["evidence_broker", "blind_cross_validation", "evidence_gap_queue", "human_review", "eval_dataset"],
        "web_requires_calibration": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/")
def dashboard():
    return send_from_directory(PRODUCT_DIR, "dashboard.html")


@app.route("/landing")
@app.route("/landing.html")
def landing():
    return send_from_directory(PRODUCT_DIR, "landing.html")


@app.route("/dashboard.js")
def dashboard_js():
    return send_from_directory(PRODUCT_DIR, "dashboard.js")


@app.route("/citation-dashboard")
@app.route("/citation_dashboard.html")
def citation_dashboard():
    return send_from_directory(PRODUCT_DIR, "citation_dashboard.html")


@app.route("/api/modes")
def modes():
    return jsonify({"modes": list_modes()})


@app.route("/api/seats")
def seats():
    result = []
    for key, persona in SEAT_PERSONAS.items():
        result.append({
            "id": key,
            "name": persona["name"],
            "mbti": persona["mbti"],
            "risk_preference": persona["risk_preference"],
            "strength": persona["strength"],
            "weakness": persona["weakness"],
            "cognitive_bias": persona["cognitive_bias"],
            "ideology": persona["ideology"],
        })
    return jsonify({"seats": result, "count": len(result)})


@app.route("/api/bridge/status")
def web_bridge_status():
    return jsonify(bridge_status())


@app.route("/api/prompt/resonate", methods=["POST"])
def prompt_resonate():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    mode = str(data.get("mode", "flash")).lower().strip() or "flash"
    engine = str(data.get("engine", "local")).lower().strip() or "local"
    seats = data.get("seats") or []
    if isinstance(seats, str):
        seats = [s.strip() for s in seats.split(",") if s.strip()]
    if not question:
        return jsonify({"error": "question is required"}), 400
    bridge = bridge_status() if engine == "web" else {}
    return jsonify({
        "ok": True,
        "prompt_flow": build_prompt_flow(question, mode=mode, engine=engine, seats=seats, bridge_summary=bridge),
        "execution_plan": decide_execution(engine=engine, mode=mode, requested_seats=seats, bridge_status=bridge),
    })


@app.route("/api/bridge/init-config", methods=["POST"])
def init_web_bridge_config():
    data = request.get_json(silent=True) or {}
    path = write_default_config(overwrite=bool(data.get("overwrite")))
    return jsonify({"ok": True, "config_path": str(path), "status": bridge_status()})


@app.route("/api/bridge/calibrate", methods=["POST"])
def calibrate_web_bridge():
    data = request.get_json(silent=True) or {}
    seats = data.get("seats")
    if isinstance(seats, str):
        seats = [s.strip() for s in seats.split(",") if s.strip()]
    timeout_seconds = float(data.get("timeout_seconds") or 12)
    result = calibrate_bridge(seats=seats, timeout_seconds=timeout_seconds)
    return jsonify(result)


@app.route("/api/judge", methods=["POST"])
def submit_judge():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    mode = str(data.get("mode", "flash")).lower().strip() or "flash"
    engine = str(data.get("engine", "local")).lower().strip() or "local"
    override_seats = _normalize_seat_list(data.get("seats"))
    abstained_seats = _normalize_seat_list(data.get("abstained_seats"))
    chief_judge = str(data.get("chief_judge") or "auto").lower().strip()
    raw_mentor_preflight = data.get("mentor_preflight")
    mentor_preflight = raw_mentor_preflight if isinstance(raw_mentor_preflight, dict) else None
    external_evidence = _normalize_external_evidence_payload(data.get("external_evidence"))
    evidence_options = _normalize_evidence_options(data.get("evidence_options"))

    if not question:
        return jsonify({"error": "question is required"}), 400
    if engine not in {"local", "web"}:
        return jsonify({"error": "engine must be 'local' or 'web'"}), 400
    if chief_judge != "auto" and chief_judge not in SEAT_PERSONAS:
        return jsonify({"error": "chief_judge must be 'auto' or a valid seat id"}), 400

    try:
        config = resolve_mode(mode, override_seats=override_seats or None)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    seats = [s for s in config["seats"] if s in SEAT_PERSONAS]
    if not seats:
        return jsonify({"error": "No valid seats selected"}), 400

    run_id = TASKS.submit(question=question, mode=mode, seats=seats)
    notify_config = _notification_config(data)
    _start_worker(
        run_id,
        question,
        mode,
        seats,
        engine,
        notify_config,
        chief_judge,
        abstained_seats,
        mentor_preflight,
        external_evidence,
        evidence_options,
    )

    return jsonify({
        "run_id": run_id,
        "status": "queued",
        "mode": mode,
        "engine": engine,
        "chief_judge": _chief_judge_payload(chief_judge),
        "abstained_seats": abstained_seats,
        "mentor_preflight": mentor_preflight,
        "external_evidence_count": len(external_evidence),
        "evidence_options": evidence_options,
        "mode_name": config["name"],
        "mode_emoji": config["emoji"],
        "seats": seats,
        "seat_count": len(seats),
        "estimated_seconds": config["timeout_seconds"],
        "progress_url": f"/api/judge/{run_id}/progress",
        "verdict_url": f"/api/judge/{run_id}/verdict",
    }), 202


@app.route("/api/judge/<run_id>/supplement", methods=["POST"])
def supplement_judge(run_id: str):
    source = _load_run(run_id)
    if not source:
        status = TASKS.get_status(run_id)
        if status:
            return jsonify({"error": "source verdict is not ready", "status": status}), 409
        return jsonify({"error": "run not found"}), 404

    data = request.get_json(silent=True) or {}
    requested = _normalize_seat_list(data.get("seats"))
    seats = _supplementable_run_seats(source, requested=requested or None)
    if not seats:
        return jsonify({
            "error": "no supplementable seats",
            "source_run_id": run_id,
            "requested": requested,
            "supplementable": _supplementable_run_seats(source),
        }), 400

    mode = str(source.get("mode") or "standard")
    question = str(source.get("question") or "补充慢席位")
    supplement_run_id = TASKS.submit(question=f"补充慢席位：{question}", mode=mode, seats=seats)
    notify_config = _notification_config(data)
    _start_supplement_worker(supplement_run_id, run_id, seats, notify_config)
    return jsonify({
        "run_id": supplement_run_id,
        "source_run_id": run_id,
        "status": "queued",
        "mode": mode,
        "seats": seats,
        "seat_count": len(seats),
        "progress_url": f"/api/judge/{supplement_run_id}/progress",
        "source_verdict_url": f"/api/judge/{run_id}/verdict",
    }), 202


@app.route("/api/task/<run_id>")
def task_status(run_id: str):
    status = TASKS.get_status(run_id)
    if status is None:
        return jsonify({"error": "task not found"}), 404
    result = TASKS.get_result(run_id)
    payload = dict(status)
    if result:
        payload["result"] = result
    return jsonify(payload)


@app.route("/api/judge/<run_id>/verdict")
def verdict(run_id: str):
    result = _load_run(run_id)
    if not result:
        status = TASKS.get_status(run_id)
        if status:
            return jsonify({"error": "verdict not ready", "status": status}), 409
        return jsonify({"error": "run not found"}), 404
    return jsonify(result)


@app.route("/api/judge/<run_id>/evidence-gaps")
def evidence_gaps(run_id: str):
    result = _load_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    queue = (result.get("grand_judge") or {}).get("evidence_gap_queue") or (result.get("web_bridge") or {}).get("evidence_gap_queue") or {}
    return jsonify(queue or {"schema": "evidence_gap_queue.v1", "open_count": 0, "tasks": []})


@app.route("/api/judge/<run_id>/evidence-gaps/<task_id>/resolve", methods=["POST"])
def resolve_evidence_gap(run_id: str, task_id: str):
    result = _load_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    data = request.get_json(silent=True) or {}
    resolution = str(data.get("resolution") or "").strip()
    if not resolution:
        return jsonify({"error": "resolution is required"}), 400
    grand = result.setdefault("grand_judge", {})
    queue = grand.get("evidence_gap_queue") or {}
    try:
        updated = resolve_gap_task(queue, task_id=task_id, resolution=resolution, evidence_id=data.get("evidence_id"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    grand["evidence_gap_queue"] = updated
    result.setdefault("web_bridge", {})["evidence_gap_queue"] = updated
    _save_run(run_id, result)
    TASKS.complete(run_id, result)
    return jsonify({"ok": True, "evidence_gap_queue": updated})


@app.route("/api/judge/<run_id>/blind-review", methods=["GET", "POST"])
def blind_review(run_id: str):
    result = _load_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    grand = result.setdefault("grand_judge", {})
    packet = grand.get("blind_cross_validation") or {}
    if request.method == "GET":
        return jsonify(packet or {"schema": "blind_cross_validation.v1", "status": "not_available"})

    data = request.get_json(silent=True) or {}
    reviews = data.get("reviews") or []
    if not isinstance(reviews, list):
        return jsonify({"error": "reviews must be a list"}), 400
    aggregate = aggregate_blind_reviews(reviews, threshold=float(data.get("threshold") or packet.get("threshold") or 0.67))
    packet["reviews"] = reviews
    packet["result"] = aggregate
    packet["status"] = aggregate.get("status")
    grand["blind_cross_validation"] = packet
    result.setdefault("web_bridge", {})["blind_cross_validation"] = packet
    _save_run(run_id, result)
    TASKS.complete(run_id, result)
    return jsonify({"ok": True, "blind_cross_validation": packet})


@app.route("/api/judge/<run_id>/human-review", methods=["POST"])
def human_review(run_id: str):
    result = _load_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    data = request.get_json(silent=True) or {}
    grand = result.setdefault("grand_judge", {})
    certification_hash = str(grand.get("certification_hash") or grand.get("replay_ledger_hash") or "")
    try:
        signature = sign_human_review(
            run_id=run_id,
            certification_hash=certification_hash,
            reviewer=str(data.get("reviewer") or "human_reviewer"),
            decision=str(data.get("decision") or "conditional"),
            reason=str(data.get("reason") or ""),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    grand["human_review_signature"] = signature
    grand["human_review_status"] = human_review_status(grand)
    result.setdefault("web_bridge", {})["human_review_status"] = grand["human_review_status"]
    if grand.get("eval_case"):
        grand["eval_case"]["human_label"] = {
            "decision": signature["decision"],
            "signature_hash": signature["signature_hash"],
        }
    _save_run(run_id, result)
    TASKS.complete(run_id, result)
    return jsonify({"ok": True, "human_review_signature": signature, "human_review_status": grand["human_review_status"]})


@app.route("/api/judge/<run_id>/trace")
def run_trace(run_id: str):
    trace = load_trace(_trace_path(run_id))
    if not trace:
        result = _load_run(run_id)
        if result and result.get("execution_trace"):
            return jsonify(result["execution_trace"])
        return jsonify({"error": "trace not found"}), 404
    return jsonify(trace)


@app.route("/api/judge/<run_id>/progress")
def progress_sse(run_id: str):
    def generate():
        last_payload = None
        for _ in range(360):
            status = TASKS.get_status(run_id)
            if not status:
                payload = {"run_id": run_id, "status": "missing", "progress": 0, "current_step": "任务不存在"}
            else:
                payload = status
            encoded = json.dumps(payload, ensure_ascii=False)
            if encoded != last_payload:
                yield f"data: {encoded}\n\n"
                last_payload = encoded
            if payload.get("status") in {"complete", "failed", "cancelled", "missing"}:
                break
            time.sleep(1)

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/history")
def history():
    status_filter = request.args.get("status")
    limit = int(request.args.get("limit", "30"))
    return jsonify({"runs": TASKS.list_tasks(status=status_filter, limit=limit)})


@app.route("/api/seat-scoreboard")
def seat_scoreboard():
    limit = max(1, min(200, int(request.args.get("limit", "80"))))
    verdicts = list(_iter_saved_verdicts(limit=limit))
    try:
        bridge = bridge_status()
    except Exception:
        bridge = {"seats": [], "seat_browser_matrix": []}
    return jsonify(_build_seat_scoreboard(verdicts=verdicts, bridge=bridge))


@app.route("/api/evals/export")
def evals_export():
    limit = max(1, min(500, int(request.args.get("limit", "200"))))
    verdicts = list(_iter_saved_verdicts(limit=limit))
    return jsonify(collect_eval_cases(verdicts=verdicts, limit=limit))


@app.route("/api/history/<run_id>")
def history_detail(run_id: str):
    result = _load_run(run_id)
    if result:
        return jsonify(result)
    status = TASKS.get_status(run_id)
    if status:
        return jsonify(status)
    return jsonify({"error": "Run not found"}), 404


@app.route("/api/judge/<run_id>/cancel", methods=["POST"])
def cancel(run_id: str):
    return jsonify({"ok": TASKS.cancel(run_id)})


@app.route("/view")
def secure_view():
    tid = request.args.get("tid", "")
    exp = request.args.get("exp", "")
    sig = request.args.get("sig", "")
    if not verify_secure_view(tid, exp, sig):
        return Response("Link expired or invalid", status=403)
    result = _load_run(tid)
    if not result:
        return Response("Verdict not found", status=404)
    trace = load_trace(_trace_path(tid))
    if trace:
        result = dict(result)
        result["execution_trace"] = trace
    return Response(_render_html_report(result), mimetype="text/html")


def _iter_saved_verdicts(limit: int = 80):
    files = sorted(RUNS_DIR.glob("*/verdict.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in files[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            yield data


def _build_seat_scoreboard(verdicts: list[dict[str, Any]], bridge: dict[str, Any] | None = None) -> dict[str, Any]:
    bridge = bridge or {}
    bridge_by_id = {str(item.get("id")): item for item in bridge.get("seats", [])}
    matrix_by_id = {str(item.get("seat")): item for item in bridge.get("seat_browser_matrix", [])}
    rows: dict[str, dict[str, Any]] = {}
    for seat, persona in SEAT_PERSONAS.items():
        bridge_seat = bridge_by_id.get(seat, {})
        mapped = matrix_by_id.get(seat, {})
        channel = mapped.get("channel") or bridge_seat.get("channel") or "local"
        rows[seat] = {
            "seat": seat,
            "seat_name": persona["name"],
            "mbti": persona["mbti"],
            "provider": mapped.get("provider") or bridge_seat.get("provider") or persona["name"],
            "channel": channel,
            "target": mapped.get("target") or bridge_seat.get("browser_label") or bridge_seat.get("url") or "-",
            "ready": bool((mapped.get("ready") if mapped else None) or bridge_seat.get("ready")),
            "history": [],
            "run_count": 0,
            "scored_run_count": 0,
            "success_count": 0,
            "failure_count": 0,
        }

    for verdict in verdicts:
        run_id = str(verdict.get("run_id") or "")
        run_meta = {
            "run_id": run_id,
            "question": verdict.get("question", ""),
            "mode": verdict.get("mode", ""),
            "created_at": verdict.get("created_at"),
            "view_url": verdict.get("view_url"),
        }
        round_scores = _round_scores_by_seat(verdict)
        raw_by_seat = {
            str(item.get("seat")): item
            for item in ((verdict.get("web_bridge") or {}).get("raw_results") or [])
        }
        touched: set[str] = set()
        for item in verdict.get("seat_scores", []) or []:
            seat = str(item.get("seat") or "")
            if seat not in rows:
                continue
            touched.add(seat)
            score = _safe_float(item.get("average_score"))
            raw = raw_by_seat.get(seat, {})
            entry = {
                **run_meta,
                "score": score,
                "claims_count": int(item.get("claims_count", 0) or 0),
                "ok": bool(raw.get("ok", True)),
                "round_scores": round_scores.get(seat, {}),
            }
            rows[seat]["history"].append(entry)
        for seat, raw in raw_by_seat.items():
            if seat not in rows or seat in touched:
                continue
            rows[seat]["history"].append({
                **run_meta,
                "score": None,
                "claims_count": 0,
                "ok": bool(raw.get("ok")),
                "round_scores": round_scores.get(seat, {}),
                "error": raw.get("error"),
            })

    for seat, row in rows.items():
        history = row["history"]
        scores = [float(item["score"]) for item in history if item.get("score") is not None]
        row["run_count"] = len(history)
        row["scored_run_count"] = len(scores)
        row["success_count"] = sum(1 for item in history if item.get("ok"))
        row["failure_count"] = sum(1 for item in history if item.get("ok") is False)
        row["latest_run"] = history[0] if history else None
        row["latest_score"] = round(scores[0], 4) if scores else None
        row["average_score"] = round(sum(scores) / len(scores), 4) if scores else None
        row["q_avg"] = row["average_score"]
        row["k_avg"] = _average_round(history, "raw_answer")
        row["c_avg"] = _average_round(history, "peer_review")
        row["r_stability"] = round(row["success_count"] / len(history), 4) if history else (1.0 if row.get("ready") else 0.0)
        row["t_tenure"] = round(min(0.35, 0.18 + len(history) * 0.03), 4) if history else None
        row["recent_scores"] = [
            {"run_id": item.get("run_id"), "score": item.get("score"), "mode": item.get("mode")}
            for item in history[:6]
        ]

    sorted_rows = sorted(
        rows.values(),
        key=lambda item: (1 if item.get("average_score") is None else -float(item.get("average_score")), item["seat_name"]),
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_considered": len(verdicts),
        "seats": sorted_rows,
    }


def _round_scores_by_seat(verdict: dict[str, Any]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for round_item in ((verdict.get("web_bridge") or {}).get("score_rounds") or []):
        phase = str(round_item.get("id") or "")
        if not phase:
            continue
        for row in round_item.get("seat_scores", []) or []:
            seat = str(row.get("seat") or "")
            if not seat:
                continue
            result.setdefault(seat, {})[phase] = _safe_float(row.get("average_score"))
    return result


def _average_round(history: list[dict[str, Any]], phase: str) -> float | None:
    values = [
        float((item.get("round_scores") or {}).get(phase))
        for item in history
        if (item.get("round_scores") or {}).get(phase) is not None
    ]
    return round(sum(values) / len(values), 4) if values else None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _compact_report_text(value: Any, limit: int = 360) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _render_collection_summary(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    requested = int(bridge.get("requested_count") or len(raw_results) or result.get("seat_count") or 0)
    ok_count = int(bridge.get("ok_count") if bridge.get("ok_count") is not None else sum(1 for item in raw_results if item.get("ok")))
    failed_count = int(
        bridge.get("failed_count")
        if bridge.get("failed_count") is not None
        else sum(1 for item in raw_results if not item.get("ok"))
    )
    pending_count = sum(1 for item in raw_results if _is_supplementable_result(item))
    hard_failed = max(0, failed_count - pending_count)
    collection_complete = bridge.get("collection_complete")
    if collection_complete is None:
        complete = not bridge or (requested > 0 and ok_count == requested and failed_count == 0)
    else:
        complete = bool(collection_complete)
    status = "完整收集" if complete else ("部分收集，待补充" if pending_count and ok_count else "未拿全")
    status_class = "good" if complete else "warn"
    pending_label = "待补充/失败" if pending_count else "失败席位"
    pending_text = f"{pending_count}/{hard_failed}" if pending_count else str(failed_count)
    return (
        '<section class="summary-grid" aria-label="收集状态">'
        f'<div><span>收集状态</span><strong class="{status_class}">{html.escape(status)}</strong></div>'
        f"<div><span>完成席位</span><strong>{ok_count}/{requested}</strong></div>"
        f"<div><span>{html.escape(pending_label)}</span><strong>{html.escape(pending_text)}</strong></div>"
        f"<div><span>置信度</span><strong>{html.escape(str(result.get('confidence', 0)))}%</strong></div>"
        "</section>"
    )


def _render_seat_answers(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    if not raw_results:
        return ""

    score_by_seat = {str(item.get("seat")): item for item in result.get("seat_scores", [])}
    cards: list[str] = []
    for item in raw_results:
        seat = str(item.get("seat") or "")
        seat_name = str(item.get("seat_name") or score_by_seat.get(seat, {}).get("seat_name") or seat)
        ok = bool(item.get("ok"))
        response = str(item.get("response") or "")
        error = item.get("error") or {}
        retry_attempts = int(item.get("retry_attempts") or 0)
        retry_note = f" · 补跑 {retry_attempts} 次" if retry_attempts else ""
        score = score_by_seat.get(seat, {})
        score_text = "-"
        if score:
            try:
                score_text = f"{float(score.get('average_score', 0.0)):.3f}"
            except Exception:
                score_text = str(score.get("average_score", "-"))
        if ok:
            status = "已返回"
            status_class = "is-ok"
            state_class = "good"
            detail = html.escape(response or "该席位返回了空回答。")
            recovered = " · 补跑追回" if item.get("recovered_by_retry") else ""
            meta = f"{len(response)} 字符 · 用时 {item.get('elapsed_seconds', '-') }s · 分数 {score_text}{retry_note}{recovered}"
            preview = _compact_report_text(response, 180)
        else:
            pending = _is_supplementable_result(item)
            status = "待补充" if pending else "未完成"
            status_class = "is-pending" if pending else "is-failed"
            state_class = "warn" if pending else "bad"
            code = str(error.get("code") or "unknown")
            message = str(error.get("message") or "No response captured.")
            history = item.get("retry_history") or []
            history_text = ""
            if history:
                history_text = "\n\n补跑历史:\n" + "\n".join(
                    f"- attempt {entry.get('attempt')}: {entry.get('error_code') or 'ok'} {entry.get('error_message') or ''}".rstrip()
                    for entry in history
                )
            detail = html.escape(f"{code}: {message}{history_text}")
            meta = f"{code} · 分数 {score_text}{retry_note}"
            preview = _compact_report_text(message, 180)
        open_attr = " open" if not ok else ""
        cards.append(
            f'<details class="seat-answer {status_class}" id="seat-answer-{html.escape(seat)}"{open_attr}>'
            "<summary>"
            f"<strong>{html.escape(seat_name)}</strong>"
            f'<span class="seat-state {state_class}">{html.escape(status)}</span>'
            f'<span class="seat-meta">{html.escape(meta)}</span>'
            "</summary>"
            f'<p class="seat-preview">{html.escape(preview)}</p>'
            f'<pre class="answer">{detail}</pre>'
            "</details>"
        )
    return (
        '<section class="band" id="seat-answers">'
        '<div class="section-head"><div>'
        "<h2>席位完整回答</h2>"
        "<p class=\"muted\">成功席位默认收起，慢席位和失败席位默认展开；底层状态会保留，但不会混入最终判词。</p>"
        '</div><div class="mini-actions">'
        '<button type="button" data-seat-action="expand">全部展开</button>'
        '<button type="button" data-seat-action="collapse">全部收起</button>'
        "</div></div>"
        f'<div class="seat-answer-list">{"".join(cards)}</div>'
        "</section>"
    )


def _render_mentor_supplements(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    supplements = bridge.get("mentor_supplements") or []
    if not supplements:
        return ""

    cards: list[str] = []
    for item in supplements:
        seat = str(item.get("seat") or "")
        seat_name = str(item.get("seat_name") or seat)
        ok = bool(item.get("ok"))
        questions = item.get("source_questions") or []
        question_items = "".join(f"<li>{html.escape(str(q))}</li>" for q in questions) or "<li>该席位未显式返回问题，系统使用了兜底共振问题。</li>"
        response = str(item.get("response") or "")
        error = item.get("error") or {}
        status = "已补充" if ok else "未完成"
        status_class = "is-ok" if ok else "is-failed"
        state_class = "good" if ok else "bad"
        detail = html.escape(response) if ok else html.escape(f"{error.get('code', 'unknown')}: {error.get('message', 'No response captured.')}")
        preview = _compact_report_text(response if ok else error.get("message", ""), 180)
        cards.append(
            f'<details class="seat-answer {status_class}" id="mentor-supplement-{html.escape(seat)}"{"" if ok else " open"}>'
            "<summary>"
            f"<strong>{html.escape(seat_name)}</strong>"
            f'<span class="seat-state {state_class}">{html.escape(status)}</span>'
            f'<span class="seat-meta">{len(questions)} 个问题 · {html.escape(str(item.get("elapsed_seconds", "-")))}s</span>'
            "</summary>"
            f'<ul class="compact-list">{question_items}</ul>'
            f'<p class="seat-preview">{html.escape(preview)}</p>'
            f'<pre class="answer">{detail}</pre>'
            "</details>"
        )
    ok_count = sum(1 for item in supplements if item.get("ok"))
    question_count = sum(len(item.get("source_questions") or []) for item in supplements)
    return (
        '<section class="band" id="mentor-supplements">'
        '<div class="section-head"><div>'
        "<h2>共振提问与二轮方案</h2>"
        f'<p class="muted">每个模型先提出补强问题，再带入用户角色回答自己的问题。已回收 {ok_count}/{len(supplements)} 席，问题 {question_count} 个。</p>'
        "</div></div>"
        f'<div class="seat-answer-list">{"".join(cards)}</div>'
        "</section>"
    )


def _render_judge_answer(result: dict[str, Any]) -> str:
    judge = result.get("judge_answer") or {}
    baseline = result.get("single_judge_baseline") or {}
    if not judge and not baseline:
        return ""
    label = str(judge.get("label") or baseline.get("label") or "AI Judge 法官答案")
    limits = "".join(f"<li>{html.escape(str(item))}</li>" for item in judge.get("limits", []))
    agreements = ", ".join(str(item) for item in judge.get("agreements", [])[:8]) or "-"
    comparison_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('metric', '')))}</td>"
        f"<td>{html.escape(str(item.get('single_judge', '')))}</td>"
        f"<td>{html.escape(str(item.get('council', '')))}</td>"
        "</tr>"
        for item in baseline.get("comparison", [])
    )
    return (
        '<section class="band" id="judge-answer">'
        f"<h2>{html.escape(label)}与单模型对照</h2>"
        f"<p>{html.escape(str(judge.get('answer', '暂无法官汇总答案。')))}</p>"
        '<section class="summary-grid compact" aria-label="法官基准">'
        f"<div><span>法官单模型分</span><strong>{html.escape(str(baseline.get('score', '-')))}</strong></div>"
        f"<div><span>单模型层级</span><strong>{html.escape(str(baseline.get('tier', '-')))}</strong></div>"
        f"<div><span>议会均分</span><strong>{html.escape(str(baseline.get('council_average_score', result.get('average_score', '-'))))}</strong></div>"
        f"<div><span>差值</span><strong>{html.escape(str(baseline.get('delta_vs_council', '-')))}</strong></div>"
        "</section>"
        f"<p><strong>主导立场：</strong>{html.escape(str(judge.get('dominant_stance', '-')))}</p>"
        f"<p><strong>主要共识：</strong>{html.escape(agreements)}</p>"
        f"<ul class=\"compact-list\">{limits}</ul>"
        "<h3>单一法官 vs 多席位议会</h3>"
        "<table><thead><tr><th>维度</th><th>AI Judge 单模型</th><th>AI Judge 议会</th></tr></thead>"
        f"<tbody>{comparison_rows}</tbody></table>"
        "</section>"
    )


def _render_score_rounds(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    rounds = bridge.get("score_rounds") or []
    if not rounds:
        return ""
    round_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', item.get('id', ''))))}</td>"
        f"<td>{html.escape(str(item.get('claim_count', 0)))}</td>"
        f"<td>{html.escape(_format_report_score(item.get('average_score')))}</td>"
        f"<td>{html.escape(_round_seat_score_text(item.get('seat_scores', [])))}</td>"
        "</tr>"
        for item in rounds
    )
    details = "".join(_render_round_detail(item) for item in rounds if item.get("top_claims"))
    return (
        '<section class="band" id="score-rounds">'
        "<h2>每轮评分表现</h2>"
        '<p class="muted">这里显示评分体系的实际运转：原始答案、答案总结、席位互评分别怎样进入 claim 评分。</p>'
        "<table><thead><tr><th>评分轮次</th><th>Claims</th><th>均分</th><th>席位表现</th></tr></thead>"
        f"<tbody>{round_rows}</tbody></table>"
        f"{details}"
        "</section>"
    )


def _render_round_detail(round_item: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('seat_name', item.get('seat', ''))))}</td>"
        f"<td>{float(item.get('score', 0.0)):.3f}</td>"
        f"<td>{html.escape(str(item.get('tier', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('claim', ''), 220))}</td>"
        "</tr>"
        for item in round_item.get("top_claims", [])[:8]
    )
    return (
        "<details class=\"nested\"><summary>"
        f"{html.escape(str(round_item.get('label', '评分轮次')))} Top Claims"
        "</summary>"
        "<table><thead><tr><th>席位</th><th>分数</th><th>层级</th><th>Claim</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></details>"
    )


def _render_seat_digest(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    digest = bridge.get("seat_answer_digest") or []
    if not digest:
        return ""
    rows = "".join(
        "<tr>"
        f"<td><a href=\"#seat-answer-{html.escape(str(item.get('seat', '')))}\">{html.escape(str(item.get('seat_name', item.get('seat', ''))))}</a></td>"
        f"<td>{html.escape(str(item.get('status', '-')))}</td>"
        f"<td>{html.escape(_format_report_score(item.get('score')))}</td>"
        f"<td>{html.escape(str(item.get('stance', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text('；'.join(str(x) for x in item.get('pros', [])), 220))}</td>"
        f"<td>{html.escape(_compact_report_text('；'.join(str(x) for x in item.get('cons', [])), 220))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('answer_preview', ''), 180))}</td>"
        "</tr>"
        for item in digest
    )
    return (
        '<section class="band" id="seat-digest">'
        "<h2>每个模型的回答入口、优缺点</h2>"
        '<p class="muted">这一层是索引：点席位名可跳到完整原文，优缺点来自席位画像、证据密度、互评和评分结果。</p>'
        "<table><thead><tr><th>席位</th><th>状态</th><th>均分</th><th>立场</th><th>优点</th><th>缺点</th><th>回答预览</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "</section>"
    )


def _round_seat_score_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "-"
    return " / ".join(
        f"{row.get('seat_name', row.get('seat'))}:{float(row.get('average_score', 0.0)):.3f}"
        for row in rows[:6]
    )


def _format_report_score(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.3f}"
    except Exception:
        return str(value)


def _render_deliberation(result: dict[str, Any]) -> str:
    bridge = result.get("web_bridge") or {}
    deliberation = bridge.get("deliberation") or {}
    if not deliberation:
        return ""

    stance = deliberation.get("stance_distribution") or {}
    stance_text = " · ".join(f"{key} {value}" for key, value in stance.items()) or "-"
    agreements = ", ".join(str(item) for item in deliberation.get("agreements", [])[:8]) or "-"
    disagreements = "".join(
        f"<li>{html.escape(str(item))}</li>"
        for item in deliberation.get("disagreements", [])[:8]
    ) or "<li>暂无明显分歧。</li>"

    summary_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('seat_name', item.get('seat'))))}</td>"
        f"<td>{html.escape(str(item.get('stance', '-')))}</td>"
        f"<td>{float(item.get('quality', 0.0)):.3f}</td>"
        f"<td>{html.escape(str(item.get('avg_peer_score', '-')))}</td>"
        f"<td>{int(item.get('review_count', 0))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('summary', ''), 160))}</td>"
        "</tr>"
        for item in deliberation.get("answer_summaries", [])
    )
    review_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('reviewer_name', item.get('reviewer'))))}</td>"
        f"<td>{html.escape(str(item.get('target_name', item.get('target'))))}</td>"
        f"<td>{float(item.get('score', 0.0)):.3f}</td>"
        f"<td>{html.escape(str(item.get('label', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('comment', ''), 220))}</td>"
        "</tr>"
        for item in deliberation.get("peer_reviews", [])[:80]
    )
    pipeline = bridge.get("pipeline") or {}
    phase_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', item.get('id', ''))))}</td>"
        f"<td>{html.escape(str(item.get('count', '-')))}</td>"
        "</tr>"
        for item in pipeline.get("phases", [])
    )
    return (
        '<section class="band" id="deliberation">'
        '<div class="section-head"><div>'
        "<h2>答案总结、互评与评分链路</h2>"
        '<p class="muted">这是网页席位返回后的 AI Judge 底层审议阶段：先压缩答案，再互评，最后进入评分引擎。</p>'
        "</div></div>"
        '<section class="summary-grid compact" aria-label="审议状态">'
        f"<div><span>互评轮次</span><strong>{int(deliberation.get('peer_review_count', 0))}</strong></div>"
        f"<div><span>摘要 Claims</span><strong>{int(deliberation.get('summary_claim_count', 0))}</strong></div>"
        f"<div><span>审议 Claims</span><strong>{int(deliberation.get('claim_count', 0))}</strong></div>"
        f"<div><span>评分引擎</span><strong>{html.escape(str(pipeline.get('scoring_engine', 'score_jury_v2')).split('.')[-1])}</strong></div>"
        "</section>"
        f"<p><strong>立场分布：</strong>{html.escape(stance_text)}</p>"
        f"<p><strong>主要共识词：</strong>{html.escape(agreements)}</p>"
        f'<ul class="compact-list">{disagreements}</ul>'
        "<h3>底层阶段</h3>"
        f"<table><thead><tr><th>阶段</th><th>数量</th></tr></thead><tbody>{phase_rows}</tbody></table>"
        "<h3>席位答案摘要</h3>"
        "<table><thead><tr><th>席位</th><th>立场</th><th>质量</th><th>互评分</th><th>互评数</th><th>摘要</th></tr></thead>"
        f"<tbody>{summary_rows}</tbody></table>"
        "<details class=\"nested\"><summary>查看互评矩阵</summary>"
        "<table><thead><tr><th>评审席位</th><th>被评席位</th><th>分数</th><th>标签</th><th>判断</th></tr></thead>"
        f"<tbody>{review_rows}</tbody></table></details>"
        "</section>"
    )


def _render_citation_verification(result: dict[str, Any]) -> str:
    report = result.get("grand_judge") or {}
    bridge = result.get("web_bridge") or {}
    citation = report.get("citation_verification") or bridge.get("citation_verification") or {}
    ledger = report.get("replay_ledger") or bridge.get("replay_ledger") or []
    if not citation and not ledger:
        return ""

    counts = citation.get("counts") or {}
    status = str(citation.get("overall_status") or "unverifiable")
    certification_id = str(citation.get("certification_id") or bridge.get("certification_id") or report.get("certification_id") or "-")
    ledger_hash = str(citation.get("replay_ledger_hash") or bridge.get("replay_ledger_hash") or report.get("replay_ledger_hash") or "-")
    gap_suggestions = (report.get("evidence_gap_suggestions") or bridge.get("evidence_gap_suggestions") or {}).get("suggestions") or []
    rows: list[str] = []
    for entry in ledger:
        rows.extend(_citation_rows_for_entry(entry, layer="原始回答", report_key="citation_verification"))
        rows.extend(_citation_rows_for_entry(entry, layer="导师补充", report_key="mentor_citation_verification"))
    if not rows:
        rows.append("<tr><td colspan=\"7\">暂无可展示引用行。</td></tr>")

    gap_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('citation_id', '-')))}</td>"
        f"<td>{html.escape(str(item.get('mentor_level', '-')))}</td>"
        f"<td>{html.escape(str(item.get('status', '-')))}</td>"
        f"<td>{html.escape(str(item.get('suggested_action', '-')))}</td>"
        "</tr>"
        for item in gap_suggestions[:12]
    ) or "<tr><td colspan=\"4\">暂无证据缺口建议。</td></tr>"

    return (
        '<section class="band" id="citation-verification">'
        '<div class="section-head"><div>'
        "<h2>引用验证 MVP</h2>"
        '<p class="muted">Grand Judge 只编排验证，不改写模型原文。原始回答、导师补充、外部证据三层隔离。</p>'
        "</div></div>"
        '<section class="summary-grid compact" aria-label="引用验证状态">'
        f"<div><span>Certification ID</span><strong>{html.escape(certification_id)}</strong></div>"
        f"<div><span>整体状态</span><strong class=\"{_citation_status_class(status)}\">{html.escape(_citation_status_label(status))}</strong></div>"
        f"<div><span>引用条目</span><strong>{html.escape(str(citation.get('item_count', 0)))}</strong></div>"
        f"<div><span>外部证据</span><strong>{html.escape(str(citation.get('external_evidence_count', 0)))}</strong></div>"
        "</section>"
        f"<p class=\"muted\"><strong>unverifiable 说明：</strong>{html.escape(str(citation.get('unverifiable_explanation') or 'unverifiable 不是 false。'))}</p>"
        f"<p class=\"muted\">Replay Ledger Hash: <code>{html.escape(ledger_hash[:24])}</code> · verified {counts.get('verified', 0)} / weak {counts.get('weakly_verified', 0)} / irrelevant {counts.get('irrelevant', 0)} / unverifiable {counts.get('unverifiable', 0)} / contradicted {counts.get('contradicted', 0)}</p>"
        "<table><thead><tr><th>席位</th><th>层</th><th>Citation</th><th>状态</th><th>相关性</th><th>原因</th><th>证据</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<details class=\"nested\"><summary>Replay Ledger 与证据缺口建议</summary>"
        "<p class=\"muted\">Ledger 记录原始回答哈希、导师补充哈希、不可验证原因和验证时间戳；完整原文在“席位完整回答”和“共振二轮”中查看。</p>"
        "<table><thead><tr><th>Citation</th><th>导师等级</th><th>状态</th><th>建议动作</th></tr></thead>"
        f"<tbody>{gap_rows}</tbody></table></details>"
        "</section>"
    )


def _citation_rows_for_entry(entry: dict[str, Any], *, layer: str, report_key: str) -> list[str]:
    report = entry.get(report_key) or {}
    rows: list[str] = []
    for item in report.get("items") or []:
        evidence = item.get("matched_evidence") or {}
        evidence_text = evidence.get("title") or evidence.get("url") or evidence.get("evidence_id") or "-"
        status = str(item.get("status") or "unverifiable")
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(entry.get('seat_name') or entry.get('seat') or '-'))}</td>"
            f"<td>{html.escape(layer)}</td>"
            f"<td>{html.escape(_compact_report_text(item.get('raw', '-'), 120))}</td>"
            f"<td><span class=\"status-pill {_citation_status_class(status)}\">{html.escape(_citation_status_label(status))}</span></td>"
            f"<td>{html.escape(_format_report_score(item.get('relevance_score')))}</td>"
            f"<td>{html.escape(_compact_report_text(item.get('reason', ''), 180))}</td>"
            f"<td>{html.escape(_compact_report_text(evidence_text, 160))}</td>"
            "</tr>"
        )
    return rows


def _citation_status_label(status: str) -> str:
    return {
        "verified": "verified",
        "weakly_verified": "weakly verified",
        "irrelevant": "irrelevant",
        "unverifiable": "unverifiable",
        "contradicted": "contradicted",
    }.get(status, status)


def _citation_status_class(status: str) -> str:
    return {
        "verified": "good",
        "weakly_verified": "warn",
        "irrelevant": "warn",
        "unverifiable": "warn",
        "contradicted": "bad",
    }.get(status, "warn")


def _render_evidence_os(result: dict[str, Any]) -> str:
    grand = result.get("grand_judge") or {}
    if not grand:
        return ""
    broker = grand.get("evidence_broker") or {}
    metrics = grand.get("evidence_quality_metrics") or {}
    blind = grand.get("blind_cross_validation") or {}
    queue = grand.get("evidence_gap_queue") or {}
    human = grand.get("human_review_status") or {}
    eval_case = grand.get("eval_case") or {}
    broker_counts = broker.get("counts") or {}
    blind_result = blind.get("result") or {}
    evidence_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('id', '-')))}</td>"
        f"<td>{html.escape(str(item.get('source_layer', '-')))}</td>"
        f"<td>{html.escape(str(item.get('retrieval_state', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('title') or item.get('url') or item.get('raw_source') or '-', 180))}</td>"
        "</tr>"
        for item in (broker.get("items") or [])[:16]
    ) or "<tr><td colspan=\"4\">暂无外部证据。</td></tr>"
    gap_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('task_id', '-')))}</td>"
        f"<td>{html.escape(str(item.get('priority', '-')))}</td>"
        f"<td>{html.escape(str(item.get('queue_status', '-')))}</td>"
        f"<td>{html.escape(_compact_report_text(item.get('suggested_action', '-'), 220))}</td>"
        "</tr>"
        for item in (queue.get("tasks") or [])[:12]
    ) or "<tr><td colspan=\"4\">暂无证据缺口任务。</td></tr>"
    return (
        '<section class="band" id="evidence-os">'
        '<div class="section-head"><div>'
        "<h2>Evidence OS</h2>"
        '<p class="muted">硬证据层、匿名双盲验证、证据缺口队列、人工签名和 eval case 都在这里汇总。</p>'
        "</div></div>"
        '<section class="summary-grid compact" aria-label="Evidence OS 状态">'
        f"<div><span>Groundedness</span><strong>{html.escape(str(metrics.get('groundedness_proxy', '-')))}</strong></div>"
        f"<div><span>Trust Gate</span><strong class=\"{_evidence_gate_class(str(metrics.get('trust_gate', '')))}\">{html.escape(str(metrics.get('trust_gate', '-')))}</strong></div>"
        f"<div><span>双盲状态</span><strong>{html.escape(str(blind_result.get('status') or blind.get('status') or '-'))}</strong></div>"
        f"<div><span>人工签名</span><strong>{html.escape(str(human.get('status', '-')))}</strong></div>"
        "</section>"
        f"<p class=\"muted\">Evidence Broker: user {broker_counts.get('user_supplied', 0)} / fetched {broker_counts.get('network_fetch', 0)} / candidate {broker_counts.get('candidate_source', 0)}。Eval Case: <code>{html.escape(str(eval_case.get('case_id', '-')))}</code></p>"
        "<details class=\"nested\"><summary>查看 Evidence Broker 来源</summary>"
        "<table><thead><tr><th>ID</th><th>来源层</th><th>检索状态</th><th>标题/URL</th></tr></thead>"
        f"<tbody>{evidence_rows}</tbody></table></details>"
        "<details class=\"nested\"><summary>查看证据缺口队列</summary>"
        "<table><thead><tr><th>任务</th><th>优先级</th><th>状态</th><th>建议动作</th></tr></thead>"
        f"<tbody>{gap_rows}</tbody></table></details>"
        "</section>"
    )


def _evidence_gate_class(gate: str) -> str:
    if gate == "pass":
        return "good"
    if gate == "blocked_contradiction":
        return "bad"
    return "warn"


def _render_html_report(result: dict[str, Any]) -> str:
    reasons = "".join(
        f"<li>{html.escape(_compact_report_text(r, 260))}</li>"
        for r in result.get("reasons", [])
    ) or "<li>暂无关键理由。</li>"
    steps = "".join(f"<li>{html.escape(str(s))}</li>" for s in result.get("next_steps", [])) or "<li>暂无建议行动。</li>"
    prompt_flow = result.get("prompt_flow") or {}
    execution_plan = result.get("execution_plan") or {}
    prompt_html = ""
    if prompt_flow:
        assumptions = "".join(f"<li>{html.escape(str(item))}</li>" for item in prompt_flow.get("assumptions_to_check", []))
        prompt_html = (
            "<details class=\"band\"><summary><h2>本地共振与专业提示词</h2></summary>"
            f"<p>{html.escape(str(prompt_flow.get('quick_response', '')))}</p>"
            f"<h3>专业提示词</h3><pre>{html.escape(str(prompt_flow.get('professional_prompt', '')))}</pre>"
            f"<h3>需要核查的假设</h3><ul>{assumptions}</ul>"
            "</details>"
        )
    blocked_html = ""
    if execution_plan:
        blocked_rows = "".join(
            "<tr>"
            f"<td>{html.escape(str(item.get('seat_name', item.get('seat'))))}</td>"
            f"<td>{html.escape(str(item.get('driver', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            f"<td>{html.escape(str(item.get('calibration_status', '')))}</td>"
            "</tr>"
            for item in execution_plan.get("blocked_seats", [])
        )
        blocked_html = (
            "<details class=\"band\"><summary><h2>执行驱动</h2></summary>"
            f"<p>{html.escape(str(execution_plan.get('message', '')))}</p>"
            f"<p>可运行席位：{html.escape(', '.join(execution_plan.get('runnable_seats', [])) or '-')}</p>"
            "<table><thead><tr><th>阻断席位</th><th>驱动</th><th>原因</th><th>校准</th></tr></thead>"
            f"<tbody>{blocked_rows}</tbody></table></details>"
        )
    trace = result.get("execution_trace") or {}
    trace_html = ""
    if trace.get("events"):
        trace_rows = "".join(
            "<tr>"
            f"<td>{int(event.get('index', 0))}</td>"
            f"<td>{html.escape(str(event.get('phase', '')))}</td>"
            f"<td>{html.escape(str(event.get('action', '')))}</td>"
            f"<td>{html.escape(str(event.get('detail', '')))}</td>"
            f"<td><pre>{html.escape(json.dumps(event.get('data', {}), ensure_ascii=False, indent=2))}</pre></td>"
            "</tr>"
            for event in trace.get("events", [])[:80]
        )
        trace_html = (
            "<details class=\"band\"><summary><h2>底层执行轨迹</h2></summary>"
            "<table><thead><tr><th>#</th><th>Phase</th><th>Action</th><th>Detail</th><th>Data</th></tr></thead>"
            f"<tbody>{trace_rows}</tbody></table></details>"
        )
    seats_html = "".join(
        "<tr>"
        f"<td>{html.escape(str(s.get('seat_name', s.get('seat'))))}</td>"
        f"<td>{html.escape(str(s.get('mbti', '')))}</td>"
        f"<td>{float(s.get('average_score', 0.0)):.3f}</td>"
        f"<td>{int(s.get('claims_count', 0))}</td>"
        "</tr>"
        for s in result.get("seat_scores", [])
    )
    raw_json = html.escape(json.dumps(result, ensure_ascii=False, indent=2))
    collection_html = _render_collection_summary(result)
    judge_answer_html = _render_judge_answer(result)
    score_rounds_html = _render_score_rounds(result)
    seat_digest_html = _render_seat_digest(result)
    seat_answers_html = _render_seat_answers(result)
    mentor_supplements_html = _render_mentor_supplements(result)
    deliberation_html = _render_deliberation(result)
    citation_verification_html = _render_citation_verification(result)
    evidence_os_html = _render_evidence_os(result)
    judge_answer_link = '<a href="#judge-answer">法官答案</a>' if judge_answer_html else ""
    score_rounds_link = '<a href="#score-rounds">评分轮次</a>' if score_rounds_html else ""
    seat_digest_link = '<a href="#seat-digest">模型总览</a>' if seat_digest_html else ""
    seat_answers_link = '<a href="#seat-answers">查看席位回答</a>' if seat_answers_html else ""
    mentor_supplements_link = '<a href="#mentor-supplements">共振二轮</a>' if mentor_supplements_html else ""
    deliberation_link = '<a href="#deliberation">查看互评评分</a>' if deliberation_html else ""
    citation_link = '<a href="#citation-verification">引用验证</a>' if citation_verification_html else ""
    evidence_os_link = '<a href="#evidence-os">Evidence OS</a>' if evidence_os_html else ""
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Judge Verdict</title>
  <style>
    :root {{ color-scheme: dark; --bg:#080b14; --panel:#111827; --soft:#151d2c; --line:#263149; --text:#f4f6fb; --muted:#9aa4b5; --accent:#ffc53d; --green:#36d06f; --red:#ff6868; --blue:#65a8ff; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; margin: 0; background: var(--bg); color: var(--text); letter-spacing: 0; }}
    .nav {{ position: sticky; top: 0; z-index: 2; display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px 24px; background:#0d1425; border-bottom:1px solid var(--line); }}
    .nav a {{ color: var(--text); text-decoration:none; border:1px solid var(--line); border-radius:8px; padding:8px 12px; background:#101622; font-weight:700; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px 20px 52px; }}
    .hero {{ padding: 6px 0 18px; }}
    .badge {{ display: inline-block; padding: 7px 12px; border-radius: 999px; background: var(--accent); color: #111; font-weight: 800; }}
    h1 {{ font-size: clamp(28px, 4vw, 46px); line-height: 1.18; margin: 18px 0 12px; max-width: 980px; }}
    h2 {{ font-size: 18px; margin: 0; }}
    h3 {{ font-size: 14px; margin: 18px 0 8px; color: var(--accent); }}
    p {{ line-height: 1.65; }}
    .question {{ color: var(--muted); max-width: 900px; }}
    .muted {{ color: var(--muted); }}
    .summary-grid {{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:10px; margin: 8px 0 18px; }}
    .summary-grid.compact {{ margin-top:12px; }}
    .summary-grid div {{ border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:14px; }}
    .summary-grid span {{ display:block; color:var(--muted); font-size:12px; margin-bottom:6px; }}
    .summary-grid strong {{ font-size:22px; }}
    .good {{ color: var(--green); }}
    .warn {{ color: var(--accent); }}
    .bad {{ color: var(--red); }}
    .band {{ border: 1px solid var(--line); border-radius: 8px; padding: 18px; margin: 14px 0; background: var(--soft); }}
    .nested {{ margin-top:14px; border:1px solid var(--line); border-radius:8px; background:#101622; padding:12px; }}
    .nested summary {{ cursor:pointer; font-weight:800; }}
    details.band > summary {{ cursor: pointer; list-style: none; display:flex; align-items:center; justify-content:space-between; gap:12px; }}
    details.band > summary::-webkit-details-marker, .seat-answer summary::-webkit-details-marker {{ display:none; }}
    details.band > summary::after {{ content:"展开"; color:var(--muted); font-size:12px; }}
    details.band[open] > summary::after {{ content:"收起"; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }} td, th {{ border-bottom: 1px solid var(--line); padding: 10px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); background:#111827; }}
    pre {{ white-space: pre-wrap; overflow: auto; background: #070b14; padding: 14px; border-radius: 8px; border:1px solid #1f2937; line-height:1.55; }}
    .section-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:12px; }}
    .section-head p {{ margin:8px 0 0; }}
    .mini-actions {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    button {{ color:var(--text); border:1px solid var(--line); border-radius:8px; padding:8px 10px; background:#101622; font-weight:700; cursor:pointer; }}
    button:hover, .actions a:hover, .nav a:hover {{ border-color:var(--accent); }}
    .seat-answer-list {{ display:grid; gap:10px; }}
    .seat-answer {{ border:1px solid var(--line); border-radius:8px; background:#101622; padding:0; }}
    .seat-answer.is-pending {{ border-color:rgba(255,197,61,.65); }}
    .seat-answer.is-failed {{ border-color:rgba(255,104,104,.55); }}
    .seat-answer summary {{ cursor:pointer; display:grid; grid-template-columns:minmax(120px, 1fr) auto auto; gap:10px; align-items:center; padding:14px; }}
    .seat-state {{ font-weight:800; }}
    .seat-meta {{ color:var(--muted); font-size:12px; text-align:right; }}
    .seat-preview {{ margin:0; padding:0 14px 12px; color:var(--muted); }}
    .answer {{ margin:0 14px 14px; max-height:420px; }}
    .compact-list {{ margin:0; padding-left:18px; }}
    .status-pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 8px; font-weight:800; background:#0b1020; }}
    code {{ color:var(--accent); }}
    .actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }}
    .actions a {{ color:var(--text); text-decoration:none; border:1px solid var(--line); border-radius:8px; padding:9px 12px; background:#101622; font-weight:700; }}
    @media (max-width: 760px) {{
      .summary-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
      .section-head {{ display:block; }}
      .mini-actions {{ justify-content:flex-start; margin-top:10px; }}
      .seat-answer summary {{ grid-template-columns:1fr; }}
      .seat-meta {{ text-align:left; }}
      .nav {{ padding:12px 14px; }}
      main {{ padding:22px 14px 42px; }}
    }}
  </style>
</head>
<body>
<nav class="nav">
  <strong>AI Judge 完整报告</strong>
  <a href="/">返回提问</a>
</nav>
<main>
  <section class="hero">
    <p class="badge">{html.escape(str(result.get("mode_emoji", "")))} {html.escape(str(result.get("verdict_label", "")))} · {result.get("confidence", 0)}%</p>
    <h1>{html.escape(str(result.get("one_liner", "AI Judge Verdict")))}</h1>
    <p class="question">{html.escape(str(result.get("question", "")))}</p>
    <div class="actions"><a href="/">返回提问界面</a>{judge_answer_link}{score_rounds_link}{citation_link}{evidence_os_link}{seat_digest_link}{seat_answers_link}{mentor_supplements_link}{deliberation_link}</div>
  </section>
  {collection_html}
  {judge_answer_html}
  {score_rounds_html}
  {citation_verification_html}
  {evidence_os_html}
  <section class="band"><h2>关键理由</h2><ul class="compact-list">{reasons}</ul></section>
  {seat_digest_html}
  {mentor_supplements_html}
  {deliberation_html}
  {seat_answers_html}
  {prompt_html}
  <section class="band"><h2>建议行动</h2><ul class="compact-list">{steps}</ul></section>
  {blocked_html}
  <section class="band"><h2>席位评分</h2><table><thead><tr><th>席位</th><th>MBTI</th><th>均分</th><th>Claims</th></tr></thead><tbody>{seats_html}</tbody></table></section>
  {trace_html}
  <details class="band"><summary><h2>原始 JSON</h2></summary><pre>{raw_json}</pre></details>
</main>
<script>
document.addEventListener("click", (event) => {{
  const button = event.target.closest("[data-seat-action]");
  if (!button) return;
  const shouldOpen = button.dataset.seatAction === "expand";
  document.querySelectorAll(".seat-answer").forEach((node) => {{
    node.open = shouldOpen;
  }});
}});
</script>
</body></html>"""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI Judge v3.6 API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8501, help="Bind port")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()

    print("\n  AI Judge API Server v3.6.0")
    print(f"  http://{args.host}:{args.port}")
    print(f"  {len(SEAT_PERSONAS)} seats available")
    print("  POST /api/judge now runs automatically\n")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
