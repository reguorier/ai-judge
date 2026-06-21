"""AI Judge Output Contract — single source of truth for all report outputs.

Every client (Dashboard, MCP, Codex, Marvis, OpenSpark, Client API) should
call render_contract_report() to get a consistent, schema-validated report.

The contract defines:
- Canonical schema: what fields exist and their types
- normalize(): turn any verdict dict into the canonical shape
- render(): produce html / md / json / compact from the canonical shape

This replaces the 8 independent renderers with 1 normalizer + 1 renderer.
"""

from __future__ import annotations

import html as _html
import json
from dataclasses import dataclass, field
from typing import Any

from core.high_risk_domain_gate import attach_high_risk_domain_gate
from core.required_seat_recovery_queue import build_required_seat_recovery_queue
from product.reporting.incomplete_high_risk_report import (
    build_incomplete_high_risk_report,
    render_incomplete_high_risk_report_html,
    render_incomplete_high_risk_report_markdown,
)

CONTRACT_VERSION = "ai_judge.output_contract.v1"

# ── Canonical sections (order matters) ────────────────────────────────

SECTION_ORDER = [
    "header",
    "verdict",
    "seats",
    "claims",
    "reasons",
    "risks",
    "actions",
    "evidence",
    "audit",
    "trace",
]


# ── Normalizer ────────────────────────────────────────────────────────

def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize any verdict dict into the canonical contract shape.

    Handles:
    - verdict.json (full API output)
    - summary.json (client API output)
    - MCP compact (already reduced)
    - OpenSpark raw results (if they reach here)
    """
    if not isinstance(raw, dict):
        return _empty_contract("invalid input")

    # Already canonical
    if raw.get("contract_version") == CONTRACT_VERSION:
        return _with_high_risk_gate(dict(raw), raw)

    # Extract core fields with safe defaults
    run_id = str(raw.get("run_id") or raw.get("id") or "")
    question = str(raw.get("question") or raw.get("title") or "")
    mode = _normalize_mode(raw.get("mode") or raw.get("mode_label") or "")

    # Verdict
    verdict_str = str(raw.get("verdict") or raw.get("verdict_status") or "unknown")
    verdict_label = str(raw.get("verdict_label") or _verdict_label(verdict_str))
    confidence = _int(raw.get("confidence"), default=0)
    one_liner = str(raw.get("one_liner") or "")

    # Status
    status = str(raw.get("status") or "unknown")

    # Seats
    seats = _extract_seats(raw)

    # Claims
    claims = _extract_claims(raw)

    # Reasons
    reasons = _str_list(raw.get("reasons") or [])

    # Next steps / actions
    actions = _str_list(raw.get("next_steps") or [])

    # Risks (from various sources)
    risks = _extract_risks(raw)

    # Evidence / bridge
    bridge = raw.get("web_bridge") or {}
    evidence = {
        "ok_count": _int(bridge.get("ok_count")),
        "failed_count": _int(bridge.get("failed_count")),
        "requested_count": _int(bridge.get("requested_count")),
        "collection_complete": bool(bridge.get("collection_complete")),
    }
    audit = _extract_audit(raw, bridge)

    # Trace (optional, large)
    trace = raw.get("execution_trace") or {}
    if not isinstance(trace, dict):
        trace = {}

    # View URL
    view_url = str(raw.get("view_url") or "")

    # Timestamps
    created_at = str(raw.get("created_at") or "")

    contract = {
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "question": question,
        "mode": mode,
        "status": status,
        "verdict": verdict_str,
        "verdict_label": verdict_label,
        "confidence": confidence,
        "one_liner": one_liner,
        "seats": seats,
        "claims": claims,
        "reasons": reasons,
        "risks": risks,
        "actions": actions,
        "evidence": evidence,
        "audit": audit,
        "trace": trace,
        "view_url": view_url,
        "created_at": created_at,
    }
    return _with_high_risk_gate(contract, raw)


def _with_high_risk_gate(contract: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    attach_high_risk_domain_gate(contract, source=raw)
    gate = contract.get("high_risk_gate") or {}
    if gate.get("blocked") and gate.get("high_risk_domain"):
        queue = build_required_seat_recovery_queue(contract, gate)
        report = build_incomplete_high_risk_report(contract, gate, queue)
        contract["recovery_queue"] = queue
        contract["high_risk_formal_verdict_blocker_brief"] = report
        contract["incomplete_high_risk_report"] = report
        contract["evidence"]["collection_complete"] = False
        contract["actions"] = report["required_re_run_plan"]
        contract["risks"] = report["cannot_be_concluded"]
    return contract


def _empty_contract(error: str) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": "",
        "question": "",
        "mode": "",
        "status": "error",
        "verdict": "unknown",
        "verdict_label": "",
        "confidence": 0,
        "one_liner": "",
        "seats": [],
        "claims": [],
        "reasons": [],
        "risks": [],
        "actions": [],
        "evidence": {"ok_count": 0, "failed_count": 0, "requested_count": 0, "collection_complete": False},
        "audit": {},
        "trace": {},
        "view_url": "",
        "created_at": "",
        "error": error,
    }


def _normalize_mode(mode: str) -> str:
    mode = mode.strip().lower()
    mapping = {
        "quick_judge": "flash", "quick": "flash", "deep_judge": "strategic",
        "deep": "strategic", "standard_judge": "standard", "council": "strategic",
        "ops_check": "standard",
    }
    return mapping.get(mode, mode) or "strategic"


def _verdict_label(v: str) -> str:
    labels = {"credible": "可信", "conditional": "建议推进但需验证",
              "unverified": "证据不足", "rejected": "不建议采纳"}
    return labels.get(v, v)


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _str_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v if x]
    return []


def _extract_seats(raw: dict) -> list[dict[str, Any]]:
    """Extract seat info from various formats."""
    seats = []

    # From seat_scores (verdict.json format)
    for s in raw.get("seat_scores") or []:
        if isinstance(s, dict):
            seats.append({
                "seat": str(s.get("seat") or s.get("seat_name") or ""),
                "seat_name": str(s.get("seat_name") or s.get("seat") or ""),
                "mbti": str(s.get("mbti") or ""),
                "score": round(float(s.get("average_score") or 0), 4),
                "claims_count": _int(s.get("claims_count")),
                "strength": str(s.get("strength") or ""),
                "weakness": str(s.get("weakness") or ""),
            })

    # From seats list (MCP compact format)
    if not seats:
        for s in raw.get("seats") or []:
            if isinstance(s, dict):
                seats.append({
                    "seat": str(s.get("seat") or s.get("seat_name") or ""),
                    "seat_name": str(s.get("seat_name") or s.get("seat") or ""),
                    "ok": bool(s.get("ok")),
                    "preview": str(s.get("answer_preview") or s.get("preview") or ""),
                })
            elif isinstance(s, str):
                seats.append({"seat": s, "seat_name": s})

    return seats


def _extract_claims(raw: dict) -> list[dict[str, Any]]:
    """Extract claims with scores."""
    claims = []
    for c in raw.get("claims") or []:
        if not isinstance(c, dict):
            continue
        claims.append({
            "seat": str(c.get("_seat") or c.get("seat") or ""),
            "claim_id": str(c.get("claim_id") or ""),
            "claim": str(c.get("claim") or "")[:500],
            "score": round(float(c.get("_score") or c.get("score") or 0), 4),
            "tier": str(c.get("_tier") or c.get("tier") or ""),
            "confidence": round(float(c.get("confidence") or 0), 4),
        })
    return claims


def _extract_risks(raw: dict) -> list[str]:
    """Extract risks from various locations in the verdict."""
    risks = []
    # From final_report
    fr = raw.get("final_report") or {}
    risks.extend(_str_list(fr.get("risks") or []))
    # From closeout_sop
    sop = fr.get("closeout_sop") or {}
    risks.extend(_str_list(sop.get("risks") or []))
    # From judge_answer
    ja = raw.get("judge_answer") or {}
    risks.extend(_str_list(ja.get("limits") or []))
    return risks


def _extract_audit(raw: dict[str, Any], bridge: dict[str, Any]) -> dict[str, Any]:
    """Preserve compact protocol/scoring metadata without raw model answers."""
    if not isinstance(bridge, dict):
        bridge = {}
    noise = raw.get("noise_audit") if isinstance(raw.get("noise_audit"), dict) else bridge.get("noise_audit")
    noise = noise if isinstance(noise, dict) else {}
    stability = raw.get("model_stability") if isinstance(raw.get("model_stability"), dict) else bridge.get("model_stability")
    stability = stability if isinstance(stability, dict) else {}
    plan = bridge.get("three_round_protocol") if isinstance(bridge.get("three_round_protocol"), dict) else {}
    board = bridge.get("information_board") if isinstance(bridge.get("information_board"), dict) else {}
    pipeline = bridge.get("pipeline") if isinstance(bridge.get("pipeline"), dict) else {}
    round2_scheduler = bridge.get("round2_scheduler") if isinstance(bridge.get("round2_scheduler"), dict) else {}
    late_evidence_queue = bridge.get("late_evidence_queue") if isinstance(bridge.get("late_evidence_queue"), list) else []
    scoring = raw.get("scoring_pipeline") if isinstance(raw.get("scoring_pipeline"), dict) else {}
    if not any([plan, board, pipeline, scoring, round2_scheduler, late_evidence_queue, noise, stability]):
        return {}

    governance = bridge.get("governance") if isinstance(bridge.get("governance"), dict) else {}
    return {
        "schema": "ai_judge.output_audit.v1",
        "noise": _compact_noise(noise),
        "model_stability": _compact_model_stability(stability),
        "pipeline": {
            "version": str(pipeline.get("version") or raw.get("engine") or ""),
            "scoring_engine": str(pipeline.get("scoring_engine") or bridge.get("scoring_engine") or ""),
            "phases": _compact_phases(pipeline.get("phases") or []),
        },
        "frame_lock": str(
            ((plan.get("frame_lock") or {}).get("name") if isinstance(plan.get("frame_lock"), dict) else "")
            or governance.get("frame_lock")
            or ""
        ),
        "three_round_protocol": _compact_three_round_plan(plan),
        "information_board": _compact_information_board(board),
        "round2_scheduler": _compact_round2_scheduler(round2_scheduler),
        "late_evidence": _compact_late_evidence_queue(late_evidence_queue),
        "scoring": {
            "schema": "ai_judge.three_round_scoring.v1" if scoring else "",
            "average_score_unweighted": raw.get("average_score_unweighted"),
            "average_score_weighted": raw.get("average_score_weighted"),
            "peach_winners": raw.get("peach_winners") or ((scoring.get("phase3_peach_projection") or {}).get("winners") or []),
            "phase_keys": list(scoring.keys())[:12],
        },
    }


def _compact_model_stability(stability: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(stability, dict) or not stability:
        return {}
    rows = stability.get("profiles") if isinstance(stability.get("profiles"), list) else []
    return {
        "schema": str(stability.get("schema") or "ai_judge.model_stability_profiles.v1"),
        "updated_at": str(stability.get("updated_at") or ""),
        "profile_count": _int(stability.get("profile_count")),
        "profiles": [
            {
                "seat": str(item.get("seat") or ""),
                "seat_name": str(item.get("seat_name") or item.get("seat") or ""),
                "runs_seen": _int(item.get("runs_seen")),
                "stability_score": float(item.get("stability_score") or 0.0),
                "rates": item.get("rates") if isinstance(item.get("rates"), dict) else {},
            }
            for item in rows[:12]
            if isinstance(item, dict)
        ],
    }


def _compact_noise(noise: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(noise, dict) or not noise:
        return {}
    return {
        "schema": str(noise.get("schema") or "ai_judge.noise_audit.v1"),
        "score": _int(noise.get("noise_score") if noise.get("noise_score") is not None else noise.get("score")),
        "level": str(noise.get("noise_level") or noise.get("level") or ""),
        "recommended_action": str(noise.get("recommended_action") or noise.get("recommendedAction") or ""),
        "noise_sources": [str(item) for item in (noise.get("noise_sources") or noise.get("sources") or [])[:8]],
        "summary": noise.get("summary") if isinstance(noise.get("summary"), dict) else {},
    }


def _compact_phases(phases: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(phases, list):
        return rows
    for item in phases[:12]:
        if not isinstance(item, dict):
            continue
        rows.append({
            "id": str(item.get("id") or ""),
            "label": str(item.get("label") or item.get("name") or ""),
            "count": _int(item.get("count")),
            "scheduled_count": _int(item.get("scheduled_count")) if item.get("scheduled_count") is not None else None,
            "completed_count": _int(item.get("completed_count")) if item.get("completed_count") is not None else None,
            "deferred_count": _int(item.get("deferred_count")) if item.get("deferred_count") is not None else None,
        })
    return rows


def _compact_three_round_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict) or not plan:
        return {}
    lanes = plan.get("information_lanes") if isinstance(plan.get("information_lanes"), dict) else {}
    assertion_schema = plan.get("required_assertion_schema") if isinstance(plan.get("required_assertion_schema"), dict) else {}
    return {
        "schema": str(plan.get("schema") or ""),
        "version": str(plan.get("version") or ""),
        "protocol_hash": str(plan.get("protocol_hash") or ""),
        "question_hash": str(plan.get("question_hash") or ""),
        "rounds": _compact_phases(plan.get("rounds") or []),
        "information_lanes": [
            {"id": str(lane_id), "label": str((lane or {}).get("label") or "")}
            for lane_id, lane in list(lanes.items())[:16]
            if isinstance(lane, dict)
        ],
        "required_assertion_fields": [str(key) for key in assertion_schema.keys()],
        "seat_mandates": _compact_seat_mandates(plan.get("seat_mandates") or []),
    }


def _compact_seat_mandates(mandates: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(mandates, list):
        return rows
    for item in mandates[:24]:
        if not isinstance(item, dict):
            continue
        rows.append({
            "seat": str(item.get("seat") or ""),
            "seat_name": str(item.get("seat_name") or item.get("seat") or ""),
            "information_lanes": [str(x) for x in (item.get("information_lanes") or [])[:6]],
            "mandate": str(item.get("mandate") or "")[:360],
        })
    return rows


def _compact_information_board(board: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(board, dict) or not board:
        return {}
    seat_rows = []
    for item in (board.get("seat_information") or [])[:24]:
        if not isinstance(item, dict):
            continue
        seat_rows.append({
            "seat": str(item.get("seat") or ""),
            "seat_name": str(item.get("seat_name") or item.get("seat") or ""),
            "stance": str(item.get("stance") or ""),
            "evidence_count": _int(item.get("evidence_count")),
            "information_delta": str(item.get("information_delta") or "")[:360],
            "frame_markers": [str(x) for x in (item.get("frame_markers") or [])[:8]],
        })
    return {
        "schema": str(board.get("schema") or ""),
        "board_hash": str(board.get("board_hash") or ""),
        "question_hash": str(board.get("question_hash") or ""),
        "seat_count": _int(board.get("seat_count")),
        "rare_terms": [str(x) for x in (board.get("rare_terms") or [])[:18]],
        "seat_information": seat_rows,
        "disagreement_count": len(board.get("disagreements") or []),
        "judge_feedback": str(board.get("judge_feedback") or "")[:1000],
    }


def _compact_round2_scheduler(scheduler: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scheduler, dict) or not scheduler:
        return {}
    rows = []
    for item in (scheduler.get("priority_order") or [])[:24]:
        if not isinstance(item, dict):
            continue
        rows.append({
            "seat": str(item.get("seat") or ""),
            "seat_name": str(item.get("seat_name") or item.get("seat") or ""),
            "rank": _int(item.get("rank")),
            "score": round(float(item.get("score") or 0.0), 4),
            "scheduled": bool(item.get("scheduled")),
            "completed": bool(item.get("completed")),
            "late_evidence": bool(item.get("late_evidence")),
            "status": str(item.get("status") or ""),
            "reason": str(item.get("reason") or "")[:240],
            "deferred_reason": str(item.get("deferred_reason") or "")[:160],
            "lanes": [str(x) for x in (item.get("lanes") or [])[:6]],
            "prompt_hash": str(item.get("prompt_hash") or ""),
        })
    policy = scheduler.get("policy") if isinstance(scheduler.get("policy"), dict) else {}
    return {
        "schema": str(scheduler.get("schema") or ""),
        "policy": {
            "name": str(policy.get("name") or ""),
            "reason": str(policy.get("reason") or "")[:360],
            "max_priority_seats": _int(policy.get("max_priority_seats")),
            "input_count": _int(policy.get("input_count")),
        },
        "scheduled_count": _int(scheduler.get("scheduled_count")),
        "completed_count": _int(scheduler.get("completed_count")),
        "deferred_count": _int(scheduler.get("deferred_count")),
        "failed_count": _int(scheduler.get("failed_count")),
        "priority_order": rows,
    }


def _compact_late_evidence_queue(queue: Any) -> dict[str, Any]:
    rows = []
    if isinstance(queue, list):
        for item in queue[:24]:
            if not isinstance(item, dict):
                continue
            rows.append({
                "seat": str(item.get("seat") or ""),
                "seat_name": str(item.get("seat_name") or item.get("seat") or ""),
                "status": str(item.get("status") or ""),
                "deferred_reason": str(item.get("deferred_reason") or "")[:160],
                "rank": _int(item.get("rank")),
                "score": round(float(item.get("score") or 0.0), 4),
                "reason": str(item.get("reason") or "")[:240],
                "lanes": [str(x) for x in (item.get("lanes") or [])[:6]],
                "prompt_hash": str(item.get("prompt_hash") or ""),
            })
    return {
        "schema": "ai_judge.late_evidence_queue.v1",
        "deferred_count": len(rows),
        "queue": rows,
    }


# ── Renderer ──────────────────────────────────────────────────────────

def render(contract: dict[str, Any], fmt: str = "json") -> str | dict:
    """Render a canonical contract into the requested format.

    Formats:
    - "json" → dict (for API responses)
    - "compact" → dict (minimal, for MCP)
    - "html" → str (full HTML page)
    - "md" → str (Markdown)
    """
    if fmt == "compact":
        return _render_compact(contract)
    if fmt == "html":
        return _render_html(contract)
    if fmt == "md":
        return _render_md(contract)
    return contract  # json = raw dict


def _render_compact(c: dict) -> dict:
    """Minimal output for MCP and token-constrained contexts."""
    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": c["run_id"],
        "question": c["question"][:200],
        "mode": c["mode"],
        "verdict": c["verdict"],
        "verdict_label": c["verdict_label"],
        "confidence": c["confidence"],
        "one_liner": c["one_liner"],
        "status": c["status"],
        "seat_count": len(c["seats"]),
        "seats": [{"seat": s.get("seat"), "score": s.get("score")} for s in c["seats"][:12]],
        "reasons": c["reasons"][:5],
        "actions": c["actions"][:5],
        "evidence": c["evidence"],
        "audit": c.get("audit") or {},
        "high_risk_gate": c.get("high_risk_gate") or {},
        "recovery_queue": c.get("recovery_queue") or {},
        "view_url": c["view_url"],
    }


def _render_html(c: dict) -> str:
    """Full HTML report — single source of truth for all clients."""
    if (c.get("high_risk_gate") or {}).get("blocked") and c.get("incomplete_high_risk_report"):
        return render_incomplete_high_risk_report_html(c["incomplete_high_risk_report"])
    esc = _html.escape

    # Verdict color
    v = c["verdict"]
    vc = "#16a34a" if v == "credible" else "#d97706" if v == "conditional" else "#dc2626"

    # Seats rows
    seat_rows = ""
    for s in c["seats"]:
        name = esc(s.get("seat_name") or s.get("seat") or "")
        score = s.get("score", 0)
        tier_color = "#16a34a" if score >= 0.7 else "#d97706" if score >= 0.5 else "#dc2626"
        seat_rows += f'<tr><td>{name}</td><td style="color:{tier_color};font-weight:700">{score:.2f}</td><td>{esc(s.get("mbti") or "")}</td><td>{esc(s.get("strength") or "")}</td></tr>\n'

    # Claims rows
    claim_rows = ""
    for cl in c["claims"][:20]:
        tier_bg = "#dcfce7" if cl["tier"] == "credible" else "#fef3c7" if cl["tier"] == "conditional" else "#fee2e2"
        claim_rows += f'<tr><td style="max-width:400px">{esc(cl["claim"][:200])}</td><td>{cl["score"]:.2f}</td><td><span style="background:{tier_bg};padding:2px 6px;border-radius:4px;font-size:11px">{esc(cl["tier"])}</span></td></tr>\n'

    # Reasons
    reasons_html = "".join(f"<li>{esc(r)}</li>" for r in c["reasons"]) or "<li>暂无</li>"

    # Actions
    actions_html = "".join(f"<li>{esc(a)}</li>" for a in c["actions"]) or "<li>暂无</li>"

    # Risks
    risks_html = "".join(f"<li>{esc(r)}</li>" for r in c["risks"]) or "<li>暂无</li>"

    # Evidence
    ev = c["evidence"]
    noise = ((c.get("audit") or {}).get("noise") or {}) if isinstance(c.get("audit"), dict) else {}
    noise_card = ""
    if noise:
        noise_sources = ", ".join(str(item) for item in (noise.get("noise_sources") or [])[:8]) or "low_observed_noise"
        noise_card = f"""
<div class="sec"><div class="sec-t">Noise Audit / 噪声审计</div>
<div class="card">
<p><strong>噪声分数：</strong>{_int(noise.get("score"))}/100 · {esc(str(noise.get("level") or ""))}</p>
<p><strong>建议动作：</strong>{esc(str(noise.get("recommended_action") or ""))}</p>
<p><strong>主要来源：</strong>{esc(noise_sources)}</p>
</div></div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Judge 裁决报告</title>
<style>
:root{{color-scheme:light}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a1d21;background:#f8f9fb;line-height:1.6;font-size:14px}}
.wrap{{max-width:920px;margin:0 auto;padding:32px 20px 64px}}
.hero{{background:linear-gradient(135deg,#1e40af,#7c3aed);border-radius:12px;padding:28px;color:#fff;text-align:center;margin-bottom:24px}}
.hero .v{{font-size:32px;font-weight:800}}.hero .c{{font-size:42px;font-weight:900}}.hero .o{{font-size:13px;opacity:.85;max-width:600px;margin:10px auto 0}}
.bar{{width:180px;height:7px;background:rgba(255,255,255,.2);border-radius:4px;margin:8px auto 0}}.bar .f{{height:100%;border-radius:4px;background:#4ade80}}
.card{{background:#fff;border:1px solid #e2e6ea;border-radius:12px;padding:20px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.card h3{{font-size:14px;font-weight:700;color:#2563eb;margin-bottom:10px}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin:10px 0}}th{{background:#f1f3f5;text-align:left;padding:8px 10px;border-bottom:2px solid #e2e6ea;font-size:11px}}td{{padding:8px 10px;border-bottom:1px solid #e2e6ea;vertical-align:top}}
.sec{{margin:24px 0}}.sec-t{{font-size:16px;font-weight:700;border-bottom:2px solid #2563eb;display:inline-block;padding-bottom:4px;margin-bottom:12px}}
.meta{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}.chip{{font-size:11px;padding:3px 10px;border:1px solid #e2e6ea;border-radius:16px;color:#5a6270}}
ul{{padding-left:20px}}li{{margin-bottom:4px;font-size:13px}}
.footer{{text-align:center;padding:24px 0;color:#5a6270;font-size:11px;border-top:1px solid #e2e6ea;margin-top:24px}}
</style></head><body><div class="wrap">

<div class="hero">
<div style="font-size:11px;opacity:.7;text-transform:uppercase;letter-spacing:1px">裁决结论</div>
<div class="v">{esc(c["verdict_label"])}</div>
<div class="c" style="color:{vc}">{c["confidence"]}%</div>
<div class="bar"><div class="f" style="width:{c['confidence']}%"></div></div>
<div class="o">{esc(c["one_liner"])}</div>
</div>

<div class="meta">
<span class="chip">Run {esc(c["run_id"])}</span>
<span class="chip">{esc(c["mode"])}</span>
<span class="chip">{len(c["seats"])} 席位</span>
<span class="chip">{ev["ok_count"]}/{ev["ok_count"]+ev["failed_count"]} 有效</span>
<span class="chip">{esc(c["created_at"][:10])}</span>
</div>

<div class="sec"><div class="sec-t">席位评分</div>
<div class="card"><table><thead><tr><th>席位</th><th>评分</th><th>MBTI</th><th>强度</th></tr></thead><tbody>{seat_rows}</tbody></table></div></div>

<div class="sec"><div class="sec-t">关键理由</div>
<div class="card"><ul>{reasons_html}</ul></div></div>

<div class="sec"><div class="sec-t">Claims 评分</div>
<div class="card"><table><thead><tr><th>Claim</th><th>评分</th><th>Tier</th></tr></thead><tbody>{claim_rows}</tbody></table></div></div>

<div class="sec"><div class="sec-t">风险提示</div>
<div class="card"><ul>{risks_html}</ul></div></div>

{noise_card}

<div class="sec"><div class="sec-t">行动建议</div>
<div class="card"><ul>{actions_html}</ul></div></div>

<div class="footer">AI Judge Trust Workbench · Output Contract {CONTRACT_VERSION} · {esc(c["view_url"])}</div>

</div></body></html>"""


def _render_md(c: dict) -> str:
    """Markdown report."""
    if (c.get("high_risk_gate") or {}).get("blocked") and c.get("incomplete_high_risk_report"):
        return render_incomplete_high_risk_report_markdown(c["incomplete_high_risk_report"])
    lines = [
        f"# AI Judge 裁决报告",
        "",
        f"**Run ID**: `{c['run_id']}`",
        f"**Mode**: {c['mode']}",
        f"**Verdict**: {c['verdict_label']} ({c['confidence']}%)",
        "",
        f"> {c['one_liner']}",
        "",
        "---",
        "",
        "## 席位评分",
        "",
        "| 席位 | 评分 | MBTI | 强度 |",
        "|------|------|------|------|",
    ]
    for s in c["seats"]:
        name = s.get("seat_name") or s.get("seat") or ""
        lines.append(f"| {name} | {s.get('score', 0):.2f} | {s.get('mbti', '')} | {s.get('strength', '')} |")

    lines += ["", "## 关键理由", ""]
    for r in c["reasons"]:
        lines.append(f"- {r}")

    lines += ["", "## Claims", "", "| Claim | 评分 | Tier |", "|-------|------|------|"]
    for cl in c["claims"][:20]:
        lines.append(f"| {cl['claim'][:100]} | {cl['score']:.2f} | {cl['tier']} |")

    lines += ["", "## 风险提示", ""]
    for r in c["risks"]:
        lines.append(f"- {r}")

    noise = ((c.get("audit") or {}).get("noise") or {}) if isinstance(c.get("audit"), dict) else {}
    if noise:
        lines += ["", "## Noise Audit / 噪声审计", ""]
        lines.append(f"- 噪声分数：{_int(noise.get('score'))}/100（{noise.get('level', '')}）")
        lines.append(f"- 建议动作：{noise.get('recommended_action', '')}")
        sources = noise.get("noise_sources") or []
        if sources:
            lines.append("- 主要噪声来源：" + "、".join(str(item) for item in sources[:8]))

    lines += ["", "## 行动建议", ""]
    for a in c["actions"]:
        lines.append(f"- {a}")

    lines += ["", "---", f"*{CONTRACT_VERSION}*"]
    return "\n".join(lines)


# ── Convenience ───────────────────────────────────────────────────────

def render_from_verdict(raw: dict, fmt: str = "json") -> str | dict:
    """One-call: normalize + render."""
    return render(normalize(raw), fmt)
