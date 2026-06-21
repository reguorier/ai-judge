# AI Judge 最终报告

Run ID: `client-8699a9696674`
模式: 运维验收

## FDJP 五维裁决协议审计

**审计模式**：`heuristic_only`（请求）→ `heuristic_only`（实际）

### 专业审计信息

- **audit_mode**: `heuristic_only`
- **effective_mode**: `heuristic_only`
- **status**: `FDJP_CONTENT_BLOCKED`

### 阻塞项
- `PHILOSOPHY_ESSENCE_MISSING`: 未识别问题本质，只复述题面
- `ECONOMY_STAKEHOLDER_MISSING`: 没有识别关键利益方
- `HISTORY_PRECEDENT_REQUIRED_MISSING`: 应有历史/先例/时间线但缺失

### 警告项
- `POWER_MAP_SHALLOW`: 权力结构分析浅
- `NO_FALLBACK_PLAN`: 缺少失败预案
- `FDJP_LLM_UNAVAILABLE_HEURISTIC_ONLY`: 仅启用启发式审计，不能标 FULL_PASS

| 维度 | 得分 | 核心发现 | 行动影响 |
|---|---:|---|---|
| 哲学层｜本质校验 | 0.18 | 未从席位回答中提取到可追溯的 哲学层｜本质校验 结构化断言；不能用题面关键词替代审计发现。 | 待补充 |
| 经济层｜利益结构 | 0.18 | 未从席位回答中提取到可追溯的 经济层｜利益结构 结构化断言；不能用题面关键词替代审计发现。 | 待补充 |
| 政治层｜权力坐标 | 0.39 | 从 1 个来源提取 1 条结构化断言；主约束：权力约束：识别话语权、规则制定者、否决点、组织阻力和治理边界。 代表断言： | 显式标出谁能改规则、谁能否决、谁负责最终放行。 |
| 军事层｜战略执行 | 0.46 | 从 1 个来源提取 2 条结构化断言；主约束：执行约束：在资源有限和风险存在时，确定目标、主攻点、优先级、行动顺序和预案 | 把方案拆成 MVP/P1/P2，并为每段绑定验收和回滚条件。 |
| 历史层｜时间参照 | 0.18 | 未从席位回答中提取到可追溯的 历史层｜时间参照 结构化断言；不能用题面关键词替代审计发现。 | 待补充 |

**FDJP 状态**：`FDJP_CONTENT_BLOCKED`
**整体认知分**：`0.28`

### 五维交叉验证
- 政治层的规则/否决点可能约束执行层速度，必须保留 human gate 和发布门禁。

## 1. 核心结论
针对议题「Check system health」，本报告基于  进行分析。

## 2. 适用边界
本报告基于多源分析生成，用于把议题分析、席位观点、证据强度和风险压缩为可审计结论；不替代人工最终判断。

## 3. 已验证事实
- run_id 已生成：client-8699a9696674（来源：summary.json）
- 本次模式为 运维验收。（来源：summary.json）
- 分析来源：无实质性推理来源（来源：source_pack）

## 4. 推断与判断
- 报告围绕用户议题「Check system health」展开分析。（强度：weak）（来源：template）

## 5. 席位观点摘要
- Report Builder: 压缩问题、证据和行动建议到最终报告。（强度：medium）
- Dissent Reviewer: 保留分歧、失败条件和反方提醒。（强度：medium）
- Human Final Gate: 把最终裁决留给本地人工确认。（强度：medium）

## 6. 共识与分歧
### 共识
- 报告基于可用的分析来源生成。
- 若分析来源不足，结论应标记为低置信度。

### 分歧
- 当分析来源不充分时，不应伪造未执行的席位或检索结果。

## 7. 证据强度
整体强度：high

- 实质性分析来源：无（强度：weak）
- 席位有效性：3/3（强度：medium）

## 8. 风险与失败条件
### 风险
- 当前分析可能未覆盖全部司法辖区的观点差异。
- 法律议题的时效性可能影响结论的准确性。

### 失败条件
- 无 LLM / search-agent / seat_outputs 等实质性推理来源。
- 最终报告未经 report_quality_gate 验证通过。
- 席位矩阵与实际执行状态不一致。

## 9. 推荐行动
- 若结论置信度不足，建议补充联网检索或专业法律数据库查询。
- 重要法律决策应咨询持证律师。

## 10. Noise Audit / 噪声审计
- 噪声分数：18 / 100（low）
- 建议动作：publishable_low_noise
- 有效输出：3/3
- 结论聚类：2
- 置信度离散：0.0
- 证据重叠率：0.3333
- 污染/拒绝/格式失败：0 / 0 / 0
- 主要噪声来源：stance_disagreement、evidence_divergence
- 分歧类型：conclusion_disagreement、evidence_weight_disagreement
- 解读：本轮输出较稳定，主要分歧未显示为系统噪声。

## 11. Model Stability / 模型稳定性画像
- 已画像席位：3
- 累计更新轮次：1
- Dissent Reviewer: 稳定性 100.0/100，有效率 1.0，格式合规 1.0，污染率 0.0，推理模式失败率 0.0
- Human Final Gate: 稳定性 100.0/100，有效率 1.0，格式合规 1.0，污染率 0.0，推理模式失败率 0.0
- Report Builder: 稳定性 100.0/100，有效率 1.0，格式合规 1.0，污染率 0.0，推理模式失败率 0.0

## 12. 审计附件
- 生成时间：2026-06-17T18:24:08+00:00
- 有效席位：3
- 失败席位：0
- artifact: `<local-user-path>/Documents/ai-judge-skill/reports/runs/client-8699a9696674/final_report.md`
- artifact: `<local-user-path>/Documents/ai-judge-skill/reports/runs/client-8699a9696674/final_report.html`
- artifact: `<local-user-path>/Documents/ai-judge-skill/reports/runs/client-8699a9696674/summary.json`
- artifact: `<local-user-path>/Documents/ai-judge-skill/reports/runs/client-8699a9696674/evidence_packet.json`
- artifact: `<local-user-path>/Documents/ai-judge-skill/reports/runs/client-8699a9696674/seat_matrix.json`
- artifact: `<local-user-path>/Documents/ai-judge-skill/reports/runs/client-8699a9696674/noise_audit.json`
