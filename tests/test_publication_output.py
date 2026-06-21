"""Publication Output V2 tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.publication import (
    build_publication_report,
    render_publication_bundle,
)
from product.reporting.publication.domain_router import detect_domain
from product.reporting.publication.judge_ir import IRComponent
from product.reporting.publication.layout_compiler import compile_judge_ir
from product.reporting.publication.render_contract import RenderContractError, validate_judge_ir
from product.reporting.publication.renderer_html import render_judge_ir_html


def _sample_report(domain_hint: str = "auto") -> dict:
    return {
        "run_id": "publication-test-run",
        "question": "世界杯预测池 run-15：预测和下注怎么拆？",
        "title": "世界杯预测池全量报告",
        "mode": "prediction_pool",
        "mode_label": "预测池",
        "status": "completed",
        "core_conclusion": "本轮应区分预测和下注：预测是判断方向，下注是资金管理选择。",
        "consensus": ["多数席位认为葡萄牙方向更稳。"],
        "disagreements": ["是否应该在低赔率下继续下注存在分歧。"],
        "risks": ["赔率缺口会放大下注噪声。"],
        "recommended_actions": ["高噪声比赛先人工复核，再进入结算。"],
        "evidence_strength": {"overall": "medium", "items": [{"description": "席位覆盖 11/12", "strength": "medium"}]},
        "audit": {"valid_seats": 11, "failed_seats": 1, "total_seats": 12},
        "noise_audit": {
            "schema": "ai_judge.noise_audit.v1",
            "noise_score": 42,
            "noise_level": "medium",
            "recommended_action": "manual_review_recommended",
            "noise_sources": ["confidence_dispersion", "selection_disagreement"],
            "summary": {"schema_failures": 1, "pollution_count": 0},
        },
        "model_stability": {
            "schema": "ai_judge.model_stability_profiles.v1",
            "profile_count": 1,
            "profiles": [
                {
                    "seat": "xunfei",
                    "seat_name": "讯飞星火",
                    "runs_seen": 3,
                    "stability_score": 78,
                    "rates": {"valid_rate": 1.0, "schema_failure_rate": 0.0},
                }
            ],
        },
        "prediction_pool": {
            "summary": {
                "valid_seats": "11/12",
                "accepted_bets": 23,
                "no_bets": 32,
                "total_stake_gp": 4170,
                "loan_exposure_gp": 0,
                "roi": 0,
            },
            "matches": [
                {
                    "match": "葡萄牙 vs 哥伦比亚",
                    "consensus": "葡萄牙胜",
                    "recommendation": "小额主胜，赔率不足则观望",
                    "risk": "平局概率不可忽视",
                }
            ],
            "models": [
                {"seat": "deepseek", "behavior": "预测但不下注", "risk": "保守", "note": "认为盘口没有优势"}
            ],
        },
        "domain_hint": domain_hint,
    }


def test_detect_domain_routes_key_question_types():
    assert detect_domain("股东以股权清偿公司赔偿债务，法院能否执行？") == "legal_memo"
    assert detect_domain("世界杯预测池 run-15 下注 ROI 和 GP 怎么看？") == "prediction_pool"
    assert detect_domain("这个 API 链路烟测是否通过？") == "ops_check"
    assert detect_domain("普通产品策略怎么收口？") == "business_strategy"


def test_publication_report_contains_base_industry_and_audit_without_path_leak():
    model = build_publication_report(_sample_report(), domain_hint="auto")
    outputs = render_publication_bundle(model)
    blob = json.dumps(model, ensure_ascii=False) + outputs["html"] + outputs["markdown"]

    assert model["schema"] == "ai_judge.publication_report.v2"
    assert model["domain"] == "prediction_pool"
    assert model["reader_blocks"]
    assert model["base_blocks"]
    assert model["industry_blocks"]
    assert model["audit_blocks"]
    body = outputs["markdown"].split("## 延伸材料", 1)[0]
    assert "预测 vs 下注" in outputs["markdown"]
    assert "Noise Audit / 噪声审计" in outputs["markdown"]
    assert "Model Stability / 模型稳定性画像" in outputs["markdown"]
    assert "Noise Audit / 噪声审计" not in body
    assert "Model Stability / 模型稳定性画像" not in body
    assert "## 当前建议" in body
    assert "## 关键依据" in body
    assert "## 最大风险" in body
    assert "## 适用边界" in body
    assert "/Users/" not in blob
    assert "file:///" not in blob
    assert model["quality"]["publishable"] is True


def test_judge_ir_layout_contract_enforces_fixed_section_order():
    model = build_publication_report(_sample_report(), domain_hint="prediction_pool")
    ir = compile_judge_ir(model)

    assert tuple(section.slot for section in ir.sections) == (
        "summary",
        "metrics",
        "analysis",
        "comparison",
        "risk",
        "appendix",
    )
    assert validate_judge_ir(ir) is ir


def test_judge_ir_renderer_rejects_unstructured_and_raw_html_inputs():
    model = build_publication_report(_sample_report(), domain_hint="prediction_pool")
    ir = compile_judge_ir(model)

    try:
        validate_judge_ir({"title": "not ir"})
    except RenderContractError as exc:
        assert str(exc) == "render_input_must_be_judge_ir"
    else:
        raise AssertionError("unstructured input was accepted")

    unsafe_ir = type(ir)(
        title=ir.title,
        subtitle=ir.subtitle,
        run_id=ir.run_id,
        domain_label=ir.domain_label,
        generated_at=ir.generated_at,
        sections=ir.sections,
        rail=IRComponent("RailSummary", {"variant": "rail", "raw_html": "<script>alert(1)</script>"}),
        quality=ir.quality,
    )
    try:
        validate_judge_ir(unsafe_ir)
    except RenderContractError as exc:
        assert "raw_html_prop_rejected" in str(exc)
    else:
        raise AssertionError("raw HTML prop was accepted")


def test_judge_ir_html_rendering_is_deterministic_and_component_based():
    model = build_publication_report(_sample_report(), domain_hint="prediction_pool")
    ir = compile_judge_ir(model)

    first = render_judge_ir_html(ir)
    second = render_judge_ir_html(ir)

    assert first == second
    assert 'content="judge-ir-component-renderer" name="ai-judge-renderer"' in first
    assert "审阅目录" in first
    assert "风险矩阵" in first
    assert "MetricGrid" not in first
    assert "<script" not in first


def test_prediction_pool_does_not_guess_matches_from_broken_pdf_text():
    report = _sample_report()
    report.pop("prediction_pool")
    report["body_text"] = "A目前被执行总标的 vs 可供执行财产净值？这不是比赛，只是破碎 PDF 文本。"

    model = build_publication_report(report, domain_hint="prediction_pool")
    outputs = render_publication_bundle(model)

    assert "A目前被执行总标的 vs 可供执行财产净值" not in outputs["markdown"]
    assert "暂无逐场结构化数据" in outputs["markdown"]


def test_source_text_enriches_prediction_pool_without_audit_noise_in_body():
    report = _sample_report()
    report.pop("prediction_pool")
    report["source_text"] = """
    世界杯预测池全量报告：run-15
    11/12有效 · 23笔下注 · 32次观望 · 零贷款
    5场比赛 · 葡萄牙vs哥伦比亚为主战场（8席/1,360 GP）
    总投入 4,170 GP
    DeepSeek 全场零注：守榜首保守策略，仅在有明确概率边缘且能交叉验证时下注。
    比利时让球线参数缺失，DeepSeek、Gemini、ChatGPT选择不下注。
    """

    model = build_publication_report(report, domain_hint="prediction_pool")
    outputs = render_publication_bundle(model)
    body = outputs["markdown"].split("## 延伸材料", 1)[0]

    assert "专业分析" in body
    assert "11/12 席有效、23 笔下注、32 次观望、贷款暴露降为 0" in body
    assert "原文证据映射" in outputs["markdown"]
    assert "Noise Audit / 噪声审计" not in body


def test_source_text_enriches_legal_memo_with_syllogism():
    report = {
        "run_id": "publication-legal-source-test",
        "question": "股东以股权清偿对公司赔偿债务，法院能否执行？",
        "mode": "deep_judge",
        "core_conclusion": "可以把股权作为执行和变现对象，但主路径应是变价清偿。",
        "source_text": "股权属于财产性权益。正确表达：依法处置股权后以价款清偿。错误表达：直接将股权过户给公司抵债。《公司法》第85条。",
        "audit": {"valid_seats": 10, "failed_seats": 0, "total_seats": 10},
    }

    model = build_publication_report(report, domain_hint="legal_memo")
    outputs = render_publication_bundle(model)
    body = outputs["markdown"].split("## 延伸材料", 1)[0]

    assert "专业分析" in body
    assert "法律三段论地图" in outputs["markdown"]
    assert "公司直接取得自身股权" in body
    assert "Noise Audit / 噪声审计" not in body


def test_legal_publication_report_uses_legal_memo_blocks_without_path_leak():
    report = {
        "run_id": "publication-legal-test",
        "question": "股东以股权清偿对公司赔偿债务，法院能否执行？",
        "mode": "deep_judge",
        "core_conclusion": "可以把股权作为执行和变现对象，但主路径应是变价清偿。",
        "body_text": "依据《民事诉讼法》第二百四十八条，股权属于可供执行的财产性权益。",
        "verified_facts": [{"fact": "债务人为公司股东。", "source": "用户问题"}],
        "inferences": [{"text": "股权可执行，但不宜直接抵债。", "strength": "medium"}],
        "risks": ["股权价值不足以覆盖赔偿金。"],
        "recommended_actions": ["申请法院冻结股权并启动评估。"],
        "evidence_strength": {"overall": "medium", "items": [{"description": "需律师核对最新条文。"}]},
        "audit": {"valid_seats": 10, "failed_seats": 1, "total_seats": 11},
        "noise_audit": {
            "noise_score": 35,
            "noise_level": "medium",
            "recommended_action": "manual_review_recommended",
            "noise_sources": ["evidence_gap"],
            "summary": {"schema_failures": 0, "pollution_count": 0},
        },
        "model_stability": {"profile_count": 0, "profiles": []},
    }

    model = build_publication_report(report, domain_hint="legal_memo")
    outputs = render_publication_bundle(model)
    blob = json.dumps(model, ensure_ascii=False) + outputs["html"] + outputs["markdown"]

    assert model["domain"] == "legal_memo"
    assert model["reader_blocks"]
    assert "法律依据" in outputs["markdown"]
    assert "事实认定与涵摄" in outputs["markdown"]
    assert "律师复核清单" in outputs["markdown"]
    body = outputs["markdown"].split("## 延伸材料", 1)[0]
    assert "律师复核清单" not in body
    assert "Noise Audit / 噪声审计" not in body
    assert "/Users/" not in blob
    assert "file:///" not in blob
