# P9 Acceptance Criteria

## Prerequisites (Blockers if not met)
- readiness overall_status = pass
- drift status = clean 或 generated_only
- strict_code_changes = []（或全部经过 triage 并标记 intentional）
- entry_decision = approved
- P9.0 gate 仍为 approved

## P9.2 Functional Acceptance

### UI Acceptance
- 维护面板在 dashboard 中可见且可交互
- Release / Drift / Readiness 状态正确聚合
- 快捷按钮可触发对应操作
- Vault index 链接可正确跳转
- 所有 UI 操作在 trace 文件中可见

### API Acceptance
- 所有新 API 返回 HTTP 200（或结构化错误）
- 聚合 summary 端点数据与各独立 report 一致

### Data Safety
- 不删除 runs/vault 中任何数据
- 不覆盖已有 report JSON
- trace 仅追加写入，不覆盖

### Regression
- P0–P8 baseline 功能不受影响
- release_readiness / freeze_drift_sentinel / unfreeze_request 仍可正常运行
- dashboard 原有功能（bridge/state/viewport/log）不受影响

## Stop-Line Rules
以下任一条件触发立即停止 P9.2，回滚所有 P9 变更：
1. readiness 从 pass 变为 fail
2. drift 出现 strict_code_changes（非 generated）
3. 任何 P9 操作导致 runs/vault 数据丢失
4. dashboard 原有功能异常
5. API server 崩溃或返回 500

## Rollback
回滚方法见 P9_ROLLBACK_BOUNDARY.md
