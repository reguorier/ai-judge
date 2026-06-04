from bridges.chrome_fixed_tab_bridge import (
    _final_nudge_timeout_seconds,
    _human_pacing_window,
    _page_state_needs_reload,
    _post_timeout_grace_seconds,
    _seat_timeout_seconds,
)
from pathlib import Path
from tempfile import TemporaryDirectory
from core.seat_execution_policy import execution_policy_summary
import bridges.web_seat_bridge as web_seat_bridge
from bridges.web_seat_bridge import (
    _calibrate_desktop_seat,
    _desktop_collection_block,
    _merge_retry_results,
    _readiness_reason,
    _run_driver_with_retries,
    _seat_prompt,
    _seat_login_state,
    _should_retry_result,
    default_config,
    merge_bridge_config_overrides,
)


def test_retryable_timeout_can_be_retried_but_quota_cannot():
    assert _should_retry_result({
        "seat": "qwen",
        "ok": False,
        "error": {"code": "response_timeout", "message": "No response captured."},
    })
    assert _should_retry_result({
        "seat": "chatgpt",
        "ok": False,
        "supplementable": True,
        "error": {"code": "slow_response_pending", "message": "still thinking"},
    })
    assert not _should_retry_result({
        "seat": "grok",
        "ok": False,
        "error": {"code": "provider_quota_limited", "message": "usage limit"},
    })


def test_merge_retry_results_preserves_order_and_marks_recovery():
    original = [
        {
            "seat": "gemini",
            "ok": True,
            "response": "ok",
        },
        {
            "seat": "qwen",
            "ok": False,
            "response": "",
            "error": {"code": "response_timeout", "message": "No response captured."},
        },
    ]
    retried = [
        {
            "seat": "qwen",
            "ok": True,
            "response": "retry answer",
            "error": None,
        }
    ]

    merged = _merge_retry_results(original, retried, attempt=1)

    assert [item["seat"] for item in merged] == ["gemini", "qwen"]
    assert merged[1]["ok"]
    assert merged[1]["recovered_by_retry"]
    assert merged[1]["retry_attempts"] == 1
    assert merged[1]["retry_history"][0]["error_code"] == "response_timeout"


def test_retry_wrapper_reruns_only_retryable_failed_seats():
    calls = []
    retry_flags = []

    def runner(question, seats, config, mode, progress=None, trace=None):
        calls.append(list(seats))
        retry_flags.append(bool(config.get("_retry_run")))
        if len(calls) == 1:
            return [
                {"seat": "gemini", "ok": True, "response": "ok"},
                {
                    "seat": "qwen",
                    "ok": False,
                    "response": "",
                    "error": {"code": "response_timeout", "message": "No response captured."},
                },
                {
                    "seat": "grok",
                    "ok": False,
                    "response": "",
                    "error": {"code": "provider_quota_limited", "message": "usage limit"},
                },
            ]
        return [{"seat": "qwen", "ok": True, "response": "retry answer", "error": None}]

    results = _run_driver_with_retries(
        runner=runner,
        question="test",
        seats=["gemini", "qwen", "grok"],
        config={"retry_failed_seats": True, "retry_attempts": 1},
        mode="flash",
        progress=None,
        trace=None,
        driver_label="test-driver",
    )

    assert calls == [["gemini", "qwen", "grok"], ["qwen"]]
    assert retry_flags == [False, True]
    assert results[1]["ok"]
    assert results[1]["recovered_by_retry"]
    assert not results[2]["ok"]


def test_rescue_config_overrides_enable_clean_conversation_without_losing_seat_settings():
    config = default_config()
    config["seats"]["minimax"]["enabled"] = True
    merged = merge_bridge_config_overrides(config, {
        "fresh_conversation_per_run": True,
        "seats": {"minimax": {"timeout_seconds": 900}},
    })

    assert merged["fresh_conversation_per_run"] is True
    assert merged["seats"]["minimax"]["enabled"] is True
    assert merged["seats"]["minimax"]["timeout_seconds"] == 900
    assert merged["seats"]["minimax"]["url"] == "https://agent.minimax.io"
    assert merged["seats"]["minimax"]["fallback_url"] == ""


def test_default_config_enables_humanized_pacing_and_fragile_seats():
    config = default_config()

    assert config["humanized_pacing"] is True
    assert config["page_recovery_attempts"] == 1
    assert config["human_pacing"]["after_reload_seconds"] >= 4
    assert config["seats"]["chatgpt"]["fragile_page"] is True
    assert config["seats"]["deepseek"]["fragile_page"] is True
    assert config["seats"]["qwen"]["fragile_page"] is True
    assert config["seats"]["wenxin"]["fragile_page"] is True
    assert config["seats"]["mimo"]["fragile_page"] is True
    assert config["seats"]["gemini"]["fragile_page"] is False


def test_worldcup_fragile_seats_receive_short_structured_prompt():
    prompt = _seat_prompt(
        "minimax",
        "世界杯预测池 Run #7：14 席全部参审，输出 bet_ledger、贷款和 GP 投注。",
        "strategic",
    )

    assert "世界杯预测池短回执" in prompt
    assert '"seat_status"' in prompt
    assert "不要 Markdown 表格" in prompt


def test_human_pacing_can_be_disabled_and_is_more_conservative_for_fragile_pages():
    assert _human_pacing_window({"humanized_pacing": False}, {}, "chatgpt") == (0.0, 0.0)

    normal = _human_pacing_window(default_config(), default_config()["seats"]["gemini"], "gemini", "before_submit")
    fragile = _human_pacing_window(default_config(), default_config()["seats"]["chatgpt"], "chatgpt", "before_submit")

    assert fragile[0] > normal[0]
    assert fragile[1] > normal[1]


def test_page_state_reload_filter_ignores_quota_but_recovers_crash_and_page_error():
    assert _page_state_needs_reload({"page_error": True, "reason": "page_error"})
    assert _page_state_needs_reload({"chrome_crash": True, "reason": "chrome_crash"})
    assert _page_state_needs_reload({"blank_page": True, "reason": "blank_page"})
    assert not _page_state_needs_reload({"page_error": True, "reason": "provider_quota_limited"})


def test_login_state_does_not_treat_chat_id_404_as_page_error():
    class Tab:
        title = "MiniMax Agent: 简单指令, 无限可能"
        url = "https://agent.minimax.io/?id=404104636134110"

    seat_config = {"url": "https://agent.minimax.io", "match_domains": ["agent.minimax.io"]}

    assert _seat_login_state(seat_config, [Tab()])["state"] == "session_present"


def test_login_state_still_detects_real_404_pages():
    class Tab:
        title = "404 Not Found"
        url = "https://agent.minimax.io/not-found"

    seat_config = {"url": "https://agent.minimax.io", "match_domains": ["agent.minimax.io"]}

    assert _seat_login_state(seat_config, [Tab()])["state"] == "page_error"


def test_required_page_error_failure_is_supplementable():
    summary = execution_policy_summary(
        [
            {
                "seat": "deepseek",
                "seat_name": "DeepSeek",
                "ok": False,
                "error": {"code": "page_error", "message": "页面错误"},
                "submission_confirmed": True,
            }
        ],
        requested_seats=["deepseek"],
    )

    assert summary["required_supplementable_seats"][0]["seat"] == "deepseek"
    assert summary["required_supplementable_seats"][0]["supplementable"] is True


def test_fixed_tab_timeout_prefers_per_seat_retry_timeout():
    config = {"timeout_seconds": 120, "retry_timeout_seconds": 180, "_retry_run": True}
    seat_config = {"timeout_seconds": 300, "retry_timeout_seconds": 420}

    assert _seat_timeout_seconds(config, seat_config) == 420
    assert _seat_timeout_seconds({"timeout_seconds": 120}, seat_config) == 300


def test_final_nudge_timeout_is_shorter_than_slow_seat_timeout():
    assert _final_nudge_timeout_seconds({}, {}) == 90
    assert _final_nudge_timeout_seconds({}, {"final_nudge_timeout_seconds": 45}) == 45


def test_post_timeout_grace_is_opt_in_and_bounded():
    assert _post_timeout_grace_seconds({}, {}) == 0
    assert _post_timeout_grace_seconds({}, {"post_timeout_grace_seconds": 45}) == 45
    assert _post_timeout_grace_seconds({}, {"post_timeout_grace_seconds": 120}) == 120


def test_deepseek_desktop_path_is_explicitly_blocked_until_expert_operator_exists():
    tmp = TemporaryDirectory()
    app_path = Path(tmp.name) / "DeepSeek.app"
    app_path.mkdir()
    seat_config = {
        "provider": "DeepSeek",
        "channel": "desktop",
        "desktop_app": {
            "name": "DeepSeek",
            "bundle_id": "com.deepseek.chat",
            "path": str(app_path),
        },
    }

    reason = _readiness_reason(
        channel="desktop",
        enabled=True,
        installed=True,
        configured=True,
        desktop_installed=True,
        seat_config=seat_config,
        calibration_entry={"status": "missing"},
        driver={"safe_background": False},
    )
    code, message = _desktop_collection_block("deepseek", seat_config)
    calibration = _calibrate_desktop_seat("deepseek", seat_config)

    assert reason == "deepseek_desktop_expert_operator_missing"
    assert code == "deepseek_desktop_expert_operator_missing"
    assert "专家模式" in message
    assert calibration["error"]["code"] == "deepseek_desktop_expert_operator_missing"


def test_login_state_detects_claude_restricted_page():
    """P62: A Claude tab at /restricted must return provider_account_restricted, not session_present."""
    class Tab:
        title = "Claude"
        url = "https://claude.ai/restricted"

    seat_config = {"url": "https://claude.ai/new", "match_domains": ["claude.ai"]}

    result = _seat_login_state(seat_config, [Tab()])
    assert result["state"] == "provider_account_restricted"


def test_bridge_status_marks_restricted_required_tab_not_ready(monkeypatch):
    """A restricted required tab must not count as ready in the product status matrix."""
    config = web_seat_bridge.default_config()
    config["automation_driver"] = "chrome_cdp"
    config["auto_wake_cdp"] = False
    config["auto_wake_open_tabs"] = False
    config["login_state_audit"] = False
    for seat_config in config["seats"].values():
        seat_config["enabled"] = False
    config["seats"]["claude"].update({
        "enabled": True,
        "url": "https://claude.ai/new",
        "fresh_url": "https://claude.ai/new",
        "match_domains": ["claude.ai"],
        "channel": "web",
        "execution_required": True,
    })

    class Tab:
        title = "Claude"
        url = "https://claude.ai/restricted"

    monkeypatch.setattr(web_seat_bridge, "load_bridge_config", lambda path=None: config)
    monkeypatch.setattr(web_seat_bridge, "load_calibration", lambda: {"version": 1, "updated_at": None, "seats": {}})
    monkeypatch.setattr(web_seat_bridge, "playwright_installed", lambda: True)
    monkeypatch.setattr(web_seat_bridge, "chrome_cdp_status", lambda config: {"available": True})
    monkeypatch.setattr(web_seat_bridge, "list_cdp_tabs", lambda config: [Tab()])
    monkeypatch.setattr(web_seat_bridge, "_write_login_state_audit", lambda config, status_payload: None)

    status = web_seat_bridge.bridge_status()
    claude = next(row for row in status["seat_browser_matrix"] if row["seat"] == "claude")

    assert status["ready_count"] == 0
    assert claude["configured"] is True
    assert claude["ready"] is False
    assert claude["reason"] == "provider_account_restricted"
    assert claude["login_state"]["state"] == "provider_account_restricted"


def test_login_state_detects_generic_account_blocked_markers():
    """P62: Various account-restriction markers must produce provider_account_restricted."""
    blocked_cases = [
        ("Account on hold", "https://claude.ai/restricted"),
        ("Request a review", "https://chatgpt.com/"),
        ("Your account has been suspended", "https://gemini.google.com/app"),
        ("Blocked", "https://chat.deepseek.com/"),
    ]
    for title, url in blocked_cases:
        class Tab:
            pass
        Tab.title = title
        Tab.url = url
        domain = url.split("//")[1].split("/")[0]
        seat_config = {"url": url, "match_domains": [domain]}
        result = _seat_login_state(seat_config, [Tab()])
        assert result["state"] == "provider_account_restricted", (
            f"Expected provider_account_restricted for title={title!r} url={url!r}, got {result['state']}"
        )


def test_login_state_normal_session_not_flagged_as_restricted():
    """P62: A normal Claude session must remain session_present."""
    class Tab:
        title = "Claude"
        url = "https://claude.ai/new"

    seat_config = {"url": "https://claude.ai/new", "match_domains": ["claude.ai"]}
    assert _seat_login_state(seat_config, [Tab()])["state"] == "session_present"
