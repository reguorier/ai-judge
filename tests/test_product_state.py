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

    assert verdict["chief_judge"]["id"] == "deepseek"
    assert verdict["seat_roster"]["selected"] == ["chatgpt", "deepseek"]
    assert verdict["seat_roster"]["abstained"] == ["grok"]
    assert verdict["judge_answer"]["label"] == "DeepSeek 轮值主审"
    assert "本轮主审：DeepSeek" in verdict["judge_answer"]["answer"]
    assert verdict["single_judge_baseline"]["label"] == "DeepSeek 单模型对照"
    assert verdict["roster_sensitivity"]


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
