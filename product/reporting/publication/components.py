"""Component registry for schema-driven publication rendering."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from product.reporting.publication.html_nodes import HtmlNode, h
from product.reporting.publication.judge_ir import IRComponent


ComponentRenderer = Callable[[dict[str, Any]], HtmlNode]


class ComponentRegistry:
    """Maps JudgeIR component types to deterministic renderers."""

    def __init__(self) -> None:
        self._renderers: dict[str, ComponentRenderer] = {}

    def register(self, component_type: str, renderer: ComponentRenderer) -> None:
        self._renderers[component_type] = renderer

    def render(self, component: IRComponent) -> HtmlNode:
        renderer = self._renderers.get(component.type)
        if renderer is None:
            raise KeyError(f"unregistered_component:{component.type}")
        return renderer(component.props)


def default_component_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register("MetricGrid", _metric_grid)
    registry.register("ModelComparisonTable", _model_comparison_table)
    registry.register("RiskMatrix", _risk_matrix)
    registry.register("EvidenceBlock", _evidence_block)
    registry.register("RailSummary", _rail_summary)
    registry.register("AppendixPanel", _appendix_panel)
    return registry


def _rail_summary(props: dict[str, Any]) -> HtmlNode:
    variant = _text(props.get("variant"), "hero")
    if variant == "rail":
        metrics = props.get("metrics") if isinstance(props.get("metrics"), list) else []
        return h(
            "aside",
            {"class": "rail", "aria-label": "决策摘要"},
            [
                h("div", {"class": "rail-head"}, "决策摘要"),
                h(
                    "section",
                    {"class": "rail-section"},
                    [
                        h("p", {"class": "rail-label"}, "核心判断"),
                        h("p", {"class": "rail-lead"}, _text(props.get("summary"), "暂无稳定判断。")),
                    ],
                ),
                h(
                    "section",
                    {"class": "rail-section"},
                    [
                        h("p", {"class": "rail-label"}, "关键指标"),
                        h("div", {"class": "rail-metrics"}, _rail_metric_nodes(metrics[:4])),
                    ],
                ),
                h(
                    "section",
                    {"class": "rail-section"},
                    [
                        h("p", {"class": "rail-label"}, "质量门禁"),
                        h("span", {"class": "status-pill"}, _quality_label(props.get("quality"))),
                    ],
                ),
            ],
        )

    meta = props.get("meta") if isinstance(props.get("meta"), list) else []
    return h(
        "section",
        {"class": "doc-head", "id": "section-summary"},
        [
            h(
                "div",
                {"class": "doc-head-main"},
                [
                    h("p", {"class": "kicker"}, "AI Judge 专业审阅"),
                    h("h1", children=_text(props.get("title"), "AI Judge 判断报告")),
                    h("p", {"class": "subtitle"}, _text(props.get("subtitle"), "面向决策的 AI Judge 阅读版")),
                    h("p", {"class": "cover-lead"}, _text(props.get("summary"), "当前材料不足以形成稳定判断。")),
                ],
            ),
            h("aside", {"class": "meta-card", "aria-label": "report metadata"}, _meta_nodes(meta)),
        ],
    )


def _metric_grid(props: dict[str, Any]) -> HtmlNode:
    metrics = props.get("metrics") if isinstance(props.get("metrics"), list) else []
    return h(
        "section",
        {"class": "metric-band", "id": "section-metrics"},
        [
            h("div", {"class": "section-kicker"}, _text(props.get("title"), "关键指标")),
            h("div", {"class": "headline-metrics"}, _metric_nodes(metrics)),
        ],
    )


def _evidence_block(props: dict[str, Any]) -> HtmlNode:
    return h(
        "article",
        {"class": "reader-section evidence-block", "id": _text(props.get("anchor"), "")},
        [
            _section_label(props),
            h(
                "div",
                {"class": "reader-content"},
                [
                    _summary_node(props.get("summary")),
                    _items_node(props.get("items")),
                ],
            ),
        ],
    )


def _model_comparison_table(props: dict[str, Any]) -> HtmlNode:
    table = props.get("table") if isinstance(props.get("table"), dict) else {}
    return h(
        "article",
        {"class": "reader-section comparison-block", "id": _text(props.get("anchor"), "")},
        [
            _section_label(props),
            h(
                "div",
                {"class": "reader-content wide-content"},
                [
                    _summary_node(props.get("summary")),
                    _table_node(table),
                ],
            ),
        ],
    )


def _risk_matrix(props: dict[str, Any]) -> HtmlNode:
    risks = props.get("risks") if isinstance(props.get("risks"), list) else []
    cards = []
    for index, risk in enumerate(risks, start=1):
        risk_text = _text(risk.get("risk") if isinstance(risk, dict) else risk, "")
        control = _text(risk.get("control") if isinstance(risk, dict) else "", "回源核对后再采纳")
        severity = _text(risk.get("severity") if isinstance(risk, dict) else "", "medium")
        cards.append(
            h(
                "div",
                {"class": f"risk-card risk-{severity}"},
                [
                    h("span", {"class": "risk-index"}, f"{index:02d}"),
                    h("strong", children=risk_text),
                    h("p", children=control),
                ],
            )
        )
    return h(
        "article",
        {"class": "reader-section risk-block", "id": "section-risk"},
        [
            _section_label(props),
            h("div", {"class": "reader-content"}, [h("div", {"class": "risk-grid"}, cards)]),
        ],
    )


def _appendix_panel(props: dict[str, Any]) -> HtmlNode:
    groups = props.get("groups") if isinstance(props.get("groups"), list) else []
    details = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        blocks = group.get("blocks") if isinstance(group.get("blocks"), list) else []
        if not blocks:
            continue
        details.append(
            h(
                "details",
                {"class": "appendix", "id": _text(group.get("anchor"), "")},
                [
                    h("summary", children=_text(group.get("title"), "附录")),
                    h("div", {"class": "appendix-body"}, [_block_node(block) for block in blocks if isinstance(block, dict)]),
                ],
            )
        )
    return h("section", {"class": "appendix-panel", "id": "section-appendix"}, details)


def _section_label(props: dict[str, Any]) -> HtmlNode:
    return h(
        "div",
        {"class": "section-label"},
        [
            h("span", {"class": "section-index"}, _text(props.get("index"), "00")),
            h("h2", children=_text(props.get("title"), "正文")),
        ],
    )


def _meta_nodes(meta: list[Any]) -> list[HtmlNode]:
    nodes: list[HtmlNode] = []
    for item in meta:
        if not isinstance(item, dict):
            continue
        nodes.append(
            h(
                "div",
                children=[
                    h("span", children=_text(item.get("label"), "-")),
                    h("strong", children=_text(item.get("value"), "-")),
                ],
            )
        )
    return nodes


def _metric_nodes(metrics: list[Any]) -> list[HtmlNode]:
    nodes: list[HtmlNode] = []
    for metric in metrics[:4]:
        if not isinstance(metric, dict):
            continue
        nodes.append(
            h(
                "div",
                {"class": "headline-metric"},
                [
                    h("span", children=_text(metric.get("label"), "-")),
                    h("strong", children=_text(metric.get("value"), "-")),
                ],
            )
        )
    return nodes


def _rail_metric_nodes(metrics: list[Any]) -> list[HtmlNode]:
    nodes: list[HtmlNode] = []
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        nodes.append(
            h(
                "div",
                {"class": "rail-metric"},
                [
                    h("span", children=_text(metric.get("label"), "-")),
                    h("strong", children=_text(metric.get("value"), "-")),
                ],
            )
        )
    return nodes


def _summary_node(summary: Any) -> HtmlNode | None:
    text = _text(summary, "")
    if not text:
        return None
    return h("p", children=text)


def _items_node(items: Any) -> HtmlNode | None:
    if not isinstance(items, list) or not items:
        return None
    return h("ul", children=[h("li", children=_text(item, "")) for item in items if _text(item, "")])


def _table_node(table: dict[str, Any]) -> HtmlNode | None:
    columns = table.get("columns") if isinstance(table.get("columns"), list) else []
    rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    if not columns or not rows:
        return None
    return h(
        "div",
        {"class": "table-wrap"},
        h(
            "table",
            children=[
                h("thead", children=h("tr", children=[h("th", children=_text(col, "")) for col in columns])),
                h(
                    "tbody",
                    children=[
                        h("tr", children=[h("td", children=_text(cell, "")) for cell in row[: len(columns)]])
                        for row in rows
                    ],
                ),
            ],
        ),
    )


def _block_node(block: dict[str, Any]) -> HtmlNode:
    return h(
        "article",
        {"class": "report-block"},
        [
            h("h3", children=_text(block.get("title") or block.get("id"), "报告模块")),
            _summary_node(block.get("summary")),
            _appendix_metrics(block.get("metrics")),
            _appendix_cards(block.get("cards")),
            _items_node(block.get("items")),
            _table_node(block.get("table") if isinstance(block.get("table"), dict) else {}),
        ],
    )


def _appendix_metrics(metrics: Any) -> HtmlNode | None:
    if not isinstance(metrics, list) or not metrics:
        return None
    cells = []
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        cells.append(
            h(
                "div",
                {"class": "metric"},
                [
                    h("span", children=_text(metric.get("label"), "-")),
                    h("strong", children=_text(metric.get("value"), "-")),
                ],
            )
        )
    return h("div", {"class": "metric-grid"}, cells) if cells else None


def _appendix_cards(cards: Any) -> HtmlNode | None:
    if not isinstance(cards, list) or not cards:
        return None
    nodes = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        nodes.append(
            h(
                "div",
                {"class": "card"},
                [
                    h("span", children=_text(card.get("title"), "-")),
                    h("div", {"class": "card-value"}, _text(card.get("value"), "")),
                    h("p", children=_text(card.get("body"), "")),
                ],
            )
        )
    return h("div", {"class": "card-grid"}, nodes) if nodes else None


def _quality_label(value: Any) -> str:
    quality = value if isinstance(value, dict) else {}
    status = _text(quality.get("status"), "unknown")
    publishable = "可发布" if quality.get("publishable") else "需复核"
    return f"{status} · {publishable}"


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


DEFAULT_COMPONENT_REGISTRY = default_component_registry()
