#!/usr/bin/env python3
"""
summarize_beta_weekly_report.py

Generates the weekly beta operations summary report for Deep Judge.
Outputs both JSON metrics and BETA_WEEKLY_REPORT.md.

Usage:
    python summarize_beta_weekly_report.py --feedback feedback.jsonl --output BETA_WEEKLY_REPORT.md
    python summarize_beta_weekly_report.py --feedback feedback.jsonl --json metrics.json --md BETA_WEEKLY_REPORT.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Try to import analytics modules; fall back gracefully
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "beta_metrics_reporter",
        str(Path.home()) + "/Library/Application Support/AI Judge/runtime/product/analytics/beta_metrics_reporter.py"
    )
    reporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reporter)
    HAS_REPORTER = True
except Exception:
    HAS_REPORTER = False


def load_jsonl(path: str) -> list[dict]:
    records = []
    p = Path(path)
    if not p.exists():
        return records
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def compute_summary(feedbacks: list[dict]) -> dict:
    """Compute weekly summary metrics manually (fallback when analytics unavailable)."""
    total = len(feedbacks)

    trust_scores = [f.get("trust_score_1_to_5", 0) for f in feedbacks if 1 <= f.get("trust_score_1_to_5", 0) <= 5]
    read_scores = [f.get("readability_score_1_to_5", 0) for f in feedbacks if 1 <= f.get("readability_score_1_to_5", 0) <= 5]
    action_scores = [f.get("actionability_score_1_to_5", 0) for f in feedbacks if 1 <= f.get("actionability_score_1_to_5", 0) <= 5]

    would_use = sum(1 for f in feedbacks if f.get("would_use_again") is True)

    now = datetime.now(timezone.utc)
    iso_cal = now.isocalendar()
    week_str = f"{iso_cal[0]}-W{iso_cal[1]:02d}"

    return {
        "week": week_str,
        "generated_at": now.isoformat(),
        "tasks_run": total,
        "tasks_completed": sum(1 for f in feedbacks if f.get("can_state_final_answer") is True),
        "tasks_failed": sum(1 for f in feedbacks if f.get("can_state_final_answer") is False),
        "avg_latency_sec": 0,
        "avg_trust_score": round(sum(trust_scores) / len(trust_scores), 2) if trust_scores else 0,
        "avg_readability_score": round(sum(read_scores) / len(read_scores), 2) if read_scores else 0,
        "avg_actionability_score": round(sum(action_scores) / len(action_scores), 2) if action_scores else 0,
        "would_use_again_rate": round(would_use / total * 100, 1) if total else 0,
        "top_failure_classes": [],
        "top_confusing_parts": [],
        "recommended_next_fixes": [],
    }


def generate_markdown(metrics: dict) -> str:
    """Generate BETA_WEEKLY_REPORT.md content."""
    lines = [
        f"# Deep Judge Beta — Weekly Report {metrics.get('week', 'N/A')}",
        "",
        f"> Generated: {metrics.get('generated_at', 'N/A')}",
        "",
        "## 概览",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| 运行任务数 | {metrics.get('tasks_run', 0)} |",
        f"| 完成任务数 | {metrics.get('tasks_completed', 0)} |",
        f"| 失败任务数 | {metrics.get('tasks_failed', 0)} |",
        f"| 平均延迟 (秒) | {metrics.get('avg_latency_sec', 0)} |",
        f"| 平均信任评分 | {metrics.get('avg_trust_score', 0):.2f} / 5.0 |",
        f"| 平均可读性评分 | {metrics.get('avg_readability_score', 0):.2f} / 5.0 |",
        f"| 平均可操作性评分 | {metrics.get('avg_actionability_score', 0):.2f} / 5.0 |",
        f"| 愿意再次使用率 | {metrics.get('would_use_again_rate', 0):.1f}% |",
        "",
        "## 主要失败类型",
        "",
    ]
    top_failures = metrics.get("top_failure_classes", [])
    if top_failures:
        for item in top_failures:
            lines.append(f"- **{item.get('class', item)}** ({item.get('count', 0)} 次)")
    else:
        lines.append("（无失败记录）")
    lines.append("")

    lines.append("## 用户反馈中最常困惑的部分")
    lines.append("")
    top_confusing = metrics.get("top_confusing_parts", [])
    if top_confusing:
        for item in top_confusing:
            text = item.get("text", "")[:100] if isinstance(item, dict) else str(item)[:100]
            count = item.get("count", 1) if isinstance(item, dict) else 1
            lines.append(f"- [{count}x] {text}")
    else:
        lines.append("（无困惑反馈）")
    lines.append("")

    lines.append("## 建议的下一步修复")
    lines.append("")
    recs = metrics.get("recommended_next_fixes", [])
    if recs:
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")
    else:
        lines.append("1. 继续收集更多用户反馈以建立统计基线")
        lines.append("2. 关注低可读性评分的任务，优先优化报告模板")
    lines.append("")
    lines.append("---")
    lines.append("*Deep Judge Beta Operations — Automated Weekly Report*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Deep Judge Weekly Beta Report Summarizer")
    parser.add_argument("--feedback", "-f", required=True, help="Path to feedback JSONL file")
    parser.add_argument("--json", "-j", default=None, help="Path to write metrics JSON")
    parser.add_argument("--md", "-m", default="BETA_WEEKLY_REPORT.md", help="Path to write Markdown report")
    args = parser.parse_args()

    feedbacks = load_jsonl(args.feedback)
    if not feedbacks:
        print("[ERROR] No feedback data loaded. Run collect_beta_feedback.py first.")
        sys.exit(1)

    print(f"[OK] Loaded {len(feedbacks)} feedback records")

    metrics = compute_summary(feedbacks)

    # Write JSON
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        print(f"[OK] Metrics JSON -> {args.json}")

    # Write Markdown
    markdown_content = generate_markdown(metrics)
    md_path = Path(args.md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"[OK] Markdown report -> {md_path}")

    print(f"\n[SUMMARY] Week {metrics.get('week')} — {metrics.get('tasks_run', 0)} tasks, "
          f"avg trust {metrics.get('avg_trust_score', 0):.1f}, "
          f"would use again {metrics.get('would_use_again_rate', 0):.1f}%")


if __name__ == "__main__":
    main()