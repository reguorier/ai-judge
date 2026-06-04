# Manual Drift Review P8.10

**Generated**: 2026-06-03 21:14:28
**Schema**: ai-judge-manual-drift-review-p8-v1
**Total Reviewed**: 28 files

## Summary

| Decision | Count |
|---|---|
| quarantine | 24 |
| keep_intentional | 4 |
| generated | 0 |
| unexpected | 0 |

## Quarantine (24)

Files moved to quarantine — backup/bak/report/changelog patterns, temp pages, stray copies, unreferenced docs.

| # | File | Role | Reason |
|---|---|---|---|
| 1 | x_claim_support_cards.html | product | temp page, 0 refs |
| 2 | x_claim_support_cards.html | src | temp page, 0 refs |
| 3 | pro_early_access.html | product | temp page, 0 refs |
| 4 | pro_early_access.html | src | temp page, 0 refs |
| 5 | dashboard.js.backup_20260531_043523 | product | backup pattern |
| 6 | dashboard.html.backup_20260531_043523 | product | backup pattern |
| 7 | dashboard.js.bak.p23 | product | bak pattern |
| 8 | dashboard.js.bak.p23 | src | bak pattern |
| 9 | dashboard.html.bak.p23 | product | bak pattern |
| 10 | dashboard.html.bak.p23 | src | bak pattern |
| 11 | dashboard.html.marvis-changelog.md | product | changelog, 0 refs |
| 12 | dashboard.html.marvis-changelog.md | src | changelog, 0 refs |
| 13 | restore_wc.sh | product | restore script, 0 refs |
| 14 | hermes_backfill.py | product | standalone, 0 external refs |
| 15 | hermes_backfill.py | src | standalone, 0 external refs |
| 16 | UI_FIX_REPORT.md | product | report, 0 refs |
| 17 | p61_worldcup_pool_product_loop_report.md | src | report, 0 refs |
| 18 | p60_worldcup_pool_visual_qa_report.md | src | report, 0 refs |
| 19 | worldcup_pool.html.p62-backup | src | backup suffix |
| 20 | MONETIZATION.md | product | doc, 0 active refs |
| 21 | MONETIZATION.md | src | doc, 0 active refs |
| 22 | checkout_config.example.json | product | example, 0 active refs |
| 23 | checkout_config.example.json | src | example, 0 active refs |
| 24 | execution_drivers.py | src | root stray; real at core/execution_drivers.py |

## Keep Intentional (4)

Files kept with evidence of active use.

| # | File | Role | Evidence |
|---|---|---|---|
| 1 | __init__.py | product | Python package marker |
| 2 | __init__.py | src | Python package marker |
| 3 | ai-judge-icon.png | product | dashboard.html src refs + api_server.py route |
| 4 | ai-judge-icon.png | src | dashboard.html src refs + api_server.py route |
