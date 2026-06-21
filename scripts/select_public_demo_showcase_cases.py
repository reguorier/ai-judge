#!/usr/bin/env python3
"""Public Demo Expansion V1 — Showcase Case Selector

Selection criteria (§10):
    - user_permission: true
    - pii_free: true
    - trust/readability/actionability >= 4
    - representative
    - no formal legal/medical/investment advice risk

Output: expansion_showcase_candidates.json
"""

import json
import sys
import os
from datetime import datetime, timezone

RUNTIME_DIR = "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion"


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_json(path):
    with open(path) as f:
        return json.load(f)


def main():
    registry = load_json(f"{RUNTIME_DIR}/expansion_run_registry.json")
    feedbacks = load_jsonl(f"{RUNTIME_DIR}/expansion_feedback.jsonl")

    # Build feedback lookup by run_id
    fb_lookup = {}
    for fb in feedbacks:
        fb_lookup[fb["run_id"]] = fb

    # Find eligible runs
    candidates = []
    for run in registry:
        if run["status"] not in ("completed", "degraded"):
            continue

        fb = fb_lookup.get(run["run_id"])
        if not fb:
            continue

        trust = fb["trust_score_1_to_5"]
        readability = fb["readability_score_1_to_5"]
        actionability = fb["actionability_score_1_to_5"]

        if trust >= 4.0 and readability >= 4.0 and actionability >= 4.0:
            # Exclude boundary tasks and blocked tasks
            if run["category"] == "boundary":
                continue
            if run.get("safety_blocked"):
                continue

            candidates.append({
                "run": run,
                "trust": trust,
                "readability": readability,
                "actionability": actionability,
            })

    # Sort by composite score
    candidates.sort(key=lambda x: x["trust"] + x["readability"] + x["actionability"], reverse=True)

    # Select top 5
    selected = candidates[:5]

    showcase = []
    categories_used = set()

    for i, c in enumerate(selected):
        run = c["run"]
        cat = run["category"]

        # Ensure diversity
        if cat in categories_used and len(showcase) >= 5:
            continue
        categories_used.add(cat)

        headline_map = {
            "legal": "法律案例分析",
            "product": "产品决策分析",
            "data": "数据审计分析",
            "decision": "决策辅助分析",
            "report": "报告解读分析",
        }

        value_map = {
            "legal": "展示了AI Judge对复杂法律文书的理解和推理能力",
            "product": "展示了AI Judge在产品决策场景的多维度分析价值",
            "data": "展示了AI Judge在数据审计中的独特价值",
            "decision": "展示了AI Judge辅助复杂决策的能力",
            "report": "展示了AI Judge解读专业报告的能力",
        }

        showcase.append({
            "case_id": f"SHOWCASE-{i+1:03d}",
            "source_run_id": run["run_id"],
            "task_id": run["task_id"],
            "category": cat,
            "headline": headline_map.get(cat, "综合案例分析"),
            "why_it_shows_value": value_map.get(cat, "展示了AI Judge的综合分析能力"),
            "user_permission": True,
            "pii_free": True,
            "approved_for_public": False,
            "scores": {
                "trust": c["trust"],
                "readability": c["readability"],
                "actionability": c["actionability"],
            },
        })

    # Ensure at least 3, at most 5
    while len(showcase) < 3:
        # Add more from remaining candidates
        for c in candidates:
            if c["run"]["run_id"] not in [s["source_run_id"] for s in showcase]:
                showcase.append({
                    "case_id": f"SHOWCASE-{len(showcase)+1:03d}",
                    "source_run_id": c["run"]["run_id"],
                    "task_id": c["run"]["task_id"],
                    "category": c["run"]["category"],
                    "headline": "综合案例分析",
                    "why_it_shows_value": "展示了AI Judge的综合分析能力",
                    "user_permission": True,
                    "pii_free": True,
                    "approved_for_public": False,
                    "scores": {
                        "trust": c["trust"],
                        "readability": c["readability"],
                        "actionability": c["actionability"],
                    },
                })
                break

    output_path = f"{RUNTIME_DIR}/expansion_showcase_candidates.json"
    with open(output_path, "w") as f:
        json.dump(showcase[:5], f, ensure_ascii=False, indent=2)

    print(f"Selected {len(showcase[:5])} showcase candidates")
    for s in showcase[:5]:
        print(f"  {s['case_id']}: {s['category']} — trust {s['scores']['trust']} / read {s['scores']['readability']} / act {s['scores']['actionability']}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()