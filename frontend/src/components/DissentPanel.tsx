/**
 * DissentPanel — 异议面板
 *
 * 借鉴天府Agent 的争议标注
 * 展示反方Agent 的论点、异议强度和需要补充的验证事项
 */

import React, { useState } from "react";
import type { ReasoningNodeData, CounterArgument } from "../lib/types";

interface DissentPanelProps {
  node: ReasoningNodeData;
}

export const DissentPanel: React.FC<DissentPanelProps> = ({ node }) => {
  const [showDetails, setShowDetails] = useState(false);

  // 从 node.detail 解析 counterarguments
  const args = parseArguments(node.detail);

  return (
    <div className="dissent-panel">
      {/* 异议摘要 */}
      <div
        className="dissent-header"
        onClick={() => setShowDetails(!showDetails)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setShowDetails(!showDetails)}
      >
        <span className="dissent-icon">⚡</span>
        <span className="dissent-title">
          异议Agent 已提出 {args.length} 条反方论点
        </span>
        <span className="dissent-toggle">
          {showDetails ? "▾" : "▸"}
        </span>
      </div>

      {/* 异议详细内容 */}
      {showDetails && (
        <div className="dissent-body">
          {args.map((arg, i) => (
            <div key={i} className={`dissent-arg ${arg.severity ?? "weak"}`}>
              <div className="arg-header">
                <SeverityBadge severity={arg.severity} />
                <span className="arg-claim">{arg.claim}</span>
              </div>
              <p className="arg-reasoning">{arg.reasoning}</p>
            </div>
          ))}

          {/* 需要补充验证的事项 */}
          {node.detail.includes("需要补充验证") && (
            <div className="dissent-checks">
              <h4>需要补充验证:</h4>
              <ul>
                {extractRequiredChecks(node.detail).map((check, i) => (
                  <li key={i}>{check}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <style>{`
        .dissent-panel {
          margin: 8px 0;
          border: 1px solid rgba(175, 82, 222, 0.2);
          border-radius: 8px;
          background: rgba(175, 82, 222, 0.03);
          overflow: hidden;
        }

        .dissent-header {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
          color: #AF52DE;
          transition: background 0.15s;
        }
        .dissent-header:hover {
          background: rgba(175, 82, 222, 0.06);
        }

        .dissent-icon { font-size: 14px; }
        .dissent-title { flex: 1; }
        .dissent-toggle {
          font-size: 10px;
          opacity: 0.6;
        }

        .dissent-body {
          padding: 8px 12px 12px;
          border-top: 1px solid rgba(175, 82, 222, 0.1);
        }

        .dissent-arg {
          margin-bottom: 8px;
          padding: 8px;
          border-radius: 6px;
          background: rgba(0,0,0,0.02);
        }
        .dissent-arg.fatal {
          border-left: 3px solid #FF3B30;
          background: rgba(255,59,48,0.04);
        }
        .dissent-arg.strong {
          border-left: 3px solid #FF9500;
          background: rgba(255,149,0,0.04);
        }
        .dissent-arg.weak {
          border-left: 3px solid #8E8E93;
        }

        .arg-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 4px;
        }
        .arg-claim {
          font-size: 12px;
          font-weight: 600;
          color: var(--color-text, #3C3C43);
        }
        .arg-reasoning {
          font-size: 11px;
          color: #8E8E93;
          line-height: 1.5;
          margin: 0;
        }

        .dissent-checks {
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid rgba(175, 82, 222, 0.1);
        }
        .dissent-checks h4 {
          font-size: 11px;
          font-weight: 600;
          color: #8E8E93;
          margin: 0 0 4px;
        }
        .dissent-checks ul {
          margin: 0;
          padding-left: 16px;
          font-size: 11px;
          color: #8E8E93;
        }
        .dissent-checks li {
          margin-bottom: 2px;
        }
      `}</style>
    </div>
  );
};

// ─── Severity Badge ────────────────────────────────────

const SeverityBadge: React.FC<{ severity?: string }> = ({ severity }) => {
  const labels: Record<string, { text: string; color: string }> = {
    fatal: { text: "致命", color: "#FF3B30" },
    strong: { text: "重大", color: "#FF9500" },
    weak: { text: "轻微", color: "#8E8E93" },
  };

  const info = labels[severity ?? "weak"] ?? labels.weak;

  return (
    <span className="severity-badge" style={{ color: info.color, borderColor: info.color }}>
      {info.text}
      <style>{`
        .severity-badge {
          font-size: 10px;
          font-weight: 600;
          padding: 0 4px;
          border: 1px solid;
          border-radius: 3px;
          text-transform: uppercase;
        }
      `}</style>
    </span>
  );
};

// ─── Helpers ───────────────────────────────────────────

interface ParsedArg {
  claim: string;
  reasoning: string;
  severity?: string;
}

function parseArguments(detail: string): ParsedArg[] {
  const args: ParsedArg[] = [];

  // 尝试解析 "• claim: reasoning" 格式
  const lines = detail.split("\n");
  for (const line of lines) {
    const match = line.match(/^[•-]\s*(.+?):\s*(.+)$/);
    if (match) {
      args.push({
        claim: match[1].trim(),
        reasoning: match[2].trim(),
        severity: "weak",
      });
    }
  }

  return args;
}

function extractRequiredChecks(detail: string): string[] {
  const checks: string[] = [];
  const inChecksSection = false;

  for (const line of detail.split("\n")) {
    const match = line.match(/^[•-]\s*(.+)$/);
    if (match && line.includes("验证")) {
      checks.push(match[1].trim());
    }
  }

  return checks.length > 0 ? checks : ["请查看完整推理链获取验证事项"];
}

export default DissentPanel;
