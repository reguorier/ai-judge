from bridges.chrome_fixed_tab_bridge import (
    _build_capture_js,
    _build_click_send_js,
    _build_clear_blocking_ui_js,
    _build_existing_answer_capture_js,
    _build_fresh_navigation_js,
    _build_prepare_submission_ui_js,
    _build_submission_check_js,
    _deepseek_prepare_verified,
    _doubao_prepare_verified,
    _page_state_needs_reload,
    _quality_mode_failure,
    _quality_mode_policy_snapshot,
    _quality_mode_prepare_verified,
    _quality_mode_required_mode,
    _response_matches_question,
    _readiness_can_recover,
    _should_send_final_answer_nudge,
    _seat_prompt,
)
from core.prompt_resonance import build_prompt_flow


def test_deepseek_prepare_enforces_expert_and_tool_modes():
    js = _build_prepare_submission_ui_js("AIJUDGE-deepseek-test")

    assert "deepseek_new_chat" in js
    assert "deepseek_专家模式" in js
    assert "deepseek_new_chat_once" in js
    assert "deepseek_expert_verified" in js
    assert "deepseek_tools_verified" in js
    assert "使用专家模式开始对话" in js
    assert "deepseek_${toolName}_on" in js
    assert "ds-toggle-button--selected" in js


def test_deepseek_prepare_requires_expert_and_tools_verified():
    assert _deepseek_prepare_verified({
        "clicked_names": ["deepseek_expert_verified:yes", "deepseek_tools_verified:yes"],
    })
    assert _deepseek_prepare_verified({
        "clicked_names": ["deepseek_expert_verified:no", "deepseek_tools_verified:no"],
        "followup": {"clicked_names": ["deepseek_expert_verified:yes", "deepseek_tools_verified:yes"]},
    })
    assert not _deepseek_prepare_verified({
        "clicked_names": ["deepseek_expert_verified:yes", "deepseek_tools_verified:no"],
    })


def test_doubao_prepare_enforces_expert_or_super_mode_before_submission():
    js = _build_prepare_submission_ui_js("AIJUDGE-doubao-test")

    assert "doubao_expert_clicked" in js
    assert "doubao_expert_verified:yes" in js
    assert "超能模式" in js
    assert "专家模式" in js
    assert "专业模式" in js
    assert "深度思考" in js
    assert "nearComposer" in js


def test_doubao_prepare_requires_expert_mode_verified():
    assert _doubao_prepare_verified({
        "clicked_names": ["doubao_expert_clicked:超能模式 Beta", "doubao_expert_verified:yes"],
    })
    assert _doubao_prepare_verified({
        "clicked_names": ["doubao_expert_verified:no"],
        "followup": {"clicked_names": ["doubao_expert_clicked:专家模式", "doubao_expert_verified:yes"]},
    })
    assert not _doubao_prepare_verified({
        "clicked_names": ["doubao_expert_verified:no"],
    })


def test_qwen_prepare_requires_deep_thinking_mode_for_bridge_output():
    js = _build_prepare_submission_ui_js("AIJUDGE-qwen-test")

    assert "qwen_model_verified:yes" in js
    assert "qwen_model_clicked" in js
    assert "qwen_deep_thinking_clicked" in js
    assert "qwen_thinking_menu_open" in js
    assert "qwen_deep_thinking_verified:yes" in js
    assert "Qwen3\\.7[-\\s]*Plus" in js
    assert "深入思考" in js
    assert "qwen_reliable_mode" not in js


def test_xunfei_prepare_requires_reasoning_mode_for_bridge_output():
    js = _build_prepare_submission_ui_js("AIJUDGE-xunfei-test")

    assert "xunfei_reasoning_clicked" in js
    assert "xunfei_reasoning_verified:yes" in js
    assert "xunfei_reasoning_verified:no" in js
    assert "推理模式" in js
    assert "xinghuo\\.xfyun\\.cn" in js


def test_prepare_enforces_high_quality_modes_for_required_bridge_seats():
    js = _build_prepare_submission_ui_js("AIJUDGE-quality-modes-test")

    assert "meta_thinking_clicked" in js
    assert "meta_thinking_verified:yes" in js
    assert "wenxin_deep_thinking_clicked" in js
    assert "wenxin_deep_thinking_verified:yes" in js
    assert "xunfei_reasoning_clicked" in js
    assert "xunfei_reasoning_verified:yes" in js
    assert "minimax_model_clicked" in js
    assert "minimax_model_verified:yes" in js
    assert "minimax_thinking_clicked" in js
    assert "minimax_thinking_verified:yes" in js
    assert "yuanbao_deep_thinking_clicked" in js
    assert "yuanbao_deep_thinking_verified:yes" in js
    assert "kimi_model_clicked" in js
    assert "kimi_model_verified:yes" in js
    assert "kimi_thinking_clicked" in js
    assert "kimi_thinking_verified:yes" in js
    assert "gemini_expanded_clicked" in js
    assert "gemini_expanded_verified:yes" in js
    assert "Pro 扩展" in js
    assert "深度思考" in js
    assert "Thinking" in js


def test_quality_mode_verifier_blocks_unverified_required_modes():
    positive = {
        "meta": ["meta_thinking_verified:yes"],
        "wenxin": ["wenxin_deep_thinking_verified:yes"],
        "minimax": ["minimax_model_verified:yes", "minimax_thinking_verified:yes"],
        "yuanbao": ["yuanbao_deep_thinking_verified:yes"],
        "kimi": ["kimi_model_verified:yes", "kimi_thinking_verified:yes"],
        "qwen": ["qwen_model_verified:yes", "qwen_deep_thinking_verified:yes"],
        "gemini": ["gemini_pro_verified:yes", "gemini_expanded_verified:yes"],
        "xunfei": ["xunfei_reasoning_verified:yes"],
        "deepseek": ["deepseek_expert_verified:yes", "deepseek_tools_verified:yes"],
        "doubao": ["doubao_expert_verified:yes"],
    }

    for seat, clicked_names in positive.items():
        assert _quality_mode_prepare_verified(seat, {"clicked_names": clicked_names})

    assert _quality_mode_prepare_verified("qwen", {
        "clicked_names": ["qwen_deep_thinking_verified:no"],
        "followup": {"clicked_names": ["qwen_model_verified:yes", "qwen_deep_thinking_verified:yes"]},
    })
    assert not _quality_mode_prepare_verified("qwen", {"clicked_names": ["qwen_deep_thinking_verified:no"]})
    assert not _quality_mode_prepare_verified("gemini", {"clicked_names": ["gemini_pro_verified:yes"]})
    assert _quality_mode_failure("kimi")[0] == "kimi_quality_mode_not_verified"


def test_quality_mode_policy_snapshot_pins_current_choices():
    policy = _quality_mode_policy_snapshot()

    assert policy["meta"]["required_mode"] == "思考"
    assert policy["wenxin"]["required_mode"] == "深度思考"
    assert policy["minimax"]["required_mode"] == "MiniMax-M3 + Thinking"
    assert policy["yuanbao"]["required_mode"] == "深度思考"
    assert policy["kimi"]["required_mode"] == "K2.6 思考"
    assert policy["qwen"]["required_mode"] == "Qwen3.7-Plus + 思考"
    assert policy["gemini"]["required_mode"] == "Pro 扩展"
    assert policy["xunfei"]["required_mode"] == "推理模式"
    assert policy["gemini"]["verification_markers"] == ["gemini_pro_verified:yes", "gemini_expanded_verified:yes"]
    assert policy["xunfei"]["verification_markers"] == ["xunfei_reasoning_verified:yes"]
    assert policy["xunfei"]["strict"] is True
    assert policy["gemini"]["strict"] is True
    assert _quality_mode_required_mode("chatgpt") == ""


def test_required_quality_mode_hosts_bypass_prepare_short_circuit():
    js = _build_prepare_submission_ui_js("AIJUDGE-quality-hosts-test")

    assert "forceQualityPrepareHost" in js
    assert "sessionStorage.getItem(key) && !forceQualityPrepareHost" in js
    assert "chat\\.qwen\\.ai" in js
    assert "agent\\.minimax\\.io" in js
    assert "gemini\\.google\\.com" in js
    assert "xinghuo\\.xfyun\\.cn" in js


def test_existing_answer_capture_reports_retryable_page_state():
    js = _build_existing_answer_capture_js("deepseek")

    assert "existing_answer_page_state" in js
    assert "page_error" in js
    assert "chrome_crash" in js
    assert "blank_page" in js


def test_existing_answer_capture_prioritizes_answer_marker_before_page_error():
    js = _build_existing_answer_capture_js("minimax")

    assert js.index("const latest = unique[unique.length - 1] || null") < js.index("if (pageError || chromeCrash || blankPage)")
    assert "existing_answer_marker" in js


def test_gemini_prepare_prefers_pro_expanded_model():
    js = _build_prepare_submission_ui_js("AIJUDGE-gemini-test")

    assert "gemini_pro_clicked" in js
    assert "gemini_pro_verified:yes" in js
    assert "gemini_expanded_clicked" in js
    assert "gemini_expanded_verified:yes" in js
    assert "gemini_model_menu_open" in js
    assert "gemini_thinking_level_menu_open" in js
    assert "Gemini\\s*2\\.5\\s*Pro" in js


def test_commercial_growth_prompt_rejects_report_ui_stale_answer():
    question = "【任务：AI Judge 商业化/投稿/融资/GitHub 加星全量评审】请给商业化、投稿、融资、社媒和 GitHub star 增长方案。"
    stale_answer = "当前 AI Judge 报告存在结构性失败，首屏同时承载流程状态和完整业务报告，建议重构运行健康门禁。"
    current_answer = "条件支持：优先冲 GitHub 加星、Hugging Face Spaces 开源传播、融资加速器投稿和社媒增长。"

    assert not _response_matches_question(stale_answer, question)
    assert _response_matches_question(current_answer, question)


def test_chatgpt_prepare_prefers_reliable_mode_for_bridge_output():
    js = _build_prepare_submission_ui_js("AIJUDGE-chatgpt-test")

    assert "chatgpt_reliable_mode" in js
    assert "chatgpt_mode_menu_open" in js
    assert "chatgpt_thinking_mode" not in js
    assert "reliableChatgptMode" in js
    assert "shortChatgptLabel" in js
    assert "inOpenMenu" in js
    assert "Auto" in js
    assert "No Thinking" in js


def test_mimo_fresh_navigation_treats_hash_chat_ids_as_stale_routes():
    js = _build_fresh_navigation_js("https://aistudio.xiaomimimo.com/#/chat")

    assert "hashSensitiveNavigation" in js
    assert "hash_route_mismatch" in js
    assert "mimo_stale_chat_route" in js
    assert "aistudio\\.xiaomimimo\\.com" in js


def test_mimo_provider_limit_overlay_is_recoverable_once():
    assert _page_state_needs_reload({
        "reason": "provider_quota_limited",
        "url": "https://aistudio.xiaomimimo.com/#/chat/123",
    })
    assert _readiness_can_recover({
        "page_blocked": True,
        "reason": "provider_quota_limited",
        "url": "https://aistudio.xiaomimimo.com/#/chat/123",
    })
    assert not _page_state_needs_reload({
        "reason": "provider_quota_limited",
        "url": "https://grok.com/",
    })


def test_mimo_clear_blocking_ui_dismisses_dialogs_and_reports_quota():
    js = _build_clear_blocking_ui_js()

    assert "mimo_blocking_ui_dismissed" in js
    assert "mimo_blocking_icon_closed" in js
    assert "provider_quota_limited" in js
    assert "aistudio\\.xiaomimimo\\.com" in js


def test_mimo_prepare_opens_new_chat_from_history_page():
    js = _build_prepare_submission_ui_js("AIJUDGE-mimo-test")

    assert "mimo_new_chat_from_history" in js
    assert "新对话" in js
    assert "aistudio\\.xiaomimimo\\.com" in js


def test_first_round_prompt_requests_resonance_questions():
    prompt = _seat_prompt("qwen", "升级 AI Judge", "strategic")

    assert "共振提问" in prompt
    assert "3-5 个" in prompt


def test_second_round_prompt_answers_resonance_questions_instead_of_looping():
    prompt = _seat_prompt("qwen", "[AIJUDGE_RESONANCE_FOLLOWUP]\n升级 AI Judge", "strategic")

    assert "第二轮共振回答" in prompt
    assert "不需要继续提出新问题" in prompt
    assert "详细技术方案" in prompt


def test_capture_scans_all_answer_markers_and_qwen_blocks():
    js = _build_capture_js("AIJUDGE-chatgpt-test")

    assert "source.indexOf(answerStart, searchFrom)" in js
    assert "最终答案正文" in js
    assert ".response-message-content" in js
    assert ".qwen-markdown" in js
    assert "已经完成思考" in js
    assert "qwenThinkingCompleteOnly" in js
    assert "qwen_thinking_complete_only" in js
    assert js.index("const answerMarkerInBody") < js.index("const qwenThinkingCompleteOnly")
    assert js.index("const answerMarkerInRaw") < js.index("const qwenThinkingCompleteOnly")


def test_qwen_thinking_complete_can_nudge_despite_prompt_echo():
    item = {
        "submission_confirmed": True,
        "submitted_at": 1,
        "timeout_seconds": 120,
    }
    capture = {
        "qwen_thinking_complete_only": True,
        "page_busy": False,
    }
    assessment = {
        "accepted": False,
        "polluted": False,
        "prompt_echo": True,
        "response_text": "",
    }

    assert _should_send_final_answer_nudge("qwen", item, capture, assessment)


def test_existing_answer_capture_reads_prior_markers_without_prompt_write():
    js = _build_existing_answer_capture_js("qwen")

    assert "AIJUDGE_ANSWER_START:(AIJUDGE-" in js
    assert "safeSeat" in js
    assert "existing_answer_not_found" in js
    assert "existing_answer_placeholder" in js
    assert "startRe.lastIndex = 0" in js
    assert "fallback_found" in js
    assert "existing_answer_fallback" in js
    assert "execCommand" not in js
    assert "click()" not in js
    assert "你的最终答案" in js


def test_slow_seat_prompts_require_direct_final_body_not_thinking_only():
    chatgpt_prompt = _seat_prompt("chatgpt", "升级 AI Judge", "strategic")
    qwen_prompt = _seat_prompt("qwen", "升级 AI Judge", "strategic")

    assert "不要切换到深入/思考模式" in chatgpt_prompt
    assert "不要只停在思考完成提示" in qwen_prompt
    assert "完整保留 AIJUDGE 起止标记" in chatgpt_prompt
    assert "完整保留 AIJUDGE 起止标记" in qwen_prompt


def test_doubao_prompt_requires_expert_mode_guardrail():
    prompt = _seat_prompt("doubao", "升级 AI Judge", "strategic")

    assert "专家/超能模式" in prompt
    assert "不要使用快速模式" in prompt
    assert "完整保留 AIJUDGE 起止标记" in prompt


def test_submission_check_prioritizes_prompt_still_in_input():
    js = _build_submission_check_js("AIJUDGE-chatgpt-test")

    assert js.index("prompt_still_in_input") < js.index("marker_in_conversation")


def test_fresh_navigation_reloads_same_url_page_errors():
    js = _build_fresh_navigation_js("https://yiyan.baidu.com/")

    assert "pageError" in js
    assert "location.reload()" in js
    assert 'reason: "page_error"' in js
    assert "normalizeForNavigation" in js
    assert "currentUrl" in js


def test_clear_blocking_ui_detects_crashes_blank_pages_and_retryable_errors():
    js = _build_clear_blocking_ui_js()

    assert "chrome_crash" in js
    assert "blank_page" in js
    assert "page_error" in js
    assert "Aw, Snap" in js
    assert "网络错误" in js


def test_minimax_fixed_tab_has_dedicated_send_fallback():
    js = _build_click_send_js("AIJUDGE-minimax-test")

    assert "agent\\.minimax\\.io" in js
    assert "miniMaxButtons" in js
    assert "closeToComposerRight" in js
    assert "提出共振" in js


def test_mimo_send_fallback_is_composer_scoped():
    js = _build_click_send_js("AIJUDGE-mimo-test")

    assert "aistudio\\.xiaomimimo\\.com" in js
    assert "mimoButtons" in js
    assert "inputRect.right - 120" in js
    assert "rect.bottom <= inputRect.bottom + 160" in js


def test_doubao_fixed_tab_has_dedicated_send_fallback():
    js = _build_click_send_js("AIJUDGE-doubao-test")

    assert "doubao\\.com" in js
    assert "doubaoButtons" in js
    assert "send-btn" in js
    assert "emptyRightIcon" in js


def test_forecast_market_product_term_does_not_force_prediction_intent():
    flow = build_prompt_flow(
        "请评估 Grand Judge 与 Forecast Market 的产品升级方案",
        mode="strategic",
        engine="web",
    )

    assert "产品方案" in flow["intent"]
