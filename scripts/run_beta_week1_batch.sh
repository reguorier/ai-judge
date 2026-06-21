#!/usr/bin/env bash
# run_beta_week1_batch.sh
# Beta Week 1 批量运行脚本
# 功能：读取 beta_task_bank.json → 选取 >=20 tasks → POST /api/runs → 等待 artifacts
#        → 校验 validation → 写入 run_registry → 输出 BETA_WEEK1_BATCH_RUN_PASS
#
# 用法: bash scripts/run_beta_week1_batch.sh
#
# 依赖: curl, jq
# 环境变量: DEEP_JUDGE_API_URL (默认 http://localhost:8080)

set -euo pipefail

API_URL="${DEEP_JUDGE_API_URL:-http://localhost:8080}"
BETA_OPS_DIR="${BETA_OPS_DIR:-/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops}"
REGISTRY_FILE="${BETA_OPS_DIR}/beta_week1_run_registry.json"
TASK_BANK="${BETA_OPS_DIR}/beta_task_bank.json"

# ── 颜色输出 ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── 前置检查 ───────────────────────────────────────────────────────────────────
log_info "Step 1/7: 检查前置依赖..."

if ! command -v curl &>/dev/null; then log_error "curl 未安装"; exit 1; fi
if ! command -v jq &>/dev/null; then log_error "jq 未安装 (brew install jq)"; exit 1; fi
if [[ ! -f "$TASK_BANK" ]]; then log_error "任务库不存在: $TASK_BANK"; exit 1; fi

# ── Step 2: 读取任务库，选取 >=20 tasks ──────────────────────────────────────
log_info "Step 2/7: 读取任务库，选取 >=20 个任务..."

TASK_IDS=$(jq -r '.[].id' "$TASK_BANK" | head -20)
TASK_COUNT=$(echo "$TASK_IDS" | wc -l | tr -d ' ')
log_info "已选取 $TASK_COUNT 个任务（目标 >=20）"

if (( TASK_COUNT < 20 )); then
    log_error "任务数量不足 20（当前 $TASK_COUNT），请先运行 NEXT_PHASE_BETA_OPERATIONS 生成任务库"
    exit 1
fi

# ── Step 3: 初始化 run_registry ───────────────────────────────────────────────
log_info "Step 3/7: 初始化 run_registry..."
echo "[]" > "$REGISTRY_FILE"

# ── Step 4: 按 category 分批提交 POST /api/runs ─────────────────────────────
log_info "Step 4/7: 提交任务到 API..."

REGISTRY_ENTRIES="[]"
RUN_INDEX=0

while IFS= read -r TASK_ID; do
    RUN_INDEX=$((RUN_INDEX + 1))
    RUN_ID="BW1-RUN-$(printf '%03d' $RUN_INDEX)"

    log_info "  [$RUN_INDEX/$TASK_COUNT] 提交 $TASK_ID → $RUN_ID"

    # 从任务库读取任务详情
    TASK_JSON=$(jq -r --arg id "$TASK_ID" '.[] | select(.id == $id)' "$TASK_BANK")
    QUESTION=$(echo "$TASK_JSON" | jq -r '.question')
    CATEGORY=$(echo "$TASK_JSON" | jq -r '.category')
    READER=$(echo "$TASK_JSON" | jq -r '.target_reader')

    # POST /api/runs
    RESPONSE=$(curl -s -X POST "${API_URL}/api/runs" \
        -H "Content-Type: application/json" \
        -d "{\"task_id\":\"${TASK_ID}\",\"question\":\"${QUESTION}\",\"mode\":\"deep_judge\"}" 2>/dev/null || echo "{}")

    API_RUN_ID=$(echo "$RESPONSE" | jq -r '.run_id // empty' 2>/dev/null || echo "")

    if [[ -z "$API_RUN_ID" ]]; then
        log_warn "  API 调用失败或返回为空，使用本地生成的 run_id: $RUN_ID"
        API_RUN_ID="$RUN_ID"
    fi

    # 记录到 registry（初始状态 pending）
    ENTRY=$(jq -n \
        --arg task_id "$TASK_ID" \
        --arg run_id "$API_RUN_ID" \
        --arg category "$CATEGORY" \
        --arg reader_type "$READER" \
        --arg status "pending" \
        --arg created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            task_id: $task_id,
            run_id: $run_id,
            category: $category,
            reader_type: $reader_type,
            status: $status,
            artifact_path: "",
            validation_ok: false,
            latency_sec: 0,
            substantive_sources: [],
            created_at: $created_at
        }')

    REGISTRY_ENTRIES=$(echo "$REGISTRY_ENTRIES" | jq ". + [$ENTRY]")
    echo "$REGISTRY_ENTRIES" | jq '.' > "$REGISTRY_FILE"

    # 避免 API 限流
    sleep 0.5

done <<< "$TASK_IDS"

log_info "已提交 $RUN_INDEX 个任务"

# ── Step 5: 等待 artifacts（轮询 /api/runs/{run_id}）────────────────────────
log_info "Step 5/7: 等待 artifacts 生成（最多等待 300s/任务）..."

UPDATED_ENTRIES="[]"
for entry in $(echo "$REGISTRY_ENTRIES" | jq -c '.[]'); do
    TASK_ID=$(echo "$entry" | jq -r '.task_id')
    API_RUN_ID=$(echo "$entry" | jq -r '.run_id')

    log_info "  等待 $TASK_ID ($API_RUN_ID)..."

    WAITED=0
    STATUS="pending"
    ARTIFACT_PATH=""
    VALIDATION_OK=false
    LATENCY=0

    while (( WAITED < 300 )); do
        RUN_STATUS=$(curl -s "${API_URL}/api/runs/${API_RUN_ID}" 2>/dev/null || echo "{}")
        STATUS=$(echo "$RUN_STATUS" | jq -r '.status // "pending"' 2>/dev/null || echo "pending")

        if [[ "$STATUS" == "completed" || "$STATUS" == "failed" || "$STATUS" == "degraded" ]]; then
            ARTIFACT_PATH=$(echo "$RUN_STATUS" | jq -r '.artifact_path // ""' 2>/dev/null || echo "")
            VALID_OK=$(echo "$RUN_STATUS" | jq -r '.validation_ok // false' 2>/dev/null || echo "false")
            LATENCY=$(echo "$RUN_STATUS" | jq -r '.latency_sec // 0' 2>/dev/null || echo "0")
            break
        fi

        sleep 5
        WAITED=$((WAITED + 5))
    done

    if (( WAITED >= 300 )); then
        log_warn "  $TASK_ID 等待超时，标记为 failed"
        STATUS="failed"
    fi

    UPDATED_ENTRY=$(echo "$entry" | jq \
        --arg status "$STATUS" \
        --arg artifact_path "$ARTIFACT_PATH" \
        --argjson validation_ok "$VALIDATION_OK" \
        --argjson latency_sec "$LATENCY" \
        '. + {
            status: $status,
            artifact_path: $artifact_path,
            validation_ok: $validation_ok,
            latency_sec: $latency_sec
        }')

    UPDATED_ENTRIES=$(echo "$UPDATED_ENTRIES" | jq ". + [$UPDATED_ENTRY]")
done

echo "$UPDATED_ENTRIES" | jq '.' > "$REGISTRY_FILE"
log_info "所有任务状态已更新"

# ── Step 6: 校验 validation_result ────────────────────────────────────────────
log_info "Step 6/7: 校验 validation_result..."

COMPLETED=0; FAILED=0; DEGRADED=0
while IFS= read -r entry; do
    STATUS=$(echo "$entry" | jq -r '.status')
    TASK_ID=$(echo "$entry" | jq -r '.task_id')
    VALID_OK=$(echo "$entry" | jq -r '.validation_ok')

    if [[ "$STATUS" == "completed" ]]; then
        COMPLETED=$((COMPLETED + 1))
        if [[ "$VALID_OK" != "true" ]]; then
            log_warn "  $TASK_ID: completed 但 validation_ok=false"
        fi
    elif [[ "$STATUS" == "failed" ]]; then
        FAILED=$((FAILED + 1))
    elif [[ "$STATUS" == "degraded" ]]; then
        DEGRADED=$((DEGRADED + 1))
    fi
done < <(jq -c '.[]' "$REGISTRY_FILE")

# ── Step 7: 输出 task summary ─────────────────────────────────────────────────
log_info "Step 7/7: 输出任务摘要..."
echo ""
echo "=========================================="
echo "  Beta Week 1 Batch Run Summary"
echo "=========================================="
echo "  总任务数 : $TASK_COUNT"
echo "  完成     : $COMPLETED"
echo "  降级     : $DEGRADED"
echo "  失败     : $FAILED"
echo "  完成率   : $(awk "BEGIN {printf \"%.0f%%\", $COMPLETED/$TASK_COUNT*100}")"
echo "=========================================="
echo ""

# ── 输出通过标志 ───────────────────────────────────────────────────────────────
COMPLETION_RATE=$(awk "BEGIN {print $COMPLETED/$TASK_COUNT}")
if (( $(echo "$COMPLETION_RATE >= 0.85" | bc -l) )); then
    log_info "BETA_WEEK1_BATCH_RUN_PASS"
    exit 0
else
    log_error "完成率不足 85%（当前 $(awk "BEGIN {printf \"%.0f%%\", $COMPLETION_RATE*100}")），未通过"
    exit 1
fi
