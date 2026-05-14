/**
 * EvidenceLink — 证据溯源链接
 *
 * 借鉴天府Agent 的「知识溯源」——每个结论标注古籍出处
 * AI Judge 版: 每个判断标注工具/规则/文件出处，点击跳转本地 IDE
 */

import React from "react";
import type { EvidenceSource } from "../lib/types";

interface EvidenceLinkProps {
  source: EvidenceSource;
  onJump?: (source: EvidenceSource) => void;
  compact?: boolean;
}

export const EvidenceLink: React.FC<EvidenceLinkProps> = ({
  source,
  onJump,
  compact = false,
}) => {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // 防止触发父节点展开/折叠
    onJump?.(source);
  };

  // 无文件路径 → 仅展示文本，不可点击
  if (!source.filePath) {
    return (
      <span className="evidence-link text-only">
        {source.ruleId && <span className="source-rule">{source.ruleId}</span>}
        {source.toolName && <span className="source-tool">[{source.toolName}]</span>}
        <style>{`
          .evidence-link.text-only {
            font-size: 11px;
            color: #8E8E93;
            display: inline-flex;
            gap: 4px;
          }
          .source-rule {
            background: rgba(0,122,255,0.08);
            color: #007AFF;
            padding: 1px 6px;
            border-radius: 4px;
            font-weight: 500;
          }
          .source-tool {
            color: #8E8E93;
          }
        `}</style>
      </span>
    );
  }

  // 文件路径 + 行号 → 可点击跳转
  const displayPath = compact
    ? source.filePath.split("/").pop() ?? source.filePath
    : source.filePath;

  const lineStr = source.line ? `:${source.line}` : "";

  return (
    <button
      className={`evidence-link clickable ${compact ? "compact" : ""}`}
      onClick={handleClick}
      title={`在 IDE 中打开: ${source.filePath}${lineStr}`}
    >
      <span className="link-icon">↗</span>
      <span className="link-path">{displayPath}{lineStr}</span>
      {source.ruleId && !compact && (
        <span className="link-rule">{source.ruleId}</span>
      )}
      {source.toolName && !compact && (
        <span className="link-tool">[{source.toolName}]</span>
      )}

      <style>{`
        .evidence-link.clickable {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 2px 6px;
          border: none;
          border-radius: 4px;
          background: transparent;
          cursor: pointer;
          font-family: "SF Mono", "Menlo", monospace;
          font-size: 11px;
          color: #007AFF;
          transition: background 0.15s;
          flex-shrink: 0;
          max-width: 220px;
          overflow: hidden;
        }
        .evidence-link.clickable:hover {
          background: rgba(0,122,255,0.08);
        }
        .evidence-link.clickable:focus-visible {
          outline: 2px solid #007AFF;
          outline-offset: 1px;
        }

        .evidence-link.compact {
          max-width: 140px;
        }

        .link-icon {
          font-size: 10px;
          flex-shrink: 0;
        }

        .link-path {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          min-width: 0;
        }

        .link-rule {
          background: rgba(0,122,255,0.06);
          padding: 0 4px;
          border-radius: 3px;
          font-size: 10px;
          white-space: nowrap;
        }

        .link-tool {
          color: #8E8E93;
          font-size: 10px;
          white-space: nowrap;
        }
      `}</style>
    </button>
  );
};

export default EvidenceLink;
