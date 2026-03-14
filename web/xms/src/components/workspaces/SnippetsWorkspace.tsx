"use client";

import * as React from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Copy,
  Trash2,
  FileText,
} from "lucide-react";
import { SnippetEditor } from "@/components/SnippetEditor";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";

import type { Snippet } from "@/types/snippet";
import { useSnippets } from "@/hooks/use-snippets";
import { useVariables } from "@/hooks/use-variables";
import { useUiStore } from "@/hooks/use-ui-store";
import { generateIncrementalName } from "@/lib/utils";

export function SnippetsWorkspace() {
  const { listQuery, createSnippet, updateSnippet, deleteSnippet } = useSnippets();
  const { variablesQuery } = useVariables();
  const snippets = (listQuery.data || []) as Snippet[];
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedTags, setSelectedTags] = React.useState<string[]>([]);
  const [selectedSnippet, setSelectedSnippet] = React.useState<Snippet | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [snippetToDelete, setSnippetToDelete] = React.useState<Snippet | null>(null);
  const { setUnsaved } = useUiStore();

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

  const handleNewSnippet = async () => {
    const defaultName = generateIncrementalName(
      "snippet",
      snippets.map((s) => s.name),
    );
    const created = await createSnippet({
      name: defaultName,
      body: "",
      tags: [],
    });
    setSelectedSnippet(created);
  };

  const handleDuplicateSnippet = async (snippet: Snippet) => {
    const duplicated = await createSnippet({
      name: `${snippet.name} (Copy)`,
      body: snippet.body,
      tags: snippet.tags,
    });
    setSelectedSnippet(duplicated);
  };

  const handleDeleteSnippet = (snippet: Snippet) => {
    setSnippetToDelete(snippet);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (snippetToDelete) {
      await deleteSnippet(snippetToDelete.id);
      setSnippetToDelete(null);
      if (selectedSnippet?.id === snippetToDelete.id) {
        setSelectedSnippet(null);
      }
    }
    setDeleteDialogOpen(false);
  };

  const handleSaveSnippet = async (updatedSnippet: Snippet) => {
    const saved = await updateSnippet({
      id: updatedSnippet.id,
      name: updatedSnippet.name,
      body: updatedSnippet.body,
      tags: updatedSnippet.tags,
    });
    setSelectedSnippet(saved);
    setUnsaved("snippets", false);
  };

  const variableOptions = (variablesQuery.data || []).map((v) => ({
    name: v.name,
    description: v.description,
  }));

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-border bg-card border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-foreground text-2xl font-semibold">Snippets</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Author reusable text blocks with tags; insert variables via @
            </p>
          </div>
          <div className="flex gap-2">
            {selectedSnippet && (
              <Button
                variant="outline"
                onClick={() => handleDuplicateSnippet(selectedSnippet)}
                className="gap-2 bg-transparent"
              >
                <Copy className="h-4 w-4" />
                Duplicate
              </Button>
            )}
            <Button onClick={handleNewSnippet} className="gap-2">
              <Plus className="h-4 w-4" />
              New Snippet
            </Button>
          </div>
        </div>

        {/* Search and filters */}
        <div className="mt-4 flex items-center gap-4">
          <div className="relative max-w-md flex-1">
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
      </div>

      {/* Content - Split View */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Snippet List */}
        <div className="border-border bg-card w-80 overflow-auto border-r">
          {filteredSnippets.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center p-6 text-center">
              <FileText className="text-muted-foreground mb-4 h-12 w-12" />
              <h3 className="text-foreground mb-2 text-lg font-medium">
                {snippets.length === 0
                  ? "No snippets yet"
                  : "No snippets match your search"}
              </h3>
              <p className="text-muted-foreground mb-6 text-sm">
                {snippets.length === 0
                  ? "Create your first snippet—short, reusable text with @variables."
                  : "Try adjusting your search terms or filters."}
              </p>
              {snippets.length === 0 && (
                <Button onClick={handleNewSnippet} className="gap-2">
                  <Plus className="h-4 w-4" />
                  Create your first snippet
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-2 p-4">
              {filteredSnippets.map((snippet) => (
                <Card
                  key={snippet.id}
                  className={`cursor-pointer p-4 transition-all hover:shadow-md ${
                    selectedSnippet?.id === snippet.id
                      ? "ring-primary bg-primary/5 ring-2"
                      : ""
                  }`}
                  onClick={() => setSelectedSnippet(snippet)}
                >
                  <div className="mb-2 flex items-start justify-between">
                    <h3 className="text-foreground line-clamp-1 font-medium">
                      {snippet.name}
                    </h3>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => handleDuplicateSnippet(snippet)}
                        >
                          <Copy className="mr-2 h-4 w-4" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => handleDeleteSnippet(snippet)}
                          className="text-destructive"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  <p className="text-muted-foreground mb-3 line-clamp-2 text-sm">
                    {snippet.body}
                  </p>

                  <div className="mb-2 flex flex-wrap gap-1">
                    {snippet.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  <div className="text-muted-foreground flex items-center justify-between text-xs">
                    <span>Updated {snippet.updatedAt}</span>
                    <span>{snippet.wordCount} words</span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Right Panel - Editor */}
        <div className="flex-1 overflow-hidden">
          {selectedSnippet ? (
            <SnippetEditor
              snippet={selectedSnippet}
              variables={variableOptions}
              onSave={handleSaveSnippet}
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <FileText className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
                <p className="text-muted-foreground">Select a snippet to edit</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={confirmDelete}
        title="Delete Snippet"
        description={`Are you sure you want to delete "${snippetToDelete?.name}"? This action cannot be undone.`}
      />
    </div>
  );
}
