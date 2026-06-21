#!/bin/bash
# run_reader_type_readability_regression.sh
# Reader Type Readability Patch V1 回归测试
# 确保 reader_type 适配不破坏 AJ_REPORT_V1 默认行为
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================="
echo "Reader Type Readability Regression Suite"
echo "========================================="
echo ""

# Step 1: Profile 验证
echo "[1/6] Verifying reader_type_profiles.json..."
python3 -c "
import json, os, sys
path = os.path.join(os.path.dirname('$SCRIPT_DIR'), '..', 'Library/Application Support/AI Judge/runtime/product/readability/reader_type_profiles.json')
# Try both paths
if not os.path.exists(path):
    path = os.path.expanduser('~/Library/Application Support/AI Judge/runtime/product/readability/reader_type_profiles.json')
with open(path) as f:
    data = json.load(f)
assert 'reader_types' in data, 'Missing reader_types'
for rt in ['ordinary_user', 'pm_founder', 'professional_user', 'legal_compliance_user']:
    assert rt in data['reader_types'], f'Missing {rt}'
    p = data['reader_types'][rt]
    assert 'label' in p, f'{rt} missing label'
    assert 'tone' in p, f'{rt} missing tone'
    assert 'max_sentence_chars' in p, f'{rt} missing max_sentence_chars'
# ordinary_user 禁止术语
ou = data['reader_types']['ordinary_user']
assert len(ou['avoid_terms']) > 0, 'ordinary_user must have avoid_terms'
assert 'hard gate' in ou['avoid_terms'] or 'schema' in ou['avoid_terms'], 'ordinary_user must avoid tech terms'
print('  PASS: All 4 profiles valid')
"

# Step 2: Adapter 单元测试
echo "[2/6] Running reader_type_adapter unit tests..."
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/Library/Application Support/AI Judge/runtime/product'))
from readability.reader_type_adapter import ReaderTypeAdapter, adapt_report_for_reader

# Test 1: ordinary_user removes jargon
report = {
    'headline': 'AI Judge 通过 JSON schema 验证了 hard gate',
    'subtitle': '使用 renderer 渲染 validator 结果',
    'decision_cards': [{'title': 'test', 'verdict': 'pass', 'explanation': '使用了共识矩阵和 embedding'}],
    'next_steps': [{'action': '检查 RAG 幻觉率'}],
    'appendix': {'key': 'val'},
    'hard_gates': [{'name': 'gate1'}]
}
adapted = adapt_report_for_reader(report, 'ordinary_user')
assert 'JSON' not in adapted['headline'], f'JSON not removed: {adapted[\"headline\"]}'
assert 'schema' not in adapted['headline'], f'schema not removed'
assert 'hard gate' not in adapted['headline'], f'hard gate not removed'
assert adapted['appendix'] == {'key': 'val'}, 'appendix modified!'
assert adapted['hard_gates'] == [{'name': 'gate1'}], 'hard_gates modified!'
print('  PASS: Jargon removal + appendix preserved')

# Test 2: ordinary_user adds so_what
report2 = {
    'headline': '结论',
    'decision_cards': [{'title': 'Q1', 'verdict': '有风险', 'action': '补充条款'}],
    'next_steps': [{'action': 'review'}],
    'appendix': {}
}
adapted2 = adapt_report_for_reader(report2, 'ordinary_user')
assert 'so_what' in adapted2['decision_cards'][0], 'so_what missing'
print('  PASS: so_what added')

# Test 3: professional_user preserves evidence
report3 = {
    'headline': '专业审查: 证据强度高',
    'decision_cards': [{'title': 'Q', 'verdict': '通过', 'evidence_strength': 'high', 'uncertainty': 'low'}],
    'appendix': {'evidence': '...'}
}
adapted3 = adapt_report_for_reader(report3, 'professional_user')
assert adapted3['decision_cards'][0].get('evidence_strength') == 'high', 'evidence_strength lost'
assert adapted3['decision_cards'][0].get('uncertainty') == 'low', 'uncertainty lost'
print('  PASS: evidence/uncertainty preserved for professional')
print('  ALL ADAPTER TESTS PASSED')
"

# Step 3: Linter 自测
echo "[3/6] Running readability_linter self-test..."
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/Library/Application Support/AI Judge/runtime/product'))
from readability.readability_linter import lint_report

sample = {
    'headline': 'AI Judge 评估结论：该方案存在中等法律风险',
    'subtitle': '综合分析合同与法规',
    'decision_cards': [
        {'title': '数据隐私', 'verdict': '存在风险', 'explanation': '需获得用户同意',
         'action': '补充数据保护条款', 'so_what': '所以你应该：补充数据保护条款'}
    ],
    'what_if_no_ai_judge': '你可能需要数天查阅法规',
    'blocking_problems': [{'title': '缺少数据保护条款', 'what_it_is': '合同未约定保护措施'}],
    'ai_judge_value': {'title': '价值', 'explanation': '180秒完成分析'},
    'next_steps': [{'action': '补充条款后重新审查'}],
    'appendix': {'full': '...'}
}
result = lint_report(sample, 'ordinary_user')
assert result['score'] >= 85, f'Score too low: {result[\"score\"]}'
assert result['has_final_verdict'], 'missing final verdict'
assert result['has_next_action'], 'missing next action'
assert result['has_so_what'], 'missing so_what'
assert result['appendix_separated'], 'appendix not separated'
print(f'  PASS: Linter score={result[\"score\"]}, all structural checks passed')
"

# Step 4: Metrics 自测
echo "[4/6] Running readability_metrics self-test..."
python3 -c "
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/Library/Application Support/AI Judge/runtime/product'))
from readability.readability_metrics import compute_readability_metrics

reports = [
    {'headline': '结论A', 'decision_cards': [{'title': 'Q', 'verdict': 'OK', 'so_what': '可以'}], 'next_steps': [{'action': 'done'}], 'appendix': {}},
    {'headline': '结论B', 'decision_cards': [{'title': 'Q', 'verdict': 'OK', 'so_what': '可以'}], 'next_steps': [{'action': 'done'}], 'appendix': {}},
]
result = compute_readability_metrics(reports)
assert result['aggregated']['count'] == 2
assert result['aggregated']['avg_score'] > 0
print(f'  PASS: Metrics aggregated, count={result[\"aggregated\"][\"count\"]}')
"

# Step 5: pytest suite
echo "[5/6] Running pytest test suite..."
cd "$PROJECT_ROOT"
pytest tests/test_reader_type_profiles.py tests/test_reader_type_adapter.py \
       tests/test_readability_linter.py tests/test_reader_type_report_variants.py \
       tests/test_beta_week3_readability_metrics.py -q

# Step 6: 汇总
echo "[6/6] Generating summary..."
python3 scripts/summarize_beta_week3_readability.py

echo ""
echo "========================================="
echo "READER_TYPE_READABILITY_REGRESSION_PASS"
echo "========================================="