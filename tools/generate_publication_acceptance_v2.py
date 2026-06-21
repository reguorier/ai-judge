"""Generate source-grounded publication acceptance samples."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.reporting.publication import build_publication_report, render_publication_bundle
from product.reporting.publication.layout_compiler import compile_judge_ir


SOURCE_DIR = Path("/private/tmp/aijudge_pdf_text")
OUTPUT_DIR = ROOT / "artifacts" / os.environ.get(
    "PUBLICATION_ACCEPTANCE_DIR",
    "20260617-publication-format-acceptance-v2",
)


SAMPLES: list[dict[str, str]] = [
    {
        "id": "worldcup_run15_full",
        "title": "世界杯预测池全量报告 · run-15",
        "domain": "prediction_pool",
        "source": "full_run15.txt",
    },
    {
        "id": "worldcup_run15_dual",
        "title": "世界杯预测池 · 预测与下注双维度 · run-15",
        "domain": "prediction_pool",
        "source": "dual_run15.txt",
    },
    {
        "id": "worldcup_ticai_reference",
        "title": "2026世界杯 · 中国体彩投注分析参考",
        "domain": "prediction_pool",
        "source": "ticai.txt",
    },
    {
        "id": "worldcup_run11_full",
        "title": "世界杯预测池全量报告 · run-11",
        "domain": "prediction_pool",
        "source": "full_run11.txt",
    },
    {
        "id": "worldcup_run12_full",
        "title": "世界杯预测池全量报告 · run-12 正式版",
        "domain": "prediction_pool",
        "source": "full_run12.txt",
    },
    {
        "id": "worldcup_run9_bets",
        "title": "世界杯预测池 · run-9 下注拆解",
        "domain": "prediction_pool",
        "source": "bet_run9.txt",
    },
    {
        "id": "legal_equity_setoff",
        "title": "股东以股权清偿对公司赔偿债务：法律分析报告",
        "domain": "legal_memo",
        "source": "legal_equity.txt",
    },
]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"schema": "ai_judge.publication_acceptance_manifest.v2", "samples": []}
    index_lines = [
        "# AI Judge Publication Output V2 · Source-Grounded 验收包",
        "",
        "这些文件没有接入正式客户端输出，只用于验收新格式。",
        "",
    ]

    for sample in SAMPLES:
        source_path = SOURCE_DIR / sample["source"]
        if not source_path.exists():
            raise FileNotFoundError(f"missing extracted source text: {source_path}")
        source_text = _sanitize_source(source_path.read_text(encoding="utf-8"))
        report = _report_payload(sample, source_text)
        model = build_publication_report(report, domain_hint=sample["domain"], report_profile="both")
        outputs = render_publication_bundle(model)
        judge_ir = compile_judge_ir(model)

        stem = sample["id"]
        (OUTPUT_DIR / f"{stem}.json").write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (OUTPUT_DIR / f"{stem}.judge_ir.json").write_text(
            json.dumps(judge_ir.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (OUTPUT_DIR / f"{stem}.md").write_text(outputs["markdown"], encoding="utf-8")
        (OUTPUT_DIR / f"{stem}.html").write_text(outputs["html"], encoding="utf-8")

        quality = model.get("quality") if isinstance(model.get("quality"), dict) else {}
        manifest["samples"].append(
            {
                "id": stem,
                "title": sample["title"],
                "domain": sample["domain"],
                "quality": quality.get("status", "unknown"),
                "markdown": f"{stem}.md",
                "html": f"{stem}.html",
                "json": f"{stem}.json",
                "judge_ir": f"{stem}.judge_ir.json",
            }
        )
        index_lines.append(
            f"- `{stem}` · {sample['title']} · {sample['domain']} · quality={quality.get('status', 'unknown')}"
        )
        print(f"wrote {stem}")

    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    return 0


def _report_payload(sample: dict[str, str], source_text: str) -> dict[str, Any]:
    if sample["domain"] == "legal_memo":
        return {
            "run_id": sample["id"],
            "question": sample["title"],
            "title": sample["title"],
            "mode": "deep_judge",
            "source_text": source_text,
            "body_text": source_text,
            "core_conclusion": "可以把股权作为执行和变现对象，但主路径应是变价清偿。",
            "recommended_actions": [
                "优先申请法院冻结、评估、拍卖或变卖股权。",
                "避免表述为公司直接受让自身股权抵债。",
                "补齐章程、登记、案卷、财务和优先购买权材料。",
            ],
            "risks": [
                "公司直接取得自身股权可能触发资本维持和登记风险。",
                "股权估值、权利负担和优先购买权会影响处置效率。",
            ],
            "evidence_strength": {"overall": "medium", "items": [{"description": "历史法律报告全文已纳入源文增强。", "strength": "medium"}]},
            "audit": {"valid_seats": 10, "failed_seats": 0, "total_seats": 10},
            "noise_audit": _noise(30),
            "model_stability": _stability(),
        }

    return {
        "run_id": sample["id"],
        "question": sample["title"],
        "title": sample["title"],
        "mode": "prediction_pool",
        "mode_label": "预测池",
        "source_text": source_text,
        "body_text": source_text,
        "core_conclusion": "预测池报告应先解释模型行为和资金风险，再给逐场参考。",
        "recommended_actions": [
            "先拆分预测命中、下注 ROI 和资金暴露。",
            "对缺盘口、低赔率和高集中度场次保留人工复核。",
        ],
        "risks": [
            "历史 PDF 迁移样本仍需回源确认赔率、赛果和盘口时间戳。",
            "模型共识可能来自同一激励结构，不等于独立判断。",
        ],
        "evidence_strength": {"overall": "medium", "items": [{"description": "历史预测池报告全文已纳入源文增强。", "strength": "medium"}]},
        "audit": {"valid_seats": 11, "failed_seats": 1, "total_seats": 12},
        "noise_audit": _noise(35),
        "model_stability": _stability(),
    }


def _noise(score: int) -> dict[str, Any]:
    return {
        "noise_score": score,
        "noise_level": "medium" if score >= 30 else "low",
        "recommended_action": "manual_review_recommended",
        "noise_sources": ["source_text_migration", "historical_report_reflow"],
        "summary": {"schema_failures": 0, "pollution_count": 0},
    }


def _stability() -> dict[str, Any]:
    return {
        "profile_count": 2,
        "profiles": [
            {"seat": "deepseek", "seat_name": "DeepSeek", "runs_seen": 5, "stability_score": 82, "rates": {"valid_rate": 1.0, "schema_failure_rate": 0.0}},
            {"seat": "gemini", "seat_name": "Gemini", "runs_seen": 5, "stability_score": 76, "rates": {"valid_rate": 1.0, "schema_failure_rate": 0.0}},
        ],
    }


def _sanitize_source(text: str) -> str:
    text = re.sub(r"file:///Users/[^\n]+", "", text)
    text = re.sub(r"/Users/[^\s)]+", "[local-path-redacted]", text)
    text = re.sub(r"/private/(?:var|tmp|folders)[^\s)]+", "[local-path-redacted]", text)
    return text.strip()


if __name__ == "__main__":
    raise SystemExit(main())
