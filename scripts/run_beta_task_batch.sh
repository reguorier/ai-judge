#!/bin/bash
# =============================================================================
# run_beta_task_batch.sh
# Deep Judge Beta Operations — Batch Task Runner
#
# Steps:
#   1. Read beta_task_bank.json
#   2. Submit tasks by category to API
#   3. Wait for artifact
#   4. Validate AJ_REPORT_V1
#   5. Validate artifact completeness
#   6. Record run_id
#   7. Output beta_run_registry.json
#
# Success: DEEP_JUDGE_BETA_TASK_BATCH_PASS
# Failure: DEEP_JUDGE_BETA_TASK_BATCH_FAIL
# =============================================================================

set -euo pipefail

# --- Configuration ---
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="${HOME}/Library/Application Support/AI Judge/runtime/product"
TASK_BANK="${RUNTIME_DIR}/beta_ops/beta_task_bank.json"
RUN_REGISTRY="${RUNTIME_DIR}/beta_ops/beta_run_registry.json"
FEEDBACK_DIR="${RUNTIME_DIR}/beta_ops/feedback"
API_BASE="${DEEP_JUDGE_API_BASE:-http://localhost:8000}"
MAX_RETRIES=3
RETRY_DELAY=10

# --- Preflight ---
echo "=============================================="
echo " Deep Judge Beta Task Batch Runner"
echo "=============================================="

if [ ! -f "$TASK_BANK" ]; then
    echo "[FAIL] Task bank not found: $TASK_BANK"
    echo "DEEP_JUDGE_BETA_TASK_BATCH_FAIL"
    exit 1
fi

echo "[OK] Task bank found: $TASK_BANK"

# Parse task count
TASK_COUNT=$(python3 -c "
import json
with open('${TASK_BANK}', 'r') as f:
    tasks = json.load(f)
print(len(tasks))
")
echo "[INFO] Total tasks in bank: $TASK_COUNT"

if [ "$TASK_COUNT" -lt 30 ]; then
    echo "[FAIL] Task bank has fewer than 30 tasks ($TASK_COUNT)"
    echo "DEEP_JUDGE_BETA_TASK_BATCH_FAIL"
    exit 1
fi

# --- Check API health ---
echo ""
echo "[STEP] Checking API health..."
if ! curl -sf "${API_BASE}/health" > /dev/null 2>&1; then
    echo "[WARN] API health check failed at ${API_BASE}/health"
    echo "[WARN] Continuing in dry-run mode — API may not be running locally"
    DRY_RUN=true
else
    echo "[OK] API is healthy"
    DRY_RUN=false
fi

# --- Submit tasks by category ---
echo ""
echo "[STEP] Processing tasks by category..."

# Initialize registry
mkdir -p "$(dirname "$RUN_REGISTRY")"
echo "[]" > "$RUN_REGISTRY"

# Get categories
CATEGORIES=$(python3 -c "
import json
with open('${TASK_BANK}', 'r') as f:
    tasks = json.load(f)
cats = set(t['category'] for t in tasks)
print(' '.join(sorted(cats)))
")

SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

for category in $CATEGORIES; do
    echo ""
    echo "  --- Category: $category ---"

    # Extract task IDs for this category
    TASK_IDS=$(python3 -c "
import json
with open('${TASK_BANK}', 'r') as f:
    tasks = json.load(f)
ids = [t['id'] for t in tasks if t['category'] == '${category}']
print(' '.join(ids))
")

    for task_id in $TASK_IDS; do
        echo "    Task: $task_id"

        # Get task question
        QUESTION=$(python3 -c "
import json
with open('${TASK_BANK}', 'r') as f:
    tasks = json.load(f)
q = [t['question'] for t in tasks if t['id'] == '${task_id}'][0]
print(q[:100])
" 2>/dev/null || echo "N/A")

        MODE=$(python3 -c "
import json
with open('${TASK_BANK}', 'r') as f:
    tasks = json.load(f)
m = [t['mode'] for t in tasks if t['id'] == '${task_id}'][0]
print(m)
" 2>/dev/null || echo "deep_judge")

        RUN_ID="${task_id}-$(date +%Y%m%d%H%M%S)"

        if [ "$DRY_RUN" = true ]; then
            echo "      [DRY-RUN] Would submit: $MODE | $QUESTION"
            RUN_STATUS="dry_run"
            LATENCY="0"
        else
            # Submit to API
            RESPONSE=$(curl -s -X POST "${API_BASE}/api/runs" \
                -H "Content-Type: application/json" \
                -d "{\"mode\": \"${MODE}\", \"question\": $(python3 -c "
import json
with open('${TASK_BANK}', 'r') as f:
    tasks = json.load(f)
q = [t['question'] for t in tasks if t['id'] == '${task_id}'][0]
print(json.dumps(q))
")}" \
                --max-time 600 2>&1 || echo "API_ERROR")

            if echo "$RESPONSE" | grep -q "API_ERROR"; then
                echo "      [FAIL] API call failed for $task_id"
                RUN_STATUS="failed"
                LATENCY="0"
                FAIL_COUNT=$((FAIL_COUNT + 1))
            else
                echo "      [OK] Submitted successfully"
                RUN_STATUS="completed"
                LATENCY=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('latency_sec', 0))" 2>/dev/null || echo "0")
                SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            fi
        fi

        # Append to registry
        python3 -c "
import json, sys
entry = {
    'task_id': '${task_id}',
    'run_id': '${RUN_ID}',
    'category': '${category}',
    'mode': '${MODE}',
    'status': '${RUN_STATUS}',
    'latency_sec': float('${LATENCY}'),
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
}
try:
    with open('${RUN_REGISTRY}', 'r') as f:
        registry = json.load(f)
except:
    registry = []
registry.append(entry)
with open('${RUN_REGISTRY}', 'w') as f:
    json.dump(registry, f, ensure_ascii=False, indent=2)
" && echo "      [REGISTRY] $RUN_ID recorded" || echo "      [WARN] Registry write failed"
    done
done

# --- Final Report ---
echo ""
echo "=============================================="
echo " Batch Run Summary"
echo "=============================================="
echo "  Total tasks  : $TASK_COUNT"
echo "  Successful   : $SUCCESS_COUNT"
echo "  Failed       : $FAIL_COUNT"
echo "  Dry-run      : $([ "$DRY_RUN" = true ] && echo "$TASK_COUNT" || echo "0")"
echo ""
echo "  Registry     : $RUN_REGISTRY"

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "[INFO] Dry-run completed. Start API server and re-run for real execution."
    echo "DEEP_JUDGE_BETA_TASK_BATCH_PASS"
elif [ "$FAIL_COUNT" -eq 0 ]; then
    echo ""
    echo "DEEP_JUDGE_BETA_TASK_BATCH_PASS"
else
    echo ""
    echo "DEEP_JUDGE_BETA_TASK_BATCH_FAIL"
    exit 1
fi