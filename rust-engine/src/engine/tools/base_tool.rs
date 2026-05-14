/// 插件化工具接口
/// 借鉴天府Agent 的 250+ 工具矩阵设计
/// 统一接口、统一输出格式、支持按任务类型自动路由

use serde::{Deserialize, Serialize};
use crate::{JudgeTask, TaskCategory};

/// 工具运行结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ToolResult {
    Findings(Vec<Finding>),
    Empty,
}

/// 工具发现项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub id: String,
    pub severity: Severity,
    pub file_path: String,
    pub line: u32,
    pub description: String,
    pub rule_ref: Option<String>,
    pub suggestion: Option<String>,
}

/// 严重度
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum Severity {
    Critical,
    High,
    Medium,
    Low,
    Info,
}

impl Severity {
    pub fn label(&self) -> &str {
        match self {
            Self::Critical => "critical",
            Self::High => "high",
            Self::Medium => "medium",
            Self::Low => "low",
            Self::Info => "info",
        }
    }
}

/// 工具错误
#[derive(Debug, thiserror::Error)]
pub enum ToolError {
    #[error("Tool execution failed: {0}")]
    Execution(String),
    #[error("Tool not applicable to task")]
    NotApplicable,
    #[error("Tool timed out after {0}ms")]
    Timeout(u64),
}

/// 工具 trait——所有分析器必须实现
/// 借鉴天府Agent 的插件化设计
pub trait BaseTool: Send + Sync {
    /// 工具名称
    fn name(&self) -> String;

    /// 工具版本
    fn version(&self) -> String { "1.0.0".into() }

    /// 工具自身的置信度（如 SAST 的准确率）
    fn confidence(&self) -> f64;

    /// 是否可被客观验证
    fn is_verifiable(&self) -> bool;

    /// 运行工具: 输入任务，输出结构化结果
    fn run(&self, task: &JudgeTask) -> Result<ToolResult, ToolError>;

    /// 工具适用的判断类型（用于自动路由）
    fn applicable_to(&self) -> Vec<TaskCategory>;

    /// 工具的资源需求评估
    fn resource_estimate(&self) -> ResourceEstimate {
        ResourceEstimate::default()
    }
}

/// 工具资源需求评估
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceEstimate {
    /// 预估内存占用 (MB)
    pub memory_mb: usize,
    /// 预估 CPU 时间 (ms)
    pub cpu_time_ms: u64,
    /// 是否需要网络访问
    pub requires_network: bool,
    /// 是否可在后台运行
    pub can_run_background: bool,
}

impl Default for ResourceEstimate {
    fn default() -> Self {
        Self {
            memory_mb: 50,
            cpu_time_ms: 500,
            requires_network: false,
            can_run_background: true,
        }
    }
}

/// 工具注册表——管理所有已注册的工具
pub struct ToolRegistry {
    tools: Vec<Box<dyn BaseTool>>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self { tools: Vec::new() }
    }

    /// 注册工具
    pub fn register(&mut self, tool: Box<dyn BaseTool>) {
        tracing::info!("Registered tool: {} v{}", tool.name(), tool.version());
        self.tools.push(tool);
    }

    /// 按任务分类获取适用工具
    pub fn get_for_category(&self, category: &TaskCategory) -> Vec<&dyn BaseTool> {
        self.tools.iter()
            .filter(|t| t.applicable_to().contains(category))
            .map(|t| t.as_ref())
            .collect()
    }

    /// 获取所有工具
    pub fn all(&self) -> &[Box<dyn BaseTool>] {
        &self.tools
    }

    /// 按名称获取工具
    pub fn get_by_name(&self, name: &str) -> Option<&dyn BaseTool> {
        self.tools.iter()
            .find(|t| t.name() == name)
            .map(|t| t.as_ref())
    }

    /// 强制工具列表（无论适用性）
    pub fn get_mandatory(&self, names: &[String]) -> Vec<&dyn BaseTool> {
        names.iter()
            .filter_map(|n| self.get_by_name(n))
            .collect()
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockTool {
        name: String,
        applicable: Vec<TaskCategory>,
    }
    impl BaseTool for MockTool {
        fn name(&self) -> String { self.name.clone() }
        fn confidence(&self) -> f64 { 0.9 }
        fn is_verifiable(&self) -> bool { true }
        fn run(&self, _task: &JudgeTask) -> Result<ToolResult, ToolError> {
            Ok(ToolResult::Empty)
        }
        fn applicable_to(&self) -> Vec<TaskCategory> { self.applicable.clone() }
    }

    #[test]
    fn test_registry_filter() {
        let mut registry = ToolRegistry::new();
        registry.register(Box::new(MockTool {
            name: "security_scanner".into(),
            applicable: vec![TaskCategory::Security],
        }));
        registry.register(Box::new(MockTool {
            name: "style_checker".into(),
            applicable: vec![TaskCategory::Style],
        }));

        let security_tools = registry.get_for_category(&TaskCategory::Security);
        assert_eq!(security_tools.len(), 1);
        assert_eq!(security_tools[0].name(), "security_scanner");
    }
}
