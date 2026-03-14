"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  ChevronLeft,
  Copy,
  MessageSquareText,
  MoreHorizontal,
  MoveRight,
  Pencil,
  Plus,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

const GROUP_CONVERSATIONS = [
  {
    id: "channel-performance-breakdown",
    title: "Channel performance breakdown",
    updated: "Last updated 1 month ago",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
  },
  {
    id: "cost-efficiency-opportunities-q4",
    title: "Cost Efficiency Opportunities Identified in Q4",
    updated: "Last updated 1 month ago",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
  },
  {
    id: "month-over-month-cost-trends",
    title: "Month-over-Month Cost Trends",
    updated: "Last updated 1 month ago",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
  },
  {
    id: "revenue-trends-across-q4",
    title: "Revenue trends across Q4",
    updated: "Last updated 3 days ago",
    summary:
      "Key insights: Revenue performance summary for Q3 2025. Revenue increased 23% QoQ, driven by strong December performance.",
  },
];

export default function GroupConversationsPage() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isSelecting, setIsSelecting] = useState(false);
  const [isDuplicateOpen, setIsDuplicateOpen] = useState(false);
  const [duplicateDestination, setDuplicateDestination] = useState("same");
  const [selectedGroup, setSelectedGroup] = useState("");
  const conversationIds = useMemo(() => GROUP_CONVERSATIONS.map((item) => item.id), []);
  const hasSelection = selectedIds.length > 0;
  const showCheckboxes = isSelecting || hasSelection;
  const allSelected = selectedIds.length === conversationIds.length && conversationIds.length > 0;

  const toggleSelection = (id: string, nextValue?: boolean) => {
    setSelectedIds((prev) => {
      const isSelected = prev.includes(id);
      const shouldSelect = nextValue ?? !isSelected;
      if (shouldSelect) {
        return isSelected ? prev : [...prev, id];
      }
      return prev.filter((itemId) => itemId !== id);
    });
  };

  const handleSelectAll = (checked: boolean) => {
    setSelectedIds(checked ? [...conversationIds] : []);
  };

  return (
    <div className="bg-muted/10 min-h-screen">
      <header className="flex flex-wrap items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-3">
          <Button asChild variant="outline" size="icon" className="h-9 w-9">
            <Link href="/conversations">
              <ChevronLeft className="size-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-foreground text-lg font-semibold">Q4 Revenue Analysis</h1>
            <p className="text-muted-foreground text-xs">Updated 2 days ago</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {hasSelection ? (
            <Button variant="outline" size="sm" className="gap-2" disabled>
              <Plus className="size-4" />
              Add new conversation
            </Button>
          ) : (
            <Button asChild variant="outline" size="sm" className="gap-2">
              <Link href="/conversations/new">
                <Plus className="size-4" />
                Add new conversation
              </Link>
            </Button>
          )}
          <Button size="sm" disabled={hasSelection}>
            Create dashboard
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
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
      </header>

      <main className={cn("px-6 pb-10", hasSelection && "pb-28")}>
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          <div className="space-y-2">
            <h2 className="text-foreground text-base font-semibold">Conversations</h2>
            <p className="text-muted-foreground text-sm">
              Analysis of Q4 product cost data to uncover month-over-month trends, identify major cost drivers, and
              compare manufacturing and logistics expenses.
            </p>
          </div>

          <div className="flex items-center justify-between text-sm">
            {showCheckboxes ? (
              <div className="flex items-center gap-2">
                <Checkbox checked={allSelected} onCheckedChange={(checked) => handleSelectAll(checked === true)} />
                <span className="text-foreground font-medium">Selected ({selectedIds.length})</span>
              </div>
            ) : (
              <button type="button" className="text-primary font-medium" onClick={() => setIsSelecting(true)}>
                Select
              </button>
            )}
            <Button variant="ghost" size="icon-sm">
              <SlidersHorizontal className="size-4" />
            </Button>
          </div>

          <div className="space-y-4">
            {GROUP_CONVERSATIONS.map((conversation) => (
              <div
                key={conversation.id}
                className={cn(
                  "bg-background rounded-lg border p-4 shadow-sm transition",
                  selectedIds.includes(conversation.id) && "border-primary/60 shadow-md",
                )}
              >
                <div className="flex items-start gap-3">
                  {showCheckboxes ? (
                    <Checkbox
                      checked={selectedIds.includes(conversation.id)}
                      onCheckedChange={(checked) => toggleSelection(conversation.id, checked === true)}
                    />
                  ) : null}
                  <div className="bg-muted/20 text-muted-foreground flex size-9 items-center justify-center rounded-md border">
                    <MessageSquareText className="size-4" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-foreground text-sm font-semibold">{conversation.title}</h3>
                    <p className="text-muted-foreground text-xs">{conversation.updated}</p>
                    <p className="text-muted-foreground pt-2 text-sm">{conversation.summary}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      {hasSelection ? (
        <div className="bg-background/95 sticky bottom-0 border-t px-6 py-3 backdrop-blur">
          <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => {
                  setSelectedIds([]);
                }}
              >
                <X className="size-4" />
                Clear
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSelectedIds([]);
                  setIsSelecting(false);
                }}
              >
                Cancel
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="gap-2" onClick={() => setIsDuplicateOpen(true)}>
                <Copy className="size-4" />
                Duplicate
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <MoveRight className="size-4" />
                Move to
              </Button>
              <Button variant="destructive" size="sm" className="gap-2">
                <Trash2 className="size-4" />
                Delete
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      <Dialog open={isDuplicateOpen} onOpenChange={setIsDuplicateOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="bg-muted text-muted-foreground flex size-8 items-center justify-center rounded-md">
                <Copy className="size-4" />
              </div>
              <DialogTitle className="text-xl font-semibold">Duplicate conversation</DialogTitle>
            </div>
            <DialogDescription>Choose where to duplicate</DialogDescription>
          </DialogHeader>

          <RadioGroup value={duplicateDestination} onValueChange={setDuplicateDestination}>
            <div className="flex items-center gap-3">
              <RadioGroupItem value="same" id="duplicate-same" />
              <Label htmlFor="duplicate-same">In this location</Label>
            </div>
            <div className="flex items-center gap-3">
              <RadioGroupItem value="group" id="duplicate-group" />
              <Label htmlFor="duplicate-group">Copy to a group</Label>
            </div>
          </RadioGroup>

          <div className="space-y-2">
            <Label
              htmlFor="duplicate-group-select"
              className={cn(duplicateDestination !== "group" && "text-muted-foreground")}
            >
              Select group
            </Label>
            <Select value={selectedGroup} onValueChange={setSelectedGroup} disabled={duplicateDestination !== "group"}>
              <SelectTrigger id="duplicate-group-select">
                <SelectValue placeholder="Select group" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="q4-revenue-analysis">Q4 Revenue Analysis</SelectItem>
                <SelectItem value="product-cost-q4">Product cost in Q4</SelectItem>
                <SelectItem value="margin-comparison-2025">Margin comparison 2025</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setIsDuplicateOpen(false)}>
              Cancel
            </Button>
            <Button>Duplicate</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
