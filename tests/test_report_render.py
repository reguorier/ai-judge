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
    assert 'data-lang-button="en"' in rendered
    assert 'data-print-report' in rendered
    assert 'data-copy-link' in rendered
    assert "Download PDF" in rendered
    assert "Copy Share Link" in rendered
    assert "setReportLanguage" in rendered
    assert "window.print()" in rendered
    assert 'id="seat-answers"' in rendered
    assert "未拿全" in rendered
    assert full_answer in rendered
    assert "send_button_not_found" in rendered
    assert "AI Judge 法官答案与单模型对照" in rendered
    assert "每轮评分表现" in rendered
    assert "内部资料库：每个模型的回答索引" in rendered
    assert "答案总结、互评与评分链路" in rendered
    assert "score_jury_v2" in rendered
    assert 'class="seat-answer is-ok"' in rendered
    assert 'class="seat-answer is-failed" id="seat-answer-gemini" open' in rendered
    assert "全部展开" in rendered


def test_report_renders_readable_stored_answers_and_archive_index():
    api_server = _load_api_server()
    rendered = api_server._render_html_report({
        "question": "检查内部资料库是否能看完整结果。",
        "one_liner": "原始答案、互评、共振和依据都应可追溯。",
        "verdict_label": "建议推进",
        "confidence": 88,
        "web_bridge": {
            "ok_count": 1,
            "failed_count": 0,
            "requested_count": 1,
            "collection_complete": True,
            "raw_results": [
                {
                    "seat": "doubao",
                    "seat_name": "Doubao",
                    "ok": True,
                    "response": (
                        r"\u6700\u7ec8\u65b9\u6848\uff1a\u4fdd\u7559\u5b8c\u6574\u539f\u6587\n"
                        "| 路径 | 动作 |\n"
                        "|---|---|\n"
                        "| GitHub | 发布 README |\n"
                        "参考 https://example.com/report"
                    ),
                }
            ],
            "deliberation": {
                "peer_review_count": 1,
                "summary_claim_count": 1,
                "claim_count": 1,
                "peer_reviews": [
                    {"reviewer": "doubao", "reviewer_name": "Doubao", "target": "doubao", "target_name": "Doubao", "score": 0.8, "label": "支持", "comment": "路径可执行。"}
                ],
                "answer_summaries": [
                    {"seat": "doubao", "seat_name": "Doubao", "stance": "支持", "quality": 0.8, "summary": "保留完整原文。"}
                ],
            },
            "mentor_supplements": [
                {
                    "seat": "doubao",
                    "seat_name": "Doubao",
                    "ok": True,
                    "source_questions": ["如何追溯原始日志？"],
                    "response": "二轮补充：打开内部资料库。",
                }
            ],
        },
    })

    readable_part = rendered.split('id="raw-json"', 1)[0]
    assert "最终方案：保留完整原文" in rendered
    assert r"\u6700\u7ec8" not in readable_part
    assert 'class="answer readable-answer"' in rendered
    assert 'class="raw-log"' in rendered
    assert "stored-table" in rendered
    assert "查看纯文本原始日志" in rendered
    assert 'id="result-archive"' in rendered
    assert "完整结果资料库" in rendered
    assert 'href="#seat-answers"' in rendered
    assert 'href="#deliberation"' in rendered
    assert 'href="#mentor-supplements"' in rendered
    assert 'id="raw-json"' in rendered


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

    assert 'id="report-manuscript"' in rendered
    assert 'data-report-root="professional-manuscript"' in rendered
    assert 'class="paper-cover"' in rendered
    assert "AI JUDGE FINAL REPORT" in rendered
    assert "摘要 / ABSTRACT" in rendered
    assert "关键指标 / SCORECARD" in rendered
    assert "证据溯源 / EVIDENCE LEDGER" in rendered
    assert 'id="internal-library"' in rendered
    assert "color-scheme: light" in rendered
    assert "--paper:#fffdf8" in rendered
    assert "background:rgba(251,252,254,.96)" in rendered
    assert "研究报告" in rendered or "RESEARCH REPORT" in rendered
    assert "内部资料库" in rendered
    assert "席位覆盖 2/3" in rendered
    assert "最终方案" in rendered
    assert rendered.index('id="report-manuscript"') < rendered.index('id="internal-library"')
    assert 'class="council-card"' not in rendered


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

    report_body = rendered.split('id="internal-library"', 1)[0]
    abstract_start = report_body.index("摘要 / ABSTRACT")
    abstract_end = report_body.index("关键指标 / SCORECARD")
    abstract_html = report_body[abstract_start:abstract_end]
    assert "RAW_SHOULD_NOT_APPEAR" not in abstract_html
    assert "DeepSeek 轮值法官" in rendered
    assert "行动建议 / ACTION ITEMS" in rendered


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
    assert report["executive_summary"]["detail_anchor"] == "#report-manuscript"
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
    assert 'id="report-manuscript"' in rendered
    assert 'id="internal-library"' in rendered
    assert "Final Decision Manuscript" in rendered
    assert "摘要 / ABSTRACT" in rendered
    assert "争议裁决表" in rendered
    assert "模型贡献附录" in rendered
    assert rendered.index("摘要 / ABSTRACT") < rendered.index("模型贡献附录")


def test_final_report_keeps_title_and_plan_topic_aligned():
    api_server = _load_api_server()
    verdict = {
        "run_id": "topic-align-001",
        "question": "请整合 AI Judge 抖音和 TikTok 运营方案，目标是获得点赞、评论、关注和 GitHub stars。",
        "one_liner": "建议围绕 9 个 AI 同审一个判断做短视频增长闭环。",
        "verdict_label": "建议推进但需验证",
        "confidence": 84,
        "reasons": ["内容必须围绕短视频钩子、互动挑战和双语发布节奏。"],
        "next_steps": ["先确定首发选题和 9:16 视觉素材包。", "再排一周五条内容矩阵。"],
        "web_bridge": {
            "ok_count": 2,
            "failed_count": 0,
            "requested_count": 2,
            "collection_complete": True,
            "raw_results": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "response": (
                        "最终方案：首发视频用“我让 9 个 AI 同时审一个判断，结果它们互相否定”做冲突钩子。\n"
                        "执行路线图：T0 写中文抖音文案和 TikTok caption，T1 生成 9:16 图片 prompt，T2 发布复盘评论率。\n"
                    ),
                },
                {
                    "seat": "stale",
                    "seat_name": "Stale Model",
                    "ok": True,
                    "response": "最终方案：奇绩秋季营预计 8-9 月开，LinkedIn/X 英文 KOL 矩阵，Papers with Code 加速器。",
                },
            ],
        },
    }

    api_server.attach_final_report(verdict)
    report = verdict["final_report"]
    rendered = api_server._render_html_report(verdict)
    visible_report = rendered.split('id="internal-library"', 1)[0]
    brief_blob = " ".join(
        [report["decision_brief"]["title"], *[card["value"] for card in report["decision_brief"]["cards"]]]
    )

    assert "抖音/TikTok" in report["decision_brief"]["title"]
    assert "首发视频" in brief_blob or "9 个 AI" in brief_blob
    assert "奇绩秋季营" not in brief_blob
    assert "奇绩秋季营" not in visible_report


def test_commercial_growth_report_stays_aligned_when_bridge_is_blocked():
    api_server = _load_api_server()
    prompt = (
        "【任务：AI Judge 商业化/投稿/融资/GitHub 加星全量评审】\n"
        "请给能落地执行的商业化、投稿、融资、社媒和 GitHub star 增长方案，"
        "同时覆盖抖音/TikTok、Reddit、Show HN、Hugging Face Spaces 和投资人触达。"
    )
    verdict = {
        "run_id": "commercial-bridge-001",
        "question": prompt,
        "one_liner": "非 Grok 必需网页席位只拿到 8/9 个执行有效回答；这不是问题本身的判决。",
        "verdict_label": "必需席位执行未完成",
        "confidence": 0,
        "reasons": ["MiMo provider_quota_limited，Grok 可选。"],
        "next_steps": ["先恢复 MiMo，再做发布确认。"],
        "web_bridge": {
            "ok_count": 2,
            "failed_count": 1,
            "requested_count": 3,
            "collection_complete": False,
            "execution_policy": {
                "required_count": 3,
                "required_valid_count": 2,
                "required_failures": [
                    {"seat": "mimo", "seat_name": "MiMo", "error": {"code": "provider_quota_limited"}}
                ],
            },
            "raw_results": [
                {
                    "seat": "gemini",
                    "seat_name": "Gemini",
                    "ok": True,
                    "response": "最终方案：修复报告 UI，避免把必需席位执行未完成写进抖音/TikTok 运营方案。",
                },
                {
                    "seat": "qwen",
                    "seat_name": "Qwen",
                    "ok": True,
                    "response": (
                        "最终方案：聚焦 Agent 评测基建，以开源陪审团架构和合规审计 SaaS 为商业化主轴。"
                        "优先 GitHub README、Hugging Face Spaces、Show HN、Reddit 和 AI Evaluation Demo。"
                    ),
                },
            ],
        },
    }

    api_server.attach_final_report(verdict)
    report = verdict["final_report"]
    rendered = api_server._render_html_report(verdict)
    hero = rendered.split('<details class="prompt-details"', 1)[0]
    visible_draft = rendered.split('id="internal-library"', 1)[0]
    brief_blob = " ".join(
        [report["decision_brief"]["title"], report["decision_brief"]["one_sentence"], *[card["value"] for card in report["decision_brief"]["cards"]]]
    )

    assert report["decision_brief"]["title"] == "AI Judge 商业化 / 投稿 / 融资 / GitHub 加星收口报告"
    assert "抖音/TikTok 内容增长" not in report["decision_brief"]["title"]
    assert "开源可信基础设施" in brief_blob
    assert "必需席位执行未完成" not in report["decision_brief"]["title"]
    assert "请给能落地执行" not in hero
    assert "商业化 / 投稿 / 融资 / GitHub 加星收口报告" in hero
    assert "Final Decision Manuscript" in visible_draft
    assert "GitHub" in visible_draft
    assert "Hugging Face" in visible_draft or "HF" in visible_draft


def test_product_flow_report_stays_aligned_when_bridge_is_blocked():
    api_server = _load_api_server()
    verdict = {
        "run_id": "product-flow-bridge-001",
        "question": (
            "【任务：AI Judge 网页版产品流程全量评审】检查主要流程、跑任务、拿报告收口、"
            "下载、转发、一键切换语言和最终报告展示。"
        ),
        "one_liner": "非 Grok 必需网页席位只拿到 10/12 个执行有效回答；这不是问题本身的判决。",
        "verdict_label": "必需席位执行未完成",
        "confidence": 0,
        "reasons": ["ChatGPT 未匹配当前问题，DeepSeek 未找到旧页面答案。"],
        "next_steps": ["先恢复 ChatGPT 和 DeepSeek，再做发布确认。"],
        "web_bridge": {
            "ok_count": 10,
            "failed_count": 2,
            "requested_count": 12,
            "collection_complete": False,
            "execution_policy": {
                "required_count": 12,
                "required_valid_count": 10,
                "required_failures": [
                    {"seat": "chatgpt", "seat_name": "ChatGPT", "error": {"code": "response_not_relevant"}},
                    {"seat": "deepseek", "seat_name": "DeepSeek", "error": {"code": "existing_answer_not_found"}},
                ],
            },
            "raw_results": [
                {
                    "seat": "mimo",
                    "seat_name": "MiMo",
                    "ok": True,
                    "response": "最终方案：报告做成单页成稿，首屏放结论、方案、计划、风险，底部放模型附录。",
                },
                {
                    "seat": "qwen",
                    "seat_name": "Qwen",
                    "ok": True,
                    "response": "最终方案：新增下载、分享、中英切换，并把桥接恢复放到运行健康门禁。",
                },
            ],
        },
    }

    api_server.attach_final_report(verdict)
    report = verdict["final_report"]
    brief = report["decision_brief"]
    brief_blob = " ".join([brief["title"], brief["one_sentence"], *[card["value"] for card in brief["cards"]]])

    assert report["compact_overview"]["schema"] == "ai_judge.compact_report_overview.v1"
    assert report["compact_overview"]["title"] == "AI Judge 产品流程与报告收口方案"
    assert report["compact_overview"]["jump_pages"][0]["label"] == "全量路径汇总"
    assert report["compact_overview"]["jump_pages"][2]["label"] == "全部议员草稿"
    assert report["compact_overview"]["council_index"][0]["draft_href"] == "#seat-answer-mimo"
    assert report["title"] == "AI Judge 最终行动方案：报告页重点与执行计划"
    assert brief["title"] == "AI Judge 产品流程与报告收口方案"
    assert "单页可读的最终报告工作台" in brief["one_sentence"]
    assert "直接看、下载和转发" in brief_blob
    assert "ChatGPT" in brief_blob and "DeepSeek" in brief_blob
    assert "必需席位执行未完成" not in brief["title"]


def test_compact_report_uses_internal_logs_instead_of_external_model_pages():
    api_server = _load_api_server()
    verdict = {
        "question": "针对 AI Judge 给出商业化、投稿、融资、GitHub 加星的落地计划。",
        "verdict_label": "建议推进",
        "confidence": 82,
        "web_bridge": {
            "ok_count": 1,
            "failed_count": 0,
            "requested_count": 1,
            "collection_complete": True,
            "raw_results": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "url": "https://chatgpt.com/c/external-login-page",
                    "response": "GitHub README + Demo 是第一路径，72 小时内发布 Show HN。",
                }
            ],
        },
    }

    api_server.attach_final_report(verdict)
    row = verdict["final_report"]["compact_overview"]["council_index"][0]
    rendered = api_server._render_html_report(verdict)
    compact_html = rendered.split('id="seat-answers"', 1)[0]

    assert row["raw_href"] == "#seat-answer-chatgpt"
    assert row["stored_log_href"] == "#seat-answer-chatgpt"
    assert row["external_url"] == "https://chatgpt.com/c/external-login-page"
    assert "https://chatgpt.com/c/external-login-page" not in compact_html
    assert "内部日志" in compact_html
    assert "内部资料库：席位完整原始日志" in rendered


def test_commercial_report_synthesizes_full_action_paths_from_model_drafts():
    api_server = _load_api_server()
    verdict = {
        "question": "针对 AI Judge 项目给出商业化方向、投稿方向、参赛方向、融资方向和 GitHub 加星全量计划。",
        "verdict_label": "建议推进",
        "confidence": 88,
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
                    "response": "72 小时内重写 GitHub README 首屏，录制 Demo，并发布 Show HN / Reddit / LinkedIn 首轮帖子。",
                },
                {
                    "seat": "kimi",
                    "seat_name": "Kimi",
                    "ok": True,
                    "response": "投稿路径：Hugging Face 中文社区 https://hf.link/tougao；AI Engineer Workshop 截止 2026-05-30。",
                },
                {
                    "seat": "qwen",
                    "seat_name": "Qwen",
                    "ok": True,
                    "response": "商业化路径：企业试点先卖 SLA、私有化部署、CI 审计报告；融资优先联系 AI infra 投资人。",
                },
            ],
        },
    }

    api_server.attach_final_report(verdict)
    overview = verdict["final_report"]["compact_overview"]
    rendered = api_server._render_html_report(verdict)
    path_blob = " ".join(
        " ".join(str(row.get(key, "")) for key in ("path", "execution", "entry", "deadline", "evidence"))
        for row in overview["action_paths"]
    )

    assert len(overview["action_paths"]) >= 8
    assert "GitHub" in path_blob
    assert "Hugging Face" in path_blob
    assert "Show HN" in path_blob
    assert "企业试点" in path_blob
    assert "ChatGPT" in " ".join("、".join(row.get("source_models", [])) for row in overview["action_paths"])
    assert "全量可执行路径汇总" in rendered


def test_final_report_html_surfaces_decision_brief_before_longform_body():
    api_server = _load_api_server()
    verdict = {
        "question": "报告页方案和标题对不上，需要重新梳理重点和计划。",
        "one_liner": "先按结论、方案、计划、风险重排。",
        "verdict_label": "建议推进但需验证",
        "confidence": 88,
        "reasons": ["用户首屏看不到重点。"],
        "next_steps": ["先改完整报告首屏信息架构。", "再把模型贡献放进附录。"],
        "web_bridge": {"ok_count": 3, "failed_count": 0, "requested_count": 3, "collection_complete": True},
    }

    api_server.attach_final_report(verdict)
    rendered = api_server._render_html_report(verdict)

    assert 'id="report-manuscript"' in rendered
    assert "Final Decision Manuscript" in rendered
    assert "关键指标 / SCORECARD" in rendered
    assert "行动建议 / ACTION ITEMS" in rendered
    assert 'id="internal-library"' in rendered
    assert rendered.index('id="report-manuscript"') < rendered.index('id="internal-library"')
    assert rendered.index("摘要 / ABSTRACT") < rendered.index("行动建议 / ACTION ITEMS")


def test_incomplete_final_report_surfaces_run_health_gate_before_draft():
    api_server = _load_api_server()
    verdict = {
        "run_id": "bridge-blocked-001",
        "question": "当前完整报告看不懂，需要全量 AI Judge 评审报告展示，并排查桥接问题。",
        "one_liner": "运行未闭环，不能把草稿包装成最终报告。",
        "verdict_label": "不可发布",
        "confidence": 0,
        "reasons": ["DeepSeek 未确认专家模式，Qwen 未返回可用正文。"],
        "next_steps": ["先恢复 DeepSeek 专家模式与 Qwen 深入思考回收。"],
        "web_bridge": {
            "ok_count": 1,
            "failed_count": 2,
            "requested_count": 3,
            "collection_complete": False,
            "execution_policy": {
                "required_count": 3,
                "required_valid_count": 1,
                "required_failed_count": 2,
                "required_rule": "all_requested_non_grok_seats_must_have_valid_execution",
                "collection_complete": False,
                "required_failures": [
                    {
                        "seat": "deepseek",
                        "seat_name": "DeepSeek",
                        "error": {"code": "expert_mode_not_confirmed", "message": "未确认专家模式，拒绝提交"},
                        "supplementable": True,
                    },
                    {
                        "seat": "qwen",
                        "seat_name": "Qwen",
                        "error": {"code": "slow_response_pending", "message": "未读到可用回答"},
                        "supplementable": True,
                    },
                ],
            },
            "rescue_plan": {
                "button_label": "一键修复并回收答案",
                "actions": [
                    {
                        "seat": "deepseek",
                        "seat_name": "DeepSeek",
                        "code": "expert_mode_not_confirmed",
                        "label": "修复专家模式并重试",
                    },
                    {
                        "seat": "qwen",
                        "seat_name": "Qwen",
                        "code": "slow_response_pending",
                        "label": "读取旧页面答案",
                    },
                ],
            },
            "raw_results": [
                {"seat": "kimi", "seat_name": "Kimi", "ok": True, "response": "首屏先放运行健康、结论、下一步。"},
                {"seat": "deepseek", "seat_name": "DeepSeek", "ok": False, "error": {"code": "expert_mode_not_confirmed"}},
                {"seat": "qwen", "seat_name": "Qwen", "ok": False, "error": {"code": "slow_response_pending"}},
            ],
        },
    }

    api_server.attach_final_report(verdict)
    report = verdict["final_report"]
    rendered = api_server._render_html_report(verdict)

    assert report["report_mode"] == "bridge_recovery_required"
    assert report["status_label"] == "运行未闭环"
    assert report["executive_summary"]["detail_anchor"] == "#run-health"
    assert "运行健康门禁" in rendered
    assert "运行未闭环：必需席位覆盖只有 1/3" in rendered
    assert "不生成业务最终结论" in rendered
    assert "阶段性文稿 · 等待桥接闭环" in rendered
    assert "内部资料库" in rendered
    assert "DeepSeek" in rendered and "expert_mode_not_confirmed" in rendered
    assert rendered.index("运行健康门禁") < rendered.index('id="report-manuscript"')


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
