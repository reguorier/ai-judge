"""FDJP report blocks – Markdown and HTML render blocks for five-dimension audit.

Production-hardened: includes provider metadata, hybrid conflicts,
unsupported evidence warnings, and professional audit display data.
"""

from __future__ import annotations

import html as html_mod
from typing import Any

from product.fdjp.constants import DIMENSION_LABELS, DIMENSIONS


def build_fdjp_report_blocks(audit: dict[str, Any]) -> list[dict[str, Any]]:
    """Build structured report blocks for consumption by renderers."""
    gates = audit.get("gates", {})
    llm_meta = audit.get("llm_metadata", {})
    heur_meta = audit.get("heuristic_metadata", {})
    provider_meta = audit.get("provider_metadata", {})
    parse_meta = audit.get("parse_metadata", {})
    audit_mode = audit.get("audit_mode", audit.get("mode", "heuristic_only"))
    effective_mode = audit.get("effective_mode", audit_mode)
    hybrid_conflicts = audit.get("hybrid_conflicts", [])

    return [
        {
            "type": "fdjp_overview",
            "title": "FDJP 五维裁决协议",
            "status": audit.get("status"),
            "overall_score": audit.get("overall_score"),
            "dimension_scores": audit.get("dimension_scores"),
            "mode": audit.get("mode"),
            "audit_mode": audit_mode,
            "requested_mode": audit.get("requested_mode", audit_mode),
            "effective_mode": effective_mode,
            "warnings": gates.get("warnings", []),
            "blockers": gates.get("blockers", []),
            "llm_metadata": llm_meta,
            "heuristic_metadata": heur_meta,
            "provider_metadata": provider_meta,
            "parse_metadata": parse_meta,
            "hybrid_conflicts": hybrid_conflicts,
        },
        {
            "type": "fdjp_cross_dimension",
            "title": "五维交叉验证",
            "conflicts": audit.get("cross_dimension_conflicts", []),
            "hybrid_conflicts": hybrid_conflicts,
        },
        {
            "type": "fdjp_next_actions",
            "title": "五维行动建议",
            "actions": _extract_fdjp_actions(audit),
        },
    ]


def _extract_fdjp_actions(audit: dict[str, Any]) -> list[str]:
    """Extract actionable next-steps from dimension findings."""
    actions: list[str] = []
    dims = audit.get("dimensions", {})
    for dim in DIMENSIONS:
        dim_data = dims.get(dim, {})
        findings = dim_data.get("findings", [])
        for f in findings:
            if f.get("action_impact"):
                actions.append(f"【{DIMENSION_LABELS.get(dim, dim)}】{f['action_impact']}")
    if not actions:
        for dim in DIMENSIONS:
            dim_data = dims.get(dim, {})
            if dim_data.get("status") == "insufficient":
                actions.append(
                    f"【{DIMENSION_LABELS.get(dim, dim)}】信息不足，建议补充材料"
                )
    return actions[:10]


def build_fdjp_markdown_block(audit: dict[str, Any]) -> str:
    """Render FDJP audit as a Markdown section with professional audit info."""
    dim_scores = audit.get("dimension_scores", {})
    dims = audit.get("dimensions", {})
    gates = audit.get("gates", {})
    status = audit.get("status", "unknown")
    overall = audit.get("overall_score", 0)
    audit_mode = audit.get("audit_mode", audit.get("mode", "heuristic_only"))
    effective_mode = audit.get("effective_mode", audit_mode)
    llm_meta = audit.get("llm_metadata", {})
    provider_meta = audit.get("provider_metadata", {})
    parse_meta = audit.get("parse_metadata", {})
    hybrid_conflicts = audit.get("hybrid_conflicts", [])

    lines = [
        "## FDJP 五维裁决协议审计",
        "",
        f"**审计模式**：`{audit_mode}`（请求）→ `{effective_mode}`（实际）",
        "",
    ]

    # ── Professional audit display ──
    lines.append("### 专业审计信息")
    lines.append("")
    lines.append(f"- **audit_mode**: `{audit_mode}`")
    lines.append(f"- **effective_mode**: `{effective_mode}`")
    if provider_meta:
        lines.append(f"- **provider_kind**: `{provider_meta.get('provider_kind', 'none')}`")
        lines.append(f"- **model**: `{provider_meta.get('model', 'none')}`")
        lines.append(f"- **latency_ms**: `{provider_meta.get('latency_ms', 0)}`")
        lines.append(f"- **retry_count**: `{provider_meta.get('retry_count', 0)}`")
        lines.append(f"- **fallback_used**: `{provider_meta.get('fallback_used', False)}`")
    if parse_meta:
        unsup_ratio = parse_meta.get("unsupported_ratio", 0)
        lines.append(f"- **unsupported_evidence_ratio**: `{unsup_ratio}`")
        if parse_meta.get("parse_warnings"):
            lines.append(f"- **parse_warnings**: {parse_meta.get('parse_warnings')}")
    lines.append(f"- **status**: `{status}`")
    lines.append("")

    if llm_meta:
        lines.append("### LLM 审计元数据")
        lines.append("")
        for key in [
            "provider",
            "model",
            "attempted",
            "success",
            "latency_ms",
            "parse_success",
            "error_type",
            "error_message",
            "retry_count",
            "fallback_used",
            "raw_response_saved",
        ]:
            if key in llm_meta:
                lines.append(f"- **{key}**: `{llm_meta.get(key)}`")
        lines.append("")

    # ── Blockers ──
    blockers = gates.get("blockers", [])
    lines.append("### 阻塞项")
    if blockers:
        for b in blockers:
            lines.append(f"- `{b.get('blocker_id', '?')}`: {b.get('reason', '')}")
    else:
        lines.append("- 无")
    lines.append("")

    # ── Warnings ──
    warnings = gates.get("warnings", [])
    lines.append("### 警告项")
    if warnings:
        for w in warnings:
            lines.append(f"- `{w.get('warning_id', '?')}`: {w.get('reason', '')}")
    else:
        lines.append("- 无")
    lines.append("")

    # ── Dimension scores ──
    lines.append("| 维度 | 得分 | 核心发现 | 行动影响 |")
    lines.append("|---|---:|---|---|")
    for dim in DIMENSIONS:
        label = DIMENSION_LABELS.get(dim, dim)
        score = dim_scores.get(dim, 0)
        dim_data = dims.get(dim, {})
        summary = dim_data.get("summary", dim_data.get("claim", "未生成"))
        findings = dim_data.get("findings", [])
        action = findings[0].get("action_impact", "待补充") if findings else "待补充"
        lines.append(
            f"| {label} | {score:.2f} | {str(summary)[:60]} | {str(action)[:40]} |"
        )

    lines.extend([
        "",
        f"**FDJP 状态**：`{status}`",
        f"**整体认知分**：`{overall:.2f}`",
    ])

    # ── Hybrid conflicts ──
    if hybrid_conflicts:
        lines.append("")
        lines.append("### 混合审计冲突")
        for c in hybrid_conflicts:
            lines.append(
                f"- {c.get('dimension', '?')}: LLM=`{c.get('llm_status')}` "
                f"vs Heuristic=`{c.get('heuristic_status')}` "
                f"→ `{c.get('resolution')}`"
            )

    # ── Cross-dimension ──
    conflicts = audit.get("cross_dimension_conflicts", [])
    lines.append("")
    lines.append("### 五维交叉验证")
    if conflicts:
        for c in conflicts:
            lines.append(f"- {c.get('description', str(c))}")
    else:
        lines.append("- **共识**：各维度未发现明显冲突。")

    return "\n".join(lines)


def build_fdjp_html_block(audit: dict[str, Any]) -> str:
    """Render FDJP audit as an HTML section block with professional audit data."""
    dim_scores = audit.get("dimension_scores", {})
    dims = audit.get("dimensions", {})
    gates = audit.get("gates", {})
    status = audit.get("status", "unknown")
    overall = audit.get("overall_score", 0)
    audit_mode = audit.get("audit_mode", audit.get("mode", "heuristic_only"))
    effective_mode = audit.get("effective_mode", audit_mode)
    provider_meta = audit.get("provider_metadata", {})
    parse_meta = audit.get("parse_metadata", {})
    hybrid_conflicts = audit.get("hybrid_conflicts", [])

    def esc(s: Any) -> str:
        return html_mod.escape(str(s))

    overall_pct = round(overall * 100)

    rows = []
    for dim in DIMENSIONS:
        label = DIMENSION_LABELS.get(dim, dim)
        score = dim_scores.get(dim, 0)
        pct = round(score * 100)
        dim_data = dims.get(dim, {})
        summary = dim_data.get("summary", "未生成")
        findings = dim_data.get("findings", [])
        action = findings[0].get("action_impact", "待补充") if findings else "待补充"
        rows.append(
            f"<tr><td>{esc(label)}</td>"
            f"<td>{pct}%</td>"
            f"<td>{esc(summary[:80])}</td>"
            f"<td>{esc(action[:60])}</td></tr>"
        )

    status_tag = "tag-red" if "BLOCKED" in str(status) or "UNAVAILABLE" in str(status) else (
        "tag-amber" if "WARNINGS" in str(status) or "PARTIAL" in str(status) else "tag-green"
    )

    # Professional audit metadata
    audit_meta_rows = ""
    if provider_meta:
        audit_meta_rows += (
            f"<tr><td>provider_kind</td><td>{esc(provider_meta.get('provider_kind', ''))}</td></tr>"
            f"<tr><td>model</td><td>{esc(provider_meta.get('model', ''))}</td></tr>"
            f"<tr><td>latency_ms</td><td>{esc(provider_meta.get('latency_ms', 0))}</td></tr>"
            f"<tr><td>retry_count</td><td>{esc(provider_meta.get('retry_count', 0))}</td></tr>"
            f"<tr><td>fallback_used</td><td>{esc(provider_meta.get('fallback_used', False))}</td></tr>"
        )
    if parse_meta:
        audit_meta_rows += (
            f"<tr><td>unsupported_evidence_ratio</td><td>{esc(parse_meta.get('unsupported_ratio', 0))}</td></tr>"
        )

    blockers_html = ""
    for b in gates.get("blockers", []):
        blockers_html += (
            f'<div class="fdjp-blocker">{esc(b.get("blocker_id", ""))}: '
            f'{esc(b.get("reason", ""))}</div>'
        )

    warnings_html = ""
    for w in gates.get("warnings", []):
        warnings_html += (
            f'<div class="fdjp-warning">{esc(w.get("warning_id", ""))}: '
            f'{esc(w.get("reason", ""))}</div>'
        )

    conflicts_html = ""
    for c in hybrid_conflicts:
        conflicts_html += (
            f'<div class="fdjp-conflict">{esc(c.get("dimension", ""))}: '
            f'LLM={esc(c.get("llm_status", ""))} vs Heuristic={esc(c.get("heuristic_status", ""))} '
            f'→ {esc(c.get("resolution", ""))}</div>'
        )

    return f"""<div class="section fdjp-section">
  <h2>FDJP 五维裁决协议</h2>
  <div class="card fdjp-overview-card">
    <div class="fdjp-status-row">
      <span class="tag {status_tag}">{esc(status)}</span>
      <span class="tag tag-blue">Overall {overall_pct}%</span>
      <span class="tag tag-amber">{esc(audit_mode)} → {esc(effective_mode)}</span>
    </div>
    <h3>专业审计信息</h3>
    <table class="fdjp-meta-table">
      {audit_meta_rows}
    </table>
    <h3>维度得分</h3>
    <table class="fdjp-table">
      <tr><th>维度</th><th>得分</th><th>核心发现</th><th>行动影响</th></tr>
      {''.join(rows)}
    </table>
    {blockers_html}
    {warnings_html}
    {conflicts_html}
  </div>
</div>"""
