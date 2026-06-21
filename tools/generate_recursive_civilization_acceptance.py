#!/usr/bin/env python3
"""Generate Recursive Civilization Layer acceptance artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from product.reporting.final_report_builder import build_client_final_report, write_report_bundle


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "20260617-recursive-civilization-acceptance-v2"
RUN_NAMESPACE = os.environ.get("RCL_ACCEPTANCE_NAMESPACE") or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
REPORTS_ROOT = ARTIFACT_ROOT / f"reports-{RUN_NAMESPACE}"


def main() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["AI_JUDGE_MODEL_STABILITY_PATH"] = str(ARTIFACT_ROOT / "model_stability.json")

    patterns = ["noise", "price", "price", "liquidity", "reversal", "drawdown", "price", "civilization"]
    bundles = [
        write_report_bundle(_report(f"rcl-accept-{RUN_NAMESPACE}-run-{index}", pattern, index), reports_root=REPORTS_ROOT)
        for index, pattern in enumerate(patterns)
    ]
    latest = bundles[-1]
    manifest = {
        "schema": "ai_judge.recursive_civilization_acceptance.v1",
        "artifact_root": str(ARTIFACT_ROOT),
        "run_namespace": RUN_NAMESPACE,
        "runs": [_run_manifest(bundle) for bundle in bundles],
        "primary_review_files": {
            "runtime_view": latest["paths"]["runtime_view"],
            "recursive_civilization": latest["paths"]["recursive_civilization"],
            "recursive_civilization_state": latest["paths"]["recursive_civilization_state"],
            "autonomous_economy": latest["paths"]["autonomous_economy"],
            "summary": latest["paths"]["summary"],
        },
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for key, filename in [
        ("runtime_view", "runtime_view.html"),
        ("recursive_civilization", "recursive_civilization.json"),
        ("recursive_civilization_state", "recursive_civilization_state.json"),
        ("autonomous_economy", "autonomous_economy.json"),
        ("summary", "summary.json"),
    ]:
        shutil.copy2(latest["paths"][key], ARTIFACT_ROOT / filename)
    print(json.dumps(manifest["primary_review_files"], ensure_ascii=False, indent=2))


def _report(run_id: str, pattern: str, index: int) -> dict:
    if pattern == "price":
        question = f"Recursive Civilization Layer: {run_id} 正期望策略连续胜出时，文明是否应采用绩效议会治理？"
        seats = [
            ("gemini", "Gemini", "arbitrage", 0.87, "赔率错配持续出现，价值策略文明应获得更高资本份额，但需要风险议会保留否决权。"),
            ("deepseek", "DeepSeek", "support value bet", 0.83, "建议让正 ROI 策略形成绩效城市，治理规则按风险调整收益选择。"),
            ("claude", "Claude", "support", 0.76, "同意小仓位执行，同时要求每次扩张必须通过治理适应度检查。"),
            ("qwen", "通义千问", "support", 0.79, "表现好的策略可以产生克隆分支，但分支必须归入同一治理层级。"),
        ]
    elif pattern == "liquidity":
        question = f"Recursive Civilization Layer: {run_id} 流动性下降时，文明之间是否应合并或收缩？"
        seats = [
            ("gemini", "Gemini", "support", 0.80, "流动性下降会放大滑点，低份额文明应尝试合并以保留治理资源。"),
            ("deepseek", "DeepSeek", "arbitrage", 0.75, "仍有价差，但商人型文明要按流动性调整扩张规则。"),
            ("claude", "Claude", "no bet", 0.63, "保守议会文明应暂时提高资本防守权重。"),
            ("xunfei", "讯飞星火", "support", 0.72, "可以保留代理，但要降低风险预算并观察下一轮治理演化。"),
        ]
    elif pattern == "reversal":
        question = f"Recursive Civilization Layer: {run_id} 临场信号反转时，失败文明是否应分裂或崩塌？"
        seats = [
            ("gemini", "Gemini", "oppose", 0.70, "原策略在反转场景下失效，应让其文明失去资本份额。"),
            ("deepseek", "DeepSeek", "support value bet", 0.68, "价格仍有可能，但必须等待二次确认，治理规则应更保守。"),
            ("claude", "Claude", "no bet", 0.67, "建议暂不执行，让保守文明获得更多资本保护组合。"),
            ("qwen", "通义千问", "oppose", 0.69, "连续负反馈的文明应触发崩塌或重组事件。"),
        ]
    elif pattern == "drawdown":
        question = f"Recursive Civilization Layer: {run_id} 回撤集中时，治理规则是否应突变为风险宪章？"
        seats = [
            ("gemini", "Gemini", "no bet", 0.68, "回撤集中说明高收益文明需要更强风险否决。"),
            ("deepseek", "DeepSeek", "support", 0.72, "应保留文明但降低其扩张规则和资本乘数。"),
            ("claude", "Claude", "no bet", 0.65, "治理层应优先保护资本，而不是追逐交易次数。"),
            ("yuanbao", "腾讯元宝", "support", 0.71, "建议让资本从高回撤文明流向稳定文明。"),
        ]
    elif pattern == "civilization":
        question = f"Recursive Civilization Layer: {run_id} 多个策略社会形成后，是否应生成元文明宪章？"
        seats = [
            ("gemini", "Gemini", "support", 0.84, "当绩效城市、保守议会和套利商会并存时，应生成双院制元文明。"),
            ("deepseek", "DeepSeek", "arbitrage", 0.78, "元文明应把价格信号、资本分配和风险否决拆成不同治理院。"),
            ("claude", "Claude", "support", 0.73, "支持递归治理，但候选宪章必须先进入观察，不直接支配生产层。"),
            ("xunfei", "讯飞星火", "no bet", 0.61, "治理递归过快时，应保留人工复核阈值。"),
            ("qwen", "通义千问", "support value bet", 0.80, "建议把成功策略群体升级为文明，再由元文明统一约束。"),
        ]
    else:
        question = f"Recursive Civilization Layer: {run_id} 噪声和过度自信并存时，噪声文明是否应隔离？"
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
        generated_at=f"2026-06-17T10:{index:02d}:00+08:00",
        seat_outputs=[
            {
                "seat_id": seat_id,
                "display_name": display,
                "stance": stance,
                "confidence": confidence,
                "answer": f"{answer}\n\n{_grounding_paragraph(question)}",
            }
            for seat_id, display, stance, confidence, answer in seats
        ],
    )


def _grounding_paragraph(question: str) -> str:
    return (
        f"本席位直接回应议题「{question}」。分析重点是策略社会、文明分组、治理规则、资本分配、"
        "绩效议会、风险否决、文明竞争、文明合并、文明分裂、文明崩塌、元文明宪章和涌现行为。"
        "因此结论不是普通下注建议，而是判断这些策略是否应归入可审计的治理文明，并说明下一轮"
        "如何通过治理突变、选择压力和资本约束影响系统运行。"
    )


def _run_manifest(bundle: dict) -> dict:
    summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
    return {
        "run_id": summary.get("run_id"),
        "snapshot_id": summary.get("snapshot_id"),
        "agent_count": summary.get("ael_agent_count"),
        "civilization_count": summary.get("rcl_civilization_count"),
        "active_civilizations": summary.get("rcl_active_civilization_count"),
        "collapsed_civilizations": summary.get("rcl_collapsed_civilization_count"),
        "top_civilization_id": summary.get("rcl_top_civilization_id"),
        "top_governance_archetype": summary.get("rcl_top_governance_archetype"),
        "governance_mutations": summary.get("rcl_governance_mutation_count"),
        "interactions": summary.get("rcl_interaction_count"),
        "meta_civilizations": summary.get("rcl_meta_civilization_count"),
        "emergent_behaviors": summary.get("rcl_emergent_behavior_count"),
        "civilization_entropy": summary.get("rcl_civilization_entropy"),
        "runtime_view": bundle["paths"]["runtime_view"],
        "recursive_civilization": bundle["paths"]["recursive_civilization"],
    }


if __name__ == "__main__":
    main()
