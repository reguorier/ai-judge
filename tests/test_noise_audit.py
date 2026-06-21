from core.noise_audit import build_noise_audit, noise_summary


def test_noise_audit_scores_pollution_and_disagreement():
    audit = build_noise_audit(
        run_id="noise-test",
        question="是否应该发布？",
        mode="strategic",
        raw_results=[
            {
                "seat": "gemini",
                "ok": True,
                "response": "支持：有证据 A，建议发布。",
                "confidence": 0.82,
            },
            {
                "seat": "deepseek",
                "ok": True,
                "response": "反对：证据不足，建议暂缓。",
                "confidence": 0.42,
            },
            {
                "seat": "qwen",
                "ok": False,
                "response": "旧 AIJUDGE trace transcript 污染",
                "error": {"code": "transcript_pollution"},
                "execution_validity": {"polluted": True},
            },
        ],
    )

    assert audit["schema"] == "ai_judge.noise_audit.v1"
    assert audit["summary"]["models_total"] == 3
    assert audit["summary"]["pollution_count"] == 1
    assert audit["summary"]["conclusion_clusters"] >= 2
    assert "context_pollution" in audit["noise_sources"]
    assert audit["noise_level"] in {"high", "blocked"}
    assert audit["recommended_action"] == "block_publish_and_rerun"


def test_noise_summary_is_public_safe():
    audit = build_noise_audit(
        run_id="noise-low",
        question="是否继续？",
        mode="flash",
        raw_results=[
            {"seat": "gemini", "ok": True, "response": "支持：有来源依据。", "confidence": 0.7},
            {"seat": "wenxin", "ok": True, "response": "支持：有来源依据。", "confidence": 0.72},
        ],
    )

    summary = noise_summary(audit)

    assert summary["schema"] == "ai_judge.noise_audit.v1"
    assert summary["score"] == audit["noise_score"]
    assert summary["level"] == audit["noise_level"]
    assert "summary" in summary
