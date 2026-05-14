/// Texas Council (德州议会) — 已有组件
/// v3.1.2 改造: 加入 DissentAgent 角色，实现真正的对抗性合议
/// 借鉴天府Agent 的多 Agent 协作，但不做完整合议庭，只用角色化调度

use serde::{Deserialize, Serialize};
use crate::engine::dissent::{DissentAgent, DissentResult, RestrictedContext};
use crate::engine::evidence::Evidence;
use crate::JudgeTask;

/// 议会成员角色
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CouncilRole {
    /// 事实认定者——调用工具，收集客观数据
    FactFinder,
    /// 规则执行者——匹配规则库，输出规则判断
    RuleEnforcer,
    /// 异议者——反方，专门挑战主判断 (v3.1.2 新增)
    DevilAdvocate,
    /// 仲裁者——解决冲突，生成最终结论
    Arbitrator,
    /// 报告撰写者——生成可审计判决书
    Reporter,
}

/// 议会成员
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CouncilMember {
    pub id: String,
    pub role: CouncilRole,
    pub model_id: String,
    /// v3.1.2 新增: 是否为异议角色 (影响 Temperature 等参数)
    pub is_adversarial: bool,
}

/// Texas Council
pub struct TexasCouncil {
    members: Vec<CouncilMember>,
    dissent_agent: DissentAgent,
}

impl TexasCouncil {
    pub fn new() -> Self {
        Self {
            members: vec![
                CouncilMember {
                    id: "fact_finder".into(),
                    role: CouncilRole::FactFinder,
                    model_id: "local-8b".into(),
                    is_adversarial: false,
                },
                CouncilMember {
                    id: "rule_enforcer".into(),
                    role: CouncilRole::RuleEnforcer,
                    model_id: "local-8b".into(),
                    is_adversarial: false,
                },
                CouncilMember {
                    id: "arbitrator".into(),
                    role: CouncilRole::Arbitrator,
                    model_id: "local-8b".into(),
                    is_adversarial: false,
                },
                CouncilMember {
                    id: "reporter".into(),
                    role: CouncilRole::Reporter,
                    model_id: "local-4b".into(),
                    is_adversarial: false,
                },
            ],
            dissent_agent: DissentAgent::default(),
        }
    }

    /// 【v3.1.2 新增】注册异议角色
    pub fn register_devil_advocate(&mut self, model_id: &str) {
        self.members.push(CouncilMember {
            id: "devil_advocate".into(),
            role: CouncilRole::DevilAdvocate,
            model_id: model_id.to_string(),
            is_adversarial: true,
        });
    }

    /// 是否有异议角色
    pub fn has_devil_advocate(&self) -> bool {
        self.members.iter()
            .any(|m| m.role == CouncilRole::DevilAdvocate)
    }

    /// 获取异议角色配置
    pub fn get_adversarial_config(&self) -> Option<AdversarialConfig> {
        if self.has_devil_advocate() {
            Some(AdversarialConfig {
                temperature: 0.8,   // Gemini方案: 高温度鼓励发散
                top_p: 0.95,
                context_isolation: true,
                max_tokens: 512,
            })
        } else {
            None
        }
    }

    /// 获取事实认定角色的配置
    pub fn get_fact_finder_config(&self) -> FactFinderConfig {
        FactFinderConfig {
            temperature: 0.0,    // 极低温度保证确定性
            top_p: 0.1,
            max_tokens: 256,
        }
    }

    /// 执行异议挑战
    pub fn run_dissent(
        &self,
        claim: &str,
        evidence: &[Evidence],
        task: &JudgeTask,
    ) -> Option<DissentResult> {
        if !self.has_devil_advocate() {
            return None;
        }

        let restricted = RestrictedContext::from_task(task);
        Some(self.dissent_agent.challenge(claim, evidence, Some(&restricted)))
    }
}

impl Default for TexasCouncil {
    fn default() -> Self {
        Self::new()
    }
}

/// 异议角色配置 (Gemini 方案)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdversarialConfig {
    pub temperature: f32,
    pub top_p: f32,
    pub context_isolation: bool,
    pub max_tokens: usize,
}

/// 事实认定角色配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FactFinderConfig {
    pub temperature: f32,
    pub top_p: f32,
    pub max_tokens: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_council_without_dissent() {
        let council = TexasCouncil::new();
        assert!(!council.has_devil_advocate());
        assert!(council.run_dissent("test", &[], &JudgeTask {
            task_id: "t1".into(),
            files_changed: 0,
            lines_added: 0,
            lines_deleted: 0,
            touched_modules: vec![],
            risk_surface: vec![],
            has_tests_changed: false,
            test_results: None,
            diff: vec![],
        }).is_none());
    }

    #[test]
    fn test_council_with_dissent() {
        let mut council = TexasCouncil::new();
        council.register_devil_advocate("local-8b");
        assert!(council.has_devil_advocate());
        assert!(council.get_adversarial_config().is_some());
        assert_eq!(council.get_adversarial_config().unwrap().temperature, 0.8);
    }
}
