#!/usr/bin/env bash
# export_beta_week1_pack.sh
# 打包所有 Beta Week 1 产物为 tar.gz
#
# 用法: bash scripts/export_beta_week1_pack.sh [output_dir]
#       默认输出到当前目录

set -euo pipefail

OUTPUT_DIR="${1:-.}"
ARCHIVE_NAME="beta_week1_operations_$(date +%Y%m%d_%H%M%S).tar.gz"
BETA_OPS_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops"
REPORTS_DIR="/Users/audimacmini/Documents/ai-judge-skill/reports"
SCRIPTS_DIR="/Users/audimacmini/Documents/ai-judge-skill/scripts"
PROJECT_DIR="/Users/audimacmini/Documents/ai-judge-skill"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${GREEN}[INFO]${NC} 打包 Beta Week 1 产物..."

# ── 创建临时目录 ──
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

PACK_DIR="$TMPDIR/beta_week1_operations"
mkdir -p "$PACK_DIR/beta_ops"
mkdir -p "$PACK_DIR/reports"
mkdir -p "$PACK_DIR/scripts"
mkdir -p "$PACK_DIR/"

# ── 复制 beta_ops 文件 ──
echo "  复制 beta_ops 文件..."
cp "$BETA_OPS_DIR/beta_week1_plan.md"           "$PACK_DIR/beta_ops/" 2>/dev/null || echo "  [WARN] beta_week1_plan.md 未找到"
cp "$BETA_OPS_DIR/beta_week1_run_registry.json" "$PACK_DIR/beta_ops/" 2>/dev/null || echo "  [WARN] beta_week1_run_registry.json 未找到"
cp "$BETA_OPS_DIR/beta_week1_feedback.jsonl"    "$PACK_DIR/beta_ops/" 2>/dev/null || echo "  [WARN] beta_week1_feedback.jsonl 未找到"
cp "$BETA_OPS_DIR/beta_week1_failure_review.jsonl" "$PACK_DIR/beta_ops/" 2>/dev/null || echo "  [WARN] beta_week1_failure_review.jsonl 未找到"
cp "$BETA_OPS_DIR/beta_week1_patch_backlog.json" "$PACK_DIR/beta_ops/" 2>/dev/null || echo "  [WARN] beta_week1_patch_backlog.json 未找到"
cp "$BETA_OPS_DIR/beta_week1_metrics.json"      "$PACK_DIR/beta_ops/" 2>/dev/null || echo "  [WARN] beta_week1_metrics.json 未找到"

# ── 复制 reports ──
echo "  复制 reports 文件..."
cp "$REPORTS_DIR/BETA_WEEK1_REPORT.md"           "$PACK_DIR/reports/" 2>/dev/null || echo "  [WARN] BETA_WEEK1_REPORT.md 未找到"
cp "$REPORTS_DIR/BETA_WEEK1_EXECUTIVE_SUMMARY.md" "$PACK_DIR/reports/" 2>/dev/null || echo "  [WARN] BETA_WEEK1_EXECUTIVE_SUMMARY.md 未找到"

# ── 复制 scripts ──
echo "  复制 scripts 文件..."
cp "$SCRIPTS_DIR/run_beta_week1_batch.sh"        "$PACK_DIR/scripts/" 2>/dev/null || echo "  [WARN] run_beta_week1_batch.sh 未找到"
cp "$SCRIPTS_DIR/collect_beta_week1_feedback.py" "$PACK_DIR/scripts/" 2>/dev/null || echo "  [WARN] collect_beta_week1_feedback.py 未找到"
cp "$SCRIPTS_DIR/summarize_beta_week1.py"        "$PACK_DIR/scripts/" 2>/dev/null || echo "  [WARN] summarize_beta_week1.py 未找到"
cp "$SCRIPTS_DIR/export_beta_week1_pack.sh"      "$PACK_DIR/scripts/" 2>/dev/null || echo "  [WARN] export_beta_week1_pack.sh 未找到"

# ── 复制 Release Seal ──
echo "  复制 Release Seal..."
cp "$PROJECT_DIR/RELEASE_SEAL_BETA_WEEK1_OPERATIONS.md" "$PACK_DIR/" 2>/dev/null || echo "  [WARN] RELEASE_SEAL_BETA_WEEK1_OPERATIONS.md 未找到"

# ── 生成 MANIFEST ──
echo "  生成 MANIFEST..."
find "$PACK_DIR" -type f | sed "s|$PACK_DIR/||" | sort > "$PACK_DIR/MANIFEST.txt"

# ── 打包 ──
ARCHIVE_PATH="$OUTPUT_DIR/$ARCHIVE_NAME"
cd "$TMPDIR"
tar -czf "$ARCHIVE_PATH" beta_week1_operations
cd - > /dev/null

# ── 输出结果 ──
echo ""
echo "=========================================="
echo "  Beta Week 1 Export Complete"
echo "=========================================="
echo "  Archive : $ARCHIVE_PATH"
echo "  Size    : $(du -h "$ARCHIVE_PATH" | cut -f1)"
echo "  Files   : $(tar -tzf "$ARCHIVE_PATH" | wc -l | tr -d ' ')"
echo "=========================================="
echo ""

echo -e "${GREEN}[INFO]${NC} EXPORT_BETA_WEEK1_PACK_PASS"