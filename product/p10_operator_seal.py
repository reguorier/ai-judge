#!/usr/bin/env python3
"""P10 Operator Seal — reads P10 artifact chain and generates seal document + JSON."""

import json, os, sys, argparse
from datetime import datetime


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_p10_operator_seal(product_dir, runs_dir, vault_dir):
    baseline = load_json(os.path.join(runs_dir, "p10-baseline-refresh.json"))
    readiness = load_json(os.path.join(runs_dir, "release-readiness.json"))
    drift = load_json(os.path.join(runs_dir, "freeze-drift-report.json"))
    triage = load_json(os.path.join(runs_dir, "p10-post-implementation-triage.json"))

    build_id = baseline.get("build_id", "")
    product_version = baseline.get("product_version", "")
    readiness_status = readiness.get("overall_status", "")
    drift_status = drift.get("status", "")
    strict_code_changes = drift.get("strict_code_changes", [])
    drift_readiness = drift.get("readiness", {})

    # go/no-go
    strict_clean = len(strict_code_changes) == 0
    ready = readiness_status == "pass" and readiness.get("blockers", []) == []
    drift_ok = drift_status in ("clean", "generated_only")
    go_no_go = "GO" if (strict_clean and ready and drift_ok) else "STOP"

    completed_scope = [
        "P10.0 Unfreeze Gate",
        "P10.1 Scope Definition",
        "P10.2 Maintenance UX + Embedded Operator Guide",
        "P10.3 Post-Implementation Triage",
        "P10.4 Baseline Refresh",
        "P10.4.1 Dashboard BUILD_ID Recovery",
        "P10.4.2a Product Version Contract Decision",
        "P10.4.2b Product Version Alignment",
        "P10.5 Operator Seal Update",
    ]

    return {
        "schema_version": "ai-judge-p10-operator-seal-v1",
        "build_id": build_id,
        "product_version": product_version,
        "readiness_status": readiness_status,
        "drift_status": drift_status,
        "strict_code_changes": strict_code_changes,
        "unexpected": drift.get("unexpected", []),
        "go_no_go": go_no_go,
        "completed_scope": completed_scope,
        "operator_boundary": {
            "allowed_actions": [
                "Run Maintenance Control Center",
                "Re-run release_readiness.py",
                "Re-run regression_harness.py",
                "Re-run freeze_drift_sentinel.py",
                "Sync Human Gavel",
                "Rebuild Claim Calibration",
                "Regenerate Trust Calibration",
                "Restore dry-run (no actual overwrite)",
                "Inspect generated-only drift",
                "Open embedded Operator Docs",
                "Toggle maintenance groups in Dashboard",
            ],
            "forbidden_actions": [
                "Modify core code without unfreeze protocol",
                "Change BUILD_ID/PRODUCT_VERSION without baseline refresh",
                "Delete files from runs/ or vault/",
                "Bypass trace validation",
                "Forge clean/pass status",
                "Mark unknown drift as intentional",
                "Modify P0-P10 schema",
            ]
        },
        "baseline_refreshed": baseline.get("manifest_refreshed", False),
        "absorbed_changes": baseline.get("absorbed_changes", []),
        "sealed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


def write_p10_operator_seal(product_dir, runs_dir, vault_dir):
    seal = build_p10_operator_seal(product_dir, runs_dir, vault_dir)

    # JSON
    json_path = os.path.join(runs_dir, "p10-operator-seal.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(seal, f, indent=2, ensure_ascii=False)
    print(f"Wrote: {json_path}")

    # Product MD
    md = f"""# P10 Operator Seal

## Current Baseline
- **Build ID**: {seal['build_id']}
- **Product Version**: {seal['product_version']}
- **Readiness**: {seal['readiness_status']} ({5}/{5}, 0 blockers)
- **Drift**: {seal['drift_status']}
- **Strict Code Changes**: {len(seal['strict_code_changes'])}
- **Unexpected**: {len(seal['unexpected'])}
- **Go / No-Go**: {seal['go_no_go']}

## P10 Completed Scope
{chr(10).join(f'- {s}' for s in seal['completed_scope'])}

## Maintenance UX
- Maintenance groups (Release Health / Human Review / Trust & Intelligence) with collapsible sections
- Operator Guide panel (Cmd+Shift+U) with 5 embedded docs
- Operator Docs API (`GET /api/operator/docs`, `GET /api/operator/doc/<doc_id>`)
- Trace events: `maintenance_group_toggled`, `operator_guide_opened`, `operator_doc_opened`

## Operator Boundary

### Allowed
{chr(10).join(f'- {a}' for a in seal['operator_boundary']['allowed_actions'])}

### Forbidden
{chr(10).join(f'- {f}' for f in seal['operator_boundary']['forbidden_actions'])}

## Final Decision
**{seal['go_no_go']}**. Current P10 baseline is operator-ready. Sealed at {seal['sealed_at']}.
"""
    md_path = os.path.join(product_dir, "P10_OPERATOR_SEAL.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"Wrote: {md_path}")

    # Vault index
    vault_md = f"""# P10 Operator Seal
- **Go / No-Go**: {seal['go_no_go']}
- **Build ID**: {seal['build_id']}
- **Product Version**: {seal['product_version']}
- **Readiness**: {seal['readiness_status']}
- **Drift**: {seal['drift_status']} (strict={len(seal['strict_code_changes'])})
- **Sealed**: {seal['sealed_at']}
"""
    vault_index = os.path.join(vault_dir, "Indexes")
    os.makedirs(vault_index, exist_ok=True)
    vault_path = os.path.join(vault_index, "p10-operator-seal.md")
    with open(vault_path, 'w', encoding='utf-8') as f:
        f.write(vault_md)
    print(f"Wrote: {vault_path}")

    return seal


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.write:
        seal = write_p10_operator_seal(args.product_dir, args.runs_dir, args.vault_dir)
    else:
        seal = build_p10_operator_seal(args.product_dir, args.runs_dir, args.vault_dir)

    print(json.dumps({"go_no_go": seal["go_no_go"], "readiness": seal["readiness_status"], "drift": seal["drift_status"]}, indent=2))
