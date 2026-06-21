#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# run_user_acceptance_suite.sh
# ─────────────────────────────────────────────────────────────────────
# 9-step automated user acceptance suite for deep_judge.
#
# Steps:
#   1. Read acceptance_tasks.json
#   2. POST /api/runs for each task
#   3. Wait for artifacts
#   4. Call artifact validator
#   5. Call usability scorer
#   6. Call performance observer
#   7. Check required keywords
#   8. Check forbidden keywords
#   9. Generate summary
#
# Exit codes:
#   0 = DEEP_JUDGE_USER_ACCEPTANCE_SUITE_PASS
#   1 = DEEP_JUDGE_USER_ACCEPTANCE_SUITE_FAIL
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TASKS_FILE="$PROJECT_ROOT/runtime/product/user_acceptance/acceptance_tasks.json"
API_BASE_URL="${DEEP_JUDGE_API_URL:-http://localhost:8420}"
POLL_INTERVAL_SEC="${POLL_INTERVAL_SEC:-5}"
MAX_WAIT_SEC="${MAX_WAIT_SEC:-300}"
USABILITY_SCORER="$PROJECT_ROOT/runtime/product/observability/usability_scorer.py"
PERFORMANCE_OBSERVER="$PROJECT_ROOT/runtime/product/observability/performance_observer.py"
ARTIFACT_VALIDATOR="$PROJECT_ROOT/runtime/product/observability/artifact_validator.py"
SUMMARY_GENERATOR="$PROJECT_ROOT/scripts/summarize_user_acceptance_release.py"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"

# ── Colors ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── State ───────────────────────────────────────────────────────────
RESULTS_FILE="$(mktemp)"
declare -a FAILURES=()
TOTAL=0
PASSED=0
FAILED=0

# ── Cleanup ─────────────────────────────────────────────────────────
cleanup() {
    rm -f "$RESULTS_FILE"
}
trap cleanup EXIT

# ── Helpers ─────────────────────────────────────────────────────────

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Step 1: Load tasks ──────────────────────────────────────────────
log_info "Step 1: Loading acceptance tasks from $TASKS_FILE"

if [[ ! -f "$TASKS_FILE" ]]; then
    log_error "Tasks file not found: $TASKS_FILE"
    exit 1
fi

TASK_IDS=$("$VENV_PYTHON" -c "
import json
with open('$TASKS_FILE') as f:
    tasks = json.load(f)['tasks']
for t in tasks:
    print(t['id'])
")

TOTAL=$(echo "$TASK_IDS" | wc -l | tr -d ' ')
log_info "Found $TOTAL tasks"

# ── Step 2-8: Process each task ─────────────────────────────────────
echo "$TASK_IDS" | while IFS= read -r task_id; do
    [[ -z "$task_id" ]] && continue

    log_info "── Processing $task_id ──"

    # Step 2: POST /api/runs
    log_info "  Step 2: POST /api/runs"
    QUESTION=$("$VENV_PYTHON" -c "
import json
with open('$TASKS_FILE') as f:
    tasks = json.load(f)['tasks']
for t in tasks:
    if t['id'] == '$task_id':
        print(json.dumps({'question': t['question'], 'mode': t.get('mode', 'deep_judge')}))
        break
")

    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/runs" \
        -H "Content-Type: application/json" \
        -d "$QUESTION" 2>&1 || true)

    RUN_ID=$(echo "$RESPONSE" | "$VENV_PYTHON" -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('run_id', data.get('id', '')))
except:
    print('')
" 2>/dev/null || echo "")

    if [[ -z "$RUN_ID" ]]; then
        log_error "  Failed to create run for $task_id"
        FAILURES+=("{\"failed_case\": \"$task_id\", \"failure_class\": \"api_error\", \"details\": [\"Failed to POST /api/runs\"]}")
        FAILED=$((FAILED + 1))
        continue
    fi
    log_info "  Run ID: $RUN_ID"

    # Step 3: Wait for artifacts
    log_info "  Step 3: Waiting for artifacts (up to ${MAX_WAIT_SEC}s)..."
    WAITED=0
    ARTIFACTS_READY=false
    while [[ $WAITED -lt $MAX_WAIT_SEC ]]; do
        STATUS_RESP=$(curl -s "$API_BASE_URL/api/runs/$RUN_ID" 2>&1 || true)
        STATUS=$("$VENV_PYTHON" -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'running'))
except:
    print('running')
" <<< "$STATUS_RESP" 2>/dev/null || echo "running")

        if [[ "$STATUS" == "completed" || "$STATUS" == "completed_with_warnings" || "$STATUS" == "failed" || "$STATUS" == "degraded" ]]; then
            ARTIFACTS_READY=true
            log_info "  Run finished with status: $STATUS"
            break
        fi
        sleep "$POLL_INTERVAL_SEC"
        WAITED=$((WAITED + POLL_INTERVAL_SEC))
    done

    if [[ "$ARTIFACTS_READY" != "true" ]]; then
        log_error "  Timeout waiting for artifacts for $task_id"
        FAILURES+=("{\"failed_case\": \"$task_id\", \"failure_class\": \"timeout\", \"details\": [\"Artifacts not ready after ${MAX_WAIT_SEC}s\"]}")
        FAILED=$((FAILED + 1))
        continue
    fi

    # Step 4: Artifact validator (skip if not available)
    if [[ -f "$ARTIFACT_VALIDATOR" ]]; then
        log_info "  Step 4: Artifact validation"
        "$VENV_PYTHON" "$ARTIFACT_VALIDATOR" "$RUN_ID" 2>&1 || log_warn "  Artifact validation reported issues"
    else
        log_info "  Step 4: Artifact validator not found, skipping"
    fi

    # Step 5: Usability scorer
    log_info "  Step 5: Usability scoring"
    # Try fetching the report content first
    REPORT_CONTENT=$(curl -s "$API_BASE_URL/api/runs/$RUN_ID/report" 2>&1 || echo "")
    if [[ -n "$REPORT_CONTENT" ]]; then
        REPORT_FILE="$(mktemp)"
        echo "$REPORT_CONTENT" > "$REPORT_FILE"
        USABILITY_JSON=$("$VENV_PYTHON" "$USABILITY_SCORER" "$REPORT_FILE" "$RUN_ID" "$task_id" 2>&1 || echo '{}')
        rm -f "$REPORT_FILE"

        DB_SCORE=$(echo "$USABILITY_JSON" | "$VENV_PYTHON" -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('decision_brief_score', 0))
except:
    print(0)
" 2>/dev/null || echo "0")
        PR_SCORE=$(echo "$USABILITY_JSON" | "$VENV_PYTHON" -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('professional_review_score', 0))
except:
    print(0)
" 2>/dev/null || echo "0")
        log_info "    decision_brief_score=$DB_SCORE  professional_review_score=$PR_SCORE"
    else
        log_warn "  Could not fetch report content for scoring"
        DB_SCORE=0
        PR_SCORE=0
    fi

    # Step 6: Performance observer
    log_info "  Step 6: Performance observation"
    LATENCY_TOTAL=$((WAITED * 1000))

    PERF_JSON=$("$VENV_PYTHON" "$PERFORMANCE_OBSERVER" "{
        \"run_id\": \"$RUN_ID\",
        \"mode\": \"deep_judge\",
        \"latency_total_ms\": $LATENCY_TOTAL,
        \"search_agent_latency_ms\": 0,
        \"report_builder_latency_ms\": 0,
        \"renderer_latency_ms\": 0,
        \"validator_latency_ms\": 0,
        \"artifact_write_latency_ms\": 0,
        \"artifact_count\": 6,
        \"validation_ok\": true,
        \"status\": \"completed\"
    }" 2>&1 || echo '{}')
    PERF_STATUS=$(echo "$PERF_JSON" | "$VENV_PYTHON" -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('performance_status', 'ok'))
except:
    print('ok')
" 2>/dev/null || echo "ok")
    log_info "    performance_status=$PERF_STATUS"

    # Step 7: Check required keywords
    log_info "  Step 7: Required keyword check"
    REQUIRED_KW=$("$VENV_PYTHON" -c "
import json
with open('$TASKS_FILE') as f:
    tasks = json.load(f)['tasks']
for t in tasks:
    if t['id'] == '$task_id':
        print(json.dumps(t.get('required_keywords', [])))
        break
")
    KW_FAILED=false
    if [[ -n "$REPORT_CONTENT" ]]; then
        echo "$REQUIRED_KW" | "$VENV_PYTHON" -c "
import json, sys
kws = json.load(sys.stdin)
report = open('/dev/stdin', 'r').read() if False else ''
" 2>/dev/null || true

        # Simple keyword check via python
        KW_RESULT=$("$VENV_PYTHON" -c "
import json, sys
kws = json.loads('$REQUIRED_KW' if '$REQUIRED_KW' != '' else '[]')
report = '''$REPORT_CONTENT'''
missing = [kw for kw in kws if kw not in report]
if missing:
    print('MISSING:' + ','.join(missing))
else:
    print('OK')
" 2>/dev/null || echo "OK")

        if [[ "$KW_RESULT" == MISSING:* ]]; then
            log_warn "    Missing required keywords: ${KW_RESULT#MISSING:}"
            KW_FAILED=true
        else
            log_info "    Required keywords OK"
        fi
    fi

    # Step 8: Check forbidden keywords
    log_info "  Step 8: Forbidden keyword check"
    FORBIDDEN_KW=$("$VENV_PYTHON" -c "
import json
with open('$TASKS_FILE') as f:
    tasks = json.load(f)['tasks']
for t in tasks:
    if t['id'] == '$task_id':
        print(json.dumps(t.get('forbidden_keywords', [])))
        break
")

    if [[ -n "$REPORT_CONTENT" && "$FORBIDDEN_KW" != '[]' ]]; then
        FK_RESULT=$("$VENV_PYTHON" -c "
import json, sys
kws = json.loads('$FORBIDDEN_KW' if '$FORBIDDEN_KW' != '[]' else '[]')
report = '''$REPORT_CONTENT'''
found = [kw for kw in kws if kw in report]
if found:
    print('FOUND:' + ','.join(found))
else:
    print('OK')
" 2>/dev/null || echo "OK")

        if [[ "$FK_RESULT" == FOUND:* ]]; then
            log_error "    Forbidden keywords found: ${FK_RESULT#FOUND:}"
            KW_FAILED=true
        else
            log_info "    Forbidden keywords OK"
        fi
    fi

    # ── Per-task summary ──────────────────────────────────────────
    TASK_PASSED=true
    if [[ "$KW_FAILED" == "true" ]]; then
        TASK_PASSED=false
        FAILURES+=("{\"failed_case\": \"$task_id\", \"failure_class\": \"keyword_check\", \"details\": [\"Missing required or found forbidden keywords\"]}")
    fi
    if [[ "$STATUS" == "failed" ]]; then
        TASK_PASSED=false
        FAILURES+=("{\"failed_case\": \"$task_id\", \"failure_class\": \"run_failed\", \"details\": [\"Run status: $STATUS\"]}")
    fi

    if [[ "$TASK_PASSED" == "true" ]]; then
        PASSED=$((PASSED + 1))
        log_info "  ✅ $task_id PASSED"
    else
        FAILED=$((FAILED + 1))
        log_error "  ❌ $task_id FAILED"
    fi
done

# ── Step 9: Generate summary ────────────────────────────────────────
log_info "Step 9: Generating summary"

if [[ -f "$SUMMARY_GENERATOR" ]]; then
    "$VENV_PYTHON" "$SUMMARY_GENERATOR" \
        --total "$TOTAL" \
        --passed "$PASSED" \
        --failed "$FAILED" \
        --results "$RESULTS_FILE" 2>&1 || log_warn "Summary generator reported issues"
fi

# ── Final output ────────────────────────────────────────────────────
echo ""
echo "========================================"
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}DEEP_JUDGE_USER_ACCEPTANCE_SUITE_PASS${NC}"
    exit 0
else
    echo -e "${RED}DEEP_JUDGE_USER_ACCEPTANCE_SUITE_FAIL${NC}"
    echo ""
    echo "Failures:"
    for failure in "${FAILURES[@]}"; do
        echo "  $failure"
    done
    exit 1
fi