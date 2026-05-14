/// 证据对象模块
/// 借鉴天府Agent 的知识溯源——每个结论都标注工具/规则/测试来源
/// AI Judge 独有优势: harness Ground Truth 替代天府的古籍验证

use serde::{Deserialize, Serialize};
use crate::JudgeTask;
use super::tools::base_tool::{BaseTool, ToolResult};

/// 证据类型枚举
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EvidenceKind {
    /// 工具检测结果（SAST/Lint/TestRunner 等）
    ToolResult {
        tool_id: String,
        finding_id: String,
        confidence: f64,
        verifiable: bool,
    },
    /// 规则匹配结果
    RuleMatch {
        rule_id: String,
        source: String,
        match_confidence: f64,
    },
    /// Harness 测试结果——AI Judge 独有的 Ground Truth
    HarnessResult {
        test_suite: String,
        passed: bool,
        coverage_delta: f64,
    },
    /// 历史判例
    Precedent {
        case_id: String,
        similarity: f64,
        outcome: String,
    },
}

/// 单个证据项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Evidence {
    pub kind: EvidenceKind,
    pub description: String,
    pub source_path: Option<String>,
    pub source_line: Option<u32>,
}

impl Evidence {
    /// 从天府的「知识溯源」映射过来: 每个判断必须有出处
    pub fn new(kind: EvidenceKind, description: impl Into<String>) -> Self {
        Self {
            kind,
            description: description.into(),
            source_path: None,
            source_line: None,
        }
    }

    pub fn with_location(mut self, path: impl Into<String>, line: u32) -> Self {
        self.source_path = Some(path.into());
        self.source_line = Some(line);
        self
    }

    /// 该证据是否可被客观验证（不可证伪的证据权重应降低）
    pub fn is_verifiable(&self) -> bool {
        matches!(&self.kind,
            EvidenceKind::ToolResult { verifiable: true, .. } |
            EvidenceKind::HarnessResult { .. }
        )
    }

    /// 该证据自身的置信度
    pub fn intrinsic_confidence(&self) -> f64 {
        match &self.kind {
            EvidenceKind::ToolResult { confidence, .. } => *confidence,
            EvidenceKind::RuleMatch { match_confidence, .. } => *match_confidence,
            EvidenceKind::HarnessResult { .. } => 1.0, // 客观测试结果是最高置信度
            EvidenceKind::Precedent { similarity, .. } => *similarity,
        }
    }
}

/// 证据收集器: 天府Agent 的「排盘计算Agent」映射
/// 在所有推理开始前，先收集所有工具和规则的客观输出
pub struct EvidenceCollector {
    tools: Vec<Box<dyn BaseTool>>,
}

impl EvidenceCollector {
    pub fn new(tools: Vec<Box<dyn BaseTool>>) -> Self {
        Self { tools }
    }

    /// 核心函数: 收集所有证据
    /// 对应天府Agent 的「事实认定」阶段
    pub fn collect(&self, task: &JudgeTask) -> Vec<Evidence> {
        let mut evidence_list = Vec::new();

        // 1. 收集所有工具输出
        for tool in &self.tools {
            match tool.run(task) {
                Ok(ToolResult::Findings(findings)) => {
                    for f in findings {
                        let evidence = Evidence {
                            kind: EvidenceKind::ToolResult {
                                tool_id: tool.name(),
                                finding_id: f.id,
                                confidence: tool.confidence(),
                                verifiable: tool.is_verifiable(),
                            },
                            description: format!("[{}] {}", tool.name(), f.description),
                            source_path: Some(f.file_path.clone()),
                            source_line: Some(f.line),
                        };
                        evidence_list.push(evidence);
                    }
                }
                Ok(ToolResult::Empty) => {}
                Err(e) => {
                    tracing::warn!("Tool {} failed: {:?}", tool.name(), e);
                }
            }
        }

        // 2. 收集 Harness 测试结果——AI Judge 独有的 Ground Truth
        if let Some(test_results) = &task.test_results {
            evidence_list.push(Evidence {
                kind: EvidenceKind::HarnessResult {
                    test_suite: "default".into(),
                    passed: test_results.all_passed,
                    coverage_delta: test_results.coverage_delta,
                },
                description: if test_results.all_passed {
                    "所有测试通过".into()
                } else {
                    format!("{} 个测试失败: {}",
                        test_results.failed_tests.len(),
                        test_results.failed_tests.join(", "))
                },
                source_path: None,
                source_line: None,
            });
        }

        evidence_list
    }

    /// 过滤出可验证的证据
    pub fn verifiable<'a>(&self, evidence: &'a [Evidence]) -> Vec<&'a Evidence> {
        evidence.iter().filter(|e| e.is_verifiable()).collect()
    }

    /// 检查是否存在与给定结论冲突的证据
    pub fn find_conflicts<'a>(&self, evidence: &'a [Evidence], _claim: &str) -> Vec<&'a Evidence> {
        // 简化实现: 检查是否有 HarnessResult 显示测试失败
        evidence.iter()
            .filter(|e| matches!(&e.kind, EvidenceKind::HarnessResult { passed: false, .. }))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::super::tools::base_tool::{Finding, Severity, ToolError};
    use crate::TaskCategory;

    struct MockLintTool;
    impl BaseTool for MockLintTool {
        fn name(&self) -> String { "lint".into() }
        fn confidence(&self) -> f64 { 0.95 }
        fn is_verifiable(&self) -> bool { true }
        fn applicable_to(&self) -> Vec<TaskCategory> { vec![TaskCategory::Style] }
        fn run(&self, _task: &JudgeTask) -> Result<ToolResult, ToolError> {
            Ok(ToolResult::Findings(vec![
                Finding {
                    id: "lint_001".into(),
                    severity: Severity::Medium,
                    file_path: "src/main.rs".into(),
                    line: 42,
                    description: "变量命名不符合规范".into(),
                    rule_ref: Some("naming-convention".into()),
                    suggestion: None,
                }
            ]))
        }
    }

    #[test]
    fn test_evidence_collection() {
        let collector = EvidenceCollector::new(vec![Box::new(MockLintTool)]);
        let task = JudgeTask {
            task_id: "test-1".into(),
            files_changed: 1,
            lines_added: 10,
            lines_deleted: 5,
            touched_modules: vec!["main".into()],
            risk_surface: vec![],
            has_tests_changed: false,
            test_results: None,
            diff: vec![],
        };

        let evidence = collector.collect(&task);
        assert_eq!(evidence.len(), 1);
        assert_eq!(evidence[0].source_path.as_deref(), Some("src/main.rs"));
        assert!(evidence[0].is_verifiable());
    }
}
