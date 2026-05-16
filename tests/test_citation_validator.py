from __future__ import annotations

from core.citation_validator import UNVERIFIABLE_EXPLANATION, validate_citations


def test_citation_validator_outputs_verified_status():
    report = validate_citations(
        "方案依据 https://example.com/report 支持引用验证 MVP。",
        question="AI Judge 引用验证 MVP",
        external_evidence=[
            {
                "url": "https://example.com/report",
                "title": "AI Judge 引用验证 MVP report",
                "snippet": "引用验证 MVP 支持 verified / weakly_verified 状态。",
            }
        ],
        generated_at="2026-05-16T00:00:00+00:00",
    )

    assert report["overall_status"] == "verified"
    assert report["items"][0]["status"] == "verified"
    assert report["counts"]["verified"] == 1


def test_citation_validator_outputs_weak_irrelevant_unverifiable_and_contradicted():
    weak = validate_citations(
        "according to DeepMind AlphaFold study, 该技术已有基准结果。",
        question="DeepMind AlphaFold research",
        external_evidence=[{"title": "DeepMind AlphaFold technical report", "snippet": "protein folding benchmark"}],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    irrelevant = validate_citations(
        "参考 https://example.com/weather 。",
        question="AI Judge 引用验证",
        external_evidence=[{"url": "https://example.com/weather", "title": "Weather forecast", "snippet": "rain and temperature"}],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    unverifiable = validate_citations(
        "参考 https://missing.example/source 。",
        question="AI Judge 引用验证",
        external_evidence=[],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    contradicted = validate_citations(
        "参考 https://example.com/wrong 。",
        question="AI Judge 引用验证",
        external_evidence=[{"url": "https://example.com/wrong", "status": "contradicted", "snippet": "该断言被外部证据反驳"}],
        generated_at="2026-05-16T00:00:00+00:00",
    )

    assert weak["items"][0]["status"] == "weakly_verified"
    assert irrelevant["items"][0]["status"] == "irrelevant"
    assert unverifiable["items"][0]["status"] == "unverifiable"
    assert UNVERIFIABLE_EXPLANATION in unverifiable["unverifiable_explanation"]
    assert contradicted["overall_status"] == "contradicted"


def test_no_citation_is_unverifiable_not_false():
    report = validate_citations("这是没有引用的模型回答。", generated_at="2026-05-16T00:00:00+00:00")

    assert report["citation_count"] == 0
    assert report["overall_status"] == "unverifiable"
    assert "不是 false" in report["unverifiable_explanation"]
