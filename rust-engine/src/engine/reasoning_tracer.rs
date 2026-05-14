/// 推理链构建器 (Reasoning Tracer)
/// 借鉴天府Agent 的可视化推理链——从输入到结论的每一步都可展开
/// 输出 ReasoningNode 树，供前端 ReasoningTree 组件渲染

use serde::{Deserialize, Serialize};
use crate::{JudgeTask, RuleMatch};
use super::evidence::Evidence;
use super::dissent::DissentResult;

/// 推理节点——树状结构的一个节点
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningNode {
    pub id: String,
    pub kind: NodeKind,
    pub label: String,
    pub detail: String,
    pub confidence: Option<f64>,
    pub source: Option<EvidenceSource>,
    pub children: Vec<ReasoningNode>,
    pub disputed: bool,
    pub collapsed_by_default: bool,
}

/// 节点类型
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum NodeKind {
    /// 事实认定
    Fact,
    /// 工具证据
    Evidence,
    /// 规则匹配
    Rule,
    /// 异议节点
    Dissent,
    /// 最终结论
    Conclusion,
}

/// 证据溯源链接——点击可跳转 IDE
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceSource {
    pub file_path: String,
    pub line: Option<u32>,
    pub rule_id: Option<String>,
    pub tool_name: Option<String>,
}

/// 推理链构建器
pub struct ReasoningTracer;

impl ReasoningTracer {
    /// 核心函数: 构建推理树
    /// 对应天府Agent 的「可视化推理链」数据结构
    pub fn build_tree(
        &self,
        task: &JudgeTask,
        evidence: &[Evidence],
        rule_matches: &[RuleMatch],
        dissent: Option<&DissentResult>,
        verdict_summary: &str,
    ) -> ReasoningNode {
        // 根节点: 最终结论
        let mut root = ReasoningNode {
            id: "root".into(),
            kind: NodeKind::Conclusion,
            label: verdict_summary.to_string(),
            detail: self.build_verdict_detail(task, evidence.len(), rule_matches.len(), dissent),
            confidence: None, // 由外部 ConfidenceEngine 计算
            source: None,
            children: vec![],
            disputed: dissent.is_some(),
            collapsed_by_default: false,
        };

        // 1. 事实认定分支 (始终展示)
        root.children.push(self.build_fact_section(task));

        // 2. 证据分支
        if !evidence.is_empty() {
            let evidence_section = self.build_evidence_section(evidence);
            root.children.push(evidence_section);
        }

        // 3. 规则匹配分支
        if !rule_matches.is_empty() {
            let rule_section = self.build_rule_section(rule_matches);
            root.children.push(rule_section);
        }

        // 4. 异议分支 (如有)
        if let Some(d) = dissent {
            root.children.push(self.build_dissent_section(d));
        }

        root
    }

    /// 构建事实认定部分
    fn build_fact_section(&self, task: &JudgeTask) -> ReasoningNode {
        let modules = if task.touched_modules.is_empty() {
            "无".into()
        } else {
            task.touched_modules.join(", ")
        };

        let risk = if task.risk_surface.is_empty() {
            "无".into()
        } else {
            task.risk_surface.join(", ")
        };

        let test_status = match &task.test_results {
            Some(tr) if tr.all_passed => "全部通过".to_string(),
            Some(tr) => format!("{} 个失败", tr.failed_tests.len()),
            None => "无测试".to_string(),
        };

        ReasonNode {
            id: "facts".into(),
            kind: NodeKind::Fact,
            label: format!("变更 {} 个文件, +{}/-{} 行",
                task.files_changed, task.lines_added, task.lines_deleted),
            detail: format!(
                "涉及模块: {}\n风险领域: {}\n测试状态: {}\n",
                modules, risk, test_status
            ),
            confidence: None,
            source: None,
            children: task.diff.iter().map(|d| {
                ReasonNode {
                    id: format!("fact_file_{}", d.path.replace('/', "_")),
                    kind: NodeKind::Fact,
                    label: format!("{} (+{}/-{})", d.path, d.additions, d.deletions),
                    detail: format!("{} 个变更块", d.hunks.len()),
                    confidence: None,
                    source: Some(EvidenceSource {
                        file_path: d.path.clone(),
                        line: d.hunks.first().map(|h| h.start_line as u32),
                        rule_id: None,
                        tool_name: None,
                    }),
                    children: vec![],
                    disputed: false,
                    collapsed_by_default: true,
                }
            }).collect(),
            disputed: false,
            collapsed_by_default: false,
        }
    }

    /// 构建证据部分
    fn build_evidence_section(&self, evidence: &[Evidence]) -> ReasoningNode {
        ReasonNode {
            id: "evidence_section".into(),
            kind: NodeKind::Evidence,
            label: format!("证据 ({} 条)", evidence.len()),
            detail: format!(
                "可验证: {} 条 | 不可验证: {} 条",
                evidence.iter().filter(|e| e.is_verifiable()).count(),
                evidence.iter().filter(|e| !e.is_verifiable()).count(),
            ),
            confidence: None,
            source: None,
            children: evidence.iter().enumerate().map(|(i, e)| {
                let source = if e.source_path.is_some() || e.source_line.is_some() {
                    Some(EvidenceSource {
                        file_path: e.source_path.clone().unwrap_or_default(),
                        line: e.source_line,
                        rule_id: None,
                        tool_name: match &e.kind {
                            super::evidence::EvidenceKind::ToolResult { tool_id, .. } => Some(tool_id.clone()),
                            _ => None,
                        },
                    })
                } else {
                    None
                };

                ReasonNode {
                    id: format!("evidence_{}", i),
                    kind: NodeKind::Evidence,
                    label: e.description.clone(),
                    detail: format!(
                        "类型: {:?}\n置信度: {:.0}%\n可验证: {}",
                        std::mem::discriminant(&e.kind),
                        e.intrinsic_confidence() * 100.0,
                        e.is_verifiable(),
                    ),
                    confidence: Some(e.intrinsic_confidence()),
                    source,
                    children: vec![],
                    disputed: false,
                    collapsed_by_default: false,
                }
            }).collect(),
            disputed: false,
            collapsed_by_default: false,
        }
    }

    /// 构建规则匹配部分
    fn build_rule_section(&self, rule_matches: &[RuleMatch]) -> ReasoningNode {
        ReasonNode {
            id: "rule_section".into(),
            kind: NodeKind::Rule,
            label: format!("规则匹配 ({} 条)", rule_matches.len()),
            detail: "以下规则被触发:".into(),
            confidence: None,
            source: None,
            children: rule_matches.iter().map(|r| {
                ReasonNode {
                    id: format!("rule_{}", r.rule_id),
                    kind: NodeKind::Rule,
                    label: format!("{} — {:?}", r.source, r.blocking_level),
                    detail: format!(
                        "适用: {}\n匹配精度: {:.0}%\n规则ID: {}",
                        r.applies_to,
                        r.match_confidence * 100.0,
                        r.rule_id,
                    ),
                    confidence: Some(r.match_confidence),
                    source: Some(EvidenceSource {
                        file_path: String::new(),
                        line: None,
                        rule_id: Some(r.rule_id.clone()),
                        tool_name: None,
                    }),
                    children: vec![],
                    disputed: false,
                    collapsed_by_default: false,
                }
            }).collect(),
            disputed: false,
            collapsed_by_default: false,
        }
    }

    /// 构建异议部分
    fn build_dissent_section(&self, dissent: &DissentResult) -> ReasoningNode {
        let args = dissent.counterarguments.iter()
            .map(|a| format!("• {}: {}", a.claim, a.reasoning))
            .collect::<Vec<_>>()
            .join("\n");

        let checks = dissent.required_checks.iter()
            .map(|c| format!("• {}", c))
            .collect::<Vec<_>>()
            .join("\n");

        ReasonNode {
            id: "dissent".into(),
            kind: NodeKind::Dissent,
            label: format!("异议 ✦ (强度: {:.0}%)", dissent.strength * 100.0),
            detail: format!(
                "反方论点:\n{}\n\n需要补充验证:\n{}",
                args, checks,
            ),
            confidence: Some(1.0 - dissent.strength),
            source: None,
            children: dissent.counterarguments.iter().enumerate().map(|(i, a)| {
                ReasonNode {
                    id: format!("dissent_arg_{}", i),
                    kind: NodeKind::Dissent,
                    label: a.claim.clone(),
                    detail: a.reasoning.clone(),
                    confidence: None,
                    source: None,
                    children: vec![],
                    disputed: true,
                    collapsed_by_default: true,
                }
            }).collect(),
            disputed: true,
            collapsed_by_default: false,
        }
    }

    fn build_verdict_detail(
        &self,
        task: &JudgeTask,
        evidence_count: usize,
        rule_count: usize,
        dissent: Option<&DissentResult>,
    ) -> String {
        let mut detail = format!(
            "任务: {}\n证据: {} 条 | 规则: {} 条",
            task.task_id, evidence_count, rule_count,
        );
        if let Some(d) = dissent {
            detail.push_str(&format!(
                "\n异议: {} 条反方论点 | 强度: {:.0}%",
                d.counterarguments.len(),
                d.strength * 100.0,
            ));
        }
        detail
    }
}

// 重新导出为 ReasoningNode (简化命名)
pub use ReasoningNode as ReasonNode;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{TestResults, FileDiff, DiffHunk};

    #[test]
    fn test_build_basic_tree() {
        let tracer = ReasoningTracer;
        let task = JudgeTask {
            task_id: "test-1".into(),
            files_changed: 2,
            lines_added: 50,
            lines_deleted: 20,
            touched_modules: vec!["auth".into(), "payment".into()],
            risk_surface: vec!["security".into()],
            has_tests_changed: true,
            test_results: Some(TestResults {
                all_passed: true,
                failed_tests: vec![],
                coverage_delta: 0.05,
            }),
            diff: vec![
                FileDiff {
                    path: "src/auth.rs".into(),
                    additions: 30,
                    deletions: 10,
                    hunks: vec![DiffHunk { start_line: 10, end_line: 40, content: "fn login".into() }],
                },
            ],
        };

        let tree = tracer.build_tree(&task, &[], &[], None, "通过审查");
        assert_eq!(tree.kind, NodeKind::Conclusion);
        assert!(!tree.children.is_empty());
        assert_eq!(tree.children[0].kind, NodeKind::Fact);
    }

    #[test]
    fn test_build_tree_with_dissent() {
        let tracer = ReasoningTracer;
        let task = JudgeTask {
            task_id: "test-2".into(),
            files_changed: 1,
            lines_added: 10,
            lines_deleted: 0,
            touched_modules: vec!["ui".into()],
            risk_surface: vec![],
            has_tests_changed: false,
            test_results: None,
            diff: vec![],
        };

        let dissent = DissentResult {
            strength: 0.7,
            counterarguments: vec![],
            required_checks: vec!["验证SQL参数化".into()],
            should_reduce_confidence: true,
            generation_time_ms: 100,
        };

        let tree = tracer.build_tree(&task, &[], &[], Some(&dissent), "需人工复核");
        assert!(tree.disputed);
        assert!(tree.children.iter().any(|c| c.kind == NodeKind::Dissent));
    }
}
