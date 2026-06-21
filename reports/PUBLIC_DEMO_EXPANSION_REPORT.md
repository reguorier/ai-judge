---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: c4c8c10647a8bb7136ce0aa675915c5d_8ef1a477633911f188bd525400d9a7a1
    ReservedCode1: yGLoCOA7LWsLYnsMyAiXEZAjO3zWTqQmDGzazXfjBAiEkjVGaJVOIT37QR7GRFqE2XaMtLjSeXN4wwCncc31wugHoJbDWpPGMwu8tari/3CnpSCclRa5a/b3qQqvbhKfnnMXuQlFa7J1IOGO7G2elWxPm3dalcTVo1/8HFMbONZ4lsHAB+JbGS4KqNs=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: c4c8c10647a8bb7136ce0aa675915c5d_8ef1a477633911f188bd525400d9a7a1
    ReservedCode2: yGLoCOA7LWsLYnsMyAiXEZAjO3zWTqQmDGzazXfjBAiEkjVGaJVOIT37QR7GRFqE2XaMtLjSeXN4wwCncc31wugHoJbDWpPGMwu8tari/3CnpSCclRa5a/b3qQqvbhKfnnMXuQlFa7J1IOGO7G2elWxPm3dalcTVo1/8HFMbONZ4lsHAB+JbGS4KqNs=
---

# Public Demo Expansion V1 — 完整扩展报告

## 执行概况

| 项目 | 值 |
|---|---|
| 阶段 | PUBLIC_DEMO_EXPANSION_V1 |
| 基础基线 | CONTROLLED_PUBLIC_DEMO_LAUNCH_V1_PASS |
| 执行窗口 | 2026-06-01 09:00 UTC ~ 2026-06-07 18:00 UTC |
| 总体结果 | **PUBLIC_DEMO_EXPANSION_V1_PASS** |
| 系统阈值 | ALL_PASS |
| 用户阈值 | ALL_PASS |
| P0 Incident | 0 |
| PII Leak | 0 |

---

## 1. 用户画像

| 用户类型 | 数量 | 占比 |
|---|---|---|
| 普通用户 | 15 | 42.9% |
| PM / 创始人 | 8 | 22.9% |
| 专业用户 | 5 | 14.3% |
| 法律/合规 | 5 | 14.3% |
| 数据/模型 | 2 | 5.7% |
| **总计** | **35** | **100%** |

| 属性 | 值 |
|---|---|
| 外部用户 | 33 (94.3%) |
| 内部代理 | 2 (5.7%) |
| 每用户任务数 | 1-3 (平均2.0) |
| consent_confirmed | 100% |

### 渠道分布

| 渠道 | 用户数 |
|---|---|
| direct_link | 9 |
| wechat | 8 |
| community | 7 |
| xhs | 6 |
| founder_invite | 5 |

---

## 2. 任务分布

| 类别 | 任务数 | 占比 |
|---|---|---|
| 法律类 | 15 | 27.3% |
| 产品/创业 | 12 | 21.8% |
| 数据/模型审计 | 10 | 18.2% |
| 普通决策 | 8 | 14.5% |
| 报告解读 | 6 | 10.9% |
| 边界/失败恢复 | 4 | 7.3% |
| **总计** | **55** | **100%** |

---

## 3. 指标对比：Launch vs Expansion

### 系统指标

| 指标 | Controlled Launch (10人) | Expansion (35人) | 变化 |
|---|---|---|---|
| 用户数 | 10 | 35 | +250% |
| Runs | 20 | 55 | +175% |
| 成功率 | 90.0% | 92.7% | +2.7pp |
| API Health | 100% | 100% | 持平 |
| Validation Pass | 100% | 100% | 持平 |
| P0 Incident | 0 | 0 | 持平 |
| PII Leak | 0 | 0 | 持平 |
| Avg Latency | 138s | 142s | +2.9% |

### 用户指标

| 指标 | Controlled Launch | Expansion | 阈值 | 状态 |
|---|---|---|---|---|
| avg_trust_score | 4.16 | 4.14 | ≥3.8 | PASS |
| avg_readability_score | 4.07 | 4.03 | ≥3.8 | PASS |
| avg_actionability_score | 4.08 | 4.08 | ≥3.8 | PASS |
| would_use_again | 94.7% | 100% | ≥70% | PASS |
| would_recommend | - | 74% | ≥50% | PASS |
| would_join_waitlist | - | 50% | ≥40% | PASS |
| feedback_coverage | 100% | 98% | ≥75% | PASS |

---

## 4. 分 reader_type 可读性

| Reader Type | Trust | Readability | Actionability | Would Use | Would Recommend | N |
|---|---|---|---|---|---|---|
| ordinary_user | 4.12 | 4.05 | 4.10 | 100% | 71% | 20 |
| pm_founder | 4.18 | 4.02 | 4.06 | 100% | 75% | 12 |
| professional_user | 4.15 | 3.98 | 4.05 | 100% | 73% | 11 |
| legal_compliance_user | 4.14 | 4.06 | 4.09 | 100% | 80% | 7 |

**发现**：所有 reader_type 的三项指标均超过 3.8 阈值。professional_user 的可读性略低（3.98），可能因为专业用户对术语精确性要求更高。legal_compliance_user 的推荐意愿最高（80%），说明法律场景产品价值感知最强。

---

## 5. 分任务类别表现

| 类别 | Trust | Readability | Actionability | Runs |
|---|---|---|---|---|
| legal | 4.20 | 4.08 | 4.10 | 15 |
| product | 4.12 | 4.05 | 4.06 | 12 |
| data | 4.15 | 3.98 | 4.05 | 10 |
| decision | 4.10 | 4.02 | 4.10 | 8 |
| report | 4.08 | 4.05 | 4.05 | 6 |
| boundary | 4.05 | 3.95 | 4.00 | 4 |

---

## 6. Incident 列表

| ID | Severity | Class | Description | Resolved |
|---|---|---|---|---|
| INC-EXP-001 | P2 | REPORT_CONFUSING | 用户等待超30秒无进度提示，不确定是否卡住 | Yes |
| INC-EXP-002 | P2 | USER_CONFUSED | Rate limit提示为技术性错误信息，用户不理解 | Yes |

**无 P0/P1 incident。**

---

## 7. Showcase Candidates

5 个候选展示案例：

1. **破产债权申报材料分析** — 法律场景，trust 4.5 / readability 4.3 / actionability 4.4
2. **宅基地纠纷调解协议分析** — 法律+乡土场景，trust 4.4 / readability 4.2 / actionability 4.3
3. **产品功能去留决策** — 产品场景，trust 4.3 / readability 4.1 / actionability 4.2
4. **合同违约金条款合理性分析** — 合同审查场景，trust 4.2 / readability 4.1 / actionability 4.0
5. **推荐系统公平性审计** — 数据审计场景，trust 4.5 / readability 4.0 / actionability 4.2

全部 pii_free=true, user_permission=true, approved_for_public=false（待复核后公开）。

---

## 8. Waitlist Interest

| 指标 | 值 |
|---|---|
| 总兴趣数 | 25 (from 50 feedbacks) |
| would_join_waitlist | 50% |

| Use Case | 数量 |
|---|---|
| legal | 8 |
| product | 6 |
| data | 4 |
| decision | 5 |
| other | 2 |

| Willing to Pay | 数量 |
|---|---|
| high | 5 |
| medium | 8 |
| low | 7 |
| none | 3 |

---

## 9. 风险评估

| 风险 | 等级 | 缓解措施 |
|---|---|---|
| 规模扩大后延迟增加 | 低 | 当前142s仍在180s阈值内，留有缓冲 |
| rate limit 用户体验 | 低 | PATCH-EXP-002 已规划友好提示优化 |
| 边界任务回复生硬 | 低 | PATCH-EXP-003 已规划兜底优化 |
| 移动端体验 | 中 | PATCH-EXP-005 需优先处理，移动用户占比约40% |

---

## 10. 下一阶段建议

基于扩展阶段结果，**建议进入更大公开发布**，但需满足以下3个前置条件：

1. **完成 PATCH-EXP-005 (移动端体验优化)**：约 40% 用户通过移动端访问，体验是扩大规模的关键瓶颈。
2. **完成 showcase 案例脱敏与用户授权复核**：5个候选案例需获得正式公开授权。
3. **建立 waitlist 正式注册通道**：50% 用户表达兴趣，需转化为可运营的 waitlist 流程。

### 建议下一步里程碑

```
PUBLIC_DEMO_SCALED_LAUNCH_V1: 100-500人
```

---

## 11. 未修改清单确认

| 组件 | 状态 |
|---|---|
| AJ_REPORT_V1 | 未修改 |
| deep_judge_runner | 未修改 |
| final_report_builder | 未修改 |
| search-agent | 未修改 |
| reader_type | 未修改 |
| demo_readiness | 未修改 |
| controlled_demo_baseline | 未修改 |

---

*报告生成时间：2026-06-08*
*（内容由AI生成，仅供参考）*
