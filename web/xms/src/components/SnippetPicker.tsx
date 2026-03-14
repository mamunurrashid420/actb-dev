"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Checkbox } from "@/components/ui/Checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/Dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import { Search, Filter, Plus } from "lucide-react";
// local state, no zustand

interface Snippet {
  id: string;
  name: string;
  body: string;
  tags: string[];
}

interface SnippetPickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  snippets: Snippet[];
  onSelect: (snippetIds: string[]) => void;
}

export function SnippetPicker({
  open,
  onOpenChange,
  snippets,
  onSelect,
}: SnippetPickerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedSnippets, setSelectedSnippets] = useState<string[]>([]);

  // Get all unique tags
  const allTags = Array.from(new Set(snippets.flatMap((s) => s.tags)));

  // Filter snippets based on search and tags
  const filteredSnippets = snippets.filter((snippet) => {
    const matchesSearch =
      snippet.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      snippet.body.toLowerCase().includes(searchQuery.toLowerCase()) ||
      snippet.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesTags =
      selectedTags.length === 0 ||
      selectedTags.some((tag) => snippet.tags.includes(tag));

    return matchesSearch && matchesTags;
  });

  const handleSnippetToggle = (snippetId: string) => {
    setSelectedSnippets((prev) =>
      prev.includes(snippetId)
        ? prev.filter((id) => id !== snippetId)
        : [...prev, snippetId],
    );
  };

  const handleInsert = () => {
    if (selectedSnippets.length > 0) {
      onSelect(selectedSnippets);
      setSelectedSnippets([]);
      setSearchQuery("");
      setSelectedTags([]);
    }
  };

  const handleCancel = () => {
    setSelectedSnippets([]);
    setSearchQuery("");
    setSelectedTags([]);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-4xl flex-col">
        <DialogHeader>
          <DialogTitle>Insert Snippets</DialogTitle>
          <DialogDescription>
            Search and select snippets to add to your prompt. Multiple selections will
            preserve the order selected.
          </DialogDescription>
        </DialogHeader>

        {/* Search and filters */}
        <div className="flex items-center gap-4 border-b py-4">
          <div className="relative flex-1">
            <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform" />
            <Input
              placeholder="Search snippets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2 bg-transparent">
                <Filter className="h-4 w-4" />
                Filter by tags
                {selectedTags.length > 0 && (
                  <Badge variant="secondary" className="ml-1">
                    {selectedTags.length}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={() => setSelectedTags([])}>
                Clear filters
              </DropdownMenuItem>
              {allTags.map((tag) => (
                <DropdownMenuItem
                  key={tag}
                  onClick={() =>
                    setSelectedTags((prev) =>
                      prev.includes(tag)
                        ? prev.filter((t) => t !== tag)
                        : [...prev, tag],
                    )
                  }
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`h-2 w-2 rounded-full ${
                        selectedTags.includes(tag) ? "bg-primary" : "bg-muted"
                      }`}
                    />
                    {tag}
                  </div>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Snippet list */}
        <div className="flex-1 overflow-auto">
          {filteredSnippets.length === 0 ? (
            <div className="flex h-32 items-center justify-center">
              <p className="text-muted-foreground">
                No snippets found matching your criteria.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 p-4">
              {filteredSnippets.map((snippet) => (
                <Card
                  key={snippet.id}
                  className={`cursor-pointer p-4 transition-all hover:shadow-md ${
                    selectedSnippets.includes(snippet.id)
                      ? "ring-primary bg-primary/5 ring-2"
                      : ""
                  }`}
                  onClick={() => handleSnippetToggle(snippet.id)}
                >
                  <div className="flex items-start gap-3">
                    <Checkbox
                      checked={selectedSnippets.includes(snippet.id)}
                      onChange={() => handleSnippetToggle(snippet.id)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <div className="mb-2 flex items-center justify-between">
                        <h3 className="text-foreground font-medium">{snippet.name}</h3>
                        {selectedSnippets.includes(snippet.id) && (
                          <Badge variant="secondary" className="text-xs">
                            #{selectedSnippets.indexOf(snippet.id) + 1}
                          </Badge>
                        )}
                      </div>
                      <p className="text-muted-foreground mb-3 line-clamp-2 text-sm">
                        {snippet.body}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {snippet.tags.map((tag) => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between border-t pt-4">
          <div className="text-muted-foreground text-sm">
            {selectedSnippets.length > 0 &&
              `${selectedSnippets.length} snippet(s) selected`}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button
              onClick={handleInsert}
              disabled={selectedSnippets.length === 0}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Insert {selectedSnippets.length > 0 && `(${selectedSnippets.length})`}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
