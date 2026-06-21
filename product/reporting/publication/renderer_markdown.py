"""Reader-first Markdown renderer for Publication Output V2."""

from __future__ import annotations

from typing import Any


def render_publication_markdown(model: dict[str, Any]) -> str:
    lines: list[str] = [
        f"# {model.get('title') or 'AI Judge 判断报告'}",
        "",
        f"> {model.get('subtitle') or '面向决策的 AI Judge 阅读版'}",
        "",
    ]

    reader_blocks = [block for block in model.get("reader_blocks") or [] if isinstance(block, dict)]
    for block in reader_blocks:
        _render_reader_block(lines, block)

    lines.extend([
        "## 延伸材料",
        "",
        "- [A. 行业展开](#附录-a-行业展开)",
        "- [B. 证据与来源](#附录-b-证据与来源)",
        "- [C. 系统审计](#附录-c-系统审计)",
        "",
        "---",
        "",
    ])

    _render_appendix(lines, "附录 A. 行业展开", model.get("industry_blocks") or [])
    _render_appendix(lines, "附录 B. 证据与来源", model.get("base_blocks") or [])
    _render_appendix(lines, "附录 C. 系统审计", model.get("audit_blocks") or [])

    quality = model.get("quality") if isinstance(model.get("quality"), dict) else {}
    lines.extend([
        "### 输出质量门禁",
        "",
        f"- 状态: {quality.get('status', 'unknown')}",
        f"- 可发布: {quality.get('publishable', False)}",
    ])
    for error in quality.get("errors") or []:
        lines.append(f"- error: {error}")
    for warning in quality.get("warnings") or []:
        lines.append(f"- warning: {warning}")
    lines.append("")
    return "\n".join(lines)


def _render_reader_block(lines: list[str], block: dict[str, Any]) -> None:
    lines.extend([f"## {block.get('title') or block.get('id')}", ""])
    if block.get("summary"):
        lines.extend([str(block["summary"]), ""])
    for item in block.get("items") or []:
        lines.append(f"- {item}")
    if block.get("items"):
        lines.append("")


def _render_appendix(lines: list[str], title: str, blocks: list[Any]) -> None:
    clean = [block for block in blocks if isinstance(block, dict)]
    if not clean:
        return
    lines.extend([f"## {title}", ""])
    for block in clean:
        _render_block(lines, block)


def _render_block(lines: list[str], block: dict[str, Any]) -> None:
    lines.extend([f"### {block.get('title') or block.get('id')}", ""])
    if block.get("summary"):
        lines.extend([str(block["summary"]), ""])
    metrics = block.get("metrics") if isinstance(block.get("metrics"), list) else []
    for metric in metrics:
        lines.append(f"- **{metric.get('label', '-')}**: {metric.get('value', '-')}")
    if metrics:
        lines.append("")
    cards = block.get("cards") if isinstance(block.get("cards"), list) else []
    for card in cards:
        title = card.get("title", "-")
        value = card.get("value", "")
        body = card.get("body", "")
        lines.append(f"- **{title}**: {value} {body}".strip())
    if cards:
        lines.append("")
    items = block.get("items") if isinstance(block.get("items"), list) else []
    for item in items:
        lines.append(f"- {item}")
    if items:
        lines.append("")
    table = block.get("table") if isinstance(block.get("table"), dict) else {}
    columns = table.get("columns") if isinstance(table.get("columns"), list) else []
    rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    if columns and rows:
        lines.append("| " + " | ".join(str(col) for col in columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        for row in rows:
            cells = [str(cell).replace("\n", "<br>") for cell in row[: len(columns)]]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
