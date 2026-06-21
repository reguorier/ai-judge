"""Schema-driven HTML renderer for client-first final reports."""

from __future__ import annotations

from typing import Any

from product.reporting.publication import build_publication_report, render_publication_html
from product.reporting.publication.judge_ir import JudgeIR
from product.reporting.publication.layout_compiler import compile_judge_ir


def render_final_report_html(report: dict[str, Any]) -> str:
    """Render client final reports through JudgeIR and registered components."""

    model = build_final_report_publication_model(report)
    return render_publication_html(model)


def build_final_report_judge_ir(report: dict[str, Any]) -> JudgeIR:
    """Build the exact JudgeIR used by the client HTML renderer."""

    return compile_judge_ir(build_final_report_publication_model(report))


def build_final_report_publication_model(report: dict[str, Any]) -> dict[str, Any]:
    """Adapt a client final report to the publication model before IR compile."""

    payload = dict(report)
    payload.setdefault("title", report.get("title") or report.get("question") or "AI Judge 最终报告")
    payload.setdefault("question", report.get("question") or report.get("title") or "")
    payload.setdefault("core_conclusion", report.get("core_conclusion") or report.get("one_liner") or "")
    payload.setdefault("recommended_actions", report.get("recommended_actions") or report.get("next_steps") or [])
    payload.setdefault("risks", report.get("risks") or report.get("failure_conditions") or [])
    payload.setdefault("mode_label", report.get("mode_label") or report.get("mode") or "AI Judge")

    model = build_publication_report(
        payload,
        domain_hint=_domain_hint(payload),
        report_profile="both",
        reader_type="professional_user",
    )
    audit = report.get("audit") if isinstance(report.get("audit"), dict) else {}
    if audit.get("generated_at"):
        model["generated_at"] = str(audit["generated_at"])
    return model


def _domain_hint(report: dict[str, Any]) -> str:
    question = str(report.get("question") or report.get("title") or "")
    mode = str(report.get("mode") or "")
    if mode == "prediction_pool" or "预测池" in question or "世界杯" in question:
        return "prediction_pool"
    if mode == "deep_judge" or any(token in question for token in ("法律", "法院", "股权", "合同", "债务", "破产")):
        return "legal_memo"
    return "auto"
