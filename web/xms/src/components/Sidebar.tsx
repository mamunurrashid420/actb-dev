"use client";

import { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import {
  Database,
  FileText,
  MessageSquare,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useUiStore } from "@/hooks/use-ui-store";

import type { Workspace } from "@/hooks/use-ui-store";

interface SidebarProps {
  activeWorkspace: string;
  onWorkspaceChange: (workspace: Workspace) => void;
}

type WorkspaceNavItem = {
  id: Workspace;
  label: string;
  icon: typeof Database;
  description: string;
};
const workspaces: WorkspaceNavItem[] = [
  {
    id: "variables",
    label: "Variables",
    icon: Database,
    description: "Define reusable variables",
  },
  {
    id: "snippets",
    label: "Snippets",
    icon: FileText,
    description: "Create text blocks with variables",
  },
  {
    id: "prompts",
    label: "Prompts",
    icon: MessageSquare,
    description: "Compose prompts from snippets",
  },
];

export function Sidebar({ activeWorkspace, onWorkspaceChange }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { setHelpPanelOpen } = useUiStore();

  return (
    <div
      className={cn(
        "bg-sidebar border-sidebar-border fixed left-0 top-0 z-50 h-full border-r transition-all duration-300",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="border-sidebar-border border-b p-4">
          <div className="flex items-center justify-between">
            {!collapsed ? (
              <div className="flex flex-col items-start gap-2">
                <Image
                  src="/pinax-blue-logo.svg"
                  alt="Pinax"
                  width={120}
                  height={120}
                  className="h-[120px] w-[120px]"
                />
                <h1 className="text-sidebar-foreground text-xl font-semibold leading-tight">
                  Context Management System
                </h1>
              </div>
            ) : null}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCollapsed(!collapsed)}
              className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4">
          <div className="space-y-2">
            {workspaces.map((workspace) => {
              const Icon = workspace.icon;
              const isActive = activeWorkspace === workspace.id;

              return (
                <Button
                  key={workspace.id}
                  variant={isActive ? "default" : "ghost"}
                  className={cn(
                    "w-full justify-start gap-3 text-left",
                    isActive
                      ? "bg-sidebar-primary text-sidebar-primary-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    collapsed ? "h-12 px-3" : "min-h-[72px] py-3",
                  )}
                  onClick={() => onWorkspaceChange(workspace.id)}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" />
                  {!collapsed && (
                    <div className="flex min-w-0 flex-col items-start">
                      <span className="font-medium">{workspace.label}</span>
                      <span className="whitespace-normal break-words text-xs leading-snug opacity-70">
                        {workspace.description}
                      </span>
                    </div>
                  )}
                </Button>
              );
            })}
          </div>
        </nav>

        {/* Footer */}
        <div className="border-sidebar-border border-t p-4">
          <Button
            variant="ghost"
            onClick={() => setHelpPanelOpen(true)}
            className={cn(
              "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground w-full justify-start gap-3",
              collapsed && "px-3",
            )}
          >
            <HelpCircle className="h-4 w-4 flex-shrink-0" />
            {!collapsed && <span className="text-sm">Help & Shortcuts</span>}
          </Button>
        </div>
      </div>
    </div>
  );
}
