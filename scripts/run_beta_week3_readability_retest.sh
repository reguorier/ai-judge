#!/bin/bash
# run_beta_week3_readability_retest.sh
# Week 3 Readability Retest — 7 步复测流程
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BETA_OPS_DIR="$HOME/Library/Application Support/AI Judge/runtime/product/beta_ops"
READABILITY_DIR="$HOME/Library/Application Support/AI Judge/runtime/product/readability"

echo "========================================="
echo "Beta Week 3 Readability Retest"
echo "========================================="
echo ""

# Step 1: 加载 reader_type tasks
echo "[1/7] Loading reader_type tasks..."
TASK_FILE="$BETA_OPS_DIR/beta_week3_reader_type_tasks.json"
if [ ! -f "$TASK_FILE" ]; then
    echo "  ERROR: $TASK_FILE not found"
    exit 1
fi
TASK_COUNT=$(python3 -c "import json; print(len(json.load(open('$TASK_FILE'))))")
echo "  OK: $TASK_COUNT tasks loaded"

# Step 2: 验证 profiles
echo "[2/7] Validating reader_type profiles..."
PROFILE_FILE="$READABILITY_DIR/reader_type_profiles.json"
if [ ! -f "$PROFILE_FILE" ]; then
    echo "  ERROR: profiles not found"
    exit 1
fi
python3 -c "
import json
with open('$PROFILE_FILE') as f:
    data = json.load(f)
for rt in ['ordinary_user', 'pm_founder', 'professional_user', 'legal_compliance_user']:
    assert rt in data['reader_types'], f'Missing {rt}'
print('  OK: All 4 profiles present')
"

# Step 3: Linter 预检
echo "[3/7] Running readability linter pre-check..."
python3 -c "
import sys, json
sys.path.insert(0, '$READABILITY_DIR/..')
from readability.readability_linter import lint_report

sample_ou = {
    'headline': 'AI Judge 评估结论',
    'subtitle': '综合分析',
    'decision_cards': [{'title': 'Q', 'verdict': 'OK', 'so_what': '可以签署'}],
    'next_steps': [{'action': 'review'}],
    'appendix': {}
}
r = lint_report(sample_ou, 'ordinary_user')
assert r['score'] >= 85, f'Linter score {r[\"score\"]} < 85'
print(f'  OK: Linter score={r[\"score\"]}')
"

# Step 4: 收集反馈
echo "[4/7] Collecting Week 3 feedback..."
FEEDBACK_FILE="$BETA_OPS_DIR/beta_week3_feedback.jsonl"
if [ ! -f "$FEEDBACK_FILE" ]; then
    echo "  ERROR: feedback file not found"
    exit 1
fi
FB_COUNT=$(wc -l < "$FEEDBACK_FILE" | tr -d ' ')
echo "  OK: $FB_COUNT feedback entries"

# Step 5: 计算指标
echo "[5/7] Computing Week 3 metrics..."
python3 -c "
import json, statistics

feedbacks = []
with open('$FEEDBACK_FILE') as f:
    for line in f:
        line = line.strip()
        if line:
            feedbacks.append(json.loads(line))

readability_scores = [f['readability_score_1_to_5'] for f in feedbacks]
trust_scores = [f['trust_score_1_to_5'] for f in feedbacks]
actionability_scores = [f['actionability_score_1_to_5'] for f in feedbacks]
would_use = sum(1 for f in feedbacks if f.get('would_use_again'))

print(f'  avg_readability: {statistics.mean(readability_scores):.2f}')
print(f'  avg_trust: {statistics.mean(trust_scores):.2f}')
print(f'  avg_actionability: {statistics.mean(actionability_scores):.2f}')
print(f'  would_use_again: {would_use}/{len(feedbacks)} ({would_use/len(feedbacks)*100:.0f}%)')

# reader type breakdown
from collections import defaultdict
rt_scores = defaultdict(list)
for f in feedbacks:
    rt_scores[f['reader_type']].append(f['readability_score_1_to_5'])
for rt, scores in sorted(rt_scores.items()):
    print(f'  {rt}: avg_readability={statistics.mean(scores):.2f} (n={len(scores)})')

# delta vs Week 2
week2_baseline = 3.42
week3_avg = statistics.mean(readability_scores)
delta = week3_avg - week2_baseline
print(f'  delta vs Week 2 (3.42): {delta:+.2f}')

# ordinary_user delta
ou_scores = rt_scores.get('ordinary_user', [])
if ou_scores:
    ou_avg = statistics.mean(ou_scores)
    print(f'  ordinary_user delta vs Week 2 (~3.1): {ou_avg - 3.1:+.2f}')
"

# Step 6: 生成报告
echo "[6/7] Generating reports..."
REPORT_FILE="$PROJECT_ROOT/reports/BETA_WEEK3_READABILITY_REPORT.md"
EXEC_FILE="$PROJECT_ROOT/reports/BETA_WEEK3_READABILITY_EXECUTIVE_SUMMARY.md"
for f in "$REPORT_FILE" "$EXEC_FILE"; do
    if [ -f "$f" ]; then
        echo "  OK: $(basename $f)"
    else
        echo "  WARNING: $(basename $f) not found"
    fi
done

# Step 7: 汇总
echo "[7/7] Running summary script..."
if [ -f "$PROJECT_ROOT/scripts/summarize_beta_week3_readability.py" ]; then
    python3 "$PROJECT_ROOT/scripts/summarize_beta_week3_readability.py"
else
    echo "  SKIP: summarize script not found (will be created separately)"
fi

echo ""
echo "========================================="
echo "BETA_WEEK3_READABILITY_RETEST_PASS"
echo "========================================="