# Werewolf + Prediction Pool Unification

## What was deployed

1. `api_werewolf_pool_contract_patch.py` — API endpoints for:
   - `/api/werewolf/<game_id>/contract` → AJ_REPORT_V1 contract
   - `/api/werewolf/<game_id>/decision-brief` → contract + mode
   - `/api/worldcup-pool/<round_id>/contract` → AJ_REPORT_V1 contract
   - `/api/worldcup-pool/<round_id>/decision-brief` → contract + mode

2. `worldcup_pool_local.html` — Local prediction pool page (no Vercel dependency)

3. `verdict_to_contract_bridge.py` (already deployed) — Auto-routes:
   - mode=werewolf → werewolf contract (headline="AI Judge 狼人杀：X阵营获胜")
   - mode=worldcup_pool → pool contract (headline="AI Judge 预测池结算：X/Y注命中")
   - mode=data_audit → standard data audit contract

## How to use

### Werewolf
1. Start a game: POST /api/werewolf/start
2. Game runs automatically
3. Get contract: GET /api/werewolf/<game_id>/contract
4. Render HTML: pass contract to renderDecisionBriefReport()

### Prediction Pool
1. Open local page: /worldcup_pool_local.html (or rename to /worldcup_pool.html)
2. Start demo: click "开始演示局"
3. Get contract: GET /api/worldcup-pool/<round_id>/contract
4. Render HTML: pass contract to renderDecisionBriefReport()

### Unified pipeline
All three modes (data_audit, werewolf, prediction_pool) flow through:
  verdict_to_report_contract(verdict) → detect_mode() → mode-specific template
  → ReportContractSchema.parse() → renderDecisionBriefReport() → validateRenderedHtml()
