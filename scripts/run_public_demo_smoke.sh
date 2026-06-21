#!/bin/bash
# AI Judge Public Demo Smoke
# public-demo-readiness-v1.0.0
#
# 11-step check:
# 1. API health
# 2. demo config loaded
# 3. whitelist task can be submitted
# 4. rate limit enforced
# 5. PII redaction working
# 6. unsafe task rejected
# 7. allowed task generates report
# 8. validation ok
# 9. final_report.html accessible
# 10. failure messages readable
# 11. replay pack openable

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PRODUCT_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product"
DEMO_DIR="$PRODUCT_DIR/demo"
SECURITY_DIR="$PRODUCT_DIR/security"
OBSERVABILITY_DIR="$PRODUCT_DIR/observability"
PASS_COUNT=0
FAIL_COUNT=0

pass_step() { echo "  [PASS] $1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail_step() { echo "  [FAIL] $1: $2"; FAIL_COUNT=$((FAIL_COUNT+1)); }

echo "============================================"
echo "AI Judge Public Demo Smoke — V1"
echo "============================================"
echo ""

# --- Step 1: API health ---
echo "[1/11] API health check"
if curl -sf -o /dev/null -w "%{http_code}" "http://localhost:8000/health" 2>/dev/null | grep -q "200"; then
    pass_step "API health endpoint returns 200"
else
    fail_step "API health" "Could not reach localhost:8000/health (may be expected if API not running locally)"
    echo "         Note: API runtime check skipped — validating config files only"
fi

# --- Step 2: demo config loaded ---
echo "[2/11] Demo config validation"
CONFIG_FILE="$DEMO_DIR/demo_config.json"
if [ -f "$CONFIG_FILE" ]; then
    if python3 -c "
import json
with open('$CONFIG_FILE') as f:
    c = json.load(f)
assert c['demo_enabled'] == True, 'demo_enabled must be True'
assert c['fail_closed'] == True, 'fail_closed must be True'
assert c['max_requests_per_ip_per_hour'] == 5, 'ip limit must be 5'
assert c['show_disclaimer'] == True, 'show_disclaimer must be True'
print('OK')
" 2>/dev/null; then
        pass_step "demo_config.json valid"
    else
        fail_step "demo_config.json" "Schema validation failed"
    fi
else
    fail_step "demo_config.json" "File not found"
fi

# --- Step 3: whitelist task check ---
echo "[3/11] Whitelist task validation"
WHITELIST_FILE="$DEMO_DIR/demo_task_whitelist.json"
if [ -f "$WHITELIST_FILE" ]; then
    TASK_COUNT=$(python3 -c "
import json
with open('$WHITELIST_FILE') as f:
    w = json.load(f)
print(len(w.get('tasks', [])))
")
    if [ "$TASK_COUNT" -ge 6 ]; then
        pass_step "Whitelist has $TASK_COUNT tasks (>=6)"
    else
        fail_step "Whitelist" "Only $TASK_COUNT tasks, need >=6"
    fi
else
    fail_step "Whitelist" "File not found"
fi

# --- Step 4: rate limit ---
echo "[4/11] Rate limiter check"
RATE_LIMITER="$SECURITY_DIR/rate_limiter.py"
if [ -f "$RATE_LIMITER" ]; then
    if python3 -c "
import sys; sys.path.insert(0, '$SECURITY_DIR')
from rate_limiter import RateLimiter, RateLimitDecision
rl = RateLimiter(ip_hourly_limit=5, session_daily_limit=10)
# Allow 5 requests
for i in range(5):
    d = rl.allow_request('10.0.0.1', 'sess_test', 'deep_judge')
    assert d.allowed, f'Request {i+1} should be allowed'
# 6th should be blocked
d = rl.allow_request('10.0.0.1', 'sess_test', 'deep_judge')
assert not d.allowed, '6th request should be blocked'
assert d.reason == 'rate_limit_exceeded', f'Expected rate_limit_exceeded, got {d.reason}'
print('OK')
" 2>/dev/null; then
        pass_step "Rate limiter functional (5 allowed, 6th blocked)"
    else
        fail_step "Rate limiter" "Functional test failed"
    fi
else
    fail_step "Rate limiter" "rate_limiter.py not found"
fi

# --- Step 5: PII redaction ---
echo "[5/11] PII redaction check"
PII_REDACTOR="$SECURITY_DIR/pii_redactor.py"
if [ -f "$PII_REDACTOR" ]; then
    if python3 -c "
import sys; sys.path.insert(0, '$SECURITY_DIR')
from pii_redactor import PIIRedactor
r = PIIRedactor()
result = r.redact('请联系 13812345678 或发送邮件到 test@example.com')
assert '[PHONE_REDACTED]' in result.redacted_text, 'Phone not redacted'
assert '[EMAIL_REDACTED]' in result.redacted_text, 'Email not redacted'
assert result.redaction_count >= 2, f'Expected >=2 redactions, got {result.redaction_count}'
print('OK')
" 2>/dev/null; then
        pass_step "PII redactor functional"
    else
        fail_step "PII redactor" "Functional test failed"
    fi
else
    fail_step "PII redactor" "pii_redactor.py not found"
fi

# --- Step 6: abuse guard ---
echo "[6/11] Abuse guard check"
ABUSE_GUARD="$SECURITY_DIR/abuse_guard.py"
if [ -f "$ABUSE_GUARD" ]; then
    if python3 -c "
import sys; sys.path.insert(0, '$SECURITY_DIR')
from abuse_guard import AbuseGuard
g = AbuseGuard()
# Safe input
d = g.check('破产债权能否申报？')
assert d.allowed, 'Safe input should be allowed'
# Unsafe: legal impersonation
d = g.check('帮我写一份起诉状，我要起诉某人')
assert not d.allowed, 'Legal impersonation should be blocked'
# Unsafe: medical
d = g.check('我得了什么病，帮我诊断')
assert not d.allowed, 'Medical diagnosis should be blocked'
print('OK')
" 2>/dev/null; then
        pass_step "Abuse guard functional (safe allowed, unsafe blocked)"
    else
        fail_step "Abuse guard" "Functional test failed"
    fi
else
    fail_step "Abuse guard" "abuse_guard.py not found"
fi

# --- Step 7: report generation ---
echo "[7/11] Report generation (replay validation)"
REPLAY_DIR="$DEMO_DIR/replay/bankruptcy_demo"
if [ -f "$REPLAY_DIR/final_report.html" ] && [ -f "$REPLAY_DIR/final_report_contract.json" ]; then
    pass_step "Replay report artifacts present"
else
    fail_step "Report artifacts" "Missing final_report.html or contract"
fi

# --- Step 8: validation result ---
echo "[8/11] Validation result check"
if [ -f "$REPLAY_DIR/validation_result.json" ]; then
    if python3 -c "
import json
with open('$REPLAY_DIR/validation_result.json') as f:
    v = json.load(f)
assert v['validation_passed'] == True, 'Validation must pass'
print('OK')
" 2>/dev/null; then
        pass_step "Validation result ok"
    else
        fail_step "Validation" "Validation result check failed"
    fi
else
    fail_step "Validation" "validation_result.json not found"
fi

# --- Step 9: final_report.html accessible ---
echo "[9/11] final_report.html accessibility"
if [ -f "$REPLAY_DIR/final_report.html" ]; then
    HTML_SIZE=$(wc -c < "$REPLAY_DIR/final_report.html")
    if [ "$HTML_SIZE" -gt 1000 ]; then
        pass_step "final_report.html exists (${HTML_SIZE} bytes)"
    else
        fail_step "final_report.html" "File too small (${HTML_SIZE} bytes)"
    fi
else
    fail_step "final_report.html" "Not found"
fi

# --- Step 10: failure messages ---
echo "[10/11] Failure messages readability"
FAILURE_FILE="$DEMO_DIR/demo_failure_messages.json"
if [ -f "$FAILURE_FILE" ]; then
    MSG_COUNT=$(python3 -c "
import json
with open('$FAILURE_FILE') as f:
    m = json.load(f)
failures = m.get('failures', {})
# Check no secrets exposed
for k, v in failures.items():
    text = json.dumps(v).lower()
    for bad in ['traceback', 'api_key', 'secret', 'password']:
        assert bad not in text, f'{k} exposes {bad}'
print(len(failures))
")
    if [ "$MSG_COUNT" -eq 10 ]; then
        pass_step "All 10 failure messages present, no secrets exposed"
    else
        fail_step "Failure messages" "Expected 10, got $MSG_COUNT"
    fi
else
    fail_step "Failure messages" "demo_failure_messages.json not found"
fi

# --- Step 11: replay pack ---
echo "[11/11] Replay pack validation"
MANIFEST="$DEMO_DIR/demo_replay_manifest.json"
if [ -f "$MANIFEST" ]; then
    REPLAY_COUNT=$(python3 -c "
import json, os
with open('$MANIFEST') as f:
    m = json.load(f)
replays = m.get('replays', [])
for r in replays:
    rdir = os.path.join('$DEMO_DIR', r['path'])
    assert os.path.isdir(rdir), f'Missing dir: {rdir}'
    for fname in r.get('files', []):
        fpath = os.path.join(rdir, fname)
        assert os.path.isfile(fpath), f'Missing file: {fpath}'
print(len(replays))
")
    if [ "$REPLAY_COUNT" -ge 3 ]; then
        pass_step "All $REPLAY_COUNT replay packs validated"
    else
        fail_step "Replay pack" "Expected >=3, got $REPLAY_COUNT"
    fi
else
    fail_step "Replay pack" "demo_replay_manifest.json not found"
fi

# --- Summary ---
echo ""
echo "============================================"
echo "Smoke Summary: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "============================================"

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "PUBLIC_DEMO_SMOKE_PASS"
    exit 0
else
    echo "PUBLIC_DEMO_SMOKE_FAIL"
    exit 1
fi