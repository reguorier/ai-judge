#!/usr/bin/env python3
"""
collect_beta_week1_feedback.py

Beta Week 1 反馈收集脚本。
支持 --input 参数指定 feedback JSONL 文件路径，解析并校验每条反馈条目。

用法:
    python scripts/collect_beta_week1_feedback.py --input runtime/product/beta_ops/beta_week1_feedback.jsonl

校验规则:
    1. 每条 entry 必须包含 feedback_id / task_id / run_id / reader_type / user_type
    2. trust_score_1_to_5 在 1-5 范围内（非 failed 的任务）
    3. is_external_user 必须为 boolean
    4. created_at 必须为 ISO-8601 格式
    5. 同 feedback_id 不可重复

退出码:
    0: 所有校验通过
    1: 校验失败
"""

import json
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any


REQUIRED_FIELDS = [
    "feedback_id", "task_id", "run_id", "reader_type", "user_type",
    "is_external_user", "can_state_final_answer", "can_state_next_step",
    "can_explain_why", "confusing_part", "missing_information",
    "would_use_again", "free_text", "created_at"
]

SCORE_FIELDS = ["trust_score_1_to_5", "readability_score_1_to_5", "actionability_score_1_to_5"]


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError as e:
                print(f"[ERROR] 第 {line_num} 行 JSON 解析失败: {e}")
                sys.exit(1)
    return entries


def validate_feedback(entries: List[Dict[str, Any]]) -> bool:
    errors = []
    seen_ids = set()

    for i, entry in enumerate(entries, 1):
        prefix = f"[条目 {i}] {entry.get('feedback_id', 'UNKNOWN')}"

        # 1. 必填字段检查
        for field in REQUIRED_FIELDS:
            if field not in entry:
                errors.append(f"{prefix}: 缺少必填字段 '{field}'")
            elif entry[field] is None:
                errors.append(f"{prefix}: 字段 '{field}' 值为 null")

        # 2. 用户类型检查
        if "user_type" in entry:
            if entry["user_type"] not in ("internal_proxy", "external"):
                errors.append(f"{prefix}: user_type 必须为 'internal_proxy' 或 'external'，实际为 '{entry['user_type']}'")

        # 3. is_external_user 类型检查
        if "is_external_user" in entry:
            if not isinstance(entry["is_external_user"], bool):
                errors.append(f"{prefix}: is_external_user 必须为 boolean 类型")

        # 4. 评分字段检查（仅在非 failed 时检查）
        task_id = entry.get("task_id", "")
        has_scores = all(f in entry and entry[f] is not None for f in SCORE_FIELDS)
        no_scores = all(f in entry and entry[f] is None for f in SCORE_FIELDS)

        if has_scores:
            for field in SCORE_FIELDS:
                val = entry[field]
                if not isinstance(val, (int, float)) or val < 1 or val > 5:
                    errors.append(f"{prefix}: {field} 必须在 1-5 范围内，实际为 {val}")
        elif not no_scores and not has_scores:
            # 有些为 None 有些不是 — 不一致
            errors.append(f"{prefix}: 评分字段部分为 null、部分有值，请统一（全部 null 表示 failed，否则全部 1-5）")

        # 5. 布尔字段检查
        bool_fields = ["can_state_final_answer", "can_state_next_step", "can_explain_why", "would_use_again"]
        for bf in bool_fields:
            if bf in entry and entry[bf] is not None and not isinstance(entry[bf], bool):
                errors.append(f"{prefix}: {bf} 必须为 boolean 类型")

        # 6. created_at ISO-8601 格式检查
        if "created_at" in entry and entry["created_at"]:
            try:
                datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                errors.append(f"{prefix}: created_at 格式不正确，需为 ISO-8601")

        # 7. feedback_id 重复检查
        fid = entry.get("feedback_id", "")
        if fid:
            if fid in seen_ids:
                errors.append(f"{prefix}: feedback_id '{fid}' 重复")
            seen_ids.add(fid)

    if errors:
        print(f"\n[FAIL] 共发现 {len(errors)} 个校验错误:\n")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print(f"\n[PASS] 全部 {len(entries)} 条反馈校验通过")
        return True


def print_summary(entries: List[Dict[str, Any]]):
    scored = [e for e in entries if all(e.get(f) is not None for f in SCORE_FIELDS)]
    n = len(scored)
    print("\n反馈摘要:")
    print(f"  总条目数      : {len(entries)}")
    print(f"  有效评分条目  : {n}")
    if n > 0:
        avg_trust = sum(e["trust_score_1_to_5"] for e in scored) / n
        avg_read = sum(e["readability_score_1_to_5"] for e in scored) / n
        avg_act = sum(e["actionability_score_1_to_5"] for e in scored) / n
        would_use = sum(1 for e in scored if e["would_use_again"]) / n * 100
        print(f"  平均信任度     : {avg_trust:.2f}")
        print(f"  平均可读性     : {avg_read:.2f}")
        print(f"  平均可操作性   : {avg_act:.2f}")
        print(f"  愿意再次使用   : {would_use:.0f}%")
    print()


def main():
    parser = argparse.ArgumentParser(description="Beta Week 1 反馈收集与校验")
    parser.add_argument("--input", required=True, help="反馈 JSONL 文件路径")
    args = parser.parse_args()

    print(f"读取反馈文件: {args.input}")
    entries = load_jsonl(args.input)

    if not entries:
        print("[ERROR] 反馈文件为空")
        sys.exit(1)

    print_summary(entries)
    ok = validate_feedback(entries)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()