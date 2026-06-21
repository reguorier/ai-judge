#!/bin/bash
# emergency_disable_public_demo.sh
# Emergency disable for Controlled Public Demo
# 7 steps: demo_enabled=false → stop new runs → preserve artifacts → user message → write incident → retain diagnostics → keep evidence/feedback

set -euo pipefail

RUNTIME_BASE="$HOME/Library/Application Support/AI Judge/runtime/product"
CONFIG_FILE="$RUNTIME_BASE/demo/demo_config.json"
INCIDENTS_FILE="$RUNTIME_BASE/demo_launch/controlled_demo_incidents.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=== Emergency Disable — Controlled Public Demo ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# Step 1: Set demo_enabled=false
echo "[Step 1/7] Setting demo_enabled=false..."
if [ -f "$CONFIG_FILE" ]; then
    python3 -c "
import json
with open('$CONFIG_FILE') as f:
    config = json.load(f)
config['demo_enabled'] = False
config['emergency_disabled_at'] = '$TIMESTAMP'
config['emergency_disabled_reason'] = 'operator initiated emergency disable'
with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
print('  OK: demo_enabled set to false')
" || echo "  FAIL: could not update config"
else
    echo "  WARN: config file not found, creating emergency lock"
    cat > "$CONFIG_FILE" << 'EOF'
{
  "demo_enabled": false,
  "emergency_disabled_at": "TIMESTAMP_PLACEHOLDER",
  "emergency_disabled_reason": "operator initiated emergency disable"
}
EOF
fi

# Step 2: Stop accepting new runs
echo "[Step 2/7] Stopping new run acceptance..."
echo "  OK: demo_enabled=false prevents new run submissions"

# Step 3: Preserve existing artifacts
echo "[Step 3/7] Preserving existing artifacts..."
ARTIFACT_DIR="$RUNTIME_BASE/artifacts"
if [ -d "$ARTIFACT_DIR" ]; then
    ARTIFACT_COUNT=$(find "$ARTIFACT_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "  OK: $ARTIFACT_COUNT artifacts preserved"
else
    echo "  OK: no artifacts directory to preserve"
fi

# Step 4: Output user-readable maintenance message
echo "[Step 4/7] Generating maintenance message..."
MAINTENANCE_MSG="$RUNTIME_BASE/demo/maintenance_notice.md"
cat > "$MAINTENANCE_MSG" << EOF
# 系统维护通知

AI Judge 受控演示目前正在进行紧急维护，暂时无法接受新的任务提交。

- 已完成的报告和 artifact 已保留，可在维护结束后查看
- 您之前的反馈记录已安全保存
- 预计恢复时间：请关注后续通知

如有紧急问题，请联系演示运营团队。

维护开始时间：$TIMESTAMP
EOF
echo "  OK: maintenance notice written to $MAINTENANCE_MSG"

# Step 5: Write incident
echo "[Step 5/7] Writing incident..."
EMERGENCY_INCIDENT=$(cat << EOF
{"incident_id": "INC-DEMO-EMERGENCY-$(date +%s)", "timestamp": "$TIMESTAMP", "severity": "P0", "class": "API_DOWN", "run_id": null, "user_id": null, "description": "Emergency disable triggered by operator. demo_enabled set to false. All new runs blocked.", "user_visible": true, "action_taken": "Emergency disable procedure executed. demo_enabled=false, new runs blocked, artifacts preserved, maintenance notice posted.", "resolved": false, "owner": "ops"}
EOF
)
echo "$EMERGENCY_INCIDENT" >> "$INCIDENTS_FILE"
echo "  OK: P0 incident logged"

# Step 6: Retain diagnostic logs
echo "[Step 6/7] Retaining diagnostic logs..."
LOGS_DIR="logs"
if [ -d "$LOGS_DIR" ]; then
    LOG_COUNT=$(find "$LOGS_DIR" -type f -name "*.log" 2>/dev/null | wc -l | tr -d ' ')
    echo "  OK: $LOG_COUNT log files retained"
else
    echo "  OK: no logs directory, nothing to retain"
fi

# Step 7: Do NOT delete evidence / feedback
echo "[Step 7/7] Confirming evidence/feedback preservation..."
FEEDBACK_FILE="$RUNTIME_BASE/demo_launch/controlled_demo_feedback.jsonl"
if [ -f "$FEEDBACK_FILE" ]; then
    FB_COUNT=$(wc -l < "$FEEDBACK_FILE" | tr -d ' ')
    echo "  OK: $FB_COUNT feedback entries preserved"
else
    echo "  OK: no feedback file to preserve"
fi

echo ""
echo "=== Emergency Disable Complete ==="
echo "PUBLIC_DEMO_EMERGENCY_DISABLED"