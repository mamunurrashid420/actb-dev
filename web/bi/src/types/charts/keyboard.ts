export type KeyboardModifier = "ctrl" | "shift" | "alt" | "meta";

export type ShortcutCategory = "navigation" | "chart" | "ai" | "data";

export interface KeyboardShortcut {
  key: string;
  modifiers?: KeyboardModifier[];
  action: string;
  description: string;
  hint?: string;
  category: ShortcutCategory;
}

// Re-export from shared - SSOT is @actbi/shared
export type { KeyboardShortcutMap } from "@actbi/shared";

export const CHART_SHORTCUTS: KeyboardShortcut[] = [
  // Navigation
  {
    key: "Escape",
    action: "closePanel",
    description: "Close interaction panel",
    category: "navigation",
  },
  {
    key: "Tab",
    action: "nextChart",
    description: "Navigate to next chart",
    category: "navigation",
  },
  {
    key: "Tab",
    modifiers: ["shift"],
    action: "prevChart",
    description: "Navigate to previous chart",
    category: "navigation",
  },
  {
    key: "?",
    action: "showShortcuts",
    description: "Show keyboard shortcuts",
    category: "navigation",
  },

  // Chart Interactions
  {
    key: "c",
    action: "toggleChartType",
    description: "Cycle chart type",
    category: "chart",
  },
  {
    key: "d",
    action: "downloadChart",
    description: "Download as image",
    category: "chart",
  },
  {
    key: "f",
    action: "fullscreen",
    description: "Toggle fullscreen",
    category: "chart",
  },
  {
    key: "r",
    action: "resetChart",
    description: "Reset to default view",
    category: "chart",
  },

  // AI Interactions
  {
    key: "a",
    modifiers: ["ctrl"],
    action: "aiAnalyze",
    description: "AI analyze selection",
    category: "ai",
  },
  {
    key: "e",
    modifiers: ["ctrl"],
    action: "aiExplain",
    description: "AI explain chart",
    category: "ai",
  },
  {
    key: "q",
    modifiers: ["ctrl"],
    action: "aiQuestion",
    description: "Ask AI a question",
    category: "ai",
  },

  // Data Manipulation
  {
    key: "s",
    modifiers: ["ctrl"],
    action: "saveChart",
    description: "Save chart configuration",
    category: "data",
  },
  {
    key: "z",
    modifiers: ["ctrl"],
    action: "undo",
    description: "Undo last change",
    category: "data",
  },
  {
    key: "y",
    modifiers: ["ctrl"],
    action: "redo",
    description: "Redo last change",
    category: "data",
  },

  // Selection
  {
    key: "ArrowLeft",
    action: "selectPrev",
    description: "Select previous data point",
    category: "navigation",
  },
  {
    key: "ArrowRight",
    action: "selectNext",
    description: "Select next data point",
    category: "navigation",
  },
  {
    key: "ArrowUp",
    action: "selectFirst",
    description: "Select first data point",
    category: "navigation",
  },
  {
    key: "ArrowDown",
    action: "selectLast",
    description: "Select last data point",
    category: "navigation",
  },
  {
    key: "Enter",
    action: "activateSelection",
    description: "Show details of selected",
    category: "navigation",
  },
];
