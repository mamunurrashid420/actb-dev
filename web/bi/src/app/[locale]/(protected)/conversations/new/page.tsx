"use client";

import { useState, type KeyboardEvent } from "react";
import Link from "next/link";
import {
  ArrowUp,
  Bird,
  Check,
  ChevronLeft,
  ChevronRight,
  Lightbulb,
  MessageSquareText,
  MoreHorizontal,
  TrendingUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const AI_INSIGHTS = {
  question: "Q4 vs Q3 Revenue Overview",
  metricLabel: "YoY Bean Cost Change",
  metricValue: "14.0%",
  insights: [
    {
      text: "Revenue increased by 23% in Q4 2025 compared to Q3, driven primarily by strong performance in November and December.",
      actions: ["Analyze monthly revenue drivers", "Compare to previous years"],
    },
    {
      text: "December performance exceeded expectations with $4.2M in revenue, setting a new monthly record.",
      actions: ["Breakdown by channel"],
    },
  ],
  breakdownInsights: [
    {
      text: "December showed the highest single-month revenue at $4.2M, representing a 15% increase from the previous peak in November.",
      actions: ["Analyze seasonal patterns", "Forecast next quarter"],
    },
  ],
};

export default function NewConversationPage() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<string[]>([]);
  const [started, setStarted] = useState(false);

  const sendMessage = () => {
    const trimmed = draft.trim();
    if (!trimmed) return;
    setMessages((prev) => [...prev, trimmed]);
    setDraft("");
    if (!started) setStarted(true);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  if (!started) {
    return (
      <div className="bg-background flex h-screen flex-col">
        <header className="bg-background sticky top-0 z-10 flex items-center justify-between border-b border-sidebar-border px-6 py-4 backdrop-blur">
          <h1 className="text-foreground text-[22px] font-normal leading-[1.5]">New conversation</h1>
          <Button asChild variant="ghost" size="sm">
            <Link href="/conversations">Cancel</Link>
          </Button>
        </header>

        <main className="flex flex-1 flex-col items-center gap-10 overflow-y-auto px-6 pt-6 pb-12">
          <div className="flex max-w-xl flex-col items-center gap-3 text-center">
            <div className="bg-card flex size-16 items-center justify-center rounded-full shadow-sm">
              <Bird className="text-muted-foreground size-8" />
            </div>
            <div className="space-y-1">
              <h2 className="text-foreground text-[18px] font-medium leading-[1.5]">
                Ask anything about your business
              </h2>
              <p className="text-muted-foreground text-sm">
                See suggested insights you can generate — then ask your own question.
              </p>
            </div>
          </div>

          <div className="flex w-full max-w-4xl items-center justify-center gap-4">
            <Button variant="outline" size="icon" className="rounded-full bg-card border-border text-foreground opacity-50">
              <ChevronLeft className="size-4" />
            </Button>

            <div className="bg-card flex w-full max-w-xl items-center gap-4 rounded-xl border p-4 shadow-sm">
              <div className="bg-muted h-24 w-36 shrink-0 rounded-lg border" />
              <div className="space-y-2">
                <span className="bg-secondary text-secondary-foreground inline-flex items-center rounded-full px-2 py-0.5 text-xs font-normal">
                  Revenue
                </span>
                <p className="text-foreground text-base font-semibold">
                  Q4 revenue grew 23% QoQ, driven by enterprise products in Nov – Dec
                </p>
                <p className="text-muted-foreground text-sm">
                  “Show me our revenue trends for Q4 2025 compared to Q3”
                </p>
              </div>
            </div>

            <Button variant="outline" size="icon" className="rounded-full bg-card border-border text-foreground">
              <ChevronRight className="size-4" />
            </Button>
          </div>

          <div className="w-full max-w-2xl">
            <div className="bg-card relative rounded-xl border border-[color:var(--border-strong)] p-3 shadow-sm">
              <Textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleKeyDown}
                className="min-h-[110px] resize-none border-0 bg-transparent p-2 text-sm shadow-none focus-visible:ring-0"
                placeholder="Ask questions like examples above..."
              />
              <Button
                size="icon"
                className="absolute right-3 bottom-3 rounded-full bg-[#8ecfff] text-[#315784] hover:bg-[#8ecfff]/90"
                onClick={sendMessage}
                disabled={!draft.trim()}
              >
                <ArrowUp className="size-4" />
              </Button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="bg-background flex h-screen flex-col">
      <header className="bg-background sticky top-0 z-10 flex flex-wrap items-center justify-between gap-4 border-b border-sidebar-border px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="bg-muted text-muted-foreground flex size-9 items-center justify-center rounded-md">
            <MessageSquareText className="size-4" />
          </div>
          <h1 className="text-foreground text-lg font-semibold">Q4 2025 Revenue Analysis</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm">Create dashboard</Button>
          <Button variant="ghost" size="icon-sm">
            <MoreHorizontal className="size-4" />
          </Button>
        </div>
      </header>

      <div className="grid h-full flex-1 gap-6 overflow-hidden px-6 pt-6 pb-8 lg:grid-cols-[320px_1fr]">
        <aside className="bg-sidebar flex h-full flex-col gap-4 overflow-hidden rounded-[4px] px-6 pb-6 pt-4">
          <div className="text-foreground text-[18px] font-medium leading-[1.5]">actBI chat</div>

          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-1">
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div key={`${message}-${index}`} className="flex justify-end">
                  <div className="bg-[color:var(--background-user-chat)] text-foreground w-full max-w-[350px] rounded-[24px] px-3 py-3 text-sm">
                    {message}
                  </div>
                </div>
              ))}

              <div className="flex items-start gap-3">
                <div className="flex size-5 items-center justify-center">
                  <Bird className="text-primary size-[18px]" />
                </div>
                <div className="text-muted-foreground space-y-2 text-sm">
                  <p className="text-foreground">Here’s how coffee bean costs are trending over time.</p>
                  <p>I’ve pulled the last quarter of cost trends for review.</p>
                  <div>
                    <p className="text-foreground text-sm font-normal">I created:</p>
                    <ul className="text-foreground mt-2 space-y-1 text-sm">
                      <li className="flex items-center gap-2">
                        <Check className="size-4" />
                        Revenue Trend: Q3 vs Q4 2025
                      </li>
                      <li className="flex items-center gap-2">
                        <Check className="size-4" />
                        Monthly Breakdown
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="bg-[color:var(--background-version-chat)] text-secondary-foreground rounded-[4px] px-3 py-3 text-[12px] font-medium">
                V1 - Q4 vs Q3 Revenue Overview
              </div>
            </div>
          </div>

          <div className="mt-auto">
            <div className="bg-card relative rounded-[4px] border border-[color:var(--border-strong)] p-3">
              <Textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleKeyDown}
                className="min-h-[110px] resize-none border-0 bg-transparent p-2 text-sm shadow-none focus-visible:ring-0"
                placeholder="Ask actBI"
              />
              <Button
                size="icon"
                className="absolute right-3 bottom-3 rounded-full bg-[#8ecfff] text-[#315784] hover:bg-[#8ecfff]/90"
                onClick={sendMessage}
                disabled={!draft.trim()}
              >
                <ArrowUp className="size-4" />
              </Button>
            </div>
          </div>
        </aside>

        <section className="flex h-full flex-col gap-6 overflow-y-auto pr-1">
          <div>
            <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">Question 1</p>
            <h2 className="text-foreground text-base font-semibold">{AI_INSIGHTS.question}</h2>
          </div>

          <div className="bg-card rounded-lg border p-4 shadow-sm">
            <p className="text-muted-foreground text-xs">{AI_INSIGHTS.metricLabel}</p>
            <div className="text-foreground mt-2 flex items-center gap-2 text-lg font-semibold">
              <TrendingUp className="size-4 text-emerald-500" />
              {AI_INSIGHTS.metricValue}
            </div>
          </div>

          <div className="bg-card rounded-lg border p-4 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-foreground text-sm font-semibold">Revenue Trend: Q3 vs Q4 2025</p>
                <p className="text-muted-foreground text-xs">USD per pound</p>
              </div>
              <div className="bg-muted text-muted-foreground flex size-8 items-center justify-center rounded-md">
                <Lightbulb className="size-4" />
              </div>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_260px]">
              <div className="bg-muted/30 h-56 rounded-lg border" />
              <div className="bg-muted/10 text-muted-foreground rounded-lg border p-3 text-xs">
                <div className="text-muted-foreground flex items-center gap-2 text-[10px] font-semibold tracking-wide uppercase">
                  <Lightbulb className="size-3" />
                  Insights and recommendations
                </div>
                <ol className="text-foreground mt-3 space-y-3 text-xs">
                  {AI_INSIGHTS.insights.map((insight) => (
                    <li key={insight.text} className="space-y-2">
                      <p>{insight.text}</p>
                      <p className="text-muted-foreground text-[11px] font-semibold">Recommended action:</p>
                      <div className="flex flex-col gap-2">
                        {insight.actions.map((action) => (
                          <Button key={action} variant="outline" size="sm" className="justify-start">
                            {action}
                          </Button>
                        ))}
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>

          <div className="bg-card rounded-lg border p-4 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-foreground text-sm font-semibold">Monthly Breakdown</p>
                <p className="text-muted-foreground text-xs">USD per pound</p>
              </div>
              <div className="bg-muted text-muted-foreground flex size-8 items-center justify-center rounded-md">
                <Lightbulb className="size-4" />
              </div>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_260px]">
              <div className="bg-muted/30 h-56 rounded-lg border" />
              <div className="bg-muted/10 text-muted-foreground rounded-lg border p-3 text-xs">
                <div className="text-muted-foreground flex items-center gap-2 text-[10px] font-semibold tracking-wide uppercase">
                  <Lightbulb className="size-3" />
                  Insights and recommendations
                </div>
                <ol className="text-foreground mt-3 space-y-3 text-xs">
                  {AI_INSIGHTS.breakdownInsights.map((insight) => (
                    <li key={insight.text} className="space-y-2">
                      <p>{insight.text}</p>
                      <p className="text-muted-foreground text-[11px] font-semibold">Recommended action:</p>
                      <div className="flex flex-col gap-2">
                        {insight.actions.map((action) => (
                          <Button key={action} variant="outline" size="sm" className="justify-start">
                            {action}
                          </Button>
                        ))}
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
