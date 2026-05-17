from bridges.chrome_fixed_tab_bridge import (
    _build_capture_js,
    _build_click_send_js,
    _build_existing_answer_capture_js,
    _build_fresh_navigation_js,
    _build_prepare_submission_ui_js,
    _build_submission_check_js,
    _deepseek_prepare_verified,
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


def test_qwen_prepare_prefers_reliable_non_thinking_mode_for_bridge_output():
    js = _build_prepare_submission_ui_js("AIJUDGE-qwen-test")

    assert "qwen_reliable_mode" in js
    assert "qwen_mode_menu_open" in js
    assert "qwen_thinking_mode" not in js


def test_chatgpt_prepare_prefers_reliable_mode_for_bridge_output():
    js = _build_prepare_submission_ui_js("AIJUDGE-chatgpt-test")

    assert "chatgpt_reliable_mode" in js
    assert "chatgpt_mode_menu_open" in js
    assert "chatgpt_thinking_mode" not in js


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


def test_minimax_fixed_tab_has_dedicated_send_fallback():
    js = _build_click_send_js("AIJUDGE-minimax-test")

    assert "agent\\.minimaxi\\.com" in js
    assert "miniMaxButtons" in js
    assert "closeToComposerRight" in js
    assert "提出共振" in js


def test_forecast_market_product_term_does_not_force_prediction_intent():
    flow = build_prompt_flow(
        "请评估 Grand Judge 与 Forecast Market 的产品升级方案",
        mode="strategic",
        engine="web",
    )

    assert "产品方案" in flow["intent"]
