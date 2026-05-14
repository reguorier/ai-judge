/// 置信度引擎
/// 借鉴天府Agent 的 GPRO 算法——对推理链的每个节点输出概率
/// AI Judge 独有优势: 用 harness Ground Truth 替代天府的古籍验证

use serde::{Deserialize, Serialize};
use crate::{RuleMatch, PrecedentCase};
use super::evidence::Evidence;
use super::dissent::DissentResult;

/// 置信度得分
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceScore {
    /// 综合置信度 0.0-1.0
    pub overall: f64,
    /// 四维分解 (GPRO 节点概率映射)
    pub components: ConfidenceComponents,
    /// 置信度等级
    pub level: ConfidenceLevel,
}

/// 置信度四维拆解
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceComponents {
    /// 工具证据强度: 有 SAST/Lint/Test 支撑 → 高
    pub tool_evidence_strength: f64,
    /// 规则匹配强度: 规则精确命中度
    pub rule_match_strength: f64,
    /// 判例相似度: 历史类似案例支持度
    pub precedent_similarity: f64,
    /// 异议未解决风险: 反方论点未被驳倒的程度 (越高越扣分)
    pub dissent_unresolved_risk: f64,
}

/// 置信度等级
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ConfidenceLevel {
    /// ≥0.85: 可阻断
    High,
    /// 0.60-0.84: 需人工复核
    Medium,
    /// <0.60: 仅作建议
    Low,
}

/// 置信度引擎
pub struct ConfidenceEngine {
    /// 权重配置 (可被 Ground Truth 自动校准)
    pub weights: ConfidenceWeights,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceWeights {
    pub tool: f64,       // 默认 0.4
    pub rule: f64,       // 默认 0.3
    pub precedent: f64,  // 默认 0.2
    pub dissent_penalty: f64, // 默认 0.1
}

impl Default for ConfidenceWeights {
    fn default() -> Self {
        Self {
            tool: 0.4,
            rule: 0.3,
            precedent: 0.2,
            dissent_penalty: 0.1,
        }
    }
}

impl Default for ConfidenceEngine {
    fn default() -> Self {
        Self { weights: ConfidenceWeights::default() }
    }
}

impl ConfidenceEngine {
    pub fn new(weights: ConfidenceWeights) -> Self {
        Self { weights }
    }

    /// 核心函数: 计算置信度
    /// 对应天府Agent 的 GPRO 节点概率计算
    ///
    /// 公式:
    ///   overall = tool_strength * Wt + rule_strength * Wr
    ///           + precedent_similarity * Wp - dissent_risk * Wd
    ///
    /// 其中:
    ///   tool_strength: 可验证工具证据的比例
    ///   rule_strength: 规则匹配精度
    ///   precedent_similarity: 最相似判例的加权平均
    ///   dissent_risk: 异议Agent的反对强度
    pub fn calculate(
        &self,
        evidence: &[Evidence],
        rule_match: Option<&RuleMatch>,
        precedents: &[PrecedentCase],
        dissent: Option<&DissentResult>,
    ) -> ConfidenceScore {
        // 1. 计算工具证据强度
        let tool_strength = Self::calc_tool_strength(evidence);

        // 2. 获取规则匹配强度
        let rule_strength = rule_match
            .map(|r| r.match_confidence)
            .unwrap_or(0.5); // 无规则时不扣分也不加分 (中性)

        // 3. 判例相似度
        let precedent_s = if precedents.is_empty() {
            0.5 // 无判例时为中性
        } else {
            // 取前5个最相似判例，加权平均
            let mut sorted: Vec<_> = precedents.iter().collect();
            sorted.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap());
            let top_n = sorted.iter().take(5);
            let total: f64 = top_n.clone().map(|p| p.similarity).sum();
            let count = top_n.count().max(1) as f64;
            total / count
        };

        // 4. 异议未解决风险
        let dissent_risk = dissent
            .map(|d| d.strength)
            .unwrap_or(0.0);

        // 综合置信度 (clamp 到 0.0-1.0)
        let raw = tool_strength * self.weights.tool
                + rule_strength * self.weights.rule
                + precedent_s * self.weights.precedent
                - dissent_risk * self.weights.dissent_penalty;

        let overall = raw.max(0.0).min(1.0);
        let level = Self::classify(overall);

        ConfidenceScore {
            overall,
            level,
            components: ConfidenceComponents {
                tool_evidence_strength: tool_strength,
                rule_match_strength: rule_strength,
                precedent_similarity: precedent_s,
                dissent_unresolved_risk: dissent_risk,
            },
        }
    }

    /// 快速计算: 仅基于工具证据 (用于快判模式)
    pub fn quick_calculate(&self, evidence: &[Evidence]) -> ConfidenceScore {
        let tool_strength = Self::calc_tool_strength(evidence);
        let overall = tool_strength;

        ConfidenceScore {
            overall,
            level: Self::classify(overall),
            components: ConfidenceComponents {
                tool_evidence_strength: tool_strength,
                rule_match_strength: 0.5,
                precedent_similarity: 0.5,
                dissent_unresolved_risk: 0.0,
            },
        }
    }

    /// 工具证据强度: 可验证工具证据的比例
    fn calc_tool_strength(evidence: &[Evidence]) -> f64 {
        if evidence.is_empty() {
            return 0.0;
        }

        let verifiable_count = evidence.iter()
            .filter(|e| e.is_verifiable())
            .count();

        let avg_confidence = if verifiable_count > 0 {
            evidence.iter()
                .filter(|e| e.is_verifiable())
                .map(|e| e.intrinsic_confidence())
                .sum::<f64>() / verifiable_count as f64
        } else {
            0.0
        };

        // 可验证证据的比例 × 工具平均置信度
        (verifiable_count as f64 / evidence.len() as f64) * avg_confidence
    }

    fn classify(score: f64) -> ConfidenceLevel {
        if score >= 0.85 {
            ConfidenceLevel::High
        } else if score >= 0.60 {
            ConfidenceLevel::Medium
        } else {
            ConfidenceLevel::Low
        }
    }

    /// Harness Ground Truth 校准
    /// 当判断与测试结果冲突时，自动降权
    pub fn calibrate_with_ground_truth(
        &self,
        current: &ConfidenceScore,
        harness_conflict: bool,
    ) -> ConfidenceScore {
        if !harness_conflict {
            return current.clone();
        }

        // 与客观测试冲突 → 置信度骤降
        let new_overall = (current.overall * 0.3).max(0.0);
        ConfidenceScore {
            overall: new_overall,
            level: Self::classify(new_overall),
            components: ConfidenceComponents {
                tool_evidence_strength: current.components.tool_evidence_strength * 0.5,
                rule_match_strength: current.components.rule_match_strength,
                precedent_similarity: current.components.precedent_similarity,
                dissent_unresolved_risk: 0.9, // 标记高异议
            },
        }
    }

    /// 根据置信度等级决定合并策略
    pub fn merge_decision(&self, score: &ConfidenceScore, severity: &crate::BlockingLevel) -> MergeDecision {
        match (&score.level, severity) {
            (ConfidenceLevel::High, crate::BlockingLevel::Blocker) => MergeDecision::Block,
            (ConfidenceLevel::High, crate::BlockingLevel::Warning) => MergeDecision::Warn,
            (ConfidenceLevel::Medium, crate::BlockingLevel::Blocker) => MergeDecision::HumanReview,
            (ConfidenceLevel::Medium, _) => MergeDecision::Warn,
            (ConfidenceLevel::Low, _) => MergeDecision::Suggestion,
            _ => MergeDecision::Warn,
        }
    }
}

/// 合并策略
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum MergeDecision {
    /// 阻断合并
    Block,
    /// 需人工审核
    HumanReview,
    /// 警告
    Warn,
    /// 建议
    Suggestion,
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::super::evidence::EvidenceKind;

    fn make_evidence(verifiable: bool, confidence: f64) -> Evidence {
        Evidence {
            kind: EvidenceKind::ToolResult {
                tool_id: "test".into(),
                finding_id: "f1".into(),
                confidence,
                verifiable,
            },
            description: "test".into(),
            source_path: None,
            source_line: None,
        }
    }

    #[test]
    fn test_high_confidence_with_verifiable_evidence() {
        let engine = ConfidenceEngine::default();
        let evidence = vec![
            make_evidence(true, 0.95),
            make_evidence(true, 0.90),
        ];

        let score = engine.quick_calculate(&evidence);
        assert!(score.overall > 0.8);
        assert_eq!(score.level, ConfidenceLevel::High);
    }

    #[test]
    fn test_low_confidence_without_evidence() {
        let engine = ConfidenceEngine::default();
        let evidence: Vec<Evidence> = vec![];

        let score = engine.quick_calculate(&evidence);
        assert_eq!(score.overall, 0.0);
        assert_eq!(score.level, ConfidenceLevel::Low);
    }

    #[test]
    fn test_ground_truth_calibration_conflict() {
        let engine = ConfidenceEngine::default();
        let evidence = vec![make_evidence(true, 0.95)];
        let original = engine.quick_calculate(&evidence);
        assert!(original.overall > 0.8);

        let calibrated = engine.calibrate_with_ground_truth(&original, true);
        assert!(calibrated.overall < 0.5, "Should be drastically reduced, got {}", calibrated.overall);
    }
}
