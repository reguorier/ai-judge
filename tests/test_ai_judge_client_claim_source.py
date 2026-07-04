from __future__ import annotations


def test_client_smoke_prints_claim_source_support_summary(monkeypatch, capsys):
    from client import ai_judge_client

    monkeypatch.setattr(
        ai_judge_client,
        "submit_direct",
        lambda *args, **kwargs: {
            "run_id": "client-claim-source",
            "status": "partial_completed",
            "human_status": "部分完成",
            "support_verdict_counts": {
                "supported": 3,
                "unsupported_by_cited_source": 1,
                "contradicted": 0,
                "not_enough_evidence": 2,
            },
            "overall_support_verdict": "unsupported_by_cited_source",
            "claim_support_pass_rate": 0.5,
        },
    )

    assert ai_judge_client.main(["--smoke"]) == 0

    out = capsys.readouterr().out
    assert "claim_source_support: overall=unsupported_by_cited_source pass_rate=0.5" in out
    assert "supported=3 unsupported_by_cited_source=1 contradicted=0 not_enough_evidence=2" in out
