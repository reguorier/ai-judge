from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_api_server():
    module_path = Path(__file__).resolve().parents[1] / "product" / "api_server.py"
    spec = importlib.util.spec_from_file_location("api_server_report_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_report_keeps_navigation_and_full_web_answers():
    api_server = _load_api_server()
    full_answer = "完整席位回答：" + ("A" * 1200)

    rendered = api_server._render_html_report({
        "question": "测试网页桥接是否拿全",
        "one_liner": "网页桥接只拿到 1/2 个席位完整回答",
        "verdict_label": "需要重跑",
        "confidence": 0,
        "reasons": ["Gemini 未完成，不能把局部结果当最终判词。"],
        "next_steps": ["修复失败 adapter 后重跑。"],
        "judge_answer": {
            "answer": "AI Judge 法官答案：当前只拿到部分席位，因此这是阶段性判断。",
            "ok_count": 1,
            "failed_count": 1,
            "dominant_stance": "支持/推进",
            "agreements": ["测试"],
            "limits": ["1/2 个席位未返回完整答案。"],
        },
        "single_judge_baseline": {
            "score": 0.57,
            "tier": "conditional",
            "council_average_score": 0.82,
            "delta_vs_council": 0.25,
            "comparison": [
                {"metric": "答案来源", "single_judge": "法官汇总后的单一答案", "council": "1/2 个网页席位原始答案"},
                {"metric": "互评校验", "single_judge": "无模型间互评", "council": "0 条席位互评"},
            ],
        },
        "web_bridge": {
            "ok_count": 1,
            "failed_count": 1,
            "requested_count": 2,
            "collection_complete": False,
            "score_rounds": [
                {
                    "id": "raw_answer",
                    "label": "第一轮：网页原始回答评分",
                    "claim_count": 2,
                    "average_score": 0.42,
                    "seat_scores": [{"seat": "grok", "seat_name": "Grok", "average_score": 0.82}],
                    "top_claims": [{"seat_name": "Grok", "score": 0.82, "tier": "credible", "claim": "Grok 原始回答"}],
                },
                {
                    "id": "answer_summary",
                    "label": "第二轮：答案总结评分",
                    "claim_count": 1,
                    "average_score": 0.72,
                    "seat_scores": [{"seat": "grok", "seat_name": "Grok", "average_score": 0.72}],
                    "top_claims": [],
                },
            ],
            "seat_answer_digest": [
                {
                    "seat": "grok",
                    "seat_name": "Grok",
                    "status": "已返回",
                    "score": 0.82,
                    "stance": "支持/推进",
                    "pros": ["互评认可度高"],
                    "cons": ["仍需核查事实"],
                    "answer_preview": full_answer,
                },
                {
                    "seat": "gemini",
                    "seat_name": "Gemini",
                    "status": "未完成",
                    "score": 0.1,
                    "stance": "未返回",
                    "pros": ["失败原因被保留"],
                    "cons": ["send_button_not_found"],
                    "answer_preview": "发送按钮未找到",
                },
            ],
            "pipeline": {
                "scoring_engine": "core.scoring_v2.score_jury_v2",
                "phases": [
                    {"label": "网页席位收集", "count": 2},
                    {"label": "答案总结", "count": 1},
                    {"label": "席位互评", "count": 0},
                    {"label": "评分引擎 v2", "count": 2},
                ],
            },
            "deliberation": {
                "ok_count": 1,
                "failed_count": 1,
                "stance_distribution": {"支持/推进": 1},
                "agreements": ["测试"],
                "disagreements": ["席位立场整体同向，主要差异在证据密度和风险提示。"],
                "summary_claim_count": 1,
                "peer_review_count": 0,
                "claim_count": 1,
                "answer_summaries": [
                    {
                        "seat": "grok",
                        "seat_name": "Grok",
                        "stance": "支持/推进",
                        "quality": 0.72,
                        "avg_peer_score": None,
                        "review_count": 0,
                        "summary": full_answer,
                    }
                ],
                "peer_reviews": [],
            },
            "raw_results": [
                {
                    "seat": "grok",
                    "seat_name": "Grok",
                    "ok": True,
                    "response": full_answer,
                    "elapsed_seconds": 4.2,
                },
                {
                    "seat": "gemini",
                    "seat_name": "Gemini",
                    "ok": False,
                    "error": {
                        "code": "send_button_not_found",
                        "message": "发送按钮未找到",
                    },
                },
            ],
        },
        "seat_scores": [
            {
                "seat": "grok",
                "seat_name": "Grok",
                "mbti": "INTJ",
                "average_score": 0.82,
                "claims_count": 2,
            },
        ],
    })

    assert "返回提问" in rendered
    assert 'id="seat-answers"' in rendered
    assert "未拿全" in rendered
    assert full_answer in rendered
    assert "send_button_not_found" in rendered
    assert "AI Judge 法官答案与单模型对照" in rendered
    assert "每轮评分表现" in rendered
    assert "每个模型的回答入口、优缺点" in rendered
    assert "答案总结、互评与评分链路" in rendered
    assert "score_jury_v2" in rendered
    assert 'class="seat-answer is-ok"' in rendered
    assert 'class="seat-answer is-failed" id="seat-answer-gemini" open' in rendered
    assert "全部展开" in rendered


def test_report_renders_cross_temporal_closeout():
    api_server = _load_api_server()
    rendered = api_server._render_html_report({
        "question": "横纵分析是否能进入报告",
        "one_liner": "条件支持，但需要补齐旧页面答案。",
        "verdict_label": "条件支持",
        "confidence": 78,
        "average_score": 0.71,
        "reasons": ["网页席位未全量回收。"],
        "next_steps": ["先回收旧页面答案。"],
        "cross_temporal_analysis": {
            "schema": "cross_temporal_analysis.v1",
            "method": "纵向追时间深度，横向追同期广度，交叉后形成可执行判断。",
            "closeout_report": {
                "decision_score": "78/100 · 均分 0.710",
                "trust_tier": {"tier": "C", "label": "C · 阶段性判断", "summary": "仍需补齐旧页面答案。"},
                "executive_summary": "最终判决：条件支持。席位覆盖 2/3，MiniMax 待回收。",
            },
            "trust_tier": {"tier": "C", "label": "C · 阶段性判断", "summary": "仍需补齐旧页面答案。"},
            "vertical_trace": {
                "bridge_health": "网页桥接部分完成",
                "key_turn": "网页席位未全量回收，结论必须带条件",
                "timeline": [{"phase": "collect", "detail": "等待 MiniMax"}],
            },
            "horizontal_comparison": {
                "ok_count": 2,
                "requested_count": 3,
                "consensus_label": "席位不完整",
                "comparison_note": "只回收到 2/3 席，当前判断不能包装成全模型共识。",
                "seat_ranking": [{"seat_name": "ChatGPT", "score": 0.82, "status": "已返回", "claims_count": 4}],
            },
            "math_audit": {
                "signals": [
                    {
                        "label": "容斥式席位覆盖",
                        "severity": "block",
                        "value": 0.667,
                        "summary": "2/3 席形成有效答案。",
                        "next_action": "先补齐可回收席位。",
                    }
                ]
            },
            "recommended_actions": ["先执行旧页面只读回收。"],
        },
    })

    assert 'id="cross-temporal"' in rendered
    assert "横纵分析收口报告" in rendered
    assert "最终判决：条件支持" in rendered
    assert "C · 阶段性判断" in rendered
    assert "容斥式席位覆盖" in rendered


def test_report_renders_mentor_resonance_supplements():
    api_server = _load_api_server()
    rendered = api_server._render_html_report({
        "question": "升级 AI Judge",
        "one_liner": "阶段性方案。",
        "verdict_label": "条件支持",
        "confidence": 78,
        "web_bridge": {
            "mentor_supplements": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "elapsed_seconds": 12.5,
                    "source_questions": ["如何定义验收标准？", "哪些接口要改？"],
                    "response": "二轮方案：新增 mentor_supplements，并把原文、补充、外部证据隔离。",
                }
            ],
        },
    })

    assert 'id="mentor-supplements"' in rendered
    assert "共振提问与二轮方案" in rendered
    assert "如何定义验收标准？" in rendered
    assert "新增 mentor_supplements" in rendered


def test_report_renders_citation_verification_mvp():
    api_server = _load_api_server()
    rendered = api_server._render_html_report({
        "question": "升级 AI Judge",
        "one_liner": "引用验证 MVP 已生成。",
        "verdict_label": "条件支持",
        "confidence": 82,
        "grand_judge": {
            "certification_id": "CITE-20260516-ABCDEF1234",
            "replay_ledger_hash": "hash-1234567890",
            "citation_verification": {
                "certification_id": "CITE-20260516-ABCDEF1234",
                "overall_status": "unverifiable",
                "item_count": 1,
                "counts": {"verified": 0, "weakly_verified": 0, "irrelevant": 0, "unverifiable": 1, "contradicted": 0},
                "replay_ledger_hash": "hash-1234567890",
                "external_evidence_count": 0,
                "unverifiable_explanation": "unverifiable 不是 false。",
            },
            "replay_ledger": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "raw_answer": "参考 https://missing.example/source",
                    "mentor_supplement": "导师补充",
                    "citation_verification": {
                        "items": [
                            {
                                "citation_id": "CITE-001",
                                "raw": "https://missing.example/source",
                                "status": "unverifiable",
                                "reason": "未在隔离的外部证据层找到可匹配来源。",
                                "relevance_score": 0,
                            }
                        ]
                    },
                }
            ],
            "evidence_gap_suggestions": {
                "suggestions": [
                    {
                        "citation_id": "CITE-001",
                        "mentor_level": "L1",
                        "status": "unverifiable",
                        "suggested_action": "补充可复核 URL/DOI/报告页码。",
                    }
                ]
            },
        },
    })

    assert 'id="citation-verification"' in rendered
    assert "CITE-20260516-ABCDEF1234" in rendered
    assert "unverifiable 不是 false" in rendered
    assert "Replay Ledger" in rendered
    assert "https://missing.example/source" in rendered


def test_report_renders_evidence_os_section():
    api_server = _load_api_server()
    rendered = api_server._render_html_report({
        "question": "升级 AI Judge",
        "one_liner": "Evidence OS 已生成。",
        "verdict_label": "条件支持",
        "confidence": 82,
        "grand_judge": {
            "citation_verification": {"overall_status": "unverifiable", "item_count": 1, "external_evidence_count": 0, "counts": {"unverifiable": 1}},
            "evidence_broker": {
                "counts": {"user_supplied": 0, "network_fetch": 0, "candidate_source": 1},
                "items": [{"id": "CAND-1", "source_layer": "candidate_source", "retrieval_state": "not_fetched", "url": "https://example.com"}],
            },
            "evidence_quality_metrics": {"groundedness_proxy": 0.0, "trust_gate": "needs_external_evidence"},
            "blind_cross_validation": {"status": "pending_model_reviews"},
            "evidence_gap_queue": {
                "open_count": 1,
                "tasks": [{"task_id": "GAP-001", "priority": "high", "queue_status": "open", "suggested_action": "补充来源"}],
            },
            "human_review_status": {"status": "required"},
            "eval_case": {"case_id": "EVAL-123"},
        },
    })

    assert 'id="evidence-os"' in rendered
    assert "Evidence OS" in rendered
    assert "needs_external_evidence" in rendered
    assert "EVAL-123" in rendered
    assert "GAP-001" in rendered
