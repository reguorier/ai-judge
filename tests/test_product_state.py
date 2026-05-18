from __future__ import annotations

import importlib.util
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _load_api_server():
    module_path = Path(__file__).resolve().parents[1] / "product" / "api_server.py"
    spec = importlib.util.spec_from_file_location("api_server_product_state_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dashboard_exposes_report_link_in_result_area_and_allows_human_confirmation_with_blockers():
    root = Path(__file__).resolve().parents[1]
    html = (root / "product" / "dashboard.html").read_text(encoding="utf-8")
    js = (root / "product" / "dashboard.js").read_text(encoding="utf-8")

    assert 'id="result-view-link"' in html
    assert "打开网站完整报告" in html
    assert ".executive-report" in html
    assert "查看专业报告" in js
    assert '$$("#view-link, #result-view-link")' in js
    assert "const canConfirm = hasVerdict;" in js
    assert 'state: !hasVerdict ? "block" : state.publishCleared ? "ok" : "block"' in js


def test_product_capabilities_and_health_are_v38():
    api_server = _load_api_server()
    client = api_server.app.test_client()

    health = client.get("/api/health").get_json()
    capabilities = client.get("/api/product/capabilities").get_json()

    assert health["version"] == "3.8.0"
    assert "stable_closeout" in health["product_layers"]
    assert capabilities["stable_mode"]["label"] == "简约版"
    assert capabilities["lab_mode"]["label"] == "专业版"
    assert capabilities["human_gavel"]["states"][2]["id"] == "publishable"


def test_benchmark_summary_returns_four_reliability_cards(monkeypatch):
    api_server = _load_api_server()
    monkeypatch.setattr(api_server, "_iter_saved_verdicts", lambda limit=80: iter([]))
    monkeypatch.setattr(api_server, "bridge_status", lambda: {
        "seats": [{"id": "chatgpt", "provider": "OpenAI", "channel": "web", "ready": True}],
        "seat_browser_matrix": [{"seat": "chatgpt", "ready": True, "target": "ChatGPT"}],
    })

    data = api_server.app.test_client().get("/api/benchmarks/summary").get_json()

    assert data["version"] == "3.8.0"
    assert [card["id"] for card in data["cards"]] == [
        "citation",
        "decision",
        "web_recovery",
        "cdp_reliability",
    ]
    assert data["scoreboard"]["ready_seats"] >= 1


def test_chief_judge_metadata_attaches_to_local_verdict():
    api_server = _load_api_server()
    verdict = {
        "question": "测试主审",
        "seats": ["chatgpt", "deepseek"],
        "seat_scores": [
            {"seat": "deepseek", "seat_name": "DeepSeek", "average_score": 0.82, "claims_count": 3},
            {"seat": "chatgpt", "seat_name": "ChatGPT", "average_score": 0.74, "claims_count": 3},
        ],
        "average_score": 0.78,
        "verdict": "credible",
        "verdict_label": "可采信",
        "one_liner": "本轮判断成立。",
    }

    api_server._attach_product_run_metadata(verdict, chief_judge="deepseek", abstained_seats=["grok"])

    assert verdict["product_version"] == "3.8.0"
    assert verdict["product_layer"]["stable_mode"] == "5-minute trustworthy closeout"
    assert verdict["chief_judge"]["id"] == "deepseek"
    assert verdict["seat_roster"]["selected"] == ["chatgpt", "deepseek"]
    assert verdict["seat_roster"]["abstained"] == ["grok"]
    assert verdict["judge_answer"]["label"] == "DeepSeek 轮值主审"
    assert "本轮主审：DeepSeek" in verdict["judge_answer"]["answer"]
    assert verdict["single_judge_baseline"]["label"] == "DeepSeek 单模型对照"
    assert verdict["roster_sensitivity"]
    assert verdict["final_report"]["schema"] == "ai_judge.final_report.v1"
    assert verdict["final_report"]["title"] == "AI Judge 轮值法官最终报告"
    assert verdict["final_report"]["judge_editor"]["label"] == "DeepSeek 轮值法官"
    assert verdict["final_report"]["recommendation"]
    assert verdict["final_report"]["key_findings"]
    assert verdict["final_report"]["postulates"]
    assert "本轮判断成立" in verdict["final_report"]["abstract"]


def test_progress_diagnostics_surface_page_recovery_states():
    api_server = _load_api_server()
    previous = None
    recovery_event = {
        "phase": "seat",
        "action": "chrome_tab_recovery",
        "detail": "chatgpt 页面刷新恢复完成",
        "at": "2026-05-18T12:00:00+00:00",
        "data": {"seat": "chatgpt", "reason": "page_error"},
    }
    failed_event = {
        "phase": "seat",
        "action": "chrome_tab_recovery_failed",
        "detail": "qwen 页面刷新恢复未就绪",
        "at": "2026-05-18T12:00:01+00:00",
        "data": {"seat": "qwen", "reason": "chrome_crash"},
    }

    recovering = api_server._next_seat_progress_state("chatgpt", previous, recovery_event)
    blocked = api_server._next_seat_progress_state("qwen", previous, failed_event)

    assert recovering["state"] == "submitting"
    assert recovering["status"] == "刷新恢复"
    assert blocked["state"] == "blocked"
    assert blocked["code"] == "page_recovery_failed"
    assert api_server._seat_error_label("chrome_crash") == "标签崩溃"
    assert "刷新后补跑" in api_server._seat_error_reason("page_error")


def test_progress_diagnostics_surface_doubao_expert_mode_block():
    api_server = _load_api_server()
    event = {
        "phase": "seat",
        "action": "doubao_expert_mode_blocked",
        "detail": "doubao 未确认专家/超能模式",
        "at": "2026-05-18T12:00:02+00:00",
        "data": {"seat": "doubao", "prepared": {"clicked_names": ["doubao_expert_verified:no"]}},
    }

    state = api_server._next_seat_progress_state("doubao", None, event)

    assert state["state"] == "blocked"
    assert state["code"] == "doubao_expert_mode_not_verified"
    assert state["status"] == "专家模式未确认"
    assert "拒绝快速模式提交" in state["reason"]


def test_seat_scoreboard_aggregates_runs_and_rounds():
    api_server = _load_api_server()
    verdicts = [
        {
            "run_id": "run-new",
            "question": "新问题",
            "mode": "strategic",
            "created_at": "2026-05-16T12:00:00+00:00",
            "seat_scores": [
                {"seat": "deepseek", "seat_name": "DeepSeek", "average_score": 0.9, "claims_count": 4},
                {"seat": "chatgpt", "seat_name": "ChatGPT", "average_score": 0.7, "claims_count": 4},
            ],
            "web_bridge": {
                "score_rounds": [
                    {"id": "raw_answer", "seat_scores": [{"seat": "deepseek", "average_score": 0.8}]},
                    {"id": "peer_review", "seat_scores": [{"seat": "deepseek", "average_score": 0.88}]},
                ],
                "raw_results": [
                    {"seat": "deepseek", "ok": True},
                    {"seat": "chatgpt", "ok": False, "error": {"code": "response_timeout"}},
                ],
            },
        },
        {
            "run_id": "run-old",
            "question": "旧问题",
            "mode": "standard",
            "created_at": "2026-05-15T12:00:00+00:00",
            "seat_scores": [
                {"seat": "deepseek", "seat_name": "DeepSeek", "average_score": 0.7, "claims_count": 3},
            ],
        },
    ]

    scoreboard = api_server._build_seat_scoreboard(
        verdicts=verdicts,
        bridge={
            "seats": [{"id": "deepseek", "provider": "DeepSeek", "channel": "web", "ready": True}],
            "seat_browser_matrix": [{"seat": "deepseek", "target": "DeepSeek Tab", "ready": True}],
        },
    )

    deepseek = next(row for row in scoreboard["seats"] if row["seat"] == "deepseek")
    chatgpt = next(row for row in scoreboard["seats"] if row["seat"] == "chatgpt")

    assert scoreboard["runs_considered"] == 2
    assert deepseek["run_count"] == 2
    assert deepseek["average_score"] == 0.8
    assert deepseek["latest_run"]["run_id"] == "run-new"
    assert deepseek["k_avg"] == 0.8
    assert deepseek["c_avg"] == 0.88
    assert deepseek["r_stability"] == 1.0
    assert chatgpt["failure_count"] == 1


def test_supplement_merge_replaces_slow_seat_and_marks_recovery():
    api_server = _load_api_server()
    original = [
        {
            "seat": "chatgpt",
            "ok": False,
            "supplementable": True,
            "error": {"code": "slow_response_pending", "message": "still thinking"},
        },
        {"seat": "deepseek", "ok": True, "response": "done"},
    ]
    supplement = [
        {"seat": "chatgpt", "ok": True, "response": "late answer", "error": None},
    ]

    merged = api_server._merge_supplement_raw_results(original, supplement, "supp-1")

    assert merged[0]["ok"]
    assert merged[0]["recovered_by_supplement"]
    assert merged[0]["supplemented_from_run_id"] == "supp-1"
    assert merged[0]["supplement_history"][0]["previous_error"]["code"] == "slow_response_pending"
    assert merged[1]["seat"] == "deepseek"


def test_supplement_merge_preserves_original_success_when_recheck_fails():
    api_server = _load_api_server()
    original = [
        {"seat": "gemini", "ok": True, "response": "original useful answer", "error": None},
    ]
    supplement = [
        {
            "seat": "gemini",
            "ok": False,
            "response": "",
            "error": {"code": "existing_answer_placeholder", "message": "placeholder only"},
        },
    ]

    merged = api_server._merge_supplement_raw_results(original, supplement, "supp-failed")

    assert merged[0]["ok"] is True
    assert merged[0]["response"] == "original useful answer"
    assert merged[0]["failed_supplement_preserved"] is True
    assert merged[0]["latest_supplement_error"]["code"] == "existing_answer_placeholder"
    assert merged[0]["supplement_history"][0]["new_ok"] is False


def test_send_button_failures_are_recoverable():
    api_server = _load_api_server()

    assert api_server._is_supplementable_result({
        "seat": "minimax",
        "ok": False,
        "error": {"code": "send_button_not_found"},
    })
    assert api_server._is_supplementable_result({
        "seat": "minimax",
        "ok": False,
        "error": {"code": "long_prompt_still_in_input"},
    })
    assert api_server._is_supplementable_result({
        "seat": "qwen",
        "ok": False,
        "error": {"code": "existing_answer_not_found"},
    })
    assert api_server._is_supplementable_result({
        "seat": "chatgpt",
        "ok": False,
        "error": {"code": "existing_answer_placeholder"},
    })


def test_rescue_plan_prefers_read_only_then_targeted_clean_resubmit():
    api_server = _load_api_server()
    verdict = {
        "seats": ["chatgpt", "minimax", "qwen", "grok"],
        "web_bridge": {
            "raw_results": [
                {"seat": "chatgpt", "ok": True, "response": "done"},
                {
                    "seat": "minimax",
                    "ok": False,
                    "supplementable": True,
                    "error": {"code": "send_button_not_found", "message": "no button"},
                },
                {
                    "seat": "qwen",
                    "ok": False,
                    "supplementable": True,
                    "error": {"code": "slow_response_pending", "message": "still thinking"},
                },
                {
                    "seat": "grok",
                    "ok": False,
                    "supplementable": True,
                    "error": {"code": "slow_response_pending", "message": "optional"},
                },
            ],
        },
    }

    plan = api_server._build_rescue_plan(verdict)

    assert plan["status"] == "ready"
    assert plan["button_label"] == "一键修复并回收答案"
    assert plan["read_only_seats"] == ["qwen"]
    assert plan["fresh_seats"] == ["minimax"]
    assert plan["sends_prompt"] is True
    assert [item["seat"] for item in plan["actions"]] == ["minimax", "qwen"]
    assert "Grok/Gork" in plan["summary"]


def test_rescue_plan_marks_transcript_pollution_as_clean_session_resubmit():
    api_server = _load_api_server()
    verdict = {
        "seats": ["chatgpt"],
        "web_bridge": {
            "raw_results": [
                {
                    "seat": "chatgpt",
                    "ok": False,
                    "supplementable": True,
                    "error": {"code": "transcript_pollution", "message": "old markers"},
                },
            ],
        },
    }

    plan = api_server._build_rescue_plan(verdict)

    assert plan["fresh_seats"] == ["chatgpt"]
    assert plan["actions"][0]["method"] == "clean_session_resubmit"
    assert plan["actions"][0]["label"] == "清理串流并回收"


def test_supplementable_run_seats_prefers_required_non_grok_seats():
    api_server = _load_api_server()
    verdict = {
        "seats": ["chatgpt", "qwen", "grok"],
        "web_bridge": {
            "raw_results": [
                {"seat": "chatgpt", "ok": True, "response": "done"},
                {
                    "seat": "qwen",
                    "ok": False,
                    "supplementable": True,
                    "error": {"code": "slow_response_pending"},
                },
                {
                    "seat": "grok",
                    "ok": False,
                    "supplementable": True,
                    "error": {"code": "slow_response_pending"},
                },
            ],
        },
    }

    assert api_server._supplementable_run_seats(verdict) == ["qwen"]
    assert api_server._supplementable_run_seats(verdict, requested=["grok"]) == ["grok"]


def test_web_worker_enables_second_round_resonance_collection(monkeypatch):
    api_server = _load_api_server()
    old_tasks = api_server.TASKS
    old_runs_dir = api_server.RUNS_DIR
    captured = {}

    class FakeTasks:
        def __init__(self):
            self.completed = {}
            self.failed = {}
            self.progress = []

        def update_progress(self, run_id, step, progress):
            self.progress.append((run_id, step, progress))

        def complete(self, run_id, verdict):
            self.completed[run_id] = verdict

        def fail(self, run_id, error):
            self.failed[run_id] = error

    fake_tasks = FakeTasks()

    def fake_run_web_jury(**kwargs):
        captured.update(kwargs)
        return {
            "run_id": kwargs["run_id"],
            "question": kwargs["display_question"],
            "mode": kwargs["mode"],
            "seats": kwargs["seats"],
            "web_bridge": {"raw_results": [], "mentor_supplements": []},
            "average_score": 0.61,
            "verdict": "conditional",
            "verdict_label": "建议推进但需验证",
            "one_liner": "二轮共振已进入收集链路。",
        }

    with tempfile.TemporaryDirectory() as tmp:
        api_server.RUNS_DIR = Path(tmp)
        api_server.TASKS = fake_tasks
        monkeypatch.setattr(api_server, "bridge_status", lambda: {
            "enabled_count": 1,
            "configured_count": 1,
            "ready_count": 1,
            "playwright_installed": True,
            "seat_browser_matrix": [],
            "isolation": {},
        })
        monkeypatch.setattr(api_server, "build_prompt_flow", lambda *args, **kwargs: {
            "intent": "fix",
            "trace_id": "trace-followup",
            "required_output": ["二轮共振"],
            "assumptions_to_check": [],
            "professional_prompt": "专业化后的修复请求",
        })
        monkeypatch.setattr(api_server, "decide_execution", lambda **kwargs: {
            "can_run_deep_collection": True,
            "runnable_seats": ["chatgpt"],
            "message": "ready",
        })
        monkeypatch.setattr(api_server, "run_web_jury", fake_run_web_jury)
        monkeypatch.setattr(api_server, "_attach_product_run_metadata", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_server, "_attach_citation_mvp", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_server, "generate_secure_view_url", lambda run_id: f"/view/{run_id}")
        monkeypatch.setattr(api_server, "_save_run", lambda *args, **kwargs: None)
        try:
            api_server._run_worker(
                "run-web-followup",
                "修复二次共振互动",
                "flash",
                ["chatgpt"],
                "web",
                {},
            )
        finally:
            api_server.TASKS = old_tasks
            api_server.RUNS_DIR = old_runs_dir

    assert fake_tasks.failed == {}
    assert captured["question"] == "专业化后的修复请求"
    assert captured["display_question"] == "修复二次共振互动"
    assert captured["collect_followups"] is True
    assert "run-web-followup" in fake_tasks.completed


def test_progress_diagnostics_names_waiting_and_stale_seats():
    api_server = _load_api_server()
    old_runs_dir = api_server.RUNS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        run_dir = tmp_path / "run-watch"
        run_dir.mkdir(parents=True)
        (run_dir / "trace.json").write_text(json.dumps({
            "run_id": "run-watch",
            "events": [
                {
                    "phase": "seat",
                    "action": "chrome_submit_complete",
                    "detail": "chatgpt 提示词已发送",
                    "at": "2026-05-16T15:44:24+00:00",
                    "data": {"seat": "chatgpt"},
                },
                {
                    "phase": "seat",
                    "action": "chrome_submit_unconfirmed",
                    "detail": "minimax 未确认提交",
                    "at": "2026-05-16T15:44:40+00:00",
                    "data": {"seat": "minimax", "submit": {"error": "send_button_not_found"}},
                },
            ],
        }), encoding="utf-8")
        try:
            status = {
                "run_id": "run-watch",
                "status": "running",
                "progress": 0.85,
                "current_step": "补跑 1/1：Chrome 固定标签回答轮询：等待 ChatGPT、Qwen，剩余 2 席，最长等待 427s",
                "updated_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
            }

            diagnostics = api_server._progress_diagnostics(status)
        finally:
            api_server.RUNS_DIR = old_runs_dir

    assert diagnostics["stale"] is True
    assert diagnostics["retry"] == {"attempt": 1, "total": 1}
    assert diagnostics["waiting"]["labels"] == ["ChatGPT", "Qwen"]
    assert diagnostics["waiting"]["longest_wait_seconds"] == 427
    assert diagnostics["seats"][0]["seat"] == "chatgpt"
    assert diagnostics["seats"][0]["state"] == "waiting"
    assert diagnostics["seats"][1]["seat"] == "minimax"
    assert diagnostics["seats"][1]["status"] == "发送未确认"
    assert diagnostics["rescue_plan"]["sends_prompt"] is True
    assert diagnostics["rescue_plan"]["actions"][0]["seat"] == "chatgpt"
    assert diagnostics["rescue_plan"]["actions"][1]["seat"] == "minimax"


def test_progress_diagnostics_label_unconfirmed_submit_without_nested_error():
    api_server = _load_api_server()
    old_runs_dir = api_server.RUNS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        api_server.RUNS_DIR = Path(tmp)
        run_dir = api_server.RUNS_DIR / "run-unconfirmed"
        run_dir.mkdir(parents=True)
        (run_dir / "trace.json").write_text(json.dumps({
            "run_id": "run-unconfirmed",
            "events": [
                {
                    "phase": "seat",
                    "action": "chrome_submit_unconfirmed",
                    "detail": "minimax 未确认提交",
                    "at": "2026-05-16T15:44:40+00:00",
                    "data": {
                        "seat": "minimax",
                        "submit": {"verification": {"reason": "long_prompt_still_in_input"}},
                    },
                },
            ],
        }), encoding="utf-8")
        try:
            diagnostics = api_server._progress_diagnostics({
                "run_id": "run-unconfirmed",
                "status": "running",
                "progress": 0.45,
                "current_step": "Chrome 固定标签回答轮询：剩余 1 席，最长等待 90s",
                "updated_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
            })
        finally:
            api_server.RUNS_DIR = old_runs_dir

    assert diagnostics["seats"][0]["seat"] == "minimax"
    assert diagnostics["seats"][0]["status"] == "提交未确认"
    assert diagnostics["rescue_plan"]["actions"][0]["method"] == "fresh_web_submission"


def test_recheck_endpoint_accepts_stale_running_task():
    api_server = _load_api_server()
    old_tasks = api_server.TASKS
    old_runs_dir = api_server.RUNS_DIR
    old_start = api_server._start_recheck_worker
    captured = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        api_server.TASKS = api_server.TaskManager(db_path=tmp_path / "tasks.sqlite3")

        def fake_start(recheck_run_id, source_run_id, task, seats, notify_config):
            captured.update({
                "recheck_run_id": recheck_run_id,
                "source_run_id": source_run_id,
                "task": task,
                "seats": seats,
                "notify_config": notify_config,
            })

        api_server._start_recheck_worker = fake_start
        try:
            run_id = api_server.TASKS.submit("需要二次回收的网页任务", mode="strategic", seats=["chatgpt", "minimax"])
            api_server.TASKS.update_progress(
                run_id,
                "补跑 1/1：Chrome 固定标签回答轮询：等待 ChatGPT，剩余 1 席，最长等待 427s",
                0.85,
            )
            run_dir = tmp_path / run_id
            run_dir.mkdir(parents=True)
            (run_dir / "trace.json").write_text(json.dumps({
                "run_id": run_id,
                "events": [
                    {
                        "phase": "seat",
                        "action": "chrome_submit_complete",
                        "detail": "chatgpt 提示词已发送",
                        "at": "2026-05-16T15:44:24+00:00",
                        "data": {"seat": "chatgpt"},
                    },
                    {
                        "phase": "seat",
                        "action": "chrome_submit_unconfirmed",
                        "detail": "minimax 未确认提交",
                        "at": "2026-05-16T15:44:40+00:00",
                        "data": {"seat": "minimax", "submit": {"error": "send_button_not_found"}},
                    },
                ],
            }), encoding="utf-8")

            response = api_server.app.test_client().post(f"/api/judge/{run_id}/recheck", json={"seats": ["minimax"]})
        finally:
            api_server._start_recheck_worker = old_start
            api_server.TASKS = old_tasks
            api_server.RUNS_DIR = old_runs_dir

    assert response.status_code == 202
    assert response.get_json()["source_run_id"] == run_id
    assert captured["source_run_id"] == run_id
    assert captured["seats"] == ["minimax"]
    assert captured["task"]["question"] == "需要二次回收的网页任务"


def test_recheck_endpoint_can_resubmit_saved_required_seat():
    api_server = _load_api_server()
    old_tasks = api_server.TASKS
    old_runs_dir = api_server.RUNS_DIR
    old_start_fresh = api_server._start_fresh_recheck_worker
    old_start_supplement = api_server._start_supplement_worker
    captured = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        api_server.TASKS = api_server.TaskManager(db_path=tmp_path / "tasks.sqlite3")
        run_dir = tmp_path / "run-fresh"
        run_dir.mkdir(parents=True)
        (run_dir / "verdict.json").write_text(json.dumps({
            "run_id": "run-fresh",
            "question": "需要 Qwen 重新执行",
            "mode": "strategic",
            "seats": ["chatgpt", "qwen"],
            "web_bridge": {
                "raw_results": [
                    {"seat": "chatgpt", "ok": True, "response": "done"},
                    {
                        "seat": "qwen",
                        "ok": False,
                        "supplementable": True,
                        "error": {"code": "response_not_relevant"},
                    },
                ],
            },
        }), encoding="utf-8")

        def fake_start_fresh(recheck_run_id, source_run_id, seats, notify_config):
            captured.update({
                "recheck_run_id": recheck_run_id,
                "source_run_id": source_run_id,
                "seats": seats,
                "notify_config": notify_config,
            })

        def fail_supplement(*args, **kwargs):  # pragma: no cover - should not be called
            raise AssertionError("fresh recheck must not use read-only supplement worker")

        api_server._start_fresh_recheck_worker = fake_start_fresh
        api_server._start_supplement_worker = fail_supplement
        try:
            response = api_server.app.test_client().post(
                "/api/judge/run-fresh/recheck",
                json={"seats": ["qwen"], "method": "fresh"},
            )
        finally:
            api_server._start_fresh_recheck_worker = old_start_fresh
            api_server._start_supplement_worker = old_start_supplement
            api_server.TASKS = old_tasks
            api_server.RUNS_DIR = old_runs_dir

    data = response.get_json()
    assert response.status_code == 202
    assert data["method"] == "fresh_web_submission"
    assert data["sends_prompt"] is True
    assert captured["source_run_id"] == "run-fresh"
    assert captured["seats"] == ["qwen"]


def test_rescue_endpoint_starts_one_click_rescue_for_saved_required_seats():
    api_server = _load_api_server()
    old_tasks = api_server.TASKS
    old_runs_dir = api_server.RUNS_DIR
    old_start_rescue = api_server._start_rescue_worker
    captured = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        api_server.TASKS = api_server.TaskManager(db_path=tmp_path / "tasks.sqlite3")
        run_dir = tmp_path / "run-rescue"
        run_dir.mkdir(parents=True)
        (run_dir / "verdict.json").write_text(json.dumps({
            "run_id": "run-rescue",
            "question": "需要 MiniMax 修复发送",
            "mode": "strategic",
            "seats": ["chatgpt", "minimax"],
            "web_bridge": {
                "raw_results": [
                    {"seat": "chatgpt", "ok": True, "response": "done"},
                    {
                        "seat": "minimax",
                        "ok": False,
                        "supplementable": True,
                        "error": {"code": "send_button_not_found"},
                    },
                ],
            },
        }), encoding="utf-8")

        def fake_start_rescue(rescue_run_id, source_run_id, seats, notify_config):
            captured.update({
                "rescue_run_id": rescue_run_id,
                "source_run_id": source_run_id,
                "seats": seats,
                "notify_config": notify_config,
            })

        api_server._start_rescue_worker = fake_start_rescue
        try:
            response = api_server.app.test_client().post("/api/judge/run-rescue/rescue")
        finally:
            api_server._start_rescue_worker = old_start_rescue
            api_server.TASKS = old_tasks
            api_server.RUNS_DIR = old_runs_dir

    data = response.get_json()
    assert response.status_code == 202
    assert data["method"] == "read_existing_first_then_targeted_clean_resubmit"
    assert data["sends_prompt"] is True
    assert data["rescue_plan"]["fresh_seats"] == ["minimax"]
    assert captured["source_run_id"] == "run-rescue"
    assert captured["seats"] == ["minimax"]


def test_rescue_worker_reads_existing_first_then_fresh_resubmits_only_remaining(monkeypatch):
    api_server = _load_api_server()
    old_tasks = api_server.TASKS
    old_runs_dir = api_server.RUNS_DIR
    captured = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        api_server.TASKS = api_server.TaskManager(db_path=tmp_path / "tasks.sqlite3")
        source_run_id = "run-rescue-worker"
        run_dir = tmp_path / source_run_id
        run_dir.mkdir(parents=True)
        (run_dir / "verdict.json").write_text(json.dumps({
            "run_id": source_run_id,
            "question": "需要一键救援",
            "deep_prompt": "专业版 prompt",
            "mode": "strategic",
            "seats": ["chatgpt", "qwen", "minimax"],
            "web_bridge": {
                "raw_results": [
                    {"seat": "chatgpt", "ok": True, "response": "ChatGPT done"},
                    {
                        "seat": "qwen",
                        "ok": False,
                        "supplementable": True,
                        "error": {"code": "slow_response_pending"},
                    },
                    {
                        "seat": "minimax",
                        "ok": False,
                        "supplementable": True,
                        "error": {"code": "send_button_not_found"},
                    },
                ],
                "mentor_supplements": [],
                "external_evidence": [],
            },
        }), encoding="utf-8")
        rescue_run_id = api_server.TASKS.submit("一键救援", mode="strategic", seats=["qwen", "minimax"])

        def fake_recover_existing_fixed_tab_answers(**kwargs):
            captured["existing_seats"] = kwargs["seats"]
            return [
                {"seat": "qwen", "ok": True, "response": "Qwen late answer", "error": None},
                {
                    "seat": "minimax",
                    "ok": False,
                    "supplementable": True,
                    "error": {"code": "existing_answer_not_found"},
                },
            ]

        def fake_run_web_jury(**kwargs):
            captured["fresh_seats"] = kwargs["seats"]
            captured["bridge_config_overrides"] = kwargs.get("bridge_config_overrides")
            return {
                "web_bridge": {
                    "raw_results": [
                        {"seat": "minimax", "ok": True, "response": "MiniMax fresh answer", "error": None}
                    ]
                }
            }

        monkeypatch.setattr(api_server, "recover_existing_fixed_tab_answers", fake_recover_existing_fixed_tab_answers)
        monkeypatch.setattr(api_server, "run_web_jury", fake_run_web_jury)
        monkeypatch.setattr(api_server, "_attach_citation_mvp", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_server, "generate_secure_view_url", lambda run_id: f"/view/{run_id}")
        try:
            api_server._run_rescue_worker(
                rescue_run_id,
                source_run_id,
                ["qwen", "minimax"],
                {},
            )
            saved = api_server._load_run(source_run_id)
        finally:
            api_server.TASKS = old_tasks
            api_server.RUNS_DIR = old_runs_dir

    assert captured["existing_seats"] == ["qwen", "minimax"]
    assert captured["fresh_seats"] == ["minimax"]
    assert captured["bridge_config_overrides"]["fresh_conversation_per_run"] is True
    assert saved is not None
    assert saved["rescue"]["existing_recovered_count"] == 1
    assert saved["rescue"]["fresh_recovered_count"] == 1
    assert saved["rescue"]["sends_prompt"] is True
    raw_by_seat = {item["seat"]: item for item in saved["web_bridge"]["raw_results"]}
    assert raw_by_seat["qwen"]["ok"] is True
    assert raw_by_seat["minimax"]["ok"] is True


def test_recheck_worker_reads_only_requested_recovery_seats(monkeypatch):
    api_server = _load_api_server()
    old_tasks = api_server.TASKS
    old_runs_dir = api_server.RUNS_DIR
    captured = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        api_server.TASKS = api_server.TaskManager(db_path=tmp_path / "tasks.sqlite3")
        source_run_id = api_server.TASKS.submit(
            "需要二次回收的网页任务",
            mode="strategic",
            seats=["chatgpt", "qwen", "deepseek"],
        )
        recheck_run_id = api_server.TASKS.submit("回收旧页面答案", mode="strategic", seats=["qwen"])
        task = api_server.TASKS.get_task(source_run_id)

        def fake_recover_existing_fixed_tab_answers(**kwargs):
            captured["recovery_seats"] = kwargs["seats"]
            return [{"seat": "qwen", "ok": False, "response": "", "error": {"code": "existing_answer_not_found"}}]

        def fake_assemble_web_verdict_from_raw_results(**kwargs):
            captured["assembled_seats"] = kwargs["seats"]
            captured["raw_results"] = kwargs["raw_results"]
            return {
                "run_id": kwargs["run_id"],
                "question": kwargs["display_question"],
                "mode": kwargs["mode"],
                "seats": kwargs["seats"],
                "web_bridge": {"raw_results": kwargs["raw_results"], "ok_count": 0, "failed_count": 1},
                "average_score": 0.0,
                "verdict": "insufficient",
                "verdict_label": "信息不足",
                "one_liner": "未回收。",
            }

        monkeypatch.setattr(api_server, "recover_existing_fixed_tab_answers", fake_recover_existing_fixed_tab_answers)
        monkeypatch.setattr(api_server, "assemble_web_verdict_from_raw_results", fake_assemble_web_verdict_from_raw_results)
        monkeypatch.setattr(api_server, "load_bridge_config", lambda: {})
        monkeypatch.setattr(api_server, "_attach_product_run_metadata", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_server, "_attach_citation_mvp", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_server, "generate_secure_view_url", lambda run_id: f"/view/{run_id}")
        try:
            api_server._run_recheck_worker(
                recheck_run_id,
                source_run_id,
                task,
                ["qwen"],
                {},
            )
        finally:
            api_server.TASKS = old_tasks
            api_server.RUNS_DIR = old_runs_dir

    assert captured["recovery_seats"] == ["qwen"]
    assert captured["assembled_seats"] == ["chatgpt", "qwen", "deepseek"]
    assert [item["seat"] for item in captured["raw_results"]] == ["qwen"]


def test_fresh_recheck_worker_resubmits_and_merges_requested_seat(monkeypatch):
    api_server = _load_api_server()
    old_tasks = api_server.TASKS
    old_runs_dir = api_server.RUNS_DIR
    captured = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        api_server.TASKS = api_server.TaskManager(db_path=tmp_path / "tasks.sqlite3")
        source_run_id = "run-fresh-worker"
        run_dir = tmp_path / source_run_id
        run_dir.mkdir(parents=True)
        (run_dir / "verdict.json").write_text(json.dumps({
            "run_id": source_run_id,
            "question": "需要 Qwen 重新执行",
            "deep_prompt": "专业版 prompt",
            "mode": "strategic",
            "seats": ["chatgpt", "qwen"],
            "web_bridge": {
                "raw_results": [
                    {"seat": "chatgpt", "ok": True, "response": "ChatGPT done"},
                    {
                        "seat": "qwen",
                        "ok": False,
                        "supplementable": True,
                        "error": {"code": "response_not_relevant"},
                    },
                ],
                "mentor_supplements": [],
                "external_evidence": [],
            },
        }), encoding="utf-8")
        recheck_run_id = api_server.TASKS.submit("重新提交席位", mode="strategic", seats=["qwen"])

        def fake_run_web_jury(**kwargs):
            captured["fresh_question"] = kwargs["question"]
            captured["fresh_seats"] = kwargs["seats"]
            captured["bridge_config_overrides"] = kwargs.get("bridge_config_overrides")
            return {
                "web_bridge": {
                    "raw_results": [
                        {"seat": "qwen", "ok": True, "response": "Qwen fresh answer", "error": None}
                    ]
                }
            }

        def fake_assemble_web_verdict_from_raw_results(**kwargs):
            captured["assembled_seats"] = kwargs["seats"]
            captured["raw_results"] = kwargs["raw_results"]
            return {
                "run_id": kwargs["run_id"],
                "question": kwargs["display_question"],
                "mode": kwargs["mode"],
                "seats": kwargs["seats"],
                "web_bridge": {"raw_results": kwargs["raw_results"], "ok_count": 2, "failed_count": 0},
                "average_score": 0.7,
                "verdict": "conditional",
                "verdict_label": "条件成立",
                "one_liner": "Qwen 已重新执行。",
            }

        monkeypatch.setattr(api_server, "run_web_jury", fake_run_web_jury)
        monkeypatch.setattr(api_server, "assemble_web_verdict_from_raw_results", fake_assemble_web_verdict_from_raw_results)
        monkeypatch.setattr(api_server, "_attach_product_run_metadata", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_server, "_attach_citation_mvp", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_server, "generate_secure_view_url", lambda run_id: f"/view/{run_id}")
        try:
            api_server._run_fresh_recheck_worker(
                recheck_run_id,
                source_run_id,
                ["qwen"],
                {},
            )
            saved = api_server._load_run(source_run_id)
        finally:
            api_server.TASKS = old_tasks
            api_server.RUNS_DIR = old_runs_dir

    assert captured["fresh_question"] == "专业版 prompt"
    assert captured["fresh_seats"] == ["qwen"]
    assert captured["bridge_config_overrides"]["fresh_conversation_per_run"] is True
    assert captured["assembled_seats"] == ["chatgpt", "qwen"]
    assert [item["seat"] for item in captured["raw_results"]] == ["chatgpt", "qwen"]
    qwen = captured["raw_results"][1]
    assert qwen["ok"] is True
    assert qwen["recovered_by_supplement"] is True
    assert saved is not None
    assert saved["recheck"]["method"] == "fresh_web_submission"
    assert saved["recheck"]["sends_prompt"] is True


def test_attach_citation_mvp_adds_replay_ledger_and_gap_suggestions():
    api_server = _load_api_server()
    verdict = {
        "run_id": "run-cite",
        "question": "升级 AI Judge",
        "web_bridge": {
            "raw_results": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "response": "引用验证 MVP 参考 https://example.com/report 。",
                }
            ],
            "mentor_supplements": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "response": "导师补充：Replay Ledger 保留原文。",
                }
            ],
            "external_evidence": [
                {"url": "https://example.com/report", "title": "AI Judge 引用验证 MVP report", "snippet": "引用验证 MVP"}
            ],
        },
    }

    report = api_server._attach_citation_mvp(verdict, run_id="run-cite")

    assert report["certification_id"].startswith("CITE-")
    assert verdict["web_bridge"]["certification_id"] == report["certification_id"]
    assert verdict["web_bridge"]["replay_ledger"][0]["raw_answer"].startswith("引用验证 MVP")
    assert verdict["web_bridge"]["evidence_gap_suggestions"]["will_rewrite_body"] is False
    assert verdict["web_bridge"]["evidence_broker"]["counts"]["user_supplied"] == 1
    assert verdict["web_bridge"]["blind_cross_validation"]["status"] == "pending_model_reviews"
    assert report["evidence_gap_queue"]["schema"] == "evidence_gap_queue.v1"
    assert report["eval_case"]["case_id"].startswith("EVAL-")


def test_evidence_os_api_endpoints_update_saved_run():
    api_server = _load_api_server()
    old_runs_dir = api_server.RUNS_DIR
    old_tasks = api_server.TASKS
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        api_server.TASKS = api_server.TaskManager(db_path=tmp_path / "tasks.sqlite3")
        try:
            verdict = {
                "run_id": "run-api",
                "question": "AI Judge",
                "web_bridge": {
                    "raw_results": [{"seat": "chatgpt", "ok": True, "response": "无引用回答。"}],
                    "mentor_supplements": [],
                    "external_evidence": [],
                },
            }
            api_server._attach_citation_mvp(verdict, run_id="run-api")
            api_server._save_run("run-api", verdict)
            client = api_server.app.test_client()

            gaps = client.get("/api/judge/run-api/evidence-gaps")
            assert gaps.status_code == 200
            task_id = gaps.get_json()["tasks"][0]["task_id"]

            resolved = client.post(
                f"/api/judge/run-api/evidence-gaps/{task_id}/resolve",
                json={"resolution": "补充外部证据", "evidence_id": "EVID-1"},
            )
            assert resolved.status_code == 200
            assert resolved.get_json()["evidence_gap_queue"]["open_count"] == 0

            blind = client.post(
                "/api/judge/run-api/blind-review",
                json={"reviews": [
                    {"reviewer": "gemini", "citation_id": "CITE-000", "decision": "confirm"},
                    {"reviewer": "qwen", "citation_id": "CITE-000", "decision": "confirm"},
                ]},
            )
            assert blind.status_code == 200
            assert blind.get_json()["blind_cross_validation"]["result"]["confirmed_count"] == 1

            signed = client.post(
                "/api/judge/run-api/human-review",
                json={"reviewer": "Auditor", "decision": "conditional", "reason": "我确认该结果仍需补充外部证据再发布，并保留人工复核记录。"},
            )
            assert signed.status_code == 200
            assert signed.get_json()["human_review_status"]["status"] == "signed"
        finally:
            api_server.RUNS_DIR = old_runs_dir
            api_server.TASKS = old_tasks
