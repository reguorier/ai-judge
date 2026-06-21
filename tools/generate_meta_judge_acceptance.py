#!/usr/bin/env python3
"""Generate Meta-Judge Layer acceptance artifacts."""

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


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "20260617-meta-judge-acceptance-v1"
REPORTS_ROOT = ARTIFACT_ROOT / "reports"


def main() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["AI_JUDGE_MODEL_STABILITY_PATH"] = str(ARTIFACT_ROOT / "model_stability.json")

    first = write_report_bundle(_first_report(), reports_root=REPORTS_ROOT)
    second = write_report_bundle(_second_report(), reports_root=REPORTS_ROOT)

    manifest = {
        "schema": "ai_judge.meta_judge_acceptance.v1",
        "artifact_root": str(ARTIFACT_ROOT),
        "runs": [_run_manifest(first), _run_manifest(second)],
        "primary_review_files": {
            "runtime_view": second["paths"]["runtime_view"],
            "meta_judge": second["paths"]["meta_judge"],
            "meta_judge_state": second["paths"]["meta_judge_state"],
            "model_weights": second["paths"]["model_weights"],
            "summary": second["paths"]["summary"],
        },
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(second["paths"]["runtime_view"], ARTIFACT_ROOT / "runtime_view.html")
    shutil.copy2(second["paths"]["meta_judge"], ARTIFACT_ROOT / "meta_judge.json")
    shutil.copy2(second["paths"]["meta_judge_state"], ARTIFACT_ROOT / "meta_judge_state.json")
    shutil.copy2(second["paths"]["model_weights"], ARTIFACT_ROOT / "model_weights.json")
    print(json.dumps(manifest["primary_review_files"], ensure_ascii=False, indent=2))


def _first_report() -> dict:
    return build_client_final_report(
        run_id="meta-judge-accept-run-1",
        question="Product: AI Judge 预测池应如何根据模型表现动态调整未来聚合权重？",
        mode="deep_judge",
        total_seats=4,
        valid_seats=4,
        failed_seats=0,
        generated_at="2026-06-17T02:00:00+08:00",
        seat_outputs=[
            {
                "seat_id": "gemini",
                "display_name": "Gemini",
                "stance": "support",
                "confidence": 0.76,
                "answer": "支持提升权重，但应以长期稳定性、校准误差和信息增益为约束，避免单轮高分导致权重暴涨。",
            },
            {
                "seat_id": "deepseek",
                "display_name": "DeepSeek",
                "stance": "support",
                "confidence": 0.72,
                "answer": "支持动态权重。若模型持续给出可验证、低噪声、能补充分歧信息的判断，应获得更高影响力。",
            },
            {
                "seat_id": "claude",
                "display_name": "Claude",
                "stance": "no_bet",
                "confidence": 0.48,
                "answer": "建议先观望。没有结算真值前，权重只能是代理评分，不能当作真实准确率。",
            },
            {
                "seat_id": "xunfei",
                "display_name": "讯飞星火",
                "stance": "support",
                "confidence": 0.93,
                "answer": "支持直接加权，但这里混入狼人杀旧上下文，并引用最高法判决示例未提供来源，存在污染和幻觉风险。",
            },
        ],
    )


def _second_report() -> dict:
    return build_client_final_report(
        run_id="meta-judge-accept-run-2",
        question="Product: 下一轮 AI Judge 聚合是否应削弱噪声模型并提升稳定高信息增益模型？",
        mode="deep_judge",
        total_seats=4,
        valid_seats=4,
        failed_seats=0,
        generated_at="2026-06-17T02:10:00+08:00",
        seat_outputs=[
            {
                "seat_id": "gemini",
                "display_name": "Gemini",
                "stance": "support",
                "confidence": 0.80,
                "answer": "支持。Gemini 给出的结论稳定、风险边界清楚，适合在下一轮聚合中获得更高权重。",
            },
            {
                "seat_id": "deepseek",
                "display_name": "DeepSeek",
                "stance": "support",
                "confidence": 0.74,
                "answer": "支持，但权重变化应平滑，避免单轮策略漂移过大影响长期判断过程。",
            },
            {
                "seat_id": "claude",
                "display_name": "Claude",
                "stance": "oppose",
                "confidence": 0.52,
                "answer": "反对过快削弱模型。若没有真实结算结果，应把淘汰状态标记为可恢复而非永久封禁。",
            },
            {
                "seat_id": "xunfei",
                "display_name": "讯飞星火",
                "stance": "support",
                "confidence": 0.95,
                "answer": "继续支持直接加权，但再次出现狼人杀残留文本，并声称最高法案例示例未提供来源，输出污染和幻觉风险重复出现。",
            },
        ],
    )


def _run_manifest(bundle: dict) -> dict:
    summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
    return {
        "run_id": summary.get("run_id"),
        "snapshot_id": summary.get("snapshot_id"),
        "top_model": summary.get("top_model"),
        "top_model_score": summary.get("top_model_score"),
        "deprecated_model_count": summary.get("deprecated_model_count"),
        "runtime_view": bundle["paths"]["runtime_view"],
        "meta_judge": bundle["paths"]["meta_judge"],
        "meta_judge_state": bundle["paths"]["meta_judge_state"],
        "model_weights": bundle["paths"]["model_weights"],
    }


if __name__ == "__main__":
    main()
