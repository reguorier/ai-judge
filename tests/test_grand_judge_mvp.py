from __future__ import annotations

from core.answer_certification import certify
from core.evidence_gap_filler import suggest_evidence_gaps
from core.grand_judge import run_grand_judge_mvp


def test_grand_judge_mvp_preserves_raw_mentor_and_external_evidence_isolation():
    raw_answer = "原文不可改写。参考 https://missing.example/source 。"
    report = run_grand_judge_mvp(
        question="升级 AI Judge",
        raw_answers=[{"seat": "chatgpt", "seat_name": "ChatGPT", "ok": True, "response": raw_answer}],
        mentor_supplements=[{"seat": "chatgpt", "seat_name": "ChatGPT", "ok": True, "response": "导师补充保持隔离。"}],
        external_evidence=[],
        run_id="run-1",
        generated_at="2026-05-16T00:00:00+00:00",
    )

    entry = report["replay_ledger"][0]
    assert report["phase"] == "citation_verification_mvp"
    assert entry["raw_answer"] == raw_answer
    assert entry["mentor_supplement"] == "导师补充保持隔离。"
    assert entry["unverifiable_reasons"]
    assert entry["verification_timestamp"] == "2026-05-16T00:00:00+00:00"
    assert report["source_isolation"]["raw_model_answers"] == "replay_ledger[].raw_answer"
    assert report["judge_contract"]["does_not_rewrite_model_originals"] is True


def test_evidence_gap_filler_is_suggestion_only():
    report = run_grand_judge_mvp(
        question="升级 AI Judge",
        raw_answers=[{"seat": "qwen", "ok": True, "response": "没有引用的方案。"}],
        generated_at="2026-05-16T00:00:00+00:00",
    )

    gaps = suggest_evidence_gaps(report)

    assert gaps["will_rewrite_body"] is False
    assert gaps["suggestions"][0]["action"] == "suggest_evidence_gap"
    assert gaps["suggestions"][0]["will_rewrite_body"] is False


def test_answer_certification_hash_includes_citation_report():
    citation_report = run_grand_judge_mvp(
        question="升级 AI Judge",
        raw_answers=[{"seat": "chatgpt", "ok": True, "response": "参考 https://example.com/report"}],
        external_evidence=[{"url": "https://example.com/report", "title": "AI Judge report", "snippet": "升级 AI Judge"}],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    cert_with_citation = certify(
        question="升级 AI Judge",
        mode="standard",
        seats=["chatgpt"],
        verdict_data={"verdict": "conditional"},
        claims=[{"claim_id": "C001", "claim": "升级 AI Judge", "_seat": "chatgpt", "score": 0.7, "tier": "conditional"}],
        citation_report=citation_report,
    )
    cert_without_citation = certify(
        question="升级 AI Judge",
        mode="standard",
        seats=["chatgpt"],
        verdict_data={"verdict": "conditional"},
        claims=[{"claim_id": "C001", "claim": "升级 AI Judge", "_seat": "chatgpt", "score": 0.7, "tier": "conditional"}],
    )

    assert cert_with_citation.citation_verification is not None
    assert cert_with_citation.citation_verification.certification_id.startswith("CITE-")
    assert cert_with_citation.certification_hash != cert_without_citation.certification_hash
