"use client";

import { useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { VariablesWorkspace } from "@/components/workspaces/VariablesWorkspace";
import { SnippetsWorkspace } from "@/components/workspaces/SnippetsWorkspace";
import { PromptsWorkspace } from "@/components/workspaces/PromptsWorkspace";
import { CommandPalette } from "@/components/CommandPalette";
import { HelpPanel } from "@/components/HelpPanel";
// Page no longer mounts its own ToastProvider; global Toaster is in layout
import { useToast } from "@/hooks/use-toast";
import { useUiStore, type Workspace } from "@/hooks/use-ui-store";

export default function HomePage() {
  const {
    activeWorkspace,
    setActiveWorkspace,
    commandPaletteOpen,
    setCommandPaletteOpen,
    helpPanelOpen,
    setHelpPanelOpen,
  } = useUiStore();
  const { toast } = useToast();
  const { unsaved, saveHandlers } = useUiStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Command palette (Cmd/Ctrl + K)
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }

      // Focus search (/)
      if (e.key === "/" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const target = e.target as HTMLElement;
        if (target.tagName !== "INPUT" && target.tagName !== "TEXTAREA") {
          e.preventDefault();
          const searchInput = document.querySelector(
            'input[placeholder*="Search"]',
          ) as HTMLInputElement;
          if (searchInput) {
            searchInput.focus();
          }
        }
      }

      // New item (N)
      if (e.key === "n" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const target = e.target as HTMLElement;
        if (target.tagName !== "INPUT" && target.tagName !== "TEXTAREA") {
          e.preventDefault();
          handleNewItem();
        }
      }

      // Escape to close dialogs
      if (e.key === "Escape") {
        setCommandPaletteOpen(false);
        setHelpPanelOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [activeWorkspace, setCommandPaletteOpen, setHelpPanelOpen]);

  const handleNewItem = () => {
    const newButton = document.querySelector(
      'button:has(svg + *):contains("New")',
    ) as HTMLButtonElement;
    if (newButton) {
      newButton.click();
    }
  };

  const maybeAutoSave = async () => {
    const current = activeWorkspace;
    if (unsaved[current]) {
      const handler = saveHandlers[current];
      if (handler) {
        await handler();
        toast({ title: "Saved changes", description: `Saved ${current}` });
      }
    }
  };

  const handleNewVariable = async () => {
    await maybeAutoSave();
    setActiveWorkspace("variables");
    setTimeout(() => {
      const newVariableButton = document.querySelector(
        'button:contains("New Variable")',
      ) as HTMLButtonElement;
      if (newVariableButton) {
        newVariableButton.click();
      }
    }, 100);
    toast({
      title: "Creating new variable",
      description: "Switched to Variables workspace",
    });
  };

  const handleNewSnippet = async () => {
    await maybeAutoSave();
    setActiveWorkspace("snippets");
    setTimeout(() => {
      const newSnippetButton = document.querySelector(
        'button:contains("New Snippet")',
      ) as HTMLButtonElement;
      if (newSnippetButton) {
        newSnippetButton.click();
      }
    }, 100);
    toast({
      title: "Creating new snippet",
      description: "Switched to Snippets workspace",
    });
  };

  const handleNewPrompt = async () => {
    await maybeAutoSave();
    setActiveWorkspace("prompts");
    setTimeout(() => {
      const newPromptButton = document.querySelector(
        'button:contains("New Prompt")',
      ) as HTMLButtonElement;
      if (newPromptButton) {
        newPromptButton.click();
      }
    }, 100);
    toast({
      title: "Creating new prompt",
      description: "Switched to Prompts workspace",
    });
  };

  const renderWorkspace = () => {
    switch (activeWorkspace) {
      case "variables":
        return <VariablesWorkspace />;
      case "snippets":
        return <SnippetsWorkspace />;
      case "prompts":
        return <PromptsWorkspace />;
      default:
        return <VariablesWorkspace />;
    }
  };

  return (
    <div className="bg-background flex h-screen">
      <Sidebar
        activeWorkspace={activeWorkspace}
        onWorkspaceChange={async (w: Workspace) => {
          await maybeAutoSave();
          setActiveWorkspace(w);
        }}
      />

      <main className="ml-64 flex-1 overflow-hidden">
        <div className="h-full">{renderWorkspace()}</div>
      </main>

      {/* Global Components */}
      <CommandPalette
        open={commandPaletteOpen}
        onOpenChange={setCommandPaletteOpen}
        onNavigate={async (w: Workspace) => {
          await maybeAutoSave();
          setActiveWorkspace(w);
        }}
        onNewVariable={handleNewVariable}
        onNewSnippet={handleNewSnippet}
        onNewPrompt={handleNewPrompt}
        onShowHelp={() => setHelpPanelOpen(true)}
      />

      <HelpPanel open={helpPanelOpen} onOpenChange={setHelpPanelOpen} />
    </div>
  );
}
