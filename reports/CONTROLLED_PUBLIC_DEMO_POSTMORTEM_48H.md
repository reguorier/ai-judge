---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: c4c8c10647a8bb7136ce0aa675915c5d_9f921fc2633411f19fb15254006c9bbf
    ReservedCode1: JequhgWefw9gfef1qglAQcHC6CszjgJyFgfpl31h21WMCN/JX/8Gx/MiJo2qSc1ugonuecQbyrSvgxi+E/H5icY4E52TlS7L/gDjxf46z30RKIE6Px93adpYtUMnNqJSNgY7fUOhfpNnoGrEUkSvdZFUBCTXdUZx/gyjH8uKT2n/wYsPTlf6+XTDcEg=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: c4c8c10647a8bb7136ce0aa675915c5d_9f921fc2633411f19fb15254006c9bbf
    ReservedCode2: JequhgWefw9gfef1qglAQcHC6CszjgJyFgfpl31h21WMCN/JX/8Gx/MiJo2qSc1ugonuecQbyrSvgxi+E/H5icY4E52TlS7L/gDjxf46z30RKIE6Px93adpYtUMnNqJSNgY7fUOhfpNnoGrEUkSvdZFUBCTXdUZx/gyjH8uKT2n/wYsPTlf6+XTDcEg=
---

# Controlled Public Demo — 48 小时复盘报告

## 1. 运行窗口
- 开始：2026-06-08 08:00 UTC
- 结束：2026-06-10 08:00 UTC
- 时长：48 小时

## 2. 用户数
10 名外部用户：
- 普通用户：5 人 (DEMO-U001 – DEMO-U005)
- PM：2 人 (DEMO-U006, DEMO-U007)
- 创始人：2 人 (DEMO-U008, DEMO-U009)
- 专业用户：1 人 (DEMO-U010)

## 3. 任务数
20 个 runs，每用户 2 个，覆盖 5 种白名单任务：
- DEMO-LEGAL-001：7 runs
- DEMO-LEGAL-002：5 runs
- DEMO-DECISION-001：5 runs
- DEMO-AUDIT-001：2 runs
- DEMO-PRODUCT-001：1 run

## 4. 完成率
- Completed：18 (90.0%)
- Degraded：1 (5.0%)
- Failed：1 (5.0%)
- 综合成功率：95.0%

## 5. 平均延迟
- 整体平均：50.1s
- Completed 平均：45.8s
- Degraded：125.7s (RUN-DEMO-0013, 知识库冷启动)
- Failed：60.0s (RUN-DEMO-0020, search-agent 超时)

## 6. Trust / Readability / Actionability

### 综合
| 维度 | 平均分 | 阈值 | 结果 |
|------|--------|------|------|
| Trust | 4.16 | ≥3.8 | PASS |
| Readability | 4.07 | ≥3.8 | PASS |
| Actionability | 4.08 | ≥3.8 | PASS |

### 按用户类型
| 类型 | Trust | Readability | Actionability |
|------|-------|-------------|---------------|
| 普通用户 | 4.11 | 4.01 | 4.02 |
| PM | 4.25 | 4.23 | 4.23 |
| 创始人 | 4.18 | 4.03 | 4.10 |
| 专业用户 | 3.90 | 4.00 | 3.90 |

### 按任务类型
| 任务 | Trust | Readability | Actionability |
|------|-------|-------------|---------------|
| DEMO-LEGAL-001 | 4.10 | 4.00 | 4.03 |
| DEMO-LEGAL-002 | 4.00 | 3.96 | 3.90 |
| DEMO-DECISION-001 | 4.24 | 4.12 | 4.20 |
| DEMO-AUDIT-001 | 4.10 | 3.85 | 4.00 |
| DEMO-PRODUCT-001 | 4.37 | 4.30 | 4.33 |

## 7. Would Use Again
- 18/19 评分用户 (94.7%) 表示愿意再次使用
- 唯一不愿再次使用：DEMO-U010（审计任务失败用户）

## 8. Incident 列表

| ID | 严重度 | 类别 | 描述 | 状态 |
|----|--------|------|------|------|
| INC-DEMO-001 | P2 | ARTIFACT_MISSING | search-agent 审计模式超时导致 artifact 缺失 | open |
| INC-DEMO-002 | P2 | REPORT_CONFUSING | 知识库冷启动导致延迟 125.7s | open |

P0 incident：0。

## 9. 失败分类

### 失败任务：RUN-DEMO-0020
- **用户**：DEMO-U010（专业用户）
- **任务**：DEMO-AUDIT-001
- **失败原因**：search-agent 在审计模式下超时（30s），未返回证据链
- **影响**：artifact 未生成，validation 失败
- **根因**：审计模式证据收集需要更长搜索时间，当前 30s 阈值不足
- **修复**：PATCH-DEMO-001 — 将审计模式超时调整为 45s

### 降级任务：RUN-DEMO-0013
- **用户**：DEMO-U007（PM）
- **任务**：DEMO-DECISION-001
- **降级原因**：知识库检索冷启动导致延迟 125.7s（正常 40-50s）
- **影响**：用户体验受影响但结果质量正常
- **修复**：PATCH-DEMO-002 — 增加知识库预热机制

## 10. 用户原话摘录

> "整体不错，对普通人理解合同条款有帮助" — DEMO-U001（普通用户）

> "决策框架清晰，直接能用" — DEMO-U002（普通用户）

> "法律分析到位但落地指导偏弱" — DEMO-U002（普通用户）

> "PM 视角下决策辅助很有价值，希望支持更多产品场景" — DEMO-U006（PM）

> "结果质量尚可，但响应速度需优化" — DEMO-U007（PM，degraded run 用户）

> "对初创公司法律风险快速判断很有帮助" — DEMO-U008（创始人）

> "在风控早期阶段可提供结构化参考" — DEMO-U009（创始人）

> "专业用户视角下法条时效性需关注，但整体方向正确" — DEMO-U010（专业用户）

> "审计任务提交后返回失败，希望增加失败原因说明" — DEMO-U010（专业用户，failed run 用户）

## 11. Patch Backlog

| ID | 优先级 | 组件 | 说明 |
|----|--------|------|------|
| PATCH-DEMO-001 | minor | search-agent audit adapter | 审计超时阈值 30s→45s + 渐进重试 |
| PATCH-DEMO-002 | minor | knowledge-base retriever | 启动时预加载常用索引 |
| PATCH-DEMO-003 | minor | demo_failure_messages.json | 失败信息增强：增加具体下一步建议 |

## 12. 是否建议扩大公开范围

**建议：是，但需先修复 3 条 patch。**

理由：
- 系统安全防线有效（0 P0 incident, 0 PII leak, 0 traceback exposure）
- 用户满意度高（94.7% 愿意再次使用）
- Trust / Readability / Actionability 全面超过阈值
- 仅 1 次失败和 1 次降级，根因已定位

扩大建议：
- 下一阶段目标：20–50 人，覆盖更多行业场景
- 新增任务类型：合同审查、知识产权、数据合规
- 修复 patch backlog 中的 3 条后即可进入 V2

---

**最终标志：CONTROLLED_PUBLIC_DEMO_LAUNCH_V1_PASS**
*（内容由AI生成，仅供参考）*
