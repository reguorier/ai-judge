#!/usr/bin/env python3
"""
P10.0 Unfreeze Request & Problem Selection Gate
Phase: P10.0 — Unfreeze & Candidate Collection
Purpose: Validate P9 seal, collect candidate problems, assess impact, render entry gate decision.
Outputs: p10-unfreeze-request.json, p10-problem-candidates.json, p10-impact-assessment.json
"""

import argparse, json, os, sys
from datetime import datetime, timezone

PROBLEM_CANDIDATES = [
    {
        "id": "P10-A",
        "title": "Maintenance Center 交互体验增强",
        "problem": "当前 Maintenance Control Center 为纯 JSON 面板，无进度可视化、无操作日志回放、无快捷重试。运维人员在执行 maintenance actions 时缺少实时反馈与历史追溯。",
        "expected_value": "增加 action 进度条、操作时间线、上次执行时间/状态标记、一键重试按钮；Dashboard 上直观展示 8 个 maintenance actions 的最新状态。",
        "affected_files": ["dashboard.js", "dashboard.html"],
        "affected_apis": ["/api/release/readiness", "/api/release/regression", "/api/release/drift/check",
                          "/api/gavel/sync-all", "/api/claims/calibration/rebuild-all",
                          "/api/trust/calibration/refresh", "/api/decision/intelligence/refresh",
                          "/api/release/restore-drill"],
        "risk_level": "low",
        "requires_schema_change": False,
        "requires_core_logic_change": False,
        "recommended": True
    },
    {
        "id": "P10-B",
        "title": "Operator Guide 内置到 Dashboard",
        "problem": "OPERATOR_GUIDE.md 和 REGRESSION_CHECKLIST.md 仅存在于文件系统，Dashboard 无内嵌帮助入口。运维人员需要在 Dashboard 和文档间切换，效率低。",
        "expected_value": "Dashboard 新增 Help/Guide 面板，内嵌 operator guide 摘要、快速参考卡片，并支持一键跳转完整文档。",
        "affected_files": ["dashboard.js", "dashboard.html"],
        "affected_apis": [],
        "risk_level": "low",
        "requires_schema_change": False,
        "requires_core_logic_change": False,
        "recommended": True
    },
    {
        "id": "P10-C",
        "title": "一键导出完整交付包",
        "problem": "交付时需要手动打包 runs/、product/、vault/ 等多个目录，缺少一键导出为 zip/tar.gz 的 Dashboard 操作入口。",
        "expected_value": "Dashboard 增加 Export Delivery Package 按钮，一键打包 runs + product + vault Indexes + trace 为带时间戳的压缩包。",
        "affected_files": ["dashboard.js", "dashboard.html", "api_server.py"],
        "affected_apis": ["/api/release/export"],
        "risk_level": "low",
        "requires_schema_change": False,
        "requires_core_logic_change": False,
        "recommended": False
    },
    {
        "id": "P10-D",
        "title": "Trust Calibration 解释视图",
        "problem": "/api/trust/calibration/refresh 返回纯 JSON，无可视化解释。运维人员不理解 trust 分数的构成与变化趋势。",
        "expected_value": "Dashboard 增加 Trust Calibration 面板，展示分数分布、趋势图、关键因子分解，并附简短解释。",
        "affected_files": ["dashboard.js", "dashboard.html"],
        "affected_apis": ["/api/trust/calibration/refresh"],
        "risk_level": "medium",
        "requires_schema_change": False,
        "requires_core_logic_change": True,
        "recommended": False
    },
    {
        "id": "P10-E",
        "title": "Gavel/Claim 复核批处理 UX",
        "problem": "gavel_sync_all 和 claim_calibration_rebuild_all 执行后仅返回计数，缺少每一项的逐条审核界面。人工复核困难。",
        "expected_value": "Dashboard 增加逐条 gavel/claim 审核界面，支持 approve/reject/flag 批量操作，附带 diff 视图。",
        "affected_files": ["dashboard.js", "dashboard.html"],
        "affected_apis": ["/api/gavel/sync-all", "/api/claims/calibration/rebuild-all"],
        "risk_level": "medium",
        "requires_schema_change": False,
        "requires_core_logic_change": True,
        "recommended": False
    },
    {
        "id": "P10-F",
        "title": "Run Universe gaps 修复助手",
        "problem": "run 文件分散在 runs/ 目录下，缺少完整性检查——可能出现缺失的 trace、孤儿 run 或重复 run_id。当前需人工排查。",
        "expected_value": "Dashboard 增加 Run Universe Integrity Check 面板，自动扫描 runs/ 目录，标记异常 run 并给出修复建议。",
        "affected_files": ["dashboard.js", "dashboard.html"],
        "affected_apis": [],
        "risk_level": "low",
        "requires_schema_change": False,
        "requires_core_logic_change": False,
        "recommended": False
    },
    {
        "id": "P10-G",
        "title": "Electron 点击层稳定性专项",
        "problem": "macOS 26.x + Electron 环境下 Dashboard 偶现点击穿透、z-index 层叠异常，导致按钮不可点击。需专项排查与修复。",
        "expected_value": "修复 Electron 窗口层叠问题；增加点击事件隔离层；添加 e2e 稳定性测试用例覆盖关键交互路径。",
        "affected_files": ["dashboard.js", "dashboard.html"],
        "affected_apis": [],
        "risk_level": "high",
        "requires_schema_change": False,
        "requires_core_logic_change": False,
        "recommended": False
    },
]


def validate_baseline_state(product_dir, runs_dir, vault_dir):
    """Verify P9 seal and baseline integrity."""
    results = {}
    seal_path = os.path.join(runs_dir, 'p9-operator-seal.json')
    if not os.path.exists(seal_path):
        results['seal_exists'] = False
        results['seal_error'] = 'p9-operator-seal.json not found'
        return results
    with open(seal_path) as f:
        seal = json.load(f)
    results['seal_exists'] = True
    results['seal_go_no_go'] = seal.get('go_no_go', 'UNKNOWN')
    results['seal_readiness'] = seal.get('readiness_status', 'UNKNOWN')

    readiness_path = os.path.join(runs_dir, 'release-readiness.json')
    with open(readiness_path) as f:
        readiness = json.load(f)
    results['readiness_overall'] = readiness.get('overall_status', 'UNKNOWN')
    results['readiness_blockers'] = readiness.get('blockers', [])

    drift_path = os.path.join(runs_dir, 'freeze-drift-report.json')
    with open(drift_path) as f:
        drift = json.load(f)
    results['drift_status'] = drift.get('status', 'UNKNOWN')
    results['drift_strict'] = drift.get('strict_code_changes', [])
    results['drift_unexpected'] = drift.get('unexpected', [])

    manifest_path = os.path.join(runs_dir, 'FREEZE_MANIFEST_P8.json')
    results['manifest_exists'] = os.path.exists(manifest_path)

    # Check vault integrity
    vault_idx = os.path.join(vault_dir, 'Indexes')
    vault_p9_keys = ['p9-operator-seal.md', 'p9-baseline-refresh.md', 'p9-post-implementation-triage.md']
    if os.path.isdir(vault_idx):
        vault_files = os.listdir(vault_idx)
        results['vault_intact'] = all(any(k in v for v in vault_files) for k in vault_p9_keys)
    else:
        results['vault_intact'] = False

    # Check runs integrity - key files
    runs_files = os.listdir(runs_dir) if os.path.isdir(runs_dir) else []
    runs_key = ['release-readiness.json', 'freeze-drift-report.json', 'FREEZE_MANIFEST_P8.json',
                 'p9-operator-seal.json', 'p9-baseline-refresh.json', 'p9-post-implementation-triage.json']
    results['runs_intact'] = all(f in runs_files for f in runs_key)

    return results


def make_entry_decision(baseline, candidates):
    """Apply P10 entry gate rules."""
    blockers = []

    # Gate 1: Baseline readiness
    if baseline.get('readiness_overall') != 'pass':
        blockers.append('readiness not pass')
    if baseline.get('readiness_blockers'):
        blockers.append(f'readiness has blockers: {baseline["readiness_blockers"]}')

    # Gate 2: Drift must be clean
    if baseline.get('drift_status') not in ('clean', 'generated_only'):
        blockers.append(f'drift status is {baseline["drift_status"]}, not clean/generated_only')
    if baseline.get('drift_strict'):
        blockers.append(f'drift has strict_code_changes: {baseline["drift_strict"]}')
    if baseline.get('drift_unexpected'):
        blockers.append(f'drift has unexpected changes: {baseline["drift_unexpected"]}')

    # Gate 3: Seal exists
    if not baseline.get('seal_exists'):
        blockers.append('P9 operator seal missing')
    elif baseline.get('seal_go_no_go') != 'GO':
        blockers.append(f'seal go_no_go is {baseline.get("seal_go_no_go")}')

    # Gate 4: Manifest & vault/runs intact
    if not baseline.get('manifest_exists'):
        blockers.append('freeze manifest missing')
    if not baseline.get('vault_intact'):
        blockers.append('vault integrity compromised')
    if not baseline.get('runs_intact'):
        blockers.append('runs integrity compromised')

    # Gate 5: At least one candidate meets criteria
    viable = [
        c for c in candidates
        if c['risk_level'] in ('low', 'medium')
        and not c['requires_schema_change']
        and not c['requires_core_logic_change']
    ]
    if not viable:
        blockers.append('no viable candidate (risk=low|medium, no schema/core change)')

    approved = len(blockers) == 0
    return {
        'entry_decision': 'approved' if approved else 'blocked',
        'blockers': blockers,
        'viable_candidates': [c['id'] for c in viable],
        'total_candidates': len(candidates)
    }


def main():
    parser = argparse.ArgumentParser(description='P10.0 Unfreeze Request & Problem Selection Gate')
    parser.add_argument('--product-dir', required=True)
    parser.add_argument('--runs-dir', required=True)
    parser.add_argument('--vault-dir', required=True)
    parser.add_argument('--build-id', required=True)
    parser.add_argument('--product-version', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Step 1: Validate P9 baseline
    baseline = validate_baseline_state(args.product_dir, args.runs_dir, args.vault_dir)

    # Step 2: Entry decision
    decision = make_entry_decision(baseline, PROBLEM_CANDIDATES)

    # Step 3: Impact assessment
    impact = {
        'schema_version': 'ai-judge-p10-impact-assessment-v1',
        'generated_at': ts,
        'build_id': args.build_id,
        'product_version': args.product_version,
        'candidates': [],
    }
    for c in PROBLEM_CANDIDATES:
        impacted_scope = []
        if any('api_server.py' in f for f in c['affected_files']) or c['affected_apis']:
            impacted_scope.append('api')
        if any(f in ('dashboard.js', 'dashboard.html') for f in c['affected_files']):
            impacted_scope.append('frontend')
        if c['requires_core_logic_change']:
            impacted_scope.append('core_logic')
        if c['requires_schema_change']:
            impacted_scope.append('schema')

        impact['candidates'].append({
            'id': c['id'],
            'title': c['title'],
            'risk_level': c['risk_level'],
            'requires_schema_change': c['requires_schema_change'],
            'requires_core_logic_change': c['requires_core_logic_change'],
            'affected_scope': impacted_scope,
            'affected_file_count': len(c['affected_files']),
            'affected_api_count': len(c['affected_apis']),
            'recommended': c['recommended'],
        })
    impact['recommended_for_p10_1'] = [c['id'] for c in PROBLEM_CANDIDATES if c['recommended']]
    impact['entry_decision'] = decision['entry_decision']

    # Step 4: Assemble unfreeze request
    unfreeze = {
        'schema_version': 'ai-judge-p10-unfreeze-request-v1',
        'generated_at': ts,
        'build_id': args.build_id,
        'product_version': args.product_version,
        'unfreeze_phase': 'P10.0',
        'unfreeze_type': 'entry_gate_only',
        'baseline_state': {
            'seal_go_no_go': baseline.get('seal_go_no_go'),
            'readiness': baseline.get('readiness_overall'),
            'drift': baseline.get('drift_status'),
            'strict_code_changes': baseline.get('drift_strict'),
            'unexpected': baseline.get('drift_unexpected'),
            'manifest_exists': baseline.get('manifest_exists'),
            'vault_intact': baseline.get('vault_intact'),
            'runs_intact': baseline.get('runs_intact'),
        },
        'entry_decision': decision,
        'candidate_count': len(PROBLEM_CANDIDATES),
        'recommended_count': len([c for c in PROBLEM_CANDIDATES if c['recommended']]),
        'next_phase': 'P10.1 Scope Definition' if decision['entry_decision'] == 'approved' else 'BLOCKED — resolve blockers first',
    }

    if args.write:
        # Write runs JSON
        os.makedirs(args.runs_dir, exist_ok=True)
        with open(os.path.join(args.runs_dir, 'p10-unfreeze-request.json'), 'w') as f:
            json.dump(unfreeze, f, indent=2, ensure_ascii=False)
        with open(os.path.join(args.runs_dir, 'p10-problem-candidates.json'), 'w') as f:
            json.dump(PROBLEM_CANDIDATES, f, indent=2, ensure_ascii=False)
        with open(os.path.join(args.runs_dir, 'p10-impact-assessment.json'), 'w') as f:
            json.dump(impact, f, indent=2, ensure_ascii=False)

        # Write product MD docs
        def write_md(filename, content):
            with open(os.path.join(args.product_dir, filename), 'w') as f:
                f.write(content)

        # P10_UNFREEZE_REQUEST.md
        md = f"""# P10.0 Unfreeze Request

**Generated**: {ts}
**Build ID**: {args.build_id}
**Product Version**: {args.product_version}
**Phase**: P10.0 — Entry Gate Only

## Baseline Verification

| Field | Value |
|-------|-------|
| P9 Operator Seal | {baseline.get('seal_go_no_go', 'UNKNOWN')} |
| Release Readiness | {baseline.get('readiness_overall', 'UNKNOWN')} |
| Freeze Drift | {baseline.get('drift_status', 'UNKNOWN')} |
| Strict Code Changes | {len(baseline.get('drift_strict', []))} |
| Unexpected Changes | {baseline.get('drift_unexpected')} |
| Freeze Manifest | {'Present' if baseline.get('manifest_exists') else 'MISSING'} |
| Vault Integrity | {'Intact' if baseline.get('vault_intact') else 'COMPROMISED'} |
| Runs Integrity | {'Intact' if baseline.get('runs_intact') else 'COMPROMISED'} |

## Entry Gate Decision

**Decision**: {decision['entry_decision'].upper()}

### Blockers

{chr(10).join(f'- {b}' for b in decision['blockers']) if decision['blockers'] else 'None'}

### Viable Candidates

{chr(10).join(f'- {c}' for c in decision['viable_candidates']) if decision['viable_candidates'] else 'None'}

### Next Phase

{unfreeze['next_phase']}
"""
        write_md('P10_UNFREEZE_REQUEST.md', md)

        # P10_PROBLEM_CANDIDATES.md
        candidates_md = f"""# P10 Problem Candidates

## Summary

Total candidates: {len(PROBLEM_CANDIDATES)}
Recommended for P10.1: {', '.join(impact['recommended_for_p10_1'])}

## Candidates

"""
        for c in PROBLEM_CANDIDATES:
            candidates_md += f"""### {c['id']}: {c['title']}

- **Risk Level**: {c['risk_level']}
- **Problem**: {c['problem']}
- **Expected Value**: {c['expected_value']}
- **Affected Files**: {', '.join(c['affected_files'])}
- **Affected APIs**: {', '.join(c['affected_apis']) if c['affected_apis'] else 'None'}
- **Schema Change**: {'Yes' if c['requires_schema_change'] else 'No'}
- **Core Logic Change**: {'Yes' if c['requires_core_logic_change'] else 'No'}
- **Recommended**: {'Yes' if c['recommended'] else 'No'}

"""
        write_md('P10_PROBLEM_CANDIDATES.md', candidates_md)

        # P10_IMPACT_ASSESSMENT.md
        impact_md = f"""# P10 Impact Assessment

## Overview

| Candidate | Risk | Schema Change | Core Logic Change | Affected Scope | Recommended |
|-----------|------|---------------|-------------------|----------------|-------------|
"""
        for ci in impact['candidates']:
            impact_md += f"| {ci['id']} | {ci['risk_level']} | {'Yes' if ci['requires_schema_change'] else 'No'} | {'Yes' if ci['requires_core_logic_change'] else 'No'} | {', '.join(ci['affected_scope'])} | {'Yes' if ci['recommended'] else 'No'} |\n"

        impact_md += f"""
## Recommended for P10.1 Scope Definition

{', '.join(impact['recommended_for_p10_1'])}

## Entry Decision

{decision['entry_decision'].upper()}
"""
        write_md('P10_IMPACT_ASSESSMENT.md', impact_md)

        # P10_ENTRY_GATE.md
        gate_md = f"""# P10 Entry Gate Report

## Decision

**{decision['entry_decision'].upper()}**

## Gate Checks

| Gate | Status | Detail |
|------|--------|--------|
| P9 Operator Seal | {'PASS' if baseline.get('seal_exists') and baseline.get('seal_go_no_go') == 'GO' else 'FAIL'} | go_no_go={baseline.get('seal_go_no_go')} |
| Release Readiness | {'PASS' if baseline.get('readiness_overall') == 'pass' and not baseline.get('readiness_blockers') else 'FAIL'} | {baseline.get('readiness_overall')}, blockers={baseline.get('readiness_blockers')} |
| Freeze Drift | {'PASS' if baseline.get('drift_status') in ('clean','generated_only') and not baseline.get('drift_strict') and not baseline.get('drift_unexpected') else 'FAIL'} | {baseline.get('drift_status')}, strict={len(baseline.get('drift_strict',[]))}, unexpected={baseline.get('drift_unexpected')} |
| Freeze Manifest | {'PASS' if baseline.get('manifest_exists') else 'FAIL'} | {'Present' if baseline.get('manifest_exists') else 'MISSING'} |
| Vault Integrity | {'PASS' if baseline.get('vault_intact') else 'FAIL'} | {'Intact' if baseline.get('vault_intact') else 'COMPROMISED'} |
| Runs Integrity | {'PASS' if baseline.get('runs_intact') else 'FAIL'} | {'Intact' if baseline.get('runs_intact') else 'COMPROMISED'} |
| Viable Candidate | {'PASS' if decision['viable_candidates'] else 'FAIL'} | {decision['viable_candidates'] if decision['viable_candidates'] else 'None'} |

## Blockers

{chr(10).join(f'- {b}' for b in decision['blockers']) if decision['blockers'] else 'None'}

## Next Phase

{unfreeze['next_phase']}
"""
        write_md('P10_ENTRY_GATE.md', gate_md)

        # Write vault index
        vault_idx = os.path.join(args.vault_dir, 'Indexes')
        os.makedirs(vault_idx, exist_ok=True)
        with open(os.path.join(vault_idx, 'p10-unfreeze-request.md'), 'w') as f:
            f.write(md)

    # Print summary
    print(f'P10.0 Unfreeze Request — {ts}')
    print(f'Baseline: readiness={baseline.get("readiness_overall")}, drift={baseline.get("drift_status")}, seal={baseline.get("seal_go_no_go")}')
    print(f'Entry Decision: {decision["entry_decision"].upper()}')
    print(f'Blockers: {decision["blockers"]}')
    print(f'Viable Candidates: {decision["viable_candidates"]}')
    print(f'Total Candidates: {decision["total_candidates"]}')


if __name__ == '__main__':
    main()
