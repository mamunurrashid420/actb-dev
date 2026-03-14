"use client";

import React from "react";

import { Loader2, Send, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import type {
  ChartAnalysisResponse,
  ChartDataPoint,
} from "@/types/charts/interactions";

interface AIInteractionPanelProps {
  selectedData: ChartDataPoint | null;
  selectedIndex: number | null;
  analysisResult?: ChartAnalysisResponse;
  isAnalyzing?: boolean;
  onSubmitChat?: (message: string) => Promise<void>;
  onFocusChange?: (focused: boolean) => void;
}

export const AIInteractionPanel: React.FC<AIInteractionPanelProps> = ({
  selectedData,
  selectedIndex,
  analysisResult,
  isAnalyzing = false,
  onSubmitChat,
  onFocusChange,
}) => {
  const [chatInput, setChatInput] = React.useState("");

  const selectedLabel = selectedData?.label ?? selectedData?.name ?? "Data point";
  const isChatDisabled = !selectedData || isAnalyzing;

  const handleSubmit = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const message = chatInput.trim();
    if (!message || !onSubmitChat || !selectedData) {
      return;
    }
    await onSubmitChat(message);
    setChatInput("");
  };

  const handleFocusChange = (focused: boolean) => {
    if (onFocusChange) {
      onFocusChange(focused);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header - Fixed */}
      <div className="border-b border-neutral-200 px-6 py-4 dark:border-neutral-800">
        <h2 className="text-base font-semibold tracking-tight text-neutral-900 dark:text-neutral-100">
          Analytics Result
        </h2>
        <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">
          AI-powered insights from your chart interactions
        </p>
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
        <SelectedDataSummary
          selectedData={selectedData}
          selectedIndex={selectedIndex}
          label={selectedLabel}
        />
        <div className="min-h-[220px] rounded-lg border border-neutral-200 bg-neutral-50/50 p-4 dark:border-neutral-800 dark:bg-neutral-900/50">
          <AnalysisContent analysisResult={analysisResult} isAnalyzing={isAnalyzing} />
        </div>
      </div>

      {/* Input - Fixed at Bottom */}
      <div className="border-t border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
        <form onSubmit={handleSubmit} className="flex w-full items-end gap-2">
          <Textarea
            rows={2}
            value={chatInput}
            onChange={(event) => setChatInput(event.target.value)}
            placeholder={
              selectedData
                ? "Ask a follow-up about this data point..."
                : "Select a data point to ask questions."
            }
            disabled={isChatDisabled}
            onFocus={() => handleFocusChange(true)}
            onBlur={() => handleFocusChange(false)}
            className="resize-none text-sm"
          />
          <Button
            type="submit"
            disabled={isChatDisabled || !chatInput.trim()}
            className="shrink-0"
            onFocus={() => handleFocusChange(true)}
            onBlur={() => handleFocusChange(false)}
          >
            {isAnalyzing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
};

function SelectedDataSummary({
  selectedData,
  selectedIndex,
  label,
}: {
  selectedData: ChartDataPoint | null;
  selectedIndex: number | null;
  label: string;
}) {
  if (!selectedData) {
    return null;
  }

  return (
    <>
      <div className="bg-secondary/30 space-y-1 rounded-xl border p-3">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground text-xs uppercase">Selected</span>
          <Badge variant="secondary" className="text-[11px]">
            #{typeof selectedIndex === "number" ? selectedIndex : "-"}
          </Badge>
        </div>
        <p className="text-foreground text-sm font-medium">{label}</p>
        <p className="text-muted-foreground text-sm">
          Value{" "}
          <span className="text-foreground font-semibold">{selectedData.value}</span>
        </p>
      </div>
      <Separator />
    </>
  );
}

function AnalysisContent({
  analysisResult,
  isAnalyzing,
}: {
  analysisResult?: ChartAnalysisResponse;
  isAnalyzing: boolean;
}) {
  if (isAnalyzing) {
    return (
      <div className="text-muted-foreground flex h-full flex-col items-center justify-center gap-2 text-sm">
        <Loader2 className="h-5 w-5 animate-spin" />
        AI is thinking…
      </div>
    );
  }

  if (analysisResult) {
    const primaryText = analysisResult.analysis?.trim();
    const fallbackText = analysisResult.summary?.trim() ?? "";
    const content = primaryText && primaryText.length > 0 ? primaryText : fallbackText;

    return (
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="text-muted-foreground flex h-full flex-col items-center justify-center gap-2 text-sm">
      <Sparkles className="h-4 w-4" />
      Run any action from the chart popover to see insights here.
    </div>
  );
}
