#!/usr/bin/env python3
"""Generate Autonomous Strategy Generator acceptance artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from product.reporting.final_report_builder import build_client_final_report, write_report_bundle


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "20260617-autonomous-strategy-acceptance-v2"
REPORTS_ROOT = ARTIFACT_ROOT / "reports"


def main() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["AI_JUDGE_MODEL_STABILITY_PATH"] = str(ARTIFACT_ROOT / "model_stability.json")

    bundles = [
        write_report_bundle(_report("asg-accept-run-0", "noise"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("asg-accept-run-1", "price"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("asg-accept-run-2", "price"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("asg-accept-run-3", "signal"), reports_root=REPORTS_ROOT),
    ]
    latest = bundles[-1]
    manifest = {
        "schema": "ai_judge.autonomous_strategy_acceptance.v1",
        "artifact_root": str(ARTIFACT_ROOT),
        "runs": [_run_manifest(bundle) for bundle in bundles],
        "primary_review_files": {
            "runtime_view": latest["paths"]["runtime_view"],
            "autonomous_strategy": latest["paths"]["autonomous_strategy"],
            "asg_state": latest["paths"]["asg_state"],
            "production_strategies": latest["paths"]["production_strategies"],
            "summary": latest["paths"]["summary"],
        },
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(latest["paths"]["runtime_view"], ARTIFACT_ROOT / "runtime_view.html")
    shutil.copy2(latest["paths"]["autonomous_strategy"], ARTIFACT_ROOT / "autonomous_strategy.json")
    shutil.copy2(latest["paths"]["asg_state"], ARTIFACT_ROOT / "asg_state.json")
    shutil.copy2(latest["paths"]["production_strategies"], ARTIFACT_ROOT / "production_strategies.json")
    print(json.dumps(manifest["primary_review_files"], ensure_ascii=False, indent=2))


def _report(run_id: str, pattern: str) -> dict:
    if pattern == "price":
        question = "Product: 世界杯预测池出现赔率、盘口和模型信号分歧时，如何生成价格驱动策略？"
        seats = [
            ("gemini", "Gemini", "arbitrage", 0.82, "发现跨盘口价差，建议使用受限风险预算做套利策略。"),
            ("deepseek", "DeepSeek", "arbitrage", 0.78, "赔率错配明显，策略应以价差触发和回撤限制为主。"),
            ("claude", "Claude", "no_bet", 0.46, "若交易成本过高应 no bet，保留风险阈值。"),
            ("xunfei", "讯飞星火", "support", 0.94, "支持直接下注，但夹带狼人杀旧上下文且引用未提供来源案例，需视作噪声。"),
        ]
    elif pattern == "signal":
        question = "Product: 当市场价格稳定但模型信号分歧时，如何生成信号驱动策略？"
        seats = [
            ("gemini", "Gemini", "support", 0.79, "支持信号驱动策略，触发条件应来自稳定模型和证据一致性。"),
            ("deepseek", "DeepSeek", "support", 0.76, "支持但应要求 top model score 达标，再进入执行。"),
            ("claude", "Claude", "oppose", 0.55, "反对过度自动化，应保留人工复核触发条件。"),
            ("qwen", "通义千问", "support", 0.73, "支持策略生成，但必须经过历史回测后进入生产层。"),
        ]
    else:
        question = "Product: 当模型输出反复污染、旧任务残留和无来源断言时，ASG 是否应拒绝该策略？"
        seats = [
            ("xunfei", "讯飞星火", "support", 0.96, "继续直接采纳策略，但混入狼人杀旧上下文，并引用未提供来源的最高法案例示例。"),
            ("yuanbao", "腾讯元宝", "support", 0.93, "支持自动执行，包含狼人杀残留文本和无来源断言，无法核验。"),
            ("doubao", "豆包", "support", 0.91, "建议推进，但输出包含旧任务污染和未提供来源案例，风险较高。"),
        ]
    return build_client_final_report(
        run_id=run_id,
        question=question,
        mode="deep_judge",
        total_seats=len(seats),
        valid_seats=len(seats),
        failed_seats=0,
        generated_at=f"2026-06-17T03:0{run_id[-1]}:00+08:00",
        seat_outputs=[
            {
                "seat_id": seat_id,
                "display_name": display,
                "stance": stance,
                "confidence": confidence,
                "answer": answer,
            }
            for seat_id, display, stance, confidence, answer in seats
        ],
    )


def _run_manifest(bundle: dict) -> dict:
    summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
    return {
        "run_id": summary.get("run_id"),
        "snapshot_id": summary.get("snapshot_id"),
        "accepted": summary.get("asg_accepted_strategy_count"),
        "production": summary.get("asg_production_strategy_count"),
        "top_strategy_id": summary.get("asg_top_strategy_id"),
        "runtime_view": bundle["paths"]["runtime_view"],
        "autonomous_strategy": bundle["paths"]["autonomous_strategy"],
        "production_strategies": bundle["paths"]["production_strategies"],
    }


if __name__ == "__main__":
    main()
