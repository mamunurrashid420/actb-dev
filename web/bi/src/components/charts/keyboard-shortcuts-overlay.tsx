"use client";

import React, { useEffect, useState } from "react";

import { Command, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { CHART_SHORTCUTS } from "@/types/charts/keyboard";

interface KeyboardShortcutsOverlayProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const KeyboardShortcutsOverlay: React.FC<KeyboardShortcutsOverlayProps> = ({
  open,
  onOpenChange,
}) => {
  const [isMac, setIsMac] = useState(false);

  useEffect(() => {
    setIsMac(navigator.platform.toUpperCase().indexOf("MAC") >= 0);
  }, []);

  const formatKey = (key: string): string => {
    if (isMac) {
      return key.replace("ctrl", "⌘").replace("alt", "⌥").replace("shift", "⇧");
    }
    return key;
  };

  const parseShortcut = (shortcut: string) => {
    const parts = shortcut.split("+");
    return parts.map((part) => part.trim());
  };

  // Group shortcuts by category
  const groupedShortcuts = CHART_SHORTCUTS.reduce(
    (acc, shortcut) => {
      if (!acc[shortcut.category]) {
        acc[shortcut.category] = [];
      }
      acc[shortcut.category].push(shortcut);
      return acc;
    },
    {} as Record<string, typeof CHART_SHORTCUTS>,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Command className="h-5 w-5" />
            Keyboard Shortcuts
          </DialogTitle>
          <DialogDescription>
            Use these keyboard shortcuts to navigate and interact with charts
            efficiently
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[500px] pr-4">
          <div className="space-y-6">
            {Object.entries(groupedShortcuts).map(([category, shortcuts]) => (
              <div key={category}>
                <h3 className="mb-3 text-sm font-semibold capitalize">{category}</h3>
                <div className="space-y-2">
                  {shortcuts.map((shortcut, idx) => (
                    <div
                      key={idx}
                      className="hover:bg-muted/50 flex items-center justify-between rounded-lg px-3 py-2 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium">{shortcut.description}</p>
                        {shortcut.hint && (
                          <p className="text-muted-foreground mt-0.5 text-xs">
                            {shortcut.hint}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        {parseShortcut(formatKey(shortcut.key)).map((key, keyIdx) => (
                          <React.Fragment key={keyIdx}>
                            {keyIdx > 0 && (
                              <span className="text-muted-foreground text-xs">+</span>
                            )}
                            <Badge
                              variant="secondary"
                              className="px-2 py-0.5 font-mono text-xs"
                            >
                              {key}
                            </Badge>
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                {category !==
                  Object.keys(groupedShortcuts)[
                    Object.keys(groupedShortcuts).length - 1
                  ] && <Separator className="mt-4" />}
              </div>
            ))}
          </div>
        </ScrollArea>

        <div className="flex items-center justify-between border-t pt-4">
          <p className="text-muted-foreground text-xs">
            Press{" "}
            <Badge variant="outline" className="mx-1 font-mono text-xs">
              ?
            </Badge>{" "}
            to toggle this overlay
          </p>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            <X className="mr-1 h-4 w-4" />
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
