"""Compile publication models into fixed-order JudgeIR."""

from __future__ import annotations

from typing import Any

from product.reporting.publication.judge_ir import IRComponent, IRSection, JudgeIR


def compile_judge_ir(model: dict[str, Any]) -> JudgeIR:
    """Compile a publication report model into deterministic JudgeIR."""

    title = _text(model.get("title"), "AI Judge 判断报告")
    subtitle = _text(model.get("subtitle"), "面向决策的 AI Judge 阅读版")
    run_id = _text(model.get("run_id"), "unknown")
    domain_label = _text(model.get("domain_label") or model.get("domain"), "AI Judge")
    generated_at = _text(model.get("generated_at"), "")
    quality = model.get("quality") if isinstance(model.get("quality"), dict) else {}

    reader_blocks = _blocks(model.get("reader_blocks"))
    cover_metrics = _metrics(model.get("cover_metrics") or model.get("metrics"))
    summary_text = _first_summary(reader_blocks) or _text(
        (model.get("summary") or {}).get("one_line") if isinstance(model.get("summary"), dict) else "",
        "当前材料不足以形成稳定判断。",
    )

    meta = [
        {"label": "领域", "value": domain_label},
        {"label": "Run ID", "value": run_id},
        {"label": "生成时间", "value": generated_at},
    ]

    sections = (
        IRSection(
            "summary",
            "核心摘要",
            (
                IRComponent(
                    "RailSummary",
                    {
                        "variant": "hero",
                        "title": title,
                        "subtitle": subtitle,
                        "summary": summary_text,
                        "meta": meta,
                    },
                ),
            ),
        ),
        IRSection(
            "metrics",
            "关键指标",
            (IRComponent("MetricGrid", {"title": "关键指标", "metrics": cover_metrics}),),
        ),
        IRSection("analysis", "专业分析", tuple(_analysis_components(reader_blocks))),
        IRSection("comparison", "模型比较", tuple(_comparison_components(model))),
        IRSection("risk", "风险矩阵", (_risk_component(reader_blocks),)),
        IRSection("appendix", "延伸材料", (_appendix_component(model, quality),)),
    )

    rail = IRComponent(
        "RailSummary",
        {
            "variant": "rail",
            "summary": summary_text,
            "metrics": cover_metrics,
            "quality": quality,
        },
    )
    return JudgeIR(
        title=title,
        subtitle=subtitle,
        run_id=run_id,
        domain_label=domain_label,
        generated_at=generated_at,
        sections=sections,
        rail=rail,
        quality=quality,
    )


def _analysis_components(reader_blocks: list[dict[str, Any]]) -> list[IRComponent]:
    components: list[IRComponent] = []
    blocked_titles = {"一句话判断", "最大风险", "适用边界"}
    index = 1
    for block in reader_blocks:
        title = _text(block.get("title") or block.get("id"), "")
        if title in blocked_titles:
            continue
        items = block.get("items") if isinstance(block.get("items"), list) else []
        summary = _text(block.get("summary"), "")
        if not items and not summary:
            continue
        components.append(
            IRComponent(
                "EvidenceBlock",
                {
                    "index": f"{index:02d}",
                    "anchor": f"section-analysis-{index}",
                    "title": title or "专业分析",
                    "summary": summary,
                    "items": items,
                },
            )
        )
        index += 1
    if not components:
        components.append(
            IRComponent(
                "EvidenceBlock",
                {
                    "index": "01",
                    "anchor": "section-analysis-1",
                    "title": "专业分析",
                    "summary": "当前材料不足以形成展开分析。",
                    "items": [],
                },
            )
        )
    return components


def _comparison_components(model: dict[str, Any]) -> list[IRComponent]:
    components: list[IRComponent] = []
    source_blocks = _blocks(model.get("industry_blocks")) + _blocks(model.get("base_blocks"))
    index = 1
    for block in source_blocks:
        table = block.get("table") if isinstance(block.get("table"), dict) else {}
        columns = table.get("columns") if isinstance(table.get("columns"), list) else []
        rows = table.get("rows") if isinstance(table.get("rows"), list) else []
        if not columns or not rows:
            continue
        components.append(
            IRComponent(
                "ModelComparisonTable",
                {
                    "index": f"{index:02d}",
                    "anchor": f"section-comparison-{index}",
                    "title": _text(block.get("title"), "模型比较"),
                    "summary": _text(block.get("summary"), ""),
                    "table": {"columns": columns, "rows": rows},
                },
            )
        )
        index += 1
        if index > 4:
            break
    if not components:
        components.append(
            IRComponent(
                "EvidenceBlock",
                {
                    "index": "01",
                    "anchor": "section-comparison-1",
                    "title": "模型比较",
                    "summary": "当前报告没有可结构化比较的席位表格。",
                    "items": [],
                },
            )
        )
    return components


def _risk_component(reader_blocks: list[dict[str, Any]]) -> IRComponent:
    risk_items = _items_for_title(reader_blocks, "最大风险")
    boundary_items = _items_for_title(reader_blocks, "适用边界")
    risks = []
    for index, item in enumerate(risk_items[:6], start=1):
        control = boundary_items[(index - 1) % len(boundary_items)] if boundary_items else "回源核对后再采纳。"
        risks.append(
            {
                "risk": item,
                "control": control,
                "severity": "high" if index <= 2 else "medium",
            }
        )
    if not risks:
        risks.append(
            {
                "risk": "证据缺口或上下文变化可能改变当前判断。",
                "control": "进入正式结论前由人工复核原始材料。",
                "severity": "medium",
            }
        )
    return IRComponent(
        "RiskMatrix",
        {
            "index": "01",
            "title": "风险矩阵",
            "risks": risks,
        },
    )


def _appendix_component(model: dict[str, Any], quality: dict[str, Any]) -> IRComponent:
    quality_block = {
        "id": "render_quality",
        "title": "输出质量门禁",
        "summary": f"状态：{_text(quality.get('status'), 'unknown')} · 可发布：{'是' if quality.get('publishable') else '否'}",
        "items": [f"error: {item}" for item in quality.get("errors") or []]
        + [f"warning: {item}" for item in quality.get("warnings") or []],
        "metrics": [],
        "cards": [],
        "table": {"columns": [], "rows": []},
    }
    groups = [
        {"title": "行业展开", "anchor": "appendix-industry", "blocks": _blocks(model.get("industry_blocks"))},
        {"title": "证据与来源", "anchor": "appendix-evidence", "blocks": _blocks(model.get("base_blocks"))},
        {
            "title": "系统审计",
            "anchor": "appendix-audit",
            "blocks": _blocks(model.get("audit_blocks")) + [quality_block],
        },
    ]
    return IRComponent("AppendixPanel", {"groups": groups})


def _blocks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _metrics(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    metrics = []
    for item in value:
        if not isinstance(item, dict):
            continue
        metrics.append(
            {
                "label": _text(item.get("label"), "-"),
                "value": _text(item.get("value"), "-"),
                "tone": _text(item.get("tone"), "neutral"),
            }
        )
    return metrics


def _first_summary(blocks: list[dict[str, Any]]) -> str:
    for block in blocks:
        summary = _text(block.get("summary"), "")
        if summary:
            return summary
    return ""


def _items_for_title(blocks: list[dict[str, Any]], title: str) -> list[str]:
    for block in blocks:
        if _text(block.get("title"), "") != title:
            continue
        items = block.get("items") if isinstance(block.get("items"), list) else []
        if items:
            return [_text(item, "") for item in items if _text(item, "")]
        summary = _text(block.get("summary"), "")
        return [summary] if summary else []
    return []


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default
