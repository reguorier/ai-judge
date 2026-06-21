"""Publication-grade report view model helpers for AI Judge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


PUBLICATION_SCHEMA_VERSION = "ai_judge.publication_report.v2"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def text_value(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def clip_text(value: Any, limit: int = 360, default: str = "") -> str:
    text = text_value(value, default=default)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def as_text_items(value: Any, *, limit: int = 8, item_limit: int = 260) -> list[str]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else [value]
    items: list[str] = []
    for item in raw_items:
        if isinstance(item, dict):
            text = (
                item.get("text")
                or item.get("fact")
                or item.get("summary")
                or item.get("description")
                or item.get("action")
                or item.get("risk")
                or item.get("title")
                or ""
            )
            source = item.get("source")
            strength = item.get("strength")
            suffix_parts = []
            if strength:
                suffix_parts.append(f"强度：{strength}")
            if source:
                suffix_parts.append(f"来源：{source}")
            suffix = f"（{'；'.join(suffix_parts)}）" if suffix_parts else ""
            text = f"{text}{suffix}"
        else:
            text = str(item)
        text = clip_text(text, item_limit)
        if text:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def build_metric(label: str, value: Any, tone: str = "neutral", hint: str = "") -> dict[str, str]:
    return {
        "label": text_value(label),
        "value": text_value(value, "-"),
        "tone": text_value(tone, "neutral"),
        "hint": clip_text(hint, 120),
    }


def build_card(
    title: str,
    value: Any = "",
    body: Any = "",
    tone: str = "neutral",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "title": text_value(title),
        "value": clip_text(value, 220),
        "body": clip_text(body, 420),
        "tone": text_value(tone, "neutral"),
        "meta": meta or {},
    }


def build_table(columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    clean_rows = []
    for row in rows:
        clean_rows.append([clip_text(cell, 260) for cell in row[: len(columns)]])
    return {
        "columns": [text_value(col) for col in columns],
        "rows": clean_rows,
    }


def build_block(
    block_id: str,
    title: str,
    *,
    kind: str = "section",
    summary: Any = "",
    items: list[Any] | None = None,
    metrics: list[dict[str, Any]] | None = None,
    cards: list[dict[str, Any]] | None = None,
    table: dict[str, Any] | None = None,
    level: str = "base",
) -> dict[str, Any]:
    return {
        "id": text_value(block_id),
        "title": text_value(title),
        "kind": text_value(kind, "section"),
        "level": text_value(level, "base"),
        "summary": clip_text(summary, 800),
        "items": as_text_items(items or [], limit=12, item_limit=320),
        "metrics": metrics or [],
        "cards": cards or [],
        "table": table or {"columns": [], "rows": []},
    }


def empty_publication_report(
    *,
    run_id: str,
    question: str,
    domain: str = "general_decision",
    report_profile: str = "both",
    reader_type: str = "professional_user",
) -> dict[str, Any]:
    return {
        "schema": PUBLICATION_SCHEMA_VERSION,
        "run_id": text_value(run_id, "unknown"),
        "question": text_value(question),
        "title": "AI Judge 判断报告",
        "subtitle": "基础版 + 行业版 + 审计版",
        "domain": text_value(domain, "general_decision"),
        "report_profile": text_value(report_profile, "both"),
        "reader_type": text_value(reader_type, "professional_user"),
        "generated_at": utc_now_iso(),
        "summary": {},
        "metrics": [],
        "base_blocks": [],
        "industry_blocks": [],
        "audit_blocks": [],
        "quality": {},
    }
