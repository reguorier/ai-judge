#!/usr/bin/env python3
"""Render an AI Judge agent trace audit report from a JSON fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.agent_trace_audit import (
    audit_agent_trace,
    render_agent_trace_html,
    render_agent_trace_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Agent trace JSON fixture")
    parser.add_argument("--json", dest="json_path", help="Output JSON report")
    parser.add_argument("--md", dest="markdown_path", help="Output Markdown report")
    parser.add_argument("--html", dest="html_path", help="Output HTML report")
    parser.add_argument("--audit-id", default=None, help="Stable audit id for reproducible demos")
    parser.add_argument("--generated-at", default=None, help="Stable timestamp for reproducible demos")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = audit_agent_trace(payload, audit_id=args.audit_id, generated_at=args.generated_at)
    if args.json_path:
        _write(args.json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.markdown_path:
        _write(args.markdown_path, render_agent_trace_markdown(report))
    if args.html_path:
        _write(args.html_path, render_agent_trace_html(report))
    if not any([args.json_path, args.markdown_path, args.html_path]):
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _write(path: str, content: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
