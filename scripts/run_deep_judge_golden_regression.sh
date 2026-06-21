#!/usr/bin/env bash
#
# run_deep_judge_golden_regression.sh
# 10-step golden regression pipeline for Deep Judge runs.
#
# Steps:
# 1.  Read golden_cases.json
# 2.  Call /api/runs for each case
# 3.  Wait for artifact landing
# 4.  Call artifact validator
# 5.  Check required keywords
# 6.  Check forbidden keywords
# 7.  Check substantive_sources
# 8.  Check validation_result
# 9.  Compute cross-case similarity
# 10. Output summary JSON + PASS/FAIL
#
set -euo pipefail

# ── Paths ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GOLDEN_CASES="$PROJECT_ROOT/runtime/product/golden_cases/golden_cases.json"
ARTIFACT_VALIDATOR="$PROJECT_ROOT/runtime/product/observability/artifact_validator.py"
REPORT_SIMILARITY="$PROJECT_ROOT/runtime/product/observability/report_similarity.py"
SUMMARIZE_SCRIPT="$SCRIPT_DIR/summarize_deep_judge_release.py"

# API config (override via env)
API_HOST="${API_HOST:-http://127.0.0.1:8000}"
API_RUNS_ENDPOINT="${API_HOST}/api/runs"
WAIT_SECONDS="${WAIT_SECONDS:-60}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"
RUNS_ROOT="${RUNS_ROOT:-$PROJECT_ROOT/runs}"

TEMP_DIR="$PROJECT_ROOT/runtime/product/golden_cases/temp"
SUMMARY_FILE="$TEMP_DIR/golden_regression_summary.json"
mkdir -p "$TEMP_DIR"

# ── Logging ────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
fail() { log "FAIL: $*"; echo "DEEP_JUDGE_GOLDEN_REGRESSION_FAIL"; exit 1; }

# ── Step 1: Read golden cases ──────────────────────────────
log "Step 1: Reading golden_cases.json"
if [ ! -f "$GOLDEN_CASES" ]; then
    fail "golden_cases.json not found at $GOLDEN_CASES"
fi

CASE_COUNT=$(python3 -c "
import json
with open('$GOLDEN_CASES') as f:
    cases = json.load(f)
print(len(cases))
")
log "Found $CASE_COUNT golden cases"

# ── Check if API is running ─────────────────────────────────
log "Checking API health at $API_HOST/api/health"
if curl -sf "$API_HOST/api/health" > /dev/null 2>&1; then
    API_RUNNING=true
    log "API is running, will submit runs via $API_RUNS_ENDPOINT"
else
    API_RUNNING=false
    log "API is not running — will validate existing runs in $RUNS_ROOT"
fi

# ── Results accumulators ────────────────────────────────────
declare -a CASE_RESULTS
TOTAL_PASSED=0
TOTAL_FAILED=0
REPORT_PATHS=()

# ── Process each case ───────────────────────────────────────
for i in $(seq 0 $((CASE_COUNT - 1))); do
    CASE_ID=$(python3 -c "
import json
with open('$GOLDEN_CASES') as f:
    cases = json.load(f)
print(cases[$i]['id'])
")
    CASE_QUESTION=$(python3 -c "
import json
with open('$GOLDEN_CASES') as f:
    cases = json.load(f)
print(cases[$i]['question'])
")

    log ""
    log "──────────────────────────────────────────────"
    log "Case $((i+1))/$CASE_COUNT: $CASE_ID"
    log "Question: $CASE_QUESTION"

    CASE_FAILURES=()

    if [ "$API_RUNNING" = true ]; then
        # ── Step 2: Submit run ──────────────────────────────────
        log "Step 2: Submitting run to $API_RUNS_ENDPOINT"
        RUN_RESPONSE=$(curl -sf -X POST "$API_RUNS_ENDPOINT" \
            -H 'Content-Type: application/json' \
            -d "{\"question\": \"$CASE_QUESTION\", \"mode\": \"deep_judge\"}" 2>&1) || true
        RUN_ID=$(echo "$RUN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id',''))" 2>/dev/null || echo "")
        log "Run ID: ${RUN_ID:-<could not parse>}"

        # ── Step 3: Wait for artifact landing ───────────────────
        log "Step 3: Waiting for artifacts (max ${WAIT_SECONDS}s)..."
        RUN_DIR="$RUNS_ROOT/$RUN_ID"
        ELAPSED=0
        while [ "$ELAPSED" -lt "$WAIT_SECONDS" ]; do
            if [ -f "$RUN_DIR/final_report.html" ] && [ -f "$RUN_DIR/final_report_contract.json" ]; then
                log "Artifacts landed after ${ELAPSED}s"
                break
            fi
            sleep "$POLL_INTERVAL"
            ELAPSED=$((ELAPSED + POLL_INTERVAL))
        done
        if [ ! -f "$RUN_DIR/final_report.html" ]; then
            CASE_FAILURES+=("artifact_timeout")
            log "WARN: Artifacts did not land within ${WAIT_SECONDS}s"
        fi
    else
        # API not running — find matching existing run
        log "API not running — searching existing runs for case: $CASE_ID"
        RUN_DIR=""
        for d in "$RUNS_ROOT"/*/; do
            if [ -f "$d/run_metadata.json" ]; then
                Q=$(python3 -c "import json; m=json.load(open('$d/run_metadata.json')); print(m.get('question',''))" 2>/dev/null || echo "")
                if [[ "$Q" == *"$CASE_QUESTION"* ]] || [[ "$CASE_QUESTION" == *"$Q"* ]]; then
                    RUN_DIR="$d"
                    RUN_DIR="${RUN_DIR%/}"
                    break
                fi
            fi
        done
        if [ -z "$RUN_DIR" ]; then
            log "No existing run found for case $CASE_ID — skipping artifact checks"
            CASE_FAILURES+=("no_run_found")
        fi
    fi

    RUN_DIR="${RUN_DIR%/}"
    if [ -n "$RUN_DIR" ] && [ -d "$RUN_DIR" ]; then
        # ── Step 4: Artifact validation ─────────────────────────
        log "Step 4: Running artifact validator on $RUN_DIR"
        ARTIFACT_RESULT=$(python3 "$ARTIFACT_VALIDATOR" "$RUN_DIR" 2>&1) || true
        ARTIFACT_OK=$(echo "$ARTIFACT_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',False))" 2>/dev/null || echo "false")
        if [ "$ARTIFACT_OK" != "True" ]; then
            CASE_FAILURES+=("artifact_validation_failed")
            log "WARN: Artifact validation failed"
            log "Details: $ARTIFACT_RESULT"
        else
            log "Artifact validation: PASS"
        fi

        # ── Step 5: Check required keywords ─────────────────────
        log "Step 5: Checking required keywords in final_report.html"
        if [ -f "$RUN_DIR/final_report.html" ]; then
            REPORT_HTML=$(cat "$RUN_DIR/final_report.html")
            REQ_KWS=$(python3 -c "
import json
with open('$GOLDEN_CASES') as f:
    cases = json.load(f)
print('|'.join(cases[$i]['required_keywords']))
")
            IFS='|' read -ra KW_ARRAY <<< "$REQ_KWS"
            ALL_REQUIRED_OK=true
            for kw in "${KW_ARRAY[@]}"; do
                if ! echo "$REPORT_HTML" | grep -qF "$kw"; then
                    log "WARN: Required keyword missing: $kw"
                    CASE_FAILURES+=("required_keyword_missing:$kw")
                    ALL_REQUIRED_OK=false
                fi
            done
            if [ "$ALL_REQUIRED_OK" = true ]; then
                log "All required keywords found"
            fi

            # ── Step 6: Check forbidden keywords ────────────────────
            log "Step 6: Checking forbidden keywords"
            FORBIDDEN_KWS=$(python3 -c "
import json
with open('$GOLDEN_CASES') as f:
    cases = json.load(f)
print('|'.join(cases[$i]['forbidden_keywords']))
")
            IFS='|' read -ra FK_ARRAY <<< "$FORBIDDEN_KWS"
            ALL_CLEAN=true
            for fk in "${FK_ARRAY[@]}"; do
                if echo "$REPORT_HTML" | grep -qF "$fk"; then
                    log "WARN: Forbidden keyword found: $fk"
                    CASE_FAILURES+=("forbidden_keyword_found:$fk")
                    ALL_CLEAN=false
                fi
            done
            if [ "$ALL_CLEAN" = true ]; then
                log "No forbidden keywords found"
            fi

            # Collect report paths for similarity comparison
            REPORT_PATHS+=("$RUN_DIR/final_report.html")
        fi

        # ── Step 7: Check substantive_sources ────────────────────
        log "Step 7: Checking substantive_sources"
        if [ -f "$RUN_DIR/run_metadata.json" ]; then
            SUBST_SOURCES=$(python3 -c "
import json
with open('$RUN_DIR/run_metadata.json') as f:
    m = json.load(f)
print(json.dumps(m.get('deep_judge',{}).get('substantive_sources',[])))
" 2>/dev/null)
            if [ "$SUBST_SOURCES" = "[]" ] || [ -z "$SUBST_SOURCES" ]; then
                CASE_FAILURES+=("empty_substantive_sources")
                log "WARN: substantive_sources is empty"
            else
                log "substantive_sources: $SUBST_SOURCES"
            fi
        fi

        # ── Step 8: Check validation_result ──────────────────────
        log "Step 8: Checking validation_result"
        if [ -f "$RUN_DIR/validation_result.json" ]; then
            VAL_STATUS=$(python3 -c "
import json
with open('$RUN_DIR/validation_result.json') as f:
    v = json.load(f)
print(v.get('status','').lower())
" 2>/dev/null)
            if [[ "$VAL_STATUS" == "ok" || "$VAL_STATUS" == "passed" || "$VAL_STATUS" == "success" ]]; then
                log "validation_result: $VAL_STATUS (pass)"
            else
                CASE_FAILURES+=("validation_failed:$VAL_STATUS")
                log "WARN: validation_result status=$VAL_STATUS"
            fi
        fi
    fi

    # Accumulate results
    if [ ${#CASE_FAILURES[@]} -eq 0 ]; then
        log "Case $CASE_ID: PASS"
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
        CASE_RESULTS+=("{\"id\":\"$CASE_ID\",\"passed\":true}")
    else
        log "Case $CASE_ID: FAIL — ${CASE_FAILURES[*]}"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        FAILS_JSON=$(printf '%s\n' "${CASE_FAILURES[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin.readlines()]))")
        CASE_RESULTS+=("{\"id\":\"$CASE_ID\",\"passed\":false,\"failures\":$FAILS_JSON}")
    fi
done

# ── Step 9: Cross-case similarity ──────────────────────────
log ""
log "Step 9: Computing cross-case similarity"
SIMILARITY_RESULTS="[]"
SIM_DIFF_OK=0
SIM_DIFF_FAIL=0

if [ ${#REPORT_PATHS[@]} -ge 2 ]; then
    for ((a=0; a<${#REPORT_PATHS[@]}; a++)); do
        for ((b=a+1; b<${#REPORT_PATHS[@]}; b++)); do
            SIM_RESULT=$(python3 "$REPORT_SIMILARITY" "${REPORT_PATHS[$a]}" "${REPORT_PATHS[$b]}" 2>&1) || true
            SIM_VAL=$(echo "$SIM_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('similarity',0))" 2>/dev/null || echo "0")
            SIM_RISK=$(echo "$SIM_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('risk',''))" 2>/dev/null || echo "")
            if [ -n "$SIM_RISK" ] && [ "$SIM_RISK" != "None" ]; then
                SIM_DIFF_FAIL=$((SIM_DIFF_FAIL + 1))
                log "Similarity risk: ${REPORT_PATHS[$a]} vs ${REPORT_PATHS[$b]} = $SIM_VAL ($SIM_RISK)"
            fi
        done
    done
    SIMILARITY_RESULTS="{ \"similarity_checks_total\": $(( ${#REPORT_PATHS[@]} * (${#REPORT_PATHS[@]} - 1) / 2 )), \"risks_found\": $SIM_DIFF_FAIL }"
fi
log "Similarity checks: $SIM_DIFF_FAIL risks found"

# ── Step 10: Summary ───────────────────────────────────────
log ""
log "Step 10: Building summary"

SUMMARY=$(cat <<JSON_END
{
  "golden_cases_total": $CASE_COUNT,
  "golden_cases_passed": $TOTAL_PASSED,
  "golden_cases_failed": $TOTAL_FAILED,
  "case_results": [$(IFS=,; echo "${CASE_RESULTS[*]}")],
  "cross_case_similarity": $SIMILARITY_RESULTS,
  "api_used": $API_RUNNING
}
JSON_END
)

echo "$SUMMARY" | python3 -m json.tool > "$SUMMARY_FILE"
log "Summary written to $SUMMARY_FILE"

# Final verdict
log ""
log "=============================================="
if [ "$TOTAL_FAILED" -eq 0 ]; then
    echo "DEEP_JUDGE_GOLDEN_REGRESSION_PASS"
    exit 0
else
    echo "DEEP_JUDGE_GOLDEN_REGRESSION_FAIL"
    echo "Failed cases: $TOTAL_FAILED / $CASE_COUNT"
    exit 1
fi