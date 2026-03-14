import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge class names using tailwind-merge and clsx */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Generate a random UUID (v4) */
export function generateUUID(): string {
  const canUseNativeUUID =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function";
  if (canUseNativeUUID) {
    return crypto.randomUUID();
  }

  // Fallback implementation for environments that don't support crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** Get initials from a name (max 2 characters) */
export function getInitials(name: string): string {
  if (!name) return "";
  return name
    .split(" ")
    .map((part) => part.charAt(0).toUpperCase())
    .join("")
    .substring(0, 2);
}

export interface FormatCurrencyOptions {
  currency?: string;
  noDecimals?: boolean;
}

/** Format a number as currency */
export function formatCurrency(
  amount: number,
  options: FormatCurrencyOptions | string = "USD",
): string {
  // Handle backward compatibility where the second parameter could be a string
  const currency = typeof options === "string" ? options : (options.currency ?? "USD");
  const noDecimals = typeof options === "object" && options.noDecimals === true;

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: noDecimals ? 0 : undefined,
    maximumFractionDigits: noDecimals ? 0 : undefined,
  }).format(amount);
}
