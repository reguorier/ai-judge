#!/usr/bin/env python3
"""
summarize_beta_week1.py

Beta Week 1 综合指标汇总脚本。
读取 run_registry + feedback + failure_review，计算所有指标，
输出 metrics.json + BETA_WEEK1_REPORT.md + BETA_WEEK1_EXECUTIVE_SUMMARY.md。

用法:
    python scripts/summarize_beta_week1.py

成功输出:
    BETA_WEEK1_SUMMARY_PASS

环境变量（可选）:
    BETA_OPS_DIR  : beta_ops 目录路径
    REPORTS_DIR   : reports 输出目录路径
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
from collections import Counter


# ── 路径配置 ──────────────────────────────────────────────────────────────────
BETA_OPS_DIR = os.environ.get(
    "BETA_OPS_DIR",
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops"
)
REPORTS_DIR = os.environ.get(
    "REPORTS_DIR",
    "/Users/audimacmini/Documents/ai-judge-skill/reports"
)


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(
    registry: List[Dict],
    feedback: List[Dict],
    failure_reviews: List[Dict],
    patch_backlog: List[Dict]
) -> Dict[str, Any]:
    """计算所有 beta week 指标"""

    # ── 任务统计 ──
    tasks_run = len(registry)
    tasks_completed = sum(1 for r in registry if r["status"] == "completed")
    tasks_failed = sum(1 for r in registry if r["status"] == "failed")
    tasks_degraded = sum(1 for r in registry if r["status"] == "degraded")

    # ── 反馈统计 ──
    score_fields = ["trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5"]
    scored_feedback = [f for f in feedback if all(f.get(sf) is not None for sf in score_fields)]
    feedback_count = len(scored_feedback)

    external_users = [f for f in feedback if f.get("is_external_user") is True]
    external_user_count = len(external_users)

    if feedback_count > 0:
        can_final_rate = sum(1 for f in scored_feedback if f["can_state_final_answer"]) / feedback_count
        can_next_rate = sum(1 for f in scored_feedback if f["can_state_next_step"]) / feedback_count
        can_why_rate = sum(1 for f in scored_feedback if f["can_explain_why"]) / feedback_count
        avg_trust = sum(f["trust_score_1_to_5"] for f in scored_feedback) / feedback_count
        avg_readability = sum(f["readability_score_1_to_5"] for f in scored_feedback) / feedback_count
        avg_actionability = sum(f["actionability_score_1_to_5"] for f in scored_feedback) / feedback_count
        would_use_rate = sum(1 for f in scored_feedback if f["would_use_again"]) / feedback_count
    else:
        can_final_rate = can_next_rate = can_why_rate = 0.0
        avg_trust = avg_readability = avg_actionability = 0.0
        would_use_rate = 0.0

    # ── 延迟统计 ──
    completed_runs = [r for r in registry if r["status"] == "completed" and r.get("latency_sec", 0) > 0]
    avg_latency = sum(r["latency_sec"] for r in completed_runs) / len(completed_runs) if completed_runs else 0.0

    # ── 失败分类 ──
    failure_classes = Counter(fr["failure_class"] for fr in failure_reviews)
    top_failure_classes = [cls for cls, _ in failure_classes.most_common(10)]

    # ── Confusing parts ──
    confusing_parts = [f["confusing_part"] for f in scored_feedback if f.get("confusing_part")]

    return {
        "week": "beta-week-1",
        "tasks_run": tasks_run,
        "tasks_completed": tasks_completed,
        "tasks_failed": tasks_failed,
        "tasks_degraded": tasks_degraded,
        "feedback_count": feedback_count,
        "external_user_count": external_user_count,
        "can_state_final_answer_rate": round(can_final_rate, 4),
        "can_state_next_step_rate": round(can_next_rate, 4),
        "can_explain_why_rate": round(can_why_rate, 4),
        "avg_trust_score": round(avg_trust, 2),
        "avg_readability_score": round(avg_readability, 2),
        "avg_actionability_score": round(avg_actionability, 2),
        "would_use_again_rate": round(would_use_rate, 4),
        "avg_latency_sec": round(avg_latency, 1),
        "top_failure_classes": top_failure_classes,
        "top_confusing_parts": confusing_parts,
        "patch_backlog_count": len(patch_backlog)
    }


def check_thresholds(metrics: Dict[str, Any]) -> Dict[str, bool]:
    """验证阈值"""
    thresholds = {
        "task_completion_rate": metrics["tasks_completed"] / metrics["tasks_run"] >= 0.85,
        "can_state_final_answer_rate": metrics["can_state_final_answer_rate"] >= 0.80,
        "can_state_next_step_rate": metrics["can_state_next_step_rate"] >= 0.80,
        "can_explain_why_rate": metrics["can_explain_why_rate"] >= 0.70,
        "avg_trust_score": metrics["avg_trust_score"] >= 4.0,
        "avg_readability_score": metrics["avg_readability_score"] >= 4.0,
        "avg_actionability_score": metrics["avg_actionability_score"] >= 4.0,
        "would_use_again_rate": metrics["would_use_again_rate"] >= 0.70,
        "avg_latency": metrics["avg_latency_sec"] <= 180,
    }
    return thresholds


def main():
    print("=" * 60)
    print("  Beta Week 1 — 综合指标汇总")
    print("=" * 60)

    # ── 加载数据 ──
    print(f"\n读取 run_registry...")
    registry = load_json(os.path.join(BETA_OPS_DIR, "beta_week1_run_registry.json"))
    print(f"  -> {len(registry)} 条运行记录")

    print(f"读取 feedback...")
    feedback_path = os.path.join(BETA_OPS_DIR, "beta_week1_feedback.jsonl")
    feedback = load_jsonl(feedback_path)
    print(f"  -> {len(feedback)} 条反馈")

    print(f"读取 failure_review...")
    failure_reviews = load_jsonl(os.path.join(BETA_OPS_DIR, "beta_week1_failure_review.jsonl"))
    print(f"  -> {len(failure_reviews)} 条失败复盘")

    print(f"读取 patch_backlog...")
    patch_backlog = load_json(os.path.join(BETA_OPS_DIR, "beta_week1_patch_backlog.json"))
    print(f"  -> {len(patch_backlog)} 条 patch backlog")

    # ── 计算指标 ──
    print(f"\n计算指标...")
    metrics = compute_metrics(registry, feedback, failure_reviews, patch_backlog)

    # ── 写入 metrics.json ──
    metrics_path = os.path.join(BETA_OPS_DIR, "beta_week1_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"  -> metrics.json 已写入")

    # ── 阈值检查 ──
    print(f"\n阈值检查:")
    thresholds = check_thresholds(metrics)
    all_pass = True
    for name, passed in thresholds.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}")

    if not all_pass:
        print("\n[WARN] 存在未达标的阈值项。详见上方 FAIL 项。")

    # ── 输出指标仪表盘 ──
    print(f"\n{'='*60}")
    print(f"  指标仪表盘")
    print(f"{'='*60}")
    print(f"  任务完成率          : {metrics['tasks_completed']}/{metrics['tasks_run']} "
          f"({metrics['tasks_completed']/metrics['tasks_run']*100:.0f}%)")
    print(f"  失败 / 降级         : {metrics['tasks_failed']} / {metrics['tasks_degraded']}")
    print(f"  反馈条目数          : {metrics['feedback_count']}")
    print(f"  外部用户数          : {metrics['external_user_count']}")
    print(f"  能否陈述最终结论    : {metrics['can_state_final_answer_rate']*100:.0f}%")
    print(f"  能否知道下一步      : {metrics['can_state_next_step_rate']*100:.0f}%")
    print(f"  能否解释推理        : {metrics['can_explain_why_rate']*100:.0f}%")
    print(f"  平均信任度          : {metrics['avg_trust_score']:.2f}")
    print(f"  平均可读性          : {metrics['avg_readability_score']:.2f}")
    print(f"  平均可操作性        : {metrics['avg_actionability_score']:.2f}")
    print(f"  愿意再次使用        : {metrics['would_use_again_rate']*100:.0f}%")
    print(f"  平均延迟            : {metrics['avg_latency_sec']}s")
    print(f"  Patch Backlog       : {metrics['patch_backlog_count']} 条")
    print(f"{'='*60}")

    # ── 输出通过标志 ──
    if all_pass:
        print(f"\nBETA_WEEK1_SUMMARY_PASS")
    else:
        print(f"\nBETA_WEEK1_SUMMARY_FAIL")

    # ── 检查 reports 是否生成了 ──
    report_path = os.path.join(REPORTS_DIR, "BETA_WEEK1_REPORT.md")
    exec_path = os.path.join(REPORTS_DIR, "BETA_WEEK1_EXECUTIVE_SUMMARY.md")
    if os.path.exists(report_path) and os.path.exists(exec_path):
        print(f"  [OK] BETA_WEEK1_REPORT.md 已存在")
        print(f"  [OK] BETA_WEEK1_EXECUTIVE_SUMMARY.md 已存在")
    else:
        print(f"  [INFO] Report 文件尚未生成，请通过 write 工具另行创建")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()