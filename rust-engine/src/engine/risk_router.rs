/// 风险分级路由
/// 借鉴天府Agent 的分级调度——critical任务走合议，trivial任务走快判

use serde::{Deserialize, Serialize};
use crate::JudgeTask;

/// 审查深度
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ReviewDepth {
    /// 全合议: 事实认定 + 规则 + 异议 + 置信度 + 判例
    FullJury,
    /// 标准 + 异议: 标准审查 + 反方Agent
    StandardWithDissent,
    /// 标准: 事实 + 规则 + 置信度
    Standard,
    /// 快速: 只用工具结果 + 规则
    FastCheck,
}

/// 风险路由配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskRouterConfig {
    /// 高敏感领域 (触发 FullJury)
    pub high_sensitivity_domains: Vec<String>,
    /// 合规相关关键词
    pub compliance_keywords: Vec<String>,
    /// 快判最大变更行数
    pub fast_check_max_lines: usize,
    /// 是否强制所有安全类任务走 FullJury
    pub force_full_jury_on_security: bool,
}

impl Default for RiskRouterConfig {
    fn default() -> Self {
        Self {
            high_sensitivity_domains: vec![
                "payment".into(), "auth".into(), "privacy".into(),
                "security".into(), "data".into(), "encryption".into(),
                "credentials".into(), "token".into(), "session".into(),
            ],
            compliance_keywords: vec![
                "compliance".into(), "policy".into(), "regulation".into(),
                "gdpr".into(), "hipaa".into(), "soc2".into(), "pci".into(),
            ],
            fast_check_max_lines: 30,
            force_full_jury_on_security: true,
        }
    }
}

/// 风险路由
pub struct RiskRouter {
    config: RiskRouterConfig,
}

impl Default for RiskRouter {
    fn default() -> Self {
        Self { config: RiskRouterConfig::default() }
    }
}

impl RiskRouter {
    pub fn new(config: RiskRouterConfig) -> Self {
        Self { config }
    }

    /// 核心函数: 按风险分类
    pub fn classify(&self, task: &JudgeTask) -> ReviewDepth {
        let high_sensitivity_domains = self.high_sensitivity_domains();

        // 1. 安全/支付/隐私/认证等敏感领域 → 必须全合议
        if self.config.force_full_jury_on_security
            && task.touches_any(&high_sensitivity_domains) {
            tracing::info!("Task {} classified as FullJury: touches sensitive domain", task.task_id);
            return ReviewDepth::FullJury;
        }

        // 2. 合规/策略相关 → 标准 + 异议
        if task.contains_policy_or_compliance()
            || self.has_compliance_keywords(task) {
            tracing::info!("Task {} classified as StandardWithDissent: compliance", task.task_id);
            return ReviewDepth::StandardWithDissent;
        }

        // 3. 变更极小 + 测试全过 + 无敏感领域 → 快判
        if task.diff_size() <= self.config.fast_check_max_lines
            && task.all_tests_pass()
            && !task.touches_any(&high_sensitivity_domains) {
            tracing::info!("Task {} classified as FastCheck: small diff + tests pass", task.task_id);
            return ReviewDepth::FastCheck;
        }

        // 4. 默认标准审查
        ReviewDepth::Standard
    }

    /// 是否需要异议Agent
    pub fn needs_dissent(&self, depth: &ReviewDepth, task: &JudgeTask) -> bool {
        let high_sensitivity_domains = self.high_sensitivity_domains();

        match depth {
            ReviewDepth::FullJury => true,
            ReviewDepth::StandardWithDissent => true,
            ReviewDepth::Standard => {
                // 即使标准模式，如果触及敏感领域也加异议
                task.touches_any(&high_sensitivity_domains)
            }
            ReviewDepth::FastCheck => false,
        }
    }

    /// 是否需要判例检索
    pub fn needs_precedent_search(&self, depth: &ReviewDepth) -> bool {
        matches!(depth, ReviewDepth::FullJury | ReviewDepth::StandardWithDissent)
    }

    /// 工具调用策略
    pub fn tool_strategy(&self, depth: &ReviewDepth) -> ToolStrategy {
        match depth {
            ReviewDepth::FullJury => ToolStrategy {
                run_all: true,
                mandatory: vec!["sast".into(), "lint".into(), "test".into(), "ast".into()],
                optional: vec!["dependency".into(), "performance".into(), "coverage".into()],
            },
            ReviewDepth::StandardWithDissent | ReviewDepth::Standard => ToolStrategy {
                run_all: false,
                mandatory: vec!["sast".into(), "lint".into()],
                optional: vec!["ast".into(), "test".into()],
            },
            ReviewDepth::FastCheck => ToolStrategy {
                run_all: false,
                mandatory: vec!["lint".into()],
                optional: vec![],
            },
        }
    }

    /// 模型选择策略
    pub fn model_strategy(&self, depth: &ReviewDepth) -> ModelStrategy {
        match depth {
            ReviewDepth::FullJury => ModelStrategy {
                use_local: true,
                allow_remote: true,
                min_context_window: 8192,
            },
            ReviewDepth::StandardWithDissent | ReviewDepth::Standard => ModelStrategy {
                use_local: true,
                allow_remote: false,
                min_context_window: 4096,
            },
            ReviewDepth::FastCheck => ModelStrategy {
                use_local: true,
                allow_remote: false,
                min_context_window: 2048,
            },
        }
    }

    fn has_compliance_keywords(&self, task: &JudgeTask) -> bool {
        task.risk_surface.iter().any(|r| {
            self.config.compliance_keywords.iter()
                .any(|k| r.to_lowercase().contains(&k.to_lowercase()))
        })
    }

    fn high_sensitivity_domains(&self) -> Vec<&str> {
        self.config.high_sensitivity_domains
            .iter()
            .map(String::as_str)
            .collect()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolStrategy {
    pub run_all: bool,
    pub mandatory: Vec<String>,
    pub optional: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelStrategy {
    pub use_local: bool,
    pub allow_remote: bool,
    pub min_context_window: usize,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::TestResults;

    fn make_task(id: &str, risk: Vec<&str>, diff_size: usize, tests_pass: bool) -> JudgeTask {
        JudgeTask {
            task_id: id.into(),
            files_changed: 1,
            lines_added: diff_size / 2,
            lines_deleted: diff_size / 2,
            touched_modules: vec!["test".into()],
            risk_surface: risk.iter().map(|s| s.to_string()).collect(),
            has_tests_changed: false,
            test_results: Some(TestResults {
                all_passed: tests_pass,
                failed_tests: vec![],
                coverage_delta: 0.0,
            }),
            diff: vec![],
        }
    }

    #[test]
    fn test_full_jury_on_security() {
        let router = RiskRouter::default();
        let task = make_task("t1", vec!["auth", "payment"], 100, true);
        assert_eq!(router.classify(&task), ReviewDepth::FullJury);
    }

    #[test]
    fn test_fast_check_on_small_diff() {
        let router = RiskRouter::default();
        let task = make_task("t2", vec!["style"], 20, true);
        assert_eq!(router.classify(&task), ReviewDepth::FastCheck);
    }

    #[test]
    fn test_standard_on_normal_task() {
        let router = RiskRouter::default();
        let task = make_task("t3", vec!["ui"], 200, false);
        assert_eq!(router.classify(&task), ReviewDepth::Standard);
    }

    #[test]
    fn test_dissent_needed_for_full_jury() {
        let router = RiskRouter::default();
        let task = make_task("t4", vec!["security"], 100, true);
        let depth = router.classify(&task);
        assert!(router.needs_dissent(&depth, &task));
    }
}
