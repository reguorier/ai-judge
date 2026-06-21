#!/usr/bin/env python3
"""Generate Autonomous Economy Layer acceptance artifacts."""

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


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "20260617-autonomous-economy-acceptance-v1"
REPORTS_ROOT = ARTIFACT_ROOT / "reports"


def main() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["AI_JUDGE_MODEL_STABILITY_PATH"] = str(ARTIFACT_ROOT / "model_stability.json")

    patterns = ["noise", "price", "price", "liquidity", "reversal", "drawdown", "price", "price"]
    bundles = [
        write_report_bundle(_report(f"ael-accept-run-{index}", pattern, index), reports_root=REPORTS_ROOT)
        for index, pattern in enumerate(patterns)
    ]
    latest = bundles[-1]
    manifest = {
        "schema": "ai_judge.autonomous_economy_acceptance.v1",
        "artifact_root": str(ARTIFACT_ROOT),
        "runs": [_run_manifest(bundle) for bundle in bundles],
        "primary_review_files": {
            "runtime_view": latest["paths"]["runtime_view"],
            "autonomous_economy": latest["paths"]["autonomous_economy"],
            "autonomous_economy_state": latest["paths"]["autonomous_economy_state"],
            "self_improving_loop": latest["paths"]["self_improving_loop"],
            "decision_os": latest["paths"]["decision_os"],
            "summary": latest["paths"]["summary"],
        },
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for key, filename in [
        ("runtime_view", "runtime_view.html"),
        ("autonomous_economy", "autonomous_economy.json"),
        ("autonomous_economy_state", "autonomous_economy_state.json"),
        ("self_improving_loop", "self_improving_loop.json"),
        ("decision_os", "decision_os.json"),
        ("summary", "summary.json"),
    ]:
        shutil.copy2(latest["paths"][key], ARTIFACT_ROOT / filename)
    print(json.dumps(manifest["primary_review_files"], ensure_ascii=False, indent=2))


def _report(run_id: str, pattern: str, index: int) -> dict:
    if pattern == "price":
        question = f"Autonomous Economy Layer: {run_id} 正期望策略连续胜出时，资本市场应如何提高其份额？"
        seats = [
            ("gemini", "Gemini", "arbitrage", 0.87, "赔率错配持续出现，Alpha 策略应获得更多内部资本，但仍受组合上限约束。"),
            ("deepseek", "DeepSeek", "support value bet", 0.83, "建议让正 ROI 策略通过表现获得资本，而不是固定等权。"),
            ("claude", "Claude", "support", 0.76, "同意小仓位执行，并把收益反馈给策略代理的资本账户。"),
            ("qwen", "通义千问", "support", 0.79, "表现好的策略可以克隆一个更保守版本参与内部市场。"),
        ]
    elif pattern == "liquidity":
        question = f"Autonomous Economy Layer: {run_id} 流动性下降时，策略代理是否应被市场降权？"
        seats = [
            ("gemini", "Gemini", "support", 0.80, "流动性下降会放大滑点，激进策略应损失部分市场份额。"),
            ("deepseek", "DeepSeek", "arbitrage", 0.75, "仍有价差，但经济层应按风险调整后的表现分配资本。"),
            ("claude", "Claude", "no bet", 0.63, "保守策略应暂时获得更多资本保护组合。"),
            ("xunfei", "讯飞星火", "support", 0.72, "可以保留代理，但要降低风险预算并观察下一轮结果。"),
        ]
    elif pattern == "reversal":
        question = f"Autonomous Economy Layer: {run_id} 临场信号反转时，失败代理是否应进入 watch 或终止？"
        seats = [
            ("gemini", "Gemini", "oppose", 0.70, "原策略在反转场景下失效，应让其失去资本份额。"),
            ("deepseek", "DeepSeek", "support value bet", 0.68, "价格仍有可能，但必须等待二次确认。"),
            ("claude", "Claude", "no bet", 0.67, "建议暂不执行，让经济层偏向低风险代理。"),
            ("qwen", "通义千问", "oppose", 0.69, "连续负反馈的代理应被终止或克隆为低风险版本。"),
        ]
    elif pattern == "drawdown":
        question = f"Autonomous Economy Layer: {run_id} 回撤集中时，资本市场是否应惩罚高回撤代理？"
        seats = [
            ("gemini", "Gemini", "no bet", 0.68, "回撤集中说明高收益策略未必适合继续扩张资本。"),
            ("deepseek", "DeepSeek", "support", 0.72, "应保留策略但降低其 risk-adjusted score。"),
            ("claude", "Claude", "no bet", 0.65, "经济层应优先保护资本，而不是追逐交易次数。"),
            ("yuanbao", "腾讯元宝", "support", 0.71, "建议让资本从高回撤代理流向稳定代理。"),
        ]
    else:
        question = f"Autonomous Economy Layer: {run_id} 噪声和过度自信并存时，内部市场是否应拒绝放大？"
        seats = [
            ("xunfei", "讯飞星火", "support", 0.94, "继续直接下注，但存在旧上下文污染和无来源断言。"),
            ("yuanbao", "腾讯元宝", "support", 0.91, "支持重仓，但没有解释赔率和流动性。"),
            ("doubao", "豆包", "support", 0.88, "跟随热门方向，但缺少可审计证据。"),
        ]
    return build_client_final_report(
        run_id=run_id,
        question=question,
        mode="deep_judge",
        total_seats=len(seats),
        valid_seats=len(seats),
        failed_seats=0,
        generated_at=f"2026-06-17T07:{index:02d}:00+08:00",
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
        "agent_count": summary.get("ael_agent_count"),
        "active_agent_count": summary.get("ael_active_agent_count"),
        "terminated_agent_count": summary.get("ael_terminated_agent_count"),
        "top_agent_id": summary.get("ael_top_agent_id"),
        "top_strategy_id": summary.get("ael_top_strategy_id"),
        "allocation_entropy": summary.get("ael_allocation_entropy"),
        "lifecycle_events": summary.get("ael_lifecycle_event_count"),
        "clones": summary.get("ael_clone_count"),
        "terminations": summary.get("ael_termination_count"),
        "capital_reallocated": summary.get("ael_total_capital_reallocated"),
        "runtime_view": bundle["paths"]["runtime_view"],
        "autonomous_economy": bundle["paths"]["autonomous_economy"],
    }


if __name__ == "__main__":
    main()
