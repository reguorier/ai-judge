#!/usr/bin/env python3
"""Deterministic Noise Audit for AI Judge runs.

Phase 1 is intentionally local and artifact-only: it measures instability from
already-collected seats, execution validity, deliberation metadata, and report
artifacts. It does not trigger extra model calls.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

NOISE_AUDIT_SCHEMA = "ai_judge.noise_audit.v1"

_FORMAT_ERROR_MARKERS = ("schema", "json", "format", "parse", "structured", "contract")
_POLLUTION_ERROR_MARKERS = (
    "pollution",
    "stale",
    "old_marker",
    "prompt_echo",
    "prompt_still_in_input",
    "transcript",
    "狼人杀",
)
_REFUSAL_ERROR_MARKERS = (
    "login_required",
    "auth_required",
    "challenge_required",
    "provider_account_restricted",
    "restricted",
    "refusal",
    "safety",
)
_REFUSAL_TEXT_MARKERS = (
    "无法回答",
    "不能提供",
    "我不能",
    "无法完成",
    "需要登录",
    "请登录",
)


def build_noise_audit(
    *,
    run_id: str,
    question: str = "",
    mode: str = "",
    verdict: dict[str, Any] | None = None,
    raw_results: list[dict[str, Any]] | None = None,
    seat_matrix: dict[str, Any] | None = None,
    evidence_packet: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a compact, deterministic noise audit artifact."""
    verdict = verdict if isinstance(verdict, dict) else {}
    bridge = verdict.get("web_bridge") if isinstance(verdict.get("web_bridge"), dict) else {}
    deliberation = bridge.get("deliberation") if isinstance(bridge.get("deliberation"), dict) else {}
    information_board = bridge.get("information_board") if isinstance(bridge.get("information_board"), dict) else {}
    execution_policy = bridge.get("execution_policy") if isinstance(bridge.get("execution_policy"), dict) else {}

    rows = _collect_rows(
        raw_results=raw_results or bridge.get("raw_results") or [],
        seat_matrix=seat_matrix or {},
        verdict=verdict,
    )
    total = len(rows)
    valid_outputs = sum(1 for row in rows if row["valid"])
    failed_outputs = max(0, total - valid_outputs)
    schema_failures = sum(1 for row in rows if row["format_noise"])
    pollution_count = sum(1 for row in rows if row["polluted"])
    refusal_count = sum(1 for row in rows if row["refusal"])
    hallucination_risk_count = sum(1 for row in rows if row["hallucination_risk"])
    confidence_values = [row["confidence"] for row in rows if row["confidence"] is not None]
    confidence_stddev = _stddev(confidence_values)
    conclusion_clusters = _conclusion_clusters(rows, deliberation, information_board)
    evidence_overlap = _evidence_overlap(rows, evidence_packet or {}, information_board)

    rates = {
        "invalid_rate": _rate(failed_outputs, total),
        "schema_failure_rate": _rate(schema_failures, total),
        "pollution_rate": _rate(pollution_count, total),
        "refusal_rate": _rate(refusal_count, total),
        "hallucination_risk_rate": _rate(hallucination_risk_count, total),
        "cluster_rate": _cluster_rate(conclusion_clusters, valid_outputs),
        "confidence_dispersion": min(1.0, confidence_stddev / 0.35) if confidence_values else 0.0,
        "evidence_divergence": max(0.0, 1.0 - evidence_overlap),
    }
    noise_score = _score_noise(total=total, valid_outputs=valid_outputs, rates=rates)
    noise_level = _noise_level(noise_score, pollution_count=pollution_count, total=total)
    sources = _noise_sources(rates, rows, conclusion_clusters=conclusion_clusters)
    recommended_action = _recommended_action(noise_score, pollution_count=pollution_count, valid_outputs=valid_outputs)

    return {
        "schema": NOISE_AUDIT_SCHEMA,
        "run_id": run_id,
        "question_hash": _stable_hash(question),
        "mode": mode,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "noise_score": noise_score,
        "noise_level": noise_level,
        "summary": {
            "models_total": total,
            "valid_outputs": valid_outputs,
            "failed_outputs": failed_outputs,
            "schema_failures": schema_failures,
            "conclusion_clusters": conclusion_clusters,
            "confidence_stddev": round(confidence_stddev, 4),
            "evidence_overlap": round(evidence_overlap, 4),
            "pollution_count": pollution_count,
            "refusal_count": refusal_count,
            "hallucination_risk_count": hallucination_risk_count,
            "collection_complete": bool(execution_policy.get("collection_complete")) if execution_policy else valid_outputs == total and total > 0,
        },
        "rates": {key: round(value, 4) for key, value in rates.items()},
        "noise_sources": sources,
        "disagreement_taxonomy": _disagreement_taxonomy(rows, deliberation, information_board, sources),
        "seat_noise_rows": [
            {
                "seat": row["seat"],
                "seat_name": row["seat_name"],
                "valid": row["valid"],
                "confidence": row["confidence"],
                "stance": row["stance"],
                "error_code": row["error_code"],
                "noise_flags": row["flags"],
            }
            for row in rows
        ],
        "recommended_action": recommended_action,
        "interpretation": _interpretation(noise_score, noise_level, sources),
    }


def noise_summary(noise_audit: dict[str, Any] | None) -> dict[str, Any]:
    """Return the public-safe one-line noise payload for API/summary surfaces."""
    if not isinstance(noise_audit, dict):
        return {}
    return {
        "schema": noise_audit.get("schema") or NOISE_AUDIT_SCHEMA,
        "score": int(noise_audit.get("noise_score") or 0),
        "level": str(noise_audit.get("noise_level") or "unknown"),
        "recommended_action": str(noise_audit.get("recommended_action") or ""),
        "sources": list(noise_audit.get("noise_sources") or [])[:8],
        "summary": noise_audit.get("summary") or {},
    }


def render_noise_markdown(noise_audit: dict[str, Any] | None) -> list[str]:
    """Render a short report section for the client-first markdown report."""
    if not isinstance(noise_audit, dict) or not noise_audit:
        return []
    summary = noise_audit.get("summary") if isinstance(noise_audit.get("summary"), dict) else {}
    sources = noise_audit.get("noise_sources") or []
    taxonomy = noise_audit.get("disagreement_taxonomy") or []
    lines = [
        "## 10. Noise Audit / 噪声审计",
        f"- 噪声分数：{noise_audit.get('noise_score', 'unknown')} / 100（{noise_audit.get('noise_level', 'unknown')}）",
        f"- 建议动作：{noise_audit.get('recommended_action', 'unknown')}",
        f"- 有效输出：{summary.get('valid_outputs', 'unknown')}/{summary.get('models_total', 'unknown')}",
        f"- 结论聚类：{summary.get('conclusion_clusters', 'unknown')}",
        f"- 置信度离散：{summary.get('confidence_stddev', 'unknown')}",
        f"- 证据重叠率：{summary.get('evidence_overlap', 'unknown')}",
        f"- 污染/拒绝/格式失败：{summary.get('pollution_count', 0)} / {summary.get('refusal_count', 0)} / {summary.get('schema_failures', 0)}",
    ]
    if sources:
        lines.append("- 主要噪声来源：" + "、".join(str(item) for item in sources[:8]))
    if taxonomy:
        lines.append("- 分歧类型：" + "、".join(str(item) for item in taxonomy[:8]))
    interpretation = str(noise_audit.get("interpretation") or "")
    if interpretation:
        lines.append(f"- 解读：{interpretation}")
    return lines


def _collect_rows(
    *,
    raw_results: list[dict[str, Any]],
    seat_matrix: dict[str, Any],
    verdict: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    score_by_seat = _score_by_seat(verdict)
    for item in raw_results if isinstance(raw_results, list) else []:
        if not isinstance(item, dict):
            continue
        seat = str(item.get("seat") or item.get("seat_id") or "").lower()
        row = _row_from_item(item, score_by_seat.get(seat, {}))
        rows.append(row)

    if rows:
        return rows

    for item in (seat_matrix.get("seats") or []) if isinstance(seat_matrix, dict) else []:
        if not isinstance(item, dict):
            continue
        seat = str(item.get("seat_id") or item.get("seat") or "").lower()
        row = _row_from_item(item, score_by_seat.get(seat, {}), matrix_mode=True)
        rows.append(row)

    if rows:
        return rows

    for item in verdict.get("seat_scores") or []:
        if not isinstance(item, dict):
            continue
        rows.append(_row_from_item(item, item, matrix_mode=True))
    return rows


def _row_from_item(item: dict[str, Any], score: dict[str, Any], matrix_mode: bool = False) -> dict[str, Any]:
    seat = str(item.get("seat") or item.get("seat_id") or score.get("seat") or "").lower()
    name = str(item.get("seat_name") or item.get("display_name") or score.get("seat_name") or seat)
    error = item.get("error") if isinstance(item.get("error"), dict) else {}
    error_code = str(error.get("code") or item.get("error_code") or item.get("failure_reason") or "")
    text = _seat_text(item)
    execution = item.get("execution_validity") if isinstance(item.get("execution_validity"), dict) else {}
    status = str(item.get("status") or "").lower()
    ok = bool(item.get("ok")) or status in {"valid", "completed", "answered", "success"}
    valid = bool(ok and text.strip() and not _truthy(execution.get("polluted")) and error_code not in {"transcript_pollution", "prompt_still_in_input"})
    if matrix_mode and status == "valid":
        valid = True
    confidence = _confidence(item, score)
    polluted = _truthy(execution.get("polluted")) or _contains_any(error_code, _POLLUTION_ERROR_MARKERS) or _contains_any(text[:500], _POLLUTION_ERROR_MARKERS)
    format_noise = (not valid and (not text.strip() or _contains_any(error_code, _FORMAT_ERROR_MARKERS))) or bool(item.get("structured_answer_found") is False)
    refusal = _contains_any(error_code, _REFUSAL_ERROR_MARKERS) or _contains_any(text[:400], _REFUSAL_TEXT_MARKERS)
    hallucination_risk = _hallucination_risk(text)
    stance = _stance(item, text)
    flags = []
    if not valid:
        flags.append("invalid_output")
    if format_noise:
        flags.append("format_noise")
    if polluted:
        flags.append("context_pollution")
    if refusal:
        flags.append("refusal_or_auth_block")
    if hallucination_risk:
        flags.append("hallucination_risk")
    return {
        "seat": seat or name.lower(),
        "seat_name": name,
        "valid": valid,
        "confidence": confidence,
        "stance": stance,
        "text": text,
        "error_code": error_code,
        "format_noise": format_noise,
        "polluted": polluted,
        "refusal": refusal,
        "hallucination_risk": hallucination_risk,
        "flags": flags,
    }


def _score_by_seat(verdict: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for item in verdict.get("seat_scores") or []:
        if isinstance(item, dict):
            seat = str(item.get("seat") or "").lower()
            if seat:
                rows[seat] = item
    return rows


def _seat_text(item: dict[str, Any]) -> str:
    for key in ("response", "answer", "output", "text", "summary", "answer_preview", "preview"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return re.sub(r"\s+", " ", value).strip()
    return ""


def _confidence(item: dict[str, Any], score: dict[str, Any]) -> float | None:
    for source in (item, score):
        for key in ("confidence", "score", "average_score"):
            value = source.get(key)
            if value is None:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number > 1.0:
                number = number / 100.0
            return round(max(0.0, min(1.0, number)), 4)
    return None


def _stance(item: dict[str, Any], text: str) -> str:
    for key in ("stance", "final_position", "position", "verdict"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:60]
    head = text[:500]
    if re.search(r"信息不足|无法判断|证据不足|insufficient", head, re.I):
        return "information_insufficient"
    if re.search(r"反对|不建议|rejected|oppose", head, re.I):
        return "oppose"
    if re.search(r"条件支持|谨慎支持|conditional", head, re.I):
        return "conditional_support"
    if re.search(r"支持|建议|credible|support", head, re.I):
        return "support"
    if item.get("valid") or item.get("ok"):
        return "unclassified_valid"
    return "invalid"


def _conclusion_clusters(rows: list[dict[str, Any]], deliberation: dict[str, Any], board: dict[str, Any]) -> int:
    distribution = deliberation.get("stance_distribution") if isinstance(deliberation, dict) else None
    if isinstance(distribution, dict) and distribution:
        return len([key for key, value in distribution.items() if key and int(value or 0) > 0])
    board_rows = board.get("seat_information") if isinstance(board, dict) else None
    if isinstance(board_rows, list) and board_rows:
        stances = {str(item.get("stance") or "").strip() for item in board_rows if isinstance(item, dict) and str(item.get("stance") or "").strip()}
        if stances:
            return len(stances)
    stances = {row["stance"] for row in rows if row["valid"] and row["stance"]}
    return len(stances) if stances else (1 if any(row["valid"] for row in rows) else 0)


def _evidence_overlap(rows: list[dict[str, Any]], evidence_packet: dict[str, Any], board: dict[str, Any]) -> float:
    board_rows = board.get("seat_information") if isinstance(board, dict) else None
    if isinstance(board_rows, list) and board_rows:
        counts = [int(item.get("evidence_count") or 0) for item in board_rows if isinstance(item, dict)]
        if counts and max(counts) > 0:
            return max(0.0, min(1.0, sum(counts) / (len(counts) * max(counts))))
    source_refs = []
    for item in evidence_packet.get("evidence_items") or []:
        if isinstance(item, dict):
            refs = item.get("refs") or []
            if isinstance(refs, list):
                source_refs.extend(str(ref) for ref in refs if ref)
    if source_refs:
        unique = len(set(source_refs))
        return max(0.0, min(1.0, 1.0 - (unique - 1) / max(unique, len(source_refs), 1)))
    valid_rows = [row for row in rows if row["valid"]]
    if not valid_rows:
        return 0.0
    evidence_mentions = sum(1 for row in valid_rows if re.search(r"证据|来源|引用|source|http|依据", row["text"], re.I))
    return round(evidence_mentions / max(1, len(valid_rows)), 4)


def _score_noise(*, total: int, valid_outputs: int, rates: dict[str, float]) -> int:
    if total <= 0:
        return 90
    score = (
        rates["invalid_rate"] * 22
        + rates["cluster_rate"] * 18
        + rates["confidence_dispersion"] * 18
        + rates["evidence_divergence"] * 14
        + rates["schema_failure_rate"] * 12
        + rates["pollution_rate"] * 12
        + rates["refusal_rate"] * 8
        + rates["hallucination_risk_rate"] * 8
    )
    if valid_outputs == 0:
        score = max(score, 85)
    return int(round(max(0.0, min(100.0, score))))


def _noise_level(score: int, *, pollution_count: int, total: int) -> str:
    if pollution_count and (total <= 2 or pollution_count / max(1, total) >= 0.34):
        return "blocked"
    if pollution_count:
        return "high"
    if score >= 80:
        return "blocked"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _noise_sources(rates: dict[str, float], rows: list[dict[str, Any]], *, conclusion_clusters: int) -> list[str]:
    sources = []
    if conclusion_clusters >= 3 or rates["cluster_rate"] >= 0.35:
        sources.append("stance_disagreement")
    if rates["confidence_dispersion"] >= 0.35:
        sources.append("confidence_dispersion")
    if rates["evidence_divergence"] >= 0.55:
        sources.append("evidence_divergence")
    if rates["schema_failure_rate"] > 0:
        sources.append("format_noise")
    if rates["pollution_rate"] > 0:
        sources.append("context_pollution")
    if rates["refusal_rate"] > 0:
        sources.append("refusal_or_auth_block")
    if rates["hallucination_risk_rate"] > 0:
        sources.append("hallucination_risk")
    if any(not row["valid"] and not row["error_code"] for row in rows):
        sources.append("empty_or_unclassified_failure")
    return sources or ["low_observed_noise"]


def _disagreement_taxonomy(
    rows: list[dict[str, Any]],
    deliberation: dict[str, Any],
    board: dict[str, Any],
    sources: list[str],
) -> list[str]:
    tags: list[str] = []
    disagreements = deliberation.get("disagreements") if isinstance(deliberation, dict) else []
    if isinstance(disagreements, list) and disagreements:
        tags.append("substantive_disagreement")
    board_disagreements = board.get("disagreements") if isinstance(board, dict) else []
    if isinstance(board_disagreements, list) and board_disagreements:
        tags.append("information_lane_disagreement")
    stances = {row["stance"] for row in rows if row["valid"]}
    if len(stances) > 1:
        tags.append("conclusion_disagreement")
    if "evidence_divergence" in sources:
        tags.append("evidence_weight_disagreement")
    if "format_noise" in sources:
        tags.append("format_noise")
    if "context_pollution" in sources:
        tags.append("context_pollution")
    if "refusal_or_auth_block" in sources:
        tags.append("safety_or_login_disagreement")
    return tags or ["no_material_disagreement_detected"]


def _recommended_action(score: int, *, pollution_count: int, valid_outputs: int) -> str:
    if pollution_count or score >= 80 or valid_outputs == 0:
        return "block_publish_and_rerun"
    if score >= 60:
        return "manual_review_required"
    if score >= 30:
        return "publish_with_noise_note"
    return "publishable_low_noise"


def _interpretation(score: int, level: str, sources: list[str]) -> str:
    if level == "blocked":
        return "本轮包含严重不稳定、污染或无有效输出，不能作为可采纳裁决。"
    if level == "high":
        return "本轮存在高噪声，应先人工复核关键分歧或补跑失败席位。"
    if level == "medium":
        return "本轮存在可见分歧或证据差异，报告可读但应保留噪声说明。"
    return "本轮输出较稳定，主要分歧未显示为系统噪声。"


def _hallucination_risk(text: str) -> bool:
    if not text:
        return False
    legal_citation = re.search(r"第[一二三四五六七八九十百千万0-9]+条", text)
    source_like = re.search(r"http|来源|引用|据|根据|source", text, re.I)
    fake_case = re.search(r"(最高法|法院|判决|案例|论文|报告).{0,30}(未提供|无来源|无法核验|示例)", text)
    return bool((legal_citation and not source_like) or fake_case)


def _stddev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _cluster_rate(clusters: int, valid_outputs: int) -> float:
    if valid_outputs <= 1:
        return 0.0
    return min(1.0, max(0, clusters - 1) / max(1, valid_outputs - 1))


def _rate(count: int, total: int) -> float:
    return 0.0 if total <= 0 else max(0.0, min(1.0, count / total))


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    haystack = str(text or "").lower()
    return any(marker.lower() in haystack for marker in markers)


def _truthy(value: Any) -> bool:
    return bool(value is True or str(value).lower() in {"true", "1", "yes"})


def _stable_hash(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()[:16]
