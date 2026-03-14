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
  Trash2,
  MessageSquare,
} from "lucide-react";
import { PromptComposer } from "@/components/PromptComposer";
import { useUiStore } from "@/hooks/use-ui-store";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";
import type { Prompt } from "@/types/prompt";
import { usePrompts } from "@/hooks/use-prompts";
import { useSnippets } from "@/hooks/use-snippets";
import { useVariables } from "@/hooks/use-variables";
import { generateIncrementalName } from "@/lib/utils";

// Shared types and hooks used; mock data removed

export function PromptsWorkspace() {
  const { listQuery, createPrompt, updatePrompt, deletePrompt } = usePrompts();
  const { listQuery: snippetsQuery } = useSnippets();
  const { variablesQuery } = useVariables();
  const prompts = (listQuery.data || []) as Prompt[];
  const snippets = snippetsQuery.data || [];
  const variables = variablesQuery.data || [];
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedTags, setSelectedTags] = React.useState<string[]>([]);
  const [selectedPrompt, setSelectedPrompt] = React.useState<Prompt | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [promptToDelete, setPromptToDelete] = React.useState<Prompt | null>(null);
  const { setUnsaved } = useUiStore();

  // Get all unique tags
  const allTags = Array.from(new Set(prompts.flatMap((p) => p.tags)));

  // Filter prompts based on search and tags
  const filteredPrompts = prompts.filter((prompt) => {
    const matchesSearch =
      prompt.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prompt.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesTags =
      selectedTags.length === 0 ||
      selectedTags.some((tag) => prompt.tags.includes(tag));

    return matchesSearch && matchesTags;
  });

  const handleNewPrompt = async () => {
    const defaultName = generateIncrementalName(
      "prompt",
      prompts.map((p) => p.name),
    );
    const created = await createPrompt({
      name: defaultName,
      tags: [],
      blocks: [],
    });
    setSelectedPrompt(created);
  };

  const handleDeletePrompt = (prompt: Prompt) => {
    setPromptToDelete(prompt);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (promptToDelete) {
      await deletePrompt(promptToDelete.id);
      if (selectedPrompt?.id === promptToDelete.id) {
        const remaining = prompts.filter((p) => p.id !== promptToDelete.id);
        setSelectedPrompt(remaining.length > 0 ? remaining[0] : null);
      }
      setPromptToDelete(null);
    }
    setDeleteDialogOpen(false);
  };

  const handleSavePrompt = async (updatedPrompt: Prompt) => {
    const saved = await updatePrompt({
      id: updatedPrompt.id,
      name: updatedPrompt.name,
      tags: updatedPrompt.tags,
      blocks: updatedPrompt.blocks,
    });
    setSelectedPrompt(saved);
    setUnsaved("prompts", false);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-border bg-card border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-foreground text-2xl font-semibold">Prompts</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Compose full prompts from an ordered list of snippets + ad-hoc text
            </p>
          </div>
          <Button onClick={handleNewPrompt} className="gap-2">
            <Plus className="h-4 w-4" />
            New Prompt
          </Button>
        </div>

        {/* Search and filters */}
        <div className="mt-4 flex items-center gap-4">
          <div className="relative max-w-md flex-1">
            <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform" />
            <Input
              placeholder="Search prompts..."
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
        {/* Left Panel - Prompt List */}
        <div className="border-border bg-card w-80 overflow-auto border-r">
          {filteredPrompts.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center p-6 text-center">
              <MessageSquare className="text-muted-foreground mb-4 h-12 w-12" />
              <h3 className="text-foreground mb-2 text-lg font-medium">
                {prompts.length === 0
                  ? "No prompts yet"
                  : "No prompts match your search"}
              </h3>
              <p className="text-muted-foreground mb-6 text-sm">
                {prompts.length === 0
                  ? "Compose prompts by stacking snippets and free text. Add your first block."
                  : "Try adjusting your search terms or filters."}
              </p>
              {prompts.length === 0 && (
                <Button onClick={handleNewPrompt} className="gap-2">
                  <Plus className="h-4 w-4" />
                  Create your first prompt
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-2 p-4">
              {filteredPrompts.map((prompt) => (
                <Card
                  key={prompt.id}
                  className={`group cursor-pointer p-4 transition-all hover:shadow-md ${
                    selectedPrompt?.id === prompt.id
                      ? "ring-primary bg-primary/5 ring-2"
                      : ""
                  }`}
                  onClick={() => setSelectedPrompt(prompt)}
                >
                  <div className="mb-2 flex items-start justify-between">
                    <h3 className="text-foreground line-clamp-1 font-medium">
                      {prompt.name}
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
                          onClick={() => handleDeletePrompt(prompt)}
                          className="text-destructive"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  <div className="mb-2 flex flex-wrap gap-1">
                    {prompt.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  <div className="text-muted-foreground flex items-center justify-between text-xs">
                    <span>Updated {prompt.updatedAt}</span>
                    <span>{prompt.blocks.length} blocks</span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Right Panel - Composer */}
        <div className="flex-1 overflow-hidden">
          {selectedPrompt ? (
            <PromptComposer
              prompt={selectedPrompt}
              snippets={snippets}
              variables={variables.map((v) => ({
                name: v.name,
                value: String(v.defaultValue),
              }))}
              onSave={handleSavePrompt}
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <MessageSquare className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
                <p className="text-muted-foreground">Select a prompt to edit</p>
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
        title="Delete Prompt"
        description={`Are you sure you want to delete "${promptToDelete?.name}"? This action cannot be undone.`}
      />
    </div>
  );
}
