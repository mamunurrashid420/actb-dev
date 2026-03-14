// Re-export shared utilities - SSOT is @actbi/shared
export { cn } from "@actbi/shared";

// XMS-specific utilities
export function generateId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function generateIncrementalName(
  baseName: string,
  existingNames: string[],
): string {
  const pattern = new RegExp(`^${baseName}_(\\d+)$`);
  const indices = existingNames
    .map((name) => {
      const match = name.match(pattern);
      return match ? Number(match[1]) : null;
    })
    .filter((value): value is number => value !== null);
  const nextIndex = indices.length > 0 ? Math.max(...indices) + 1 : 0;
  return `${baseName}_${nextIndex}`;
}
