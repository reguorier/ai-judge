"""Markdown renderer for the client-first final report.

Minimal change: FDJP section already handled by build_fdjp_markdown_block
which now includes professional audit display (provider metadata, hybrid conflicts,
unsupported evidence ratio, etc.). No style changes needed.
"""

from __future__ import annotations

from typing import Any

from core.model_stability import render_model_stability_markdown
from core.noise_audit import render_noise_markdown


def _bullet(items: list[Any]) -> str:
    if not items:
        return "- unknown"
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text") or item.get("fact") or item.get("summary") or item.get("description") or str(item)
            source = item.get("source")
            strength = item.get("strength")
            suffix = ""
            if strength:
                suffix += f"（强度：{strength}）"
            if source:
                suffix += f"（来源：{source}）"
            lines.append(f"- {text}{suffix}")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def render_final_report_markdown(report: dict[str, Any]) -> str:
    audit = report.get("audit", {})
    evidence = report.get("evidence_strength", {})
    fdjp_audit = report.get("fdjp_audit")

    lines = [
        "# AI Judge 最终报告",
        "",
        f"Run ID: `{report.get('run_id', 'unknown')}`",
        f"模式: {report.get('mode_label', report.get('mode', 'unknown'))}",
        "",
    ]

    # ── FDJP Five-Dimension Audit Section ──
    if fdjp_audit and isinstance(fdjp_audit, dict):
        try:
            from product.fdjp.report_blocks import build_fdjp_markdown_block
            lines.append(build_fdjp_markdown_block(fdjp_audit))
            lines.append("")
        except Exception as exc:
            fdjp_audit["status"] = "FDJP_AUDIT_UNAVAILABLE"
            fdjp_audit["error_type"] = type(exc).__name__
            fdjp_audit["error_message"] = str(exc)
            fdjp_audit["release_blocker"] = False
            fdjp_audit["report_can_render"] = True

    lines.extend([
        "## 1. 核心结论",
        report.get("core_conclusion") or "unknown",
        "",
        "## 2. 适用边界",
        report.get("scope") or "unknown",
        "",
        "## 3. 已验证事实",
        _bullet(report.get("verified_facts", [])),
        "",
        "## 4. 推断与判断",
        _bullet(report.get("inferences", [])),
        "",
        "## 5. 席位观点摘要",
        _bullet(report.get("seat_summaries", [])),
        "",
        "## 6. 共识与分歧",
        "### 共识",
        _bullet(report.get("consensus", [])),
        "",
        "### 分歧",
        _bullet(report.get("disagreements", [])),
        "",
        "## 7. 证据强度",
        f"整体强度：{evidence.get('overall', 'unknown')}",
        "",
        _bullet(evidence.get("items", [])),
        "",
        "## 8. 风险与失败条件",
        "### 风险",
        _bullet(report.get("risks", [])),
        "",
        "### 失败条件",
        _bullet(report.get("failure_conditions", [])),
        "",
        "## 9. 推荐行动",
        _bullet(report.get("recommended_actions", [])),
        "",
    ])
    noise_lines = render_noise_markdown(report.get("noise_audit"))
    if noise_lines:
        lines.extend(noise_lines)
        lines.append("")
    stability_lines = render_model_stability_markdown(report.get("model_stability"))
    if stability_lines:
        lines.extend(stability_lines)
        lines.append("")
    lines.extend([
        _audit_attachment_heading(noise_lines=bool(noise_lines), stability_lines=bool(stability_lines)),
        f"- 生成时间：{audit.get('generated_at', 'unknown')}",
        f"- 有效席位：{audit.get('valid_seats', 'unknown')}",
        f"- 失败席位：{audit.get('failed_seats', 'unknown')}",
    ])
    for path in audit.get("artifact_paths", []):
        lines.append(f"- artifact: `{path}`")
    lines.append("")
    return "\n".join(lines)


def _audit_attachment_heading(*, noise_lines: bool, stability_lines: bool) -> str:
    if noise_lines and stability_lines:
        return "## 12. 审计附件"
    if noise_lines or stability_lines:
        return "## 11. 审计附件"
    return "## 10. 审计附件"
