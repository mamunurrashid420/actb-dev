import { ReactNode } from "react";

// Root layout - minimal wrapper for locale-based routing
// The actual layout with providers is in [locale]/layout.tsx
export default function RootLayout({ children }: { children: ReactNode }) {
  return children;
}
