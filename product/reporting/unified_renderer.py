"""Unified report renderer for AI Judge.

Single rendering layer that ALL entry points use.
Accepts any verdict-like dict (from API, Client, MCP, or external callers),
normalizes it to a canonical schema, and produces consistent HTML/MD/JSON output.

This replaces the 7 parallel rendering paths with 1.

Usage:
    from product.reporting.unified_renderer import render_report

    # From any entry point:
    html = render_report(verdict_dict, format="html")
    md   = render_report(verdict_dict, format="md")
    data = render_report(verdict_dict, format="json")
    compact = render_report(verdict_dict, format="compact")
"""

from __future__ import annotations

import html as _html
import json
from datetime import datetime, timezone
from typing import Any


# ─── Canonical Schema ─────────────────────────────────────────────────

CANONICAL_SCHEMA = "ai_judge.unified_report.v1"

CANONICAL_VERDICT_LABELS = {
    "credible": "可信",
    "conditional": "建议推进但需验证",
    "unverified": "证据不足",
    "rejected": "不建议采纳",
}

CANONICAL_MODE_MAP = {
    # Client mode → API mode
    "quick_judge": "flash",
    "deep_judge": "strategic",
    "standard_judge": "standard",
    "ops_check": "flash",
    "prediction_pool": "strategic",
    "simulation_game": "strategic",
    # API mode → itself
    "flash": "flash",
    "strategic": "strategic",
    "standard": "standard",
}


def normalize_verdict(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert any verdict-like dict to the canonical schema.

    Handles input from:
    - verdict.json (API Server / _run_worker)
    - summary.json (Client API / create_client_run)
    - MCP compact output (_summarize_verdict)
    - External callers (OpenSpark, Codex, etc.)
    """
    if not isinstance(raw, dict):
        return {"schema": CANONICAL_SCHEMA, "status": "error", "error": "invalid input"}

    # If already canonical, return as-is
    if raw.get("schema") == CANONICAL_SCHEMA:
        return raw

    # ── Extract core fields with fallbacks ──
    run_id = (
        raw.get("run_id")
        or raw.get("id")
        or "unknown"
    )

    question = (
        raw.get("question")
        or raw.get("title")
        or ""
    )

    # Normalize mode
    raw_mode = (
        raw.get("mode")
        or "flash"
    )
    mode = CANONICAL_MODE_MAP.get(raw_mode, raw_mode)

    # Normalize verdict
    verdict_val = (
        raw.get("verdict")
        or raw.get("verdict_label")
        or "unknown"
    )
    verdict_label = (
        raw.get("verdict_label")
        or CANONICAL_VERDICT_LABELS.get(verdict_val, verdict_val)
    )

    # Confidence: normalize to 0-100 int
    confidence_raw = raw.get("confidence") or 0
    if isinstance(confidence_raw, float) and confidence_raw <= 1.0:
        confidence = int(confidence_raw * 100)
    else:
        confidence = int(confidence_raw)

    # Seats
    seats = raw.get("seats") or []
    if isinstance(seats, list) and seats and isinstance(seats[0], str):
        # Convert string list to dict list
        seats = [{"seat": s, "seat_name": s} for s in seats]

    seat_scores = raw.get("seat_scores") or []

    # Claims
    claims = raw.get("claims") or []

    # Web bridge
    web_bridge = raw.get("web_bridge") or {}

    # Content
    one_liner = raw.get("one_liner") or ""
    reasons = raw.get("reasons") or []
    next_steps = raw.get("next_steps") or []

    # Status
    status = raw.get("status") or "unknown"

    # Final report (from core/final_report.py)
    final_report = raw.get("final_report") or {}

    # Domain closeout
    domain_closeout = raw.get("domain_closeout") or {}

    # Execution trace
    execution_trace = raw.get("execution_trace") or {}

    # Prompt flow
    prompt_flow = raw.get("prompt_flow") or {}

    # Timestamps
    created_at = raw.get("created_at") or ""

    # View URL
    view_url = raw.get("view_url") or ""

    return {
        "schema": CANONICAL_SCHEMA,
        "run_id": run_id,
        "question": question,
        "mode": mode,
        "mode_label": _mode_label(mode),
        "verdict": verdict_val,
        "verdict_label": verdict_label,
        "confidence": confidence,
        "one_liner": one_liner,
        "status": status,
        "seats": seats,
        "seat_count": len(seats) or raw.get("seat_count") or 0,
        "seat_scores": seat_scores,
        "claims": claims,
        "total_claims": len(claims) or raw.get("total_claims") or 0,
        "reasons": reasons,
        "next_steps": next_steps,
        "web_bridge": web_bridge,
        "final_report": final_report,
        "domain_closeout": domain_closeout,
        "execution_trace": execution_trace,
        "prompt_flow": prompt_flow,
        "created_at": created_at,
        "view_url": view_url,
        "insights": raw.get("insights") or [],
        "raw_verdict": raw,  # preserve original for debugging
    }


def _mode_label(mode: str) -> str:
    labels = {
        "flash": "快速裁决",
        "strategic": "深度裁决",
        "standard": "标准议事",
    }
    return labels.get(mode, mode)


# ─── Render Entry Point ───────────────────────────────────────────────

def render_report(
    raw: dict[str, Any],
    format: str = "html",
) -> str | dict[str, Any]:
    """Render a verdict dict into the specified format.

    Args:
        raw: Any verdict-like dict from any entry point.
        format: "html", "md", "json", or "compact"

    Returns:
        HTML string, Markdown string, canonical dict, or compact dict.
    """
    canonical = normalize_verdict(raw)

    if format == "html":
        return _render_html(canonical)
    elif format == "md":
        return _render_markdown(canonical)
    elif format == "json":
        # Return canonical dict without raw_verdict
        out = {k: v for k, v in canonical.items() if k != "raw_verdict"}
        return out
    elif format == "compact":
        return _render_compact(canonical)
    else:
        return _render_html(canonical)


# ─── HTML Renderer ────────────────────────────────────────────────────

def _render_html(v: dict[str, Any]) -> str:
    """Produce a consistent HTML report from canonical verdict."""
    esc = _html.escape

    # Hero section
    hero_html = f"""
<div class="verdict-hero">
  <div class="label">裁决结论</div>
  <div class="verdict">{esc(v['verdict_label'])}</div>
  <div class="confidence">{v['confidence']}%</div>
  <div class="conf-bar"><div class="fill" style="width:{v['confidence']}%"></div></div>
  <div class="oneliner">{esc(v['one_liner'] or '暂无摘要')}</div>
  <div class="meta-row">
    <span class="chip">{v['seat_count']} 席位</span>
    <span class="chip">{esc(v['mode_label'])}</span>
    <span class="chip">{v['total_claims']} claims</span>
  </div>
</div>"""

    # Reasons section
    reasons_html = ""
    if v["reasons"]:
        items = "".join(f"<li>{esc(str(r)[:300])}</li>" for r in v["reasons"][:8])
        reasons_html = f'<div class="card"><h3>关键理由</h3><ul>{items}</ul></div>'

    # Claims section
    claims_html = ""
    if v["claims"]:
        rows = ""
        for c in v["claims"][:20]:
            seat = esc(str(c.get("_seat") or c.get("seat") or ""))
            claim_text = esc(str(c.get("claim") or "")[:200])
            score = c.get("_score") or c.get("score") or 0
            tier = esc(str(c.get("_tier") or ""))
            rows += f"<tr><td>{seat}</td><td>{claim_text}</td><td>{score:.2f}</td><td>{tier}</td></tr>"
        claims_html = f"""
<div class="card"><h3>Claims 评分</h3>
<table><thead><tr><th>席位</th><th>Claim</th><th>分数</th><th>Tier</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""

    # Seat scores section
    seats_html = ""
    if v["seat_scores"]:
        rows = ""
        for s in v["seat_scores"][:16]:
            name = esc(str(s.get("seat_name") or s.get("seat") or ""))
            avg = s.get("average_score") or s.get("avg_score") or 0
            count = s.get("claims_count") or 0
            rows += f"<tr><td>{name}</td><td>{avg:.3f}</td><td>{count}</td></tr>"
        seats_html = f"""
<div class="card"><h3>席位评分</h3>
<table><thead><tr><th>席位</th><th>均分</th><th>Claims</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""

    # Web bridge section
    bridge_html = ""
    wb = v["web_bridge"]
    if wb:
        ok = wb.get("ok_count") or 0
        failed = wb.get("failed_count") or 0
        total = wb.get("requested_count") or ok + failed
        bridge_html = f"""
<div class="card"><h3>收集状态</h3>
<p>成功 {ok}/{total} · 失败 {failed} · {'完成' if wb.get('collection_complete') else '进行中'}</p></div>"""

    # Next steps section
    steps_html = ""
    if v["next_steps"]:
        items = "".join(f"<li>{esc(str(s))}</li>" for s in v["next_steps"][:6])
        steps_html = f'<div class="card"><h3>下一步</h3><ul>{items}</ul></div>'

    # Insights section (from 5D engine)
    insights_html = ""
    if v.get("insights"):
        boxes = ""
        for ins in v["insights"]:
            if isinstance(ins, dict) and ins.get("text"):
                boxes += f'<div class="insight-box">{esc(ins["text"])}</div>'
        if boxes:
            insights_html = f'<div class="card"><h3>深度洞察</h3>{boxes}</div>'

    # Assemble full HTML
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Judge 裁决报告 — {esc(v['run_id'])}</title>
<style>
:root{{color-scheme:light;--bg:#f8f9fb;--card:#fff;--border:#e2e6ea;--text:#1a1d21;--text2:#5a6270;--accent:#2563eb;--green:#16a34a;--amber:#d97706;--red:#dc2626;--radius:12px;--shadow:0 1px 3px rgba(0,0,0,.06)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;background:var(--bg);color:var(--text);line-height:1.7;font-size:14px}}
.wrap{{max-width:960px;margin:0 auto;padding:32px 20px 64px}}
.header{{text-align:center;padding:32px 0 24px}}
.header h1{{font-size:24px;font-weight:700}}
.header .meta{{color:var(--text2);font-size:12px;margin-top:8px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}}
.header .meta span{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:2px 10px;font-size:11px}}
.verdict-hero{{background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);border-radius:var(--radius);padding:28px;color:#fff;text-align:center;margin-bottom:24px}}
.verdict-hero .label{{font-size:11px;opacity:.7;text-transform:uppercase;letter-spacing:1px}}
.verdict-hero .verdict{{font-size:30px;font-weight:800;margin:6px 0}}
.verdict-hero .confidence{{font-size:42px;font-weight:900}}
.conf-bar{{width:180px;height:7px;background:rgba(255,255,255,.2);border-radius:4px;margin:8px auto 0;overflow:hidden}}
.conf-bar .fill{{height:100%;background:#4ade80;border-radius:4px}}
.verdict-hero .oneliner{{font-size:13px;opacity:.8;max-width:600px;margin:12px auto 0;line-height:1.6}}
.verdict-hero .meta-row{{display:flex;gap:8px;justify-content:center;margin-top:10px}}
.chip{{display:inline-block;font-size:10px;padding:2px 8px;border-radius:10px;border:1px solid rgba(255,255,255,.3);color:rgba(255,255,255,.8)}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px;margin-bottom:12px;box-shadow:var(--shadow)}}
.card h3{{font-size:14px;font-weight:700;margin-bottom:10px;color:var(--accent)}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin:8px 0}}
th{{background:#f1f3f5;text-align:left;padding:8px 10px;border-bottom:2px solid var(--border);font-size:11px}}
td{{padding:8px 10px;border-bottom:1px solid var(--border)}}
ul{{padding-left:20px}}li{{margin-bottom:4px;font-size:13px}}
.insight-box{{background:#fafbff;border:1px solid #e0e4f5;border-radius:8px;padding:12px 14px;margin:8px 0;font-size:13px;color:#3b4260;line-height:1.6}}
.insight-box::before{{content:"◆ ";color:var(--accent);font-weight:700}}
.footer{{text-align:center;padding:24px 0;color:var(--text2);font-size:11px;border-top:1px solid var(--border);margin-top:24px}}
.tag{{display:inline-block;font-size:10px;font-weight:600;padding:2px 7px;border-radius:8px}}
.tag-green{{background:#dcfce7;color:#16a34a}}.tag-amber{{background:#fef3c7;color:#d97706}}.tag-red{{background:#fee2e2;color:#dc2626}}
</style>
</head>
<body>
<div class="wrap">
<div class="header">
<h1>AI Judge 裁决报告</h1>
<div class="meta">
<span>Run <code>{esc(v['run_id'])}</code></span>
<span>{esc(v['mode_label'])}</span>
<span>{v['seat_count']} 席位</span>
<span>{esc(v['status'])}</span>
</div>
</div>
{hero_html}
{reasons_html}
{claims_html}
{seats_html}
{bridge_html}
{insights_html}
{steps_html}
<div class="footer">
<p>AI Judge Trust Workbench · Unified Report v1 · {esc(v['created_at'][:19] if v['created_at'] else '')}</p>
</div>
</div>
</body>
</html>"""


# ─── Markdown Renderer ────────────────────────────────────────────────

def _render_markdown(v: dict[str, Any]) -> str:
    """Produce a consistent Markdown report from canonical verdict."""
    lines = [
        f"# AI Judge 裁决报告",
        "",
        f"**Run ID**: `{v['run_id']}`",
        f"**模式**: {v['mode_label']}",
        f"**席位**: {v['seat_count']}",
        f"**状态**: {v['status']}",
        "",
        "---",
        "",
        "## 裁决结论",
        "",
        f"**{v['verdict_label']}** · 置信度 **{v['confidence']}%**",
        "",
        v.get("one_liner") or "暂无摘要",
        "",
    ]

    if v["reasons"]:
        lines.append("## 关键理由")
        lines.append("")
        for r in v["reasons"][:8]:
            lines.append(f"- {r}")
        lines.append("")

    if v["claims"]:
        lines.append("## Claims 评分")
        lines.append("")
        lines.append("| 席位 | Claim | 分数 | Tier |")
        lines.append("|------|-------|------|------|")
        for c in v["claims"][:20]:
            seat = c.get("_seat") or c.get("seat") or ""
            claim = str(c.get("claim") or "")[:80]
            score = c.get("_score") or c.get("score") or 0
            tier = c.get("_tier") or ""
            lines.append(f"| {seat} | {claim} | {score:.2f} | {tier} |")
        lines.append("")

    if v["seat_scores"]:
        lines.append("## 席位评分")
        lines.append("")
        lines.append("| 席位 | 均分 | Claims |")
        lines.append("|------|------|--------|")
        for s in v["seat_scores"][:16]:
            name = s.get("seat_name") or s.get("seat") or ""
            avg = s.get("average_score") or s.get("avg_score") or 0
            count = s.get("claims_count") or 0
            lines.append(f"| {name} | {avg:.3f} | {count} |")
        lines.append("")

    if v.get("insights"):
        lines.append("## 深度洞察")
        lines.append("")
        for ins in v["insights"]:
            if isinstance(ins, dict) and ins.get("text"):
                lines.append(f"◆ {ins['text']}")
                lines.append("")

    if v["next_steps"]:
        lines.append("## 下一步")
        lines.append("")
        for s in v["next_steps"][:6]:
            lines.append(f"- {s}")
        lines.append("")

    return "\n".join(lines)


# ─── Compact JSON Renderer ────────────────────────────────────────────

def _render_compact(v: dict[str, Any]) -> dict[str, Any]:
    """Produce a compact JSON output (for MCP and API responses)."""
    return {
        "ok": True,
        "schema": CANONICAL_SCHEMA,
        "run_id": v["run_id"],
        "question": v["question"][:200] if v["question"] else "",
        "mode": v["mode"],
        "verdict": v["verdict"],
        "verdict_label": v["verdict_label"],
        "confidence": v["confidence"],
        "one_liner": v["one_liner"],
        "status": v["status"],
        "seat_count": v["seat_count"],
        "total_claims": v["total_claims"],
        "reasons": v["reasons"][:5],
        "next_steps": v["next_steps"][:5],
        "web_bridge": {
            "ok_count": v["web_bridge"].get("ok_count"),
            "failed_count": v["web_bridge"].get("failed_count"),
            "collection_complete": v["web_bridge"].get("collection_complete"),
        },
        "insights": [
            {"text": i.get("text"), "type": i.get("type")}
            for i in (v.get("insights") or [])
            if isinstance(i, dict) and i.get("text")
        ],
        "view_url": v["view_url"],
    }
