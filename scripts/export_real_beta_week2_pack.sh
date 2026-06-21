#!/bin/bash
# export_real_beta_week2_pack.sh — 打包所有 Week 2 产物
set -euo pipefail

RUNTIME="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/beta_ops"
REPORTS="/Users/audimacmini/Documents/ai-judge-skill/reports"
SCRIPTS="/Users/audimacmini/Documents/ai-judge-skill/scripts"
TESTS="/Users/audimacmini/Documents/ai-judge-skill/tests"
PROJECT="/Users/audimacmini/Documents/ai-judge-skill"
OUTDIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE="${OUTDIR}/beta_week2_export_${TIMESTAMP}.tar.gz"

echo "=== Exporting Beta Week 2 Artifacts ==="

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

mkdir -p "$TMPDIR/beta_ops" "$TMPDIR/reports" "$TMPDIR/scripts" "$TMPDIR/tests"

# beta_ops files
for f in \
    beta_week2_preflight.md \
    beta_week2_patch_resolution.json \
    beta_week2_user_roster.json \
    beta_week2_consent_template.md \
    beta_week2_run_registry.json \
    beta_week2_feedback.jsonl \
    beta_week2_failure_review.jsonl \
    beta_week2_patch_backlog.json \
    beta_week2_metrics.json; do
    if [ -f "${RUNTIME}/${f}" ]; then
        cp "${RUNTIME}/${f}" "$TMPDIR/beta_ops/"
        echo "  + beta_ops/$f"
    fi
done

# reports
for f in BETA_WEEK2_REPORT.md BETA_WEEK2_EXECUTIVE_SUMMARY.md; do
    if [ -f "${REPORTS}/${f}" ]; then
        cp "${REPORTS}/${f}" "$TMPDIR/reports/"
        echo "  + reports/$f"
    fi
done

# scripts
for f in \
    run_real_beta_week2_batch.sh \
    collect_real_beta_week2_feedback.py \
    summarize_real_beta_week2.py \
    export_real_beta_week2_pack.sh; do
    if [ -f "${SCRIPTS}/${f}" ]; then
        cp "${SCRIPTS}/${f}" "$TMPDIR/scripts/"
        echo "  + scripts/$f"
    fi
done

# tests
for f in \
    test_beta_week2_user_roster_schema.py \
    test_beta_week2_feedback_collection.py \
    test_beta_week2_metrics_summary.py \
    test_beta_week2_external_vs_internal_delta.py \
    test_beta_week2_failure_review.py; do
    if [ -f "${TESTS}/${f}" ]; then
        cp "${TESTS}/${f}" "$TMPDIR/tests/"
        echo "  + tests/$f"
    fi
done

# release seal
if [ -f "${PROJECT}/RELEASE_SEAL_REAL_BETA_WEEK2_EXTERNAL_USER.md" ]; then
    cp "${PROJECT}/RELEASE_SEAL_REAL_BETA_WEEK2_EXTERNAL_USER.md" "$TMPDIR/"
    echo "  + RELEASE_SEAL_REAL_BETA_WEEK2_EXTERNAL_USER.md"
fi

tar -czf "$ARCHIVE" -C "$TMPDIR" .
echo ""
echo "Archive: $ARCHIVE"
FILES_COUNT=$(tar -tzf "$ARCHIVE" | wc -l | tr -d ' ')
SIZE=$(du -h "$ARCHIVE" | cut -f1)
echo "Files: $FILES_COUNT, Size: $SIZE"
echo "EXPORT_COMPLETE"