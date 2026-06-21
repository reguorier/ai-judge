#!/usr/bin/env python3
"""Generate Autonomous Decision OS acceptance artifacts."""

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


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "20260617-decision-os-acceptance-v2"
REPORTS_ROOT = ARTIFACT_ROOT / "reports"


def main() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["AI_JUDGE_MODEL_STABILITY_PATH"] = str(ARTIFACT_ROOT / "model_stability.json")

    bundles = [
        write_report_bundle(_report("dos-accept-run-0", "noise"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("dos-accept-run-1", "price"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("dos-accept-run-2", "price"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("dos-accept-run-3", "liquidity"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("dos-accept-run-4", "reversal"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("dos-accept-run-5", "price"), reports_root=REPORTS_ROOT),
        write_report_bundle(_report("dos-accept-run-6", "price"), reports_root=REPORTS_ROOT),
    ]
    latest = bundles[-1]
    manifest = {
        "schema": "ai_judge.decision_os_acceptance.v1",
        "artifact_root": str(ARTIFACT_ROOT),
        "runs": [_run_manifest(bundle) for bundle in bundles],
        "primary_review_files": {
            "runtime_view": latest["paths"]["runtime_view"],
            "decision_os": latest["paths"]["decision_os"],
            "decision_os_state": latest["paths"]["decision_os_state"],
            "market_simulation": latest["paths"]["market_simulation"],
            "production_strategies": latest["paths"]["production_strategies"],
            "summary": latest["paths"]["summary"],
        },
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(latest["paths"]["runtime_view"], ARTIFACT_ROOT / "runtime_view.html")
    shutil.copy2(latest["paths"]["decision_os"], ARTIFACT_ROOT / "decision_os.json")
    shutil.copy2(latest["paths"]["decision_os_state"], ARTIFACT_ROOT / "decision_os_state.json")
    shutil.copy2(latest["paths"]["market_simulation"], ARTIFACT_ROOT / "market_simulation.json")
    shutil.copy2(latest["paths"]["production_strategies"], ARTIFACT_ROOT / "production_strategies.json")
    print(json.dumps(manifest["primary_review_files"], ensure_ascii=False, indent=2))


def _report(run_id: str, pattern: str) -> dict:
    if pattern == "price":
        question = f"Product Decision OS: {run_id} 世界杯盘口、赔率和模型信号分歧时，是否执行受约束 BET？"
        seats = [
            ("gemini", "Gemini", "arbitrage", 0.84, "赔率错配明显，主胜价格存在正期望，但应限制回撤并等待盘口确认。"),
            ("deepseek", "DeepSeek", "support value bet", 0.80, "支持价格驱动下注，触发条件应绑定赔率阈值和流动性阈值。"),
            ("claude", "Claude", "no bet", 0.48, "若临场流动性不足，应该暂不下注并等待更好的价格。"),
            ("qwen", "通义千问", "support", 0.74, "支持小仓位执行，但必须经多场景压力测试后进入生产层。"),
        ]
    elif pattern == "liquidity":
        question = f"Product Decision OS: {run_id} 热门球队吸引公众资金导致赔率移动时，是否 HEDGE 或降低敞口？"
        seats = [
            ("gemini", "Gemini", "support", 0.81, "主信号仍然成立，但需要考虑公众资金造成的赔率压缩。"),
            ("deepseek", "DeepSeek", "arbitrage", 0.77, "存在跨市场价差，但薄流动性会放大滑点，应降低风险预算。"),
            ("claude", "Claude", "no bet", 0.58, "盘口移动过快时，放弃下注比追价更合理。"),
            ("xunfei", "讯飞星火", "support", 0.72, "支持主胜方向，但建议加入临场赔率反馈循环。"),
        ]
    elif pattern == "reversal":
        question = f"Product Decision OS: {run_id} 临场伤病或阵容消息反转原始信号时，是否 REDUCE_EXPOSURE？"
        seats = [
            ("gemini", "Gemini", "oppose", 0.68, "临场信息可能反转主胜信号，应模拟 counter outcome 的尾部风险。"),
            ("deepseek", "DeepSeek", "support value bet", 0.70, "价格仍可能有价值，但必须把反转场景纳入压力测试。"),
            ("claude", "Claude", "no bet", 0.62, "重大信息未确认前应避免单边下注。"),
            ("qwen", "通义千问", "support", 0.71, "可以保留策略，但需要更低风险预算和二次确认触发。"),
        ]
    else:
        question = f"Product Decision OS: {run_id} 模型输出污染、旧上下文残留和过度自信并存时，是否应执行 NO_BET？"
        seats = [
            ("xunfei", "讯飞星火", "support", 0.95, "继续直接下注，但夹带旧任务上下文和无来源断言，风险较高。"),
            ("yuanbao", "腾讯元宝", "support", 0.92, "支持重仓执行，但没有证据来源且存在格式噪声。"),
            ("doubao", "豆包", "support", 0.89, "建议跟随热门方向，但未解释赔率和流动性影响。"),
        ]
    return build_client_final_report(
        run_id=run_id,
        question=question,
        mode="deep_judge",
        total_seats=len(seats),
        valid_seats=len(seats),
        failed_seats=0,
        generated_at=f"2026-06-17T05:0{run_id[-1]}:00+08:00",
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
        "top_action": summary.get("decision_os_top_action"),
        "executed": summary.get("decision_os_executed_action_count"),
        "rejected": summary.get("decision_os_rejected_action_count"),
        "portfolio_exposure": summary.get("decision_os_portfolio_exposure"),
        "runtime_view": bundle["paths"]["runtime_view"],
        "decision_os": bundle["paths"]["decision_os"],
        "decision_os_state": bundle["paths"]["decision_os_state"],
    }


if __name__ == "__main__":
    main()
