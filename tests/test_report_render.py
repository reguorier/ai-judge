from __future__ import annotations

import importlib.util
from pathlib import Path

from core.final_report import render_final_report_markdown


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


def test_report_renders_paper_style_final_report():
    api_server = _load_api_server()
    rendered = api_server._render_html_report({
        "run_id": "paper-run-001",
        "question": "如何把 AI Judge 的法官答案变成最终方案？",
        "one_liner": "支持推进，但要把答案写成可审计报告。",
        "verdict_label": "支持/推进",
        "confidence": 81,
        "reasons": ["多席位都要求输出结论、证据链、执行方案和风险边界。"],
        "next_steps": ["先生成标准报告结构。", "再把客户端和 HTML 报告接到同一结构。"],
        "judge_answer": {
            "label": "AI Judge 法官综合答案",
            "answer": "旧版只有一句总结。",
            "ok_count": 2,
            "failed_count": 1,
            "dominant_stance": "支持/推进",
            "top_seats": ["ChatGPT", "DeepSeek"],
            "agreements": ["报告必须可读", "证据必须可追溯"],
            "limits": ["仍有一个席位待回收。"],
        },
        "single_judge_baseline": {
            "label": "DeepSeek 单模型对照",
            "score": 0.66,
            "council_average_score": 0.71,
            "delta_vs_council": -0.05,
        },
        "web_bridge": {
            "ok_count": 2,
            "failed_count": 1,
            "requested_count": 3,
            "collection_complete": False,
            "required_ok_count": 2,
            "required_count": 3,
            "raw_results": [
                {"seat": "chatgpt", "seat_name": "ChatGPT", "ok": True, "response": "要给最终方案。"},
                {"seat": "deepseek", "seat_name": "DeepSeek", "ok": True, "response": "要像报告。"},
                {"seat": "wenxin", "seat_name": "Wenxin", "ok": False, "error": {"code": "response_timeout"}},
            ],
        },
        "seat_scores": [
            {"seat": "chatgpt", "seat_name": "ChatGPT", "mbti": "ENTP", "average_score": 0.72, "claims_count": 3},
            {"seat": "deepseek", "seat_name": "DeepSeek", "mbti": "INTJ", "average_score": 0.70, "claims_count": 3},
        ],
    })

    assert 'id="final-report"' in rendered
    assert "AI Judge 轮值法官最终报告" in rendered
    assert "FINAL VERDICT · HUMAN SUMMARY" in rendered
    assert "STANDARD CLOSEOUT SOP" in rendered
    assert "Codex 执行模板" in rendered
    assert "Phase 1: 收口体验基线" in rendered
    assert "输出要求" in rendered
    assert "source exists" in rendered
    assert "查看完整总结报告" in rendered
    assert "审计附录：标准 SOP" in rendered
    assert "审计附录：旧版法官报告" in rendered
    assert 'id="professional-report"' in rendered
    assert "ABSTRACT" in rendered
    assert "THESIS" in rendered
    assert "RECOMMENDATION" in rendered
    assert "KEY FINDINGS" in rendered
    assert "POSTULATE 1" in rendered
    assert "EVIDENCE MAP" in rendered
    assert "EXECUTION PLAN" in rendered
    assert "VERIFICATION CONTRACT" in rendered
    assert "席位覆盖 2/3" in rendered
    assert "最终方案" in rendered


def test_final_report_does_not_dump_raw_closeout_into_abstract():
    api_server = _load_api_server()
    raw_dump = "RAW_SHOULD_NOT_APPEAR " + ("ChatGPT: 很长的席位原文；" * 40)
    rendered = api_server._render_html_report({
        "run_id": "paper-clean-001",
        "question": "商业化路线怎么收口？",
        "one_liner": "建议先做研究型开源工具，再验证商业包装。",
        "verdict_label": "建议推进但需验证",
        "confidence": 81,
        "chief_judge": {"id": "deepseek", "name": "DeepSeek", "label": "DeepSeek 轮值主审", "mbti": "INTJ", "strength": "工程拆解"},
        "reasons": [raw_dump],
        "next_steps": ["先验证 GitHub 可跑通 demo 和可传播 README。"],
        "cross_temporal_analysis": {
            "trust_tier": {"tier": "B", "label": "B · 可内部参考"},
            "closeout_report": {"professional_report": raw_dump, "executive_summary": raw_dump},
        },
        "web_bridge": {
            "ok_count": 12,
            "failed_count": 0,
            "requested_count": 12,
            "collection_complete": True,
        },
    })

    abstract_start = rendered.index("ABSTRACT")
    abstract_end = rendered.index("FINAL POSITION")
    abstract_html = rendered[abstract_start:abstract_end]
    assert "RAW_SHOULD_NOT_APPEAR" not in abstract_html
    assert "DeepSeek 轮值法官" in rendered
    assert "RECOMMENDATION" in rendered


def test_final_report_executive_summary_filters_generic_model_steps():
    api_server = _load_api_server()
    verdict = {
        "question": "报告页摘要不够人话，需要改成一眼结论和专业报告两层。",
        "one_liner": "建议推进但需验证。",
        "verdict_label": "建议推进但需验证",
        "confidence": 86,
        "reasons": ["ChatGPT: 当前页堆叠太多模型材料，用户看不出最终建议。"],
        "next_steps": [
            "Treat the result as usable direction, not final authorization.",
            "Validate the top risk before committing money, reputation, or irreversible effort.",
        ],
        "web_bridge": {"ok_count": 13, "failed_count": 0, "requested_count": 13, "collection_complete": True},
    }
    api_server.attach_final_report(verdict)
    report = verdict["final_report"]

    assert report["executive_summary"]["headline"].startswith("建议推进但需验证")
    assert "Treat the result" not in report["executive_summary"]["recommendation"]
    assert "一眼结论" not in report["executive_summary"]["headline"]
    assert report["executive_summary"]["detail_anchor"] == "#compiled-report"
    assert report["sop_closeout"]["schema"] == "ai_judge.closeout_sop.v1"
    assert report["sop_closeout"]["codex_template"]["label"] == "Codex 执行模板"
    assert report["sop_closeout"]["phases"][0]["title"] == "Phase 1: 收口体验基线"
    assert "输出要求" in render_final_report_markdown(report)
    assert report["key_findings"][0] == "当前页的职责是帮助用户快速决策，不应承载完整证据堆栈。"


def test_final_report_compiles_model_answers_into_integrated_report():
    api_server = _load_api_server()
    verdict = {
        "run_id": "compiler-run-001",
        "question": "请整合 AI Judge 抖音和 TikTok 运营方案，给出最终落地报告。",
        "one_liner": "建议把短视频运营做成争议选题、视觉钩子、互动挑战和双语发布节奏的完整闭环。",
        "verdict_label": "建议推进但需验证",
        "confidence": 86,
        "reasons": ["多席位都认为要从模型原始答案收口成可执行报告，而不是展示散乱回答。"],
        "next_steps": ["先固定完整报告模板。", "再把每个模型贡献放入附录。"],
        "judge_answer": {
            "label": "AI Judge 法官综合答案",
            "top_seats": ["ChatGPT", "DeepSeek", "Qwen"],
            "agreements": ["需要总纲", "需要争议裁决", "需要路线图"],
            "disagreements": ["是否先做短视频模板还是先做内容数据库。"],
            "limits": ["热点选题需要人工复核。"],
        },
        "web_bridge": {
            "ok_count": 3,
            "failed_count": 0,
            "requested_count": 3,
            "collection_complete": True,
            "raw_results": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "response": (
                        "核心判断：AI Judge 需要先给总纲，再输出完整报告。\n"
                        "最终方案：建立内容矩阵、图片 prompt、中文文案、英文 caption 和话题标签。\n"
                        "执行路线图：第一周固定模板，第二周跑 5 条内容，第三周复盘互动率。\n"
                    ),
                },
                {
                    "seat": "deepseek",
                    "seat_name": "DeepSeek",
                    "ok": True,
                    "response": (
                        "风险：如果只堆模型回答，用户看不到最终裁定。\n"
                        "争议：短视频内容应该先追热点还是先建立长期栏目。\n"
                        "成功标准：每条内容必须能直接发布，并能追踪评论和完播率。\n"
                    ),
                },
                {
                    "seat": "qwen",
                    "seat_name": "Qwen",
                    "ok": True,
                    "response": (
                        "MVP：先做一页最终整合报告。\n"
                        "模块：问题重述、关键发现、最终方案、争议裁决表、路线图、风险与防护、模型贡献附录。\n"
                    ),
                },
            ],
            "deliberation": {
                "agreements": ["完整报告应该成为主交付物。"],
                "disagreements": ["是否优先做热点检索。"],
                "answer_summaries": [
                    {"seat": "chatgpt", "seat_name": "ChatGPT", "stance": "支持/推进", "quality": 0.88, "summary": "主张完整报告模板。"},
                    {"seat": "deepseek", "seat_name": "DeepSeek", "stance": "条件支持", "quality": 0.86, "summary": "强调风险和争议裁决。"},
                    {"seat": "qwen", "seat_name": "Qwen", "stance": "支持/推进", "quality": 0.84, "summary": "给出模块化 MVP。"},
                ],
            },
        },
        "seat_scores": [
            {"seat": "chatgpt", "seat_name": "ChatGPT", "average_score": 0.88, "claims_count": 3},
            {"seat": "deepseek", "seat_name": "DeepSeek", "average_score": 0.86, "claims_count": 3},
            {"seat": "qwen", "seat_name": "Qwen", "average_score": 0.84, "claims_count": 3},
        ],
    }
    api_server.attach_final_report(verdict)
    report = verdict["final_report"]
    markdown = render_final_report_markdown(report)
    rendered = api_server._render_html_report(verdict)

    assert report["compiled_report"]["schema"] == "ai_judge.compiled_report.v1"
    assert report["longform_report"]["schema"] == "ai_judge.longform_report.v1"
    assert report["longform_report"]["body_sections"][0]["paragraphs"]
    assert "完整总结报告" in markdown
    assert "争议裁决表" in markdown
    assert "执行路线图" in markdown
    assert "模型贡献附录" in markdown
    assert "ChatGPT" in markdown and "DeepSeek" in markdown and "Qwen" in markdown
    assert 'id="compiled-report"' in rendered
    assert "EDITORIAL SYNTHESIS · LONGFORM REPORT" in rendered
    assert "完整总结报告" in rendered
    assert "执行摘要" in rendered
    assert "争议裁决表" in rendered
    assert "模型贡献附录" in rendered
    assert rendered.index("执行摘要") < rendered.index("模型贡献附录")


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
