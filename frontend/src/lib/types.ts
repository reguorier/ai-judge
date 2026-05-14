/**
 * Shared types for the AI Judge frontend
 * Mirrors the Rust backend data structures
 */

export interface ReasoningNodeData {
  id: string;
  kind: "fact" | "evidence" | "rule" | "dissent" | "conclusion";
  label: string;
  detail: string;
  confidence?: number;
  source?: EvidenceSource;
  children: ReasoningNodeData[];
  disputed: boolean;
  collapsedByDefault: boolean;
}

export interface EvidenceSource {
  filePath: string;
  line?: number;
  ruleId?: string;
  toolName?: string;
}

export interface ConfidenceComponents {
  toolEvidenceStrength: number;
  ruleMatchStrength: number;
  precedentSimilarity: number;
  dissentUnresolvedRisk: number;
}

export type ConfidenceLevel = "high" | "medium" | "low";

export interface ConfidenceScore {
  overall: number;
  components: ConfidenceComponents;
  level: ConfidenceLevel;
}

export interface EvidenceItem {
  id: string;
  kind: EvidenceKind;
  description: string;
  sourcePath?: string;
  sourceLine?: number;
  intrinsicConfidence: number;
  isVerifiable: boolean;
}

export type EvidenceKind =
  | { type: "tool_result"; toolId: string; findingId: string; confidence: number; verifiable: boolean }
  | { type: "rule_match"; ruleId: string; source: string; matchConfidence: number }
  | { type: "harness_result"; testSuite: string; passed: boolean; coverageDelta: number }
  | { type: "precedent"; caseId: string; similarity: number; outcome: string };

export interface DissentData {
  strength: number;
  counterarguments: CounterArgument[];
  requiredChecks: string[];
  shouldReduceConfidence: boolean;
}

export interface CounterArgument {
  claim: string;
  reasoning: string;
  severity: "fatal" | "strong" | "weak";
}

export interface VerdictData {
  taskId: string;
  summary: string;
  detail: string;
  judgments: JudgmentData[];
  confidence: ConfidenceScore;
  reasoningTree: ReasoningNodeData;
  mergeStatus: "blocked" | "needs_review" | "approved";
}

export interface JudgmentData {
  id: string;
  claim: string;
  severity: "blocker" | "warning" | "suggestion";
  evidence: EvidenceItem[];
  confidence: ConfidenceScore;
  dissent?: DissentData;
  recommendedAction: string[];
}

/** 渐进式明示级别 */
export type DisclosureLevel = 0 | 1 | 2;
