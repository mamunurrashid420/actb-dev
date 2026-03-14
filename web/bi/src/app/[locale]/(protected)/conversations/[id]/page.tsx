import { ArrowUp, Bird, Check, Lightbulb, MessageSquareText, MoreHorizontal, TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function ConversationDetailPage() {
  return (
    <div className="bg-muted/20 flex h-screen flex-col">
      <header className="bg-muted/20 sticky top-0 z-10 flex flex-wrap items-center justify-between gap-4 border-b px-6 py-4 backdrop-blur">
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
        <aside className="bg-background/80 flex h-full flex-col gap-4 overflow-hidden rounded-xl border p-4 shadow-sm">
          <div className="text-foreground text-sm font-semibold">actBI chat</div>

          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-1">
            <div className="space-y-4">
              <div className="flex justify-end">
                <div className="bg-muted text-foreground max-w-[220px] rounded-2xl px-4 py-2 text-xs shadow-sm">
                  Show me our revenue trends for Q4 2025 compared to Q3
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="bg-muted text-muted-foreground flex size-8 items-center justify-center rounded-full">
                  <Bird className="size-4" />
                </div>
                <div className="text-muted-foreground space-y-2 text-xs">
                  <p className="text-foreground text-sm">Here’s how coffee bean costs are trending over time.</p>
                  <p>I’ve pulled the last quarter of cost trends for review.</p>
                  <div>
                    <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">I created</p>
                    <ul className="text-muted-foreground mt-2 space-y-1 text-xs">
                      <li className="flex items-center gap-2">
                        <Check className="size-3" />
                        Revenue Trend: Q3 vs Q4 2025
                      </li>
                      <li className="flex items-center gap-2">
                        <Check className="size-3" />
                        Monthly Breakdown
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="bg-muted/40 text-foreground rounded-lg px-3 py-2 text-xs font-medium">
                V1 - Q4 vs Q3 Revenue Overview
              </div>
            </div>
          </div>

          <div className="mt-auto">
            <div className="bg-background relative rounded-xl border p-3 shadow-sm">
              <Textarea
                className="min-h-24 resize-none border-0 bg-transparent p-2 shadow-none focus-visible:ring-0"
                placeholder="Ask actBI"
              />
              <Button size="icon" className="absolute right-3 bottom-3 rounded-full">
                <ArrowUp className="size-4" />
              </Button>
            </div>
          </div>
        </aside>

        <section className="flex h-full flex-col gap-6 overflow-y-auto pr-1">
          <div>
            <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">Question 1</p>
            <h2 className="text-foreground text-base font-semibold">Q4 vs Q3 Revenue Overview</h2>
          </div>

          <div className="bg-background rounded-lg border p-4 shadow-sm">
            <p className="text-muted-foreground text-xs">YoY Bean Cost Change</p>
            <div className="text-foreground mt-2 flex items-center gap-2 text-lg font-semibold">
              <TrendingUp className="size-4 text-emerald-500" />
              14.0%
            </div>
          </div>

          <div className="bg-background rounded-lg border p-4 shadow-sm">
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
                  <li className="space-y-2">
                    <p>
                      Revenue increased by 23% in Q4 2025 compared to Q3, driven primarily by strong performance in
                      November and December.
                    </p>
                    <p className="text-muted-foreground text-[11px] font-semibold">Recommended action:</p>
                    <div className="flex flex-col gap-2">
                      <Button variant="outline" size="sm" className="justify-start">
                        Analyze monthly revenue drivers
                      </Button>
                      <Button variant="outline" size="sm" className="justify-start">
                        Compare to previous years
                      </Button>
                    </div>
                  </li>
                  <li className="space-y-2">
                    <p>
                      December performance exceeded expectations with $4.2M in revenue, setting a new monthly record.
                    </p>
                    <p className="text-muted-foreground text-[11px] font-semibold">Recommended action:</p>
                    <Button variant="outline" size="sm" className="justify-start">
                      Breakdown by channel
                    </Button>
                  </li>
                </ol>
              </div>
            </div>
          </div>

          <div className="bg-background rounded-lg border p-4 shadow-sm">
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
                  <li className="space-y-2">
                    <p>
                      December showed the highest single-month revenue at $4.2M, representing a 15% increase from the
                      previous peak in November.
                    </p>
                    <p className="text-muted-foreground text-[11px] font-semibold">Recommended action:</p>
                    <div className="flex flex-col gap-2">
                      <Button variant="outline" size="sm" className="justify-start">
                        Analyze seasonal patterns
                      </Button>
                      <Button variant="outline" size="sm" className="justify-start">
                        Forecast next quarter
                      </Button>
                    </div>
                  </li>
                </ol>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
