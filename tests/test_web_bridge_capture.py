import time

from bridges.chrome_fixed_tab_bridge import (
    _capture_acceptance,
    _capture_is_polluted,
    _response_text_from_capture,
    _should_send_final_answer_nudge,
)
from core.web_jury import build_web_claims


def test_response_text_from_capture_uses_marker_text_directly():
    capture = {"text": "本轮答案：预测世界杯冠军为法国，亚军为英格兰。", "marker_found": True}
    item = {"before_text": "旧回答：技术方案"}

    assert _response_text_from_capture(capture, item).startswith("本轮答案")


def test_response_text_from_capture_diffs_fallback_transcript():
    before = "旧回答：产品方案\n旧回答：实现路径"
    current = before + "\n新回答：预测世界杯冠军为法国，四强为法国、英格兰、阿根廷、巴西。"

    assert _response_text_from_capture({"text": current, "marker_found": False}, {"before_text": before}) == (
        "新回答：预测世界杯冠军为法国，四强为法国、英格兰、阿根廷、巴西。"
    )


def test_build_web_claims_keeps_failed_page_error_visible():
    claims = build_web_claims(
        question="预测2026世界杯冠军",
        mode="standard",
        results=[
            {
                "seat": "claude",
                "ok": False,
                "error": {"code": "model_page_error", "message": "We couldn't connect to Claude."},
            }
        ],
    )

    assert "model_page_error" in claims[0]["claim"]


def test_capture_pollution_rejects_old_ai_judge_markers():
    text = (
        "旧回答内容 " * 300
        + "[trace_id: AIJUDGE-deepseek-1778867334]\n"
        + "[QUESTION] 旧问题\n[QUESTION] 新问题"
    )

    assert _capture_is_polluted(text, "AIJUDGE-deepseek-999999999999")


def test_closed_marker_answer_is_accepted_without_topic_echo():
    capture = {
        "ok": True,
        "text": "立场：信息不足。理由：这是一次格式烟测，已经收到并按要求返回。",
        "marker_found": True,
        "marker_closed": True,
    }
    item = {"prompt_id": "AIJUDGE-claude-123", "submission_confirmed": True, "before_text": ""}

    accepted = _capture_acceptance(capture, item, "必须包含关键词 AIJUDGE_SMOKE_20260516")

    assert accepted["accepted"]
    assert accepted["mode"] == "closed_marker"


def test_prompt_placeholder_marker_is_not_accepted_as_answer():
    capture = {
        "ok": True,
        "text": "",
        "marker_found": True,
        "marker_closed": False,
    }
    item = {"prompt_id": "AIJUDGE-gemini-123", "submission_confirmed": True, "before_text": ""}

    accepted = _capture_acceptance(capture, item, "AI Judge采集烟测")

    assert not accepted["accepted"]


def test_prompt_echo_with_placeholder_is_rejected_even_when_long():
    prompt_id = "AIJUDGE-gemini-456"
    text = (
        "[SYSTEM] role\n[QUESTION] AI Judge稳定网页席位整组烟测：请包含关键词 AIJUDGE_STABLE_GROUP_SMOKE。\n"
        f"[AIJUDGE_ANSWER_START:{prompt_id}]\n你的最终答案\n[AIJUDGE_ANSWER_END:{prompt_id}]\n"
        f"[trace_id: {prompt_id}]\nGemini 是一款 AI 工具，其回答未必正确无误。使用麦克风"
    )
    capture = {
        "ok": True,
        "text": text,
        "marker_found": False,
        "marker_closed": False,
    }
    item = {"prompt_id": prompt_id, "submission_confirmed": True, "before_text": "", "before_length": 0}

    accepted = _capture_acceptance(
        capture,
        item,
        "AI Judge稳定网页席位整组烟测：请包含关键词 AIJUDGE_STABLE_GROUP_SMOKE。",
    )

    assert accepted["prompt_echo"]
    assert not accepted["accepted"]


def test_capture_acceptance_strips_trailing_answer_end_marker():
    prompt_id = "AIJUDGE-yuanbao-123"
    capture = {
        "ok": True,
        "text": "支持。AIJUDGE_RETRY_QUEUE_OK。\nAIJUDGE_ANSWER_END:AIJUDGE-yuanbao-123\n1\n2\n3",
        "marker_found": True,
        "marker_closed": False,
    }
    item = {"prompt_id": prompt_id, "submission_confirmed": True, "before_text": ""}

    accepted = _capture_acceptance(capture, item, "AI Judge补跑队列真实烟测")

    assert "AIJUDGE_ANSWER_END" not in accepted["response_text"]
    assert accepted["response_text"].endswith("AIJUDGE_RETRY_QUEUE_OK。")


def test_chatgpt_short_fallback_is_not_accepted_too_early():
    capture = {
        "ok": True,
        "text": "立场：条件支持。评分：86/100。核心判断：Grand Judge 应升级，但必须先做引用验证。" * 4,
        "marker_found": False,
        "marker_closed": False,
        "page_busy": False,
    }
    item = {"seat": "chatgpt", "prompt_id": "AIJUDGE-chatgpt-123", "submission_confirmed": True, "before_text": ""}

    accepted = _capture_acceptance(capture, item, "AI Judge Grand Judge citation_validator evidence_gap_filler")

    assert not accepted["accepted"]
    assert accepted["fallback_min_chars"] == 800


def test_busy_fallback_waits_for_completion():
    capture = {
        "ok": True,
        "text": "AI Judge Grand Judge citation_validator evidence_gap_filler " * 30,
        "marker_found": False,
        "marker_closed": False,
        "page_busy": True,
    }
    item = {"seat": "qwen", "prompt_id": "AIJUDGE-qwen-123", "submission_confirmed": True, "before_text": ""}

    accepted = _capture_acceptance(capture, item, "AI Judge Grand Judge citation_validator evidence_gap_filler")

    assert not accepted["accepted"]
    assert accepted["page_busy"]


def test_chatgpt_empty_thinking_turn_triggers_final_answer_nudge():
    item = {
        "prompt_id": "AIJUDGE-chatgpt-123",
        "submitted_at": time.time() - 90,
        "timeout_seconds": 300,
        "submission_confirmed": True,
    }
    capture = {"assistant_empty": True, "thinking_only": True}
    assessment = {"accepted": False, "polluted": False, "prompt_echo": False, "response_text": ""}

    assert _should_send_final_answer_nudge("chatgpt", item, capture, assessment)
    item["final_answer_nudge"] = {"ok": True}
    assert not _should_send_final_answer_nudge("chatgpt", item, capture, assessment)


def test_nudge_waits_while_chatgpt_is_still_generating():
    item = {
        "prompt_id": "AIJUDGE-chatgpt-123",
        "submitted_at": time.time() - 90,
        "timeout_seconds": 300,
        "submission_confirmed": True,
    }
    capture = {"assistant_empty": True, "thinking_only": True, "page_busy": True}
    assessment = {"accepted": False, "polluted": False, "prompt_echo": False, "response_text": ""}

    assert not _should_send_final_answer_nudge("chatgpt", item, capture, assessment)


def test_qwen_empty_thinking_turn_triggers_final_answer_nudge():
    item = {
        "prompt_id": "AIJUDGE-qwen-123",
        "submitted_at": time.time() - 90,
        "timeout_seconds": 180,
        "submission_confirmed": True,
    }
    capture = {"assistant_empty": True, "thinking_only": True}
    assessment = {"accepted": False, "polluted": False, "prompt_echo": False, "response_text": ""}

    assert _should_send_final_answer_nudge("qwen", item, capture, assessment)


def test_required_non_grok_empty_turn_triggers_final_answer_nudge():
    item = {
        "prompt_id": "AIJUDGE-doubao-123",
        "submitted_at": time.time() - 90,
        "timeout_seconds": 180,
        "submission_confirmed": True,
    }
    capture = {"assistant_empty": True, "thinking_only": True}
    assessment = {"accepted": False, "polluted": False, "prompt_echo": False, "response_text": ""}

    assert _should_send_final_answer_nudge("doubao", item, capture, assessment)
    assert not _should_send_final_answer_nudge("grok", item, capture, assessment)
