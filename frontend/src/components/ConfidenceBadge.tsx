/**
 * ConfidenceBadge — 置信度标识
 *
 * 借鉴天府Agent 的 GPRO 概率可视化:
 * - 高置信 (≥0.85): 绿色实心 ● → 可阻断
 * - 中置信 (0.60-0.84): 黄色半满 ◐ → 需人工复核
 * - 低置信 (<0.60): 红色轮廓 ○ → 仅作参考
 */

import React from "react";

interface ConfidenceBadgeProps {
  value: number;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  value,
  showLabel = true,
  size = "sm",
}) => {
  const level = getLevel(value);
  const color = getColor(level);
  const icon = getIcon(level);
  const label = showLabel ? `${Math.round(value * 100)}%` : "";
  const tooltip = getTooltip(value, level);

  const sizeClass = `badge-${size}`;

  return (
    <span
      className={`confidence-badge ${level} ${sizeClass}`}
      title={tooltip}
      role="img"
      aria-label={`置信度: ${Math.round(value * 100)}%`}
    >
      <span className="badge-icon" style={{ color }}>
        {icon}
      </span>
      {label && <span className="badge-label">{label}</span>}

      <style>{`
        .confidence-badge {
          display: inline-flex;
          align-items: center;
          gap: 2px;
          flex-shrink: 0;
          font-variant-numeric: tabular-nums;
        }

        .badge-sm .badge-icon { font-size: 10px; }
        .badge-sm .badge-label { font-size: 10px; }
        .badge-md .badge-icon { font-size: 14px; }
        .badge-md .badge-label { font-size: 12px; }
        .badge-lg .badge-icon { font-size: 18px; }
        .badge-lg .badge-label { font-size: 14px; font-weight: 600; }

        .badge-label {
          color: var(--color-text, #3C3C43);
          font-weight: 500;
        }

        .confidence-badge.high .badge-icon { color: #34C759; }
        .confidence-badge.medium .badge-icon { color: #FF9500; }
        .confidence-badge.low .badge-icon { color: #FF3B30; }
      `}</style>
    </span>
  );
};

// ─── Helpers ───────────────────────────────────────────

type Level = "high" | "medium" | "low";

function getLevel(value: number): Level {
  if (value >= 0.85) return "high";
  if (value >= 0.60) return "medium";
  return "low";
}

function getColor(level: Level): string {
  switch (level) {
    case "high": return "#34C759";
    case "medium": return "#FF9500";
    case "low": return "#FF3B30";
  }
}

function getIcon(level: Level): string {
  switch (level) {
    case "high": return "●";   // 实心圆
    case "medium": return "◐";  // 半满圆
    case "low": return "○";    // 空心圆
  }
}

function getTooltip(value: number, level: Level): string {
  const pct = Math.round(value * 100);
  switch (level) {
    case "high":
      return `高置信度 ${pct}% — 该判断有充分的工具/规则/判例支撑，可自动执行`;
    case "medium":
      return `中等置信度 ${pct}% — 建议人工复核，可能存在合理分歧`;
    case "low":
      return `低置信度 ${pct}% — 仅供参考，不应作为阻断依据`;
  }
}

export default ConfidenceBadge;
