"""Quality gate for publication-grade reports."""

from __future__ import annotations

import json
import re
from typing import Any


LOCAL_PATH_PATTERN = re.compile(r"(/Users/|/home/|C:\\|file:///|/private/var/|/var/folders/)", re.IGNORECASE)


def validate_publication_report(
    model: dict[str, Any],
    *,
    html: str = "",
    markdown: str = "",
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not model.get("title"):
        errors.append("missing_title")
    if not model.get("question"):
        errors.append("missing_question")
    summary = model.get("summary") if isinstance(model.get("summary"), dict) else {}
    if not summary.get("one_line"):
        errors.append("missing_one_line_conclusion")
    if not model.get("base_blocks"):
        errors.append("missing_base_blocks")
    if not model.get("audit_blocks"):
        errors.append("missing_audit_blocks")

    profile = str(model.get("report_profile") or "both")
    if profile in {"both", "industry_only"} and not model.get("industry_blocks"):
        warnings.append("missing_industry_blocks")

    audit_ids = {
        str(block.get("id") or "")
        for block in (model.get("audit_blocks") or [])
        if isinstance(block, dict)
    }
    if "noise_audit" not in audit_ids:
        errors.append("missing_noise_audit_block")

    payload = json.dumps(model, ensure_ascii=False)
    if html:
        payload += "\n" + html
    if markdown:
        payload += "\n" + markdown
    if LOCAL_PATH_PATTERN.search(payload):
        errors.append("local_path_leak")

    status = "blocked" if errors else "passed_with_warnings" if warnings else "passed"
    return {
        "schema": "ai_judge.publication_quality_gate.v1",
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "publishable": not errors,
    }
