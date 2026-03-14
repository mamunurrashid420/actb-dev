"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import { Plus, Search, Filter, MoreHorizontal, Edit, Copy, Trash2 } from "lucide-react";
import { VariableDrawer } from "@/components/VariableDrawer";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";

import { useVariables } from "@/hooks/use-variables";
import type { Variable } from "@/types/variable";

export function VariablesWorkspace() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const toggleTag = (tag: string) =>
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  const clearTags = () => setSelectedTags([]);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingVariable, setEditingVariable] = useState<Variable | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [variableToDelete, setVariableToDelete] = useState<Variable | null>(null);
  const { variablesQuery, createVariable, updateVariable, deleteVariable } =
    useVariables();
  const variables: Variable[] = (variablesQuery.data || []).map((v) => ({
    ...v,
    tags: v.tags || [],
  }));

  // Get all unique tags
  const allTags = Array.from(new Set(variables.flatMap((v) => v.tags || [])));

  // Filter variables based on search and tags
  const filteredVariables = variables.filter((variable) => {
    const matchesSearch =
      variable.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      variable.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (variable.tags || []).some((tag) =>
        tag.toLowerCase().includes(searchQuery.toLowerCase()),
      );

    const matchesTags =
      selectedTags.length === 0 ||
      selectedTags.some((tag) => (variable.tags || []).includes(tag));

    return matchesSearch && matchesTags;
  });

  const handleNewVariable = () => {
    setEditingVariable(null);
    setDrawerOpen(true);
  };

  const handleEditVariable = (variable: Variable) => {
    setEditingVariable(variable);
    setDrawerOpen(true);
  };

  const handleDuplicateVariable = async (variable: Variable) => {
    await createVariable({
      name: `${variable.name}_copy`,
      type: variable.type,
      defaultValue: variable.defaultValue,
      description: variable.description,
      tags: variable.tags,
    });
  };

  const handleDeleteVariable = (variable: Variable) => {
    setVariableToDelete(variable);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (variableToDelete) {
      await deleteVariable(variableToDelete.id);
      setVariableToDelete(null);
    }
    setDeleteDialogOpen(false);
  };

  const handleSaveVariable = async (
    variable: Omit<Variable, "id" | "createdAt" | "updatedAt">,
  ) => {
    if (editingVariable) {
      await updateVariable({
        id: editingVariable.id,
        ...variable,
      });
    } else {
      await createVariable({
        ...variable,
      });
    }

    setDrawerOpen(false);
    setEditingVariable(null);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-border bg-card border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-foreground text-2xl font-semibold">Variables</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Define variables to reference inside snippets and prompts with @varName
            </p>
          </div>
          <Button onClick={handleNewVariable} className="gap-2">
            <Plus className="h-4 w-4" />
            New Variable
          </Button>
        </div>

        {/* Search and filters */}
        <div className="mt-4 flex items-center gap-4">
          <div className="relative max-w-md flex-1">
            <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform" />
            <Input
              placeholder="Search variables..."
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
              <DropdownMenuItem onClick={clearTags}>Clear filters</DropdownMenuItem>
              {allTags.map((tag) => (
                <DropdownMenuItem key={tag} onClick={() => toggleTag(tag)}>
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

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {filteredVariables.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="max-w-md">
              <h3 className="text-foreground mb-2 text-lg font-medium">
                {variables.length === 0
                  ? "No variables yet"
                  : "No variables match your search"}
              </h3>
              <p className="text-muted-foreground mb-6">
                {variables.length === 0
                  ? "Variables let you reuse context. Create your first with 'New Variable'."
                  : "Try adjusting your search terms or filters."}
              </p>
              {variables.length === 0 && (
                <Button onClick={handleNewVariable} className="gap-2">
                  <Plus className="h-4 w-4" />
                  Create your first variable
                </Button>
              )}
            </div>
          </div>
        ) : (
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Default Value</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Last edited</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredVariables.map((variable) => (
                  <TableRow key={variable.id} className="hover:bg-muted/50">
                    <TableCell className="font-medium">
                      <span className="text-blue-contrast font-mono">
                        @{variable.name}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {variable.type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <code className="bg-muted rounded px-2 py-1 text-xs">
                        {String(variable.defaultValue)}
                      </code>
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <span className="text-muted-foreground line-clamp-2 text-sm">
                        {variable.description}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {(variable.tags || []).map((tag) => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {variable.updatedAt.split("T")[0]}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => handleEditVariable(variable)}
                          >
                            <Edit className="mr-2 h-4 w-4" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => handleDuplicateVariable(variable)}
                          >
                            <Copy className="mr-2 h-4 w-4" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => handleDeleteVariable(variable)}
                            className="text-destructive"
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}
      </div>

      {/* Variable Editor Drawer */}
      <VariableDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        variable={editingVariable}
        onSave={handleSaveVariable}
        existingNames={variables
          .filter((v) => v.id !== editingVariable?.id)
          .map((v) => v.name)}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={confirmDelete}
        title="Delete Variable"
        description={`Are you sure you want to delete "@${variableToDelete?.name}"? This action cannot be undone.`}
      />
    </div>
  );
}
