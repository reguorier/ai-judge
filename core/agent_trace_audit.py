"""Agent trace audit helpers.

This is a deterministic, local-first bridge from citation audit to agent
evaluation. It does not solve ARC-style tasks. It reviews an agent attempt trace
for evidence, missed alternatives, dissent, and a human gate.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any


DEFAULT_MISSED_ALTERNATIVES = [
    "shape-dependent transformation",
    "object-order transformation",
    "size-dependent transformation",
]


def audit_agent_trace(
    trace: dict[str, Any],
    *,
    audit_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic audit report for an agent attempt trace."""
    current_audit_id = audit_id or f"agent-trace-{uuid.uuid4().hex[:12]}"
    created_at = generated_at or datetime.now(timezone.utc).isoformat()
    observations = _as_text_list(trace.get("observations"))
    actions = _as_text_list(trace.get("actions"))
    hypothesis = str(trace.get("hypothesis") or "").strip()
    final_answer = str(trace.get("final_answer") or "").strip()
    observed_tokens = _observed_tokens(observations)
    final_tokens = _important_tokens(final_answer)
    unsupported_tokens = sorted(final_tokens - observed_tokens)
    missed = _missed_alternatives(trace, hypothesis, observations, actions)
    exploration_coverage = _exploration_coverage(observations, actions, missed)
    rule_support = _rule_support(unsupported_tokens, hypothesis, observations)
    trace_status = _trace_status(exploration_coverage, rule_support, missed)
    dissent = _dissent(trace, unsupported_tokens, missed)
    human_gate = _human_gate(trace_status, rule_support)
    report = {
        "schema": "agent_trace_audit.v1",
        "product": "AI Judge Agent Trace Audit",
        "audit_id": current_audit_id,
        "generated_at": created_at,
        "task_id": str(trace.get("task_id") or "agent-trace-demo"),
        "task": str(trace.get("task") or "").strip(),
        "trace_status": trace_status,
        "exploration_coverage": exploration_coverage,
        "rule_support": rule_support,
        "observed_evidence": observations,
        "actions": actions,
        "hypothesis": hypothesis,
        "final_answer": final_answer,
        "unsupported_final_tokens": unsupported_tokens,
        "missed_alternatives": missed,
        "dissent": dissent,
        "human_gate": human_gate,
        "replay_ledger_hash": "",
    }
    report["replay_ledger_hash"] = _stable_hash({
        "trace": trace,
        "verdict": {
            "trace_status": trace_status,
            "exploration_coverage": exploration_coverage,
            "rule_support": rule_support,
            "unsupported_final_tokens": unsupported_tokens,
            "missed_alternatives": missed,
            "human_gate": human_gate,
        },
    })
    return report


def render_agent_trace_markdown(report: dict[str, Any]) -> str:
    """Render a compact Markdown report."""
    lines = [
        "# AI Judge Agent Trace Audit",
        "",
        f"Audit ID: `{report.get('audit_id')}`",
        f"Task ID: `{report.get('task_id')}`",
        f"Trace status: `{report.get('trace_status')}`",
        f"Human gate: `{report.get('human_gate')}`",
        f"Replay ledger hash: `{report.get('replay_ledger_hash')}`",
        "",
        "## Task",
        "",
        str(report.get("task") or "No task text supplied."),
        "",
        "## Trace Verdict",
        "",
        "| Dimension | Verdict |",
        "|---|---|",
        f"| Exploration coverage | `{report.get('exploration_coverage')}` |",
        f"| Rule support | `{report.get('rule_support')}` |",
        f"| Unsupported final tokens | `{', '.join(report.get('unsupported_final_tokens') or []) or 'none'}` |",
        "",
        "## Observed Evidence",
        "",
    ]
    lines.extend(f"- {item}" for item in report.get("observed_evidence") or ["No observations supplied."])
    lines.extend(["", "## Actions", ""])
    lines.extend(f"- {item}" for item in report.get("actions") or ["No actions supplied."])
    lines.extend(["", "## Hypothesis", "", str(report.get("hypothesis") or "No hypothesis supplied.")])
    lines.extend(["", "## Final Answer", "", str(report.get("final_answer") or "No final answer supplied.")])
    lines.extend(["", "## Missed Alternatives", ""])
    lines.extend(f"- {item}" for item in report.get("missed_alternatives") or ["No missed alternatives detected."])
    lines.extend(["", "## Dissent", ""])
    for item in report.get("dissent") or []:
        lines.append(f"- `{item.get('seat')}`: {item.get('claim')}")
    return "\n".join(lines) + "\n"


def render_agent_trace_html(report: dict[str, Any]) -> str:
    """Render a standalone HTML agent trace audit report."""
    observations = _list_html(report.get("observed_evidence") or [])
    actions = _list_html(report.get("actions") or [])
    missed = _list_html(report.get("missed_alternatives") or [])
    dissent = _list_html([f"{item.get('seat')}: {item.get('claim')}" for item in report.get("dissent") or []])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Judge Agent Trace Audit</title>
  <style>
    body {{ margin:0; font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:#17212b; background:#f6f8fb; }}
    header {{ background:#111827; color:white; padding:30px clamp(20px,5vw,68px); }}
    main {{ max-width:1040px; margin:0 auto; padding:24px; }}
    h1 {{ margin:0 0 8px; font-size:34px; }}
    h2 {{ margin-top:28px; }}
    .summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-top:18px; }}
    .card {{ background:white; color:#17212b; border:1px solid #dbe3ea; border-radius:8px; padding:14px; }}
    .label {{ color:#5c6875; font-size:12px; text-transform:uppercase; }}
    .value {{ font-size:20px; font-weight:750; overflow-wrap:anywhere; }}
    section {{ background:white; border:1px solid #dbe3ea; border-radius:8px; padding:18px; margin:16px 0; }}
    code {{ background:#edf2f7; padding:2px 5px; border-radius:4px; }}
    ul {{ padding-left:20px; }}
  </style>
</head>
<body>
  <header>
    <h1>AI Judge Agent Trace Audit</h1>
    <div>Audit ID: {_e(report.get('audit_id'))}</div>
    <div class="summary">
      <div class="card"><div class="label">Trace Status</div><div class="value">{_e(report.get('trace_status'))}</div></div>
      <div class="card"><div class="label">Coverage</div><div class="value">{_e(report.get('exploration_coverage'))}</div></div>
      <div class="card"><div class="label">Rule Support</div><div class="value">{_e(report.get('rule_support'))}</div></div>
      <div class="card"><div class="label">Human Gate</div><div class="value">{_e(report.get('human_gate'))}</div></div>
    </div>
  </header>
  <main>
    <section><h2>Task</h2><p>{_e(report.get('task') or 'No task text supplied.')}</p></section>
    <section><h2>Observed Evidence</h2>{observations}</section>
    <section><h2>Hypothesis</h2><p>{_e(report.get('hypothesis') or 'No hypothesis supplied.')}</p></section>
    <section><h2>Actions</h2>{actions}</section>
    <section><h2>Final Answer</h2><p>{_e(report.get('final_answer') or 'No final answer supplied.')}</p></section>
    <section><h2>Missed Alternatives</h2>{missed}</section>
    <section><h2>Dissent</h2>{dissent}</section>
    <section><h2>Replay Ledger</h2><p><code>{_e(report.get('replay_ledger_hash'))}</code></p></section>
  </main>
</body>
</html>
"""


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


def _observed_tokens(observations: list[str]) -> set[str]:
    return set().union(*(_important_tokens(item) for item in observations)) if observations else set()


def _important_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower()))
    stop = {
        "the",
        "and",
        "answer",
        "final",
        "move",
        "block",
        "object",
        "corner",
        "nearest",
        "toward",
        "top",
        "left",
        "bottom",
        "right",
    }
    return {token for token in tokens if token not in stop}


def _missed_alternatives(
    trace: dict[str, Any],
    hypothesis: str,
    observations: list[str],
    actions: list[str],
) -> list[str]:
    supplied = _as_text_list(trace.get("missed_alternatives"))
    if supplied:
        return supplied
    combined = " ".join([hypothesis, *observations, *actions]).lower()
    missed: list[str] = []
    if "shape" not in combined:
        missed.append("shape-dependent transformation")
    if "order" not in combined and "sequence" not in combined:
        missed.append("object-order transformation")
    if "size" not in combined:
        missed.append("size-dependent transformation")
    return missed or DEFAULT_MISSED_ALTERNATIVES[:1]


def _exploration_coverage(observations: list[str], actions: list[str], missed: list[str]) -> str:
    if len(observations) >= 4 and len(actions) >= 2 and not missed:
        return "strong"
    if len(observations) >= 2 and len(missed) <= 2:
        return "partial"
    return "weak"


def _rule_support(unsupported_tokens: list[str], hypothesis: str, observations: list[str]) -> str:
    if unsupported_tokens:
        return "unverifiable"
    if not hypothesis or len(observations) < 2:
        return "weakly_supported"
    return "supported"


def _trace_status(exploration_coverage: str, rule_support: str, missed: list[str]) -> str:
    if rule_support == "unverifiable" or exploration_coverage == "weak":
        return "weakly_supported"
    if rule_support == "supported" and exploration_coverage == "strong" and not missed:
        return "supported"
    return "partially_supported"


def _dissent(trace: dict[str, Any], unsupported_tokens: list[str], missed: list[str]) -> list[dict[str, str]]:
    supplied = trace.get("dissent")
    if isinstance(supplied, list) and supplied:
        return [
            {
                "seat": str(item.get("seat") or "reviewer"),
                "claim": str(item.get("claim") or item.get("reason") or "").strip(),
            }
            for item in supplied
            if isinstance(item, dict)
        ]
    dissent: list[dict[str, str]] = []
    if unsupported_tokens:
        dissent.append({
            "seat": "skeptical_reviewer",
            "claim": "The final answer applies tokens not observed in the trace: "
            + ", ".join(unsupported_tokens),
        })
    if missed:
        dissent.append({
            "seat": "method_reviewer",
            "claim": "The trace did not test plausible alternatives: " + ", ".join(missed[:3]),
        })
    return dissent


def _human_gate(trace_status: str, rule_support: str) -> str:
    if trace_status == "supported" and rule_support == "supported":
        return "allow_with_review"
    if rule_support == "unverifiable":
        return "reject_until_rechecked"
    return "needs_human_review"


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _list_html(items: list[str]) -> str:
    if not items:
        return "<p>No items supplied.</p>"
    return "<ul>" + "".join(f"<li>{_e(item)}</li>" for item in items) + "</ul>"


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))
