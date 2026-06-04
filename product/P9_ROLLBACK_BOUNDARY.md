# P9 Rollback Boundary

## Allowed Rollback Actions
- 删除 P9 新增的 dashboard.js 代码段（维护面板、按钮、trace、链接）
- 删除 P9 新增的 API 路由（summary endpoint）
- 恢复 dashboard.js 到 P8 freeze backup 版本
- 恢复 api_server.py 到 P8 freeze backup 版本（若仅新增 P9 route）

## Forbidden Rollback Actions
- 不得回滚或删除 P0–P8 历史数据（runs/ JSON、vault/ Indexes）
- 不得删除 freeze manifest 或 baseline
- 不得删除 debug-ui-io-trace.jsonl（仅可移除 P9 trace 行）

## Rollback Procedure
1. 停止 API server 和 dashboard session
2. 从 freeze backup 恢复 dashboard.js 和 api_server.py
3. 删除 P9 新增的 scope/docs 文件（P9_*.md、p9_scope_definition.py）
4. 重启 API server
5. 跑 readiness + drift + unfreeze 确认恢复 P8 baseline
6. 手工从 trace 文件移除 P9 action 行（可选）

## Post-Rollback Verification
- readiness = pass, blockers = []
- drift status = clean 或 generated_only
- strict_code_changes = []
- entry_gate = approved
- dashboard 原有功能正常
- API server 正常运行
