#!/usr/bin/env python3
"""
P10.1 Scope Definition
Phase: P10.1 — Define implementation scope for P10.
Purpose: Produce scope decision JSON, validate gate, and write all P10.1 docs.
Outputs: p10-scope-definition.json, P10_SCOPE_DEFINITION.md, P10_IMPLEMENTATION_PLAN.md,
          P10_ACCEPTANCE_CRITERIA.md, P10_ROLLBACK_PLAN.md
"""

import argparse, json, os
from datetime import datetime, timezone

SELECTED_SCOPE = ["P10-A", "P10-B"]
NON_SCOPE = [
    "P10-C (Export delivery package)",
    "P10-D (Trust Calibration explanation view — requires core logic change)",
    "P10-E (Gavel/Claim batch review UX — requires core logic change)",
    "P10-F (Run Universe gaps repair assistant)",
    "P10-G (Electron click-layer stability — high risk)",
    "AI Judge verdict logic",
    "Hermes/Gavel/Claim/Trust schema",
    "New core API beyond thin doc-reading wrappers",
    "BUILD_ID change (deferred to post-P10.2 process)",
]

AFFECTED_FILES = [
    "dashboard.js",
    "dashboard.html",
]

AFFECTED_APIS = [
    # thin read-only wrappers for operator docs if needed
]

ACCEPTANCE_CRITERIA = [
    "Maintenance Center panel still shows all 8 maintenance actions",
    "All 8 maintenance actions remain executable and write maintenance_action_clicked/maintenance_action_result trace events",
    "Operator Guide panel opens from Dashboard UI",
    "Document links/summaries (OPERATOR_GUIDE.md, REGRESSION_CHECKLIST.md) are readable in Dashboard",
    "release_readiness = pass (5/5, 0 blockers)",
    "freeze drift = generated_only (or strict changes triaged as intentional)",
    "no schema changes",
    "no runs/vault deletions",
    "UI trace events emitted: operator_doc_opened, maintenance_group_toggled",
]

REQUIRED_REGRESSION = [
    "release_readiness",
    "freeze_drift_sentinel",
    "regression",
    "maintenance_action_trace (all 8 actions)",
]

ROLLBACK_ITEMS = [
    "dashboard.js — revert P10.2 UI modifications",
    "dashboard.html — revert P10.2 HTML modifications",
    "api_server.py — revert any thin doc-reading wrappers added in P10.2",
]

ROLLBACK_EXCLUSIONS = [
    "P0-P9 data artifacts (runs/, vault/)",
    "P0-P9 operator documentation",
    "P10.0/P10.1 planning documents",
]


def generate_md_docs(product_dir, runs_dir, vault_dir, build_id):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def write_md(filename, content):
        with open(os.path.join(product_dir, filename), "w") as f:
            f.write(content)

    # P10_SCOPE_DEFINITION.md
    scope_md = f"""# P10 Scope Definition

**Generated**: {ts}
**Build ID**: {build_id}

## Selected Scope

- **P10-A**: Maintenance Center interactive experience enhancement
- **P10-B**: Operator Guide embedded in Dashboard

## Goals

- Make Maintenance Center more usable with progress feedback and action grouping
- Embed key Operator Guide content directly in the Dashboard UI
- Do NOT change underlying AI Judge verdict logic, calibration, or schema

## Non-Scope

{chr(10).join(f'- {item}' for item in NON_SCOPE)}

## Affected Files

{chr(10).join(f'- {f}' for f in AFFECTED_FILES)}

## Affected APIs

None (or thin read-only doc wrappers only).

## Scope Decision

**APPROVED** — risk_level=low, no schema change, no core logic change.
"""
    write_md("P10_SCOPE_DEFINITION.md", scope_md)

    # P10_IMPLEMENTATION_PLAN.md
    plan_md = f"""# P10 Implementation Plan

**Generated**: {ts}
**Build ID**: {build_id}

## P10.2 Executable Items

### 1. Maintenance Center Action Grouping / Collapse
- Group 8 maintenance actions into categories (Readiness / Calibration / Recovery)
- Add collapsible sections with expand/collapse toggle
- Show action count per group

### 2. Action Metadata Enhancement
- Each action shows: description, risk level (low/medium), last execution time, last result (pass/fail/error)
- Color-coded status indicators
- Tooltip with full action documentation

### 3. Operator Guide Summary Card
- New panel/tab in Dashboard: "Operator Guide"
- Shows key sections: Maintenance Control Center, Boundary Rules, Quick Reference
- One-click access to full documents

### 4. Document Quick Access
- Links to: OPERATOR_GUIDE.md, REGRESSION_CHECKLIST.md
- Inline preview of key sections
- Copy-to-clipboard for CLI commands

### 5. UI Trace Events
- `operator_doc_opened` — fired when any operator document is opened
- `maintenance_group_toggled` — fired when action groups are expanded/collapsed

## Non-Implementation Items
- No backend logic changes
- No schema migrations
- No BUILD_ID modifications
"""
    write_md("P10_IMPLEMENTATION_PLAN.md", plan_md)

    # P10_ACCEPTANCE_CRITERIA.md
    criteria_md = f"""# P10 Acceptance Criteria

**Generated**: {ts}
**Build ID**: {build_id}

## Functional Criteria

{chr(10).join(f'{i+1}. {c}' for i, c in enumerate(ACCEPTANCE_CRITERIA[:-1]))}
9. UI trace events emitted: operator_doc_opened, maintenance_group_toggled

## Regression Criteria

{chr(10).join(f'- {r}' for r in REQUIRED_REGRESSION)}

## Safety Criteria

- No schema changes
- No core logic changes
- No runs/vault deletions
- BUILD_ID unchanged
"""
    write_md("P10_ACCEPTANCE_CRITERIA.md", criteria_md)

    # P10_ROLLBACK_PLAN.md
    rollback_md = f"""# P10 Rollback Plan

**Generated**: {ts}
**Build ID**: {build_id}

## Rollback Scope

Only revert files modified in P10.2:

{chr(10).join(f'- {r}' for r in ROLLBACK_ITEMS)}

## Exclusions (Do NOT Rollback)

{chr(10).join(f'- {r}' for r in ROLLBACK_EXCLUSIONS)}

## Rollback Procedure

1. Restore dashboard.js and dashboard.html from pre-P10.2 backup
2. Remove any thin API wrappers from api_server.py
3. Run: release_readiness, freeze_drift_sentinel, regression
4. Verify all 8 maintenance actions still work
5. Confirm drift returns to generated_only

## Safety

- No P0-P9 data products are affected
- No runs/vault deletions during rollback
"""
    write_md("P10_ROLLBACK_PLAN.md", rollback_md)

    # Vault index
    vault_idx = os.path.join(vault_dir, "Indexes")
    os.makedirs(vault_idx, exist_ok=True)
    with open(os.path.join(vault_idx, "p10-scope-definition.md"), "w") as f:
        f.write(scope_md)


def main():
    parser = argparse.ArgumentParser(description="P10.1 Scope Definition")
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    scope_data = {
        "schema_version": "ai-judge-p10-scope-definition-v1",
        "generated_at": ts,
        "build_id": args.build_id,
        "scope_decision": "approved",
        "selected_scope": SELECTED_SCOPE,
        "non_scope": NON_SCOPE,
        "affected_files": AFFECTED_FILES,
        "affected_apis": AFFECTED_APIS,
        "risk_level": "low",
        "requires_schema_change": False,
        "requires_core_logic_change": False,
        "acceptance_criteria": ACCEPTANCE_CRITERIA,
        "required_regression": REQUIRED_REGRESSION,
        "blockers": [],
        "rollback_items": ROLLBACK_ITEMS,
        "rollback_exclusions": ROLLBACK_EXCLUSIONS,
    }

    if args.write:
        os.makedirs(args.runs_dir, exist_ok=True)
        with open(os.path.join(args.runs_dir, "p10-scope-definition.json"), "w") as f:
            json.dump(scope_data, f, indent=2, ensure_ascii=False)
        generate_md_docs(args.product_dir, args.runs_dir, args.vault_dir, args.build_id)

    print(f"P10.1 Scope Definition — {ts}")
    print(f"scope_decision: {scope_data['scope_decision']}")
    print(f"selected_scope: {SELECTED_SCOPE}")
    print(f"risk_level: {scope_data['risk_level']}")
    print(f"schema_change: {scope_data['requires_schema_change']}")
    print(f"core_logic_change: {scope_data['requires_core_logic_change']}")
    print(f"blockers: {scope_data['blockers']}")


if __name__ == "__main__":
    main()
（内容由AI生成，仅供参考）
