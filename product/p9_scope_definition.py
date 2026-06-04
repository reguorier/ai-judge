#!/usr/bin/env python3
"""P9 Scope Definition — generates scope JSON + vault index.

Usage:
  python3 p9_scope_definition.py --product-dir DIR --runs-dir DIR --vault-dir DIR --build-id ID [--write]
"""
import json, os, sys, argparse
from datetime import datetime, timezone

SCHEMA_VERSION = "ai-judge-p9-scope-definition-v1"

def build_p9_scope(product_dir, runs_dir, vault_dir, build_id):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Read current gate statuses
    readiness = {}
    drift = {}
    unfreeze = {}

    rp = os.path.join(runs_dir, "release-readiness.json")
    if os.path.exists(rp):
        readiness = json.load(open(rp))

    dp = os.path.join(runs_dir, "freeze-drift-report.json")
    if os.path.exists(dp):
        drift = json.load(open(dp))

    up = os.path.join(runs_dir, "unfreeze-request-p9.json")
    if os.path.exists(up):
        unfreeze = json.load(open(up))

    readiness_ok = readiness.get("overall_status") == "pass"
    drift_ok = drift.get("status") in ("clean", "generated_only")
    strict_ok = len(drift.get("strict_code_changes", [])) == 0
    entry_ok = unfreeze.get("entry_decision") == "approved"

    blockers = []
    if not readiness_ok:
        blockers.append("readiness not pass")
    if not drift_ok:
        blockers.append(f"drift status={drift.get('status')} not clean/generated_only")
    if not strict_ok:
        blockers.append(f"strict_code_changes={drift.get('strict_code_changes')}")
    if not entry_ok:
        blockers.append("entry gate not approved")

    proposed_scope = [
        "Dashboard Maintenance Panel (集中维护面板)",
        "Release/Drift/Readiness 状态聚合展示",
        "Operator 一键化快捷按钮",
        "Operator Action Trace (操作日志)",
        "Vault Index 快速链接",
        "API Summary Endpoint (可选只读聚合)"
    ]

    non_scope = [
        "No new AI Judge core logic (Gavel/Claim/Trust/Decision Intelligence)",
        "No Hermes/Gavel/Claim schema changes",
        "No P0-P8 business logic modification",
        "No freeze manifest refresh",
        "No runs/vault data deletion",
        "No new external dependencies (unless scope explicitly approved)"
    ]

    affected_files = [
        "dashboard.js (new maintenance panel section only)",
        "api_server.py (optional new summary route only)"
    ]

    affected_apis = [
        "GET /api/p9/summary (new, optional, readonly aggregation)"
    ]

    required_regression = [
        "release_readiness.py: readiness=pass, blockers=[]",
        "freeze_drift_sentinel.py: status=clean/generated_only, strict_code_changes=[]",
        "unfreeze_request.py: entry_decision=approved, entry_blockers=[]",
        "Dashboard smoke: bridge/state/viewport/log functional",
        "API health: GET /api/health returns 200"
    ]

    scope_decision = "approved" if not blockers else "blocked"

    scope = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now,
        "baseline_build_id": build_id,
        "p9_theme": "Operational Intelligence & Maintenance UX",
        "scope_decision": scope_decision,
        "proposed_scope": proposed_scope,
        "non_scope": non_scope,
        "affected_files": affected_files,
        "affected_apis": affected_apis,
        "risk_level": "low" if scope_decision == "approved" else "medium",
        "required_regression": required_regression,
        "entry_conditions": {
            "readiness": readiness.get("overall_status", "unknown"),
            "drift": drift.get("status", "unknown"),
            "entry_gate": unfreeze.get("entry_decision", "unknown")
        },
        "blockers": blockers
    }
    return scope


def write_p9_scope(product_dir, runs_dir, vault_dir, build_id):
    scope = build_p9_scope(product_dir, runs_dir, vault_dir, build_id)

    # Write JSON
    json_path = os.path.join(runs_dir, "p9-scope-definition.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scope, f, indent=2, ensure_ascii=False)
    print(f"P9_SCOPE_JSON_OK: {json_path}")

    # Write vault index
    vault_index_dir = os.path.join(vault_dir, "Indexes")
    os.makedirs(vault_index_dir, exist_ok=True)
    vault_path = os.path.join(vault_index_dir, "p9-scope-definition.md")

    vault_md = f"""# P9 Scope Definition

- **Schema Version**: {scope['schema_version']}
- **Generated At**: {scope['generated_at']}
- **Baseline Build ID**: {scope['baseline_build_id']}

## Theme
{scope['p9_theme']}

## Scope Decision
**{scope['scope_decision']}**

## Risk Level
{scope['risk_level']}

## Proposed P9.2 Scope
"""
    for item in scope['proposed_scope']:
        vault_md += f"- {item}\n"

    vault_md += "\n## Non-Scope\n"
    for item in scope['non_scope']:
        vault_md += f"- {item}\n"

    vault_md += "\n## Entry Conditions\n"
    for k, v in scope['entry_conditions'].items():
        vault_md += f"- **{k}**: {v}\n"

    vault_md += f"\n## Blockers\n"
    if scope['blockers']:
        for b in scope['blockers']:
            vault_md += f"- {b}\n"
    else:
        vault_md += "- None\n"

    with open(vault_path, "w", encoding="utf-8") as f:
        f.write(vault_md)
    print(f"P9_VAULT_SCOPE_OK: {vault_path}")

    return scope


def main():
    p = argparse.ArgumentParser(description="P9 Scope Definition")
    p.add_argument("--product-dir", required=True)
    p.add_argument("--runs-dir", required=True)
    p.add_argument("--vault-dir", required=True)
    p.add_argument("--build-id", required=True)
    p.add_argument("--write", action="store_true", default=False)
    args = p.parse_args()

    scope = write_p9_scope(args.product_dir, args.runs_dir, args.vault_dir, args.build_id)

    print(f"\nP9_SCOPE_DECISION: {scope['scope_decision']}")
    print(f"P9_RISK_LEVEL: {scope['risk_level']}")
    print(f"P9_BLOCKERS: {scope['blockers']}")

    if scope['scope_decision'] == 'blocked':
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
