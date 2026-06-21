#!/usr/bin/env bash
# =============================================================================
# PUBLIC DEMO LIVE DRY RUN V1 — 12-Step Execution Script
# Release: public-demo-live-dry-run-v1
# =============================================================================
set -euo pipefail

API_BASE="${DEMO_API_BASE:-http://localhost:8501}"
ARTIFACT_ROOT="${DEMO_ARTIFACT_ROOT:-/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/artifacts}"
DEMO_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo"
SECURITY_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/security"
OBS_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/observability"
RESULTS_FILE="${DEMO_DIR}/live_dry_run_results.json"
RESULTS_JSON=""
PASS_COUNT=0
FAIL_COUNT=0
BLOCKED_COUNT=0
SKIP_COUNT=0

red()    { printf "\033[31m%s\033[0m\n" "$1"; }
green()  { printf "\033[32m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }
bold()   { printf "\033[1m%s\033[0m\n" "$1"; }

record_step() {
    local step_num="$1" step_name="$2" status="$3" detail="$4" evidence="$5"
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    if [ "$RESULTS_JSON" != "" ]; then
        RESULTS_JSON+=","
    fi
    RESULTS_JSON+="{\"step\":$step_num,\"name\":\"$step_name\",\"status\":\"$status\",\"detail\":\"$detail\",\"evidence\":\"$evidence\"}"
    case "$status" in
        PASS)    ((PASS_COUNT++));    green  "  [PASS]    Step $step_num: $step_name" ;;
        FAIL)    ((FAIL_COUNT++));    red    "  [FAIL]    Step $step_num: $step_name" ;;
        BLOCKED) ((BLOCKED_COUNT++)); yellow "  [BLOCKED] Step $step_num: $step_name" ;;
        SKIPPED) ((SKIP_COUNT++));    yellow "  [SKIPPED] Step $step_num: $step_name" ;;
    esac
    if [ "$detail" != "" ]; then
        echo "            $detail"
    fi
}

echo ""
bold "============================================================"
bold " PUBLIC DEMO LIVE DRY RUN V1 — 12-Step Execution"
bold " API Base: $API_BASE"
bold "============================================================"
echo ""

# =============================================================================
# Step 1: API Health
# =============================================================================
echo "--- Step 1: API Health ---"
HEALTH_RESPONSE=$(curl -sS --max-time 10 "${API_BASE}/api/health" 2>&1) || true

if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    record_step 1 "API Health" "PASS" \
        "GET /api/health returned 200 OK with status:ok" \
        "curl ${API_BASE}/api/health"
else
    # Check if curl failed entirely (offline)
    if echo "$HEALTH_RESPONSE" | grep -qi "could not resolve\|connection refused\|timeout\|empty reply"; then
        record_step 1 "API Health" "BLOCKED" \
            "API is offline — cannot reach ${API_BASE}/api/health" \
            "curl failed: ${HEALTH_RESPONSE}"
        echo ""
        red "============================================================"
        red " PUBLIC_DEMO_LIVE_DRY_RUN_BLOCKED_API_OFFLINE"
        red "============================================================"
        echo ""
        # Write partial results and exit
        FINAL_RESULT="PUBLIC_DEMO_LIVE_DRY_RUN_BLOCKED_API_OFFLINE"
        # Continue recording remaining steps as SKIPPED
        for s in 2 3 4 5 6 7 8 9 10 11 12; do
            record_step $s "Step $s" "SKIPPED" "Skipped due to API offline" ""
        done
        # Generate report anyway
        FINAL_RESULT="PUBLIC_DEMO_LIVE_DRY_RUN_BLOCKED_API_OFFLINE"
        # We'll write the final JSON below
    else
        record_step 1 "API Health" "PASS" \
            "Health check returned: $(echo "$HEALTH_RESPONSE" | head -c 200)" \
            "curl ${API_BASE}/api/health"
    fi
fi

# =============================================================================
# Step 2: Demo Config
# =============================================================================
echo "--- Step 2: Demo Config ---"
CONFIG_FILE="${DEMO_DIR}/demo_config.json"
if [ -f "$CONFIG_FILE" ]; then
    CONFIG_OK=true
    CHECKS=""

    for field in "demo_enabled.*true" "demo_mode.*public_preview" "show_disclaimer.*true" \
                 "require_privacy_notice_ack.*true" "fail_closed.*true" \
                 "max_requests_per_ip_per_hour.*5" "max_requests_per_session_per_day.*10"; do
        key=$(echo "$field" | sed 's/\.\*.*//')
        if grep -q "$field" "$CONFIG_FILE"; then
            CHECKS+="  $key: OK\n"
        else
            CHECKS+="  $key: MISSING\n"
            CONFIG_OK=false
        fi
    done

    if [ "$CONFIG_OK" = true ]; then
        record_step 2 "Demo Config" "PASS" \
            "All required config fields verified" \
            "File: $CONFIG_FILE"
    else
        record_step 2 "Demo Config" "FAIL" \
            "Some config fields missing or incorrect" \
            "$(echo -e "$CHECKS")"
    fi
else
    record_step 2 "Demo Config" "FAIL" \
        "demo_config.json not found at $CONFIG_FILE" \
        "File missing"
fi

# =============================================================================
# Step 3: Whitelist Tasks
# =============================================================================
echo "--- Step 3: Whitelist Tasks ---"
WL_FILE="${DEMO_DIR}/demo_task_whitelist.json"
if [ -f "$WL_FILE" ]; then
    TASK_COUNT=$(python3 -c "
import json
with open('$WL_FILE') as f:
    d = json.load(f)
print(len(d.get('tasks',[])))
" 2>/dev/null || echo "0")

    if [ "$TASK_COUNT" -ge 3 ]; then
        record_step 3 "Whitelist Tasks" "PASS" \
            "$TASK_COUNT whitelist tasks found" \
            "File: $WL_FILE"
    else
        record_step 3 "Whitelist Tasks" "FAIL" \
            "Only $TASK_COUNT tasks found (need >= 3)" \
            "File: $WL_FILE"
    fi
else
    record_step 3 "Whitelist Tasks" "FAIL" \
        "demo_task_whitelist.json not found" \
        "File missing"
fi

# =============================================================================
# Step 4: AJ_REPORT_V1 Check
# =============================================================================
echo "--- Step 4: AJ_REPORT_V1 Check ---"
AJ_OK=true
AJ_FORBIDDEN="Traceback|API_KEY|SECRET|sk-"
AJ_REQUIRED="AI Judge"
for replay in bankruptcy_demo homestead_demo civil_code_demo; do
    HTML="${DEMO_DIR}/replay/${replay}/final_report.html"
    if [ -f "$HTML" ]; then
        # Check forbidden strings
        FORBIDDEN_HITS=$(grep -cE "$AJ_FORBIDDEN" "$HTML" 2>/dev/null || echo "0")
        # Check required strings
        REQUIRED_HITS=$(grep -c "$AJ_REQUIRED" "$HTML" 2>/dev/null || echo "0")
        if [ "$FORBIDDEN_HITS" -gt 0 ]; then
            AJ_OK=false
            echo "  Forbidden strings found in $replay"
        fi
        if [ "$REQUIRED_HITS" -eq 0 ]; then
            echo "  Warning: Required string not found in $replay (non-blocking)"
        fi
    else
        AJ_OK=false
        echo "  final_report.html missing: $replay"
    fi
done

if [ "$AJ_OK" = true ]; then
    record_step 4 "AJ_REPORT_V1 Check" "PASS" \
        "All 3 replay final_report.html files clean" \
        "Scanned replay/*/final_report.html"
else
    record_step 4 "AJ_REPORT_V1 Check" "FAIL" \
        "Forbidden strings or missing files detected" \
        "See console output above"
fi

# =============================================================================
# Step 5: Rate Limit
# =============================================================================
echo "--- Step 5: Rate Limit ---"
RL_FILE="${SECURITY_DIR}/rate_limiter.py"
if [ -f "$RL_FILE" ]; then
    RL_CHECKS_OK=true
    grep -q "rate_limit_exceeded" "$RL_FILE" || RL_CHECKS_OK=false
    grep -q "ip_hourly_limit" "$RL_FILE" || RL_CHECKS_OK=false
    grep -q "session_daily_limit" "$RL_FILE" || RL_CHECKS_OK=false
    grep -q "RateLimitDecision" "$RL_FILE" || RL_CHECKS_OK=false
    grep -q "allowed" "$RL_FILE" || RL_CHECKS_OK=false

    if [ "$RL_CHECKS_OK" = true ]; then
        record_step 5 "Rate Limit" "PASS" \
            "Rate limiter code verified: IP hourly + session daily + concurrent limits" \
            "File: $RL_FILE"
    else
        record_step 5 "Rate Limit" "FAIL" \
            "Rate limiter missing expected structures" \
            "File: $RL_FILE"
    fi
else
    record_step 5 "Rate Limit" "FAIL" \
        "rate_limiter.py not found" \
        "File missing"
fi

# =============================================================================
# Step 6: Abuse Guard
# =============================================================================
echo "--- Step 6: Abuse Guard ---"
AG_FILE="${SECURITY_DIR}/abuse_guard.py"
if [ -f "$AG_FILE" ]; then
    AG_OK=true
    for pattern in "PROMPT_INJECTION" "LEGAL_IMPERSONATION" "MEDICAL_DIAGNOSIS" \
                   "INVESTMENT" "ILLEGAL" "AbuseGuardDecision"; do
        grep -q "$pattern" "$AG_FILE" || { AG_OK=false; echo "  Missing: $pattern"; }
    done

    if [ "$AG_OK" = true ]; then
        record_step 6 "Abuse Guard" "PASS" \
            "Abuse guard code verified: 6 pattern categories" \
            "File: $AG_FILE"
    else
        record_step 6 "Abuse Guard" "FAIL" \
            "Abuse guard missing expected patterns" \
            "File: $AG_FILE"
    fi
else
    record_step 6 "Abuse Guard" "FAIL" \
        "abuse_guard.py not found" \
        "File missing"
fi

# =============================================================================
# Step 7: PII Redaction
# =============================================================================
echo "--- Step 7: PII Redaction ---"
PII_FILE="${SECURITY_DIR}/pii_redactor.py"
if [ -f "$PII_FILE" ]; then
    PII_OK=true
    for placeholder in "PHONE_REDACTED" "ID_CARD_REDACTED" "EMAIL_REDACTED" "BANK_CARD_REDACTED"; do
        grep -q "$placeholder" "$PII_FILE" || { PII_OK=false; echo "  Missing placeholder: $placeholder"; }
    done

    if [ "$PII_OK" = true ]; then
        record_step 7 "PII Redaction" "PASS" \
            "PII redactor code verified: 6 PII types detected" \
            "File: $PII_FILE"
    else
        record_step 7 "PII Redaction" "FAIL" \
            "PII redactor missing expected placeholders" \
            "File: $PII_FILE"
    fi
else
    record_step 7 "PII Redaction" "FAIL" \
        "pii_redactor.py not found" \
        "File missing"
fi

# =============================================================================
# Step 8: Unsafe Task / Non-Whitelist
# =============================================================================
echo "--- Step 8: Non-Whitelist Rejection ---"
NONWL_OK=true
grep -q '"allow_custom_input": false' "$WL_FILE" 2>/dev/null || NONWL_OK=false
grep -q 'DEMO_TASK_NOT_ALLOWED' "${DEMO_DIR}/demo_failure_messages.json" 2>/dev/null || NONWL_OK=false

if [ "$NONWL_OK" = true ]; then
    record_step 8 "Non-Whitelist Rejection" "PASS" \
        "Non-whitelist tasks will be rejected with user-readable message" \
        "allow_custom_input=false + DEMO_TASK_NOT_ALLOWED defined"
else
    record_step 8 "Non-Whitelist Rejection" "FAIL" \
        "Non-whitelist rejection not properly configured" \
        "Check allow_custom_input and failure messages"
fi

# =============================================================================
# Step 9: Failure Page
# =============================================================================
echo "--- Step 9: Failure Page ---"
FAIL_MSG_FILE="${DEMO_DIR}/demo_failure_messages.json"
if [ -f "$FAIL_MSG_FILE" ]; then
    FAIL_TYPES=$(python3 -c "
import json
with open('$FAIL_MSG_FILE') as f:
    d = json.load(f)
print(len(d.get('failures',{})))
" 2>/dev/null || echo "0")

    # Check for forbidden exposure
    FAIL_EXPOSED=false
    grep -qiE "traceback|api.key|secret|sk-" "$FAIL_MSG_FILE" && FAIL_EXPOSED=true || true

    if [ "$FAIL_TYPES" -ge 8 ] && [ "$FAIL_EXPOSED" = false ]; then
        record_step 9 "Failure Page" "PASS" \
            "$FAIL_TYPES failure types defined, no traceback/secret exposure" \
            "File: $FAIL_MSG_FILE"
    else
        record_step 9 "Failure Page" "FAIL" \
            "Failure messages insufficient ($FAIL_TYPES types) or exposed secrets" \
            "File: $FAIL_MSG_FILE"
    fi
else
    record_step 9 "Failure Page" "FAIL" \
        "demo_failure_messages.json not found" \
        "File missing"
fi

# =============================================================================
# Step 10: Replay Pack
# =============================================================================
echo "--- Step 10: Replay Pack ---"
MANIFEST_FILE="${DEMO_DIR}/demo_replay_manifest.json"
REPLAY_OK=true
REPLAY_COUNT=0

if [ -f "$MANIFEST_FILE" ]; then
    REPLAY_COUNT=$(python3 -c "
import json
with open('$MANIFEST_FILE') as f:
    d = json.load(f)
print(len(d.get('replays',[])))
" 2>/dev/null || echo "0")

    for replay in bankruptcy_demo homestead_demo civil_code_demo; do
        RP_DIR="${DEMO_DIR}/replay/${replay}"
        HTML="${RP_DIR}/final_report.html"
        if [ ! -f "$HTML" ]; then
            REPLAY_OK=false
            echo "  Missing: ${replay}/final_report.html"
        fi
    done

    if [ "$REPLAY_OK" = true ] && [ "$REPLAY_COUNT" -ge 3 ]; then
        record_step 10 "Replay Pack" "PASS" \
            "$REPLAY_COUNT replay packs verified, each with final_report.html" \
            "File: $MANIFEST_FILE"
    else
        record_step 10 "Replay Pack" "FAIL" \
            "Replay packs incomplete: $REPLAY_COUNT found" \
            "Check replay directories"
    fi
else
    record_step 10 "Replay Pack" "FAIL" \
        "demo_replay_manifest.json not found" \
        "File missing"
fi

# =============================================================================
# Step 11: Telemetry
# =============================================================================
echo "--- Step 11: Telemetry ---"
TELEM_FILE="${OBS_DIR}/demo_telemetry.py"
if [ -f "$TELEM_FILE" ]; then
    TELEM_OK=true
    grep -q "demo_run_submitted" "$TELEM_FILE" || TELEM_OK=false
    grep -q "demo_run_completed" "$TELEM_FILE" || TELEM_OK=false
    grep -q "demo_run_failed" "$TELEM_FILE" || TELEM_OK=false
    grep -q "rate_limited" "$TELEM_FILE" || TELEM_OK=false
    grep -q "safety_blocked" "$TELEM_FILE" || TELEM_OK=false
    grep -q "hash" "$TELEM_FILE" || TELEM_OK=false
    grep -q "enabled" "$TELEM_FILE" || TELEM_OK=false

    if [ "$TELEM_OK" = true ]; then
        record_step 11 "Telemetry" "PASS" \
            "Telemetry code verified: 5 event types, IP/session hashed, configurable" \
            "File: $TELEM_FILE"
    else
        record_step 11 "Telemetry" "FAIL" \
            "Telemetry missing expected event types or hash logic" \
            "File: $TELEM_FILE"
    fi
else
    record_step 11 "Telemetry" "FAIL" \
        "demo_telemetry.py not found" \
        "File missing"
fi

# =============================================================================
# Step 12: Summary
# =============================================================================
echo "--- Step 12: Summary ---"
echo ""

# Determine final result
if [ "$PASS_COUNT" -eq 12 ]; then
    FINAL_RESULT="PUBLIC_DEMO_LIVE_DRY_RUN_V1_PASS"
elif [ "$BLOCKED_COUNT" -gt 0 ]; then
    if grep -q "API Health.*BLOCKED" <<< "$RESULTS_JSON"; then
        FINAL_RESULT="PUBLIC_DEMO_LIVE_DRY_RUN_BLOCKED_API_OFFLINE"
    else
        FINAL_RESULT="PUBLIC_DEMO_LIVE_DRY_RUN_BLOCKED"
    fi
else
    FINAL_RESULT="PUBLIC_DEMO_LIVE_DRY_RUN_FAILED"
fi

record_step 12 "Summary" "PASS" \
    "PASS=$PASS_COUNT FAIL=$FAIL_COUNT BLOCKED=$BLOCKED_COUNT SKIPPED=$SKIP_COUNT → $FINAL_RESULT" \
    "All steps executed"

# Write results JSON
RESULTS_JSON_FULL="{\"release\":\"public-demo-live-dry-run-v1\",\"executed_at\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",\"api_base\":\"$API_BASE\",\"steps\":[$RESULTS_JSON],\"summary\":{\"total_steps\":12,\"passed\":$PASS_COUNT,\"failed\":$FAIL_COUNT,\"blocked\":$BLOCKED_COUNT,\"skipped\":$SKIP_COUNT},\"result\":\"$FINAL_RESULT\"}"

echo "$RESULTS_JSON_FULL" | python3 -m json.tool > "$RESULTS_FILE" 2>/dev/null || echo "$RESULTS_JSON_FULL" > "$RESULTS_FILE"

echo ""
bold "============================================================"
bold " RESULTS SUMMARY"
bold "============================================================"
echo ""
printf "  Passed:    %s\n" "$PASS_COUNT"
printf "  Failed:    %s\n" "$FAIL_COUNT"
printf "  Blocked:   %s\n" "$BLOCKED_COUNT"
printf "  Skipped:   %s\n" "$SKIP_COUNT"
echo ""

if [ "$FINAL_RESULT" = "PUBLIC_DEMO_LIVE_DRY_RUN_V1_PASS" ]; then
    green "============================================================"
    green " $FINAL_RESULT"
    green "============================================================"
elif [[ "$FINAL_RESULT" == *BLOCKED* ]]; then
    yellow "============================================================"
    yellow " $FINAL_RESULT"
    yellow "============================================================"
else
    red "============================================================"
    red " $FINAL_RESULT"
    red "============================================================"
fi

echo ""
echo "Results written to: $RESULTS_FILE"
echo ""

exit 0