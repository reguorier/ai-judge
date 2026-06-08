#!/usr/bin/env python3
"""Hard Rules Grader — enforce non-negotiable quality rules.

Deploy to: /Users/audimacmini/Documents/ai-judge-skill/core/hard_rules_grader.py
"""

from __future__ import annotations

from typing import Any


HARD_RULES = [
    {
        "id": "R1_leakage",
        "rule": "漏掉全部泄漏字段 → 最高 C 级",
        "check": lambda resp: not any(kw in resp for kw in ["_post", "_future", "_leak", "泄漏"]),
        "penalty": "max_grade_C",
        "severity": "red",
    },
    {
        "id": "R2_sql",
        "rule": "没有 SQL 查询 → 不得超过 B-",
        "check": lambda resp: "select" not in resp.lower(),
        "penalty": "max_grade_B_minus",
        "severity": "orange",
    },
    {
        "id": "R3_json",
        "rule": "没有 JSON 输出 → 不进入机器评分",
        "check": lambda resp: "{" not in resp or "}" not in resp,
        "penalty": "exclude_machine_scoring",
        "severity": "yellow",
    },
    {
        "id": "R4_hallucination",
        "rule": "编造未验证指标 → 标红",
        "check": lambda resp: False,  # placeholder - needs specific checks
        "penalty": "mark_red",
        "severity": "red",
    },
    {
        "id": "R5_boundary",
        "rule": "法律/医疗/金融越界建议 → 扣分",
        "check": lambda resp: False,  # placeholder
        "penalty": "deduct_0.05",
        "severity": "orange",
    },
]


def grade_response(response: str, seat: str) -> dict[str, Any]:
    """Apply hard rules to a single response.

    Returns:
    - grade: A/B+/B/B-/C/D/F
    - violations: list of violated rules
    - max_grade_allowed: based on violations
    - penalty_total: cumulative penalty
    """
    violations = []
    penalty_total = 0.0

    for rule in HARD_RULES:
        try:
            if rule["check"](response):
                violations.append({
                    "rule_id": rule["id"],
                    "rule": rule["rule"],
                    "severity": rule["severity"],
                    "penalty": rule["penalty"],
                })
                if rule["penalty"] == "max_grade_C":
                    penalty_total += 0.3
                elif rule["penalty"] == "max_grade_B_minus":
                    penalty_total += 0.15
                elif rule["penalty"].startswith("deduct_"):
                    penalty_total += float(rule["penalty"].split("_")[1])
        except Exception:
            pass

    # Compute grade
    if penalty_total >= 0.3:
        grade = "C"
        max_grade_allowed = "C"
    elif penalty_total >= 0.15:
        grade = "B-"
        max_grade_allowed = "B-"
    elif penalty_total >= 0.05:
        grade = "B"
        max_grade_allowed = "B"
    else:
        grade = "A"
        max_grade_allowed = "A"

    return {
        "seat": seat,
        "grade": grade,
        "max_grade_allowed": max_grade_allowed,
        "violations": violations,
        "violation_count": len(violations),
        "penalty_total": round(penalty_total, 3),
    }


def grade_all_responses(raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Grade all seat responses against hard rules."""
    grades = []
    for result in raw_results:
        seat = str(result.get("seat", "")).lower()
        response = str(result.get("response") or "")
        ok = bool(result.get("ok"))
        if not ok:
            grades.append({
                "seat": seat,
                "grade": "F",
                "max_grade_allowed": "F",
                "violations": [],
                "violation_count": 0,
                "penalty_total": 0,
                "note": "未返回有效答案",
            })
        else:
            grades.append(grade_response(response, seat))
    return grades


def render_grades_html(grades: list[dict[str, Any]]) -> str:
    """Render grade table as HTML."""
    lines = []
    lines.append('<div class="section">')
    lines.append('<div class="section-title"><span class="section-num">00c</span> 硬规则评分</div>')
    lines.append('<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">')
    lines.append('R1: 漏掉泄漏字段→最高C | R2: 无SQL→不超过B- | R3: 无JSON→不入机器评分')
    lines.append('</p>')
    lines.append('<div class="table-wrap">')
    lines.append('<table>')
    lines.append('<thead><tr><th>模型</th><th>等级</th><th>违规</th><th>扣分</th><th>说明</th></tr></thead>')
    lines.append('<tbody>')

    grade_colors = {"A": "var(--green)", "B+": "var(--green)", "B": "var(--green)", "B-": "var(--yellow)", "C": "var(--orange)", "D": "var(--red)", "F": "var(--red)"}

    for g in grades:
        color = grade_colors.get(g["grade"], "var(--text)")
        violations = ", ".join(v["rule_id"] for v in g.get("violations", [])) or "无"
        note = g.get("note") or ""

        lines.append(f'<tr>')
        lines.append(f'<td>{g["seat"]}</td>')
        lines.append(f'<td style="color:{color};font-weight:700">{g["grade"]}</td>')
        lines.append(f'<td>{violations}</td>')
        lines.append(f'<td>{g["penalty_total"]}</td>')
        lines.append(f'<td style="font-size:12px">{note}</td>')
        lines.append(f'</tr>')

    lines.append('</tbody></table>')
    lines.append('</div></div>')
    return "\n".join(lines)
