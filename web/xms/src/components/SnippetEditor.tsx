"use client";

import type React from "react";

import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { TextArea } from "@/components/ui/TextArea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/Popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/Command";
import { Save, Eye, X, Plus, AtSign } from "lucide-react";
import { useUiStore } from "@/hooks/use-ui-store";
import type { Snippet } from "@/types/snippet";

interface Variable {
  name: string;
  description: string;
}

interface SnippetEditorProps {
  snippet: Snippet;
  variables: Variable[];
  onSave: (snippet: Snippet) => void;
}

export function SnippetEditor({ snippet, variables, onSave }: SnippetEditorProps) {
  const [formData, setFormData] = useState({
    name: snippet.name,
    body: snippet.body,
    tags: [...snippet.tags],
  });
  const [newTag, setNewTag] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [variableMenuOpen, setVariableMenuOpen] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  // removed unused cursor position state
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { setUnsaved, registerSaveHandler } = useUiStore();
  const saveRef = useRef<() => void>(() => {});

  // Update form when snippet changes
  useEffect(() => {
    setFormData({
      name: snippet.name,
      body: snippet.body,
      tags: [...snippet.tags],
    });
    setHasChanges(false);
  }, [snippet]);

  // Track changes
  useEffect(() => {
    const hasNameChange = formData.name !== snippet.name;
    const hasBodyChange = formData.body !== snippet.body;
    const hasTagsChange =
      JSON.stringify(formData.tags.sort()) !== JSON.stringify(snippet.tags.sort());
    const dirty = hasNameChange || hasBodyChange || hasTagsChange;
    setHasChanges(dirty);
    setUnsaved("snippets", dirty);
  }, [formData, snippet, setUnsaved]);

  const handleSave = useCallback(() => {
    const wordCount = formData.body.trim().split(/\s+/).filter(Boolean).length;
    const updatedSnippet: Snippet = {
      ...snippet,
      name: formData.name,
      body: formData.body,
      tags: formData.tags,
      updatedAt: new Date().toISOString().split("T")[0],
      wordCount,
    };
    onSave(updatedSnippet);
    setHasChanges(false);
    setUnsaved("snippets", false);
  }, [formData, snippet, onSave, setUnsaved]);

  // Keep latest save handler in a ref to avoid re-registering on each change
  useEffect(() => {
    saveRef.current = handleSave;
  }, [handleSave]);

  // Register a stable auto-save handler while editor is mounted
  useEffect(() => {
    const handler = () => saveRef.current();
    registerSaveHandler("snippets", handler);
    return () => {
      registerSaveHandler("snippets", () => {});
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

  const insertVariable = (variableName: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = formData.body;
    const before = text.substring(0, start);
    const after = text.substring(end);

    // If the user just typed '@' (or started typing a mention), replace that mention instead of appending
    const mentionMatch = before.match(/@[\w]*$/);
    const replaceStart = mentionMatch ? start - mentionMatch[0].length : start;

    const newText = text.substring(0, replaceStart) + `@${variableName}` + after;

    setFormData((prev) => ({ ...prev, body: newText }));
    setVariableMenuOpen(false);

    // Set cursor position after the inserted variable
    setTimeout(() => {
      const newPosition = replaceStart + variableName.length + 1;
      textarea.setSelectionRange(newPosition, newPosition);
      textarea.focus();
    }, 0);
  };

  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "@") {
      setTimeout(() => setVariableMenuOpen(true), 0);
    }
  };

  const renderPreview = () => {
    let preview = formData.body;
    variables.forEach((variable) => {
      const regex = new RegExp(`@${variable.name}`, "g");
      preview = preview.replace(
        regex,
        `<span class="bg-primary/20 text-blue-contrast px-1 rounded font-mono text-sm">@${variable.name}</span>`,
      );
    });
    return { __html: preview.replace(/\n/g, "<br>") };
  };

  const getUsedVariables = () => {
    const matches = formData.body.match(/@\w+/g) || [];
    return Array.from(new Set(matches.map((match) => match.substring(1))));
  };

  const usedVariables = getUsedVariables();

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-border bg-card border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="max-w-md flex-1">
            <Input
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              className="border-none bg-transparent px-0 text-lg font-medium focus-visible:ring-0"
              placeholder="Snippet name..."
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPreview(!showPreview)}
              className="gap-2 bg-transparent"
            >
              <Eye className="h-4 w-4" />
              {showPreview ? "Edit" : "Preview"}
            </Button>
            <Button onClick={handleSave} disabled={!hasChanges} className="gap-2">
              <Save className="h-4 w-4" />
              Save
            </Button>
          </div>
        </div>

        {/* Tags */}
        <div className="mt-4 flex items-center gap-2">
          <div className="flex flex-wrap gap-2">
            {formData.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="gap-1">
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
          <div className="flex gap-2">
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

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Editor */}
        <div className="flex-1 overflow-auto p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="body" className="text-base font-medium">
                Content
              </Label>
              <Popover open={variableMenuOpen} onOpenChange={setVariableMenuOpen}>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2 bg-transparent">
                    <AtSign className="h-4 w-4" />
                    Insert Variable
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80 p-0" align="end">
                  <Command>
                    <CommandInput placeholder="Search variables..." />
                    <CommandList>
                      <CommandEmpty>No variables found.</CommandEmpty>
                      <CommandGroup>
                        {variables.map((variable) => (
                          <CommandItem
                            key={variable.name}
                            onSelect={() => insertVariable(variable.name)}
                          >
                            <div>
                              <div className="text-blue-contrast font-mono">
                                @{variable.name}
                              </div>
                              <div className="text-muted-foreground text-xs">
                                {variable.description}
                              </div>
                            </div>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            {showPreview ? (
              <Card className="min-h-[400px]">
                <CardContent className="p-6">
                  <div
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={renderPreview()}
                    style={{ whiteSpace: "pre-wrap" }}
                  />
                </CardContent>
              </Card>
            ) : (
              <TextArea
                ref={textareaRef}
                id="body"
                value={formData.body}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, body: e.target.value }))
                }
                onKeyDown={handleTextareaKeyDown}
                placeholder="Type your snippet content here... Use @ to insert variables."
                className="min-h-[400px] font-mono text-sm"
              />
            )}

            <div className="text-muted-foreground text-xs">
              {formData.body.trim().split(/\s+/).filter(Boolean).length} words
            </div>
          </div>
        </div>

        {/* Metadata Sidebar */}
        <div className="border-border bg-card w-80 overflow-auto border-l p-6">
          <div className="space-y-6">
            {/* Used Variables */}
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
                            {variable.description}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            )}

            {/* Metadata */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created by</span>
                  <span>You</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Updated</span>
                  <span>{snippet.updatedAt}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Word count</span>
                  <span>
                    {formData.body.trim().split(/\s+/).filter(Boolean).length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Used in prompts</span>
                  <span>{snippet.usedInPrompts}</span>
                </div>
              </CardContent>
            </Card>

            {/* Available Variables */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Available Variables</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {variables.map((variable) => (
                  <button
                    key={variable.name}
                    onClick={() => insertVariable(variable.name)}
                    className="hover:bg-muted w-full rounded p-2 text-left transition-colors"
                  >
                    <div className="text-blue-contrast font-mono text-xs">
                      @{variable.name}
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {variable.description}
                    </div>
                  </button>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
