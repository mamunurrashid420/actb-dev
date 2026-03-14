"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/Dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Separator } from "@/components/ui/Separator";

interface HelpPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function HelpPanel({ open, onOpenChange }: HelpPanelProps) {
  const shortcuts = [
    { key: "/", description: "Focus search bar" },
    { key: "⌘/Ctrl + K", description: "Open command palette" },
    { key: "N", description: "Create new item (context-dependent)" },
    { key: "Esc", description: "Close dialogs and panels" },
  ];

  const variableTips = [
    "Use @variable_name to reference variables in snippets and prompts",
    "Variable names must start with a letter or underscore",
    "Choose descriptive names like 'customer_name' instead of 'name'",
    "Use tags to organize and filter your variables",
  ];

  const snippetTips = [
    "Keep snippets focused on a single purpose",
    "Use @ to insert variables while typing",
    "Add descriptive tags for easy filtering",
    "Preview your snippets to see how variables render",
  ];

  const promptTips = [
    "Build prompts by combining snippet blocks and free text",
    "Drag blocks to reorder them",
    "Use the live preview to see your final prompt",
    "Toggle variable substitution to test with real values",
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] max-w-4xl overflow-auto">
        <DialogHeader>
          <DialogTitle>Help & Shortcuts</DialogTitle>
          <DialogDescription>
            Learn how to use Prompt CMS effectively with these tips and shortcuts.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Keyboard Shortcuts */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Keyboard Shortcuts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3">
                {shortcuts.map((shortcut) => (
                  <div key={shortcut.key} className="flex items-center justify-between">
                    <span className="text-sm">{shortcut.description}</span>
                    <Badge variant="outline" className="font-mono">
                      {shortcut.key}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Separator />

          {/* Variables Tips */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Variables Best Practices</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {variableTips.map((tip, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <span className="text-primary mt-1">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Snippets Tips */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Snippets Best Practices</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {snippetTips.map((tip, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <span className="text-primary mt-1">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Prompts Tips */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Prompts Best Practices</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {promptTips.map((tip, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <span className="text-primary mt-1">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Syntax Reference */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Syntax Reference</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h4 className="mb-2 font-medium">Variable References</h4>
                  <div className="bg-muted rounded p-3 font-mono text-sm">
                    <div>@customer_name → References the customer_name variable</div>
                    <div>
                      @product_category → References the product_category variable
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="mb-2 font-medium">Variable Types</h4>
                  <div className="grid gap-2 text-sm">
                    <div className="flex justify-between">
                      <span>Text</span>
                      <span className="text-muted-foreground">
                        Single line text input
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Multiline</span>
                      <span className="text-muted-foreground">
                        Multi-line text area
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Enum</span>
                      <span className="text-muted-foreground">
                        Select from predefined options
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Boolean</span>
                      <span className="text-muted-foreground">True/false value</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Number</span>
                      <span className="text-muted-foreground">Numeric value</span>
                    </div>
                    <div className="flex justify-between">
                      <span>JSON</span>
                      <span className="text-muted-foreground">
                        JSON object or array
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
}
