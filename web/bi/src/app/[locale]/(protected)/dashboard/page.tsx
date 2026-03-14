import { requireUserAbilityContext } from "@/lib/permissions/require-user-ability";

import { ArrowUp, Plus, Users } from "lucide-react";

import { Link } from "@/i18n/routing";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{ tab?: string }>;
};

type DashboardStatus = "draft" | "published" | "shared";

type DashboardKpi = {
  label: string;
  value: string;
  trendLabel: string;
  trendDirection: "up" | "down";
};

type DashboardListItem = {
  id: string;
  title: string;
  description: string;
  status: DashboardStatus;
  kpis: DashboardKpi[];
  detailHref?: string;
  author?: string;
  collaborators?: string[];
  updatedLabel?: string;
  primaryAction?: { label: string; variant?: "default" | "outline" };
};

const TABS: Array<{ id: "all" | DashboardStatus; label: string }> = [
  { id: "all", label: "All" },
  { id: "draft", label: "Draft" },
  { id: "published", label: "Published" },
  { id: "shared", label: "Shared with me" },
];

const DASHBOARDS: DashboardListItem[] = [
  {
    id: "top-cost-drivers-q4-published",
    title: "A Top Cost Drivers in Q4",
    status: "published",
    description:
      "Revenue performance summary for Q$ 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    kpis: [
      { label: "YoY Bean Cost", value: "14.0%", trendLabel: "14.0%", trendDirection: "up" },
      { label: "Gross Margin", value: "2.3%", trendLabel: "2.3%", trendDirection: "up" },
      { label: "Net Revenue", value: "7.1%", trendLabel: "7.1%", trendDirection: "up" },
    ],
    detailHref: "/dashboard/top-cost-drivers-q4-published",
    collaborators: ["DC", "AB", "JF"],
    primaryAction: { label: "Update dashboard", variant: "default" },
  },
  {
    id: "top-cost-drivers-q4-draft",
    title: "A Top Cost Drivers in Q4",
    status: "draft",
    description:
      "Revenue performance summary for Q$ 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    kpis: [
      { label: "YoY Bean Cost", value: "14.0%", trendLabel: "14.0%", trendDirection: "up" },
      { label: "Gross Margin", value: "2.3%", trendLabel: "2.3%", trendDirection: "up" },
      { label: "Net Revenue", value: "7.1%", trendLabel: "7.1%", trendDirection: "up" },
    ],
    primaryAction: { label: "Create dashboard", variant: "default" },
    updatedLabel: "Unpublished",
  },
  {
    id: "top-cost-drivers-q4-shared",
    title: "A Top Cost Drivers in Q4",
    status: "shared",
    description:
      "Revenue performance summary for Q$ 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    kpis: [
      { label: "YoY Bean Cost", value: "14.0%", trendLabel: "14.0%", trendDirection: "up" },
      { label: "Gross Margin", value: "2.3%", trendLabel: "2.3%", trendDirection: "up" },
      { label: "Net Revenue", value: "7.1%", trendLabel: "7.1%", trendDirection: "up" },
    ],
    author: "Dan Chan",
  },
  {
    id: "top-cost-drivers-q4-shared-2",
    title: "A Top Cost Drivers in Q4",
    status: "shared",
    description:
      "Revenue performance summary for Q$ 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    kpis: [
      { label: "YoY Bean Cost", value: "14.0%", trendLabel: "14.0%", trendDirection: "up" },
      { label: "Gross Margin", value: "2.3%", trendLabel: "2.3%", trendDirection: "up" },
      { label: "Net Revenue", value: "7.1%", trendLabel: "7.1%", trendDirection: "up" },
    ],
    author: "Dan Chan",
  },
  {
    id: "top-cost-drivers-q4-published-2",
    title: "A Top Cost Drivers in Q4",
    status: "published",
    description:
      "Revenue performance summary for Q$ 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    kpis: [
      { label: "YoY Bean Cost", value: "14.0%", trendLabel: "14.0%", trendDirection: "up" },
      { label: "Gross Margin", value: "2.3%", trendLabel: "2.3%", trendDirection: "up" },
      { label: "Net Revenue", value: "7.1%", trendLabel: "7.1%", trendDirection: "up" },
    ],
    detailHref: "/dashboard/top-cost-drivers-q4-published-2",
    collaborators: ["DC", "AB"],
    updatedLabel: "Last published 2 days ago",
  },
];

function StatusPill({ status }: { status: DashboardStatus }) {
  const { label, className } = (() => {
    switch (status) {
      case "published":
        return {
          label: "Published",
          className:
            "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200",
        };
      case "draft":
        return {
          label: "Unpublished",
          className:
            "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-200",
        };
      case "shared":
        return {
          label: "Shared with me",
          className:
            "border-border bg-muted/40 text-muted-foreground dark:bg-muted/20",
        };
    }
  })();

  return (
    <Badge
      variant="outline"
      className={cn("rounded-full px-3 py-1 text-[12px] font-medium", className)}
    >
      {label}
    </Badge>
  );
}

function KpiMiniCard({ kpi }: { kpi: DashboardKpi }) {
  const isUp = kpi.trendDirection === "up";

  return (
    <div className="bg-background flex-1 rounded-lg border px-4 py-3">
      <p className="text-muted-foreground text-xs font-medium">{kpi.label}</p>
      <div className="mt-1 flex items-center gap-2">
        <span className="text-foreground text-sm font-semibold">{kpi.value}</span>
        <span
          className={cn(
            "inline-flex items-center gap-1 text-xs font-medium",
            isUp ? "text-emerald-600" : "text-destructive",
          )}
        >
          <ArrowUp className={cn("size-3", !isUp && "rotate-180")} />
          {kpi.trendLabel}
        </span>
      </div>
    </div>
  );
}

function Collaborators({ initials }: { initials: string[] }) {
  if (!initials.length) return null;

  return (
    <div className="flex items-center justify-end -space-x-2">
      {initials.slice(0, 3).map((value) => (
        <Avatar key={value} className="size-7 border">
          <AvatarFallback className="text-[11px] font-semibold">{value}</AvatarFallback>
        </Avatar>
      ))}
      {initials.length > 3 ? (
        <Avatar className="size-7 border">
          <AvatarFallback className="text-[11px] font-semibold">+{initials.length - 3}</AvatarFallback>
        </Avatar>
      ) : null}
    </div>
  );
}

function DashboardCard({ dashboard }: { dashboard: DashboardListItem }) {
  const hasAction = Boolean(dashboard.primaryAction);
  const hasDetails = Boolean(dashboard.detailHref);
  const cardBody = (
    <div className="flex flex-col gap-5">
      <div className="grid gap-3 sm:grid-cols-3">
        {dashboard.kpis.map((kpi) => (
          <KpiMiniCard key={kpi.label} kpi={kpi} />
        ))}
      </div>

      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-foreground text-lg font-semibold leading-tight">{dashboard.title}</h3>
        </div>

        <StatusPill status={dashboard.status} />

        <p className="text-muted-foreground text-sm leading-relaxed">{dashboard.description}</p>
      </div>
    </div>
  );

  return (
    <div
      className={cn(
        "bg-card flex h-full flex-col rounded-xl border p-6 shadow-sm",
        hasDetails && "border-border/80 hover:border-primary/40 transition-colors",
      )}
    >
      {hasDetails ? (
        <Link href={dashboard.detailHref!} className="block">
          {cardBody}
        </Link>
      ) : (
        cardBody
      )}

      <div className="mt-auto pt-6">
        <div className="flex items-center justify-between gap-3">
          {hasAction ? (
            hasDetails ? (
              <Button
                asChild
                size="sm"
                variant={dashboard.primaryAction?.variant ?? "default"}
                className="gap-2"
              >
                <Link href={dashboard.detailHref!}>
                  {dashboard.primaryAction?.label === "Create dashboard" ? <Plus className="size-4" /> : null}
                  {dashboard.primaryAction?.label}
                </Link>
              </Button>
            ) : (
              <Button
                size="sm"
                variant={dashboard.primaryAction?.variant ?? "default"}
                className="gap-2"
              >
                {dashboard.primaryAction?.label === "Create dashboard" ? <Plus className="size-4" /> : null}
                {dashboard.primaryAction?.label}
              </Button>
            )
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Users className="size-4" />
              <span>Published by</span>
              <span className="text-foreground font-medium">{dashboard.author ?? "Unknown"}</span>
            </div>
          )}

          {dashboard.collaborators ? <Collaborators initials={dashboard.collaborators} /> : null}
        </div>

        {dashboard.updatedLabel ? (
          <p className="mt-4 text-xs text-muted-foreground">{dashboard.updatedLabel}</p>
        ) : null}
      </div>
    </div>
  );
}

export default async function Page({ params, searchParams }: Props) {
  await params;
  await requireUserAbilityContext();

  const query = (await searchParams) ?? {};
  const tab = query.tab;
  const activeTab: (typeof TABS)[number]["id"] =
    tab === "draft" || tab === "published" || tab === "shared" ? tab : "all";

  const filteredDashboards =
    activeTab === "all"
      ? DASHBOARDS
      : DASHBOARDS.filter((dashboard) => dashboard.status === activeTab);

  const counts: Record<string, number> = {
    all: DASHBOARDS.length,
    draft: DASHBOARDS.filter((dashboard) => dashboard.status === "draft").length,
    published: DASHBOARDS.filter((dashboard) => dashboard.status === "published").length,
    shared: DASHBOARDS.filter((dashboard) => dashboard.status === "shared").length,
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-background/80">
        <div className="flex items-start justify-between gap-6 px-6 py-6">
          <div>
            <h1 className="text-foreground text-2xl font-semibold">Dashboards</h1>
          </div>
          <Button className="gap-2" size="sm">
            <Plus className="size-4" />
            Create dashboard
          </Button>
        </div>

        <div className="border-[var(--sidebar-border,#d4d4d4)] mx-6 flex h-9 w-[calc(100%-3rem)] items-center border-b">
          {TABS.map((tabItem) => {
            const href = tabItem.id === "all" ? "/dashboard" : `/dashboard?tab=${tabItem.id}`;
            const isActive = activeTab === tabItem.id;
            return (
              <Link
                key={tabItem.id}
                href={href}
                className={cn(
                  "inline-flex h-9 items-center justify-center border-b px-4 py-2 text-sm font-medium whitespace-nowrap transition-[color,border-color]",
                  isActive
                    ? "border-[var(--primary-dark,#47779b)] -mb-px border-b-[3px] text-[color:rgba(30,30,30,0.95)]"
                    : "border-transparent text-[color:rgba(30,30,30,0.95)]",
                )}
              >
                {tabItem.label} ({counts[tabItem.id] ?? 0})
              </Link>
            );
          })}
        </div>
      </header>

      <section className="flex-1 px-6 py-6">
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {filteredDashboards.map((dashboard) => (
            <DashboardCard key={dashboard.id} dashboard={dashboard} />
          ))}
        </div>
      </section>
    </div>
  );
}
