import { ReactNode } from "react";

import type { Metadata } from "next";
import { Albert_Sans, Inter_Tight } from "next/font/google";
import { notFound } from "next/navigation";

import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";

import { Toaster } from "@/components/ui/sonner";
import { APP_CONFIG } from "@/config/app-config";
import { routing } from "@/i18n/routing";
import { getPreference } from "@/lib/cookies";
import { PreferencesStoreProvider } from "@/stores/preferences/preferences-provider";
import { THEME_MODE_VALUES, type ThemeMode } from "@/types/preferences/theme";

import "../globals.css";

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

type Props = {
  children: ReactNode;
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;

  // Ensure that the incoming `locale` is valid
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }

  // Enable static rendering
  setRequestLocale(locale);

  const messages = await getMessages();
  const themeMode = await getPreference<ThemeMode>(
    "theme_mode",
    THEME_MODE_VALUES,
    "light",
  );

  return (
    <html
      lang={locale}
      className={themeMode === "dark" ? "dark" : ""}
      suppressHydrationWarning
    >
      <body
        className={`${albertSans.variable} ${interTight.variable} min-h-screen antialiased`}
      >
        <NextIntlClientProvider messages={messages}>
          <PreferencesStoreProvider themeMode={themeMode}>
            {children}
            <Toaster />
          </PreferencesStoreProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
