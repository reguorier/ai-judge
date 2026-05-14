// AI Judge v3.2.0 — Auditable Jury Architecture
// 从天府Agent 借鉴: Think-Verify-Feedback闭环 + GPRO置信度 + 知识溯源 + 可视化推理链
// 基于现有架构: Texas Council + Claim Ledger + Harness + Tauri

pub mod engine;
pub mod council;

pub use engine::{
    evidence::{Evidence, EvidenceCollector, EvidenceKind},
    confidence::{ConfidenceEngine, ConfidenceScore, ConfidenceComponents, ConfidenceLevel},
    dissent::{DissentAgent, DissentResult, RestrictedContext},
    risk_router::{RiskRouter, ReviewDepth},
    orchestrator::Orchestrator,
    reasoning_tracer::{ReasoningTracer, ReasoningNode, NodeKind, EvidenceSource},
    tools::base_tool::{BaseTool, ToolResult, Finding, Severity},
};

pub use council::{
    claim_ledger::{Claim, ClaimLedger, ClaimStatus},
    council::{CouncilMember, CouncilRole, TexasCouncil},
};

use serde::{Deserialize, Serialize};

/// 评判任务：进入AI Judge的输入
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JudgeTask {
    pub task_id: String,
    pub files_changed: usize,
    pub lines_added: usize,
    pub lines_deleted: usize,
    pub touched_modules: Vec<String>,
    pub risk_surface: Vec<String>,
    pub has_tests_changed: bool,
    pub test_results: Option<TestResults>,
    pub diff: Vec<FileDiff>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestResults {
    pub all_passed: bool,
    pub failed_tests: Vec<String>,
    pub coverage_delta: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileDiff {
    pub path: String,
    pub additions: usize,
    pub deletions: usize,
    pub hunks: Vec<DiffHunk>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiffHunk {
    pub start_line: usize,
    pub end_line: usize,
    pub content: String,
}

impl JudgeTask {
    pub fn diff_size(&self) -> usize {
        self.lines_added + self.lines_deleted
    }

    pub fn all_tests_pass(&self) -> bool {
        self.test_results.as_ref().map(|t| t.all_passed).unwrap_or(false)
    }

    pub fn touches_any(&self, domains: &[&str]) -> bool {
        self.risk_surface.iter().any(|r| domains.contains(&r.as_str()))
    }

    pub fn contains_policy_or_compliance(&self) -> bool {
        self.risk_surface.contains(&"compliance".to_string())
            || self.risk_surface.contains(&"policy".to_string())
    }
}

/// 规则匹配结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuleMatch {
    pub rule_id: String,
    pub source: String,
    pub applies_to: String,
    pub match_confidence: f64,
    pub blocking_level: BlockingLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BlockingLevel {
    Blocker,
    Warning,
    Suggestion,
}

/// 判例
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrecedentCase {
    pub case_id: String,
    pub similarity: f64,
    pub outcome: String,
    pub confirmed: bool,
}

/// 最终判决
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Verdict {
    pub task_id: String,
    pub summary: String,
    pub detail: String,
    pub judgments: Vec<Judgment>,
    pub confidence: ConfidenceScore,
    pub reasoning_tree: ReasoningNode,
    pub merge_status: MergeStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Judgment {
    pub id: String,
    pub claim: String,
    pub severity: BlockingLevel,
    pub evidence: Vec<Evidence>,
    pub rule_match: Option<RuleMatch>,
    pub confidence: ConfidenceScore,
    pub dissent: Option<DissentResult>,
    pub recommended_action: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum MergeStatus {
    Blocked,
    NeedsReview,
    Approved,
}

/// 任务分类（用于工具路由）
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum TaskCategory {
    Security,
    Performance,
    Style,
    Complexity,
    Testing,
    Dependency,
    Compliance,
}
