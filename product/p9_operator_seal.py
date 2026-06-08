#!/usr/bin/env python3
"""P9 Operator Seal — aggregate baseline status and produce operator seal artifacts."""

import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "ai-judge-p9-operator-seal-v1"

MAINTENANCE_ACTIONS = [
    {"kind": "release_readiness",             "label": "Release Readiness",             "endpoint": "/api/release/readiness",                        "method": "GET"},
    {"kind": "regression",                    "label": "Regression",                     "endpoint": "/api/release/regression",                       "method": "POST"},
    {"kind": "drift_check",                   "label": "Drift Check",                    "endpoint": "/api/release/drift/check",                      "method": "POST"},
    {"kind": "restore_drill",                 "label": "Restore Drill",                  "endpoint": "/api/release/restore-drill",                    "method": "POST"},
    {"kind": "gavel_sync_all",                "label": "Gavel Sync All",                 "endpoint": "/api/gavel/sync-all",                           "method": "POST"},
    {"kind": "claim_calibration_rebuild_all", "label": "Claim Calibration Rebuild All",  "endpoint": "/api/claims/calibration/rebuild-all",            "method": "POST"},
    {"kind": "trust_calibration_refresh",     "label": "Trust Calibration Refresh",      "endpoint": "/api/trust/calibration/refresh",                 "method": "POST"},
    {"kind": "decision_intelligence_refresh", "label": "Decision Intelligence Refresh",  "endpoint": "/api/decision/intelligence/refresh",             "method": "POST"},
]

OPERATOR_BOUNDARY = {
    "allowed_actions": [
        "Run Maintenance Control Center (all 8 actions)",
        "Re-run readiness/regression/drift via scripts or API",
        "Sync gavel via /api/gavel/sync-all",
        "Rebuild claim calibration via /api/claims/calibration/rebuild-all",
        "Restore dry-run via /api/release/restore-drill",
        "Inspect generated-only drift",
        "Read release-readiness / freeze-drift-report",
        "Restart API server if needed",
    ],
    "forbidden_actions": [
        "Modify core code without unfreeze protocol (must start at P10)",
        "Change BUILD_ID without refreshing baseline",
        "Delete files from runs/ or vault/",
        "Bypass trace capture on acceptance",
        "Forge clean/pass status in reports",
        "Mark unexpected drift as intentional without full triage",
        "Modify P0-P9 schema",
        "Skip entry gate for next unfreeze",
    ],
}


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def build_p9_operator_seal(product_dir, runs_dir, vault_dir):
    baseline = load_json(os.path.join(runs_dir, "p9-baseline-refresh.json"))
    readiness = load_json(os.path.join(runs_dir, "release-readiness.json"))
    drift = load_json(os.path.join(runs_dir, "freeze-drift-report.json"))
    triage = load_json(os.path.join(runs_dir, "p9-post-implementation-triage.json"))
    unfreeze = load_json(os.path.join(runs_dir, "unfreeze-request-p9.json"))

    readiness_status = readiness.get("overall_status", "unknown")
    drift_status = drift.get("status", "unknown")
    strict_code_changes = drift.get("strict_code_changes", [])
    unexpected = drift.get("unexpected", [])
    baseline_refreshed = baseline.get("manifest_refreshed", False)

    go_no_go = "STOP"
    if (readiness_status == "pass"
            and drift_status in ("clean", "generated_only")
            and len(strict_code_changes) == 0
            and len(unexpected) == 0
            and baseline_refreshed):
        go_no_go = "GO"

    return {
        "schema_version": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "build_id": baseline.get("build_id", "p8.7-drift-sentinel-e2e-v1"),
        "product_version": "3.8.0-p8.7-drift-sentinel-e2e-v1",
        "readiness_status": readiness_status,
        "drift_status": drift_status,
        "strict_code_changes": [c.get("relative_path", c) for c in strict_code_changes],
        "unexpected": unexpected,
        "go_no_go": go_no_go,
        "maintenance_actions": MAINTENANCE_ACTIONS,
        "operator_boundary": OPERATOR_BOUNDARY,
        "baseline_refreshed": baseline_refreshed,
    }


def write_p9_operator_seal(seal, product_dir, runs_dir, vault_dir):
    json_path = os.path.join(runs_dir, "p9-operator-seal.json")
    with open(json_path, "w") as f:
        json.dump(seal, f, indent=2)
    print(f"  JSON: {json_path}")

    b = seal["build_id"]
    r = seal["readiness_status"]
    d = seal["drift_status"]
    s = seal["strict_code_changes"]
    u = seal["unexpected"]
    g = seal["go_no_go"]

    product_md = os.path.join(product_dir, "P9_OPERATOR_SEAL.md")
    vault_md = os.path.join(vault_dir, "Indexes", "p9-operator-seal.md")

    md = f"""# P9 Operator Seal

## Current Baseline
- Build ID: {b}
- Product Version: {seal["product_version"]}
- Readiness: {r.upper()}
- Drift: {d}
- Strict Code: {len(s)}
- Unexpected: {len(u)}

## P9 Scope Completed
- P9.0 Unfreeze Gate
- P9.1 Scope Definition
- P9.2 Maintenance Control Center
- P9.3 Post-Implementation Triage
- P9.4 Baseline Refresh

## Maintenance Control Center
"""
    for a in MAINTENANCE_ACTIONS:
        md += f"- {a['kind']}\n"

    md += """
## Operator Boundary

### Allowed Actions
"""
    for a in OPERATOR_BOUNDARY["allowed_actions"]:
        md += f"- {a}\n"

    md += "\n### Forbidden Actions\n"
    for f_ in OPERATOR_BOUNDARY["forbidden_actions"]:
        md += f"- {f_}\n"

    md += f"""
## Final Decision
**{g}** — P9 baseline is ready for operator handoff.
"""

    for path in [product_md, vault_md]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(md)
        print(f"  MD: {path}")

    return seal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    seal = build_p9_operator_seal(args.product_dir, args.runs_dir, args.vault_dir)
    print(json.dumps({k: seal[k] for k in ["go_no_go", "readiness_status", "drift_status",
        "strict_code_changes", "unexpected", "baseline_refreshed"]}, indent=2))

    if args.write:
        write_p9_operator_seal(seal, args.product_dir, args.runs_dir, args.vault_dir)

    if seal["go_no_go"] == "GO":
        print("STATUS: GO")
        sys.exit(0)
    else:
        print("STATUS: STOP")
        sys.exit(1)


if __name__ == "__main__":
    main()
（内容由AI生成，仅供参考）
