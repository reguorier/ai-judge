"""Batch citation audit runner.

This is the smallest Pro-facing batch layer on top of the single-file
Citation Audit pipeline. It keeps the same source-isolation rules and only
adds input expansion, per-file artifacts, a batch manifest, and an index page.
"""

from __future__ import annotations

import glob
import hashlib
import html
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.citation_audit import run_audit_file, write_audit_outputs


SUPPORTED_SUFFIXES = {".md", ".markdown", ".json"}
DEFAULT_FAIL_ON = {"contradicted"}
DEFAULT_WARN_ON = {"unverifiable", "weakly_verified", "irrelevant", "partially_supported", "unsupported"}


def expand_batch_inputs(inputs: Iterable[str | Path]) -> list[Path]:
    """Expand files, directories, and shell-style glob patterns into audit inputs."""
    seen: set[Path] = set()
    paths: list[Path] = []
    for raw in inputs:
        token = str(raw)
        candidates: list[Path] = []
        source = Path(token)
        if source.exists():
            if source.is_dir():
                candidates.extend(source.rglob("*.md"))
                candidates.extend(source.rglob("*.markdown"))
                candidates.extend(source.rglob("*.json"))
            else:
                candidates.append(source)
        else:
            candidates.extend(Path(item) for item in glob.glob(token, recursive=True))
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    paths.append(resolved)
    return sorted(paths, key=lambda item: str(item))


def run_audit_batch(
    inputs: Iterable[str | Path],
    *,
    out_dir: str | Path,
    manifest_path: str | Path | None = None,
    allow_network: bool = False,
    reviewers: list[str] | None = None,
    fail_on: Iterable[str] | None = None,
    warn_on: Iterable[str] | None = None,
    batch_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Run citation audit across many Markdown/JSON files and write artifacts."""
    created_at = generated_at or datetime.now(timezone.utc).isoformat()
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_fail = _normalize_policy(fail_on, DEFAULT_FAIL_ON)
    selected_warn = _normalize_policy(warn_on, DEFAULT_WARN_ON)
    audit_inputs = expand_batch_inputs(inputs)
    current_batch_id = batch_id or f"batch-{uuid.uuid4().hex[:12]}"
    results: list[dict[str, Any]] = []
    for index, input_path in enumerate(audit_inputs, 1):
        artifact_stem = _artifact_stem(index, input_path)
        audit_id = f"{current_batch_id}-{index:03d}"
        verdict = run_audit_file(
            input_path,
            allow_network=allow_network,
            run_id=audit_id,
            reviewers=reviewers,
        )
        html_path = output_dir / f"{artifact_stem}.html"
        json_path = output_dir / f"{artifact_stem}.json"
        write_audit_outputs(verdict, html_path, fmt="html")
        write_audit_outputs(verdict, json_path, fmt="json")
        summary = verdict.get("summary") or {}
        statuses = _policy_statuses(summary)
        failed = bool(statuses & selected_fail)
        warned = bool(statuses & selected_warn)
        results.append({
            "input": _display_path(input_path),
            "title": verdict.get("title"),
            "audit_id": verdict.get("audit_id"),
            "html": str(html_path),
            "json": str(json_path),
            "overall_status": summary.get("overall_status"),
            "overall_claim_support": summary.get("overall_claim_support"),
            "trust_gate": summary.get("trust_gate"),
            "certification_id": summary.get("certification_id"),
            "certification_hash": summary.get("certification_hash"),
            "replay_ledger_hash": summary.get("replay_ledger_hash"),
            "item_count": summary.get("item_count", 0),
            "gap_count": summary.get("gap_count", 0),
            "policy_statuses": sorted(statuses),
            "failed": failed,
            "warning": warned and not failed,
        })
    failed_count = sum(1 for item in results if item["failed"])
    warning_count = sum(1 for item in results if item["warning"])
    manifest = {
        "schema": "citation_audit_batch.v1",
        "product": "AI Judge Citation Audit",
        "version": "3.7.0",
        "batch_id": current_batch_id,
        "generated_at": created_at,
        "input_count": len(audit_inputs),
        "failed_count": failed_count,
        "warning_count": warning_count,
        "certification_ids": [item["certification_id"] for item in results if item.get("certification_id")],
        "replay_ledger_hashes": [item["replay_ledger_hash"] for item in results if item.get("replay_ledger_hash")],
        "policy": {
            "fail_on": sorted(selected_fail),
            "warn_on": sorted(selected_warn),
            "allow_network": bool(allow_network),
            "reviewers": reviewers or ["gemini", "chatgpt", "deepseek", "qwen"],
        },
        "results": results,
        "index_html": str(output_dir / "index.html"),
        "manifest_path": str(Path(manifest_path) if manifest_path else output_dir / "manifest.json"),
        "exit_code": 1 if failed_count else 0,
    }
    index_path = output_dir / "index.html"
    index_path.write_text(render_batch_index_html(manifest), encoding="utf-8")
    manifest_output = Path(manifest["manifest_path"])
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return manifest


def render_batch_index_html(manifest: dict[str, Any]) -> str:
    """Render a compact batch index page."""
    rows = []
    for item in manifest.get("results") or []:
        state = "failed" if item.get("failed") else "warning" if item.get("warning") else "ok"
        rows.append(
            "<tr>"
            f"<td><a href=\"{_e(Path(str(item.get('html') or '')).name)}\">{_e(item.get('title') or item.get('input'))}</a></td>"
            f"<td><span class=\"pill {state}\">{_e(item.get('overall_status'))}</span></td>"
            f"<td>{_e(item.get('overall_claim_support'))}</td>"
            f"<td>{_e(item.get('trust_gate'))}</td>"
            f"<td>{_e(item.get('certification_id'))}</td>"
            f"<td>{_e(item.get('gap_count'))}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Judge Citation Batch Audit</title>
  <style>
    body {{ margin:0; font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#f7f9fb; color:#17212b; }}
    header {{ background:#10212c; color:white; padding:28px clamp(20px,5vw,64px); }}
    main {{ max-width:1120px; margin:0 auto; padding:24px; }}
    h1 {{ margin:0 0 8px; font-size:34px; }}
    .summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-top:18px; }}
    .card {{ background:white; color:#17212b; border:1px solid #dbe3ea; border-radius:8px; padding:14px; }}
    .label {{ color:#5c6875; font-size:12px; text-transform:uppercase; }}
    .value {{ font-size:22px; font-weight:750; }}
    table {{ width:100%; border-collapse:collapse; background:white; border:1px solid #dbe3ea; border-radius:8px; overflow:hidden; }}
    th,td {{ padding:10px 12px; border-bottom:1px solid #dbe3ea; text-align:left; vertical-align:top; }}
    th {{ background:#eef3f6; font-size:12px; color:#45515f; text-transform:uppercase; }}
    tr:last-child td {{ border-bottom:0; }}
    a {{ color:#0f766e; font-weight:700; }}
    .pill {{ display:inline-flex; padding:2px 8px; border-radius:999px; font-weight:750; font-size:12px; background:#edf2f7; }}
    .pill.ok {{ color:#067647; background:#dcfae6; }}
    .pill.warning {{ color:#a15c07; background:#fff3d6; }}
    .pill.failed {{ color:#b42318; background:#fee4e2; }}
  </style>
</head>
<body>
  <header>
    <h1>AI Judge Citation Batch Audit</h1>
    <div>Batch ID: {_e(manifest.get('batch_id'))}</div>
    <div class="summary">
      <div class="card"><div class="label">Inputs</div><div class="value">{_e(manifest.get('input_count'))}</div></div>
      <div class="card"><div class="label">Failed</div><div class="value">{_e(manifest.get('failed_count'))}</div></div>
      <div class="card"><div class="label">Warnings</div><div class="value">{_e(manifest.get('warning_count'))}</div></div>
      <div class="card"><div class="label">Network</div><div class="value">{_e((manifest.get('policy') or {}).get('allow_network'))}</div></div>
    </div>
  </header>
  <main>
    <table>
      <thead><tr><th>File</th><th>Status</th><th>Claim Support</th><th>Trust Gate</th><th>Certification</th><th>Gaps</th></tr></thead>
      <tbody>{''.join(rows) or '<tr><td colspan="6">No supported input files found.</td></tr>'}</tbody>
    </table>
  </main>
</body>
</html>
"""


def _normalize_policy(values: Iterable[str] | None, default: set[str]) -> set[str]:
    if values is None:
        return set(default)
    normalized: set[str] = set()
    for item in values:
        normalized.update(part.strip() for part in str(item).split(",") if part.strip())
    return normalized


def _policy_statuses(summary: dict[str, Any]) -> set[str]:
    statuses = {
        str(summary.get("overall_status") or ""),
        str(summary.get("overall_claim_support") or ""),
        str(summary.get("trust_gate") or ""),
    }
    statuses.update(str(key) for key, count in (summary.get("counts") or {}).items() if _positive_count(count))
    statuses.update(
        str(key) for key, count in (summary.get("claim_support_counts") or {}).items() if _positive_count(count)
    )
    return {item for item in statuses if item}


def _positive_count(value: Any) -> bool:
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return bool(value)


def _artifact_stem(index: int, path: Path) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", path.stem).strip("-").lower() or "audit"
    digest = hashlib.sha256(_display_path(path).encode("utf-8")).hexdigest()[:8]
    return f"file-{index:03d}-{slug}-{digest}"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)
