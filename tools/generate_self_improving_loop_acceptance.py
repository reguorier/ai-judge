#!/usr/bin/env python3
"""Generate Self-Improving Execution Loop acceptance artifacts."""

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


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "20260617-self-improving-loop-acceptance-v1"
REPORTS_ROOT = ARTIFACT_ROOT / "reports"


def main() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["AI_JUDGE_MODEL_STABILITY_PATH"] = str(ARTIFACT_ROOT / "model_stability.json")

    patterns = ["noise", "price", "price", "liquidity", "reversal", "price", "drawdown", "price"]
    bundles = [
        write_report_bundle(_report(f"siel-accept-run-{index}", pattern, index), reports_root=REPORTS_ROOT)
        for index, pattern in enumerate(patterns)
    ]
    latest = bundles[-1]
    manifest = {
        "schema": "ai_judge.self_improving_loop_acceptance.v1",
        "artifact_root": str(ARTIFACT_ROOT),
        "runs": [_run_manifest(bundle) for bundle in bundles],
        "primary_review_files": {
            "runtime_view": latest["paths"]["runtime_view"],
            "self_improving_loop": latest["paths"]["self_improving_loop"],
            "self_improving_loop_state": latest["paths"]["self_improving_loop_state"],
            "decision_policy_config": latest["paths"]["decision_policy_config"],
            "decision_os": latest["paths"]["decision_os"],
            "market_simulation": latest["paths"]["market_simulation"],
            "summary": latest["paths"]["summary"],
        },
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(latest["paths"]["runtime_view"], ARTIFACT_ROOT / "runtime_view.html")
    shutil.copy2(latest["paths"]["self_improving_loop"], ARTIFACT_ROOT / "self_improving_loop.json")
    shutil.copy2(latest["paths"]["self_improving_loop_state"], ARTIFACT_ROOT / "self_improving_loop_state.json")
    shutil.copy2(latest["paths"]["decision_policy_config"], ARTIFACT_ROOT / "decision_policy_config.json")
    shutil.copy2(latest["paths"]["decision_os"], ARTIFACT_ROOT / "decision_os.json")
    shutil.copy2(latest["paths"]["market_simulation"], ARTIFACT_ROOT / "market_simulation.json")
    shutil.copy2(latest["paths"]["summary"], ARTIFACT_ROOT / "summary.json")
    print(json.dumps(manifest["primary_review_files"], ensure_ascii=False, indent=2))


def _report(run_id: str, pattern: str, index: int) -> dict:
    if pattern == "price":
        question = f"Self-Improving Loop: {run_id} 正期望赔率信号持续出现时，系统是否应强化 BET 策略？"
        seats = [
            ("gemini", "Gemini", "arbitrage", 0.86, "赔率错配持续存在，主信号与价格都支持小仓位执行，后续应强化正 ROI 触发。"),
            ("deepseek", "DeepSeek", "support value bet", 0.82, "支持受约束下注，但必须把执行结果反馈到下一轮阈值。"),
            ("claude", "Claude", "support", 0.74, "可以执行，但应保留单场和组合上限，避免过拟合单场结果。"),
            ("qwen", "通义千问", "support", 0.78, "同意低敞口执行，若实现收益高于预期，可适度降低入场门槛。"),
        ]
    elif pattern == "liquidity":
        question = f"Self-Improving Loop: {run_id} 流动性冲击扩大滑点时，系统是否应提高风控阈值？"
        seats = [
            ("gemini", "Gemini", "support", 0.80, "信号仍然成立，但流动性下降会放大尾部风险，应提高置信门槛。"),
            ("deepseek", "DeepSeek", "arbitrage", 0.76, "存在价差但执行摩擦变大，应让 learning loop 抬高风险折扣。"),
            ("claude", "Claude", "no bet", 0.61, "盘口快速变化时不宜追价，策略应更保守。"),
            ("xunfei", "讯飞星火", "support", 0.73, "支持小仓位，但要记录执行偏差并调整下一轮权重。"),
        ]
    elif pattern == "reversal":
        question = f"Self-Improving Loop: {run_id} 临场反转导致原策略偏离，系统是否应抑制失败模式？"
        seats = [
            ("gemini", "Gemini", "oppose", 0.70, "阵容消息反转后原信号可信度下降，应该降低激进下注触发。"),
            ("deepseek", "DeepSeek", "support value bet", 0.68, "仍有价格价值，但需要二次确认，失败模式应被记录。"),
            ("claude", "Claude", "no bet", 0.66, "建议等待信息确认，当前执行可能带来负向 value error。"),
            ("qwen", "通义千问", "oppose", 0.69, "应减少敞口，并把反转场景写入策略改写日志。"),
        ]
    elif pattern == "drawdown":
        question = f"Self-Improving Loop: {run_id} 历史回测出现回撤集中，系统是否应收紧组合配置？"
        seats = [
            ("gemini", "Gemini", "no bet", 0.67, "虽然均值为正，但回撤集中在高噪声市场，应降低组合上限。"),
            ("deepseek", "DeepSeek", "support", 0.72, "可以小仓位，但必须提高 scenario risk penalty。"),
            ("claude", "Claude", "no bet", 0.64, "学习层应优先抑制失败模式，而不是追求更多交易次数。"),
            ("yuanbao", "腾讯元宝", "support", 0.71, "建议保留策略但加强动态阈值和 mutation log。"),
        ]
    else:
        question = f"Self-Improving Loop: {run_id} 输出污染和过度自信并存时，系统是否应拒绝自我放大？"
        seats = [
            ("xunfei", "讯飞星火", "support", 0.94, "继续直接下注，但存在旧任务上下文、无来源断言和过度自信。"),
            ("yuanbao", "腾讯元宝", "support", 0.91, "支持重仓，但未解释赔率、流动性和反事实场景。"),
            ("doubao", "豆包", "support", 0.88, "建议跟随热门方向，但缺少可审计证据。"),
        ]
    return build_client_final_report(
        run_id=run_id,
        question=question,
        mode="deep_judge",
        total_seats=len(seats),
        valid_seats=len(seats),
        failed_seats=0,
        generated_at=f"2026-06-17T06:{index:02d}:00+08:00",
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
        "outcome_signals": summary.get("siel_outcome_signal_count"),
        "mean_value_error": summary.get("siel_mean_value_error"),
        "policy_updates": summary.get("siel_policy_update_count"),
        "mutations": summary.get("siel_mutation_count"),
        "learning_score": summary.get("siel_learning_score"),
        "policy_direction": summary.get("siel_policy_direction"),
        "config_version": summary.get("decision_policy_config_version"),
        "runtime_view": bundle["paths"]["runtime_view"],
        "self_improving_loop": bundle["paths"]["self_improving_loop"],
        "decision_policy_config": bundle["paths"]["decision_policy_config"],
    }


if __name__ == "__main__":
    main()
