"use client";

import React from "react";

interface MarkdownRendererProps {
  markdown?: string | null;
}

export function MarkdownRenderer({ markdown = "" }: MarkdownRendererProps) {
  const renderMarkdown = (text: string) => {
    // Handle null, undefined, or empty text
    if (!text || typeof text !== "string") {
      return [
        <p key="empty" className="text-muted-foreground text-sm">
          No content available
        </p>,
      ];
    }

    // Simple markdown parser for basic formatting
    const lines = text.split("\n");
    const elements: React.ReactNode[] = [];

    lines.forEach((line, index) => {
      // Headers
      if (line.startsWith("## ")) {
        const keyLine = line.substring(0, 20).replace(/\s+/g, "-").toLowerCase();
        elements.push(
          <h2
            key={`h2-${keyLine}-${index.toString().padStart(5, "0")}`}
            className="text-foreground mb-2 mt-3 text-base font-bold"
          >
            {line.replace("## ", "")}
          </h2>,
        );
      } else if (line.startsWith("### ")) {
        const keyLine = line.substring(0, 20).replace(/\s+/g, "-").toLowerCase();
        elements.push(
          <h3
            key={`h3-${keyLine}-${index.toString().padStart(5, "0")}`}
            className="text-foreground mb-1 mt-2 text-sm font-semibold"
          >
            {line.replace("### ", "")}
          </h3>,
        );
      }
      // Bold text
      else if (line.includes("**")) {
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        const keyLine = line.substring(0, 20).replace(/\s+/g, "-").toLowerCase();
        elements.push(
          <p
            key={`p-bold-${keyLine}-${index.toString().padStart(5, "0")}`}
            className="text-foreground mb-1 text-sm leading-relaxed"
          >
            {parts.map((part, partIndex) => {
              if (part.startsWith("**") && part.endsWith("**")) {
                return (
                  <strong
                    key={`strong-${keyLine}-${(index * 1000 + partIndex).toString().padStart(6, "0")}`}
                    className="text-primary font-semibold"
                  >
                    {part.slice(2, -2)}
                  </strong>
                );
              }
              return (
                <span
                  key={`span-${keyLine}-${(index * 1000 + partIndex).toString().padStart(6, "0")}`}
                >
                  {part}
                </span>
              );
            })}
          </p>,
        );
      }
      // List items
      else if (line.startsWith("- ")) {
        const keyLine = line
          .replace("- ", "")
          .substring(0, 20)
          .replace(/\s+/g, "-")
          .toLowerCase();
        elements.push(
          <li
            key={`li-${keyLine}-${index.toString().padStart(5, "0")}`}
            className="text-foreground ml-4 list-disc text-sm leading-relaxed"
          >
            {line.replace("- ", "")}
          </li>,
        );
      }
      // Regular paragraph
      else if (line.trim()) {
        const keyLine = line.substring(0, 20).replace(/\s+/g, "-").toLowerCase();
        elements.push(
          <p
            key={`p-regular-${keyLine}-${index.toString().padStart(5, "0")}`}
            className="text-foreground mb-1 text-sm leading-relaxed"
          >
            {line}
          </p>,
        );
      } else {
        elements.push(<br key={`br-${index.toString().padStart(5, "0")}`} />);
      }
    });

    return elements;
  };

  return <div className="space-y-2">{renderMarkdown(markdown ?? "")}</div>;
}
