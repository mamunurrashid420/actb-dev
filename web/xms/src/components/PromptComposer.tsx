"use client";

import type React from "react";

import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { TextArea } from "@/components/ui/TextArea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import {
  Save,
  Eye,
  Copy,
  Download,
  Plus,
  GripVertical,
  MoreHorizontal,
  Trash2,
  FileText,
  Type,
  X,
  AtSign,
} from "lucide-react";
import { SnippetPicker } from "@/components/SnippetPicker";
import type { Prompt, PromptBlock } from "@/types/prompt";
import { useUiStore } from "@/hooks/use-ui-store";

interface Snippet {
  id: string;
  name: string;
  body: string;
  tags: string[];
}

interface Variable {
  name: string;
  value: string;
}

interface PromptComposerProps {
  prompt: Prompt;
  snippets: Snippet[];
  variables: Variable[];
  onSave: (prompt: Prompt) => void;
}

export function PromptComposer({
  prompt,
  snippets,
  variables,
  onSave,
}: PromptComposerProps) {
  const [formData, setFormData] = useState({
    name: prompt.name,
    tags: [...prompt.tags],
    blocks: [...prompt.blocks],
  });
  const [newTag, setNewTag] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [substituteVariables, setSubstituteVariables] = useState(false);
  const [snippetPickerOpen, setSnippetPickerOpen] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const { setUnsaved, registerSaveHandler } = useUiStore();
  const saveRef = useRef<() => void>(() => {});

  useEffect(() => {
    setFormData({
      name: prompt.name,
      tags: [...prompt.tags],
      blocks: [...prompt.blocks],
    });
    setHasChanges(false);
  }, [prompt]);

  useEffect(() => {
    const hasNameChange = formData.name !== prompt.name;
    const hasTagsChange =
      JSON.stringify(formData.tags.sort()) !== JSON.stringify(prompt.tags.sort());
    const hasBlocksChange =
      JSON.stringify(formData.blocks) !== JSON.stringify(prompt.blocks);
    const dirty = hasNameChange || hasTagsChange || hasBlocksChange;
    setHasChanges(dirty);
    setUnsaved("prompts", dirty);
  }, [formData, prompt, setUnsaved]);

  const handleSave = useCallback(() => {
    const updatedPrompt: Prompt = {
      ...prompt,
      name: formData.name,
      tags: formData.tags,
      blocks: formData.blocks,
      updatedAt: new Date().toISOString().split("T")[0],
    };
    onSave(updatedPrompt);
    setHasChanges(false);
    setUnsaved("prompts", false);
  }, [prompt, formData, onSave, setUnsaved]);

  // Keep latest save handler in a ref to avoid re-registering on each change
  useEffect(() => {
    saveRef.current = handleSave;
  }, [handleSave]);

  // Register a stable auto-save handler while composer is mounted
  useEffect(() => {
    const handler = () => saveRef.current();
    registerSaveHandler("prompts", handler);
    return () => {
      registerSaveHandler("prompts", () => {});
    };
  }, [registerSaveHandler]);

  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData((prev) => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()],
      }));
      setNewTag("");
    }
  };

  const removeTag = (tagToRemove: string) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags.filter((tag) => tag !== tagToRemove),
    }));
  };

  const addTextBlock = () => {
    setFormData((prev) => ({
      ...prev,
      blocks: [...prev.blocks, { type: "text", text: "" }],
    }));
  };

  const addSnippetBlocks = (snippetIds: string[]) => {
    const newBlocks = snippetIds.map((id) => ({
      type: "snippet" as const,
      snippetId: id,
    }));
    setFormData((prev) => ({
      ...prev,
      blocks: [...prev.blocks, ...newBlocks],
    }));
    setSnippetPickerOpen(false);
  };

  const updateBlock = (index: number, block: PromptBlock) => {
    setFormData((prev) => ({
      ...prev,
      blocks: prev.blocks.map((b, i) => (i === index ? block : b)),
    }));
  };

  const duplicateBlock = (index: number) => {
    const block = formData.blocks[index];
    setFormData((prev) => ({
      ...prev,
      blocks: [
        ...prev.blocks.slice(0, index + 1),
        { ...block },
        ...prev.blocks.slice(index + 1),
      ],
    }));
  };

  const removeBlock = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      blocks: prev.blocks.filter((_, i) => i !== index),
    }));
  };

  const moveBlock = (fromIndex: number, toIndex: number) => {
    const blocks = [...formData.blocks];
    const [movedBlock] = blocks.splice(fromIndex, 1);
    blocks.splice(toIndex, 0, movedBlock);
    setFormData((prev) => ({ ...prev, blocks }));
  };

  const renderFinalPrompt = () => {
    let result = "";
    formData.blocks.forEach((block, index) => {
      if (block.type === "snippet" && block.snippetId) {
        const snippet = snippets.find((s) => s.id === block.snippetId);
        if (snippet) {
          result += snippet.body;
        }
      } else if (block.type === "text" && block.text) {
        result += block.text;
      }

      if (index < formData.blocks.length - 1) {
        result += "\n\n";
      }
    });

    if (substituteVariables) {
      variables.forEach((variable) => {
        const regex = new RegExp(`@${variable.name}`, "g");
        result = result.replace(regex, variable.value);
      });
    }

    return result;
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(renderFinalPrompt());
  };

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== dropIndex) {
      moveBlock(draggedIndex, dropIndex);
    }
    setDraggedIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const getUsedVariables = () => {
    const allText = formData.blocks
      .map((block) => {
        if (block.type === "snippet" && block.snippetId) {
          const snippet = snippets.find((s) => s.id === block.snippetId);
          return snippet?.body || "";
        } else if (block.type === "text" && block.text) {
          return block.text;
        }
        return "";
      })
      .join(" ");

    const matches = allText.match(/@\w+/g) || [];
    return Array.from(new Set(matches.map((match) => match.substring(1))));
  };

  const usedVariables = getUsedVariables();

  return (
    <div className="flex h-full flex-col">
      <div className="border-border bg-card border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="max-w-md flex-1">
            <Input
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              className="border-none bg-transparent px-0 text-lg font-medium focus-visible:ring-0"
              placeholder="Prompt name..."
            />
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={handleSave} disabled={!hasChanges} className="gap-2">
              <Save className="h-4 w-4" />
              Save
            </Button>
            <Button variant="outline" size="sm" className="gap-2 bg-transparent">
              <Download className="h-4 w-4" />
              Print
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={copyToClipboard}
              className="gap-2 bg-transparent"
            >
              <Copy className="h-4 w-4" />
              Export
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPreview(!showPreview)}
              className="gap-2 bg-transparent"
            >
              <Eye className="h-4 w-4" />
              {showPreview ? "Edit" : "Preview"}
            </Button>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <div className="flex min-w-0 flex-1 flex-wrap gap-2">
            {formData.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="shrink-0 gap-1">
                {tag}
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  className="hover:bg-destructive hover:text-destructive-foreground ml-1 rounded-full"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex shrink-0 gap-2">
            <Input
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addTag())}
              placeholder="Add tag..."
              className="h-8 w-24 text-sm"
            />
            <Button type="button" onClick={addTag} size="sm" variant="outline">
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-auto p-6">
          {showPreview ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Live Preview</h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSubstituteVariables(!substituteVariables)}
                  className="gap-2 bg-transparent"
                >
                  <AtSign className="h-4 w-4" />
                  {substituteVariables ? "Show variables" : "Substitute variables"}
                </Button>
              </div>
              <Card>
                <CardContent className="p-6">
                  <pre className="whitespace-pre-wrap font-mono text-sm">
                    {renderFinalPrompt()}
                  </pre>
                </CardContent>
              </Card>

              {usedVariables.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Used Variables</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {usedVariables.map((varName) => {
                      const variable = variables.find((v) => v.name === varName);
                      return (
                        <div key={varName} className="flex items-start gap-2">
                          <code className="bg-primary/20 text-blue-contrast rounded px-2 py-1 font-mono text-xs">
                            @{varName}
                          </code>
                          {variable && (
                            <span className="text-muted-foreground text-xs">
                              {variable.value}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Blocks</h3>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button className="gap-2">
                      <Plus className="h-4 w-4" />
                      Add Block
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => setSnippetPickerOpen(true)}>
                      <FileText className="text-blue-contrast h-4 w-4" />
                      Snippet Block
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={addTextBlock}>
                      <Type className="text-blue-contrast h-4 w-4" />
                      Free Text Block
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {formData.blocks.length === 0 ? (
                <Card className="p-12 text-center">
                  <div className="mx-auto max-w-md">
                    <h3 className="text-foreground mb-2 text-lg font-medium">
                      No blocks yet
                    </h3>
                    <p className="text-muted-foreground mb-6">
                      Start building your prompt by adding snippet blocks or free text
                      blocks.
                    </p>
                    <div className="flex justify-center gap-2">
                      <Button
                        onClick={() => setSnippetPickerOpen(true)}
                        variant="outline"
                        className="gap-2"
                      >
                        <FileText className="h-4 w-4" />
                        Add Snippet
                      </Button>
                      <Button
                        onClick={addTextBlock}
                        variant="outline"
                        className="gap-2 bg-transparent"
                      >
                        <Type className="h-4 w-4" />
                        Add Text
                      </Button>
                    </div>
                  </div>
                </Card>
              ) : (
                <div className="space-y-4">
                  {formData.blocks.map((block, index) => (
                    <Card
                      key={index}
                      className={`group ${draggedIndex === index ? "opacity-50" : ""}`}
                      draggable
                      onDragStart={(e) => handleDragStart(e, index)}
                      onDragOver={handleDragOver}
                      onDrop={(e) => handleDrop(e, index)}
                      onDragEnd={handleDragEnd}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="mt-1 flex flex-col items-center gap-1">
                            <GripVertical className="text-muted-foreground hover:text-foreground h-4 w-4 cursor-grab active:cursor-grabbing" />
                            <span className="text-muted-foreground text-xs">
                              {index + 1}
                            </span>
                          </div>

                          <div className="flex-1">
                            {block.type === "snippet" ? (
                              <div>
                                {block.snippetId && (
                                  <>
                                    {(() => {
                                      const snippet = snippets.find(
                                        (s) => s.id === block.snippetId,
                                      );
                                      return snippet ? (
                                        <div>
                                          <div className="mb-2 flex items-center gap-2">
                                            <FileText className="text-primary h-4 w-4" />
                                            <span className="font-medium">
                                              {snippet.name}
                                            </span>
                                            <div className="flex min-w-0 max-w-full flex-1 flex-wrap gap-1">
                                              {snippet.tags.map((tag) => (
                                                <Badge
                                                  key={tag}
                                                  variant="outline"
                                                  className="max-w-full shrink-0 truncate text-xs"
                                                >
                                                  {tag}
                                                </Badge>
                                              ))}
                                            </div>
                                          </div>
                                          <div className="bg-muted word-break overflow-hidden whitespace-pre-wrap break-words rounded p-2 font-mono text-sm">
                                            {snippet.body}
                                          </div>
                                        </div>
                                      ) : (
                                        <div className="text-destructive">
                                          Snippet not found
                                        </div>
                                      );
                                    })()}
                                  </>
                                )}
                              </div>
                            ) : (
                              <div>
                                <div className="mb-2 flex items-center gap-2">
                                  <Type className="text-blue-contrast h-4 w-4" />
                                  <span className="font-medium">Free Text</span>
                                </div>
                                <TextArea
                                  value={block.text || ""}
                                  onChange={(e) =>
                                    updateBlock(index, {
                                      ...block,
                                      text: e.target.value,
                                    })
                                  }
                                  placeholder="Enter your text here..."
                                  className="font-mono text-sm"
                                  rows={3}
                                />
                              </div>
                            )}
                          </div>

                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100"
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => duplicateBlock(index)}>
                                <Copy className="mr-2 h-4 w-4" />
                                Duplicate
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => removeBlock(index)}
                                className="text-destructive"
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Remove
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {!showPreview && (
          <div className="border-border bg-card w-80 overflow-auto border-l p-6">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between text-sm">
                    Live Preview
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSubstituteVariables(!substituteVariables)}
                      className="h-7 gap-1 bg-transparent text-xs"
                    >
                      <AtSign className="h-3 w-3" />
                      {substituteVariables ? "Variables" : "Values"}
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="bg-muted max-h-60 overflow-auto whitespace-pre-wrap rounded p-3 font-mono text-xs">
                    {renderFinalPrompt() || "Add blocks to see preview..."}
                  </div>
                </CardContent>
              </Card>

              {usedVariables.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Used Variables</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {usedVariables.map((varName) => {
                      const variable = variables.find((v) => v.name === varName);
                      return (
                        <div key={varName} className="flex items-start gap-2">
                          <code className="bg-primary/20 text-blue-contrast rounded px-2 py-1 font-mono text-xs">
                            @{varName}
                          </code>
                          {variable && (
                            <span className="text-muted-foreground text-xs">
                              {variable.value}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>

      <SnippetPicker
        open={snippetPickerOpen}
        onOpenChange={setSnippetPickerOpen}
        snippets={snippets}
        onSelect={addSnippetBlocks}
      />
    </div>
  );
}
