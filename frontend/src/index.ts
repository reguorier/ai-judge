/**
 * AI Judge UI Component Library
 *
 * 从天府Agent 借鉴的可视化推理链组件集
 * 用 Tauri 桌面端本地交互优势做超越
 */

export { ReasoningTree } from "./components/ReasoningTree";
export { ConfidenceBadge } from "./components/ConfidenceBadge";
export { EvidenceLink } from "./components/EvidenceLink";
export { DissentPanel } from "./components/DissentPanel";

export { progressive, colorSystem, confidenceToColor, confidenceToMergeAction } from "./lib/progressive";
export type * from "./lib/types";
