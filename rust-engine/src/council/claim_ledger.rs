/// Claim Ledger — 推演账本
/// 已有组件，v3.1.2 改造: 加 evidence 字段，链接到证据对象
/// 借鉴天府Agent 的「思考-验证-反馈」——每个 Claim 记录完整的推演路径

use serde::{Deserialize, Serialize};
use crate::engine::evidence::Evidence;
use crate::engine::confidence::ConfidenceScore;
use crate::engine::dissent::DissentResult;

/// 推演主张
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claim {
    pub id: String,
    pub task_id: String,
    pub timestamp: i64,

    /// 主张内容
    pub content: String,
    /// 主张类型
    pub claim_type: ClaimType,

    /// 【v3.1.2 新增】支撑该主张的证据列表
    pub evidence: Vec<Evidence>,

    /// 主张状态
    pub status: ClaimStatus,

    /// 置信度
    pub confidence: Option<ConfidenceScore>,

    /// 异议结果
    pub dissent: Option<DissentResult>,

    /// 推演路径 (记录从输入到此Claim的推理步骤)
    pub trace: Vec<TraceStep>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ClaimType {
    /// 安全漏洞主张
    SecurityVulnerability,
    /// 代码质量主张
    QualityIssue,
    /// 性能问题主张
    PerformanceIssue,
    /// 合规性主张
    ComplianceIssue,
    /// 可维护性主张
    MaintainabilityIssue,
    /// 正向主张 (代码优秀)
    PositiveObservation,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ClaimStatus {
    /// 已提出，等待验证
    Proposed,
    /// 已验证通过
    Verified,
    /// 已被驳回
    Rejected,
    /// 存在争议
    Disputed,
    /// 已确认 (人工确认)
    Confirmed,
}

/// 推演路径中的每一步
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceStep {
    pub order: usize,
    pub action: String,
    pub result: String,
    pub evidence_id: Option<String>,
}

/// Claim Ledger — 记录所有推演路径
pub struct ClaimLedger {
    claims: Vec<Claim>,
}

impl ClaimLedger {
    pub fn new() -> Self {
        Self { claims: Vec::new() }
    }

    /// 【v3.1.2 改造】记录一个新 Claim，必须绑定证据
    pub fn record(
        &mut self,
        task_id: &str,
        content: &str,
        claim_type: ClaimType,
        evidence: Vec<Evidence>,
    ) -> &Claim {
        let claim = Claim {
            id: format!("claim_{}", uuid::Uuid::new_v4()),
            task_id: task_id.to_string(),
            timestamp: chrono::Utc::now().timestamp_millis(),
            content: content.to_string(),
            claim_type,
            evidence,
            status: ClaimStatus::Proposed,
            confidence: None,
            dissent: None,
            trace: vec![TraceStep {
                order: 0,
                action: "Claim recorded".into(),
                result: content.to_string(),
                evidence_id: None,
            }],
        };
        self.claims.push(claim);
        self.claims.last().unwrap()
    }

    /// 更新 Claim 的置信度
    pub fn update_confidence(&mut self, claim_id: &str, confidence: ConfidenceScore) {
        if let Some(claim) = self.claims.iter_mut().find(|c| c.id == claim_id) {
            let confidence_percent = confidence.overall * 100.0;
            claim.confidence = Some(confidence);
            claim.trace.push(TraceStep {
                order: claim.trace.len(),
                action: "Confidence calculated".into(),
                result: format!("{:.0}%", confidence_percent),
                evidence_id: None,
            });
        }
    }

    /// 更新 Claim 的异议结果
    pub fn update_dissent(&mut self, claim_id: &str, dissent: DissentResult) {
        if let Some(claim) = self.claims.iter_mut().find(|c| c.id == claim_id) {
            let disputed = dissent.should_reduce_confidence;
            claim.dissent = Some(dissent);
            if disputed {
                claim.status = ClaimStatus::Disputed;
            }
            claim.trace.push(TraceStep {
                order: claim.trace.len(),
                action: "Dissent evaluated".into(),
                result: if disputed { "存在争议".into() } else { "异议已解决".into() },
                evidence_id: None,
            });
        }
    }

    /// 用户驳回某个 Claim
    pub fn reject(&mut self, claim_id: &str, reason: &str) {
        if let Some(claim) = self.claims.iter_mut().find(|c| c.id == claim_id) {
            claim.status = ClaimStatus::Rejected;
            claim.trace.push(TraceStep {
                order: claim.trace.len(),
                action: "User rejected".into(),
                result: reason.to_string(),
                evidence_id: None,
            });
        }
    }

    /// 用户确认某个 Claim
    pub fn confirm(&mut self, claim_id: &str) {
        if let Some(claim) = self.claims.iter_mut().find(|c| c.id == claim_id) {
            claim.status = ClaimStatus::Confirmed;
            claim.trace.push(TraceStep {
                order: claim.trace.len(),
                action: "User confirmed".into(),
                result: "已确认".into(),
                evidence_id: None,
            });
        }
    }

    /// 查询某个任务的所有 Claims
    pub fn get_by_task(&self, task_id: &str) -> Vec<&Claim> {
        self.claims.iter()
            .filter(|c| c.task_id == task_id)
            .collect()
    }

    /// 获取被驳回的 Claims (用于反馈学习)
    pub fn get_rejected(&self) -> Vec<&Claim> {
        self.claims.iter()
            .filter(|c| c.status == ClaimStatus::Rejected)
            .collect()
    }

    /// 获取存在争议的 Claims
    pub fn get_disputed(&self) -> Vec<&Claim> {
        self.claims.iter()
            .filter(|c| c.status == ClaimStatus::Disputed)
            .collect()
    }

    /// 【v3.1.2 新增】检查是否存在无证据的 Claim
    pub fn check_evidence_completeness(&self) -> Vec<&Claim> {
        self.claims.iter()
            .filter(|c| c.evidence.is_empty())
            .collect()
    }
}

impl Default for ClaimLedger {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_record_and_update_claim() {
        let mut ledger = ClaimLedger::new();
        let claim = ledger.record("task-1", "SQL注入风险", ClaimType::SecurityVulnerability, vec![]);
        assert_eq!(claim.status, ClaimStatus::Proposed);
        assert!(claim.evidence.is_empty());

        // 应能检测到无证据的 claim
        let incomplete = ledger.check_evidence_completeness();
        assert_eq!(incomplete.len(), 1);
    }

    #[test]
    fn test_reject_and_confirm() {
        let mut ledger = ClaimLedger::new();
        let claim = ledger.record("task-2", "圈复杂度过高", ClaimType::QualityIssue, vec![]);
        let id = claim.id.clone();

        ledger.reject(&id, "业务逻辑需要集中处理");
        let rejected: Vec<_> = ledger.get_rejected();
        assert_eq!(rejected.len(), 1);
        assert_eq!(rejected[0].id, id);
    }
}
