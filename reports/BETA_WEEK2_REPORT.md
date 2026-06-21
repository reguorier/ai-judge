# Deep-Judge Beta Week 2 外部用户运营报告

**报告日期**: 2026-06-08 | **阶段**: real-beta-week2-external-user | **状态**: PILOT PASS

---

## 1. 执行概览

| 维度 | 数值 |
|------|------|
| 外部用户数 | 7 (目标 >=5) |
| 招募用户数 | 8 (1 名未完成本周任务) |
| 外部任务总数 | 20 |
| 完成任务 | 18 (90%) |
| 降级任务 | 1 (5%) |
| 失败任务 | 1 (5%) |
| Artifact Validation | 95% |
| 平均延迟 | 132.1s |
| 外部反馈总数 | 20 |

---

## 2. 外部用户概览

| 用户ID | 类型 | 招募来源 | 任务数 | 完成任务 | 角色说明 |
|--------|------|----------|--------|----------|----------|
| EXT-U001 | 普通用户 | friend | 3 | 3 | 张某，35岁，非法律背景 - 测可读性 |
| EXT-U002 | PM | friend | 3 | 3 | 李某，科技公司PM - 测产品评估 |
| EXT-U003 | 创始人 | founder_network | 3 | 3 | 王某，A轮创始人 - 测决策类 |
| EXT-U004 | 专业用户 | community | 3 | 2 | 赵某，非法务顾问 - 测法律类 |
| EXT-U005 | 专业用户 | friend | 3 | 3 | 钱某，法务实习生 - 测法律深度 |
| EXT-U006 | 普通用户 | friend | 3 | 3 | 孙某，45岁教育行业 - 测可读性 |
| EXT-U007 | PM | community | 2 | 2 | 周某，金融科技PM - 测数据审计 |

---

## 3. 指标仪表盘

### 3.1 系统指标

| 指标 | 实际值 | 外部阈值 | 结果 |
|------|--------|----------|------|
| Task Completion Rate | 90% (18/20) | >= 80% | PASS |
| Artifact Validation Pass | 95% (19/20) | >= 95% | PASS |
| AJ_REPORT_V1 Validation | 100% | 100% | PASS |
| Avg Latency | 132.1s | <= 180s | PASS |
| No-Source Failure | 100% closed | 100% | PASS |

### 3.2 外部用户反馈指标

| 指标 | 实际值 | 外部阈值 | 结果 |
|------|--------|----------|------|
| can_state_final_answer_rate | 95% | >= 75% | PASS |
| can_state_next_step_rate | 95% | >= 75% | PASS |
| can_explain_why_rate | 74% | >= 65% | PASS |
| avg_trust_score | 3.95 | >= 3.8 | PASS |
| avg_readability_score | 3.42 | >= 3.8 | **FAIL** |
| avg_actionability_score | 3.84 | >= 3.8 | PASS |
| would_use_again_rate | 84% | >= 60% | PASS |

**关键发现**: 可读性 3.42 未达 3.8 阈值。外部普通用户和 PM 在统计术语和法律条文处理上存在显著理解障碍。

---

## 4. Week 1 vs Week 2 差异对比

| 指标 | Week 1 (Internal Proxy) | Week 2 (External Users) | Delta |
|------|------------------------|------------------------|-------|
| avg_trust_score | 4.26 | 3.95 | **-0.31** |
| avg_readability_score | 4.00 | 3.42 | **-0.58** |
| avg_actionability_score | 4.16 | 3.84 | **-0.32** |
| would_use_again_rate | 0.89 | 0.84 | **-0.05** |

**分析**: 外部用户在所有维度均低于内部代理，其中可读性差距最大 (-0.58)。内部代理倾向于高估非专业用户的理解能力，意味着在真实用户场景下，术语通俗化、结论摘要和法律条文分层展示是最高优先级改进项。

---

## 5. 失败复盘摘要

共产生 **6 条** 失败复盘，覆盖 5 种分类：

| # | Failure ID | 分类 | 严重度 | 任务 | 根因 |
|---|-----------|------|--------|------|------|
| 1 | FR-W2-001 | RUNTIME_FAILURE | P0 | BETA-AUDIT-001 | Multi-source audit OOM，无 artifact |
| 2 | FR-W2-002 | USER_CANNOT_UNDERSTAND | P1 | BETA-LEGAL-001 | 法条与结论混杂，普通用户分不清 |
| 3 | FR-W2-003 | REPORT_TOO_TECHNICAL | P1 | BETA-DATA-003 | 统计指标无通俗解释，降级未说明原因 |
| 4 | FR-W2-004 | REPORT_TOO_TECHNICAL | P1 | BETA-DECISION-004 | 统计推断部分纯技术文本，45岁用户完全看不懂 |
| 5 | FR-W2-005 | EVIDENCE_TOO_WEAK | P1 | BETA-PRODUCT-003 | 定价分析缺少中国市场数据 |
| 6 | FR-W2-006 | EVIDENCE_TOO_WEAK | P2 | BETA-DATA-004 | 幻觉检测方法论对PM过深 |

---

## 6. Patch Backlog 摘要

共 **8 条** patch：1 P0 / 5 P1 / 2 P2（含 Week 1 遗留 5 条 + Week 2 新增 3 条）

| 优先级 | 数量 | 描述 |
|--------|------|------|
| P0 | 1 | OOM 硬失败增加 checkpoint artifact |
| P1 | 5 | 降级门控优化 + 分层行动 + 公平性类比 + 法律结论摘要 + locale数据源 |
| P2 | 2 | reader_type术语通俗化 + 方法论分层 |

---

## 7. Confusing Parts Top 5

1. 法律条文与结论混杂，普通用户无法区分 (EXT-U001)
2. 统计推断部分完全看不懂 (EXT-U006)
3. 统计指标 (fairness metrics) 无通俗解释 (EXT-U002)
4. 定价分析缺少中国市场具体数据 (EXT-U003)
5. 幻觉检测原理部分太技术化 (EXT-U007)

---

## 8. 结论与下周建议

### 结论

1. **外部用户可跑通**: 90% 完成率，95% validation 通过，系统稳定
2. **可读性为首要短板**: 外部可读性 3.42 vs 内部 4.00，差距 -0.58，是唯一未达标的反馈指标
3. **reader_type-aware 简化是最紧迫需求**: 3 条 failure review 指向术语通俗化层缺失
4. **数据源本地化不足**: 中国市场的搜索 agent 需要 locale-aware 优先级配置
5. **高风险边界处理正确**: EXT-U003 的 boundary 任务正确降级（trust=4），无安全问题

### 下周建议

1. **优先修复 P0**: 实施 checkpoint artifact 机制避免 audit 类硬失败
2. **reader_type 术语通俗化层**: 合并 PATCH-BETA-W1-004 + PATCH-BETA-W2-002，至少覆盖普通用户场景
3. **是否进入公开 Demo**: 建议再跑一轮 Week 3 修复验证后进入，当前可读性问题对公开用户风险太高
4. **增加外部用户 1-2 名**: EXT-U008（吴某，天使轮创始人）本周未完成，建议 Week 3 补入