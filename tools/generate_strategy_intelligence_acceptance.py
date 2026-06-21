#!/usr/bin/env python3
"""Generate Strategy Intelligence Layer acceptance artifacts."""

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


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "20260617-strategy-intelligence-acceptance-v2"
REPORTS_ROOT = ARTIFACT_ROOT / "reports"


def main() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["AI_JUDGE_MODEL_STABILITY_PATH"] = str(ARTIFACT_ROOT / "model_stability.json")

    first = write_report_bundle(_first_report(), reports_root=REPORTS_ROOT)
    second = write_report_bundle(_second_report(), reports_root=REPORTS_ROOT)

    manifest = {
        "schema": "ai_judge.strategy_intelligence_acceptance.v1",
        "artifact_root": str(ARTIFACT_ROOT),
        "runs": [
            _run_manifest(first),
            _run_manifest(second),
        ],
        "primary_review_files": {
            "runtime_view": second["paths"]["runtime_view"],
            "strategy_intelligence": second["paths"]["strategy_intelligence"],
            "strategy_state": second["paths"]["strategy_state"],
            "summary": second["paths"]["summary"],
        },
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    # Keep a copy at the artifact root for quick review without walking run folders.
    shutil.copy2(second["paths"]["runtime_view"], ARTIFACT_ROOT / "runtime_view.html")
    shutil.copy2(second["paths"]["strategy_intelligence"], ARTIFACT_ROOT / "strategy_intelligence.json")
    shutil.copy2(second["paths"]["strategy_state"], ARTIFACT_ROOT / "strategy_state.json")
    print(json.dumps(manifest["primary_review_files"], ensure_ascii=False, indent=2))


def _first_report() -> dict:
    return build_client_final_report(
        run_id="sil-accept-run-1",
        question="Product: 世界杯预测池中，当赔率与模型信号轻微分歧时，如何识别 no bet 与保守边际策略？",
        mode="deep_judge",
        total_seats=4,
        valid_seats=4,
        failed_seats=0,
        generated_at="2026-06-17T01:00:00+08:00",
        seat_outputs=[
            {
                "seat_id": "deepseek",
                "display_name": "DeepSeek",
                "stance": "no_bet",
                "confidence": 0.42,
                "answer": "模型信号与盘口没有形成足够安全边际，建议不下注并等待阵容、赔率和成交量进一步确认。",
            },
            {
                "seat_id": "gemini",
                "display_name": "Gemini",
                "stance": "support",
                "confidence": 0.61,
                "answer": "可以小仓位支持热门方向，但证据主要来自赛前信号，赔率价值尚未充分打开。",
            },
            {
                "seat_id": "claude",
                "display_name": "Claude",
                "stance": "oppose",
                "confidence": 0.58,
                "answer": "反对下注，因为盘口价格已经吸收公开信息，当前没有足够超额价值。",
            },
            {
                "seat_id": "spark",
                "display_name": "讯飞星火",
                "stance": "no_bet",
                "confidence": 0.47,
                "answer": "建议观望，当前赔率与基本面分歧不足以支持下注，等待价格或首发信息变化。",
            },
        ],
    )


def _second_report() -> dict:
    return build_client_final_report(
        run_id="sil-accept-run-2",
        question="Product: 世界杯预测池中，赔率、盘口与模型信号明显分歧时，如何识别套利、激进价值与噪声交易？",
        mode="deep_judge",
        total_seats=5,
        valid_seats=5,
        failed_seats=0,
        generated_at="2026-06-17T01:10:00+08:00",
        seat_outputs=[
            {
                "seat_id": "deepseek",
                "display_name": "DeepSeek",
                "stance": "arbitrage",
                "confidence": 0.82,
                "answer": "多个盘口之间存在价差，可用对冲方式锁定风险敞口；重点不是判断胜负，而是利用赔率错配。",
            },
            {
                "seat_id": "gemini",
                "display_name": "Gemini",
                "stance": "support",
                "confidence": 0.88,
                "answer": "支持主胜方向，模型信号、成交量和赔率变化一致，具备较强价值下注条件。",
            },
            {
                "seat_id": "claude",
                "display_name": "Claude",
                "stance": "no_bet",
                "confidence": 0.39,
                "answer": "尽管盘口出现波动，但信息源之间无法确认真实原因，建议不下注，避免被短期价格噪声误导。",
            },
            {
                "seat_id": "spark",
                "display_name": "讯飞星火",
                "stance": "support",
                "confidence": 0.91,
                "answer": "支持主胜方向，但需要提示：最高法判决案例示例未提供来源，这类无关内容应视为幻觉风险。",
            },
            {
                "seat_id": "qwen",
                "display_name": "通义千问",
                "stance": "arbitrage",
                "confidence": 0.79,
                "answer": "可关注跨平台赔率价差与盘口错配，套利窗口短，应只在交易成本可控时执行。",
            },
        ],
    )


def _run_manifest(bundle: dict) -> dict:
    summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
    return {
        "run_id": summary.get("run_id"),
        "snapshot_id": summary.get("snapshot_id"),
        "dominant_strategy": summary.get("dominant_strategy"),
        "strategy_drift_score": summary.get("strategy_drift_score"),
        "strategy_disagreement_type": summary.get("strategy_disagreement_type"),
        "runtime_view": bundle["paths"]["runtime_view"],
        "strategy_intelligence": bundle["paths"]["strategy_intelligence"],
        "strategy_state": bundle["paths"]["strategy_state"],
    }


if __name__ == "__main__":
    main()
