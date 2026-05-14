/// 异议Agent (Devil's Advocate)
/// 借鉴天府Agent 的多视角验证——但只做一个反方，不做完整合议庭
/// 借鉴Gemini方案: 非对称上下文 + Temperature硬隔离 + 时间序列隔离

use serde::{Deserialize, Serialize};
use crate::JudgeTask;
use super::evidence::Evidence;

/// 异议结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DissentResult {
    /// 异议强度 0.0-1.0
    pub strength: f64,
    /// 反方论点
    pub counterarguments: Vec<CounterArgument>,
    /// 需要补充验证的事项
    pub required_checks: Vec<String>,
    /// 是否建议降低主判断置信度
    pub should_reduce_confidence: bool,
    /// 异议生成耗时 (ms)
    pub generation_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CounterArgument {
    pub claim: String,
    pub reasoning: String,
    pub severity: DissentSeverity,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DissentSeverity {
    /// 主判断可能完全错误
    Fatal,
    /// 主判断存在重大疑点
    Strong,
    /// 轻微异议
    Weak,
}

/// 异议Agent
pub struct DissentAgent {
    /// 模型温度: 高温度鼓励发散思维 (Gemini方案: 0.8)
    pub temperature: f32,
    /// 最大反方论点数量
    pub max_counterarguments: usize,
    /// 是否启用上下文隔离
    pub context_isolation: bool,
}

impl Default for DissentAgent {
    fn default() -> Self {
        Self {
            temperature: 0.8,
            max_counterarguments: 3,
            context_isolation: true,
        }
    }
}

impl DissentAgent {
    pub fn new(temperature: f32) -> Self {
        Self { temperature, ..Default::default() }
    }

    /// 核心函数: 对主判断发起挑战
    /// 对应天府Agent 的「验证阶段」——但通过对抗而非简单验证
    pub fn challenge(
        &self,
        claim: &str,
        evidence: &[Evidence],
        restricted_context: Option<&RestrictedContext>,
    ) -> DissentResult {
        let start = std::time::Instant::now();

        let mut counterarguments = Vec::new();

        // 1. 基于证据链的反驳——寻找证据中的薄弱环节
        counterarguments.extend(self.challenge_evidence_chain(evidence));

        // 2. 基于受限上下文的反驳——如果启用了非对称上下文(Gemini方案)
        if self.context_isolation {
            if let Some(ctx) = restricted_context {
                counterarguments.extend(self.challenge_from_restricted_view(ctx));
            }
        }

        // 3. 通用工程反驳——基于常见误判模式
        counterarguments.extend(self.challenge_common_patterns(claim));

        // 限制数量
        counterarguments.truncate(self.max_counterarguments);

        // 计算异议强度
        let strength = self.calculate_strength(&counterarguments);

        // 收集需要补充的验证
        let required_checks = self.collect_required_checks(&counterarguments);

        DissentResult {
            strength,
            counterarguments,
            required_checks,
            should_reduce_confidence: strength > 0.3,
            generation_time_ms: start.elapsed().as_millis() as u64,
        }
    }

    /// 挑战证据链的弱点
    fn challenge_evidence_chain(&self, evidence: &[Evidence]) -> Vec<CounterArgument> {
        let mut args = Vec::new();

        // 检查是否有不可验证的证据
        let unverifiable: Vec<_> = evidence.iter()
            .filter(|e| !e.is_verifiable())
            .collect();

        if !unverifiable.is_empty() {
            args.push(CounterArgument {
                claim: "部分证据不可客观验证".into(),
                reasoning: format!(
                    "{} 条证据依赖主观判断，无法通过工具或测试自动验证。建议补充可验证证据。",
                    unverifiable.len()
                ),
                severity: DissentSeverity::Strong,
            });
        }

        // 检查证据是否全部来自同一工具 (单点故障风险)
        let tools: std::collections::HashSet<String> = evidence.iter()
            .filter_map(|e| match &e.kind {
                super::evidence::EvidenceKind::ToolResult { tool_id, .. } => Some(tool_id.clone()),
                _ => None,
            })
            .collect();

        if tools.len() == 1 && !evidence.is_empty() {
            args.push(CounterArgument {
                claim: "证据来源单一".into(),
                reasoning: format!(
                    "所有工具证据仅来自 '{}'，建议引入更多独立工具交叉验证。",
                    tools.iter().next().unwrap()
                ),
                severity: DissentSeverity::Weak,
            });
        }

        args
    }

    /// 基于受限上下文的反驳 (Gemini非对称上下文方案)
    fn challenge_from_restricted_view(&self, ctx: &RestrictedContext) -> Vec<CounterArgument> {
        let mut args = Vec::new();

        // AST 复杂度异常
        if let Some(complexity) = ctx.ast_complexity {
            if complexity > 15 {
                args.push(CounterArgument {
                    claim: "高圈复杂度区域可能被遗漏".into(),
                    reasoning: format!(
                        "AST 分析显示圈复杂度达 {}，远超推荐阈值 10。\
                         该区域的代码变更可能引入了未被主判断覆盖的逻辑分支。",
                        complexity
                    ),
                    severity: DissentSeverity::Strong,
                });
            }
        }

        // Lint 违规数量异常
        if let Some(lint_count) = ctx.lint_violation_count {
            if lint_count > 5 {
                args.push(CounterArgument {
                    claim: "大量 Lint 违规可能掩盖更深层问题".into(),
                    reasoning: format!(
                        "存在 {} 条 Lint 违规。大量风格问题往往是\
                         匆忙提交的信号，可能伴随测试覆盖不足或逻辑错误。",
                        lint_count
                    ),
                    severity: DissentSeverity::Weak,
                });
            }
        }

        // SAST 命中高风险模式
        if let Some(ref sast_findings) = ctx.sast_high_severity_count {
            if *sast_findings > 0 {
                args.push(CounterArgument {
                    claim: "安全扫描发现高风险项".into(),
                    reasoning: format!(
                        "SAST 扫描发现 {} 个高风险项。即使主判断未归类为阻断，\
                         建议逐项人工确认。",
                        sast_findings
                    ),
                    severity: DissentSeverity::Fatal,
                });
            }
        }

        args
    }

    /// 基于常见误判模式的反驳
    fn challenge_common_patterns(&self, claim: &str) -> Vec<CounterArgument> {
        let mut args = Vec::new();

        let claim_lower = claim.to_lowercase();

        // 模式1: "always" / "never" 等绝对化断言的置信度天然较低
        if claim_lower.contains("always") || claim_lower.contains("never")
            || claim_lower.contains("must") || claim_lower.contains("必须")
            || claim_lower.contains("绝不")
        {
            args.push(CounterArgument {
                claim: "绝对化断言需要更强证据支撑".into(),
                reasoning: "判断使用了绝对化语言，但软件工程中很少有绝对的规则。\
                    建议检查是否存在合理的例外场景。".into(),
                severity: DissentSeverity::Weak,
            });
        }

        // 模式2: 可读性/可维护性等主观判断
        if claim_lower.contains("readability") || claim_lower.contains("可读")
            || claim_lower.contains("maintainability") || claim_lower.contains("可维护")
        {
            args.push(CounterArgument {
                claim: "主观维度判断存在合理分歧空间".into(),
                reasoning: "可读性和可维护性是主观维度，不同开发者可能有不同理解。\
                    建议标注为主观建议而非阻断性判断。".into(),
                severity: DissentSeverity::Strong,
            });
        }

        // 模式3: 没有引用测试结果的安全判断
        if (claim_lower.contains("security") || claim_lower.contains("安全")
            || claim_lower.contains("vulnerability") || claim_lower.contains("漏洞"))
            && !claim_lower.contains("test") && !claim_lower.contains("测试")
        {
            args.push(CounterArgument {
                claim: "安全判断未提及测试验证".into(),
                reasoning: "安全相关的判断应包含对应的测试用例或 PoC。\
                    建议补充攻击向量验证。".into(),
                severity: DissentSeverity::Strong,
            });
        }

        args
    }

    /// 计算异议综合强度
    fn calculate_strength(&self, args: &[CounterArgument]) -> f64 {
        if args.is_empty() {
            return 0.0;
        }

        // 每种严重度对应的权重
        let total: f64 = args.iter()
            .map(|a| match a.severity {
                DissentSeverity::Fatal => 1.0,
                DissentSeverity::Strong => 0.6,
                DissentSeverity::Weak => 0.3,
            })
            .sum();

        // 归一化到 0.0-1.0
        (total / args.len() as f64).min(1.0)
    }

    /// 收集需要补充的验证事项
    fn collect_required_checks(&self, args: &[CounterArgument]) -> Vec<String> {
        let mut checks = Vec::new();

        for arg in args {
            match arg.severity {
                DissentSeverity::Fatal => {
                    checks.push(format!("人工确认: {}", arg.claim));
                    checks.push("建议增加对应的自动化测试".into());
                }
                DissentSeverity::Strong => {
                    checks.push(format!("补充验证: {}", arg.claim));
                }
                DissentSeverity::Weak => {
                    checks.push(format!("可选验证: {}", arg.claim));
                }
            }
        }

        checks.dedup();
        checks
    }
}

/// 受限上下文——借鉴Gemini的非对称投喂方案
/// 反方Agent 故意看不到完整上下文，只能从代码指标中找问题
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RestrictedContext {
    /// AST 圈复杂度
    pub ast_complexity: Option<u32>,
    /// Lint 违规数量
    pub lint_violation_count: Option<u32>,
    /// SAST 高风险发现数
    pub sast_high_severity_count: Option<u32>,
    /// 变更行数 (不含注释)
    pub effective_lines_changed: Option<usize>,
    /// 文件类型分布
    pub file_types: Vec<String>,
    // 故意不包含: 原作者注释、业务逻辑描述、测试结果、完整代码
}

impl RestrictedContext {
    /// 从 JudgeTask 构建受限上下文
    /// 刻意过滤掉业务相关的信息
    pub fn from_task(task: &JudgeTask) -> Self {
        let file_types: Vec<String> = task.diff.iter()
            .filter_map(|d| d.path.split('.').last())
            .map(|s| s.to_string())
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();

        Self {
            ast_complexity: None, // 由外部 AST 分析器填充
            lint_violation_count: None,
            sast_high_severity_count: None,
            effective_lines_changed: Some(task.lines_added),
            file_types,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::super::evidence::EvidenceKind;

    #[test]
    fn test_dissent_on_unverifiable_evidence() {
        let agent = DissentAgent::default();
        let evidence = vec![Evidence {
            kind: EvidenceKind::RuleMatch {
                rule_id: "r1".into(),
                source: "主观判断".into(),
                match_confidence: 0.7,
            },
            description: "主观证据".into(),
            source_path: None,
            source_line: None,
        }];

        let result = agent.challenge("代码可读性差", &evidence, None);
        assert!(result.strength > 0.0);
        assert!(!result.counterarguments.is_empty());
    }

    #[test]
    fn test_dissent_on_absolute_claim() {
        let agent = DissentAgent::default();
        let result = agent.challenge("This must always be refactored", &[], None);
        assert!(result.strength > 0.0);
        assert!(result.counterarguments.iter()
            .any(|a| a.claim.contains("绝对化")));
    }

    #[test]
    fn test_no_dissent_on_well_evidenced_claim() {
        let agent = DissentAgent::default();
        let evidence = vec![Evidence {
            kind: EvidenceKind::ToolResult {
                tool_id: "sast".into(),
                finding_id: "f1".into(),
                confidence: 0.95,
                verifiable: true,
            },
            description: "SAST OWASP A03".into(),
            source_path: None,
            source_line: None,
        }];

        let result = agent.challenge("SQL注入风险", &evidence, None);
        // 对可验证的安全判断，异议应该较弱
        assert!(result.strength < 0.5);
    }
}
