# P10 Problem Candidates

## Summary

Total candidates: 7
Recommended for P10.1: P10-A, P10-B

## Candidates

### P10-A: Maintenance Center 交互体验增强

- **Risk Level**: low
- **Problem**: 当前 Maintenance Control Center 为纯 JSON 面板，无进度可视化、无操作日志回放、无快捷重试。运维人员在执行 maintenance actions 时缺少实时反馈与历史追溯。
- **Expected Value**: 增加 action 进度条、操作时间线、上次执行时间/状态标记、一键重试按钮；Dashboard 上直观展示 8 个 maintenance actions 的最新状态。
- **Affected Files**: dashboard.js, dashboard.html
- **Affected APIs**: /api/release/readiness, /api/release/regression, /api/release/drift/check, /api/gavel/sync-all, /api/claims/calibration/rebuild-all, /api/trust/calibration/refresh, /api/decision/intelligence/refresh, /api/release/restore-drill
- **Schema Change**: No
- **Core Logic Change**: No
- **Recommended**: Yes

### P10-B: Operator Guide 内置到 Dashboard

- **Risk Level**: low
- **Problem**: OPERATOR_GUIDE.md 和 REGRESSION_CHECKLIST.md 仅存在于文件系统，Dashboard 无内嵌帮助入口。运维人员需要在 Dashboard 和文档间切换，效率低。
- **Expected Value**: Dashboard 新增 Help/Guide 面板，内嵌 operator guide 摘要、快速参考卡片，并支持一键跳转完整文档。
- **Affected Files**: dashboard.js, dashboard.html
- **Affected APIs**: None
- **Schema Change**: No
- **Core Logic Change**: No
- **Recommended**: Yes

### P10-C: 一键导出完整交付包

- **Risk Level**: low
- **Problem**: 交付时需要手动打包 runs/、product/、vault/ 等多个目录，缺少一键导出为 zip/tar.gz 的 Dashboard 操作入口。
- **Expected Value**: Dashboard 增加 Export Delivery Package 按钮，一键打包 runs + product + vault Indexes + trace 为带时间戳的压缩包。
- **Affected Files**: dashboard.js, dashboard.html, api_server.py
- **Affected APIs**: /api/release/export
- **Schema Change**: No
- **Core Logic Change**: No
- **Recommended**: No

### P10-D: Trust Calibration 解释视图

- **Risk Level**: medium
- **Problem**: /api/trust/calibration/refresh 返回纯 JSON，无可视化解释。运维人员不理解 trust 分数的构成与变化趋势。
- **Expected Value**: Dashboard 增加 Trust Calibration 面板，展示分数分布、趋势图、关键因子分解，并附简短解释。
- **Affected Files**: dashboard.js, dashboard.html
- **Affected APIs**: /api/trust/calibration/refresh
- **Schema Change**: No
- **Core Logic Change**: Yes
- **Recommended**: No

### P10-E: Gavel/Claim 复核批处理 UX

- **Risk Level**: medium
- **Problem**: gavel_sync_all 和 claim_calibration_rebuild_all 执行后仅返回计数，缺少每一项的逐条审核界面。人工复核困难。
- **Expected Value**: Dashboard 增加逐条 gavel/claim 审核界面，支持 approve/reject/flag 批量操作，附带 diff 视图。
- **Affected Files**: dashboard.js, dashboard.html
- **Affected APIs**: /api/gavel/sync-all, /api/claims/calibration/rebuild-all
- **Schema Change**: No
- **Core Logic Change**: Yes
- **Recommended**: No

### P10-F: Run Universe gaps 修复助手

- **Risk Level**: low
- **Problem**: run 文件分散在 runs/ 目录下，缺少完整性检查——可能出现缺失的 trace、孤儿 run 或重复 run_id。当前需人工排查。
- **Expected Value**: Dashboard 增加 Run Universe Integrity Check 面板，自动扫描 runs/ 目录，标记异常 run 并给出修复建议。
- **Affected Files**: dashboard.js, dashboard.html
- **Affected APIs**: None
- **Schema Change**: No
- **Core Logic Change**: No
- **Recommended**: No

### P10-G: Electron 点击层稳定性专项

- **Risk Level**: high
- **Problem**: macOS 26.x + Electron 环境下 Dashboard 偶现点击穿透、z-index 层叠异常，导致按钮不可点击。需专项排查与修复。
- **Expected Value**: 修复 Electron 窗口层叠问题；增加点击事件隔离层；添加 e2e 稳定性测试用例覆盖关键交互路径。
- **Affected Files**: dashboard.js, dashboard.html
- **Affected APIs**: None
- **Schema Change**: No
- **Core Logic Change**: No
- **Recommended**: No
