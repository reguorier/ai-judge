#!/usr/bin/env bash
set -euo pipefail
TMP_DIR="$(mktemp -d)"
export PYTHONPATH=.
export PYTHONDONTWRITEBYTECODE=1
export AI_JUDGE_REPORTS_ROOT="$TMP_DIR/reports"
python3 - <<'PY'
from pathlib import Path
from product.run_orchestrator import archive_client_run, create_client_run, followup_client_run

run = create_client_run(question="归档 smoke：最终报告应该可追问并可归档。", mode="quick_judge")
followup = followup_client_run(run["run_id"], "下一步怎么做")
if not Path(followup["followup_path"]).exists():
    raise SystemExit("followup note missing")
archive = archive_client_run(run["run_id"], vault_dir=Path("/path/that/does/not/exist"))
if archive["status"] != "pending_local" or not Path(archive["archive_path"]).exists():
    raise SystemExit(f"archive fallback failed: {archive}")
print("[PASS] followup note generated")
print("[PASS] archive graceful fallback works")
PY
