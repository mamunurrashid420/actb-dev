import { ReactNode } from "react";

import type { Metadata } from "next";
import { Albert_Sans, Inter_Tight } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import { APP_CONFIG } from "@/config/app-config";
import { getPreference } from "@/lib/preferences";
import { PreferencesStoreProvider } from "@/stores/preferences/preferences-provider";
import { THEME_MODE_VALUES, type ThemeMode } from "@/types/preferences/theme";

import "./globals.css";

// Corporate theme fonts
const albertSans = Albert_Sans({
  subsets: ["latin"],
  variable: "--font-albert-sans",
});

const interTight = Inter_Tight({
  subsets: ["latin"],
  variable: "--font-inter-tight",
});

export const metadata: Metadata = {
  title: APP_CONFIG.meta.title,
  description: APP_CONFIG.meta.description,
};

export default async function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  const themeMode = await getPreference<ThemeMode>(
    "theme_mode",
    THEME_MODE_VALUES,
    "light",
  );

  return (
    <html
      lang="en"
      className={themeMode === "dark" ? "dark" : ""}
      suppressHydrationWarning
    >
      <body
        className={`${albertSans.variable} ${interTight.variable} min-h-screen antialiased`}
      >
        <PreferencesStoreProvider themeMode={themeMode}>
          {children}
          <Toaster />
        </PreferencesStoreProvider>
      </body>
    </html>
  );
}
