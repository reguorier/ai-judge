from __future__ import annotations

from core.blind_cross_validation import aggregate_blind_reviews, build_blind_cross_validation_packet
from core.evidence_broker import build_evidence_broker_report
from core.evidence_gap_queue import build_evidence_gap_queue, resolve_gap_task
from core.eval_dataset import build_eval_case_from_verdict
from core.eval_metrics import compute_evidence_quality_metrics
from core.grand_judge import run_grand_judge_mvp
from core.human_review import sign_human_review


def test_candidate_sources_do_not_verify_themselves():
    broker = build_evidence_broker_report(
        question="AI Judge",
        raw_answers=[{"seat": "chatgpt", "response": "参考 https://example.com/self 。"}],
        allow_network=False,
        generated_at="2026-05-16T00:00:00+00:00",
    )
    report = run_grand_judge_mvp(
        question="AI Judge",
        raw_answers=[{"seat": "chatgpt", "ok": True, "response": "参考 https://example.com/self 。"}],
        external_evidence=broker["items_for_validation"],
        generated_at="2026-05-16T00:00:00+00:00",
    )

    assert broker["counts"]["candidate_source"] == 1
    assert report["citation_verification"]["counts"]["unverifiable"] == 1
    assert "候选来源" in report["replay_ledger"][0]["citation_verification"]["items"][0]["reason"]


def test_user_supplied_evidence_can_verify_and_metrics_pass():
    broker = build_evidence_broker_report(
        question="AI Judge 引用验证",
        raw_answers=[{"seat": "gemini", "response": "参考 https://example.com/report 。"}],
        user_evidence=[{"url": "https://example.com/report", "title": "AI Judge 引用验证 report", "snippet": "AI Judge 引用验证"}],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    report = run_grand_judge_mvp(
        question="AI Judge 引用验证",
        raw_answers=[{"seat": "gemini", "ok": True, "response": "参考 https://example.com/report 。"}],
        external_evidence=broker["items_for_validation"],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    metrics = compute_evidence_quality_metrics(report)

    assert broker["counts"]["user_supplied"] == 1
    assert report["citation_verification"]["overall_status"] == "verified"
    assert metrics["trust_gate"] == "pass"


def test_blind_cross_validation_packet_and_aggregate():
    report = run_grand_judge_mvp(
        question="AI Judge",
        raw_answers=[{"seat": "chatgpt", "ok": True, "response": "无引用回答。"}],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    packet = build_blind_cross_validation_packet(question="AI Judge", grand_report=report, reviewers=["gemini", "qwen"])
    aggregate = aggregate_blind_reviews([
        {"reviewer": "gemini", "citation_id": "CITE-000", "decision": "confirm"},
        {"reviewer": "qwen", "citation_id": "CITE-000", "decision": "confirm"},
    ])

    assert packet["status"] == "pending_model_reviews"
    assert "ChatGPT" not in packet["review_prompts"][0]["prompt"]
    assert aggregate["citation_results"][0]["majority_confirmed"] is True


def test_gap_queue_and_human_signature_and_eval_case():
    report = run_grand_judge_mvp(
        question="AI Judge",
        raw_answers=[{"seat": "chatgpt", "ok": True, "response": "无引用回答。"}],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    report["evidence_gap_suggestions"] = {
        "suggestions": [
            {"citation_id": "CITE-000", "raw": "无显式引用", "status": "unverifiable", "mentor_level": "L3", "suggested_action": "补充来源"}
        ]
    }
    queue = build_evidence_gap_queue(report, generated_at="2026-05-16T00:00:00+00:00")
    resolved = resolve_gap_task(queue, task_id=queue["tasks"][0]["task_id"], resolution="added source", evidence_id="EVID-1")
    signature = sign_human_review(
        run_id="run-1",
        certification_hash=report["certification_hash"],
        reviewer="Auditor",
        decision="conditional",
        reason="我已确认当前不可验证来源需要后续补证据。",
        signed_at="2026-05-16T00:00:00+00:00",
    )
    case = build_eval_case_from_verdict({"run_id": "run-1", "question": "AI Judge", "grand_judge": report})

    assert queue["open_count"] == 1
    assert resolved["open_count"] == 0
    assert signature["signature_hash"]
    assert case["case_id"].startswith("EVAL-")

