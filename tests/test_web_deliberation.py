from core.web_jury import (
    build_mentor_supplement_claims,
    build_resonance_followup_prompts,
    build_judge_answer,
    build_score_rounds,
    build_seat_answer_digest,
    build_single_judge_baseline,
    build_web_deliberation,
    build_web_claims,
    run_web_jury,
    _bridge_collection_insufficient,
)


def test_web_deliberation_builds_summary_peer_reviews_and_claims():
    results = [
        {
            "seat": "chatgpt",
            "seat_name": "ChatGPT",
            "ok": True,
            "response": "建议法国夺冠。依据包括阵容深度、历史淘汰赛经验、2026年赛程风险与伤病风险，需要验证小组抽签。",
        },
        {
            "seat": "qwen",
            "seat_name": "Qwen",
            "ok": True,
            "response": "条件判断：阿根廷、法国、巴西都有机会。需要看2026年分组、主力健康和赛程。",
        },
        {
            "seat": "grok",
            "seat_name": "Grok",
            "ok": False,
            "supplementable": True,
            "error": {"code": "slow_response_pending", "message": "slow"},
        },
    ]

    deliberation = build_web_deliberation("预测2026世界杯冠军", "standard", results)

    assert deliberation["ok_count"] == 2
    assert deliberation["failed_count"] == 1
    assert deliberation["summary_claim_count"] == 2
    assert deliberation["peer_review_count"] == 2
    assert len(deliberation["answer_summaries"]) == 2
    assert any(claim.get("deliberation_phase") == "peer_review" for claim in deliberation["claims"])


def test_web_claims_plus_deliberation_preserve_failed_seat_visibility():
    results = [
        {
            "seat": "chatgpt",
            "ok": True,
            "response": "建议保守预测法国进入四强，但冠军需要等待赛程和伤病信息。",
        },
        {
            "seat": "gemini",
            "ok": False,
            "supplementable": True,
            "error": {"code": "slow_response_pending", "message": "No response captured."},
        },
    ]

    claims = build_web_claims("预测2026世界杯", "flash", results)
    deliberation = build_web_deliberation("预测2026世界杯", "flash", results)

    assert any("慢生成待回收" in claim["claim"] for claim in claims)
    assert deliberation["peer_review_count"] == 0
    assert deliberation["summary_claim_count"] == 1


def test_resonance_followup_prompt_uses_model_questions():
    raw_results = [
        {
            "seat": "chatgpt",
            "seat_name": "ChatGPT",
            "ok": True,
            "response": "初轮方案。共振提问：\n1. 如何定义验收标准？\n2. 哪些接口需要回滚？\n3. 外部证据如何隔离？",
        }
    ]

    prompts = build_resonance_followup_prompts("升级 AI Judge", raw_results)

    assert len(prompts) == 1
    assert prompts[0]["seat"] == "chatgpt"
    assert "如何定义验收标准？" in prompts[0]["questions"]
    assert "[AIJUDGE_RESONANCE_FOLLOWUP]" in prompts[0]["prompt"]
    assert "带入用户角色" in prompts[0]["prompt"]


def test_run_web_jury_collects_second_round_resonance_answers(monkeypatch):
    calls = []

    def fake_run_web_seats(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "response": "初轮方案。共振提问：\n1. 如何定义验收标准？\n2. 哪些接口要改？",
                }
            ]
        return [
            {
                "seat": "chatgpt",
                "seat_name": "ChatGPT",
                "ok": True,
                "elapsed_seconds": 3.2,
                "response": "二轮方案：带入用户角色后，先补齐状态字段、接口和验收测试。",
            }
        ]

    monkeypatch.setattr("core.web_jury.run_web_seats", fake_run_web_seats)

    verdict = run_web_jury(
        question="修复二次共振互动",
        mode="flash",
        seats=["chatgpt"],
        run_id="run-followup-test",
        collect_followups=True,
    )

    supplements = verdict["web_bridge"]["mentor_supplements"]
    assert len(calls) == 2
    assert calls[1]["seats"] == ["chatgpt"]
    assert "[AIJUDGE_RESONANCE_FOLLOWUP]" in calls[1]["question"]
    assert "带入用户角色" in calls[1]["question"]
    assert supplements[0]["ok"] is True
    assert supplements[0]["source_questions"] == ["如何定义验收标准？", "哪些接口要改？"]
    assert "状态字段、接口和验收测试" in supplements[0]["response"]


def test_slow_pending_seats_do_not_turn_partial_run_into_bridge_failure():
    results = [
        {"seat": "chatgpt", "ok": True, "response": "ok"},
        {
            "seat": "qwen",
            "ok": False,
            "supplementable": True,
            "error": {"code": "slow_response_pending", "message": "still thinking"},
        },
    ]

    assert not _bridge_collection_insufficient(results, ok_count=1, failed_count=1, total=2)


def test_score_rounds_and_judge_baseline_are_visible_artifacts():
    raw_results = [
        {
            "seat": "chatgpt",
            "seat_name": "ChatGPT",
            "ok": True,
            "response": "支持。依据是2026年赛程、阵容深度和历史表现，但需要验证伤病风险。",
        },
        {
            "seat": "qwen",
            "seat_name": "Qwen",
            "ok": True,
            "response": "条件支持。需要核查分组、赛程和主力状态，再给最终判断。",
        },
    ]
    primary = build_web_claims("预测2026世界杯", "flash", raw_results)
    deliberation = build_web_deliberation("预测2026世界杯", "flash", raw_results)
    mentor_claims = build_mentor_supplement_claims("预测2026世界杯", "flash", [
        {
            "seat": "chatgpt",
            "seat_name": "ChatGPT",
            "ok": True,
            "response": "二轮补充：如果我是用户，会先定义验收标准、数据流和回滚方案。",
            "source_questions": ["如何验收？", "如何回滚？"],
        }
    ])
    scored_claims = []
    for claim in primary + mentor_claims + deliberation["claims"]:
        item = dict(claim)
        item["_score"] = 0.61
        item["_tier"] = "conditional"
        scored_claims.append(item)

    rounds = build_score_rounds(scored_claims)
    digest = build_seat_answer_digest(raw_results, deliberation, [
        {"seat": "chatgpt", "seat_name": "ChatGPT", "average_score": 0.63, "claims_count": 3},
        {"seat": "qwen", "seat_name": "Qwen", "average_score": 0.59, "claims_count": 3},
    ])
    verdict = {
        "verdict_label": "建议推进但需验证",
        "average_score": 0.61,
        "seat_scores": [],
        "claims": scored_claims,
    }
    judge = build_judge_answer("预测2026世界杯", verdict, raw_results, deliberation, digest)
    baseline = build_single_judge_baseline("预测2026世界杯", judge, deliberation, raw_results, verdict)

    assert [item["id"] for item in rounds] == ["raw_answer", "mentor_supplement", "answer_summary", "peer_review"]
    assert rounds[0]["average_score"] == 0.61
    assert rounds[1]["claim_count"] == 1
    assert digest[0]["pros"]
    assert "AI Judge 法官答案" in judge["answer"]
    assert baseline["score"] >= 0
    assert baseline["comparison"][1]["metric"] == "互评校验"
