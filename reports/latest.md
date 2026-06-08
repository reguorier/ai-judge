# AI Judge 最终报告

Run ID: `both-002`
模式: 深度裁决

## 1. 核心结论
## 核心结论

非本村村民之间的宅基地房屋买卖合同**无效**。

## 丁的权利救济

丁可向甲主张：
1. **不当得利返还**（《民法典》第985条）：甲无法律根据取得拆迁补偿利益
2. **合同无效后财产返还**（《民法典》第157条）

## 案由、被告、诉讼请求

| 项目 | 内容 |
|------|------|
| 案由 | 确认合同无效纠纷 + 不当得利纠纷 |
| 被告 | 甲 |
| 第三人 | 拆迁方（征收主体）|
| 诉讼请求1 | 确认1989-2009年系列转售行为无效 |
| 诉讼请求2 | 确认补偿款中房屋价值部分归丁所有 |
| 诉讼请求3 | 判令甲

## 2. 适用边界
本报告基于多源分析生成，用于把议题分析、席位观点、证据强度和风险压缩为可审计结论；不替代人工最终判断。

## 3. 已验证事实
- run_id 已生成：both-002（来源：summary.json）
- 本次模式为 深度裁决。（来源：summary.json）
- 分析来源：search_agent（来源：source_pack）

## 4. 推断与判断
- 报告围绕用户议题「案例：甲乙丙丁都不是本村村民。1989年，甲与乙在农村宅基地合作开发共建房屋，甲作为宅基地登记的权利人。1993年，乙将」展开分析。（强度：medium）（来源：source_pack）

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
整体强度：medium

- 实质性分析来源：search_agent（强度：medium）
- 席位有效性：3/5（强度：medium）

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

## 10. 审计附件
- 生成时间：2026-06-08T05:01:28+00:00
- 有效席位：3
- 失败席位：0
- artifact: `/Users/audimacmini/Documents/ai-judge-skill/reports/runs/both-002/final_report.md`
- artifact: `/Users/audimacmini/Documents/ai-judge-skill/reports/runs/both-002/final_report.html`
- artifact: `/Users/audimacmini/Documents/ai-judge-skill/reports/runs/both-002/summary.json`
- artifact: `/Users/audimacmini/Documents/ai-judge-skill/reports/runs/both-002/evidence_packet.json`
- artifact: `/Users/audimacmini/Documents/ai-judge-skill/reports/runs/both-002/seat_matrix.json`
