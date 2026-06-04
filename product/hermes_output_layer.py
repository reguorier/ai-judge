"""
Hermes × Obsidian P0 Integration — Output Layer
Generates hermes-output.json, hermes-output.md, and obsidian-run-note.md
from a completed AI Judge run directory.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def _truncate(text: str, max_len: int = 500) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return str(val)


def write_hermes_outputs(run_dir: Path, vault_dir: Path | None = None) -> dict[str, Any]:
    """
    Generate hermes-output.json, hermes-output.md, and obsidian-run-note.md
    from the verdict.json / trace.json / index.html in run_dir.

    Returns a stats dict:
      {"run_id": ..., "generated": {"hermes_json": bool, "hermes_md": bool, "obsidian_note": bool, "vault_note": bool}}
    """
    result = {
        "run_id": "",
        "generated": {
            "hermes_json": False,
            "hermes_md": False,
            "obsidian_note": False,
            "vault_note": False,
        },
    }

    run_dir = Path(run_dir)
    verdict_path = run_dir / "verdict.json"
    trace_path = run_dir / "trace.json"
    index_html_path = run_dir / "index.html"

    verdict = _load_json(verdict_path)
    if not verdict:
        # Try to infer run_id from directory name
        run_id = run_dir.name
        result["run_id"] = run_id
        print(f"[Hermes] WARNING: no verdict.json in {run_dir}", file=sys.stderr)
        return result

    run_id = verdict.get("run_id", "") or run_dir.name
    result["run_id"] = run_id

    # --- Extract data from verdict ---
    question = _safe_str(verdict.get("question", ""))
    status = _safe_str(verdict.get("status", ""))
    mode = _safe_str(verdict.get("mode", ""))
    confidence = verdict.get("confidence", None)
    created_at = verdict.get("created_at", "")

    # Verdict summary: try summary -> verdict (if str) -> verdict.summary (if dict) -> one_liner
    verdict_raw = verdict.get("verdict", "")
    summary_raw = verdict.get("summary", "")
    one_liner = verdict.get("one_liner", "")
    if isinstance(summary_raw, str) and summary_raw.strip():
        verdict_summary = _truncate(summary_raw)
    elif isinstance(verdict_raw, str) and verdict_raw.strip():
        verdict_summary = _truncate(verdict_raw)
    elif isinstance(verdict_raw, dict) and verdict_raw.get("summary"):
        verdict_summary = _truncate(_safe_str(verdict_raw["summary"]))
    else:
        verdict_summary = _truncate(one_liner)

    # Seats
    seats_raw = verdict.get("seats", [])
    seat_roster = verdict.get("seat_roster", [])
    seat_scores = verdict.get("seat_scores", [])

    # Build seats list
    seats: list[dict[str, Any]] = []
    if isinstance(seat_roster, list) and seat_roster:
        for s in seat_roster:
            if isinstance(s, dict):
                seats.append(s)
    elif isinstance(seats_raw, list) and seats_raw:
        for s in seats_raw:
            if isinstance(s, str):
                seats.append({"name": s, "label": s})
            elif isinstance(s, dict):
                seats.append(s)

    # Claims
    claims = verdict.get("claims", [])
    top_claims: list[dict[str, Any]] = []
    if isinstance(claims, list):
        for c in claims[:10]:
            if isinstance(c, dict):
                top_claims.append({
                    "text": _truncate(c.get("claim", c.get("text", "")), 300),
                    "score": c.get("_score", c.get("score", None)),
                    "seat": c.get("_seat", c.get("seat", c.get("seat_name", ""))),
                })

    # Dissent flags: claims with risk_penalty > threshold or tier=rejected
    dissent_flags: list[dict[str, Any]] = []
    if isinstance(claims, list):
        for c in claims:
            if isinstance(c, dict):
                risk = c.get("risk_penalty", 0)
                tier = c.get("tier", "")
                if (risk and risk > 0.1) or (tier and tier.lower() in ("rejected", "unverified")):
                    dissent_flags.append({
                        "claim_id": c.get("claim_id", ""),
                        "text": _truncate(c.get("claim", c.get("text", "")), 200),
                        "reason": f"risk_penalty={risk}, tier={tier}" if risk else f"tier={tier}",
                        "seat": c.get("_seat", c.get("seat_name", "")),
                    })

    # Evidence gaps
    evidence_gaps_raw = verdict.get("evidence_gaps", [])
    evidence_gaps: list[dict[str, Any]] = []
    if isinstance(evidence_gaps_raw, list) and evidence_gaps_raw:
        for g in evidence_gaps_raw:
            if isinstance(g, dict):
                evidence_gaps.append(g)
    else:
        # Try to extract from claims lacking evidence
        if isinstance(claims, list):
            for c in claims:
                if isinstance(c, dict) and c.get("evidence_count", 1) == 0:
                    evidence_gaps.append({
                        "claim_id": c.get("claim_id", ""),
                        "text": _truncate(c.get("claim", c.get("text", "")), 200),
                        "reason": "no evidence linked",
                    })

    # Consensus map: simple version from seat scores
    consensus_map: dict[str, Any] = {}
    if isinstance(seat_scores, list):
        for s in seat_scores:
            if isinstance(s, dict):
                seat_name = s.get("seat", s.get("seat_name", ""))
                consensus_map[seat_name] = {
                    "average_score": s.get("average_score"),
                    "claims_count": s.get("claims_count"),
                }

    # --- Build hermes-output.json ---
    generated_at = datetime.now(timezone.utc).isoformat()
    source_artifacts = {
        "verdict": verdict_path.exists(),
        "trace": trace_path.exists(),
        "index_html": index_html_path.exists(),
    }

    hermes_output = {
        "schema_version": "ai-judge-hermes-output-v1",
        "run_id": run_id,
        "generated_at": generated_at,
        "source_artifacts": source_artifacts,
        "question": question,
        "status": status,
        "verdict_summary": verdict_summary,
        "confidence": confidence,
        "seats": [
            {"name": s.get("name", s.get("seat", "")), "label": s.get("label", s.get("seat_name", s.get("name", "")))}
            for s in seats
        ] if seats else [],
        "seat_scores": seat_scores,
        "consensus_map": consensus_map,
        "top_claims": top_claims,
        "dissent_flags": dissent_flags,
        "evidence_gaps": evidence_gaps,
        "publish_gate": {
            "verdict_exists": source_artifacts["verdict"],
            "trace_exists": source_artifacts["trace"],
            "report_exists": source_artifacts["index_html"],
            "publishable": source_artifacts["verdict"] and source_artifacts["index_html"],
        },
        "exports": {
            "html": str(index_html_path) if source_artifacts["index_html"] else "",
            "hermes_json": str(run_dir / "hermes-output.json"),
            "hermes_md": str(run_dir / "hermes-output.md"),
            "obsidian_note": str(run_dir / "obsidian-run-note.md"),
        },
        "security": {"metadata_only": True},
    }

    hermes_json_path = run_dir / "hermes-output.json"
    hermes_json_path.write_text(
        json.dumps(hermes_output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    result["generated"]["hermes_json"] = True

    # --- Build hermes-output.md ---
    lines: list[str] = []
    lines.append(f"# AI Judge Hermes Output — Run {run_id}")
    lines.append("")
    lines.append("## Question")
    lines.append("")
    lines.append(question)
    lines.append("")
    lines.append("## Final Verdict")
    lines.append("")
    lines.append(verdict_summary)
    lines.append("")
    lines.append("## Confidence")
    lines.append("")
    lines.append(f"{confidence}%" if confidence is not None else "N/A")
    lines.append("")
    lines.append("## Seat Breakdown")
    lines.append("")
    lines.append("| Seat | Verdict | Score |")
    lines.append("|------|---------|-------|")
    if seat_scores:
        for s in seat_scores:
            name = s.get("seat_name", s.get("seat", ""))
            score = s.get("average_score", "N/A")
            verdict_label = s.get("verdict", "")
            lines.append(f"| {name} | {verdict_label} | {score} |")
    else:
        for s in seats:
            name = s.get("label", s.get("name", s.get("seat", "")))
            lines.append(f"| {name} | — | — |")
    lines.append("")
    lines.append("## Top Claims")
    lines.append("")
    for i, c in enumerate(top_claims, 1):
        lines.append(f"{i}. [{c.get('seat', '')}] {c.get('text', '')} (score: {c.get('score', 'N/A')})")
    lines.append("")
    lines.append("## Dissent Flags")
    lines.append("")
    if dissent_flags:
        for d in dissent_flags:
            lines.append(f"- [{d.get('seat', '')}] {d.get('text', '')} — {d.get('reason', '')}")
    else:
        lines.append("None")
    lines.append("")
    lines.append("## Evidence Gaps")
    lines.append("")
    if evidence_gaps:
        for g in evidence_gaps:
            lines.append(f"- {g.get('text', g.get('reason', ''))}")
    else:
        lines.append("None")
    lines.append("")
    lines.append("## Publish Gate")
    lines.append("")
    pg = hermes_output["publish_gate"]
    lines.append(f"- verdict_exists: {pg['verdict_exists']}")
    lines.append(f"- trace_exists: {pg['trace_exists']}")
    lines.append(f"- report_exists: {pg['report_exists']}")
    lines.append(f"- publishable: {pg['publishable']}")
    lines.append("")
    lines.append("## Exports")
    lines.append("")
    for k, v in hermes_output["exports"].items():
        if v:
            lines.append(f"- {k}: {v}")

    hermes_md_path = run_dir / "hermes-output.md"
    hermes_md_path.write_text("\n".join(lines), encoding="utf-8")
    result["generated"]["hermes_md"] = True

    # --- Build obsidian-run-note.md ---
    seat_names = [
        s.get("label", s.get("seat_name", s.get("name", s.get("seat", ""))))
        for s in seats
    ]
    seat_count = len(seats)

    # Trace summary
    trace = _load_json(trace_path)
    trace_summary_lines: list[str] = []
    if trace and isinstance(trace, list):
        for evt in trace[:10]:
            if isinstance(evt, dict):
                ts = evt.get("timestamp", evt.get("ts", ""))
                evt_type = evt.get("event", evt.get("type", ""))
                msg = evt.get("message", evt.get("msg", ""))
                trace_summary_lines.append(f"- `{ts}` [{evt_type}] {msg}")

    # Seat table
    seat_table_lines: list[str] = []
    seat_table_lines.append("| Seat | Verdict | Score | Confidence |")
    seat_table_lines.append("|------|---------|-------|------------|")
    if seat_scores:
        for s in seat_scores:
            name = s.get("seat_name", s.get("seat", ""))
            score = s.get("average_score", "")
            s_conf = s.get("confidence", "")
            s_verdict = s.get("verdict", "")
            seat_table_lines.append(f"| {name} | {s_verdict} | {score} | {s_conf} |")
    else:
        for s in seats:
            name = s.get("label", s.get("name", s.get("seat", "")))
            seat_table_lines.append(f"| {name} | — | — | — |")

    # Next steps
    next_steps = verdict.get("next_steps", [])
    next_step_lines: list[str] = []
    if isinstance(next_steps, list):
        for ns in next_steps:
            next_step_lines.append(f"- {ns}")

    obsidian_lines: list[str] = []
    obsidian_lines.append("---")
    obsidian_lines.append(f"run_id: {run_id}")
    obsidian_lines.append(f"status: {status}")
    obsidian_lines.append(f"question: \"{question}\"")
    obsidian_lines.append(f"mode: {mode}")
    obsidian_lines.append(f"confidence: {confidence}")
    obsidian_lines.append(f"seats: {json.dumps(seat_names)}")
    obsidian_lines.append(f"seat_count: {seat_count}")
    obsidian_lines.append(f"created_at: {created_at or generated_at}")
    obsidian_lines.append(f"verdict_path: \"{verdict_path}\"")
    obsidian_lines.append(f"hermes_output: \"{hermes_json_path}\"")
    obsidian_lines.append(f"trace_path: \"{trace_path}\"")
    obsidian_lines.append(f"tags: [ai-judge, hermes, {mode}]")
    obsidian_lines.append("---")
    obsidian_lines.append("")
    obsidian_lines.append(f"# AI Judge Run {run_id}")
    obsidian_lines.append("")
    obsidian_lines.append("## 问题")
    obsidian_lines.append("")
    obsidian_lines.append(question)
    obsidian_lines.append("")
    obsidian_lines.append("## 最终判词")
    obsidian_lines.append("")
    obsidian_lines.append(verdict_summary)
    obsidian_lines.append("")
    obsidian_lines.append("## Hermes 摘要")
    obsidian_lines.append("")
    obsidian_lines.append(f"- confidence: {confidence}")
    obsidian_lines.append(f"- seat_count: {seat_count}")
    obsidian_lines.append(f"- top_claims: {len(top_claims)}")
    obsidian_lines.append("")
    obsidian_lines.append("## 席位表现")
    obsidian_lines.append("")
    obsidian_lines.extend(seat_table_lines)
    obsidian_lines.append("")
    obsidian_lines.append("## Claims")
    obsidian_lines.append("")
    for i, c in enumerate(top_claims[:5], 1):
        obsidian_lines.append(f"{i}. [{c.get('seat', '')}] {c.get('text', '')} (score: {c.get('score', 'N/A')})")
    obsidian_lines.append("")
    obsidian_lines.append("## Dissent / 风险")
    obsidian_lines.append("")
    if dissent_flags:
        for d in dissent_flags:
            obsidian_lines.append(f"- [{d.get('seat', '')}] {d.get('text', '')}")
    else:
        obsidian_lines.append("None")
    obsidian_lines.append("")
    obsidian_lines.append("## Publish Gate")
    obsidian_lines.append("")
    for k, v in pg.items():
        obsidian_lines.append(f"- {k}: {v}")
    obsidian_lines.append("")
    obsidian_lines.append("## 执行轨迹摘要")
    obsidian_lines.append("")
    if trace_summary_lines:
        obsidian_lines.extend(trace_summary_lines)
    else:
        obsidian_lines.append("(no trace)")
    obsidian_lines.append("")
    obsidian_lines.append("## 下一步")
    obsidian_lines.append("")
    if next_step_lines:
        obsidian_lines.extend(next_step_lines)
    else:
        obsidian_lines.append("(none)")
    obsidian_lines.append("")
    obsidian_lines.append("## 关联")
    obsidian_lines.append("")
    obsidian_lines.append("[[AI Judge]]")
    obsidian_lines.append("[[Hermes]]")

    obsidian_note_path = run_dir / "obsidian-run-note.md"
    obsidian_note_path.write_text("\n".join(obsidian_lines), encoding="utf-8")
    result["generated"]["obsidian_note"] = True

    # --- Vault note ---
    if vault_dir:
        vault_path = Path(vault_dir)
        vault_path.mkdir(parents=True, exist_ok=True)
        # Determine YYYY/MM
        ts_str = created_at or generated_at
        try:
            if ts_str:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            else:
                dt = datetime.now(timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc)
        ym_dir = vault_path / "Runs" / str(dt.year) / f"{dt.month:02d}"
        ym_dir.mkdir(parents=True, exist_ok=True)
        vault_note_path = ym_dir / f"Run {run_id}.md"
        vault_note_path.write_text("\n".join(obsidian_lines), encoding="utf-8")
        result["generated"]["vault_note"] = True

    return result