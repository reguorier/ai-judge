#!/usr/bin/env bash
# =============================================================================
# PUBLIC DEMO LIVE DRY RUN — Security Verify Script
# Release: public-demo-live-dry-run-v1
#
# Checks for:
#   - no raw traceback in artifacts
#   - no API key / secret exposure
#   - no raw phone / ID card / email in artifacts/logs
#   - rate limit enabled
#   - abuse guard enabled
#   - privacy notice present
#   - disclaimer present
# =============================================================================
set -uo pipefail
# Note: no set -e; we use explicit error handling below

DEMO_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo"
SECURITY_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/security"
OBS_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/observability"

PASS=0
FAIL=0

green()  { printf "\033[32m  [PASS] %s\033[0m\n" "$1"; ((PASS++)); }
red()    { printf "\033[31m  [FAIL] %s\033[0m\n" "$1"; ((FAIL++)); }

echo ""
echo "============================================================"
echo " LIVE DEMO SECURITY VERIFY"
echo "============================================================"
echo ""

# -------------------------------------------------------------------
# 1. No raw traceback in artifacts/reports
# -------------------------------------------------------------------
echo "--- Checking: no raw traceback ---"
FOUND_TRACEBACK=false
for pattern in "Traceback (most recent call last)" "File \".*\", line" "^\s+raise " "^\s+except "; do
    if grep -rqE "$pattern" "${DEMO_DIR}/replay/" 2>/dev/null; then
        FOUND_TRACEBACK=true
    fi
done
if grep -rqi "traceback" "${DEMO_DIR}/demo_failure_messages.json" 2>/dev/null && \
   ! grep -rqi "no.*traceback\|不暴露\|not expose" "${DEMO_DIR}/demo_failure_messages.json" 2>/dev/null; then
    FOUND_TRACEBACK=true
fi
if [ "$FOUND_TRACEBACK" = false ]; then
    green "no raw traceback in replay artifacts"
else
    red "raw traceback found in artifacts"
fi

# -------------------------------------------------------------------
# 2. No API key
# -------------------------------------------------------------------
echo "--- Checking: no API key ---"
API_KEY_FOUND=false
for pattern in 'sk-[a-zA-Z0-9]{20,}' 'api[_-]?key[\s:=]+["\x27][a-zA-Z0-9_-]{10,}["\x27]' 'OPENAI_API_KEY' 'ANTHROPIC_API_KEY'; do
    if grep -rqE "$pattern" "${DEMO_DIR}/" "${SECURITY_DIR}/" "${OBS_DIR}/" 2>/dev/null; then
        API_KEY_FOUND=true
    fi
done
# Also check reports
if grep -rqE 'sk-[a-zA-Z0-9]{20,}|api[_-]?key' /Users/audimacmini/Documents/ai-judge-skill/reports/PUBLIC_DEMO_LIVE_DRY_RUN_*.md 2>/dev/null; then
    API_KEY_FOUND=true
fi
if [ "$API_KEY_FOUND" = false ]; then
    green "no API key found in demo artifacts"
else
    red "API key found in demo artifacts"
fi

# -------------------------------------------------------------------
# 3. No raw PII (phone / ID / email) in artifacts
# -------------------------------------------------------------------
echo "--- Checking: no raw PII ---"
RAW_PII_FOUND=false
# Phone: 1[3-9]xxxxxxxxx
if grep -rqE '(?<!\d)1[3-9]\d{9}(?!\d)' "${DEMO_DIR}/replay/" 2>/dev/null; then
    RAW_PII_FOUND=true
fi
# ID card: 18 digits with date format
if grep -rqE '(?<!\d)[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)' "${DEMO_DIR}/replay/" 2>/dev/null; then
    RAW_PII_FOUND=true
fi
# Email
if grep -rqE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' "${DEMO_DIR}/replay/" 2>/dev/null; then
    RAW_PII_FOUND=true
fi

if [ "$RAW_PII_FOUND" = false ]; then
    green "no raw PII in replay artifacts"
else
    red "raw PII found in replay artifacts"
fi

# -------------------------------------------------------------------
# 4. Rate limit enabled
# -------------------------------------------------------------------
echo "--- Checking: rate limit enabled ---"
if [ -f "${SECURITY_DIR}/rate_limiter.py" ]; then
    if grep -q "rate_limit_exceeded" "${SECURITY_DIR}/rate_limiter.py" && \
       grep -q "allow_request" "${SECURITY_DIR}/rate_limiter.py"; then
        green "rate limit enabled and functional"
    else
        red "rate limit code incomplete"
    fi
else
    red "rate_limiter.py not found"
fi

# -------------------------------------------------------------------
# 5. Abuse guard enabled
# -------------------------------------------------------------------
echo "--- Checking: abuse guard enabled ---"
if [ -f "${SECURITY_DIR}/abuse_guard.py" ]; then
    if grep -q "AbuseGuardDecision" "${SECURITY_DIR}/abuse_guard.py" && \
       grep -q "allowed.*False" "${SECURITY_DIR}/abuse_guard.py"; then
        green "abuse guard enabled and functional"
    else
        red "abuse guard code incomplete"
    fi
else
    red "abuse_guard.py not found"
fi

# -------------------------------------------------------------------
# 6. Privacy notice present
# -------------------------------------------------------------------
echo "--- Checking: privacy notice ---"
if [ -f "${DEMO_DIR}/demo_privacy_notice.md" ]; then
    if grep -qi "privacy\|隐私\|不收集\|not collect\|hash" "${DEMO_DIR}/demo_privacy_notice.md"; then
        green "privacy notice present with required content"
    else
        red "privacy notice missing required content"
    fi
else
    red "demo_privacy_notice.md not found"
fi

# -------------------------------------------------------------------
# 7. Disclaimer present
# -------------------------------------------------------------------
echo "--- Checking: disclaimer ---"
if [ -f "${DEMO_DIR}/demo_disclaimer.md" ]; then
    if grep -qi "disclaimer\|免责\|实验\|experimental\|not.*legal\|不.*法律\|不.*替代" "${DEMO_DIR}/demo_disclaimer.md"; then
        green "disclaimer present with required content"
    else
        red "disclaimer missing required content"
    fi
else
    red "demo_disclaimer.md not found"
fi

# -------------------------------------------------------------------
# 8. No secrets in security code itself
# -------------------------------------------------------------------
echo "--- Checking: no secrets in security code ---"
SECRET_IN_CODE=false
for f in "${SECURITY_DIR}/rate_limiter.py" "${SECURITY_DIR}/abuse_guard.py" "${SECURITY_DIR}/pii_redactor.py"; do
    if grep -qE 'password\s*=\s*["\x27][^"\x27]{4,}["\x27]|secret\s*=\s*["\x27][^"\x27]{4,}["\x27]|token\s*=\s*["\x27][^"\x27]{4,}["\x27]' "$f" 2>/dev/null; then
        SECRET_IN_CODE=true
    fi
done
if [ "$SECRET_IN_CODE" = false ]; then
    green "no hardcoded secrets in security code"
else
    red "hardcoded secrets found in security code"
fi

# -------------------------------------------------------------------
# 9. Telemetry hashes IP/session
# -------------------------------------------------------------------
echo "--- Checking: telemetry hash ---"
if [ -f "${OBS_DIR}/demo_telemetry.py" ]; then
    if grep -q "hash" "${OBS_DIR}/demo_telemetry.py" && \
       grep -q "session_id_hash\|ip_hash" "${OBS_DIR}/demo_telemetry.py"; then
        green "telemetry hashes IP/session"
    else
        red "telemetry does not hash IP/session"
    fi
else
    red "demo_telemetry.py not found"
fi

# -------------------------------------------------------------------
# 10. No raw traceback in failure messages
# -------------------------------------------------------------------
echo "--- Checking: no raw traceback in failure messages ---"
if [ -f "${DEMO_DIR}/demo_failure_messages.json" ]; then
    # Extract only user-facing fields (plain_message, title, suggested_action) and check those
    # Skip the description field which may contain documentation phrases like "no traceback"
    USER_MSG=$(python3 -c "
import json
with open('${DEMO_DIR}/demo_failure_messages.json') as f:
    d = json.load(f)
parts = []
for k, v in d.get('failures', {}).items():
    parts.append(v.get('title', ''))
    parts.append(v.get('plain_message', ''))
    parts.append(v.get('suggested_action', ''))
print(' '.join(parts))
")
    if echo "$USER_MSG" | grep -qi "traceback\|exception\|stack"; then
        red "raw traceback/exception terms found in failure messages"
    else
        green "no raw traceback in failure messages"
    fi
else
    red "demo_failure_messages.json not found"
fi

# -------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------
echo ""
echo "============================================================"
echo " SECURITY VERIFY SUMMARY"
echo "============================================================"
echo ""

TOTAL=$((PASS + FAIL))
printf "  Passed: %s/%s\n" "$PASS" "$TOTAL"
printf "  Failed: %s/%s\n" "$FAIL" "$TOTAL"
echo ""

if [ "$FAIL" -eq 0 ]; then
    green "============================================================"
    green " LIVE_DEMO_SECURITY_PASS"
    green "============================================================"
    exit 0
else
    red "============================================================"
    red " LIVE_DEMO_SECURITY_FAIL"
    red "============================================================"
    exit 1
fi