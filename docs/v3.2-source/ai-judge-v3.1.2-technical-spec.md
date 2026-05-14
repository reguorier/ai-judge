# AI Judge v3.1.2 天府Agent 技术迁移方案

> 定位：从天府Agent 借鉴逻辑模式 + 函数设计 + 可视化方法，嫁接到 AI Judge 现有架构上
> 前置条件：Texas Council 治理层 + Claim Ledger 推演账本 + Tauri 桌面端 + Harness 测试框架
> 目标：不重造法庭，只是在现有法庭上加「证据链 + 异议 + 置信度 + 可视化推理」

---

## 一、从天府Agent 借什么（精确清单）

天府Agent 有五样东西可以直接映射到 AI Judge，其余的不必借：

| 天府Agent | AI Judge 映射 | 借不借 | 理由 |
|-----------|-------------|--------|------|
| 思考-验证-反馈闭环 | Claim → Evidence → Verdict 三阶段 | **借** | 已有 Claim Ledger，只需补 Evidence + Verdict 阶段 |
| GPRO 节点级置信度 | ConfidenceEngine 按证据强度算置信度 | **借** | 正好解决「为什么打 7.2 分」的信任问题 |
| 知识溯源（每个结论标注古籍出处） | Evidence-source 绑定（每个判断标注规则/工具出处） | **借** | 比天府更强——用 harness Ground Truth 替代古籍 |
| 250+ 工具矩阵 | 插件化 BaseTool + 按风险路由调用 | **借** | 已有 analyzers 模块，只需标准化接口 |
| 可视化推理链 | 树状推理链 + 渐进式明示 UI | **借** | 桌面端 Tauri 渲染性能完全够 |
| 多 Agent 合议庭 | 已有 Texas Council | **不借** | 已实现，只需加入 Dissent Agent 角色 |
| 自研 Embedding 模型 | Sentence-BERT 本地嵌入 | **不借** | P2 远景，v3.1.2 不需要 |
| 长期记忆时间线锚定 | 反馈记忆系统 | **不借** | 已有本地例外库，反馈闭环够用 |
| 命理大模型 | n/a | **不借** | 领域不相关 |

---

## 二、技术方案总览

### 2.1 新增模块（v3.1.2）

```
ai-judge/
├── src/
│   ├── engine/
│   │   ├── evidence.rs        # 新增：证据对象标准化
│   │   ├── confidence.rs      # 新增：置信度引擎
│   │   ├── dissent.rs         # 新增：异议Agent
│   │   ├── risk_router.rs     # 新增：风险分级路由
│   │   ├── orchestrator.rs    # 改造：合议调度器（原 runner 升级）
│   │   └── tools/
│   │       ├── base_tool.rs   # 新增：插件化工具接口
│   │       ├── sast.rs        # 改造
│   │       ├── lint.rs        # 改造
│   │       └── test_runner.rs # 改造
│   │
│   ├── council/               # 已有：Texas Council
│   │   ├── claim_ledger.rs    # 改造：加 evidence 字段
│   │   └── council.rs         # 改造：加 DissentAgent 角色
│   │
│   └── ui/                    # Tauri 前端
│       ├── components/
│       │   ├── ReasoningTree.tsx    # 新增：树状推理链
│       │   ├── ConfidenceBadge.tsx  # 新增：置信度标识
│       │   ├── DissentPanel.tsx     # 新增：异议面板
│       │   └── EvidenceLink.tsx     # 新增：证据溯源链接
│       └── lib/
│           └── progressive.ts       # 新增：渐进式明示工具函数
```

### 2.2 数据流

```
PR/代码变更
    │
    ▼
┌─────────────────┐
│  RiskRouter      │  ← 新增：按风险分级决定审查深度
│  classify()      │
└────────┬────────┘
         │
    ┌────┴────┬─────────┐
    ▼         ▼         ▼
  critical  normal   trivial
  (全合议)  (标准)   (快判)
    │         │         │
    ▼         ▼         ▼
┌─────────────────┐
│  EvidenceCollector│  ← 新增：收集所有工具输出作为证据
│  collect()       │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
  工具证据   规则匹配
  (SAST/     (OWASP/
   Lint/      团队规范/
   Test)      行业标准)
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│  Claim Ledger    │  ← 已有：记录推演路径，新增 evidence 字段
│  record()        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DissentAgent    │  ← 新增：对 Claim 生成反方论点
│  challenge()     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ConfidenceEngine│  ← 新增：综合证据+规则+判例+异议计算置信度
│  calculate()     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  VerdictComposer │  ← 改造：生成带完整推理链的判决书
│  compose()       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ReasoningTree   │  ← 新增：前端树状可视化
│  render()        │
└─────────────────┘
```

---

## 三、核心函数实现

### 3.1 证据对象（Evidence Object）

借鉴天府Agent 的知识溯源——每个结论都必须标注依据来源。

```rust
// engine/evidence.rs

/// 证据类型：从天府的知识溯源映射过来
/// 天府用古籍出处，我们用工具/规则/测试结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EvidenceKind {
    /// 工具检测结果（对应天府的工具验证）
    ToolResult {
        tool_id: String,        // 如 "sast", "lint", "test_runner"
        finding_id: String,     // 工具输出的具体发现ID
        confidence: f64,        // 工具自身的置信度 (0.0-1.0)
        verifiable: bool,       // 可否被客观验证
    },
    /// 规则匹配（对应天府的古籍出处）
    RuleMatch {
        rule_id: String,        // 如 "owasp_a03_2021"
        source: String,         // 规则出处，如 "OWASP Top 10 A03:2021 §3.2.1"
        match_confidence: f64,  // 规则匹配的精确度
    },
    /// 测试结果（AI Judge 独有的 Ground Truth）
    HarnessResult {
        test_suite: String,     // 测试套件名称
        passed: bool,           // 通过/失败
        coverage_delta: f64,    // 覆盖率变化
    },
    /// 历史判例（对应天府的案例库）
    Precedent {
        case_id: String,        // 如 "PR#287"
        similarity: f64,        // 与当前案例的相似度
        outcome: String,        // 历史裁决结果
    },
}

/// 每个 Judgment 必须绑定至少一个 Evidence
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Evidence {
    pub kind: EvidenceKind,
    pub description: String,   // 人类可读的证据描述
    pub source_path: Option<String>,  // 可跳转的源文件路径
    pub source_line: Option<u32>,     // 源文件行号
}

/// 证据收集器：借鉴天府Agent 的「排盘计算Agent」
/// 在所有其他 Agent 运行前先收集客观事实
pub struct EvidenceCollector {
    tools: Vec<Box<dyn BaseTool>>,
}

impl EvidenceCollector {
    /// 核心函数：收集所有工具输出作为证据
    /// 对应天府Agent 的「事实认定」阶段
    pub fn collect(&self, task: &JudgeTask) -> Vec<Evidence> {
        let mut evidence_list = Vec::new();

        for tool in &self.tools {
            if let Ok(result) = tool.run(task) {
                match result {
                    ToolResult::Findings(findings) => {
                        for f in findings {
                            evidence_list.push(Evidence {
                                kind: EvidenceKind::ToolResult {
                                    tool_id: tool.name(),
                                    finding_id: f.id,
                                    confidence: tool.confidence(),
                                    verifiable: tool.is_verifiable(),
                                },
                                description: f.description,
                                source_path: Some(f.file_path.clone()),
                                source_line: Some(f.line),
                            });
                        }
                    }
                    ToolResult::Empty => continue,
                }
            }
        }

        evidence_list
    }
}
```

### 3.2 置信度引擎（Confidence Engine）

借鉴天府Agent 的 GPRO 算法——不是给一个绝对分数，而是输出置信度分布。

```rust
// engine/confidence.rs

/// 置信度组成：借鉴天府GPRO的节点级概率
/// 天府用古籍验证+用户反馈算概率，我们用工具证据+规则+判例+异议
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceScore {
    /// 综合置信度 0.0-1.0
    pub overall: f64,
    /// 四维分解（对应天府GPRO的推理节点概率）
    pub components: ConfidenceComponents,
    /// 置信度等级（用于UI展示）
    pub level: ConfidenceLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceComponents {
    /// 工具证据强度：有SAST/Lint/Test支撑则高
    pub tool_evidence_strength: f64,
    /// 规则匹配强度：规则是否明确、是否精确命中
    pub rule_match_strength: f64,
    /// 判例相似度：历史类似案例的支持程度
    pub precedent_similarity: f64,
    /// 异议未解决风险：反方论点未被驳倒的程度
    pub dissent_unresolved_risk: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ConfidenceLevel {
    High,      // >= 0.85 — 可阻断
    Medium,    // 0.60-0.84 — 需人工复核
    Low,       // < 0.60 — 仅建议
}

pub struct ConfidenceEngine;

impl ConfidenceEngine {
    /// 核心函数：计算置信度
    /// 对应天府Agent 的 GPRO 节点概率计算
    pub fn calculate(
        evidence: &[Evidence],
        rule_match: Option<&RuleMatch>,
        precedents: &[PrecedentCase],
        dissent: Option<&DissentResult>,
    ) -> ConfidenceScore {
        // 1. 工具证据强度：有可验证的工具结果为满分
        let tool_strength = Self::calc_tool_strength(evidence);

        // 2. 规则匹配强度：规则越精确越可信
        let rule_strength = rule_match
            .map(|r| r.match_confidence)
            .unwrap_or(0.0);

        // 3. 判例相似度：取最相似的3个判例加权平均
        let precedent_s = if precedents.is_empty() {
            0.5  // 无判例时为中性
        } else {
            precedents.iter()
                .take(3)
                .map(|p| p.similarity)
                .sum::<f64>() / precedents.len().min(3) as f64
        };

        // 4. 异议未解决风险：反方越强，扣分越多
        let dissent_risk = dissent
            .map(|d| d.strength)
            .unwrap_or(0.0);

        // 综合置信度 = 证据加权(0.4) + 规则加权(0.3) + 判例加权(0.2) - 异议惩罚(0.1)
        let overall = (tool_strength * 0.4 + rule_strength * 0.3 + precedent_s * 0.2)
            .min(1.0)
            - (dissent_risk * 0.1);

        let overall = overall.max(0.0).min(1.0);

        ConfidenceScore {
            overall,
            level: Self::classify_level(overall),
            components: ConfidenceComponents {
                tool_evidence_strength: tool_strength,
                rule_match_strength: rule_strength,
                precedent_similarity: precedent_s,
                dissent_unresolved_risk: dissent_risk,
            },
        }
    }

    fn calc_tool_strength(evidence: &[Evidence]) -> f64 {
        if evidence.is_empty() {
            return 0.0;
        }
        let verifiable_count = evidence.iter()
            .filter(|e| matches!(&e.kind, EvidenceKind::ToolResult { verifiable: true, .. }))
            .count();
        verifiable_count as f64 / evidence.len() as f64
    }

    fn classify_level(score: f64) -> ConfidenceLevel {
        if score >= 0.85 { ConfidenceLevel::High }
        else if score >= 0.60 { ConfidenceLevel::Medium }
        else { ConfidenceLevel::Low }
    }
}
```

### 3.3 异议Agent（Dissent Agent）

借鉴天府Agent 的多视角验证——但不是做完整合议庭，而是只做一个反方。

```rust
// engine/dissent.rs

/// 异议结果：反方Agent 对主判断的挑战
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DissentResult {
    /// 异议强度 0.0(无异议) - 1.0(完全否定)
    pub strength: f64,
    /// 反方论点列表
    pub counterarguments: Vec<String>,
    /// 需要补充验证的事项
    pub required_checks: Vec<String>,
    /// 是否建议降低主判断置信度
    pub should_reduce_confidence: bool,
}

pub struct DissentAgent {
    /// 借鉴Gemini的方案：非对称上下文
    /// 正方Agent看到的是：完整代码 + 测试通过信息
    /// 反方Agent看到的是：AST复杂度 + Lint报错 + 安全扫描结果
    /// 不给反方看原作者注释和业务上下文
    model: LocalModel,
    temperature: f32,  // 0.8 — 故意提高，鼓励发散思维
}

impl DissentAgent {
    /// 核心函数：对主判断发起挑战
    /// 对应天府Agent 的「验证阶段」——但用对抗而非验证
    pub fn challenge(
        &self,
        claim: &Claim,                // 主判断
        evidence: &[Evidence],        // 主判断依据的证据
        restricted_view: &RestrictedContext,  // 反方的受限视野
    ) -> DissentResult {
        // 构建反方专用 Prompt：故意不给完整上下文
        let prompt = self.build_adversarial_prompt(
            claim,
            restricted_view,  // 只看AST/Lint/SAST，不看注释和业务逻辑
        );

        let response = self.model.generate(&prompt, self.temperature);

        self.parse_dissent(response)
    }

    /// 借鉴Gemini的非对称上下文方案
    /// 反方Agent看不到：原作者注释、业务上下文、测试通过确认
    /// 反方Agent只能看：AST结构、Lint输出、SAST结果、复杂度指标
    fn build_adversarial_prompt(
        &self,
        claim: &Claim,
        ctx: &RestrictedContext,
    ) -> String {
        format!(
            r#"You are a Devil's Advocate in a code review jury.
Your job is to find the WEAKEST point in the following judgment.

## Main Verdict
{claim}

## What You Can See (Restricted View)
- AST complexity metrics: {ast_metrics}
- Lint violations: {lint_output}
- Security scan results: {sast_output}

## What You CANNOT See
- Original author comments
- Business logic context
- Test pass/fail results

## Instructions
1. Find the weakest link in the main verdict
2. Generate 1-3 specific counterarguments
3. Identify what additional evidence would resolve each doubt
4. Rate your dissent strength from 0.0 (completely agree) to 1.0 (verdict is likely wrong)

Do NOT fabricate problems. Only challenge based on what you can actually see."#,
            claim = claim.summary,
            ast_metrics = ctx.ast_metrics,
            lint_output = ctx.lint_output,
            sast_output = ctx.sast_output,
        )
    }

    fn parse_dissent(&self, response: String) -> DissentResult {
        // 解析模型输出为结构化 DissentResult
        // ...
        todo!()
    }
}

/// 反方Agent的受限视野
/// 对应Gemini的「Blindfolded Context」方案
pub struct RestrictedContext {
    pub ast_metrics: String,     // AST复杂度指标
    pub lint_output: String,     // Lint违规输出
    pub sast_output: String,     // 安全扫描结果
    // 故意不包含：注释、业务逻辑描述、测试结果
}
```

### 3.4 风险路由（Risk Router）

借鉴天府Agent 的分级调度——critical 走合议，trivial 走快判。

```rust
// engine/risk_router.rs

pub enum ReviewDepth {
    /// 全合议：事实认定 + 规则 + 异议 + 置信度
    FullJury,
    /// 标准：事实 + 规则 + 置信度
    Standard,
    /// 快速：只用工具结果
    FastCheck,
}

pub struct RiskRouter;

impl RiskRouter {
    /// 核心函数：按风险决定审查深度
    /// 对应天府Agent 的「分级调度」逻辑
    pub fn classify(task: &JudgeTask) -> ReviewDepth {
        // 安全/支付/隐私/认证 → 必须全合议
        if task.touches_any(&["payment", "auth", "privacy", "security", "data"]) {
            return ReviewDepth::FullJury;
        }

        // 合规/策略相关 → 标准 + 异议
        if task.contains_policy_or_compliance() {
            return ReviewDepth::Standard;  // 但会强制加 Dissent
        }

        // 变更很小 + 测试全过 → 快判
        if task.diff_size() < 20 && task.all_tests_pass() {
            return ReviewDepth::FastCheck;
        }

        // 默认标准
        ReviewDepth::Standard
    }

    /// 决定是否需要异议Agent
    pub fn needs_dissent(depth: &ReviewDepth, task: &JudgeTask) -> bool {
        match depth {
            ReviewDepth::FullJury => true,
            ReviewDepth::Standard => task.contains_policy_or_compliance(),
            ReviewDepth::FastCheck => false,
        }
    }
}
```

### 3.5 推理链构建器（Reasoning Tracer）

借鉴天府Agent 的可视化推理链——从输入到结论的每一步都可展开。

```rust
// engine/reasoning_tracer.rs

/// 推理节点：树状结构的一环
/// 对应天府Agent 的推理步骤可视化
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningNode {
    pub id: String,
    pub kind: NodeKind,
    pub label: String,         // UI 显示文字
    pub detail: String,        // 展开后的详细内容
    pub confidence: Option<f64>,
    pub source: Option<EvidenceSource>,
    pub children: Vec<ReasoningNode>,
    pub disputed: bool,        // 是否有异议
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NodeKind {
    Fact,         // 事实认定
    Evidence,     // 工具证据
    Rule,         // 规则匹配
    Dissent,      // 异议节点
    Conclusion,   // 最终结论
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceSource {
    pub file_path: String,     // 可跳转的文件路径
    pub line: Option<u32>,
    pub rule_id: Option<String>,
    pub tool_name: Option<String>,
}

pub struct ReasoningTracer;

impl ReasoningTracer {
    /// 核心函数：构建推理树
    /// 对应天府Agent 的推理链可视化数据结构
    pub fn build_tree(
        task: &JudgeTask,
        evidence: &[Evidence],
        rule_matches: &[RuleMatch],
        dissent: Option<&DissentResult>,
        verdict: &Verdict,
    ) -> ReasoningNode {
        // 根节点：结论
        let mut root = ReasoningNode {
            id: "root".into(),
            kind: NodeKind::Conclusion,
            label: verdict.summary.clone(),
            detail: verdict.detail.clone(),
            confidence: Some(verdict.confidence.overall),
            source: None,
            children: vec![],
            disputed: dissent.is_some(),
        };

        // 事实认定分支
        let facts = Self::build_fact_nodes(task);
        root.children.push(facts);

        // 证据分支
        for e in evidence {
            root.children.push(Self::build_evidence_node(e));
        }

        // 规则匹配分支
        for r in rule_matches {
            root.children.push(Self::build_rule_node(r));
        }

        // 异议分支（如有）
        if let Some(d) = dissent {
            root.children.push(Self::build_dissent_node(d));
        }

        root
    }

    fn build_fact_nodes(task: &JudgeTask) -> ReasoningNode {
        ReasoningNode {
            id: "facts".into(),
            kind: NodeKind::Fact,
            label: format!("变更{}个文件，+{}/-{}行", task.files_changed, task.lines_added, task.lines_deleted),
            detail: format!("涉及模块: {}", task.touched_modules.join(", ")),
            confidence: None,
            source: None,
            children: vec![],
            disputed: false,
        }
    }

    fn build_evidence_node(evidence: &Evidence) -> ReasoningNode {
        let source = EvidenceSource {
            file_path: evidence.source_path.clone().unwrap_or_default(),
            line: evidence.source_line,
            rule_id: None,
            tool_name: match &evidence.kind {
                EvidenceKind::ToolResult { tool_id, .. } => Some(tool_id.clone()),
                _ => None,
            },
        };

        ReasoningNode {
            id: format!("evidence_{}", uuid::Uuid::new_v4()),
            kind: NodeKind::Evidence,
            label: evidence.description.clone(),
            detail: format!("工具: {:?}", evidence.kind),
            confidence: match &evidence.kind {
                EvidenceKind::ToolResult { confidence, .. } => Some(*confidence),
                _ => None,
            },
            source: Some(source),
            children: vec![],
            disputed: false,
        }
    }

    fn build_rule_node(rule: &RuleMatch) -> ReasoningNode {
        ReasoningNode {
            id: format!("rule_{}", rule.rule_id),
            kind: NodeKind::Rule,
            label: format!("规则: {}", rule.source),
            detail: format!("适用范围: {} | 阻断级别: {:?}", rule.applies_to, rule.blocking_level),
            confidence: Some(rule.match_confidence),
            source: Some(EvidenceSource {
                file_path: String::new(),
                line: None,
                rule_id: Some(rule.rule_id.clone()),
                tool_name: None,
            }),
            children: vec![],
            disputed: false,
        }
    }

    fn build_dissent_node(dissent: &DissentResult) -> ReasoningNode {
        let args = dissent.counterarguments.join(" | ");
        ReasoningNode {
            id: "dissent".into(),
            kind: NodeKind::Dissent,
            label: format!("异议强度: {:.0}%", dissent.strength * 100.0),
            detail: format!("反方论点: {} | 需补验证: {}", args, dissent.required_checks.join(", ")),
            confidence: Some(1.0 - dissent.strength),
            source: None,
            children: vec![],
            disputed: true,
        }
    }
}
```

### 3.6 插件化工具接口

借鉴天府Agent 的 250+ 工具矩阵——统一接口、统一输出格式。

```rust
// engine/tools/base_tool.rs

/// 工具运行结果：借鉴天府Agent 的结构化工具输出
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ToolResult {
    Findings(Vec<Finding>),
    Empty,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub id: String,
    pub severity: Severity,
    pub file_path: String,
    pub line: u32,
    pub description: String,
    pub rule_ref: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Severity { Critical, High, Medium, Low, Info }

/// 工具接口 trait：借鉴天府Agent 的插件化设计
/// 所有分析器必须实现此接口
pub trait BaseTool: Send + Sync {
    /// 工具名称
    fn name(&self) -> String;

    /// 工具自身的置信度（如SAST的准确率）
    fn confidence(&self) -> f64;

    /// 是否可被客观验证
    fn is_verifiable(&self) -> bool;

    /// 运行工具，输入任务，输出结构化结果
    fn run(&self, task: &JudgeTask) -> Result<ToolResult, ToolError>;

    /// 工具适用的判断类型（用于自动路由）
    fn applicable_to(&self) -> Vec<TaskCategory>;
}
```

---

## 四、前端可视化方案

### 4.1 核心组件

借鉴天府Agent 的可视化推理链，但用桌面端 Tauri 的交互优势做超越：

```typescript
// ui/components/ReasoningTree.tsx

interface ReasoningNodeData {
  id: string;
  kind: 'fact' | 'evidence' | 'rule' | 'dissent' | 'conclusion';
  label: string;
  detail: string;
  confidence?: number;
  source?: EvidenceSource;
  children: ReasoningNodeData[];
  disputed: boolean;
}

interface EvidenceSource {
  filePath: string;
  line?: number;
  ruleId?: string;
  toolName?: string;
}

/**
 * 三级渐进式明示（Gemini 方案）
 *
 * Surface（第一级）：结论摘要 + 红/黄/绿状态
 *   ┌──────────────────────────────────┐
 *   │ 🟢 Pass: 12  🟡 Warn: 2  🔴 Block: 1  │
 *   │               ✦ 争议节点 ×2              │  ← 蓝紫闪烁光点
 *   └──────────────────────────────────┘
 *
 * Popover（第二级）：空格键触发，毛玻璃面板
 *   ┌──────────────────────────────────┐
 *   │ 🔴 Blocker: SQL注入风险            │
 *   │   ├─ 证据: SAST → OWASP A03       │
 *   │   ├─ 规则: SQL参数化强制           │
 *   │   ├─ 置信度: 95%                  │
 *   │   └─ 异议✦: 上游sanitizer未确认    │
 *   └──────────────────────────────────┘
 *
 * Full Panel（第三级）：双击，完整推理链 + Claim Ledger
 */
const ReasoningTree: React.FC<{ node: ReasoningNodeData }> = ({ node }) => {
  const [expanded, setExpanded] = useState(node.kind === 'conclusion');

  return (
    <div className="reasoning-node">
      {/* 节点头部 */}
      <div
        className="node-header"
        onClick={() => setExpanded(!expanded)}
      >
        {/* 置信度色标 */}
        {node.confidence !== undefined && (
          <ConfidenceBadge value={node.confidence} />
        )}

        {/* 争议闪烁点（借鉴天府Agent 的争议标注） */}
        {node.disputed && (
          <span className="dispute-sparkle">
            ✦
          </span>
        )}

        {/* 节点标签 */}
        <span className="node-label">{node.label}</span>

        {/* 证据溯源链接（借鉴天府的知识溯源） */}
        {node.source && (
          <EvidenceLink source={node.source} />
        )}
      </div>

      {/* 展开后的详细内容 + 子节点 */}
      {expanded && (
        <>
          <div className="node-detail">{node.detail}</div>
          <div className="node-children">
            {node.children.map(child => (
              <ReasoningTree key={child.id} node={child} />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

/**
 * 置信度标识：借鉴天府GPRO的概率可视化
 * 高置信 → 绿色实心
 * 中置信 → 黄色半满
 * 低置信 → 红色轮廓
 */
const ConfidenceBadge: React.FC<{ value: number }> = ({ value }) => {
  const color = value >= 0.85 ? 'green' : value >= 0.60 ? 'yellow' : 'red';
  return (
    <span
      className={`confidence-badge ${color}`}
      title={`置信度: ${(value * 100).toFixed(0)}%`}
    >
      {color === 'green' ? '●' : color === 'yellow' ? '◐' : '○'}
      {(value * 100).toFixed(0)}%
    </span>
  );
};

/**
 * 证据溯源链接：借鉴天府的知识溯源
 * 点击文件路径 → 调用 Tauri invoke → 打开本地 IDE 并定位到行
 */
const EvidenceLink: React.FC<{ source: EvidenceSource }> = ({ source }) => {
  const handleClick = async () => {
    // Tauri 调用本地IDE
    await invoke('open_in_editor', {
      filePath: source.filePath,
      line: source.line ?? 1,
    });
  };

  return (
    <button className="evidence-link" onClick={handleClick}>
      {source.filePath}
      {source.line && `:${source.line}`}
      {source.ruleId && ` ← ${source.ruleId}`}
      {source.toolName && ` [${source.toolName}]`}
    </button>
  );
};
```

### 4.2 颜色系统

借鉴天府Agent 的视觉表达，但做极简化（Gemini 的「内卷而外简」）：

| 场景 | 颜色 | 含义 |
|------|------|------|
| 高置信 + 阻断 | macOS 系统红 `#FF3B30` | 必须修复 |
| 高置信 + 警告 | macOS 系统橙 `#FF9500` | 强烈建议 |
| 中置信 | macOS 系统黄 `#FFCC00` | 需人工复核 |
| 低置信 | macOS 系统灰 `#8E8E93` | 仅作参考 |
| 争议节点 | 蓝紫渐变 `#5856D6 → #AF52DE` | 此节点存在对抗 |
| 证据链接 | macOS 系统蓝 `#007AFF` | 可点击跳转 |
| 默认文本 | macOS 标签灰 `#3C3C43` | 正文 |

原则：默认全盘黑白灰 + macOS 原生低饱和色。只有两个例外允许高饱和色：（1）极高置信度且极具破坏性的逻辑缺陷（系统红）；（2）Agent 间存在无法调和的冲突（蓝紫渐变越权警告）。

### 4.3 渐进式明示（Progressive Disclosure）

借鉴 Gemini 的方案，替代天府的「全部铺开」风格：

```
第一级：Surface（始终可见）
  → 只展示：Pass 12 / Warn 2 / Block 1 + 争议闪烁点
  → 设计：极简状态栏，类似 Xcode 的 Issue Navigator

第二级：Popover（空格键 / Force Touch）
  → 毛玻璃背景 + 树状推理链第二层展开
  → 设计：macOS Quick Look 风格，不阻塞主窗口

第三级：Full Panel（双击 / 回车）
  → 完整 Claim Ledger 推演账本 + 置信度拆解 + 判例对比
  → 设计：悬浮侧边面板，可拖动宽度
```

---

## 五、与现有架构的集成点

```
已有组件                    改动                       新增组件
─────────────────────────────────────────────────────────
Texas Council    → 加 DissentAgent 角色          ←  dissent.rs
Claim Ledger     → claim 结构加 evidence 字段     ←  evidence.rs
runner 模块      → 改造为 Orchestrator            ←  orchestrator.rs
analyzers 模块   → 标准化为 BaseTool trait        ←  base_tool.rs
collector 模块   → 保持，加 EvidenceCollector 调用 ←  evidence.rs
reporter 模块    → 输出改为 ReasoningNode 树       ←  reasoning_tracer.rs
Tauri UI         → 新增 ReasoningTree 组件         ←  ReasoningTree.tsx
Harness          → 测试结果注入 EvidenceKind       ←  (已有，改调用方式)
```

---

## 六、实现顺序（按周排）

**第 1 周：数据结构 + 引擎核心**

- [ ] `evidence.rs` — Evidence 结构体 + EvidenceCollector
- [ ] `confidence.rs` — ConfidenceScore + ConfidenceEngine
- [ ] `base_tool.rs` — BaseTool trait 定义
- [ ] 改造现有 SAST/Lint/Test 实现 BaseTool

**第 2 周：异议 + 推理链 + 前端初版**

- [ ] `dissent.rs` — DissentAgent
- [ ] `reasoning_tracer.rs` — ReasoningTracer
- [ ] `risk_router.rs` — RiskRouter
- [ ] `ReasoningTree.tsx` — 前端树状可视化（第一级 + 第二级）

**第 3 周：集成 + 联调 + 内部测试**

- [ ] Orchestrator 集成所有新模块
- [ ] Claim Ledger 加 evidence 字段
- [ ] Texas Council 加 DissentAgent
- [ ] 端到端测试：提交 PR → 收集证据 → 异议 → 置信度 → 可视化报告

---

> 技术方案基于：天府Agent 产品架构 + DestinyLinker/MingLi-Bench 工程风格 + AI Judge 团队三路反馈（豆包/Gemini/GPT）
> 本方案可直接作为 v3.1.2 的开发任务拆分输入
