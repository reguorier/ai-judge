# AI Judge v3.1.0 → 可审计合议架构：最终裁决

> 基于天府Agent 架构分析 + 三路 AI 模型反馈（豆包 / Gemini / GPT）的交叉裁决
> 产出时间：2026-05-13
> 定位：一份可以直接拍在工程桌上的最终路线图

---

## 裁决书摘要

经过对天府Agent 架构的深入分析、向 AI Judge 团队提交七方向议题、并收回三路独立 AI 模型的反馈后，我的裁决如下：

**AI Judge 不需要做「多 Agent 议会」——那是对天府Agent 的肤浅模仿。AI Judge 的正确方向是成为「可审计判决引擎」：用 harness 的客观 Ground Truth 作为事实基础，用异议Agent 作为对抗验证，用置信度引擎诚实表达不确定性，用可视化推理链让每个判断可追溯。**

三路反馈中有一致性极高的信号：
- 豆包明确指出：当前架构是「规则引擎 70% + 模型 30%」，已有 Texas Council 和 Claim Ledger 骨架
- Gemini 指出：真正的痛点不是缺多 Agent，而是缺「合议调度器」和「异议/反方」
- GPT 指出：MVP 不应做完整合议庭，应先做「Evidence Object + Confidence Engine + Dissent Agent + Reasoning Trace」

三方共识收敛在一个结论上：**先做反方、先做证据、先做置信度、先做可视化。Agent 合议是 P2 远景项。**

---

## 一、三个模型的核心发现与交叉验证

### 1.1 架构假设修正——三个模型一致指出我之前的推测有误

| 我的假设 | 实际情况（三方确认） |
|---------|-------------------|
| 单一模型一次性输出 | 已是「规则引擎 70% + 模型推理 30%」的混合架构 |
| 缺乏异议机制 | 已有「例外场景库」——命中例外自动降级 |
| 无反馈回路 | 用户驳回会记录到本地例外库，自动触发降级 |
| UI 是 Electron | 实际是 Tauri，内存占用仅为 Electron 的 1/3 |
| 无多 Agent 框架 | 已有 Texas Council 治理逻辑 + Claim Ledger 推演账本 |

### 1.2 三个模型各自击中了一个要害

**豆包** 击中要害：「本地资源约束下，Agent 数量-推理速度-判断准确性的最优平衡点如何量化」。这是一个工程量化问题，不是玄学。豆包的答案是：critical 任务走三重验证合议，trivial 任务保留单模型快判。我完全同意。

**Gemini** 击中要害：「同构底层模型容易产生认知趋同和互相包庇」。这比「要不要做多 Agent」更底层——如果你做了多 Agent 但四个 Agent 是同一个模型套不同 prompt，它们会合谋而非对抗。Gemini 的解法（上下文非对称投喂 + Temperature/Top-P 硬隔离 + CodexPool 时间序列隔离）是三个模型中最具工程深度的。

**GPT** 击中要害：「不要先做完整合议庭。先做 Evidence Object + Confidence Engine + Dissent Agent + Reasoning Trace Report」。这是最务实的 MVP 定义。GPT 的 7 层架构（Fact Collector → Tool Evidence → Rule Matcher → Dissent Agent → Confidence Engine → Verdict Composer → Reasoning Trace UI）是最清晰的可落地架构。

### 1.3 三方争议点

| 争议 | 豆包 | Gemini | GPT | 我的裁决 |
|------|------|--------|-----|---------|
| 异议Agent 优先级 | P1（中期 v3.2） | 隐含 P0（放在核心方案中） | P0（「最值得先做的 Agent」） | **P0**。GPT 的判断更准：一个反方 Agent 成本低、收益极大 |
| 置信度实现时机 | 短期 v3.1.x（二元置信度） | 未单独讨论 | P0（Confidence Engine 在 MVP 中） | **P0**。置信度是「可审计」的前提 |
| 本地 LoRA 微调 | 长期 v3.3+ | 中期（深夜自动炼丹） | 未明确 | **P2**。先做规则优化和 Prompt 微调，LoRA 是锦上添花 |
| Agent 合议庭 | P1（中期） | P1/P2（已有骨架需激活） | P2（远景） | **P2**。GPT 的判断更克制：先把基础打牢再上合议 |

---

## 二、最终裁决：三层四级优先级路线图

### 架构收敛方向

三路反馈 + 天府Agent 分析收敛到一个统一认知：**AI Judge 的核心竞争力不是「模型强」，而是「本地可审计」**。所有升级必须围绕这个展开。

```
┌──────────────────────────────────────────────────┐
│                  UI 层：推理链可视化                │
│          树状证据链 / 置信度色标 / 一键反馈          │
├──────────────────────────────────────────────────┤
│              编排层：合议调度器 (Judge Orchestrator)  │
│    风险分级路由 / 工具调用 / 冲突仲裁 / 异议调度      │
├──────────────────┬───────────────────────────────┤
│  推理层-客观       │  推理层-主观                    │
│  规则引擎 + 工具    │  本地模型推理                   │
│  (70%)            │  (30%)                        │
│  规则匹配 / 硬验证  │  解读 / 生成 / 偏好适配          │
├──────────────────┴───────────────────────────────┤
│              数据层：本地知识库                      │
│   规则库 / 判例库(SQLite+vss) / 反馈库 / Ground Truth │
└──────────────────────────────────────────────────┘
```

### P0 — v3.1.2 MVP（2周）：信任基础设施

这四项是「不做的后果是用户持续不信任」的底线项。

**P0-1：证据对象标准化（Evidence Object Schema）**

> 豆包：「每个判断必须绑定至少一个工具输出或规则依据，没有依据的判断自动删除」
> GPT：「没有证据的 judgment 只能标为 Suggestion，不能标为 blocker」

```
{
  "judgment_id": "j_001",
  "claim": "SQL注入风险",
  "severity": "blocker",
  "confidence": 0.95,
  "evidence": [
    {"type": "tool_result", "tool": "sast", "rule": "OWASP A03:2021"}
  ],
  "dissent": {
    "strength": "low",
    "counterarguments": ["可能存在上游 sanitizer"]
  },
  "recommended_action": ["参数化查询", "添加恶意输入测试"]
}
```

验收标准：每个 judgment 必须有 claim + evidence + source + confidence + dissent + recommended_action。缺证据的自动降级。

**P0-2：置信度引擎 v0（二元置信度）**

> Gemini：「承认不确定性比盲目自信更专业」
> GPT：「高置信 + 高风险 = block；中置信 + 高风险 = human review；低置信 = suggestion」

- 客观维度（测试/SAST/Lint）：置信度 = 100%
- 主观维度（可读性/可维护性）：置信度 = 规则匹配度 × 判例相似度
- 置信度 < 70%：自动折叠，标注「需人工复核」
- 验证冲突时：置信度自动降至 30% 并标注「与测试结果不符」

**P0-3：异议Agent v0（Devil's Advocate）**

> GPT：「不要一开始搞多 Agent 合议。先做一个反方」
> Gemini：「通过上下文非对称投喂 + Temperature 硬隔离来防止合谋」

- 输入：主判断 + 证据 + 规则
- 输出：异议强度 + 反方论点 + 需要补的证据
- 配置：温度 0.8（与事实认定Agent 的 0.0 形成硬隔离）
- 验收标准：能生成不无意义、有工程价值的反方论点

**P0-4：三级推理链报告（树状可视化）**

> 豆包：「重构报告结构为三级推理链，每个节点支持展开/折叠」
> GPT：「桌面端最大优势是本地交互——点击文件路径直接打开 IDE」

```
结论：阻断合并（1个阻断问题）
├─ 🔴 SQL注入风险 (payment/checkout.ts:89)
│   ├─ 工具: SAST → OWASP A03:2021
│   ├─ 规则: SQL输入必须参数化
│   ├─ 置信度: 95%
│   └─ 异议: 可能存在上游sanitizer → 需验证
├─ 🟡 圈复杂度超标 (auth/login.ts:45-78)
│   ├─ 工具: AST → 复杂度18 (阈值10)
│   ├─ 置信度: 62%
│   └─ 异议: 业务分支多，拆分可能降低可读性
└─ 🟢 通过项: 12个
```

### P1 — v3.2（2个月）：核心竞争力

**P1-1：判例检索引擎（Precedent Retriever）**

> GPT：「如果 AI Judge 能说『这个问题和 PR#287 类似，当时被确认为真实漏洞』，可信度会大幅提升」

- 基于 SQLite + sqlite-vss 扩展实现轻量向量存储
- 本地 Sentence-BERT 生成 Embedding
- 最多存储 1000 条判例，超出后 FIFO 淘汰
- 与 Git 历史联动，关联 PR/Commit 上下文

**P1-2：反馈记忆系统（Feedback Memory）**

> Gemini：「用户的每一次 IDE 交互和 Git 操作，就是最强烈的 Ground Truth」
> 豆包：「监控 git commit --no-verify → 明确的拒绝信号」

- 隐式反馈收集：git commit --no-verify（否定信号）/ 用户修改代码后重跑测试（肯定信号）
- 显式反馈：「一键反馈」按钮——用户只需选择「规则错误 / 工具错误 / 模型误读」
- 反馈分级存储：用户偏好 / 项目局部规则 / 系统真实误判，三者分开

**P1-3：风险分级路由（Risk-based Routing）**

```
def choose_judging_route(task):
    if task.risk_surface in ["payment", "auth", "privacy", "security"]:
        return "full_jury"          # 三重验证
    if task.diff_size < 20 and task.tests_pass:
        return "fast_judge"         # 单模型快判
    if task.contains_policy_or_compliance:
        return "jury_with_dissent"  # 主判断 + 异议
    return "standard_judge"         # 规则 + 工具
```

**P1-4：插件化工具接口（BaseTool）**

> 豆包：「工具接口抽象需兼顾灵活性和易用性；参考 MingLi-Bench 的工具接口设计」

```python
class BaseTool:
    def run(self, input: ToolInput) -> ToolResult:
        """统一输入输出规范"""
        pass
```

补充空白工具：依赖风险检测、性能基准、幻觉检测。

### P2 — v3.3+（远景）：护城河加深

- P2-1：Agent 合议庭（多角色分工——P0-P1 的基础打牢后方可引入）
- P2-2：本地 LoRA 微调（Gemini 的「深夜炼丹」方案——检测到 macOS 待机 + 电源连接时自动微调）
- P2-3：推理链图谱 UI（Gemini 的「渐进式明示」——空格键 Quick Look 展开争议节点）
- P2-4：AI Judge 专属 Benchmark（参考 MingLi-Bench，用历史 Ground Truth 构建评测集）

---

## 三、对七个共振问题的裁决

以下是三路 AI 模型回抛给我的核心问题，我的逐一裁决：

### 问题 1（豆包 & GPT）：AI Judge 到底要成为什么？

**我的裁决：先做「判断质量防火墙」。**

代码审查助手和 Agent 议会系统都是手段，不是目的。核心目的是一句话：**「任何代码合入主干前，AI Judge 给出一个可审计的质量判断——哪些是确定的，哪些是存疑的，依据是什么。」** 防火墙隐喻比「助手」更有力量——助手是可选的，防火墙是必须通过的。

### 问题 2（GPT）：最想解决的是误判还是不可解释？

**我的裁决：不可解释优先，但用 Ground Truth 解决误判。**

两者不矛盾。推理链可视化解决「不知道为什么这么判」，harness 客观验证解决「判错了」。短期（v3.1.2）：可视化优先（因为这是 P0-4，改 UI 成本可控）。中期（v3.2）：Ground Truth 校准解决误判（因为需要数据积累）。长期：两者耦合——低置信度 + 无证据 + 用户驳回 → 自动触发规则校准。

### 问题 3（GPT & 豆包）：是否接受「低置信度不阻断」？

**我的裁决：强制接受。这是产品原则，不是技术选择。**

```
高置信 + 高风险 → block（阻断合并）
中置信 + 高风险 → human review（需人工复核）
低置信 + 任意   → suggestion（建议，不阻断）
无证据          → 不能标为 blocker（强制规则）
```

这条规则必须写进产品宪章。违反此规则会导致用户信任崩塌——一次武断的误阻断，会抵消一百次正确的判断。

### 问题 4（Gemini）：如何防止同构模型 Agent 的认知合谋？

**我的裁决：Gemini 的方案全盘采纳，并补充一点。**

Gemini 的三板斧（上下文非对称投喂 + Temperature/Top-P 硬隔离 + CodexPool 时间序列隔离）是正确的工程方向。我补充一点：**异议Agent 不应与主判断 Agent 用同一个模型实例**。即使本地只有一个 8B 模型，也要用不同的量化级别或不同的 prompt template 加载两个实例，确保它们在内存中不会共享 KV cache。

### 问题 5（Gemini）：隐式反馈如何转化为高质量微调信号？

**我的裁决：不用 LoRA，先用 Prompt Memory。**

Gemini 的「git commit --no-verify → 否定信号 → DPO 偏好对」思路是对的，但 LoRA 微调太重了。v3.1.x 阶段不应该碰模型权重。替代方案：

1. 将用户操作（驳回 / 修改代码 / --no-verify）记录为结构化反馈事件
2. 每次推理时，从反馈库中检索相似历史场景，作为 few-shot 反例注入 Prompt
3. 周期性地用反馈数据生成「规则权重调整建议」（人工审核后生效）
4. LoRA 微调留到 v3.3+，在积累足够多的反馈数据后作为可选功能

### 问题 6（Gemini）：如何在信息密度爆炸时保持极简 UI？

**我的裁决：三级渐进式明示。**

Gemini 的「内卷而外简」是正确哲学。具体方案：

- **第一级（Surface）**：只有结论摘要 + 红/黄/绿状态标记 + 蓝紫争议闪烁点
- **第二级（空格键 Quick Look）**：弹出毛玻璃面板，展示树状推理链，不展示 Agent 对话
- **第三级（双击深入）**：展示 Claim Ledger 推演账本、置信度拆解、判例对比

颜色克制：默认黑白灰 + macOS 低饱和蓝。只有极高置信度 + 极高破坏性的判断才用高饱和蓝紫越权警告。

### 问题 7（GPT）：判例库要不要设为护城河？

**我的裁决：必须是。这是任何云端竞品无法复制的壁垒。**

GitHub Copilot Code Review 没有本地 harness。CodeRabbit 没有用户的私有测试数据。**只有 AI Judge 拥有用户私有仓库的完整 Git 历史、测试结果、Lint 记录和人工判定。** 这些数据构建的判例向量库，是任何 SaaS 竞品永远无法触及的护城河。v3.2 必须把判例检索作为核心能力交付。

---

## 四、最终路线图（一张表）

| 版本 | 时间 | 核心交付 | 验收标准 |
|------|------|---------|---------|
| **v3.1.2 MVP** | 2周 | P0-1 Evidence Schema + P0-2 Confidence v0 + P0-3 Dissent Agent + P0-4 Tree Report | 每个判断有证据/置信度/异议/溯源；缺证据不阻断 |
| **v3.1.3** | 1个月 | 反馈日志 + 一键反馈 + 资源监控 + 推理缓存 | 用户驳回率可追踪；内存占用可控 |
| **v3.2** | 2个月 | P1-1 判例检索 + P1-2 反馈记忆 + P1-3 风险路由 + P1-4 工具接口 | 判例召回准确率 >70%；工具可插拔 |
| **v3.2.x** | 3个月 | 规则自动优化 + Prompt 微调 + IDE 深度联动 | 规则准确率自动校准；点击推理链节点直达 IDE |
| **v3.3+** | 6个月+ | Agent 合议庭 + LoRA 微调 + 推理链图谱 UI + Benchmark | 多 Agent 合议完成；本地越用越准 |

---

## 五、一句话裁决

**不要建法庭，先造天平。** 天府的启示不是「多 Agent 很酷」，而是「让用户看到判断的依据，比判断本身更重要」。AI Judge 的护城河不是模型多强、Agent 多少，而是它拥有所有云端竞品永远拿不到的东西——用户本地的测试数据、Git 历史和私有规则。把这三样东西变成证据、变成判例、变成校准信号，就是 AI Judge 不可复制的竞争力。

---

> 本裁决基于：天府Agent 公开产品架构分析 + DestinyLinker/MingLi-Bench 开源代码参考 + AI Judge 团队三路 AI 模型（豆包/Gemini/GPT）全量反馈
> 裁决人：Cowork session — Claude agent
> 下一动作：等待你对本裁决的确认 / 反驳 / 补充，然后进入 v3.1.2 MVP 的详细技术方案设计
