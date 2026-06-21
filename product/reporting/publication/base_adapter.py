"""Base publication adapter shared by all AI Judge report domains."""

from __future__ import annotations

from typing import Any

from product.reporting.publication.schema import (
    as_text_items,
    build_block,
    build_card,
    build_metric,
    build_table,
    clip_text,
    text_value,
)


def build_base_publication(
    report: dict[str, Any],
    *,
    seat_matrix: dict[str, Any] | None = None,
    evidence_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seat_matrix = seat_matrix if isinstance(seat_matrix, dict) else {}
    evidence_packet = evidence_packet if isinstance(evidence_packet, dict) else {}
    audit = report.get("audit") if isinstance(report.get("audit"), dict) else {}
    noise = report.get("noise_audit") if isinstance(report.get("noise_audit"), dict) else audit.get("noise_audit") or {}
    stability = report.get("model_stability") if isinstance(report.get("model_stability"), dict) else {}
    evidence_strength = report.get("evidence_strength") if isinstance(report.get("evidence_strength"), dict) else {}

    valid = _int(audit.get("valid_seats"), _count_valid_seats(seat_matrix))
    failed = _int(audit.get("failed_seats"), _count_failed_seats(seat_matrix))
    total = _int(audit.get("total_seats"), valid + failed)
    if total <= 0:
        total = valid + failed

    noise_score = _noise_score(noise)
    noise_level = text_value(noise.get("noise_level") or noise.get("level") or "unknown")
    noise_action = text_value(noise.get("recommended_action") or noise.get("recommendedAction") or "review_if_needed")
    conclusion = _best_conclusion(report)
    recommended_actions = as_text_items(report.get("recommended_actions") or report.get("next_steps"), limit=6)
    risks = as_text_items(report.get("risks") or report.get("failure_conditions"), limit=6)
    evidence_items = as_text_items(evidence_strength.get("items") or evidence_packet.get("evidence_items"), limit=8)
    consensus = as_text_items(report.get("consensus"), limit=6)
    disagreements = as_text_items(report.get("disagreements"), limit=6)

    metrics = [
        build_metric("有效席位", f"{valid}/{total or '?'}", "good" if failed == 0 else "warn"),
        build_metric("Noise Score", f"{noise_score}/100" if noise_score is not None else "unknown", _noise_tone(noise_score)),
        build_metric("噪声等级", noise_level, _noise_tone(noise_score)),
        build_metric("证据强度", evidence_strength.get("overall", "unknown"), "neutral"),
    ]

    summary = {
        "one_line": conclusion,
        "recommendation": recommended_actions[0] if recommended_actions else "先阅读行业版和审计版，再决定是否采纳。",
        "noise_score": noise_score,
        "noise_level": noise_level,
        "recommended_action": noise_action,
        "seat_coverage": f"{valid}/{total or '?'}",
        "evidence_strength": evidence_strength.get("overall", "unknown"),
    }

    decision_cards = [
        build_card("当前最稳健结论", conclusion, "基础版只保留可读结论，原始席位回答进入审计附录。", "primary"),
        build_card("是否需要人工复核", _human_gate(noise_score, failed), f"建议动作：{noise_action}", _noise_tone(noise_score)),
        build_card("证据强度", evidence_strength.get("overall", "unknown"), "证据强度来自席位覆盖、证据包和失败席位综合判断。", "neutral"),
        build_card("下一步", summary["recommendation"], "下一步行动必须能被人类执行或复核。", "neutral"),
    ]

    base_blocks = [
        build_block(
            "executive_summary",
            "基础版 · 一页结论",
            kind="decision_cards",
            summary=conclusion,
            metrics=metrics,
            cards=decision_cards,
            level="base",
        ),
        build_block(
            "consensus_disagreement",
            "共识与分歧",
            kind="two_column",
            summary="AI Judge 不只给结论，还要说明哪些一致、哪些分歧值得看。",
            table=build_table(
                ["类型", "内容"],
                [["共识", "\n".join(consensus) or "暂无稳定共识"], ["分歧", "\n".join(disagreements) or "暂无明确分歧"]],
            ),
            level="base",
        ),
        build_block(
            "evidence_strength",
            "证据强度",
            kind="evidence",
            summary=f"整体证据强度：{evidence_strength.get('overall', 'unknown')}",
            items=evidence_items or ["暂无可展示证据条目；应补齐证据包后再发布正式结论。"],
            level="base",
        ),
        build_block(
            "risks_next_actions",
            "风险与下一步",
            kind="action_plan",
            summary="风险和行动分开呈现，避免用户把模型语气误读为确定性。",
            table=build_table(
                ["风险/失败条件", "建议动作"],
                _zip_table_rows(risks or ["暂无明确风险"], recommended_actions or ["人工复核后再采纳"]),
            ),
            level="base",
        ),
    ]

    audit_blocks = [
        build_block(
            "noise_audit",
            "Noise Audit / 噪声审计",
            kind="audit",
            summary=f"本轮噪声：{noise_score if noise_score is not None else 'unknown'}/100，等级：{noise_level}。",
            metrics=[
                build_metric("噪声分数", f"{noise_score}/100" if noise_score is not None else "unknown", _noise_tone(noise_score)),
                build_metric("推荐动作", noise_action, _noise_tone(noise_score)),
                build_metric("Schema 失败", _nested_value(noise, ["summary", "schema_failures"], "0"), "neutral"),
                build_metric("污染计数", _nested_value(noise, ["summary", "pollution_count"], "0"), "neutral"),
            ],
            items=as_text_items(noise.get("noise_sources") or noise.get("sources"), limit=8) or ["暂无显著噪声来源。"],
            level="audit",
        ),
        build_block(
            "model_stability",
            "Model Stability / 模型稳定性画像",
            kind="audit",
            summary=f"当前累计画像数：{stability.get('profile_count', 0)}。",
            table=_model_stability_table(stability),
            level="audit",
        ),
        build_block(
            "artifact_manifest",
            "Artifact Manifest / 交付物清单",
            kind="audit",
            summary="客户端只暴露路由和报告类型，不暴露本机磁盘路径。",
            table=build_table(
                ["交付物", "用途"],
                [
                    ["基础报告", "给所有问题的稳定阅读版本"],
                    ["行业报告", "按问题类型适配的专业交付版本"],
                    ["审计版", "Noise、模型画像、证据强度和席位矩阵"],
                ],
            ),
            level="audit",
        ),
    ]

    return {
        "summary": summary,
        "metrics": metrics,
        "base_blocks": base_blocks,
        "audit_blocks": audit_blocks,
    }


def _best_conclusion(report: dict[str, Any]) -> str:
    return clip_text(
        report.get("core_conclusion")
        or report.get("one_liner")
        or report.get("recommendation")
        or report.get("title")
        or "当前没有足够内容形成正式结论。",
        360,
    )


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _count_valid_seats(seat_matrix: dict[str, Any]) -> int:
    seats = seat_matrix.get("seats") if isinstance(seat_matrix.get("seats"), list) else []
    return len([s for s in seats if isinstance(s, dict) and s.get("status") in {"valid", "completed", "answered", "success"}])


def _count_failed_seats(seat_matrix: dict[str, Any]) -> int:
    seats = seat_matrix.get("seats") if isinstance(seat_matrix.get("seats"), list) else []
    return len([s for s in seats if isinstance(s, dict) and s.get("status") in {"failed", "error", "timeout"}])


def _noise_score(noise: dict[str, Any]) -> int | None:
    value = noise.get("noise_score") if noise.get("noise_score") is not None else noise.get("score")
    if value is None:
        return None
    return max(0, min(100, _int(value, 0)))


def _noise_tone(score: int | None) -> str:
    if score is None:
        return "neutral"
    if score >= 60:
        return "bad"
    if score >= 35:
        return "warn"
    return "good"


def _human_gate(noise_score: int | None, failed: int) -> str:
    if failed > 0:
        return "需要人工复核"
    if noise_score is not None and noise_score >= 60:
        return "需要人工复核"
    if noise_score is not None and noise_score >= 35:
        return "建议复核"
    return "可作为初步参考"


def _zip_table_rows(left: list[str], right: list[str]) -> list[list[str]]:
    size = max(len(left), len(right))
    rows = []
    for index in range(size):
        rows.append([left[index] if index < len(left) else "", right[index] if index < len(right) else ""])
    return rows


def _nested_value(root: dict[str, Any], keys: list[str], default: Any = "") -> Any:
    current: Any = root
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current not in (None, "") else default


def _model_stability_table(stability: dict[str, Any]) -> dict[str, Any]:
    rows = []
    profiles = stability.get("profiles") if isinstance(stability.get("profiles"), list) else []
    for item in profiles[:12]:
        if not isinstance(item, dict):
            continue
        rates = item.get("rates") if isinstance(item.get("rates"), dict) else {}
        rows.append([
            item.get("seat_name") or item.get("seat") or "-",
            item.get("runs_seen", 0),
            item.get("stability_score", "-"),
            rates.get("valid_rate", "-"),
            rates.get("schema_failure_rate", "-"),
        ])
    return build_table(["席位", "样本数", "稳定性", "有效率", "Schema失败率"], rows or [["暂无画像", "-", "-", "-", "-"]])
