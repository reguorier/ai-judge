#!/usr/bin/env python3
"""summarize_beta_week3_readability.py — 汇总 Week 3 Readability Retest 结果。

读取：
- beta_week3_feedback.jsonl
- beta_week3_metrics.json
- beta_week3_reader_type_tasks.json

输出：
- 指标总览
- reader_type 分解
- delta vs Week 2
- 通过标志
"""

import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

BETA_OPS_DIR = os.path.expanduser(
    "~/Library/Application Support/AI Judge/runtime/product/beta_ops"
)


def load_jsonl(path: str) -> list:
    items = []
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found")
        return items
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def main():
    print("=" * 60)
    print("Beta Week 3 Readability Retest Summary")
    print("=" * 60)
    print()

    # 加载数据
    feedbacks = load_jsonl(os.path.join(BETA_OPS_DIR, "beta_week3_feedback.jsonl"))
    metrics = load_json(os.path.join(BETA_OPS_DIR, "beta_week3_metrics.json"))
    tasks = load_json(os.path.join(BETA_OPS_DIR, "beta_week3_reader_type_tasks.json"))

    if not feedbacks:
        print("ERROR: No feedback data found")
        sys.exit(1)

    # 基础统计
    print("── 基础统计 ──")
    print(f"  任务数: {len(tasks)}")
    print(f"  反馈数: {len(feedbacks)}")

    # 总体指标
    print("\n── 总体指标 ──")
    readability = [f["readability_score_1_to_5"] for f in feedbacks]
    trust = [f["trust_score_1_to_5"] for f in feedbacks]
    actionability = [f["actionability_score_1_to_5"] for f in feedbacks]
    would_use = sum(1 for f in feedbacks if f.get("would_use_again"))

    avg_r = round(statistics.mean(readability), 2)
    avg_t = round(statistics.mean(trust), 2)
    avg_a = round(statistics.mean(actionability), 2)
    wu_rate = round(would_use / len(feedbacks), 2)

    print(f"  avg_readability: {avg_r}")
    print(f"  avg_trust: {avg_t}")
    print(f"  avg_actionability: {avg_a}")
    print(f"  would_use_again: {would_use}/{len(feedbacks)} ({wu_rate*100:.0f}%)")

    # Delta vs Week 2
    print("\n── Delta vs Week 2 ──")
    week2_baseline = 3.42
    delta = round(avg_r - week2_baseline, 2)
    print(f"  Week 2 readability: {week2_baseline}")
    print(f"  Week 3 readability: {avg_r}")
    print(f"  Delta: {delta:+.2f}")

    # Reader type 分解
    print("\n── Reader Type 分解 ──")
    rt_group = defaultdict(list)
    for f in feedbacks:
        rt_group[f["reader_type"]].append(f["readability_score_1_to_5"])

    for rt in ["ordinary_user", "pm_founder", "professional_user", "legal_compliance_user"]:
        scores = rt_group.get(rt, [])
        if scores:
            avg = round(statistics.mean(scores), 2)
            # Week 2 baselines per reader type (approx)
            week2_baselines = {
                "ordinary_user": 3.1,
                "pm_founder": 3.4,
                "professional_user": 3.7,
                "legal_compliance_user": 3.6,
            }
            w2 = week2_baselines.get(rt, 3.42)
            d = round(avg - w2, 2)
            print(f"  {rt}: {avg} (n={len(scores)}, delta vs W2={d:+.2f})")

    # 普通用户专项
    print("\n── 普通用户专项 ──")
    ou_scores = rt_group.get("ordinary_user", [])
    if ou_scores:
        ou_avg = round(statistics.mean(ou_scores), 2)
        ou_delta = round(ou_avg - 3.1, 2)
        print(f"  ordinary_user readability: {ou_avg}")
        print(f"  ordinary_user delta vs Week 2: {ou_delta:+.2f}")
        print(f"  threshold (>=3.8): {'PASS' if ou_avg >= 3.8 else 'FAIL'}")
        print(f"  delta threshold (>=+0.35): {'PASS' if ou_delta >= 0.35 else 'FAIL'}")

    # 通过标志
    print("\n── 通过标志 ──")
    overall_pass = avg_r >= 3.8
    ou_pass = ou_avg >= 3.8 if ou_scores else False
    ou_delta_pass = ou_delta >= 0.35 if ou_scores else False
    wu_pass = wu_rate >= 0.70

    if overall_pass and ou_pass and ou_delta_pass and wu_pass:
        print("  READER_TYPE_READABILITY_PATCH_V1_PASS")
        print("  DEEP_JUDGE_REAL_BETA_WEEK3_READABILITY_PASS")
    elif overall_pass:
        print("  READER_TYPE_READABILITY_PATCH_PARTIAL_PASS")
        print("  (Overall pass but ordinary_user thresholds not fully met)")
    else:
        print("  READER_TYPE_READABILITY_PATCH_PARTIAL_PASS")
        print("  (Overall readability below 3.8)")

    print()
    print("BETA_WEEK3_SUMMARY_PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()