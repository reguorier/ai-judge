#!/bin/bash
# Public Demo Expansion V1 — Export Pack
# Packages expansion artifacts, excluding sensitive/PII/unauthorized showcase data
set -euo pipefail

EXPORT_DIR="/Users/audimacmini/Documents/ai-judge-skill/exports/public_demo_expansion_v1"
RUNTIME_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion"
REPORTS_DIR="/Users/audimacmini/Documents/ai-judge-skill/reports"
SCRIPTS_DIR="/Users/audimacmini/Documents/ai-judge-skill/scripts"
TESTS_DIR="/Users/audimacmini/Documents/ai-judge-skill/tests"
RELEASE_SEAL="/Users/audimacmini/Documents/ai-judge-skill/RELEASE_SEAL_PUBLIC_DEMO_EXPANSION_V1.md"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE="public_demo_expansion_v1_${TIMESTAMP}.tar.gz"

echo "=== Public Demo Expansion V1 — Export Pack ==="

# Clean and create export dir
rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR"/{runtime/product/demo_expansion,reports,scripts,tests}

echo "Step 1: Copying runtime artifacts (non-sensitive)..."
# Copy expansion data — but NOT individual user details with potential PII
cp "$RUNTIME_DIR/expansion_cohort.json" "$EXPORT_DIR/runtime/product/demo_expansion/"
cp "$RUNTIME_DIR/expansion_task_assignments.json" "$EXPORT_DIR/runtime/product/demo_expansion/"
cp "$RUNTIME_DIR/expansion_run_registry.json" "$EXPORT_DIR/runtime/product/demo_expansion/"
cp "$RUNTIME_DIR/expansion_metrics.json" "$EXPORT_DIR/runtime/product/demo_expansion/"
cp "$RUNTIME_DIR/expansion_showcase_candidates.json" "$EXPORT_DIR/runtime/product/demo_expansion/"
cp "$RUNTIME_DIR/expansion_patch_backlog.json" "$EXPORT_DIR/runtime/product/demo_expansion/"
cp "$RUNTIME_DIR/expansion_invitation_copy.md" "$EXPORT_DIR/runtime/product/demo_expansion/"

# Exclude: expansion_feedback.jsonl (may contain free_text with PII clues)
# Exclude: expansion_incidents.jsonl (internal operational data)
# Exclude: expansion_waitlist_interest.jsonl (may contain contact preferences)

echo "Step 2: Copying reports..."
cp "$REPORTS_DIR/PUBLIC_DEMO_EXPANSION_REPORT.md" "$EXPORT_DIR/reports/"
cp "$REPORTS_DIR/PUBLIC_DEMO_EXPANSION_EXECUTIVE_SUMMARY.md" "$EXPORT_DIR/reports/"
cp "$REPORTS_DIR/PUBLIC_DEMO_EXPANSION_CASE_STUDIES.md" "$EXPORT_DIR/reports/"
cp "$REPORTS_DIR/PUBLIC_DEMO_EXPANSION_POSTMORTEM.md" "$EXPORT_DIR/reports/"

echo "Step 3: Copying scripts..."
cp "$SCRIPTS_DIR/run_public_demo_expansion_batch.sh" "$EXPORT_DIR/scripts/"
cp "$SCRIPTS_DIR/collect_public_demo_expansion_feedback.py" "$EXPORT_DIR/scripts/"
cp "$SCRIPTS_DIR/monitor_public_demo_expansion.py" "$EXPORT_DIR/scripts/"
cp "$SCRIPTS_DIR/summarize_public_demo_expansion.py" "$EXPORT_DIR/scripts/"
cp "$SCRIPTS_DIR/select_public_demo_showcase_cases.py" "$EXPORT_DIR/scripts/"

echo "Step 4: Copying tests..."
cp "$TESTS_DIR/test_expansion_cohort_schema.py" "$EXPORT_DIR/tests/"
cp "$TESTS_DIR/test_expansion_feedback_schema.py" "$EXPORT_DIR/tests/"
cp "$TESTS_DIR/test_expansion_metrics.py" "$EXPORT_DIR/tests/"
cp "$TESTS_DIR/test_expansion_showcase_selection.py" "$EXPORT_DIR/tests/"
cp "$TESTS_DIR/test_expansion_waitlist_interest.py" "$EXPORT_DIR/tests/"
cp "$TESTS_DIR/test_expansion_incident_policy.py" "$EXPORT_DIR/tests/"

echo "Step 5: Copying release seal..."
cp "$RELEASE_SEAL" "$EXPORT_DIR/"

echo "Step 6: Creating archive..."
cd "$EXPORT_DIR/.."
tar -czf "$ARCHIVE" "public_demo_expansion_v1"

echo ""
echo "=== Export Complete ==="
echo "Archive: $(pwd)/$ARCHIVE"
echo "Contents:"
tar -tzf "$ARCHIVE" | head -30
echo "..."
echo "Total files: $(tar -tzf "$ARCHIVE" | wc -l | tr -d ' ')"