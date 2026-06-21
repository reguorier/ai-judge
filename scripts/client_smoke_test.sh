#!/usr/bin/env bash
set -euo pipefail

API_BASE="${AI_JUDGE_API_BASE:-http://127.0.0.1:8501}"
TMP_DIR="$(mktemp -d)"

HEALTH_JSON="$TMP_DIR/health.json"
CAP_JSON="$TMP_DIR/capabilities.json"
CREATE_JSON="$TMP_DIR/create.json"
DETAIL_JSON="$TMP_DIR/detail.json"
REPORT_JSON="$TMP_DIR/report.json"

curl_json_status() {
  local output_path="$1"
  shift
  local status=""
  local err_path="${output_path}.curl.err"
  for _attempt in 1 2 3 4 5; do
    if status="$(curl --noproxy "*" -sS -o "$output_path" -w "%{http_code}" "$@" 2>"$err_path")"; then
      printf "%s" "$status"
      return 0
    fi
    if status="$(curl -sS -o "$output_path" -w "%{http_code}" "$@" 2>"$err_path")"; then
      printf "%s" "$status"
      return 0
    fi
    sleep 0.2
  done
  cat "$err_path" >&2 || true
  printf "000"
  return 1
}

HEALTH_STATUS="$(curl_json_status "$HEALTH_JSON" "$API_BASE/api/health")"
CAP_STATUS="$(curl_json_status "$CAP_JSON" "$API_BASE/api/client/capabilities")"
CREATE_STATUS="$(curl_json_status "$CREATE_JSON" \
  -H "Content-Type: application/json" \
  -d '{"question":"CODEX client smoke: create real reviewer-visible run state","mode":"quick_judge","engine":"local","auto_complete":false}' \
  "$API_BASE/api/client/runs")"

RUN_ID="$(python3 - "$CREATE_JSON" <<'PY'
import json
import sys
data = json.loads(open(sys.argv[1], encoding="utf-8").read())
run = data.get("run") or {}
print(run.get("run_id") or data.get("run_id") or "")
PY
)"

if [[ -z "$RUN_ID" ]]; then
  echo "[FAIL] create_run did not return run_id"
  cat "$CREATE_JSON"
  exit 1
fi

DETAIL_STATUS="$(curl_json_status "$DETAIL_JSON" "$API_BASE/api/client/runs/$RUN_ID")"
REPORT_STATUS="$(curl_json_status "$REPORT_JSON" "$API_BASE/api/client/runs/$RUN_ID/report")"

export HEALTH_STATUS CAP_STATUS CREATE_STATUS DETAIL_STATUS REPORT_STATUS
export HEALTH_JSON CAP_JSON CREATE_JSON DETAIL_JSON REPORT_JSON RUN_ID

python3 <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

FORBIDDEN_MARKERS = {
    "FULL_RELEASE_PASS",
    "PRODUCT_FLOW_PASS",
    "REPORT_PROBLEM_RESOLVED",
    "HIGH_RISK_REPORT_FIXED",
}


def load_json(env_name: str) -> dict:
    path = Path(os.environ[env_name])
    try:
        return json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[FAIL] invalid_json file={path} reason={exc}")


def status(env_name: str) -> int:
    return int(os.environ[env_name])


def assert_true(condition: bool, message: str, detail: object = "") -> None:
    if not condition:
        raise SystemExit(f"[FAIL] {message}: {detail}")


health = load_json("HEALTH_JSON")
assert_true(status("HEALTH_STATUS") == 200 and health.get("status") == "ok", "health endpoint not ok", health)
print(f"[PASS] health endpoint version={health.get('version')}")

capabilities = load_json("CAP_JSON")
assert_true(status("CAP_STATUS") == 200 and capabilities.get("canStartRun") is True, "client cannot start run", capabilities)
print("[PASS] client capabilities canStartRun=true")

created = load_json("CREATE_JSON")
run = created.get("run") or {}
run_id = os.environ["RUN_ID"]
assert_true(status("CREATE_STATUS") in {200, 201} and run_id, "create_run did not return run_id", created)
assert_true(not run_id.startswith("demo-"), "create_run returned demo run_id", run_id)
print(f"[PASS] create_run returned run_id={run_id}")

detail = load_json("DETAIL_JSON")
detail_run_id = (detail.get("run") or {}).get("run_id") or detail.get("runId") or detail.get("run_id")
detail_run_status = (detail.get("run") or {}).get("status") or detail.get("status")
assert_true(status("DETAIL_STATUS") == 200 and detail_run_id == run_id, "run state unreadable", detail)
print(f"[PASS] run state readable status={detail_run_status}")

report = load_json("REPORT_JSON")
report_state = report.get("error") or report.get("status") or report.get("verdict_status")
assert_true(status("REPORT_STATUS") in {200, 202, 404}, "report status unreadable", report)
assert_true(status("REPORT_STATUS") != 500, "report endpoint returned 500", report)
print(f"[PASS] report status readable http={status('REPORT_STATUS')} state={report_state}")

serialized = json.dumps({"health": health, "created": created, "detail": detail, "report": report}, ensure_ascii=False)
for marker in FORBIDDEN_MARKERS:
    assert_true(marker not in serialized, "forbidden marker leaked", marker)
print("[PASS] no forbidden full-pass marker leaked")
PY
