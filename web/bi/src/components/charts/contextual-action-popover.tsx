"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

import { Loader2, Send, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ChartDataPoint } from "@/types/charts/interactions";

interface ContextualActionPopoverProps {
  open: boolean;
  position: { x: number; y: number } | null;
  selectedData: ChartDataPoint | null;
  selectedIndex: number | null;
  onSubmitPrompt: (
    prompt: string,
    metadata?: { source: "action" | "custom"; suggestionId?: string },
  ) => Promise<void>;
  onClose: () => void;
  chartBounds?: DOMRect;
  isAnalyzing?: boolean;
  onFocusChange?: (focused: boolean) => void;
}

interface ActionDescriptor {
  id: "explain" | "compare" | "trend" | "forecast";
  label: string;
  description: string;
  shortcut: string;
  buildPrompt: (data: ChartDataPoint, index: number | null) => string;
}

const ACTIONS: ActionDescriptor[] = [
  {
    id: "explain",
    label: "Explain data point",
    description: "Why this value matters",
    shortcut: "E",
    buildPrompt: (data) =>
      `Explain the significance of ${data.label ?? data.name ?? "this data point"} with a value of ${data.value}.`,
  },
  {
    id: "compare",
    label: "Compare to dataset",
    description: "How it ranks overall",
    shortcut: "C",
    buildPrompt: (data) =>
      `Compare ${data.label ?? data.name ?? "this data point"} (${data.value}) to the dataset average and highlight notable differences.`,
  },
  {
    id: "trend",
    label: "Trend context",
    description: "Movement before & after",
    shortcut: "T",
    buildPrompt: (data, index) =>
      `Describe the short-term trend around index ${index ?? 0}, focusing on ${data.label ?? "this data point"} (${data.value}).`,
  },
  {
    id: "forecast",
    label: "Forecast ahead",
    description: "Project what happens next",
    shortcut: "F",
    buildPrompt: (data) =>
      `Using the current trajectory, forecast the next three values after ${data.label ?? "this data point"} (${data.value}).`,
  },
];

export const ContextualActionPopover: React.FC<ContextualActionPopoverProps> = ({
  open,
  position,
  selectedData,
  selectedIndex,
  onSubmitPrompt,
  onClose,
  chartBounds,
  isAnalyzing = false,
  onFocusChange,
}) => {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [inputValue, setInputValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const runAction = useCallback(
    async (actionId: ActionDescriptor["id"]) => {
      if (!selectedData || isAnalyzing || isSubmitting) return;
      const action = ACTIONS.find((item) => item.id === actionId);
      if (!action) return;

      const basePrompt = action.buildPrompt(selectedData, selectedIndex);
      const customContext = inputValue.trim();
      const finalPrompt = customContext
        ? `${basePrompt}\n\nAdditional user input: ${customContext}`
        : basePrompt;

      setIsSubmitting(true);
      try {
        await onSubmitPrompt(finalPrompt, { source: "action", suggestionId: actionId });
        setInputValue("");
      } finally {
        setIsSubmitting(false);
      }
    },
    [
      inputValue,
      isAnalyzing,
      isSubmitting,
      onSubmitPrompt,
      selectedData,
      selectedIndex,
    ],
  );

  const submitCustomPrompt = useCallback(async () => {
    const prompt = inputValue.trim();
    if (!prompt || isAnalyzing || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmitPrompt(prompt, { source: "custom" });
      setInputValue("");
    } finally {
      setIsSubmitting(false);
    }
  }, [inputValue, isAnalyzing, isSubmitting, onSubmitPrompt]);

  const getPopoverStyle = (): React.CSSProperties => {
    if (!position) {
      return { opacity: 0, pointerEvents: "none" };
    }

    const POPOVER_WIDTH = 320;
    const POPOVER_HEIGHT = 300;
    const OFFSET = 16;
    const viewportWidth = typeof window !== "undefined" ? window.innerWidth : 0;
    const viewportHeight = typeof window !== "undefined" ? window.innerHeight : 0;
    const margin = 8;

    let x = position.x - POPOVER_WIDTH / 2;
    if (chartBounds) {
      if (x < chartBounds.left + margin) x = chartBounds.left + margin;
      if (x + POPOVER_WIDTH > chartBounds.right - margin) {
        x = chartBounds.right - POPOVER_WIDTH - margin;
      }
    } else if (viewportWidth) {
      const maxX = viewportWidth - POPOVER_WIDTH - margin;
      if (x < margin) x = margin;
      if (x > maxX) x = maxX;
    }

    let y = position.y - POPOVER_HEIGHT - OFFSET;
    const hasSpaceAbove = chartBounds
      ? y >= chartBounds.top + margin
      : viewportHeight
        ? y >= margin
        : true;

    if (!hasSpaceAbove) {
      y = position.y + OFFSET;
    }

    if (chartBounds) {
      if (y < chartBounds.top + margin) y = chartBounds.top + margin;
      if (y + POPOVER_HEIGHT > chartBounds.bottom - margin) {
        y = chartBounds.bottom - POPOVER_HEIGHT - margin;
      }
    } else if (viewportHeight) {
      const maxY = viewportHeight - POPOVER_HEIGHT - margin;
      if (y < margin) y = margin;
      if (y > maxY) y = maxY;
    }

    return {
      position: "fixed",
      left: `${x}px`,
      top: `${y}px`,
      zIndex: 50,
    };
  };

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        void submitCustomPrompt();
        return;
      }

      const key = event.key.toLowerCase();
      const hotKeyMap: Record<string, ActionDescriptor["id"]> = {
        e: "explain",
        c: "compare",
        t: "trend",
        f: "forecast",
      };

      if (!event.metaKey && !event.ctrlKey && hotKeyMap[key]) {
        event.preventDefault();
        void runAction(hotKeyMap[key]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose, runAction, submitCustomPrompt]);

  useEffect(() => {
    if (!open) {
      setInputValue("");
    }
  }, [open]);

  useEffect(() => {
    if (!selectedData) {
      setInputValue("");
    }
  }, [selectedData]);

  const handleInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(event.target.value);
  };

  const handleFocus = (focused: boolean) => {
    if (onFocusChange) {
      onFocusChange(focused);
    }
  };

  if (!open || !position || !selectedData) {
    return null;
  }

  return (
    <div
      ref={popoverRef}
      style={getPopoverStyle()}
      className="animate-in fade-in-0 zoom-in-95 slide-in-from-bottom-2 duration-200"
      role="dialog"
      aria-modal="false"
      aria-label="Ask AI about this data point"
    >
      <Card className="w-80 border shadow-xl">
        <div className="space-y-4 p-4">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-muted-foreground text-xs uppercase">
                Selected data point
              </p>
              <p className="text-sm font-semibold leading-tight">
                {selectedData.label ?? selectedData.name ?? "Value"}
              </p>
              <p className="text-muted-foreground text-sm">
                Value <span className="font-medium">{selectedData.value}</span>
                {typeof selectedIndex === "number" && (
                  <>
                    {" "}
                    · Index <span className="font-medium">{selectedIndex}</span>
                  </>
                )}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={onClose}
              aria-label="Close popover"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="space-y-2">
            <p className="text-muted-foreground text-xs font-medium uppercase">
              Actions
            </p>
            <TooltipProvider delayDuration={100}>
              <div className="flex flex-wrap gap-1.5">
                {ACTIONS.map((action) => (
                  <Tooltip key={action.id}>
                    <TooltipTrigger asChild>
                      <Button
                        variant="secondary"
                        size="sm"
                        className="h-7 rounded-full px-2.5 text-[11px] font-medium"
                        disabled={isAnalyzing || isSubmitting}
                        onClick={() => void runAction(action.id)}
                      >
                        <span className="flex flex-wrap items-center gap-1">
                          <span>{action.label}</span>
                          <kbd className="border-border bg-background rounded border px-1 text-[9px] font-semibold">
                            {action.shortcut}
                          </kbd>
                        </span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top">{action.description}</TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </TooltipProvider>
          </div>

          <div className="space-y-2">
            <label className="text-muted-foreground text-xs font-medium">
              Optional input
            </label>
            <Textarea
              value={inputValue}
              onChange={handleInputChange}
              placeholder="Ask anything else about this point..."
              className="min-h-[70px] text-sm"
              onFocus={() => handleFocus(true)}
              onBlur={() => handleFocus(false)}
            />
          </div>

          <Button
            onClick={() => void submitCustomPrompt()}
            disabled={!inputValue.trim() || isSubmitting || isAnalyzing}
            className="w-full"
            onFocus={() => handleFocus(true)}
            onBlur={() => handleFocus(false)}
          >
            {isSubmitting || isAnalyzing ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Sending
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Send className="h-4 w-4" />
                Send to AI
              </span>
            )}
          </Button>
        </div>

        <div
          className="bg-popover absolute -bottom-2 left-1/2 h-4 w-4 -translate-x-1/2 rotate-45 border-b border-r"
          aria-hidden="true"
        />
      </Card>
    </div>
  );
};
