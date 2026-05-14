/// 合议调度器 (Orchestrator)
/// 从原有 runner 模块改造而来
/// 借鉴天府Agent 的多 Agent 编排逻辑——按风险分级调度、处理冲突、生成最终判决

use crate::{
    JudgeTask, Verdict, Judgment, MergeStatus, BlockingLevel,
    RuleMatch, PrecedentCase,
};
use super::{
    evidence::{EvidenceCollector, Evidence},
    confidence::{ConfidenceEngine, ConfidenceScore, ConfidenceLevel},
    dissent::{DissentAgent, DissentResult, RestrictedContext},
    risk_router::{RiskRouter, ReviewDepth},
    reasoning_tracer::ReasoningTracer,
};

/// 编排结果
pub struct OrchestrationResult {
    pub verdict: Verdict,
    pub metrics: OrchestrationMetrics,
}

/// 编排性能指标
#[derive(Debug, Clone)]
pub struct OrchestrationMetrics {
    pub depth: ReviewDepth,
    pub evidence_count: usize,
    pub dissent_generated: bool,
    pub total_time_ms: u64,
    pub memory_used_mb: f64,
}

/// 合议调度器
pub struct Orchestrator {
    evidence_collector: EvidenceCollector,
    confidence_engine: ConfidenceEngine,
    dissent_agent: DissentAgent,
    risk_router: RiskRouter,
    reasoning_tracer: ReasoningTracer,
}

impl Orchestrator {
    pub fn new(
        evidence_collector: EvidenceCollector,
        confidence_engine: ConfidenceEngine,
        dissent_agent: DissentAgent,
        risk_router: RiskRouter,
    ) -> Self {
        Self {
            evidence_collector,
            confidence_engine,
            dissent_agent,
            risk_router,
            reasoning_tracer: ReasoningTracer,
        }
    }

    /// 核心函数: 编排整个评判流程
    /// 对应天府Agent 的 Think-Verify-Feedback 三阶段
    pub async fn orchestrate(
        &self,
        task: &JudgeTask,
        rule_matches: &[RuleMatch],
        precedents: &[PrecedentCase],
    ) -> OrchestrationResult {
        let start = std::time::Instant::now();

        // === 阶段 0: 风险分级 (天府的分级调度) ===
        let depth = self.risk_router.classify(task);
        let needs_dissent = self.risk_router.needs_dissent(&depth, task);

        tracing::info!(
            "Orchestrating task {} with depth {:?}, dissent={}",
            task.task_id, depth, needs_dissent
        );

        // === 阶段 1: Think — 收集证据 (天府的「事实认定」) ===
        let evidence = self.evidence_collector.collect(task);
        tracing::info!("Collected {} evidence items", evidence.len());

        // === 阶段 2: Think — 生成初步判断 ===
        let mut judgments = self.generate_initial_judgments(
            task, &evidence, rule_matches, &depth,
        );

        // === 阶段 3: Verify — 异议挑战 (天府的「验证」) ===
        let dissent_results: Vec<Option<DissentResult>> = if needs_dissent {
            let restricted = RestrictedContext::from_task(task);
            judgments.iter()
                .map(|j| {
                    let result = self.dissent_agent.challenge(
                        &j.claim,
                        &j.evidence,
                        Some(&restricted),
                    );
                    tracing::info!(
                        "Dissent for judgment {}: strength={:.2}",
                        j.id, result.strength
                    );
                    Some(result)
                })
                .collect()
        } else {
            vec![None; judgments.len()]
        };

        // === 阶段 4: Verify — 置信度计算 (天府的 GPRO 概率) ===
        for (i, judgment) in judgments.iter_mut().enumerate() {
            let confidence = self.confidence_engine.calculate(
                &judgment.evidence,
                judgment.rule_match.as_ref(),
                precedents,
                dissent_results[i].as_ref(),
            );

            // Harness Ground Truth 校准
            let harness_conflict = self.check_harness_conflict(&judgment.evidence, task);
            let calibrated = self.confidence_engine.calibrate_with_ground_truth(
                &confidence, harness_conflict,
            );
            judgment.confidence = calibrated;
            judgment.dissent = dissent_results[i].clone();
        }

        // === 阶段 5: 合成最终判决 ===
        let verdict = self.compose_verdict(task, &judgments, &evidence, rule_matches, &dissent_results, &depth);

        let total_time = start.elapsed().as_millis() as u64;

        OrchestrationResult {
            verdict,
            metrics: OrchestrationMetrics {
                depth,
                evidence_count: evidence.len(),
                dissent_generated: needs_dissent,
                total_time_ms: total_time,
                memory_used_mb: 0.0, // 由资源监控模块实际计算
            },
        }
    }

    /// 生成初步判断
    fn generate_initial_judgments(
        &self,
        _task: &JudgeTask,
        evidence: &[Evidence],
        _rule_matches: &[RuleMatch],
        _depth: &ReviewDepth,
    ) -> Vec<Judgment> {
        let mut judgments = Vec::new();

        // 从工具证据中提取判断
        for e in evidence {
            let severity = match &e.kind {
                super::evidence::EvidenceKind::ToolResult { .. } => BlockingLevel::Warning,
                super::evidence::EvidenceKind::RuleMatch { .. } => BlockingLevel::Blocker,
                super::evidence::EvidenceKind::HarnessResult { passed: false, .. } => BlockingLevel::Blocker,
                _ => BlockingLevel::Suggestion,
            };

            judgments.push(Judgment {
                id: format!("j_{}", uuid::Uuid::new_v4()),
                claim: e.description.clone(),
                severity,
                evidence: vec![e.clone()],
                rule_match: None,
                confidence: ConfidenceScore {
                    overall: 0.5,
                    level: ConfidenceLevel::Medium,
                    components: Default::default(),
                },
                dissent: None,
                recommended_action: vec!["请人工复核".into()],
            });
        }

        judgments
    }

    /// 检查与 harness Ground Truth 的冲突
    fn check_harness_conflict(&self, evidence: &[Evidence], task: &JudgeTask) -> bool {
        // 如果有测试失败，但判断未提及，视为冲突
        if let Some(ref tr) = task.test_results {
            if !tr.all_passed {
                let has_test_evidence = evidence.iter().any(|e| {
                    matches!(&e.kind, super::evidence::EvidenceKind::HarnessResult { .. })
                });
                if !has_test_evidence {
                    return true;
                }
            }
        }
        false
    }

    /// 合成最终判决
    fn compose_verdict(
        &self,
        task: &JudgeTask,
        judgments: &[Judgment],
        evidence: &[Evidence],
        rule_matches: &[RuleMatch],
        dissent_results: &[Option<DissentResult>],
        depth: &ReviewDepth,
    ) -> Verdict {
        // 统计
        let blockers: Vec<_> = judgments.iter()
            .filter(|j| matches!(j.confidence.level, ConfidenceLevel::High)
                && matches!(j.severity, BlockingLevel::Blocker))
            .collect();
        let warnings: Vec<_> = judgments.iter()
            .filter(|j| matches!(j.confidence.level, ConfidenceLevel::Medium))
            .collect();
        let suggestions: Vec<_> = judgments.iter()
            .filter(|j| matches!(j.confidence.level, ConfidenceLevel::Low))
            .collect();

        let merge_status = if !blockers.is_empty() {
            MergeStatus::Blocked
        } else if !warnings.is_empty() {
            MergeStatus::NeedsReview
        } else {
            MergeStatus::Approved
        };

        let summary = match merge_status {
            MergeStatus::Blocked => format!(
                "阻断合并: {} 个阻断问题, {} 个警告",
                blockers.len(), warnings.len()
            ),
            MergeStatus::NeedsReview => format!(
                "需人工复核: {} 个警告, {} 个建议",
                warnings.len(), suggestions.len()
            ),
            MergeStatus::Approved => format!(
                "允许合并: {} 个建议",
                suggestions.len()
            ),
        };

        // 构建推理树
        let dissent_for_tree = dissent_results.iter()
            .filter_map(|d| d.as_ref())
            .next();
        let reasoning_tree = self.reasoning_tracer.build_tree(
            task, evidence, rule_matches, dissent_for_tree, &summary,
        );

        // 平均置信度
        let avg_confidence = if judgments.is_empty() {
            ConfidenceScore {
                overall: 1.0,
                level: ConfidenceLevel::High,
                components: Default::default(),
            }
        } else {
            let avg = judgments.iter().map(|j| j.confidence.overall).sum::<f64>()
                / judgments.len() as f64;
            ConfidenceScore {
                overall: avg,
                level: ConfidenceEngine::default().calculate(&[], None, &[], None).level, // 简化
                components: Default::default(),
            }
        };

        let detail = format!(
            "审查深度: {:?} | 证据: {} 条 | 异议: {} | 阻断: {} / 警告: {} / 建议: {}",
            depth,
            evidence.len(),
            if dissent_results.iter().any(|d| d.is_some()) { "已生成" } else { "未触发" },
            blockers.len(), warnings.len(), suggestions.len()
        );

        Verdict {
            task_id: task.task_id.clone(),
            summary,
            detail,
            judgments: judgments.to_vec(),
            confidence: avg_confidence,
            reasoning_tree,
            merge_status,
        }
    }
}

impl Default for super::confidence::ConfidenceComponents {
    fn default() -> Self {
        Self {
            tool_evidence_strength: 0.5,
            rule_match_strength: 0.5,
            precedent_similarity: 0.5,
            dissent_unresolved_risk: 0.0,
        }
    }
}
