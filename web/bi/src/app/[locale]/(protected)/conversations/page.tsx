"use client";

import { useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronRight,
  Copy,
  Eye,
  Folder,
  ChevronDown,
  MessageSquareText,
  MoreHorizontal,
  MoveRight,
  Pencil,
  Pin,
  Plus,
  RefreshCcw,
  Search,
  Settings2,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const TABS = [
  { id: "groups", label: "My groups", count: 4 },
  { id: "conversations", label: "My conversations", count: 6 },
  { id: "shared", label: "Shared with me", count: 3 },
];

const GROUPS = [
  {
    slug: "product-cost-investigation",
    title: "Product cost investigation",
    updated: "Updated 2 hours ago",
    description: "Exploratory investigations into product cost anomalies, variance spikes, and underlying drivers.",
    conversationCount: 2,
    conversations: ["Revenue trends across Q4", "Channel performance breakdown"],
    actionLabel: "Create dashboard",
    actionIcon: Plus,
    actionVariant: "outline" as const,
  },
  {
    slug: "product-cost-in-q4",
    title: "Product cost in Q4",
    updated: "Updated 5 hours ago",
    description: "Analysis focused on Q4 product cost trends, including month-over-month changes.",
    conversationCount: 10,
    conversations: ["Revenue trends across Q4", "Channel performance breakdown", "Campaign ROI analysis"],
    actionLabel: "Update dashboard",
    actionIcon: RefreshCcw,
    actionVariant: "default" as const,
    isPinned: true,
  },
  {
    slug: "margin-comparison-2025",
    title: "Margin comparison 2025",
    updated: "Updated 1 day ago",
    description: "Comparative analysis of margins across 2025, examining trends and changes over time.",
    conversationCount: 2,
    conversations: ["Revenue trends across Q4", "Channel performance breakdown"],
    actionLabel: "View dashboard",
    actionIcon: Eye,
    actionVariant: "outline" as const,
  },
  {
    slug: "q4-revenue-analysis",
    title: "Q4 Revenue Analysis",
    updated: "Updated 2 days ago",
    description: "Analysis on Q4 revenue drivers, evaluating performance drivers and share shifts.",
    conversationCount: 4,
    conversations: [
      "Revenue trends across Q4",
      "Channel performance breakdown",
      "Cost Efficiency Opportunities",
      "Month-over-Month Cost Trends",
    ],
    actionLabel: "Create dashboard",
    actionIcon: Plus,
    actionVariant: "outline" as const,
    highlighted: true,
    isPinned: true,
  },
];

const CONVERSATIONS = [
  {
    title: "Month-over-Month Cost Trends",
    updated: "Last updated 1 month ago",
    addedTo: "Q4 Revenue Analysis",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    actionLabel: "Update dashboard",
    actionIcon: RefreshCcw,
    isNew: true,
  },
  {
    title: "Month-over-Month Cost Trends",
    updated: "Last updated 1 month ago",
    addedTo: "Product cost in Q4",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    actionLabel: "View dashboard",
    actionIcon: Eye,
  },
  {
    title: "Month-over-Month Cost Trends",
    updated: "Last updated 1 month ago",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    actionLabel: "Create dashboard",
    actionIcon: Plus,
    highlighted: true,
  },
  {
    title: "Month-over-Month Cost Trends",
    updated: "Last updated 1 month ago",
    addedTo: "Product cost investigation",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    actionLabel: "Create dashboard",
    actionIcon: Plus,
  },
  {
    title: "Month-over-Month Cost Trends",
    updated: "Last updated 1 month ago",
    addedTo: "Margin comparison 2025",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    actionLabel: "Update dashboard",
    actionIcon: RefreshCcw,
    isNew: true,
  },
  {
    title: "Month-over-Month Cost Trends",
    updated: "Last updated 1 month ago",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
    actionLabel: "View dashboard",
    actionIcon: Eye,
  },
];

const SHARED_GROUPS = [
  {
    slug: "product-cost-investigation",
    title: "Product cost investigation",
    updated: "Updated 2 hours ago",
    description: "Exploratory investigations into product cost anomalies, variance spikes, and underlying drivers.",
    conversationCount: 2,
    conversations: ["Revenue trends across Q4", "Channel performance breakdown"],
    author: "Dan Chan",
  },
  {
    slug: "product-cost-in-q4",
    title: "Product cost in Q4",
    updated: "Updated 5 hours ago",
    description: "Analysis focused on Q4 product cost trends, including month-over-month changes.",
    conversationCount: 10,
    conversations: ["Revenue trends across Q4", "Channel performance breakdown", "Campaign ROI analysis"],
    author: "Dan Chan",
  },
  {
    slug: "q4-revenue-analysis",
    title: "Q4 Revenue Analysis",
    updated: "Updated 2 days ago",
    description: "Analysis on Q4 revenue data, identifying trends and evaluating performance against targets.",
    conversationCount: 4,
    conversations: [
      "Revenue trends across Q4",
      "Channel performance breakdown",
      "Cost Efficiency Opportunities",
      "Month-over-Month Cost Trends",
    ],
    author: "Dan Chan",
    highlighted: true,
  },
];

export default function ConversationsPage() {
  const [activeTab, setActiveTab] = useState("groups");
  const [isNewGroupOpen, setIsNewGroupOpen] = useState(false);
  const router = useRouter();

  const openGroup = (slug: string) => {
    router.push(`/conversations/groups/${slug}`);
  };

  const handleGroupKeyDown = (event: KeyboardEvent<HTMLDivElement>, slug: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openGroup(slug);
    }
  };

  return (
    <div className="flex min-h-full flex-col">
      <header className="bg-background/80">
        <div className="flex items-center justify-between px-6 py-5">
          <div>
            <h1 className="text-foreground text-2xl font-semibold">Conversations</h1>
          </div>
        </div>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            {TABS.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id}>
                {tab.label} ({tab.count})
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </header>

      {activeTab === "groups" ? (
        <section className="flex-1 px-6 py-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">Groups</p>
              <h2 className="text-lg font-semibold">Groups</h2>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" className="gap-2" onClick={() => setIsNewGroupOpen(true)}>
                <Plus className="size-4" />
                New group
              </Button>
              <Button variant="ghost" size="icon-sm">
                <Settings2 className="size-4" />
              </Button>
            </div>
          </div>

          <div className="mt-6 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {GROUPS.map((group) => {
              const GroupActionIcon = group.actionIcon;

              return (
                <div
                  key={`${group.title}-${group.updated}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => openGroup(group.slug)}
                  onKeyDown={(event) => handleGroupKeyDown(event, group.slug)}
                  className={`bg-card flex h-full flex-col rounded-xl border p-6 shadow-sm ${
                    group.highlighted ? "border-foreground/40 shadow-md" : ""
                  }`}
                >
                  <div className="space-y-4">
                    <div className="bg-muted/40 h-28 w-full rounded-lg border" />
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-semibold">{group.title}</h3>
                          {group.highlighted ? <span className="bg-primary size-2 rounded-full" /> : null}
                        </div>
                        <p className="text-muted-foreground text-xs">{group.updated}</p>
                      </div>
                      <div className="flex items-center gap-1">
                        {group.isPinned ? <Pin className="text-muted-foreground size-3.5" /> : null}
                        <button
                          type="button"
                          onClick={(event) => event.stopPropagation()}
                          className="text-muted-foreground hover:bg-muted inline-flex size-8 items-center justify-center rounded-md transition"
                          aria-label="Group actions"
                        >
                          <MoreHorizontal className="size-4" />
                        </button>
                      </div>
                    </div>
                    <p className="text-muted-foreground text-sm">{group.description}</p>
                    <div className="space-y-2">
                      <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                        {group.conversationCount} Conversations
                      </p>
                      <ul className="text-primary space-y-1 text-sm">
                        {group.conversations.map((conversation) => (
                          <li key={conversation} className="flex items-center gap-2">
                            <ChevronRight className="size-3" />
                            <span className="truncate">{conversation}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  <div className="mt-auto pt-5">
                    <Button
                      variant={group.actionVariant}
                      className="w-fit gap-2"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <GroupActionIcon className="size-4" />
                      {group.actionLabel}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {activeTab === "conversations" ? (
        <section className="flex-1 px-6 py-8">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
            <div className="text-center">
              <p className="text-foreground text-sm font-semibold">All conversations</p>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
                <Input placeholder="Search conversations..." className="pl-9" />
              </div>
              <Button variant="outline" size="icon" className="h-9 w-9">
                <SlidersHorizontal className="size-4" />
              </Button>
            </div>

            <button type="button" className="text-primary w-fit text-sm font-medium">
              Select
            </button>

            <div className="space-y-4">
              {CONVERSATIONS.map((conversation, index) => {
                const ActionIcon = conversation.actionIcon;
                return (
                  <div
                    key={`${conversation.title}-${index}`}
                    className={`bg-card rounded-lg border p-4 shadow-sm ${
                      conversation.highlighted ? "border-primary/50" : ""
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <div className="bg-muted/40 mt-1 flex size-8 items-center justify-center rounded-md border">
                          <MessageSquareText className="size-4" />
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h3 className="text-foreground text-sm font-semibold">{conversation.title}</h3>
                            {conversation.isNew ? <span className="bg-primary size-2 rounded-full" /> : null}
                          </div>
                          <p className="text-muted-foreground text-xs">{conversation.updated}</p>
                        </div>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            type="button"
                            className="text-muted-foreground hover:bg-muted inline-flex size-8 items-center justify-center rounded-md transition"
                          >
                            <MoreHorizontal className="size-4" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>
                            <MoveRight className="size-4" />
                            Move to
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Pencil className="size-4" />
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Copy className="size-4" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem variant="destructive">
                            <Trash2 className="size-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    {conversation.addedTo ? (
                      <div className="text-muted-foreground mt-2 flex items-center gap-2 text-xs">
                        <Folder className="size-3" />
                        <span>Added to {conversation.addedTo}</span>
                      </div>
                    ) : null}

                    <p className="text-muted-foreground mt-2 text-sm">{conversation.summary}</p>

                    <div className="mt-3">
                      <Button variant="ghost" size="sm" className="text-primary gap-2 px-0 hover:bg-transparent">
                        <ActionIcon className="size-4" />
                        {conversation.actionLabel}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === "shared" ? (
        <section className="flex-1 px-6 py-8">
          <div className="flex items-center justify-end">
            <Button variant="outline" size="sm" className="gap-2">
              Groups
              <ChevronDown className="size-4" />
            </Button>
          </div>

          <div className="mt-6 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {SHARED_GROUPS.map((group) => (
              <div
                key={`${group.title}-${group.updated}`}
                role="button"
                tabIndex={0}
                onClick={() => openGroup(group.slug)}
                onKeyDown={(event) => handleGroupKeyDown(event, group.slug)}
                className={`bg-card flex h-full flex-col rounded-xl border p-6 shadow-sm ${
                  group.highlighted ? "border-primary/50 shadow-md" : ""
                }`}
              >
                <div className="space-y-4">
                  <div className="bg-muted/40 h-28 w-full rounded-lg border" />
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                      <h3 className="text-base font-semibold">{group.title}</h3>
                      <p className="text-muted-foreground text-xs">{group.updated}</p>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          type="button"
                          onClick={(event) => event.stopPropagation()}
                          className="text-muted-foreground hover:bg-muted inline-flex size-8 items-center justify-center rounded-md transition"
                        >
                          <MoreHorizontal className="size-4" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(event) => event.stopPropagation()}>
                          <Copy className="size-4" />
                          Duplicate
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <p className="text-muted-foreground text-sm">{group.description}</p>
                  <div className="space-y-2">
                    <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                      {group.conversationCount} Conversations
                    </p>
                    <ul className="text-primary space-y-1 text-sm">
                      {group.conversations.map((conversation) => (
                        <li key={conversation} className="flex items-center gap-2">
                          <ChevronRight className="size-3" />
                          <span className="truncate">{conversation}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="text-muted-foreground mt-auto flex items-center gap-2 pt-4 text-sm">
                  <div className="bg-muted text-foreground flex size-6 items-center justify-center rounded-full text-[10px] font-semibold">
                    {group.author
                      .split(" ")
                      .map((part) => part[0])
                      .join("")
                      .slice(0, 2)}
                  </div>
                  <span>Published by</span>
                  <span className="text-foreground font-medium">{group.author}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <Dialog open={isNewGroupOpen} onOpenChange={setIsNewGroupOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader className="space-y-2">
            <DialogTitle className="text-xl font-semibold">New group</DialogTitle>
            <DialogDescription>
              Create a new group to organize the selected conversations. You can generate a dashboard from this group
              anytime.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label className="text-foreground text-sm font-semibold" htmlFor="group-name">
              Add group name
            </label>
            <Input id="group-name" placeholder="e.g. Q4 2025 Revenue Analysis" />
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setIsNewGroupOpen(false)}>
              Cancel
            </Button>
            <Button>Create group</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
