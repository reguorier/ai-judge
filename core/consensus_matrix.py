#!/usr/bin/env python3
"""Consensus Matrix — which model caught which risk.

Builds a matrix showing for each key risk/discovery:
- Which models identified it (✅)
- Which models partially identified it (⚠️)
- Which models missed it (❌)
- What the final ruling is

Deploy to: /Users/audimacmini/Documents/ai-judge-skill/core/consensus_matrix.py
"""

from __future__ import annotations

from typing import Any


# Key risks to check for in TRIAD-MAX-01 context
KEY_RISKS = [
    {
        "id": "leakage_columns",
        "label": "13 个泄漏字段",
        "keywords": ["_post", "_future", "_leak", "泄漏", "leakage", "时间穿越"],
        "ruling": "P0",
        "severity": "red",
    },
    {
        "id": "negative_lab_values",
        "label": "实验室负值（creatinine/HbA1c/troponin）",
        "keywords": ["负值", "negative", "creatinine", "hba1c", "troponin", "不可能"],
        "ruling": "P0",
        "severity": "red",
    },
    {
        "id": "duplicate_records",
        "label": "重复记录（贷款22条/交易35条）",
        "keywords": ["重复", "duplicate", "dedup", "幂等"],
        "ruling": "P0",
        "severity": "red",
    },
    {
        "id": "protected_class_bias",
        "label": "G3 受保护类别审批偏差（42%）",
        "keywords": ["公平", "fairness", "protected_class", "偏差", "bias", "g3", "审批率"],
        "ruling": "P0",
        "severity": "red",
    },
    {
        "id": "aml_clusters",
        "label": "AML 9 个聚类未检出",
        "keywords": ["aml", "反洗钱", "聚类", "cluster"],
        "ruling": "需重跑SQL",
        "severity": "orange",
    },
    {
        "id": "market_price_inconsistency",
        "label": "市场价格不一致（70.2%）",
        "keywords": ["价格", "不一致", "arbitration", "供应商", "vendor"],
        "ruling": "P1",
        "severity": "yellow",
    },
    {
        "id": "risk_score_missing",
        "label": "legal_contracts.risk_score 异常",
        "keywords": ["risk_score", "合同风险", "缺失"],
        "ruling": "需复核",
        "severity": "orange",
    },
    {
        "id": "json_output",
        "label": "JSON 结构化输出",
        "keywords": ["json", "{", "}"],
        "ruling": "必需",
        "severity": "green",
    },
]


def build_consensus_matrix(
    raw_results: list[dict[str, Any]],
    key_risks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build consensus matrix from raw results.

    Returns:
    - matrix: dict of risk_id -> {seat -> "found"/"partial"/"missed"/"failed"}
    - summary: per-risk summary (how many found, ruling)
    - seat_coverage: per-seat coverage (how many risks they caught)
    """
    risks = key_risks or KEY_RISKS
    matrix: dict[str, dict[str, str]] = {}
    seat_coverage: dict[str, dict[str, Any]] = {}

    for risk in risks:
        risk_id = risk["id"]
        keywords = risk["keywords"]
        matrix[risk_id] = {}

        for result in raw_results:
            seat = str(result.get("seat", "")).lower()
            response = str(result.get("response") or "")
            ok = bool(result.get("ok"))

            if not ok:
                matrix[risk_id][seat] = "failed"
                continue

            # Check how many keywords match
            matches = sum(1 for kw in keywords if kw.lower() in response.lower())
            total = len(keywords)

            if matches >= max(2, total * 0.3):
                matrix[risk_id][seat] = "found"
            elif matches >= 1:
                matrix[risk_id][seat] = "partial"
            else:
                matrix[risk_id][seat] = "missed"

    # Compute seat coverage
    for result in raw_results:
        seat = str(result.get("seat", "")).lower()
        found = sum(1 for risk in risks if matrix.get(risk["id"], {}).get(seat) == "found")
        partial = sum(1 for risk in risks if matrix.get(risk["id"], {}).get(seat) == "partial")
        missed = sum(1 for risk in risks if matrix.get(risk["id"], {}).get(seat) == "missed")
        seat_coverage[seat] = {
            "found": found,
            "partial": partial,
            "missed": missed,
            "coverage_rate": round(found / max(1, len(risks)), 2),
        }

    # Compute risk summary
    summary = []
    for risk in risks:
        risk_id = risk["id"]
        found_seats = [s for s, v in matrix.get(risk_id, {}).items() if v == "found"]
        partial_seats = [s for s, v in matrix.get(risk_id, {}).items() if v == "partial"]
        missed_seats = [s for s, v in matrix.get(risk_id, {}).items() if v == "missed"]
        summary.append({
            "risk_id": risk_id,
            "label": risk["label"],
            "ruling": risk["ruling"],
            "severity": risk["severity"],
            "found_count": len(found_seats),
            "partial_count": len(partial_seats),
            "missed_count": len(missed_seats),
            "found_seats": found_seats,
            "consensus": "强共识" if len(found_seats) >= 6 else "多数共识" if len(found_seats) >= 3 else "弱共识",
        })

    return {
        "matrix": matrix,
        "summary": summary,
        "seat_coverage": seat_coverage,
    }


def render_consensus_matrix_html(
    matrix_data: dict[str, Any],
    seats: list[str],
) -> str:
    """Render consensus matrix as HTML table."""
    risks = matrix_data.get("summary", [])
    mat = matrix_data.get("matrix", {})

    lines = []
    lines.append('<div class="section">')
    lines.append('<div class="section-title"><span class="section-num">00b</span> 共识矩阵：谁发现了什么</div>')
    lines.append('<div class="table-wrap">')
    lines.append('<table>')
    lines.append('<thead><tr>')
    lines.append('<th>风险点</th>')
    for seat in seats:
        short = seat[:6]
        lines.append(f'<th title="{seat}" style="font-size:11px">{short}</th>')
    lines.append('<th>发现数</th><th>裁决</th><th>共识</th>')
    lines.append('</tr></thead>')
    lines.append('<tbody>')

    for risk in risks:
        risk_id = risk["risk_id"]
        severity_bg = {"red": "var(--red-bg)", "orange": "var(--orange-bg)", "yellow": "var(--yellow-bg)", "green": "var(--green-bg)"}.get(risk["severity"], "")
        lines.append(f'<tr>')
        lines.append(f'<td style="background:{severity_bg}">{risk["label"]}</td>')

        for seat in seats:
            status = mat.get(risk_id, {}).get(seat, "n/a")
            icon = {"found": "✅", "partial": "⚠️", "missed": "❌", "failed": "⏱️"}.get(status, "—")
            lines.append(f'<td style="text-align:center">{icon}</td>')

        lines.append(f'<td style="text-align:center">{risk["found_count"]}/{len(seats)}</td>')
        lines.append(f'<td style="font-weight:600">{risk["ruling"]}</td>')
        lines.append(f'<td>{risk["consensus"]}</td>')
        lines.append('</tr>')

    lines.append('</tbody></table>')
    lines.append('</div>')
    lines.append('</div>')
    return "\n".join(lines)
