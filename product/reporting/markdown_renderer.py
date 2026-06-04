"""Markdown renderer for the client-first final report."""

from __future__ import annotations

from typing import Any


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
    lines = [
        "# AI Judge 最终报告",
        "",
        f"Run ID: `{report.get('run_id', 'unknown')}`",
        f"模式: {report.get('mode_label', report.get('mode', 'unknown'))}",
        "",
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
        "## 10. 审计附件",
        f"- 生成时间：{audit.get('generated_at', 'unknown')}",
        f"- 有效席位：{audit.get('valid_seats', 'unknown')}",
        f"- 失败席位：{audit.get('failed_seats', 'unknown')}",
    ]
    for path in audit.get("artifact_paths", []):
        lines.append(f"- artifact: `{path}`")
    lines.append("")
    return "\n".join(lines)
