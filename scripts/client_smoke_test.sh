#!/usr/bin/env bash
set -euo pipefail
TMP_DIR="$(mktemp -d)"
export PYTHONPATH=.
export PYTHONDONTWRITEBYTECODE=1
export AI_JUDGE_REPORTS_ROOT="$TMP_DIR/reports"
export AI_JUDGE_OBSIDIAN_DIR="$TMP_DIR/missing-vault"
python3 client/ai_judge_client.py --smoke --followup "把报告压缩成给普通人的摘要" --archive
