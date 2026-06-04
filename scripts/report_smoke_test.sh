#!/usr/bin/env bash
set -euo pipefail
TMP_DIR="$(mktemp -d)"
export PYTHONPATH=.
export PYTHONDONTWRITEBYTECODE=1
export AI_JUDGE_REPORTS_ROOT="$TMP_DIR/reports"
python3 - <<'PY'
from pathlib import Path
from product.run_orchestrator import create_client_run
from product.reporting.report_schema import REPORT_SECTION_TITLES

run = create_client_run(question="检查本轮修改是否破坏现有 AI Judge Core，并给出是否 release-ready。", mode="ops_check")
run_dir = Path(run["final_report_path"]).parent
required = ["final_report.md", "final_report.html", "summary.json", "evidence_packet.json", "seat_matrix.json", "operator_note.md"]
missing = [name for name in required if not (run_dir / name).exists()]
if missing:
    raise SystemExit(f"missing report files: {missing}")
markdown = (run_dir / "final_report.md").read_text(encoding="utf-8")
for index, title in enumerate(REPORT_SECTION_TITLES, start=1):
    marker = f"## {index}. {title}"
    if marker not in markdown:
        raise SystemExit(f"missing report section: {marker}")
if not (run_dir.parent.parent / "latest.md").exists():
    raise SystemExit("latest.md not generated")
print("[PASS] final_report.md generated")
print("[PASS] final_report.html generated")
print("[PASS] summary.json generated")
print("[PASS] evidence_packet.json generated")
print("[PASS] seat_matrix.json generated")
PY
