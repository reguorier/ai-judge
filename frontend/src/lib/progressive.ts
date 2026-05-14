/**
 * Progressive Disclosure Utilities
 *
 * 借鉴 Gemini 的「渐进式明示」方案:
 * - 第一级 Surface: 只展示结论摘要 + 状态图标
 * - 第二级 Popover: 空格键触发的毛玻璃浮窗
 * - 第三级 Full: 双击展开完整推理链 + Claim Ledger
 */

import type { DisclosureLevel, ReasoningNodeData } from "./types";

export const progressive = {
  /**
   * 根据 disclosure level 过滤节点
   */
  filterByLevel(
    nodes: ReasoningNodeData[],
    level: DisclosureLevel
  ): ReasoningNodeData[] {
    switch (level) {
      case 0:
        // Surface: 只保留结论节点
        return nodes.filter((n) => n.kind === "conclusion");
      case 1:
        // Popover: 展开到第二层 (结论 → 一级子节点)
        return nodes.map((n) => ({
          ...n,
          children: n.kind === "conclusion"
            ? n.children.map((c) => ({ ...c, children: [] }))
            : [],
        }));
      case 2:
        // Full: 全部展开
        return nodes;
    }
  },

  /**
   * 获取节点应该展开到哪一级
   * 默认 collapsed 的节点即使在 Full 模式下也折叠
   */
  shouldExpand(node: ReasoningNodeData, level: DisclosureLevel): boolean {
    if (level === 0) return false;
    if (level === 1) return node.kind === "conclusion" || !node.collapsedByDefault;
    if (level === 2) return !node.collapsedByDefault;
    return false;
  },

  /**
   * 键盘快捷键映射
   */
  keybindings: {
    TOGGLE_POPOVER: "Space",
    EXPAND_FULL: "Enter",
    COLLAPSE_ALL: "Escape",
    NEXT_NODE: "j",
    PREV_NODE: "k",
  },
};

/**
 * macOS 原生低饱和色彩系统
 * 借鉴 Gemini 的「内卷而外简」原则:
 * - 默认: 黑/白/灰 + macOS 低饱和蓝
 * - 例外1: 极高置信度 + 高破坏性 → 系统红
 * - 例外2: Agent 间无法调和的死锁 → 蓝紫渐变
 */
export const colorSystem = {
  // 语义色
  blocker: "#FF3B30",      // macOS 系统红 — 必须修复
  warning: "#FF9500",      // macOS 系统橙 — 强烈建议
  caution: "#FFCC00",      // macOS 系统黄 — 需人工复核
  neutral: "#8E8E93",      // macOS 系统灰 — 仅供参考
  pass: "#34C759",         // macOS 系统绿 — 通过

  // 特殊色
  disputed: "#AF52DE",     // 蓝紫 — 节点存在对抗
  disputedGradient: "linear-gradient(135deg, #5856D6, #AF52DE)",

  // 交互色
  link: "#007AFF",         // macOS 系统蓝 — 可点击
  focus: "#007AFF",
  hover: "rgba(0,0,0,0.04)",

  // 文本色
  text: "#3C3C43",        // macOS 标签色
  textSecondary: "#8E8E93",
  textTertiary: "#C6C6C8",

  // 背景色 (macOS Vibrancy)
  surface: "#F5F5F7",
  surfaceElevated: "rgba(255,255,255,0.92)",
  surfaceBlur: "blur(20px)",
};

/**
 * 置信度 → 颜色映射
 */
export function confidenceToColor(value: number): string {
  if (value >= 0.85) return colorSystem.pass;
  if (value >= 0.60) return colorSystem.caution;
  return colorSystem.blocker;
}

/**
 * 置信度 → 合并决策
 */
export function confidenceToMergeAction(
  confidence: number,
  severity: string
): "block" | "review" | "warn" | "suggest" {
  if (confidence >= 0.85 && severity === "blocker") return "block";
  if (confidence >= 0.85 && severity === "warning") return "warn";
  if (confidence >= 0.60 && severity === "blocker") return "review";
  if (confidence >= 0.60) return "warn";
  return "suggest";
}

/**
 * Tauri invoke 封装: 在本地 IDE 中打开文件
 */
export async function openInIDE(filePath: string, line?: number): Promise<void> {
  try {
    // 使用 Tauri 的 invoke API (需要在组件中 import)
    const { invoke } = await import("@tauri-apps/api/tauri");
    await invoke("open_in_editor", {
      filePath,
      line: line ?? 1,
    });
  } catch (err) {
    console.error("Failed to open file in IDE:", err);
    // 降级: 在系统默认编辑器中打开
    window.open(`file://${filePath}`, "_blank");
  }
}
