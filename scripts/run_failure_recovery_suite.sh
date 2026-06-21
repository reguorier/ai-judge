#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# run_failure_recovery_suite.sh
# ─────────────────────────────────────────────────────────────────────
# Runs 6 failure scenario tests and validates recovery behavior.
#
# Scenarios:
#   1. search-agent timeout      → degraded/failed
#   2. no reasoning source       → failed, reason=deep_judge_no_substantive_reasoning
#   3. renderer validation fail  → blocked
#   4. artifact write fail       → failed/retry
#   5. seat partial failure      → completed_with_warnings/degraded
#   6. followup no source        → not_generated
#
# Exit codes:
#   0 = DEEP_JUDGE_FAILURE_RECOVERY_SUITE_PASS
#   1 = DEEP_JUDGE_FAILURE_RECOVERY_SUITE_FAIL
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECOVERY_VALIDATOR="$PROJECT_ROOT/runtime/product/observability/recovery_validator.py"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"

# ── Colors ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Define 6 failure scenarios with expected results ────────────────
SCENARIOS_JSON=$(cat <<'EOF'
{
  "scenarios": {
    "search_timeout": {
      "status": "degraded",
      "reason": null
    },
    "no_reasoning_source": {
      "status": "failed",
      "reason": "deep_judge_no_substantive_reasoning"
    },
    "renderer_validation_fail": {
      "status": "blocked",
      "reason": null
    },
    "artifact_write_fail": {
      "status": "failed",
      "reason": null
    },
    "seat_partial_failure": {
      "status": "completed_with_warnings",
      "reason": null
    },
    "followup_no_source": {
      "status": "not_generated",
      "reason": null
    }
  }
}
EOF
)

# ── Run validation ──────────────────────────────────────────────────
log_info "Running failure recovery validation..."

if [[ ! -f "$RECOVERY_VALIDATOR" ]]; then
    log_error "Recovery validator not found: $RECOVERY_VALIDATOR"
    exit 1
fi

RESULT=$("$VENV_PYTHON" "$RECOVERY_VALIDATOR" "$SCENARIOS_JSON" 2>&1)
EXIT_CODE=$?

log_info "Validator output:"
echo "$RESULT" | "$VENV_PYTHON" -m json.tool 2>/dev/null || echo "$RESULT"

# ── Parse results ───────────────────────────────────────────────────
PASSED=$(echo "$RESULT" | "$VENV_PYTHON" -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('scenarios_passed', 0))
except:
    print(0)
" 2>/dev/null || echo "0")
FAILED=$(echo "$RESULT" | "$VENV_PYTHON" -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('scenarios_failed', 0))
except:
    print(0)
" 2>/dev/null || echo "0")

# ── Final output ────────────────────────────────────────────────────
echo ""
echo "========================================"
if [[ "$EXIT_CODE" -eq 0 && "$FAILED" -eq 0 ]]; then
    echo -e "${GREEN}DEEP_JUDGE_FAILURE_RECOVERY_SUITE_PASS${NC}"
    exit 0
else
    echo -e "${RED}DEEP_JUDGE_FAILURE_RECOVERY_SUITE_FAIL${NC}"
    echo ""
    echo "Scenarios passed: $PASSED / 6"
    echo "Scenarios failed: $FAILED / 6"

    # Show failed scenarios
    echo "$RESULT" | "$VENV_PYTHON" -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for r in data.get('results', []):
        if not r.get('passed', False):
            print(f\"  FAIL: {r['scenario']} — {r.get('detail', '')}\")
except Exception as e:
    print(f'  Error parsing results: {e}')
" 2>/dev/null

    exit 1
fi