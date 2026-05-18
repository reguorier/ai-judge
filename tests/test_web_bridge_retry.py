from bridges.chrome_fixed_tab_bridge import _final_nudge_timeout_seconds, _post_timeout_grace_seconds, _seat_timeout_seconds
from pathlib import Path
from tempfile import TemporaryDirectory
from bridges.web_seat_bridge import (
    _calibrate_desktop_seat,
    _desktop_collection_block,
    _merge_retry_results,
    _readiness_reason,
    _run_driver_with_retries,
    _should_retry_result,
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
