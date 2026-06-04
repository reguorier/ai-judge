"""HTML renderer for client-first reports."""

from __future__ import annotations

import html
import re
from typing import Any

from product.reporting.markdown_renderer import render_final_report_markdown


def _inline(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def render_final_report_html(report: dict[str, Any]) -> str:
    markdown = render_final_report_markdown(report)
    body: list[str] = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("### "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_inline(line[2:])}</li>")
        elif line:
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p>{_inline(line)}</p>")
    if in_list:
        body.append("</ul>")
    return """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>AI Judge 最终报告</title>
  <style>
    :root { color-scheme: light; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1f2933; background: #f6f7f9; }
    main { max-width: 880px; margin: 0 auto; padding: 40px 24px 64px; background: #fff; min-height: 100vh; }
    h1 { font-size: 30px; margin: 0 0 18px; }
    h2 { font-size: 20px; margin: 30px 0 10px; padding-top: 16px; border-top: 1px solid #d8dee8; }
    h3 { font-size: 16px; margin: 18px 0 8px; }
    p, li { line-height: 1.65; font-size: 15px; }
    code { background: #eef2f7; padding: 2px 5px; border-radius: 4px; }
  </style>
</head>
<body><main>""" + "\n".join(body) + "\n</main></body></html>\n"
