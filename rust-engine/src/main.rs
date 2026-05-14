//! AI Judge v3.2.0 — Full Orchestration Example
//!
//! 完整的评判流程示例:
//! 1. 风险路由 → 2. 证据收集 → 3. 异议挑战 → 4. 置信度计算 → 5. 推理树构建 → 6. 最终判决

use ai_judge_engine::{
    JudgeTask, TestResults, FileDiff, DiffHunk, Verdict, MergeStatus,
    RuleMatch, BlockingLevel, PrecedentCase,
    engine::{
        evidence::EvidenceCollector,
        confidence::{ConfidenceEngine, ConfidenceWeights},
        dissent::{DissentAgent, RestrictedContext},
        risk_router::RiskRouter,
        reasoning_tracer::ReasoningTracer,
        tools::base_tool::{BaseTool, ToolResult, Finding, Severity, ToolRegistry, ToolError},
    },
    council::{
        claim_ledger::ClaimLedger,
        council::TexasCouncil,
    },
    TaskCategory,
};

// ─── Mock Tool Implementations ────────────────────────

struct SASTTool;
impl BaseTool for SASTTool {
    fn name(&self) -> String { "sast".into() }
    fn confidence(&self) -> f64 { 0.95 }
    fn is_verifiable(&self) -> bool { true }
    fn run(&self, _task: &JudgeTask) -> Result<ToolResult, ToolError> {
        Ok(ToolResult::Findings(vec![
            Finding {
                id: "sast_001".into(),
                severity: Severity::Critical,
                file_path: "payment/checkout.ts".into(),
                line: 89,
                description: "SQL注入风险: 用户输入直接拼入SQL查询".into(),
                rule_ref: Some("OWASP A03:2021".into()),
                suggestion: Some("改用参数化查询".into()),
            }
        ]))
    }
    fn applicable_to(&self) -> Vec<TaskCategory> {
        vec![TaskCategory::Security]
    }
}

struct ASTTool;
impl BaseTool for ASTTool {
    fn name(&self) -> String { "ast".into() }
    fn confidence(&self) -> f64 { 0.90 }
    fn is_verifiable(&self) -> bool { true }
    fn run(&self, _task: &JudgeTask) -> Result<ToolResult, ToolError> {
        Ok(ToolResult::Findings(vec![
            Finding {
                id: "ast_001".into(),
                severity: Severity::Medium,
                file_path: "auth/login.ts".into(),
                line: 45,
                description: "圈复杂度 18，超过阈值 10".into(),
                rule_ref: Some("complexity-threshold".into()),
                suggestion: Some("考虑拆分为多个小函数".into()),
            }
        ]))
    }
    fn applicable_to(&self) -> Vec<TaskCategory> {
        vec![TaskCategory::Complexity]
    }
}

struct LintTool;
impl BaseTool for LintTool {
    fn name(&self) -> String { "lint".into() }
    fn confidence(&self) -> f64 { 0.99 }
    fn is_verifiable(&self) -> bool { true }
    fn run(&self, _task: &JudgeTask) -> Result<ToolResult, ToolError> {
        Ok(ToolResult::Findings(vec![
            Finding {
                id: "lint_001".into(),
                severity: Severity::Low,
                file_path: "auth/login.ts".into(),
                line: 12,
                description: "变量使用 snake_case，规范要求 camelCase".into(),
                rule_ref: Some("naming-convention".into()),
                suggestion: Some("改为 camelCase 命名".into()),
            }
        ]))
    }
    fn applicable_to(&self) -> Vec<TaskCategory> {
        vec![TaskCategory::Style]
    }
}

// ─── Main Orchestration Example ───────────────────────

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    println!("═══ AI Judge v3.2.0 — Auditable Jury Architecture ═══\n");

    // 1. 构建评判任务
    let task = JudgeTask {
        task_id: "PR#342".into(),
        files_changed: 2,
        lines_added: 147,
        lines_deleted: 38,
        touched_modules: vec!["payment".into(), "auth".into()],
        risk_surface: vec!["security".into(), "payment".into()],
        has_tests_changed: false,
        test_results: Some(TestResults {
            all_passed: true,
            failed_tests: vec![],
            coverage_delta: -0.03,
        }),
        diff: vec![
            FileDiff {
                path: "payment/checkout.ts".into(),
                additions: 89,
                deletions: 15,
                hunks: vec![DiffHunk {
                    start_line: 80,
                    end_line: 170,
                    content: "fn checkout() { ... }".into(),
                }],
            },
            FileDiff {
                path: "auth/login.ts".into(),
                additions: 58,
                deletions: 23,
                hunks: vec![DiffHunk {
                    start_line: 10,
                    end_line: 80,
                    content: "fn login() { ... }".into(),
                }],
            },
        ],
    };

    // 2. 初始化组件
    let mut tool_registry = ToolRegistry::new();
    tool_registry.register(Box::new(SASTTool));
    tool_registry.register(Box::new(ASTTool));
    tool_registry.register(Box::new(LintTool));

    let evidence_collector = EvidenceCollector::new(vec![]); // 实际中用 registry 收集

    let confidence_engine = ConfidenceEngine::new(ConfidenceWeights {
        tool: 0.4,
        rule: 0.3,
        precedent: 0.2,
        dissent_penalty: 0.1,
    });

    let dissent_agent = DissentAgent::new(0.8);

    let risk_router = RiskRouter::default();

    let mut texas_council = TexasCouncil::new();
    texas_council.register_devil_advocate("local-8b");

    let reasoning_tracer = ReasoningTracer;

    let mut claim_ledger = ClaimLedger::new();

    // 3. 风险分级
    let depth = risk_router.classify(&task);
    let needs_dissent = risk_router.needs_dissent(&depth, &task);
    println!("审查深度: {:?}", depth);
    println!("异议Agent: {}", if needs_dissent { "激活" } else { "未触发" });

    // 4. 证据收集 (Think 阶段)
    let evidence = evidence_collector.collect(&task);
    println!("\n收集到 {} 条证据:", evidence.len());
    for e in &evidence {
        println!("  • {} [可验证: {}]", e.description, e.is_verifiable());
    }

    // 5. 规则匹配
    let rule_matches = vec![
        RuleMatch {
            rule_id: "owasp_a03_2021".into(),
            source: "OWASP A03:2021 §3.2.1".into(),
            applies_to: "payment/checkout.ts:89".into(),
            match_confidence: 0.95,
            blocking_level: BlockingLevel::Blocker,
        },
        RuleMatch {
            rule_id: "complexity_threshold".into(),
            source: "团队规范 §3.4".into(),
            applies_to: "auth/login.ts:45-78".into(),
            match_confidence: 0.75,
            blocking_level: BlockingLevel::Warning,
        },
    ];

    // 6. 判例检索
    let precedents = vec![
        PrecedentCase {
            case_id: "PR#287".into(),
            similarity: 0.88,
            outcome: "确认为真实SQL注入漏洞".into(),
            confirmed: true,
        },
    ];

    // 7. 异议挑战 (Verify 阶段)
    let restricted = RestrictedContext::from_task(&task);
    let claim = "payment/checkout.ts:89 存在 SQL 注入风险";
    let dissent = if needs_dissent {
        Some(dissent_agent.challenge(claim, &evidence, Some(&restricted)))
    } else {
        None
    };

    if let Some(ref d) = dissent {
        println!("\n异议Agent 报告:");
        println!("  强度: {:.0}%", d.strength * 100.0);
        println!("  反方论点: {} 条", d.counterarguments.len());
        for (i, arg) in d.counterarguments.iter().enumerate() {
            println!("    {}. {}: {}", i + 1, arg.claim, arg.reasoning);
        }
        println!("  需要补验证: {:?}", d.required_checks);
    }

    // 8. 记录 Claim Ledger
    let claim_record = claim_ledger.record(
        &task.task_id,
        claim,
        ai_judge_engine::council::claim_ledger::ClaimType::SecurityVulnerability,
        evidence.clone(),
    );
    let claim_id = claim_record.id.clone();

    // 9. 置信度计算 (GPRO)
    let confidence = confidence_engine.calculate(
        &evidence,
        rule_matches.first(),
        &precedents,
        dissent.as_ref(),
    );

    claim_ledger.update_confidence(&claim_id, confidence.clone());

    println!("\n置信度引擎 报告:");
    println!("  综合置信度: {:.0}%", confidence.overall * 100.0);
    println!("  等级: {:?}", confidence.level);
    println!("  工具证据: {:.0}%", confidence.components.tool_evidence_strength * 100.0);
    println!("  规则匹配: {:.0}%", confidence.components.rule_match_strength * 100.0);
    println!("  判例相似: {:.0}%", confidence.components.precedent_similarity * 100.0);
    println!("  异议风险: {:.0}%", confidence.components.dissent_unresolved_risk * 100.0);

    // 10. Harness Ground Truth 校准
    let harness_conflict = false; // 测试全部通过，无冲突
    let calibrated = confidence_engine.calibrate_with_ground_truth(&confidence, harness_conflict);

    // 11. 合并决策
    let merge_decision = confidence_engine.merge_decision(&calibrated, &BlockingLevel::Blocker);
    println!("\n合并决策: {:?}", merge_decision);

    // 12. 构建推理树 (可视化)
    let dissent_for_tree = dissent.as_ref();
    let verdict_summary = match merge_decision {
        ai_judge_engine::engine::confidence::MergeDecision::Block => "阻断合并: 1 个阻断问题".to_string(),
        _ => "需人工复核".to_string(),
    };

    let reasoning_tree = reasoning_tracer.build_tree(
        &task,
        &evidence,
        &rule_matches,
        dissent_for_tree,
        &verdict_summary,
    );

    // 13. 最终判决
    let verdict = Verdict {
        task_id: task.task_id.clone(),
        summary: verdict_summary,
        detail: format!(
            "审查深度: {:?} | 证据: {} 条 | 异议: {}",
            depth,
            evidence.len(),
            if dissent.is_some() { "已生成" } else { "未触发" }
        ),
        judgments: vec![],
        confidence: calibrated,
        reasoning_tree,
        merge_status: match merge_decision {
            ai_judge_engine::engine::confidence::MergeDecision::Block => MergeStatus::Blocked,
            ai_judge_engine::engine::confidence::MergeDecision::HumanReview => MergeStatus::NeedsReview,
            _ => MergeStatus::Approved,
        },
    };

    // 14. 输出最终判决
    println!("\n═══ 最终判决 ═══");
    println!("{}", verdict.summary);
    println!("状态: {:?}", verdict.merge_status);
    println!("置信度: {:.0}%", verdict.confidence.overall * 100.0);
    println!("推理树: {} 个根节点", verdict.reasoning_tree.children.len());

    // 15. 模拟用户反馈
    if merge_decision == ai_judge_engine::engine::confidence::MergeDecision::Block {
        println!("\n模拟用户反馈: 确认此阻断");
        claim_ledger.confirm(&claim_id);
    }

    let rejected = claim_ledger.get_rejected();
    let disputed = claim_ledger.get_disputed();
    println!("\n反馈摘要: 驳回 {} 条 | 争议 {} 条", rejected.len(), disputed.len());

    println!("\n═══ AI Judge v3.2.0 评判完成 ═══");
    Ok(())
}
