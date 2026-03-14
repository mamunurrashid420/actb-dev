"use client";

import type React from "react";

import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { TextArea } from "@/components/ui/TextArea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/Sheet";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { X, Plus } from "lucide-react";
import type { Variable } from "@/types/variable";
import { useUiStore } from "@/hooks/use-ui-store";

interface VariableDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  variable: Variable | null;
  onSave: (variable: Omit<Variable, "id" | "createdAt" | "updatedAt">) => void;
  existingNames: string[];
}

const variableTypes = [
  { value: "text", label: "Text", description: "Single line text input" },
  {
    value: "multiline",
    label: "Multiline",
    description: "Multi-line text area",
  },
  {
    value: "enum",
    label: "Enum",
    description: "Select from predefined options",
  },
  { value: "boolean", label: "Boolean", description: "True/false value" },
  { value: "number", label: "Number", description: "Numeric value" },
  {
    value: "JSON",
    label: "JSON",
    description: "JSON object or array (string)",
  },
] as const;

export function VariableDrawer({
  open,
  onOpenChange,
  variable,
  onSave,
  existingNames,
}: VariableDrawerProps) {
  const [formData, setFormData] = useState({
    name: "",
    type: "text" as Variable["type"],
    defaultValue: "",
    description: "",
    tags: [] as string[],
  });
  const [newTag, setNewTag] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { setUnsaved, registerSaveHandler } = useUiStore();
  const saveRef = useRef<() => void>(() => {});

  // Reset form when drawer opens/closes or variable changes
  useEffect(() => {
    if (open) {
      if (variable) {
        setFormData({
          name: variable.name,
          type: variable.type,
          defaultValue: String(variable.defaultValue),
          description: variable.description,
          tags: [...(variable.tags || [])],
        });
      } else {
        setFormData({
          name: "",
          type: "text",
          defaultValue: "",
          description: "",
          tags: [],
        });
      }
      setErrors({});
    }
  }, [open, variable]);

  // Track unsaved changes while drawer is open
  useEffect(() => {
    const base = variable
      ? {
          name: variable.name,
          type: variable.type,
          defaultValue: String(variable.defaultValue),
          description: variable.description,
          tags: [...(variable.tags || [])],
        }
      : {
          name: "",
          type: "text" as Variable["type"],
          defaultValue: "",
          description: "",
          tags: [] as string[],
        };

    const tagsEqual =
      JSON.stringify([...(base.tags || [])].sort()) ===
      JSON.stringify([...(formData.tags || [])].sort());

    const dirty =
      formData.name !== base.name ||
      formData.type !== base.type ||
      String(formData.defaultValue) !== String(base.defaultValue) ||
      formData.description !== base.description ||
      !tagsEqual;

    setUnsaved("variables", open && dirty);
  }, [open, formData, variable, setUnsaved]);

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = "Name is required";
    } else if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(formData.name)) {
      newErrors.name =
        "Name must start with letter/underscore and contain only letters, numbers, and underscores";
    } else if (existingNames.includes(formData.name)) {
      newErrors.name = "A variable with this name already exists";
    }

    if (!formData.description.trim()) {
      newErrors.description = "Description is required";
    }

    if (
      formData.type === "number" &&
      formData.defaultValue &&
      isNaN(Number(formData.defaultValue))
    ) {
      newErrors.value = "Must be a valid number";
    }

    if (formData.type === "JSON" && formData.defaultValue) {
      try {
        JSON.parse(String(formData.defaultValue));
      } catch {
        newErrors.value = "Invalid JSON format";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, existingNames, setErrors]);

  const handleSave = useCallback(() => {
    if (validateForm()) {
      const dv =
        formData.type === "number"
          ? Number(formData.defaultValue)
          : formData.type === "boolean"
            ? formData.defaultValue === "true"
            : formData.defaultValue;
      onSave({
        name: formData.name,
        type: formData.type,
        defaultValue: dv as Variable["defaultValue"],
        description: formData.description,
        tags: formData.tags,
      });
      setUnsaved("variables", false);
    }
  }, [formData, onSave, setUnsaved, validateForm]);

  // Keep latest save handler in a ref to avoid re-registering on each change
  useEffect(() => {
    saveRef.current = handleSave;
  }, [handleSave]);

  // Register a stable auto-save handler only when drawer is open
  useEffect(() => {
    if (open) {
      const handler = () => saveRef.current();
      registerSaveHandler("variables", handler);
      return () => {
        registerSaveHandler("variables", () => {});
      };
    } else {
      // Ensure no-op when closed
      registerSaveHandler("variables", () => {});
    }
  }, [open, registerSaveHandler]);

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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag();
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[500px] sm:max-w-[500px]">
        <SheetHeader>
          <SheetTitle>{variable ? "Edit Variable" : "New Variable"}</SheetTitle>
          <SheetDescription>
            {variable
              ? "Update the variable details below."
              : "Create a new variable to use in snippets and prompts."}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 px-4 py-6">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              placeholder="customer_name"
              className={errors.name ? "border-destructive" : ""}
            />
            {errors.name && <p className="text-destructive text-sm">{errors.name}</p>}
            <p className="text-muted-foreground text-xs">
              Use letters, numbers, and underscores. Must start with letter or
              underscore.
            </p>
          </div>

          {/* Type */}
          <div className="space-y-2">
            <Label htmlFor="type">Type *</Label>
            <Select
              value={formData.type}
              onValueChange={(value: Variable["type"]) =>
                setFormData((prev) => ({ ...prev, type: value }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {variableTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div>
                      <div className="font-medium">{type.label}</div>
                      <div className="text-muted-foreground text-xs">
                        {type.description}
                      </div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Default Value */}
          <div className="space-y-2">
            <Label htmlFor="defaultValue">Default Value</Label>
            {formData.type === "multiline" || formData.type === "JSON" ? (
              <TextArea
                id="defaultValue"
                value={formData.defaultValue}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    defaultValue: e.target.value,
                  }))
                }
                placeholder={
                  formData.type === "JSON"
                    ? '{"key":"value"}'
                    : "Enter default value..."
                }
                rows={3}
                className={errors.value ? "border-destructive" : ""}
              />
            ) : formData.type === "boolean" ? (
              <Select
                value={formData.defaultValue}
                onValueChange={(value) =>
                  setFormData((prev) => ({ ...prev, defaultValue: value }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select true or false" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="true">true</SelectItem>
                  <SelectItem value="false">false</SelectItem>
                </SelectContent>
              </Select>
            ) : (
              <Input
                id="defaultValue"
                value={formData.defaultValue}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    defaultValue: e.target.value,
                  }))
                }
                placeholder={
                  formData.type === "number" ? "42" : "Enter default value..."
                }
                className={errors.value ? "border-destructive" : ""}
              />
            )}
            {errors.value && <p className="text-destructive text-sm">{errors.value}</p>}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description *</Label>
            <TextArea
              id="description"
              value={formData.description}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
              placeholder="Describe what this variable is used for..."
              rows={2}
              className={errors.description ? "border-destructive" : ""}
            />
            {errors.description && (
              <p className="text-destructive text-sm">{errors.description}</p>
            )}
          </div>

          {/* Tags */}
          <div className="space-y-2">
            <Label>Tags</Label>
            <div className="flex gap-2">
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Add a tag..."
                className="flex-1"
              />
              <Button type="button" onClick={addTag} size="sm" variant="outline">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {formData.tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
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
            )}
          </div>

          {/* Preview */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Variable Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-2 text-sm">
                Type @ to insert:{" "}
                <code className="bg-muted text-blue-contrast rounded px-2 py-1">
                  @{formData.name || "variable_name"}
                </code>
              </p>
              {formData.defaultValue && (
                <p className="text-muted-foreground text-xs">
                  Current value:{" "}
                  <code className="bg-muted rounded px-2 py-1">
                    {formData.defaultValue}
                  </code>
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            {variable ? "Update Variable" : "Create Variable"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
