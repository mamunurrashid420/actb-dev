const currentYear = new Date().getFullYear();

export const APP_CONFIG = {
  name: "actbi",
  version: process.env.NEXT_PUBLIC_APP_VERSION ?? "1.0.0",
  copyright: `© ${currentYear}, actbi.`,
  meta: {
    title: "Actbi - Modern Next.js Dashboard Starter Template",
    description:
      "Actbi is a modern, open-source dashboard starter template built with Next.js 15, Tailwind CSS v4, and shadcn/ui. Perfect for SaaS apps, admin panels, and internal tools—fully customizable and production-ready.",
  },
};
