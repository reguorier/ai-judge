#!/usr/bin/env python3
"""Self-serve citation audit pipeline for AI Judge.

This module is intentionally narrow: it audits one AI-generated answer against
isolated evidence, produces a citation-level report, and renders a shareable
HTML artifact. It does not collect model answers and it does not rewrite text.
"""

from __future__ import annotations

import html
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.blind_cross_validation import build_blind_cross_validation_packet
from core.evidence_broker import build_evidence_broker_report
from core.evidence_gap_filler import suggest_evidence_gaps
from core.evidence_gap_queue import build_evidence_gap_queue
from core.eval_dataset import build_eval_case_from_verdict
from core.eval_metrics import compute_evidence_quality_metrics
from core.grand_judge import run_grand_judge_mvp
from core.human_review import human_review_status


_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def load_audit_input(path: str | Path) -> dict[str, Any]:
    """Load a citation audit input file.

    Supported formats:
      - JSON with question, answer, and optional external_evidence fields.
      - Markdown sections named "Question", "AI Answer", and "External Evidence".
    """
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = _parse_markdown_audit(text)
    data.setdefault("title", source.stem.replace("-", " ").title())
    data.setdefault("source_path", str(source))
    return data


def run_citation_audit(
    *,
    question: str,
    answer: str,
    title: str = "AI Judge Citation Audit",
    external_evidence: list[dict[str, Any]] | dict[str, Any] | None = None,
    allow_network: bool = False,
    run_id: str | None = None,
    reviewers: list[str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Run the automated citation audit launch pipeline."""
    created_at = generated_at or datetime.now(timezone.utc).isoformat()
    audit_id = run_id or f"audit-{uuid.uuid4().hex[:12]}"
    raw_answers = [{
        "seat": "submitted_answer",
        "seat_name": "Submitted AI Answer",
        "ok": True,
        "response": answer,
    }]
    broker = build_evidence_broker_report(
        question=question,
        raw_answers=raw_answers,
        user_evidence=external_evidence,
        allow_network=allow_network,
        generated_at=created_at,
    )
    grand_report = run_grand_judge_mvp(
        question=question,
        raw_answers=raw_answers,
        external_evidence=broker["items_for_validation"],
        run_id=audit_id,
        generated_at=created_at,
    )
    grand_report["evidence_broker"] = broker
    grand_report["evidence_gap_suggestions"] = suggest_evidence_gaps(grand_report)
    grand_report["evidence_quality_metrics"] = compute_evidence_quality_metrics(grand_report)
    grand_report["evidence_gap_queue"] = build_evidence_gap_queue(grand_report, generated_at=created_at)
    grand_report["blind_cross_validation"] = build_blind_cross_validation_packet(
        question=question,
        grand_report=grand_report,
        reviewers=reviewers or ["gemini", "chatgpt", "deepseek", "qwen"],
        generated_at=created_at,
    )
    verdict = {
        "schema": "citation_audit.v1",
        "product": "AI Judge Citation Audit",
        "version": "3.6.0",
        "audit_id": audit_id,
        "title": title,
        "question": question,
        "answer": answer,
        "allow_network": bool(allow_network),
        "grand_judge": grand_report,
        "human_review_status": human_review_status(grand_report),
        "created_at": created_at,
    }
    grand_report["eval_case"] = build_eval_case_from_verdict({
        "run_id": audit_id,
        "question": question,
        "grand_judge": grand_report,
    })
    verdict["summary"] = build_audit_summary(verdict)
    return verdict


def run_audit_file(
    input_path: str | Path,
    *,
    allow_network: bool = False,
    run_id: str | None = None,
    reviewers: list[str] | None = None,
) -> dict[str, Any]:
    """Load an input file and run a citation audit."""
    data = load_audit_input(input_path)
    return run_citation_audit(
        question=str(data.get("question") or ""),
        answer=str(data.get("answer") or data.get("ai_answer") or ""),
        title=str(data.get("title") or Path(input_path).stem),
        external_evidence=data.get("external_evidence") or data.get("evidence") or [],
        allow_network=allow_network,
        run_id=run_id,
        reviewers=reviewers,
    )


def build_audit_summary(verdict: dict[str, Any]) -> dict[str, Any]:
    """Create a compact launch-facing summary."""
    grand = verdict.get("grand_judge") or {}
    citation = grand.get("citation_verification") or {}
    counts = citation.get("counts") or {}
    metrics = grand.get("evidence_quality_metrics") or {}
    return {
        "overall_status": citation.get("overall_status", "unverifiable"),
        "certification_id": grand.get("certification_id"),
        "certification_hash": grand.get("certification_hash"),
        "replay_ledger_hash": grand.get("replay_ledger_hash"),
        "item_count": citation.get("item_count", 0),
        "counts": counts,
        "trust_gate": metrics.get("trust_gate", "needs_external_evidence"),
        "groundedness_proxy": metrics.get("groundedness_proxy", 0.0),
        "gap_count": (grand.get("evidence_gap_queue") or {}).get("open_count", 0),
        "unverifiable_explanation": citation.get("unverifiable_explanation"),
    }


def render_audit_markdown(verdict: dict[str, Any]) -> str:
    """Render the audit as Markdown for terminal and README demos."""
    summary = verdict.get("summary") or build_audit_summary(verdict)
    grand = verdict.get("grand_judge") or {}
    lines = [
        f"# {verdict.get('title', 'AI Judge Citation Audit')}",
        "",
        f"**Audit ID:** `{verdict.get('audit_id')}`",
        f"**Certification ID:** `{summary.get('certification_id')}`",
        f"**Overall status:** `{summary.get('overall_status')}`",
        f"**Trust gate:** `{summary.get('trust_gate')}`",
        f"**Groundedness proxy:** `{summary.get('groundedness_proxy')}`",
        "",
        "## Status Counts",
        "",
        "| status | count |",
        "|---|---:|",
    ]
    for status, count in (summary.get("counts") or {}).items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend([
        "",
        "## Citation Items",
        "",
        "| id | raw | status | reason |",
        "|---|---|---|---|",
    ])
    for entry in grand.get("replay_ledger") or []:
        report = entry.get("citation_verification") or {}
        for item in report.get("items") or []:
            lines.append(
                "| {id} | {raw} | `{status}` | {reason} |".format(
                    id=_md(item.get("citation_id")),
                    raw=_md(item.get("raw")),
                    status=_md(item.get("status")),
                    reason=_md(item.get("reason")),
                )
            )
    lines.extend([
        "",
        "## Source Isolation",
        "",
        "Raw answer, mentor supplements, and external evidence are kept separate. Candidate sources mentioned by the model do not verify themselves.",
    ])
    return "\n".join(lines) + "\n"


def render_audit_html(verdict: dict[str, Any]) -> str:
    """Render a standalone HTML audit report."""
    summary = verdict.get("summary") or build_audit_summary(verdict)
    grand = verdict.get("grand_judge") or {}
    broker = grand.get("evidence_broker") or {}
    citation_rows = []
    for entry in grand.get("replay_ledger") or []:
        report = entry.get("citation_verification") or {}
        for item in report.get("items") or []:
            citation_rows.append(
                "<tr>"
                f"<td>{_e(item.get('citation_id'))}</td>"
                f"<td>{_e(item.get('raw'))}</td>"
                f"<td><span class=\"pill status-{_slug(item.get('status'))}\">{_e(item.get('status'))}</span></td>"
                f"<td>{_e(item.get('reason'))}</td>"
                f"<td>{_e(item.get('relevance_score'))}</td>"
                "</tr>"
            )
    evidence_rows = []
    for item in broker.get("items") or []:
        evidence_rows.append(
            "<tr>"
            f"<td>{_e(item.get('id') or item.get('evidence_id'))}</td>"
            f"<td>{_e(item.get('source_layer'))}</td>"
            f"<td>{_e(item.get('retrieval_state'))}</td>"
            f"<td>{_e(item.get('title') or item.get('url') or item.get('raw_source'))}</td>"
            "</tr>"
        )
    gap_rows = []
    for task in (grand.get("evidence_gap_queue") or {}).get("tasks") or []:
        gap_rows.append(
            "<tr>"
            f"<td>{_e(task.get('task_id'))}</td>"
            f"<td>{_e(task.get('priority'))}</td>"
            f"<td>{_e(task.get('queue_status'))}</td>"
            f"<td>{_e(task.get('suggested_action'))}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(verdict.get('title'))}</title>
  <style>
    :root {{ color-scheme: light; --ink:#17212b; --muted:#5c6875; --line:#dbe3ea; --bg:#f7f9fb; --panel:#ffffff; --accent:#0f766e; --bad:#b42318; --warn:#a15c07; --good:#067647; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:var(--bg); }}
    header {{ padding:32px clamp(20px,5vw,64px); background:#10212c; color:white; }}
    main {{ max-width:1120px; margin:0 auto; padding:24px; }}
    h1 {{ margin:0 0 8px; font-size:clamp(28px,4vw,48px); line-height:1.05; }}
    h2 {{ margin:28px 0 12px; font-size:22px; }}
    .sub {{ color:#c9d6df; max-width:820px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-top:18px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
    .value {{ font-size:20px; font-weight:700; margin-top:3px; word-break:break-word; }}
    table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
    th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ background:#eef3f6; font-size:12px; color:#45515f; text-transform:uppercase; }}
    tr:last-child td {{ border-bottom:0; }}
    pre {{ white-space:pre-wrap; background:#0f1b24; color:#e9f1f6; border-radius:8px; padding:16px; overflow:auto; }}
    .pill {{ display:inline-flex; align-items:center; min-height:24px; padding:2px 8px; border-radius:999px; font-weight:700; font-size:12px; background:#e8eef3; }}
    .status-verified {{ color:var(--good); background:#dcfae6; }}
    .status-weakly-verified {{ color:var(--warn); background:#fff3d6; }}
    .status-unverifiable {{ color:#344054; background:#edf2f7; }}
    .status-irrelevant,.status-contradicted {{ color:var(--bad); background:#fee4e2; }}
    .note {{ color:var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>{_e(verdict.get('title'))}</h1>
    <div class="sub">AI Judge Citation Audit checks AI-generated claims against isolated external evidence. Model-mentioned candidate sources do not verify themselves.</div>
    <div class="grid">
      <div class="card"><div class="label">Overall</div><div class="value">{_e(summary.get('overall_status'))}</div></div>
      <div class="card"><div class="label">Trust Gate</div><div class="value">{_e(summary.get('trust_gate'))}</div></div>
      <div class="card"><div class="label">Certification</div><div class="value">{_e(summary.get('certification_id'))}</div></div>
      <div class="card"><div class="label">Open Gaps</div><div class="value">{_e(summary.get('gap_count'))}</div></div>
    </div>
  </header>
  <main>
    <h2>Question</h2>
    <div class="card">{_e(verdict.get('question'))}</div>
    <h2>Submitted Answer</h2>
    <pre>{_e(verdict.get('answer'))}</pre>
    <h2>Citation Verification</h2>
    <table><thead><tr><th>ID</th><th>Citation</th><th>Status</th><th>Reason</th><th>Relevance</th></tr></thead><tbody>{''.join(citation_rows) or '<tr><td colspan="5">No citation items.</td></tr>'}</tbody></table>
    <p class="note">{_e(summary.get('unverifiable_explanation'))}</p>
    <h2>Evidence Broker</h2>
    <table><thead><tr><th>ID</th><th>Layer</th><th>Retrieval</th><th>Source</th></tr></thead><tbody>{''.join(evidence_rows) or '<tr><td colspan="4">No evidence items.</td></tr>'}</tbody></table>
    <h2>Evidence Gap Queue</h2>
    <table><thead><tr><th>ID</th><th>Priority</th><th>Status</th><th>Action</th></tr></thead><tbody>{''.join(gap_rows) or '<tr><td colspan="4">No open gaps.</td></tr>'}</tbody></table>
    <h2>Replay Ledger</h2>
    <div class="card">
      <div><strong>Replay Ledger Hash:</strong> {_e(grand.get('replay_ledger_hash'))}</div>
      <div><strong>Certification Hash:</strong> {_e(grand.get('certification_hash'))}</div>
      <div><strong>Audit ID:</strong> {_e(verdict.get('audit_id'))}</div>
    </div>
  </main>
</body>
</html>
"""


def write_audit_outputs(verdict: dict[str, Any], output: str | Path, *, fmt: str = "html") -> Path:
    """Write an audit report to disk."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        output_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    elif fmt == "md":
        output_path.write_text(render_audit_markdown(verdict), encoding="utf-8")
    else:
        output_path.write_text(render_audit_html(verdict), encoding="utf-8")
    return output_path


def _parse_markdown_audit(text: str) -> dict[str, Any]:
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        title = match.group(1).strip().lower()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip()
    question = sections.get("question", "")
    answer = sections.get("ai answer") or sections.get("answer") or sections.get("submitted answer") or ""
    evidence_text = sections.get("external evidence") or sections.get("evidence") or ""
    evidence = _parse_evidence_block(evidence_text)
    title = _first_heading(text) or "AI Judge Citation Audit"
    return {"title": title, "question": question, "answer": answer, "external_evidence": evidence}


def _parse_evidence_block(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if not text:
        return []
    json_match = _JSON_BLOCK_RE.search(text)
    if json_match:
        raw = json.loads(json_match.group(1))
        return raw if isinstance(raw, list) else [raw]
    try:
        raw = json.loads(text)
        return raw if isinstance(raw, list) else [raw]
    except json.JSONDecodeError:
        pass
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), 1):
        line = line.strip().lstrip("-* ").strip()
        if not line:
            continue
        url_match = re.search(r"https?://\S+", line)
        rows.append({
            "id": f"MD-EVID-{index:03d}",
            "url": url_match.group(0).rstrip(").,;") if url_match else "",
            "title": line,
            "snippet": line,
            "text": line,
            "status": "user_supplied",
        })
    return rows


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
