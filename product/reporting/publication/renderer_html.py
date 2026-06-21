"""Schema-driven HTML renderer for AI Judge publication reports."""

from __future__ import annotations

from typing import Any

from product.reporting.publication.components import (
    DEFAULT_COMPONENT_REGISTRY,
    ComponentRegistry,
)
from product.reporting.publication.html_nodes import HtmlNode, h, render_document
from product.reporting.publication.judge_ir import JudgeIR
from product.reporting.publication.layout_compiler import compile_judge_ir
from product.reporting.publication.render_contract import validate_judge_ir


def render_publication_html(model: dict[str, Any]) -> str:
    """Compile a publication model to JudgeIR, validate it, and render HTML."""

    ir = compile_judge_ir(model)
    return render_judge_ir_html(ir)


def render_judge_ir_html(
    ir: JudgeIR,
    *,
    registry: ComponentRegistry = DEFAULT_COMPONENT_REGISTRY,
) -> str:
    """Render validated JudgeIR through registered components only."""

    ir = validate_judge_ir(ir)
    return render_document(_head(ir), _body(ir, registry))


def _head(ir: JudgeIR) -> list[HtmlNode]:
    return [
        h("meta", {"charset": "utf-8"}),
        h("meta", {"content": "width=device-width, initial-scale=1", "name": "viewport"}),
        h("meta", {"content": "judge-ir-component-renderer", "name": "ai-judge-renderer"}),
        h("title", children=ir.title),
        h("style", children=CSS),
    ]


def _body(ir: JudgeIR, registry: ComponentRegistry) -> list[HtmlNode]:
    return [
        _topbar(ir),
        h(
            "div",
            {"class": "workspace"},
            [
                _side_nav(ir),
                h("main", {"class": "doc"}, _main_sections(ir, registry)),
                registry.render(ir.rail),
            ],
        ),
    ]


def _topbar(ir: JudgeIR) -> HtmlNode:
    return h(
        "header",
        {"class": "topbar"},
        [
            h(
                "div",
                {"class": "brand"},
                [
                    h("span", {"class": "brand-mark"}, "AJ"),
                    h("span", {"class": "brand-title"}, ir.title),
                ],
            ),
            h(
                "nav",
                {"class": "actions", "aria-label": "report actions"},
                [
                    h("a", {"href": "#section-analysis"}, "正文"),
                    h("a", {"href": "#section-appendix"}, "延伸材料"),
                    h("button", {"type": "button", "onclick": "window.print()"}, "打印 / 导出 PDF"),
                ],
            ),
        ],
    )


def _side_nav(ir: JudgeIR) -> HtmlNode:
    labels = {
        "summary": "核心摘要",
        "metrics": "关键指标",
        "analysis": "专业分析",
        "comparison": "模型比较",
        "risk": "风险矩阵",
        "appendix": "延伸材料",
    }
    links = []
    for index, section in enumerate(ir.sections, start=1):
        label = labels.get(section.slot, section.title)
        links.append(
            h(
                "a",
                {"href": f"#section-{section.slot}"},
                [
                    h("span", {"class": "toc-index"}, f"{index:02d}"),
                    h("span", children=label),
                ],
            )
        )
    return h(
        "aside",
        {"class": "side", "aria-label": "审阅目录"},
        [
            h("div", {"class": "side-head"}, "审阅目录"),
            h("nav", {"class": "toc"}, links),
        ],
    )


def _main_sections(ir: JudgeIR, registry: ComponentRegistry) -> list[HtmlNode]:
    nodes: list[HtmlNode] = []
    for section in ir.sections:
        rendered = [registry.render(component) for component in section.components]
        if section.slot in {"analysis", "comparison"}:
            nodes.append(
                h(
                    "section",
                    {"class": f"reader reader-{section.slot}", "id": f"section-{section.slot}"},
                    rendered,
                )
            )
        elif section.slot == "risk":
            nodes.append(h("section", {"class": "reader reader-risk"}, rendered))
        else:
            nodes.extend(rendered)
    return nodes


CSS = """
:root {
  color-scheme: light;
  --canvas:#e4ebe7;
  --paper:#fffdf8;
  --paper-2:#f6f4ef;
  --ink:#171717;
  --ink-2:#35302a;
  --muted:#766f63;
  --line:#d8cdbc;
  --line-strong:#b8ad9b;
  --accent:#9b3728;
  --accent-2:#164b43;
  --accent-soft:#f4dfd8;
  --green-soft:#dfe9e4;
  --shadow:0 24px 80px rgba(42,34,24,.10);
  --ease:cubic-bezier(.32,.72,0,1);
}
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body {
  margin:0;
  font-family:"Avenir Next","PingFang SC","SF Pro Text","Microsoft YaHei",system-ui,sans-serif;
  background:
    linear-gradient(90deg, rgba(23,23,23,.026) 1px, transparent 1px) 0 0/30px 30px,
    linear-gradient(180deg, #f5f4ef, #e5ebe7 46%, var(--canvas));
  color:var(--ink);
  letter-spacing:0;
  font-size:15px;
}
body::before {
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  background:radial-gradient(circle at 18% 8%, rgba(155,55,40,.08), transparent 34%),
             radial-gradient(circle at 82% 10%, rgba(22,75,67,.09), transparent 30%);
  opacity:.9;
}
a { color:inherit; }
.topbar {
  position:sticky;
  top:0;
  z-index:10;
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:20px;
  height:58px;
  padding:0 24px;
  background:rgba(255,253,248,.90);
  border-bottom:1px solid rgba(74,60,44,.14);
  backdrop-filter:blur(18px);
}
.brand {
  display:flex;
  align-items:center;
  gap:12px;
  min-width:0;
  font-weight:820;
}
.brand-mark {
  width:28px;
  height:28px;
  border-radius:8px;
  display:grid;
  place-items:center;
  background:var(--ink);
  color:var(--paper);
  font-size:11px;
  letter-spacing:0;
}
.brand-title {
  min-width:0;
  overflow:hidden;
  white-space:nowrap;
  text-overflow:ellipsis;
}
.actions { display:flex; align-items:center; gap:8px; }
.actions a, .actions button {
  border:1px solid var(--line);
  border-radius:8px;
  background:rgba(255,253,248,.76);
  padding:8px 11px;
  font:inherit;
  font-weight:760;
  text-decoration:none;
  cursor:pointer;
  transition:transform .45s var(--ease), background .45s var(--ease), border-color .45s var(--ease);
}
.actions a:hover, .actions button:hover {
  transform:translateY(-1px);
  background:var(--paper);
  border-color:var(--line-strong);
}
.workspace {
  position:relative;
  width:min(1480px, calc(100vw - 28px));
  margin:22px auto 64px;
  display:grid;
  grid-template-columns:216px minmax(0, 1fr) 300px;
  gap:18px;
  align-items:start;
}
.side, .rail {
  position:sticky;
  top:78px;
  border:1px solid rgba(74,60,44,.14);
  border-radius:10px;
  background:rgba(255,253,248,.68);
  box-shadow:0 16px 52px rgba(42,34,24,.06);
  backdrop-filter:blur(16px);
  overflow:hidden;
}
.side-head, .rail-head {
  padding:14px 15px;
  border-bottom:1px solid var(--line);
  font-size:11px;
  color:var(--muted);
  font-weight:900;
  letter-spacing:0;
}
.toc { display:grid; padding:8px; gap:2px; }
.toc a {
  display:grid;
  grid-template-columns:30px 1fr;
  gap:8px;
  align-items:start;
  padding:10px 8px;
  border-radius:8px;
  text-decoration:none;
  color:var(--ink-2);
  line-height:1.35;
  font-weight:720;
}
.toc a:hover { background:rgba(155,55,40,.08); }
.toc-index { color:var(--accent); font-size:11px; font-weight:900; letter-spacing:0; }
.doc {
  min-width:0;
  border:1px solid rgba(74,60,44,.16);
  border-radius:8px;
  background:linear-gradient(180deg, rgba(255,253,248,.98), rgba(253,248,238,.98));
  box-shadow:var(--shadow);
  overflow:hidden;
}
.doc-head {
  display:grid;
  grid-template-columns:minmax(0,1fr) 218px;
  gap:28px;
  padding:34px 42px 22px;
  border-bottom:1px solid var(--line);
  background:linear-gradient(135deg, rgba(255,253,248,.94), rgba(246,244,239,.92));
}
.kicker {
  margin:0 0 14px;
  color:var(--accent-2);
  font-size:11px;
  letter-spacing:0;
  font-weight:950;
}
h1 {
  margin:0;
  max-width:26ch;
  font-family:"Avenir Next","PingFang SC","SF Pro Display","Microsoft YaHei",system-ui,sans-serif;
  font-size:36px;
  line-height:1.18;
  font-weight:820;
  letter-spacing:0;
  word-break:keep-all;
}
.subtitle {
  margin:16px 0 0;
  color:var(--muted);
  line-height:1.7;
  font-size:16px;
  max-width:58ch;
}
.cover-lead {
  margin:20px 0 0;
  padding:16px 18px;
  border-left:4px solid var(--accent);
  background:linear-gradient(135deg, rgba(244,223,216,.74), rgba(255,253,248,.72));
  font-size:16px;
  line-height:1.72;
  font-weight:680;
  color:var(--ink);
}
.meta-card {
  align-self:end;
  border-left:3px solid var(--accent);
  padding-left:16px;
  display:grid;
  gap:12px;
  font-size:12px;
}
.meta-card div { display:grid; gap:3px; }
.meta-card span { color:var(--muted); font-weight:850; }
.meta-card strong { overflow-wrap:anywhere; }
.metric-band {
  padding:0 42px 24px;
  border-bottom:1px solid var(--line);
  background:linear-gradient(135deg, rgba(255,253,248,.94), rgba(246,244,239,.88));
}
.section-kicker {
  padding:16px 0 10px;
  color:var(--muted);
  font-size:12px;
  font-weight:860;
}
.headline-metrics {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  border-top:1px solid var(--line);
  border-bottom:1px solid var(--line);
}
.headline-metric {
  min-width:0;
  padding:12px 14px;
  border-right:1px solid var(--line);
}
.headline-metric:last-child { border-right:0; }
.headline-metric span {
  display:block;
  margin-bottom:5px;
  color:var(--muted);
  font-size:11px;
  font-weight:820;
}
.headline-metric strong {
  display:block;
  font-size:16px;
  line-height:1.32;
  overflow-wrap:anywhere;
}
.reader { padding:10px 42px 20px; }
.reader-section {
  display:grid;
  grid-template-columns:170px minmax(0, 1fr);
  gap:34px;
  padding:28px 0;
  border-bottom:1px solid var(--line);
  scroll-margin-top:78px;
}
.reader-section:last-child { border-bottom:0; }
.section-label {
  display:grid;
  gap:8px;
  align-content:start;
}
.section-index {
  color:var(--accent);
  font-size:11px;
  letter-spacing:0;
  font-weight:950;
}
.section-label h2 {
  margin:0;
  font-size:20px;
  line-height:1.24;
  font-weight:820;
}
.reader-content { max-width:780px; }
.wide-content { max-width:900px; }
.reader-content p {
  margin:0;
  font-size:17px;
  line-height:1.78;
  font-weight:680;
  color:var(--ink);
}
ul { margin:0; padding-left:19px; line-height:1.84; }
li + li { margin-top:8px; }
.reader-content li { font-size:15px; }
.risk-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:12px;
}
.risk-card {
  display:grid;
  gap:8px;
  min-width:0;
  padding:15px;
  border:1px solid var(--line);
  border-left:4px solid var(--accent);
  background:rgba(255,253,248,.76);
}
.risk-card strong { line-height:1.45; }
.risk-card p { font-size:13px; color:var(--muted); }
.risk-index {
  color:var(--accent);
  font-size:11px;
  font-weight:900;
}
.appendix-panel {
  border-top:1px solid var(--line);
}
details.appendix {
  border-bottom:1px solid var(--line);
  background:rgba(255,253,248,.86);
  scroll-margin-top:78px;
}
details.appendix > summary {
  list-style:none;
  cursor:pointer;
  padding:21px 42px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:18px;
  font-size:18px;
  font-weight:900;
}
details.appendix > summary::-webkit-details-marker { display:none; }
details.appendix > summary::after {
  content:"展开";
  color:var(--muted);
  font-size:11px;
  letter-spacing:0;
}
details.appendix[open] > summary::after { content:"收起"; }
.appendix-body {
  border-top:1px solid var(--line);
  padding:30px 42px 42px;
  background:var(--paper-2);
}
.report-block {
  padding:22px 0;
  border-bottom:1px solid var(--line);
}
.report-block:first-child { padding-top:0; }
.report-block:last-child { border-bottom:0; padding-bottom:0; }
.report-block h3 {
  margin:0 0 10px;
  color:var(--accent-2);
  font-size:18px;
  line-height:1.35;
}
.report-block p, .card p {
  margin:0;
  line-height:1.76;
  color:var(--ink-2);
}
.metric-grid, .card-grid {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:1px;
  background:var(--line);
  border:1px solid var(--line);
  margin:14px 0;
}
.card-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }
.metric, .card {
  background:rgba(255,253,248,.82);
  padding:14px;
  min-width:0;
}
.metric span, .card span {
  display:block;
  color:var(--muted);
  font-size:10px;
  letter-spacing:0;
  font-weight:950;
  margin-bottom:8px;
}
.metric strong {
  display:block;
  font-size:20px;
  line-height:1.25;
  overflow-wrap:anywhere;
}
.card-value { font-weight:850; margin-bottom:7px; }
.table-wrap {
  overflow:auto;
  border-top:2px solid var(--ink);
  margin-top:14px;
  background:rgba(255,253,248,.68);
}
table {
  width:100%;
  border-collapse:collapse;
  font-size:13px;
}
th, td {
  border-bottom:1px solid var(--line);
  padding:11px 10px;
  text-align:left;
  vertical-align:top;
  line-height:1.62;
}
th {
  color:var(--muted);
  font-size:11px;
  letter-spacing:0;
  font-weight:950;
  background:rgba(246,244,239,.92);
}
.rail-section {
  padding:15px;
  border-bottom:1px solid var(--line);
}
.rail-section:last-child { border-bottom:0; }
.rail-label {
  margin:0 0 8px;
  color:var(--muted);
  font-size:10px;
  letter-spacing:0;
  font-weight:950;
}
.rail-lead {
  margin:0;
  font-size:14px;
  line-height:1.66;
  font-weight:780;
}
.rail-metrics { display:grid; gap:9px; }
.rail-metric {
  display:grid;
  gap:3px;
  padding:10px 0;
  border-bottom:1px solid rgba(216,205,188,.7);
}
.rail-metric:last-child { border-bottom:0; }
.rail-metric span { color:var(--muted); font-size:11px; font-weight:820; }
.rail-metric strong { font-size:18px; line-height:1.25; overflow-wrap:anywhere; }
.status-pill {
  display:inline-flex;
  width:max-content;
  align-items:center;
  border:1px solid rgba(22,75,67,.18);
  border-radius:999px;
  background:var(--green-soft);
  color:var(--accent-2);
  padding:6px 10px;
  font-size:12px;
  font-weight:850;
}
@media print {
  body { background:#fff; }
  body::before, .topbar, .side, .rail { display:none; }
  .workspace { display:block; width:100%; margin:0; }
  .doc { border:0; box-shadow:none; border-radius:0; }
  details.appendix:not([open]) .appendix-body { display:block; }
  details.appendix > summary::after { display:none; }
}
@media (max-width:1180px) {
  .workspace { grid-template-columns:180px minmax(0,1fr); }
  .rail { position:relative; top:auto; grid-column:1 / -1; display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); }
  .rail-head { display:none; }
  h1 { font-size:32px; }
}
@media (max-width:860px) {
  .workspace { width:min(100% - 18px, 760px); grid-template-columns:1fr; }
  .side { position:relative; top:auto; }
  .toc { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .doc-head, .reader-section { grid-template-columns:1fr; }
  .doc-head, .metric-band, .reader, details.appendix > summary, .appendix-body { padding-left:22px; padding-right:22px; }
  .headline-metrics, .risk-grid, .metric-grid, .card-grid, .rail { grid-template-columns:1fr; }
  .headline-metric { border-right:0; border-bottom:1px solid var(--line); }
  .headline-metric:last-child { border-bottom:0; }
  .actions { flex-wrap:wrap; justify-content:flex-end; }
  h1 { max-width:none; font-size:28px; word-break:normal; overflow-wrap:anywhere; }
}
"""
