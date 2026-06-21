"""Publication Output V2 service."""

from __future__ import annotations

from typing import Any

from product.reporting.publication.adapters.legal_memo import build_legal_memo_blocks
from product.reporting.publication.adapters.prediction_pool import build_prediction_pool_blocks
from product.reporting.publication.base_adapter import build_base_publication
from product.reporting.publication.domain_router import DOMAIN_LABELS, detect_domain
from product.reporting.publication.quality_gate import validate_publication_report
from product.reporting.publication.renderer_html import render_publication_html
from product.reporting.publication.renderer_markdown import render_publication_markdown
from product.reporting.publication.schema import as_text_items, build_block, empty_publication_report, text_value
from product.reporting.publication.source_digest import enrich_from_source


def build_publication_report(
    report: dict[str, Any],
    *,
    seat_matrix: dict[str, Any] | None = None,
    evidence_packet: dict[str, Any] | None = None,
    report_profile: str = "both",
    domain_hint: str = "auto",
    reader_type: str = "professional_user",
) -> dict[str, Any]:
    run_id = text_value(report.get("run_id"), "unknown")
    question = text_value(report.get("question") or report.get("title"))
    domain = detect_domain(question, report, domain_hint=domain_hint)
    model = empty_publication_report(
        run_id=run_id,
        question=question,
        domain=domain,
        report_profile=report_profile,
        reader_type=reader_type,
    )
    model["title"] = text_value(report.get("title")) or _title_for_domain(domain, question)
    model["subtitle"] = _subtitle_for_domain(domain)
    model["domain_label"] = DOMAIN_LABELS.get(domain, domain)

    base = build_base_publication(report, seat_matrix=seat_matrix, evidence_packet=evidence_packet)
    model["summary"] = base["summary"]
    model["metrics"] = base["metrics"]

    if report_profile in {"both", "base_only"}:
        model["base_blocks"] = base["base_blocks"]
    model["audit_blocks"] = base["audit_blocks"]

    if report_profile in {"both", "industry_only"}:
        model["industry_blocks"] = _industry_blocks(
            domain,
            report,
            seat_matrix=seat_matrix,
            evidence_packet=evidence_packet,
        )
    if report_profile == "audit_only":
        model["base_blocks"] = []
        model["industry_blocks"] = []

    model["reader_blocks"] = _reader_blocks(domain, report, model)
    enrich_from_source(model, report)
    model["quality"] = validate_publication_report(model)
    return model


def render_publication_bundle(model: dict[str, Any]) -> dict[str, str]:
    markdown = render_publication_markdown(model)
    html = render_publication_html(model)
    quality = validate_publication_report(model, html=html, markdown=markdown)
    model["quality"] = quality
    markdown = render_publication_markdown(model)
    html = render_publication_html(model)
    return {"markdown": markdown, "html": html}


def _industry_blocks(
    domain: str,
    report: dict[str, Any],
    *,
    seat_matrix: dict[str, Any] | None,
    evidence_packet: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if domain == "legal_memo":
        return build_legal_memo_blocks(report, seat_matrix=seat_matrix, evidence_packet=evidence_packet)
    if domain == "prediction_pool":
        return build_prediction_pool_blocks(report, seat_matrix=seat_matrix, evidence_packet=evidence_packet)
    return _generic_industry_blocks(domain, report)


def _generic_industry_blocks(domain: str, report: dict[str, Any]) -> list[dict[str, Any]]:
    from product.reporting.publication.schema import as_text_items, build_block, build_table

    return [
        build_block(
            f"{domain}_industry_frame",
            f"{DOMAIN_LABELS.get(domain, '行业')} · 专属版",
            kind="industry_frame",
            summary="该行业适配器先使用通用行业框架，后续可继续沉淀专属指标和表格。",
            table=build_table(
                ["模块", "当前内容"],
                [
                    ["核心判断", report.get("core_conclusion") or report.get("one_liner") or "暂无"],
                    ["关键风险", "\n".join(as_text_items(report.get("risks"), limit=5)) or "暂无"],
                    ["下一步", "\n".join(as_text_items(report.get("recommended_actions"), limit=5)) or "人工复核"],
                ],
            ),
            level="industry",
        )
    ]


def _title_for_domain(domain: str, question: str) -> str:
    if domain == "legal_memo":
        return "AI Judge 法律分析报告"
    if domain == "prediction_pool":
        return "AI Judge 预测池报告"
    if domain == "finance_risk":
        return "AI Judge 金融风险报告"
    if domain == "ops_check":
        return "AI Judge 工程验收报告"
    if domain == "business_strategy":
        return "AI Judge 商业策略报告"
    return "AI Judge 判断报告"


def _subtitle_for_domain(domain: str) -> str:
    if domain == "legal_memo":
        return "面向决策的法律阅读版"
    if domain == "prediction_pool":
        return "面向决策的预测池阅读版"
    return "面向决策的 AI Judge 阅读版"


def _reader_blocks(domain: str, report: dict[str, Any], model: dict[str, Any]) -> list[dict[str, Any]]:
    summary = model.get("summary") if isinstance(model.get("summary"), dict) else {}
    one_line = _reader_text(report.get("reader_one_line") or summary.get("one_line") or report.get("core_conclusion") or "")
    advice = _reader_items(report.get("reader_advice") or report.get("recommended_actions"), fallback=_default_advice(domain))
    basis = _reader_items(report.get("reader_basis") or report.get("consensus"), fallback=_default_basis(domain, report))
    risks = _reader_items(report.get("reader_risks") or report.get("risks"), fallback=_default_risks(domain))
    boundaries = _reader_items(report.get("reader_boundary") or report.get("boundaries"), fallback=_default_boundary(domain))
    return [
        build_block(
            "reader_one_line",
            "一句话判断",
            kind="reader",
            summary=one_line or "当前材料不足以形成稳定判断。",
            level="reader",
        ),
        build_block(
            "reader_advice",
            "当前建议",
            kind="reader",
            items=advice,
            level="reader",
        ),
        build_block(
            "reader_basis",
            "关键依据",
            kind="reader",
            items=basis,
            level="reader",
        ),
        build_block(
            "reader_risks",
            "最大风险",
            kind="reader",
            items=risks,
            level="reader",
        ),
        build_block(
            "reader_boundary",
            "适用边界",
            kind="reader",
            items=boundaries,
            level="reader",
        ),
    ]


def _reader_items(value: Any, *, fallback: list[str]) -> list[str]:
    items = [_reader_text(item) for item in as_text_items(value, limit=5, item_limit=220)]
    items = [item for item in items if item and not _is_system_item(item)]
    return items[:5] or fallback


def _reader_text(value: Any) -> str:
    text = str(value or "").strip()
    replacements = {
        "Noise Score": "判断波动",
        "schema": "格式",
        "historical_pdf_migration": "历史材料迁移",
        "structured_field_gap": "结构化字段缺口",
    }
    for raw, clean in replacements.items():
        text = text.replace(raw, clean)
    return text


def _is_system_item(text: str) -> bool:
    lowered = text.lower()
    system_tokens = (
        "artifact manifest",
        "model stability",
        "schema_failures",
        "pollution_count",
        "publication-output",
        "ai_judge.publication",
    )
    return any(token in lowered for token in system_tokens)


def _default_advice(domain: str) -> list[str]:
    if domain == "legal_memo":
        return [
            "先按结论判断可行方向，再由律师核对原始证据和最新规则。",
            "把可执行路径、证据缺口和程序风险分开处理。",
        ]
    if domain == "prediction_pool":
        return [
            "先把预测正确率和下注收益分开复盘。",
            "高共识但低赔率的场次允许预测但不下注。",
            "不把本样本直接作为真实下注建议。",
        ]
    return ["先采纳最稳健结论，再复核可能改变结论的风险。"]


def _default_basis(domain: str, report: dict[str, Any]) -> list[str]:
    evidence = report.get("evidence_strength") if isinstance(report.get("evidence_strength"), dict) else {}
    items = as_text_items(evidence.get("items"), limit=3, item_limit=180)
    if items:
        return [_reader_text(item) for item in items]
    if domain == "prediction_pool":
        return ["历史样本已按预测、下注、风险和复盘维度重新拆分。"]
    if domain == "legal_memo":
        return ["法律判断按结论、依据、事实、涵摄和复核清单分层呈现。"]
    return ["多席位判断已压缩成读者可执行的结论。"]


def _default_risks(domain: str) -> list[str]:
    if domain == "legal_memo":
        return ["原始证据、登记状态、执行案卷或最新规则变化可能改变结论。"]
    if domain == "prediction_pool":
        return ["赔率、阵容、赛果或数据源缺口可能改变逐场判断。"]
    return ["证据缺口或上下文变化可能改变当前判断。"]


def _default_boundary(domain: str) -> list[str]:
    if domain == "legal_memo":
        return ["这是办案研判底稿，不替代律师对证据、案卷和最新法源的复核。"]
    if domain == "prediction_pool":
        return ["这是格式验收和研究参考，不构成投注建议。"]
    return ["这是 AI Judge 的决策辅助报告，不替代人类最终判断。"]
