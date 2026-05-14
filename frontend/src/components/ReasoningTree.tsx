/**
 * ReasoningTree — 树状推理链可视化
 *
 * 借鉴天府Agent 的可视化推理链，用 Tauri 桌面端交互优势做超越:
 * - 三级渐进式明示 (Gemini 方案)
 * - 点击文件路径 → 调用 Tauri invoke 打开本地 IDE
 * - macOS 原生低饱和色彩系统
 */

import React, { useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/tauri";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { EvidenceLink } from "./EvidenceLink";
import { DissentPanel } from "./DissentPanel";
import { progressive } from "../lib/progressive";
import type { ReasoningNodeData, EvidenceSource } from "../lib/types";

// ─── Types ───────────────────────────────────────────

interface ReasoningTreeProps {
  node: ReasoningNodeData;
  /** 渐进式明示级别: 0=Surface, 1=Popover, 2=Full */
  disclosureLevel?: 0 | 1 | 2;
  /** 节点点击回调 */
  onNodeClick?: (node: ReasoningNodeData) => void;
  /** 文件跳转回调 (Tauri invoke) */
  onFileJump?: (source: EvidenceSource) => void;
}

// ─── Component ───────────────────────────────────────

export const ReasoningTree: React.FC<ReasoningTreeProps> = ({
  node,
  disclosureLevel = 1,
  onNodeClick,
  onFileJump,
}) => {
  const [expanded, setExpanded] = useState(
    disclosureLevel >= 1 || node.kind === "conclusion"
  );
  const [popoverVisible, setPopoverVisible] = useState(false);

  const handleToggle = useCallback(() => {
    setExpanded((prev) => !prev);
    onNodeClick?.(node);
  }, [node, onNodeClick]);

  const handleFileJump = useCallback(
    async (source: EvidenceSource) => {
      if (source.filePath) {
        try {
          await invoke("open_in_editor", {
            filePath: source.filePath,
            line: source.line ?? 1,
          });
        } catch (err) {
          console.error("Failed to open in IDE:", err);
        }
      }
      onFileJump?.(source);
    },
    [onFileJump]
  );

  // ─── 第一级 Surface: 只展示状态标记 ──────────────────
  if (disclosureLevel === 0 && node.kind === "conclusion") {
    return <SurfaceSummary node={node} onExpand={() => setExpanded(true)} />;
  }

  // ─── 第二级 / 第三级: 完整树状推理链 ──────────────────
  return (
    <div
      className={`reasoning-node ${node.kind} ${
        node.disputed ? "disputed" : ""
      } ${expanded ? "expanded" : "collapsed"}`}
      data-node-id={node.id}
    >
      {/* 节点头部 */}
      <div
        className="node-header"
        onClick={handleToggle}
        onMouseEnter={() => setPopoverVisible(true)}
        onMouseLeave={() => setPopoverVisible(false)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && handleToggle()}
        aria-expanded={expanded}
      >
        {/* 展开/折叠指示器 */}
        {node.children.length > 0 && (
          <span className="expand-indicator">{expanded ? "▾" : "▸"}</span>
        )}

        {/* 置信度色标 */}
        {node.confidence !== undefined && (
          <ConfidenceBadge value={node.confidence} />
        )}

        {/* 节点类型图标 */}
        <NodeIcon kind={node.kind} />

        {/* 节点标签 */}
        <span className="node-label">{node.label}</span>

        {/* 争议闪烁点 */}
        {node.disputed && (
          <span className="dispute-sparkle" title="此节点存在Agent对抗">
            ✦
          </span>
        )}

        {/* 证据溯源链接 */}
        {node.source && (
          <EvidenceLink
            source={node.source}
            onJump={handleFileJump}
          />
        )}
      </div>

      {/* 弹出式预览 (空格键 / hover Quick Look) */}
      {popoverVisible && !expanded && node.detail && (
        <div className="node-popover vibrancy">
          <p>{node.detail.slice(0, 200)}{node.detail.length > 200 ? "..." : ""}</p>
        </div>
      )}

      {/* 展开后的内容 */}
      {expanded && (
        <div className="node-body">
          {/* 详细描述 */}
          {node.detail && (
            <div className="node-detail">
              {node.detail.split("\n").map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          )}

          {/* 异议面板 */}
          {node.kind === "dissent" && node.disputed && (
            <DissentPanel node={node} />
          )}

          {/* 子节点 */}
          {node.children.length > 0 && (
            <div className="node-children">
              {node.children.map((child) => (
                <ReasoningTree
                  key={child.id}
                  node={child}
                  disclosureLevel={disclosureLevel}
                  onNodeClick={onNodeClick}
                  onFileJump={onFileJump}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <style>{`
        .reasoning-node {
          margin-left: 0;
          border-left: 2px solid var(--color-border, #e5e5e5);
          padding-left: 12px;
          transition: border-color 0.2s;
        }
        .reasoning-node.disputed {
          border-left-color: var(--color-disputed, #AF52DE);
        }
        .reasoning-node.conclusion {
          border-left: none;
          padding-left: 0;
        }

        .node-header {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 8px;
          border-radius: 6px;
          cursor: pointer;
          user-select: none;
          transition: background 0.15s;
        }
        .node-header:hover {
          background: var(--color-hover, rgba(0,0,0,0.04));
        }
        .node-header:focus-visible {
          outline: 2px solid var(--color-focus, #007AFF);
          outline-offset: 2px;
        }

        .node-header.dissent {
          background: rgba(175, 82, 222, 0.06);
        }

        .expand-indicator {
          width: 14px;
          font-size: 10px;
          color: var(--color-secondary, #8E8E93);
          flex-shrink: 0;
        }

        .node-label {
          font-size: 13px;
          font-weight: 500;
          color: var(--color-text, #3C3C43);
          flex: 1;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .dispute-sparkle {
          font-size: 12px;
          color: #AF52DE;
          animation: sparkle-pulse 2s infinite;
          flex-shrink: 0;
        }

        @keyframes sparkle-pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }

        .node-popover {
          position: absolute;
          z-index: 100;
          max-width: 360px;
          padding: 12px;
          margin: 4px 0;
          border-radius: 8px;
          background: rgba(255,255,255,0.92);
          backdrop-filter: blur(20px);
          box-shadow: 0 4px 24px rgba(0,0,0,0.12);
          font-size: 12px;
          line-height: 1.5;
          color: var(--color-text, #3C3C43);
        }

        .node-body {
          padding: 4px 0 8px 20px;
        }

        .node-detail {
          font-size: 12px;
          color: var(--color-secondary, #8E8E93);
          line-height: 1.6;
          margin-bottom: 8px;
        }
        .node-detail p {
          margin: 2px 0;
        }

        .node-children {
          border-left: 1px solid var(--color-border-light, #f0f0f0);
          padding-left: 8px;
        }
      `}</style>
    </div>
  );
};

// ─── Surface Summary (第一级) ──────────────────────────

const SurfaceSummary: React.FC<{
  node: ReasoningNodeData;
  onExpand: () => void;
}> = ({ node, onExpand }) => {
  // 统计子项
  const blockers = node.children.filter(
    (c) => c.kind === "evidence" && (c.confidence ?? 0) >= 0.85
  ).length;
  const warnings = node.children.filter(
    (c) => c.kind === "evidence" && (c.confidence ?? 0) >= 0.6 && (c.confidence ?? 0) < 0.85
  ).length;
  const passes = node.children.length - blockers - warnings;

  return (
    <div className="surface-summary" onClick={onExpand} role="button" tabIndex={0}>
      <div className="summary-stats">
        {blockers > 0 && (
          <span className="stat-blocker">🔴 Block: {blockers}</span>
        )}
        {warnings > 0 && (
          <span className="stat-warning">🟡 Warn: {warnings}</span>
        )}
        <span className="stat-pass">🟢 Pass: {passes}</span>
      </div>
      {node.disputed && (
        <span className="dispute-sparkle" title="存在争议节点">
          ✦ 争议 ×{node.children.filter((c) => c.disputed).length}
        </span>
      )}
      <span className="expand-hint">⏎ 展开详情</span>

      <style>{`
        .surface-summary {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 12px;
          border-radius: 8px;
          background: var(--color-surface, #f5f5f7);
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
          transition: background 0.15s;
        }
        .surface-summary:hover {
          background: var(--color-hover, rgba(0,0,0,0.06));
        }
        .stat-blocker { color: #FF3B30; }
        .stat-warning { color: #FF9500; }
        .stat-pass { color: #34C759; }
        .expand-hint {
          margin-left: auto;
          font-size: 11px;
          color: #8E8E93;
        }
      `}</style>
    </div>
  );
};

// ─── Node Icon ─────────────────────────────────────────

const NodeIcon: React.FC<{ kind: string }> = ({ kind }) => {
  const icons: Record<string, string> = {
    conclusion: "⚖",
    fact: "📋",
    evidence: "🔬",
    rule: "📐",
    dissent: "⚡",
  };

  return (
    <span className="node-icon" title={kind}>
      {icons[kind] ?? "•"}
      <style>{`
        .node-icon {
          font-size: 14px;
          flex-shrink: 0;
        }
      `}</style>
    </span>
  );
};

export default ReasoningTree;
