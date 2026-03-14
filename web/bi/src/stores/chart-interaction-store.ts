import { create } from "zustand";

import type {
  ChartAnalysisResponse,
  ChartDataPoint,
  ChartInteractionEvent,
} from "@/types/charts/interactions";

interface ChartInteractionState {
  selectedIndex: number | null;
  selectedData: ChartDataPoint | null;
  aiPanelOpen: boolean;
  interactionEvent: ChartInteractionEvent | null;
  chartType:
    | "bar_chart_vertical"
    | "line_chart"
    | "area_chart"
    | "pie_chart"
    | "donut_chart";
  isAnalyzing: boolean;
  analysisResult: ChartAnalysisResponse | null;
  suggestions: string[];
  shortcutsOverlayOpen: boolean;

  // Popover state
  clickPosition: { x: number; y: number } | null;
  popoverOpen: boolean;
  activePopoverAction: string | null;

  // Actions
  setSelectedIndex: (index: number | null) => void;
  setSelectedData: (data: ChartDataPoint | null) => void;
  setAiPanelOpen: (open: boolean) => void;
  setInteractionEvent: (event: ChartInteractionEvent | null) => void;
  setChartType: (
    type:
      | "bar_chart_vertical"
      | "line_chart"
      | "area_chart"
      | "pie_chart"
      | "donut_chart",
  ) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  setAnalysisResult: (result: ChartAnalysisResponse | null) => void;
  setSuggestions: (suggestions: string[]) => void;
  setShortcutsOverlayOpen: (open: boolean) => void;

  // Popover actions
  setClickPosition: (position: { x: number; y: number } | null) => void;
  setPopoverOpen: (open: boolean) => void;
  setActivePopoverAction: (action: string | null) => void;

  reset: () => void;
}

export const useChartInteractionStore = create<ChartInteractionState>((set) => ({
  selectedIndex: null,
  selectedData: null,
  aiPanelOpen: false,
  interactionEvent: null,
  chartType: "bar_chart_vertical",
  isAnalyzing: false,
  analysisResult: null,
  suggestions: [],
  shortcutsOverlayOpen: false,
  clickPosition: null,
  popoverOpen: false,
  activePopoverAction: null,

  setSelectedIndex: (index) => set({ selectedIndex: index }),
  setSelectedData: (data) => set({ selectedData: data }),
  setAiPanelOpen: (open) => set({ aiPanelOpen: open }),
  setInteractionEvent: (event) => set({ interactionEvent: event }),
  setChartType: (type) => set({ chartType: type }),
  setIsAnalyzing: (analyzing) => set({ isAnalyzing: analyzing }),
  setAnalysisResult: (result) => set({ analysisResult: result }),
  setSuggestions: (suggestions) => set({ suggestions }),
  setShortcutsOverlayOpen: (open) => set({ shortcutsOverlayOpen: open }),
  setClickPosition: (position) => set({ clickPosition: position }),
  setPopoverOpen: (open) => set({ popoverOpen: open }),
  setActivePopoverAction: (action) => set({ activePopoverAction: action }),
  reset: () =>
    set({
      selectedIndex: null,
      selectedData: null,
      aiPanelOpen: false,
      interactionEvent: null,
      isAnalyzing: false,
      analysisResult: null,
      suggestions: [],
      clickPosition: null,
      popoverOpen: false,
      activePopoverAction: null,
    }),
}));
