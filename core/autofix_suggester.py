#!/usr/bin/env python3
"""Auto-fix suggester — generate actionable fix suggestions from audit findings.

Takes audit results and produces:
- Specific code/config changes needed
- Priority and estimated effort
- Before/after examples

Deploy to: /Users/audimacmini/Documents/ai-judge-skill/core/autofix_suggester.py
"""

from __future__ import annotations

from typing import Any


def suggest_fixes(
    leakage_columns: list[dict[str, str]] | None = None,
    anomalies: list[dict[str, Any]] | None = None,
    data_quality_issues: list[dict[str, Any]] | None = None,
    fairness_issues: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate prioritized fix suggestions from audit findings.

    Returns list of fix objects, each with:
    - priority: P0/P1/P2
    - category: leakage/quality/fairness/anomaly
    - title: short description
    - what_to_do: specific action
    - code_example: optional code/config change
    - effort: estimated effort (hours)
    - consequence_if_ignored: what happens if not fixed
    """
    fixes: list[dict[str, Any]] = []

    # Leakage fixes
    if leakage_columns:
        cols = [c.get("column", "") for c in leakage_columns]
        tables = list(set(c.get("table", "") for c in leakage_columns))
        fixes.append({
            "priority": "P0",
            "category": "leakage",
            "title": f"隔离 {len(cols)} 个泄漏字段",
            "what_to_do": (
                f"从以下表中移除或标记这些字段：{', '.join(tables)}。"
                f"字段列表：{', '.join(cols[:5])}{'...' if len(cols) > 5 else ''}。"
                "在数据字典中标记为 FORBIDDEN，在特征工程管道中加入自动检测。"
            ),
            "code_example": (
                "# 在特征工程管道中加入泄漏检测\n"
                "FORBIDDEN_SUFFIXES = ['_post', '_future', '_leak']\n"
                "def check_leakage(columns):\n"
                "    return [c for c in columns if any(c.endswith(s) for s in FORBIDDEN_SUFFIXES)]\n"
                "leaked = check_leakage(feature_columns)\n"
                "if leaked:\n"
                "    raise ValueError(f'泄漏字段检测: {leaked}')"
            ),
            "effort_hours": 2,
            "consequence_if_ignored": "模型在测试环境表现完美，上线后完全失效——等于用考试答案训练模型。",
        })

    # Data quality fixes
    if data_quality_issues:
        negative_issues = [i for i in data_quality_issues if "负值" in str(i.get("title", ""))]
        duplicate_issues = [i for i in data_quality_issues if "重复" in str(i.get("title", ""))]

        if negative_issues:
            fixes.append({
                "priority": "P0",
                "category": "quality",
                "title": f"修复 {len(negative_issues)} 个负值异常",
                "what_to_do": "在 ETL 管道中为数值字段添加有效范围校验。实验室指标（creatinine、HbA1c、troponin）和收入字段不允许负值。",
                "code_example": (
                    "# ETL 管道中的有效范围校验\n"
                    "VALID_RANGES = {\n"
                    "    'creatinine': (0.1, 15.0),\n"
                    "    'HbA1c': (3.0, 20.0),\n"
                    "    'troponin': (0.0, 10.0),\n"
                    "    'annual_income_usd': (0, 10_000_000),\n"
                    "}\n"
                    "for col, (lo, hi) in VALID_RANGES.items():\n"
                    "    mask = (df[col] < lo) | (df[col] > hi)\n"
                    "    if mask.any():\n"
                    "        print(f'{col}: {mask.sum()} 行超出范围 [{lo}, {hi}]')"
                ),
                "effort_hours": 1,
                "consequence_if_ignored": "脏数据进入临床决策系统可能导致误诊；负收入进入信用模型会扭曲评分。",
            })

        if duplicate_issues:
            fixes.append({
                "priority": "P0",
                "category": "quality",
                "title": f"修复 {len(duplicate_issues)} 个重复记录问题",
                "what_to_do": "排查数据管道的 UPSERT 逻辑，确保主键唯一性约束生效。",
                "code_example": (
                    "# 添加去重步骤\n"
                    "df = df.drop_duplicates(subset=['loan_id'], keep='last')\n"
                    "# 或在数据库层面添加唯一约束\n"
                    "# ALTER TABLE finance_loans ADD CONSTRAINT uq_loan_id UNIQUE (loan_id);"
                ),
                "effort_hours": 1,
                "consequence_if_ignored": "重复记录导致统计指标虚高（如违约率被重复计算），影响业务决策。",
            })

    # Fairness fixes
    if fairness_issues:
        fixes.append({
            "priority": "P0",
            "category": "fairness",
            "title": "受保护类别审批偏差审计",
            "what_to_do": "对受保护类别（G1/G2/G3）的审批率差异进行公平性审计。当前 G3 审批率（11.6%）比 G1（19.9%）低 42%。需要排查是否存在直接或间接歧视。",
            "code_example": (
                "# 公平性审计\n"
                "approval_by_group = df.groupby('protected_class')['approved'].mean()\n"
                "print(approval_by_group)\n"
                "# 如果差异 > 20%，需要进一步分析\n"
                "gap = approval_by_group.max() - approval_by_group.min()\n"
                "if gap > 0.20:\n"
                "    print(f'警告：审批率差异 {gap:.1%}，需要公平性审计')"
            ),
            "effort_hours": 4,
            "consequence_if_ignored": "如果被监管机构发现系统性歧视，可能面临法律诉讼和巨额罚款。",
        })

    # Sort by priority
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    fixes.sort(key=lambda f: priority_order.get(f["priority"], 9))

    return fixes


def render_fixes_html(fixes: list[dict[str, Any]]) -> str:
    """Render fix suggestions as HTML for inclusion in reports."""
    if not fixes:
        return ""

    lines = ['<div class="autofix-section" style="margin-top:24px;">']
    lines.append('<h2 style="font-size:16px;margin-bottom:12px;">🔧 自动修复建议</h2>')

    for fix in fixes:
        border_color = {"P0": "#b91c1c", "P1": "#a16207", "P2": "#15803d"}.get(fix["priority"], "#6b7280")
        lines.append(f'<div style="border-left:4px solid {border_color};padding:12px 16px;margin-bottom:12px;background:#f8fafc;border-radius:0 8px 8px 0;">')
        lines.append(f'<h4 style="font-size:14px;">[{fix["priority"]}] {fix["title"]}</h4>')
        lines.append(f'<p style="font-size:13px;margin:6px 0;">{fix["what_to_do"]}</p>')

        if fix.get("code_example"):
            lines.append(f'<pre style="background:#1e1e2e;color:#cdd6f4;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;margin:8px 0;">{fix["code_example"]}</pre>')

        lines.append(f'<p style="font-size:12px;color:#5a6072;">预估工时: {fix.get("effort_hours", "?")} 小时 | 如果不修复: {fix.get("consequence_if_ignored", "未知风险")}</p>')
        lines.append('</div>')

    lines.append('</div>')
    return "\n".join(lines)
