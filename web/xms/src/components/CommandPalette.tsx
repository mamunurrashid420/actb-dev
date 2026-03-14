"use client";

import { useState } from "react";
import { Dialog, DialogContent } from "@/components/ui/Dialog";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/Command";
import { Badge } from "@/components/ui/Badge";
import { Database, FileText, MessageSquare, Plus, HelpCircle } from "lucide-react";
import type { Workspace } from "@/hooks/use-ui-store";
// local state, no zustand

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onNavigate: (workspace: Workspace) => void;
  onNewVariable: () => void;
  onNewSnippet: () => void;
  onNewPrompt: () => void;
  onShowHelp: () => void;
}

export function CommandPalette({
  open,
  onOpenChange,
  onNavigate,
  onNewVariable,
  onNewSnippet,
  onNewPrompt,
  onShowHelp,
}: CommandPaletteProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const commands = [
    // Navigation
    {
      id: "nav-variables",
      title: "Go to Variables",
      description: "Manage your variables",
      icon: Database,
      action: () => onNavigate("variables"),
      group: "Navigation",
    },
    {
      id: "nav-snippets",
      title: "Go to Snippets",
      description: "Manage your snippets",
      icon: FileText,
      action: () => onNavigate("snippets"),
      group: "Navigation",
    },
    {
      id: "nav-prompts",
      title: "Go to Prompts",
      description: "Manage your prompts",
      icon: MessageSquare,
      action: () => onNavigate("prompts"),
      group: "Navigation",
    },
    // Create actions
    {
      id: "new-variable",
      title: "New Variable",
      description: "Create a new variable",
      icon: Plus,
      action: onNewVariable,
      group: "Create",
      shortcut: "N",
    },
    {
      id: "new-snippet",
      title: "New Snippet",
      description: "Create a new snippet",
      icon: Plus,
      action: onNewSnippet,
      group: "Create",
      shortcut: "N",
    },
    {
      id: "new-prompt",
      title: "New Prompt",
      description: "Create a new prompt",
      icon: Plus,
      action: onNewPrompt,
      group: "Create",
      shortcut: "N",
    },
    // Help
    {
      id: "help",
      title: "Help & Shortcuts",
      description: "View keyboard shortcuts and tips",
      icon: HelpCircle,
      action: onShowHelp,
      group: "Help",
    },
  ];

  const filteredCommands = commands.filter(
    (command) =>
      command.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      command.description.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const groupedCommands = filteredCommands.reduce(
    (acc, command) => {
      if (!acc[command.group]) {
        acc[command.group] = [];
      }
      acc[command.group].push(command);
      return acc;
    },
    {} as Record<string, typeof commands>,
  );

  const handleSelect = (command: (typeof commands)[0]) => {
    command.action();
    onOpenChange(false);
    setSearchQuery("");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl p-0">
        <Command>
          <CommandInput
            placeholder="Type a command or search..."
            value={searchQuery}
            onValueChange={setSearchQuery}
            className="border-none"
          />
          <CommandList className="max-h-96">
            <CommandEmpty>No commands found.</CommandEmpty>
            {Object.entries(groupedCommands).map(([group, commands]) => (
              <CommandGroup key={group} heading={group}>
                {commands.map((command) => {
                  const Icon = command.icon;
                  return (
                    <CommandItem
                      key={command.id}
                      onSelect={() => handleSelect(command)}
                      className="flex items-center gap-3 p-3"
                    >
                      <Icon className="text-muted-foreground h-4 w-4" />
                      <div className="flex-1">
                        <div className="font-medium">{command.title}</div>
                        <div className="text-muted-foreground text-xs">
                          {command.description}
                        </div>
                      </div>
                      {command.shortcut && (
                        <Badge variant="outline" className="text-xs">
                          {command.shortcut}
                        </Badge>
                      )}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
