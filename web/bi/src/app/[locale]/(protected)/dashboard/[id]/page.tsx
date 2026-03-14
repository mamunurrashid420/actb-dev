import { notFound } from "next/navigation";

import {
  ChartLine,
  EllipsisVertical,
  Lightbulb,
  MessageSquareText,
  Pencil,
  Recycle,
  Scale,
  SearchCheck,
  Trash2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { requireUserAbilityContext } from "@/lib/permissions/require-user-ability";
import { cn } from "@/lib/utils";

type Props = {
  params: Promise<{ locale: string; id: string }>;
};

type TrendTone = "positive" | "negative";

type KpiCard = {
  title: string;
  value: string;
  trend: string;
  trendTone: TrendTone;
  insight: string;
  note: string;
};

type ChartInsight = {
  title: string;
  summary: string;
};

type Recommendation = {
  title: string;
  body: string;
  related: string[];
  icon: "search" | "recycle" | "scale";
};

type DashboardDetail = {
  title: string;
  updatedAt: string;
  status: "Unpublished";
  kpis: KpiCard[];
  growthInsights: ChartInsight[];
  driverInsights: ChartInsight[];
  recommendations: Recommendation[];
  keyTakeaway: string;
};

const DASHBOARD_DETAIL: DashboardDetail = {
  title: "Q4 2025 Revenue Analysis",
  updatedAt: "Last updated 3 minutes ago",
  status: "Unpublished",
  kpis: [
    {
      title: "Q4 Total Revenue",
      value: "$1,250.00",
      trend: "+12.5%",
      trendTone: "positive",
      insight: "Trending up this month",
      note: "Visitors for the last 6 months",
    },
    {
      title: "AVG Deal Size",
      value: "$ 42.3K",
      trend: "12% QoQ",
      trendTone: "negative",
      insight: "Down 20% this period",
      note: "Acquisition needs attention",
    },
    {
      title: "Growth Rate",
      value: "23.4%",
      trend: "+5.2pp QoQ",
      trendTone: "positive",
      insight: "Strong user retention",
      note: "Engagement exceed targets",
    },
    {
      title: "Customers",
      value: "280",
      trend: "+18% QoQ",
      trendTone: "positive",
      insight: "Steady performance increase",
      note: "Meets growth projections",
    },
  ],
  growthInsights: [
    {
      title: "Revenue Trend: Q3 vs Q4 2025",
      summary:
        "Growth accelerated sharply in November and peaked in December. The 23% QoQ increase was concentrated in the final two months of Q4, not evenly distributed.",
    },
    {
      title: "Monthly Breakdown",
      summary:
        "December revenue ($4.2M) exceeded November by 15%, confirming the acceleration pattern. October showed modest growth, establishing a clear upward trajectory.",
    },
  ],
  driverInsights: [
    {
      title: "Revenue by Channel",
      summary:
        "Direct sales (58% of revenue) remained the primary driver, but partner channels grew 31% QoQ, indicating diversification is working. The growth wasn't dependent on a single channel.",
    },
    {
      title: "Product Category Mix",
      summary:
        "Enterprise products led with 38% growth vs. 18% in SMB. The acceleration was primarily enterprise-driven, suggesting upmarket momentum.",
    },
  ],
  recommendations: [
    {
      title: "Investigate December acceleration",
      body:
        "December revenue ($4.2M) was 15% higher than November. Identify which products, channels, or campaigns drove this spike to replicate in Q1.",
      related: ["Revenue Trend", "Monthly breakdown"],
      icon: "search",
    },
    {
      title: "Sustain enterprise momentum",
      body:
        "Enterprise products grew 38% vs. 18% in SMB. Double down on upmarket strategy while ensuring SMB pipeline doesn't stagnate.",
      related: ["Product Category Mix"],
      icon: "recycle",
    },
    {
      title: "Scale partner channel strategy",
      body:
        "Partner channels grew 31% QoQ. With direct sales stable at 58%, expand partner enablement to diversify revenue sources.",
      related: ["Revenue by Channel"],
      icon: "scale",
    },
  ],
  keyTakeaway:
    "Q4 growth was real and significant, driven by enterprise demand and successful channel diversification. The concentration in November-December suggests seasonal factors or campaign timing worth investigating. Confidence: High — all metrics align and show consistent patterns.",
};

const DASHBOARD_DETAILS: Record<string, DashboardDetail> = {
  "top-cost-drivers-q4-published": DASHBOARD_DETAIL,
  "top-cost-drivers-q4-published-2": DASHBOARD_DETAIL,
};

const DASHBOARD_TABS = ["KPIs", "Insights", "Recommended actions", "Key takeaways"];
const CONTENT_WIDTH = "w-full px-4 sm:px-6 lg:px-8";

function TrendPill({ value, tone }: { value: string; tone: TrendTone }) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center gap-1 rounded-full px-2 text-[12px] leading-4 font-semibold text-[#1e1e1e]",
        tone === "positive" ? "bg-[#D6F1DF]" : "bg-[#FADCDD]",
      )}
    >
      {tone === "positive" ? (
        <TrendingUp className="size-3 text-[#2B9A66]" />
      ) : (
        <TrendingDown className="size-3 text-[#C13B53]" />
      )}
      {value}
    </span>
  );
}

function InsightIcon({ tone }: { tone: TrendTone }) {
  return tone === "positive" ? (
    <TrendingUp className="size-4 text-[#1e1e1e]" />
  ) : (
    <TrendingDown className="size-4 text-[#1e1e1e]" />
  );
}

function ChartPlaceholder() {
  const xLabels = ["Jan\n2023", "Jun", "Dec", "Jan\n2024", "Jun", "Dec", "Jan\n2025", "Jun", "Dec"];

  return (
    <div className="flex h-[331px] flex-col items-center justify-between">
      <div className="relative h-[300px] w-full border-b border-[#e5e5e5] border-l border-[#e5e5e5]">
        {[20, 35, 50, 65, 80].map((offset) => (
          <div key={offset} className="absolute right-0 left-0 border-t border-[#e5e5e5]" style={{ top: `${offset}%` }} />
        ))}
        <div className="absolute top-0 -left-5 flex h-full flex-col justify-between py-0.5 text-[10px] leading-none text-[#737373]">
          <span>5</span>
          <span>4</span>
          <span>3</span>
          <span>2</span>
          <span>1</span>
        </div>
        <p className="absolute top-1/2 -left-11 -translate-y-1/2 -rotate-90 text-[10px] leading-none text-[#737373]">
          USD per Pound
        </p>
        <div className="absolute right-0 bottom-0 left-0 flex items-end justify-between px-1 pt-1 text-[10px] leading-[1.2] text-[#737373]">
          {xLabels.map((label, index) => (
            <span key={`${label}-${index}`} className="text-center whitespace-pre-line">
              {label}
            </span>
          ))}
        </div>
      </div>
      <div className="flex h-[18px] items-start justify-center gap-6 text-[12px] leading-[1.5] text-[#737373]">
        <span className="inline-flex items-center gap-[7px]">
          <span className="h-[6px] w-5 bg-[#2B9A66]" />
          Q3
        </span>
        <span className="inline-flex items-center gap-[7px]">
          <span className="h-[6px] w-5 bg-[#8E4EC6]" />
          Q4
        </span>
      </div>
    </div>
  );
}

function RecommendationIcon({ icon }: { icon: Recommendation["icon"] }) {
  if (icon === "search") {
    return <SearchCheck className="size-6 text-[#6295BC]" />;
  }
  if (icon === "recycle") {
    return <Recycle className="size-6 text-[#6295BC]" />;
  }
  return <Scale className="size-6 text-[#6295BC]" />;
}

function InsightCard({ title, summary }: ChartInsight) {
  return (
    <article className="rounded-[4px] border border-[#e5e5e5] bg-white shadow-[0px_1px_3px_0px_rgba(0,0,0,0.1)]">
      <div className="flex items-center justify-between border-b border-[#e5e5e5] px-6 pt-3 pb-3">
        <h4 className="text-[16px] leading-[1.5] font-normal text-[#0a0a0a]">{title}</h4>
        <button
          type="button"
          className="inline-flex size-9 items-center justify-center rounded-[4px] bg-[#c8ddef] text-[#315784]"
          aria-label={`${title} insights`}
        >
          <Lightbulb className="size-4" />
        </button>
      </div>
      <div className="space-y-6 px-6 pt-4 pb-6">
        <ChartPlaceholder />
        <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">{summary}</p>
      </div>
    </article>
  );
}

export default async function DashboardDetailPage({ params }: Props) {
  await requireUserAbilityContext();
  const { id } = await params;
  const detail = DASHBOARD_DETAILS[id];

  if (!detail) {
    notFound();
  }

  return (
    <div className="flex min-h-full flex-col overflow-x-hidden bg-[#f0f7fd]">
      <header>
        <div className={CONTENT_WIDTH}>
          <div className="flex flex-wrap items-start justify-between gap-4 py-6">
            <div className="space-y-0.5">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-[22px] leading-[1.5] font-normal text-[#1e1e1e]">{detail.title}</h1>
                <Badge className="h-[22px] rounded-full bg-[#E6F4FE] px-2.5 text-[12px] leading-[1.5] font-normal text-[#0a0a0a] shadow-none hover:bg-[#E6F4FE]">
                  {detail.status}
                </Badge>
              </div>
              <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">{detail.updatedAt}</p>
            </div>

            <div className="flex items-center gap-2">
              <Button size="sm" className="h-9 px-4">
                Publish dashboard
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex size-9 items-center justify-center rounded-full text-[#1e1e1e] transition hover:bg-[#e6f0f8]"
                    aria-label="Dashboard actions"
                  >
                    <EllipsisVertical className="size-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[140px] rounded-[4px] p-0">
                  <DropdownMenuItem className="h-9 rounded-none px-3">
                    <Pencil className="size-4 text-[#1e1e1e]" />
                    Rename
                  </DropdownMenuItem>
                  <DropdownMenuItem variant="destructive" className="h-9 rounded-none px-3">
                    <Trash2 className="size-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        <div className="border-b border-[#d4d4d4]">
          <div className={CONTENT_WIDTH}>
            <div className="flex h-9 items-end overflow-x-auto">
              {DASHBOARD_TABS.map((tab, index) => (
                <button
                  key={tab}
                  type="button"
                  className={cn(
                    "-mb-px inline-flex h-9 items-center justify-center border-b px-4 py-2 text-[14px] leading-[1.5] font-medium whitespace-nowrap",
                    index === 0 ? "border-[#47779b] text-[rgba(30,30,30,0.95)]" : "border-[#d4d4d4] text-[rgba(30,30,30,0.95)]",
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      <section className={cn(CONTENT_WIDTH, "space-y-6 py-6")}>
        <div>
          <h2 className="text-[22px] leading-[1.5] font-medium text-[#1e1e1e]">KPI</h2>
          <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">Lorem ipsum</p>

          <div className="mt-6 grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr))]">
            {detail.kpis.map((item) => (
              <article
                key={item.title}
                className="min-h-[198px] rounded-[4px] border border-[#d4d4d4] bg-white py-6 shadow-[0px_1px_3px_0px_rgba(0,0,0,0.1)]"
              >
                <div className="space-y-1.5 px-6">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">{item.title}</p>
                    <TrendPill value={item.trend} tone={item.trendTone} />
                  </div>
                  <p className="text-[24px] leading-8 font-semibold text-[#0a0a0a]">{item.value}</p>
                </div>
                <div className="mt-6 space-y-1.5 px-6">
                  <p className="inline-flex items-center gap-1 text-[14px] leading-[1.5] font-medium text-[#0a0a0a]">
                    {item.insight}
                    <InsightIcon tone={item.trendTone} />
                  </p>
                  <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">{item.note}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-[22px] leading-[1.5] font-medium text-[#1e1e1e]">When did growth accelerate?</h3>
          <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">Timing analysis from the conversation</p>
          <div className="mt-3 grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr))]">
            {detail.growthInsights.map((item) => (
              <InsightCard key={item.title} title={item.title} summary={item.summary} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-[22px] leading-[1.5] font-medium text-[#1e1e1e]">What drove this performance?</h3>
          <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">Contributing factors identified in the conversation</p>
          <div className="mt-3 grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr))]">
            {detail.driverInsights.map((item) => (
              <InsightCard key={item.title} title={item.title} summary={item.summary} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-[22px] leading-[1.5] font-medium text-[#1e1e1e]">Recommended Actions</h3>
          <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">
            Prioritized next steps based on the conversation analysis
          </p>
          <div className="mt-3 grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))]">
            {detail.recommendations.map((item) => (
              <article
                key={item.title}
                className="min-h-[256px] rounded-[4px] border border-[#d4d4d4] bg-white py-6 shadow-[0px_1px_3px_0px_rgba(0,0,0,0.1)]"
              >
                <div className="px-6">
                  <RecommendationIcon icon={item.icon} />
                </div>
                <div className="mt-6 space-y-1.5 px-6">
                  <p className="inline-flex items-center gap-1 text-[18px] leading-[1.5] font-medium text-[#0a0a0a]">
                    {item.title}
                    <TrendingUp className="size-4 text-[#1e1e1e]" />
                  </p>
                  <p className="text-[14px] leading-[1.5] font-normal text-[#737373]">{item.body}</p>
                </div>
                <div className="mt-6 flex flex-wrap items-center gap-[6px] px-6">
                  <span className="text-[14px] leading-[1.5] font-normal text-[#737373]">Related:</span>
                  {item.related.map((tag) => (
                    <Badge
                      key={tag}
                      variant="outline"
                      className="h-[22px] rounded-full border-[#d4d4d4] px-2.5 py-0 text-[12px] leading-[1.5] font-normal text-[#1e1e1e]"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>

        <article className="rounded-[4px] bg-[#47779b] py-6 text-[rgba(255,255,255,0.95)] shadow-[0px_1px_3px_0px_rgba(0,0,0,0.1)]">
          <div className="space-y-2 px-6">
            <h3 className="text-[22px] leading-[1.5] font-medium">Key Takeaway</h3>
            <p className="text-[18px] leading-[1.5] font-normal">{detail.keyTakeaway}</p>
          </div>
          <div className="mt-6 border-t border-white/20 px-6 pt-6">
            <p className="flex items-center gap-2 text-[14px] leading-[1.5] font-normal text-[rgba(255,255,255,0.95)]">
              <MessageSquareText className="size-4" />
              Generated from 1 conversation on revenue analysis
            </p>
            <p className="mt-1.5 flex items-center gap-2 text-[14px] leading-[1.5] font-normal text-[rgba(255,255,255,0.95)]">
              <ChartLine className="size-4" />
              Analysis performed 2 minutes ago using Q4 2025 data
            </p>
          </div>
          <div className="mt-6 border-t border-white/20 px-6 pt-6">
            <p className="text-[14px] leading-[1.5] font-normal text-[rgba(255,255,255,0.95)]">
              This dashboard summarizes 5 charts and insights from your conversation. To update this analysis with new
              data, start a new conversation or regenerate from the original source.
            </p>
          </div>
        </article>
      </section>
    </div>
  );
}
