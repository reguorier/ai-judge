from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_api_server():
    module_path = Path(__file__).resolve().parents[2] / "product" / "api_server.py"
    spec = importlib.util.spec_from_file_location("api_server_blocker_repair_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_report_normalizes_dict_shaped_expected_seats(monkeypatch, tmp_path):
    api_server = _load_api_server()
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-dict-seats"
    run_dir.mkdir(parents=True)
    (run_dir / "verdict.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "question": "dict seat regression",
                "seats": [{"seat": "doubao"}, {"id": "yuanbao"}],
                "seat_scores": [{"seat": "doubao", "verdict": "ok"}],
                "web_bridge": {"raw_results": [{"seat": "yuanbao", "response": "ok"}]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api_server, "RUNS_DIR", runs_dir)

    response = api_server.app.test_client().get("/api/runs/run-dict-seats/report")
    data = response.get_json()

    assert response.status_code == 200
    assert data["ok"] is True
    assert data["seats"]["expected"] == 2
    assert data["seats"]["completed"] == 2
    assert data["seats"]["timeout"] == 0
    assert "business_report" in data
    assert "runtime_trace" in data
    assert "bridge_diagnostics" in data
    assert "raw_seat_outputs" in data
    assert "artifacts" in data
    assert data["business_report"]["question"] == "dict seat regression"


def test_run_report_pending_state_is_structured(monkeypatch, tmp_path):
    api_server = _load_api_server()
    runs_dir = tmp_path / "runs"
    (runs_dir / "run-pending").mkdir(parents=True)
    monkeypatch.setattr(api_server, "RUNS_DIR", runs_dir)

    response = api_server.app.test_client().get("/api/runs/run-pending/report")
    data = response.get_json()

    assert response.status_code == 202
    assert data["ok"] is False
    assert data["error"] == "report_pending"
    assert data["reason"]
    assert data["next_action"]
    assert data["status"] == 202
    assert data["trace_id"].startswith("run-report-")
    assert data["source"] == "run_report"


def test_release_status_exposes_actionable_drift_details(monkeypatch, tmp_path):
    api_server = _load_api_server()
    runs_dir = tmp_path / "runs"
    release_dir = tmp_path / "release" / "P3.8.14-RC1"
    product_dir = tmp_path / "product"
    runs_dir.mkdir(parents=True)
    release_dir.mkdir(parents=True)
    product_dir.mkdir(parents=True)
    (tmp_path / "release" / "current.lock").write_text(
        json.dumps(
            {
                "release_id": "P3.8.14-RC1",
                "sealed": True,
                "manifest": "release/P3.8.14-RC1/manifest.json",
            }
        ),
        encoding="utf-8",
    )
    (product_dir / "api_server.py").write_text("changed", encoding="utf-8")
    (release_dir / "manifest.json").write_text(
        json.dumps(
            {
                "release_id": "P3.8.14-RC1",
                "sealed": True,
                "files": [{"file_path": "product/api_server.py", "sha256": "0" * 64}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api_server, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(api_server, "_PROJECT_ROOT", tmp_path)

    response = api_server.app.test_client().get("/api/release/status")
    data = response.get_json()

    assert response.status_code == 200
    assert data["integrity"] == "fail"
    assert data["drift_detected"] is True
    assert data["drift_files"] == ["product/api_server.py"]
    assert data["missing_files"] == []
    assert data["failed_checks"][0]["check"] == "manifest_hash_match"
    assert data["next_action"] == "reconcile_active_runtime_with_release_manifest_or_reseal_after_review"
    assert data["runtime_source"] == str(tmp_path)
    assert data["trace_id"].startswith("release-status-")


def test_task_api_accepts_list_shaped_trace_for_completed_task(monkeypatch, tmp_path):
    api_server = _load_api_server()
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "client-list-trace"
    run_dir.mkdir(parents=True)
    (run_dir / "trace.json").write_text(
        json.dumps(
            [
                {
                    "run_id": "client-list-trace",
                    "events": [
                        {
                            "phase": "seat",
                            "action": "chrome_response_timeout",
                            "detail": "doubao 提交超时",
                            "data": {"seat": "doubao", "code": "slow_response_pending"},
                            "at": "2026-06-09T00:00:00+00:00",
                        }
                    ],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    task_db = tmp_path / "tasks.db"
    tasks = api_server.TaskManager(task_db)
    tasks.submit("list trace regression", mode="flash", seats=["doubao"], run_id="client-list-trace")
    tasks.complete("client-list-trace", {"run_id": "client-list-trace", "verdict": "ok"})
    monkeypatch.setattr(api_server, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(api_server, "TASKS", tasks)

    response = api_server.app.test_client().get("/api/task/client-list-trace")
    data = response.get_json()

    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    assert data["ok"] is True
    assert data["status"] == "complete"
    assert data["progress_diagnostics"]["seats"][0]["code"] == "slow_response_pending"
    assert data["trace_id"].startswith("task-api-")
    assert data["source"] == "task_api"


def test_task_api_recovers_completed_run_when_task_row_missing(monkeypatch, tmp_path):
    api_server = _load_api_server()
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "client-recovered"
    run_dir.mkdir(parents=True)
    (run_dir / "verdict.json").write_text(
        json.dumps({"run_id": "client-recovered", "status": "complete", "verdict": "ok"}, ensure_ascii=False),
        encoding="utf-8",
    )
    task_db = tmp_path / "tasks.db"
    monkeypatch.setattr(api_server, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(api_server, "TASKS", api_server.TaskManager(task_db))

    response = api_server.app.test_client().get("/api/task/client-recovered")
    data = response.get_json()

    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    assert data["ok"] is True
    assert data["status"] == "complete"
    assert data["recovered"] is True
    assert data["report_url"] == "/api/runs/client-recovered/report"
    assert data["reason"]
    assert data["next_action"]


def test_run_api_recovers_completed_run_from_verdict_after_restart(monkeypatch, tmp_path):
    api_server = _load_api_server()
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "client-room-recovered"
    run_dir.mkdir(parents=True)
    (run_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    (run_dir / "verdict.json").write_text(
        json.dumps(
            {
                "run_id": "client-room-recovered",
                "question": "room recovery",
                "status": "complete",
                "mode": "flash",
                "seats": [{"seat": "doubao", "seat_name": "Doubao"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api_server, "RUNS_DIR", runs_dir)

    response = api_server.app.test_client().get("/api/runs/client-room-recovered")
    data = response.get_json()

    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    assert data["run"]["run_id"] == "client-room-recovered"
    assert data["run"]["phase"] == "completed"
    assert data["run"]["progress"] == 1.0
    assert data["run"]["recovered"] is True
    assert data["run"]["metadata"]["question"] == "room recovery"
    assert data["run"]["metadata"]["seats"] == ["doubao"]
    assert data["run"]["artifacts"][0]["url"] == "/api/runs/client-room-recovered/index.html"


def test_task_api_missing_run_returns_structured_json(monkeypatch, tmp_path):
    api_server = _load_api_server()
    monkeypatch.setattr(api_server, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(api_server, "TASKS", api_server.TaskManager(tmp_path / "tasks.db"))

    response = api_server.app.test_client().get("/api/task/not-a-real-run")
    data = response.get_json()

    assert response.status_code == 404
    assert response.content_type.startswith("application/json")
    assert data["ok"] is False
    assert data["status"] == "run_not_found"
    assert data["run_id"] == "not-a-real-run"
    assert data["reason"]
    assert data["next_action"]
    assert data["trace_id"].startswith("task-api-")
    assert data["recoverable"] is False


def test_task_api_bridge_busy_failure_is_structured(monkeypatch, tmp_path):
    api_server = _load_api_server()
    task_db = tmp_path / "tasks.db"
    tasks = api_server.TaskManager(task_db)
    tasks.submit("bridge busy regression", mode="flash", seats=["doubao"], run_id="client-bridge-busy")
    tasks.fail(
        "client-bridge-busy",
        json.dumps(
            {
                "status": "bridge_busy",
                "reason": "固定 Chrome 桥接正在被其他流程使用，本轮没有提交新问题。",
                "next_action": "等待当前流程结束后重试。",
                "trace_id": "task-api-test",
                "seat": "doubao",
                "bridge": "chrome_cdp",
                "recoverable": True,
            },
            ensure_ascii=False,
        ),
    )
    monkeypatch.setattr(api_server, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(api_server, "TASKS", tasks)

    response = api_server.app.test_client().get("/api/task/client-bridge-busy")
    data = response.get_json()

    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    assert data["ok"] is False
    assert data["status"] == "failed"
    assert data["failure_status"] == "bridge_busy"
    assert data["reason"].startswith("固定 Chrome 桥接")
    assert data["next_action"]
    assert data["bridge_diagnostics"]["status"] == "bridge_busy"
    assert data["bridge_diagnostics"]["seat"] == "doubao"
    assert data["bridge_diagnostics"]["bridge"] == "chrome_cdp"
    assert data["bridge_diagnostics"]["recoverable"] is True
