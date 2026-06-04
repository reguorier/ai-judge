"""Update latest report pointers."""

from __future__ import annotations

import shutil
from pathlib import Path


def update_latest(reports_root: Path, markdown_path: Path, html_path: Path) -> dict[str, str]:
    reports_root.mkdir(parents=True, exist_ok=True)
    latest_md = reports_root / "latest.md"
    latest_html = reports_root / "latest.html"
    shutil.copyfile(markdown_path, latest_md)
    shutil.copyfile(html_path, latest_html)
    return {"latest_md": str(latest_md), "latest_html": str(latest_html)}
