# P9 Scope Definition

## P9 Theme
Operational Intelligence & Maintenance UX

## Background
P0–P8.18 已冻结，P9.0 Unfreeze Gate 已通过（readiness=pass, drift=generated_only, strict_code_changes=[], entry_decision=approved）。P9 进入规划阶段。

## Proposed P9.2 Scope

### 1. Dashboard Maintenance Panel
- 集中化的维护操作入口（在现有 dashboard UI 中新增维护面板区域）
- Release / Drift / Readiness 状态聚合展示
- Operator 常用动作一键化按钮（重跑 readiness、重跑 drift、重跑 unfreeze）

### 2. Operator Action Trace
- 所有运维操作记录 trace 到 debug-ui-io-trace.jsonl
- trace 包含时间戳、操作名称、结果状态

### 3. Vault Index Links
- 在 dashboard 中提供到 vault index (Obsidian) 的快速链接
- Freeze Report、Drift Report、Readiness Report 查看入口

### 4. API Aggregation (可选)
- 聚合 readiness + drift + entry gate 的轻量 summary endpoint
- 不修改现有 API 返回结构，仅新增只读聚合

## Explicit Non-Scope

以下内容明确不在 P9 范围内：
- 不新增核心 AI 判断逻辑（Gavel / Claim / Trust / Decision Intelligence）
- 不改 Hermes / Gavel / Claim schema
- 不修改 P0–P8 的业务逻辑代码
- 不刷新 freeze manifest 或 baseline
- 不删除 runs/vault 中的历史数据
- 不引入新的外部依赖（除非 scope 文件明确批准）

## Affected Areas
- Dashboard UI: 新增维护面板、状态聚合、快捷按钮
- API: 可选新增只读 summary endpoint
- Release/Drift/Readiness: 聚合展示
- Operator workflows: 一键化 + trace
- Vault indexes: 快速链接

## Risk Level
low

## Scope Decision
approved
