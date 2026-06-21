#!/usr/bin/env python3
"""Long-term model stability profiles derived from Noise Audit artifacts."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODEL_STABILITY_SCHEMA = "ai_judge.model_stability_profiles.v1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_QUALITY_MODE_MARKERS = (
    "quality_mode_not_verified",
    "expert_mode_not_verified",
    "deep_thinking",
    "thinking_verified",
)


def default_model_stability_path() -> Path:
    return Path(os.environ.get("AI_JUDGE_MODEL_STABILITY_PATH", str(PROJECT_ROOT / "data" / "model_stability_profiles.json")))


def load_model_stability_profiles(path: str | Path | None = None) -> dict[str, Any]:
    profile_path = Path(path) if path else default_model_stability_path()
    if not profile_path.exists():
        return _empty_store()
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return _empty_store()
    if not isinstance(payload, dict):
        return _empty_store()
    payload.setdefault("schema", MODEL_STABILITY_SCHEMA)
    payload.setdefault("profiles", {})
    payload.setdefault("run_count", 0)
    return payload


def update_model_stability_profiles(
    *,
    run_id: str,
    question: str = "",
    mode: str = "",
    noise_audit: dict[str, Any] | None = None,
    verdict: dict[str, Any] | None = None,
    path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Update aggregate per-seat stability profiles from one completed run."""
    profile_path = Path(path) if path else default_model_stability_path()
    persist = path is not None or os.environ.get("AI_JUDGE_MODEL_STABILITY_PATH") or not os.environ.get("PYTEST_CURRENT_TEST")
    store = load_model_stability_profiles(profile_path) if persist else _empty_store()
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    rows = _rows_from_noise(noise_audit)
    if not rows:
        rows = _rows_from_verdict(verdict or {})

    domain = infer_task_domain(question, mode)
    changed = False
    run_seen_anywhere = False
    for row in rows:
        seat = _seat_id(row)
        if not seat:
            continue
        profile = _profile(store, seat, row.get("seat_name") or row.get("display_name") or seat)
        recent_runs = profile.setdefault("recent_runs", [])
        if any(item.get("run_id") == run_id for item in recent_runs if isinstance(item, dict)):
            run_seen_anywhere = True
            continue
        _apply_row(
            profile=profile,
            row=row,
            run_id=run_id,
            domain=domain,
            noise_audit=noise_audit or {},
            timestamp=timestamp,
        )
        changed = True

    if changed:
        if not run_seen_anywhere:
            store["run_count"] = int(store.get("run_count") or 0) + 1
        store["updated_at"] = timestamp
        if persist:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return store


def model_stability_summary(
    store: dict[str, Any] | None,
    *,
    seats: list[str] | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    """Return a compact public/report-safe stability profile summary."""
    if not isinstance(store, dict):
        return {}
    profiles = store.get("profiles") if isinstance(store.get("profiles"), dict) else {}
    requested = {str(seat).lower() for seat in seats or [] if str(seat).strip()}
    rows: list[dict[str, Any]] = []
    for seat, profile in profiles.items():
        if requested and str(seat).lower() not in requested:
            continue
        if not isinstance(profile, dict):
            continue
        rows.append(_public_profile(profile))
    rows.sort(key=lambda item: (-float(item.get("runs_seen") or 0), -float(item.get("stability_score") or 0), item.get("seat", "")))
    return {
        "schema": MODEL_STABILITY_SCHEMA,
        "updated_at": str(store.get("updated_at") or ""),
        "run_count": int(store.get("run_count") or 0),
        "profile_count": len(profiles),
        "profiles": rows[: max(1, int(limit))],
    }


def render_model_stability_markdown(summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(summary, dict) or not summary:
        return []
    profiles = summary.get("profiles") if isinstance(summary.get("profiles"), list) else []
    if not profiles:
        return []
    lines = [
        "## 11. Model Stability / 模型稳定性画像",
        f"- 已画像席位：{summary.get('profile_count', len(profiles))}",
        f"- 累计更新轮次：{summary.get('run_count', 0)}",
    ]
    for item in profiles[:8]:
        if not isinstance(item, dict):
            continue
        rates = item.get("rates") if isinstance(item.get("rates"), dict) else {}
        lines.append(
            "- "
            f"{item.get('seat_name') or item.get('seat')}: "
            f"稳定性 {item.get('stability_score', 'unknown')}/100，"
            f"有效率 {rates.get('valid_rate', 'unknown')}，"
            f"格式合规 {rates.get('format_compliance_rate', 'unknown')}，"
            f"污染率 {rates.get('pollution_rate', 'unknown')}，"
            f"推理模式失败率 {rates.get('quality_mode_failure_rate', 'unknown')}"
        )
    return lines


def infer_task_domain(question: str, mode: str = "") -> str:
    text = f"{mode} {question}".lower()
    checks = [
        ("legal", ("法律", "合同", "法院", "律师", "诉讼", "债权", "破产", "民法典", "司法")),
        ("prediction", ("预测", "世界杯", "赛事", "赔率", "投注", "盘口", "prediction", "pool")),
        ("medical", ("医学", "诊断", "治疗", "药物", "病人", "症状", "medical")),
        ("finance", ("投资", "股票", "财务", "估值", "利率", "汇率", "finance")),
        ("product", ("产品", "代码", "系统", "架构", "客户端", "dashboard", "api", "product", "code")),
    ]
    for domain, keywords in checks:
        if any(keyword.lower() in text for keyword in keywords):
            return domain
    return "general"


def _empty_store() -> dict[str, Any]:
    return {
        "schema": MODEL_STABILITY_SCHEMA,
        "updated_at": "",
        "run_count": 0,
        "profiles": {},
    }


def _rows_from_noise(noise_audit: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(noise_audit, dict):
        return []
    rows = noise_audit.get("seat_noise_rows")
    return [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []


def _rows_from_verdict(verdict: dict[str, Any]) -> list[dict[str, Any]]:
    bridge = verdict.get("web_bridge") if isinstance(verdict.get("web_bridge"), dict) else {}
    raw = bridge.get("raw_results") if isinstance(bridge.get("raw_results"), list) else []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        error = item.get("error") if isinstance(item.get("error"), dict) else {}
        rows.append({
            "seat": item.get("seat") or item.get("seat_id"),
            "seat_name": item.get("seat_name") or item.get("display_name"),
            "valid": bool(item.get("ok")),
            "confidence": item.get("confidence") or item.get("score"),
            "error_code": error.get("code") or item.get("error_code") or item.get("failure_reason") or "",
            "noise_flags": _flags_from_verdict_row(item),
        })
    return rows


def _flags_from_verdict_row(item: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    error = item.get("error") if isinstance(item.get("error"), dict) else {}
    error_code = str(error.get("code") or item.get("error_code") or item.get("failure_reason") or "")
    if not item.get("ok"):
        flags.append("invalid_output")
    if "schema" in error_code or "json" in error_code or "format" in error_code:
        flags.append("format_noise")
    if "pollution" in error_code or "prompt_still_in_input" in error_code:
        flags.append("context_pollution")
    if "login" in error_code or "auth" in error_code or "refusal" in error_code:
        flags.append("refusal_or_auth_block")
    return flags


def _seat_id(row: dict[str, Any]) -> str:
    return str(row.get("seat") or row.get("seat_id") or row.get("id") or "").strip().lower()


def _profile(store: dict[str, Any], seat: str, seat_name: Any) -> dict[str, Any]:
    profiles = store.setdefault("profiles", {})
    profile = profiles.get(seat)
    if not isinstance(profile, dict):
        profile = {
            "seat": seat,
            "seat_name": str(seat_name or seat),
            "runs_seen": 0,
            "valid_outputs": 0,
            "failed_outputs": 0,
            "schema_failures": 0,
            "pollution_count": 0,
            "refusal_or_auth_count": 0,
            "hallucination_risk_count": 0,
            "quality_mode_failures": 0,
            "confidence_count": 0,
            "confidence_sum": 0.0,
            "confidence_sq_sum": 0.0,
            "noise_score_sum": 0.0,
            "noise_score_count": 0,
            "domain_counts": {},
            "domain_valid_counts": {},
            "recent_runs": [],
            "rates": {},
            "stability_score": 0.0,
            "latest": {},
        }
        profiles[seat] = profile
    if seat_name:
        profile["seat_name"] = str(seat_name)
    return profile


def _apply_row(
    *,
    profile: dict[str, Any],
    row: dict[str, Any],
    run_id: str,
    domain: str,
    noise_audit: dict[str, Any],
    timestamp: str,
) -> None:
    flags = {str(flag) for flag in (row.get("noise_flags") or []) if str(flag)}
    error_code = str(row.get("error_code") or "")
    valid = bool(row.get("valid"))
    confidence = _as_float(row.get("confidence"))
    noise_score = _as_score(noise_audit.get("noise_score") if isinstance(noise_audit, dict) else None)

    profile["runs_seen"] = int(profile.get("runs_seen") or 0) + 1
    if valid:
        profile["valid_outputs"] = int(profile.get("valid_outputs") or 0) + 1
    else:
        profile["failed_outputs"] = int(profile.get("failed_outputs") or 0) + 1

    if "format_noise" in flags:
        profile["schema_failures"] = int(profile.get("schema_failures") or 0) + 1
    if "context_pollution" in flags:
        profile["pollution_count"] = int(profile.get("pollution_count") or 0) + 1
    if "refusal_or_auth_block" in flags:
        profile["refusal_or_auth_count"] = int(profile.get("refusal_or_auth_count") or 0) + 1
    if "hallucination_risk" in flags:
        profile["hallucination_risk_count"] = int(profile.get("hallucination_risk_count") or 0) + 1
    if _quality_mode_failed(error_code, flags):
        profile["quality_mode_failures"] = int(profile.get("quality_mode_failures") or 0) + 1

    if confidence is not None:
        profile["confidence_count"] = int(profile.get("confidence_count") or 0) + 1
        profile["confidence_sum"] = float(profile.get("confidence_sum") or 0.0) + confidence
        profile["confidence_sq_sum"] = float(profile.get("confidence_sq_sum") or 0.0) + confidence * confidence
    if noise_score is not None:
        profile["noise_score_count"] = int(profile.get("noise_score_count") or 0) + 1
        profile["noise_score_sum"] = float(profile.get("noise_score_sum") or 0.0) + noise_score

    domain_counts = profile.setdefault("domain_counts", {})
    domain_valid_counts = profile.setdefault("domain_valid_counts", {})
    domain_counts[domain] = int(domain_counts.get(domain) or 0) + 1
    if valid:
        domain_valid_counts[domain] = int(domain_valid_counts.get(domain) or 0) + 1

    recent_runs = profile.setdefault("recent_runs", [])
    recent_runs.insert(0, {
        "run_id": run_id,
        "at": timestamp,
        "domain": domain,
        "valid": valid,
        "confidence": round(confidence, 4) if confidence is not None else None,
        "noise_score": int(round(noise_score)) if noise_score is not None else None,
        "error_code": error_code,
        "flags": sorted(flags),
    })
    del recent_runs[30:]

    _recompute_profile(profile)


def _recompute_profile(profile: dict[str, Any]) -> None:
    runs = max(1, int(profile.get("runs_seen") or 0))
    valid_rate = _rate(profile.get("valid_outputs"), runs)
    format_compliance = 1.0 - _rate(profile.get("schema_failures"), runs)
    pollution_rate = _rate(profile.get("pollution_count"), runs)
    refusal_rate = _rate(profile.get("refusal_or_auth_count"), runs)
    hallucination_rate = _rate(profile.get("hallucination_risk_count"), runs)
    quality_failure_rate = _rate(profile.get("quality_mode_failures"), runs)
    confidence_mean, confidence_stddev = _confidence_stats(profile)
    confidence_consistency = max(0.0, 1.0 - min(1.0, confidence_stddev / 0.35))
    average_noise = _average(profile.get("noise_score_sum"), profile.get("noise_score_count"))

    stability = 100.0 * (
        valid_rate * 0.35
        + format_compliance * 0.18
        + (1.0 - pollution_rate) * 0.14
        + (1.0 - refusal_rate) * 0.12
        + (1.0 - quality_failure_rate) * 0.11
        + confidence_consistency * 0.10
    )

    profile["rates"] = {
        "valid_rate": round(valid_rate, 4),
        "format_compliance_rate": round(format_compliance, 4),
        "pollution_rate": round(pollution_rate, 4),
        "refusal_or_auth_rate": round(refusal_rate, 4),
        "hallucination_risk_rate": round(hallucination_rate, 4),
        "quality_mode_failure_rate": round(quality_failure_rate, 4),
    }
    profile["confidence_mean"] = round(confidence_mean, 4) if confidence_mean is not None else None
    profile["confidence_stddev"] = round(confidence_stddev, 4)
    profile["average_noise_score"] = round(average_noise, 2) if average_noise is not None else None
    profile["stability_score"] = round(max(0.0, min(100.0, stability)), 1)
    recent = profile.get("recent_runs") if isinstance(profile.get("recent_runs"), list) else []
    profile["latest"] = recent[0] if recent else {}
    profile["domain_fit"] = _domain_fit(profile)


def _public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "seat": str(profile.get("seat") or ""),
        "seat_name": str(profile.get("seat_name") or profile.get("seat") or ""),
        "runs_seen": int(profile.get("runs_seen") or 0),
        "valid_outputs": int(profile.get("valid_outputs") or 0),
        "failed_outputs": int(profile.get("failed_outputs") or 0),
        "stability_score": float(profile.get("stability_score") or 0.0),
        "average_noise_score": profile.get("average_noise_score"),
        "confidence_mean": profile.get("confidence_mean"),
        "confidence_stddev": profile.get("confidence_stddev"),
        "rates": profile.get("rates") if isinstance(profile.get("rates"), dict) else {},
        "domain_fit": profile.get("domain_fit") if isinstance(profile.get("domain_fit"), dict) else {},
        "latest": profile.get("latest") if isinstance(profile.get("latest"), dict) else {},
    }


def _domain_fit(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    counts = profile.get("domain_counts") if isinstance(profile.get("domain_counts"), dict) else {}
    valid_counts = profile.get("domain_valid_counts") if isinstance(profile.get("domain_valid_counts"), dict) else {}
    result: dict[str, dict[str, Any]] = {}
    for domain, count in counts.items():
        total = int(count or 0)
        if total <= 0:
            continue
        result[str(domain)] = {
            "runs": total,
            "valid_rate": round(_rate(valid_counts.get(domain), total), 4),
        }
    return result


def _quality_mode_failed(error_code: str, flags: set[str]) -> bool:
    text = " ".join([error_code, *sorted(flags)]).lower()
    return any(marker in text for marker in _QUALITY_MODE_MARKERS)


def _confidence_stats(profile: dict[str, Any]) -> tuple[float | None, float]:
    count = int(profile.get("confidence_count") or 0)
    if count <= 0:
        return None, 0.0
    mean = float(profile.get("confidence_sum") or 0.0) / count
    variance = max(0.0, float(profile.get("confidence_sq_sum") or 0.0) / count - mean * mean)
    return mean, math.sqrt(variance)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    if number > 1.0:
        number = number / 100.0
    return max(0.0, min(1.0, number))


def _as_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return max(0.0, min(100.0, number))


def _rate(count: Any, total: Any) -> float:
    try:
        denominator = float(total)
        numerator = float(count or 0)
    except Exception:
        return 0.0
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def _average(total: Any, count: Any) -> float | None:
    try:
        denominator = float(count or 0)
        numerator = float(total or 0.0)
    except Exception:
        return None
    if denominator <= 0:
        return None
    return numerator / denominator
