#!/usr/bin/env bash
set -euo pipefail
TMP_DIR="$(mktemp -d)"
export PYTHONPATH=.
export PYTHONDONTWRITEBYTECODE=1
export AI_JUDGE_REPORTS_ROOT="$TMP_DIR/reports"
python3 - <<'PY'
try:
    from flask import Flask
except ModuleNotFoundError:
    Flask = None

if Flask is not None:
    from product.client_api import client_blueprint

    app = Flask(__name__)
    app.register_blueprint(client_blueprint)
    client = app.test_client()
    created = client.post("/api/client/runs", json={"question": "run control smoke", "mode": "deep_judge", "auto_complete": False})
    if created.status_code != 201:
        raise SystemExit(f"create failed: {created.status_code} {created.get_data(as_text=True)}")
    run = created.get_json()["run"]
    run_id = run["run_id"]
    status = client.get(f"/api/client/runs/{run_id}").get_json()
    if status["status"] != "running" or not status["controls"]["can_pause"]:
        raise SystemExit(f"bad initial status: {status}")
    paused = client.post(f"/api/client/runs/{run_id}/pause").get_json()
    if paused["status"] != "paused" or not paused["controls"]["can_resume"]:
        raise SystemExit(f"pause failed: {paused}")
    resumed = client.post(f"/api/client/runs/{run_id}/resume").get_json()
    if resumed["status"] != "running" or not resumed["controls"]["can_stop"]:
        raise SystemExit(f"resume failed: {resumed}")
    stopped = client.post(f"/api/client/runs/{run_id}/stop").get_json()
    if stopped["status"] != "cancelled" or stopped["controls"]["can_stop"]:
        raise SystemExit(f"stop failed: {stopped}")
else:
    from product.run_orchestrator import create_client_run, load_summary, pause_client_run, resume_client_run, stop_client_run

    run = create_client_run(question="run control smoke", mode="deep_judge", auto_complete=False)
    run_id = run["run_id"]
    status = load_summary(run_id)
    if status["status"] != "running" or not status["controls"]["can_pause"]:
        raise SystemExit(f"bad initial status: {status}")
    paused = pause_client_run(run_id)
    if paused["status"] != "paused" or not paused["controls"]["can_resume"]:
        raise SystemExit(f"pause failed: {paused}")
    resumed = resume_client_run(run_id)
    if resumed["status"] != "running" or not resumed["controls"]["can_stop"]:
        raise SystemExit(f"resume failed: {resumed}")
    stopped = stop_client_run(run_id)
    if stopped["status"] != "cancelled" or stopped["controls"]["can_stop"]:
        raise SystemExit(f"stop failed: {stopped}")

print("[PASS] run status is real backend status")
print("[PASS] pause/resume/stop are real backend controls")
PY
