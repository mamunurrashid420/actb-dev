"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/routing";

export default function NotFound() {
  const t = useTranslations("common");

  return (
    <div className="flex h-dvh flex-col items-center justify-center space-y-2 text-center">
      <h1 className="text-2xl font-semibold">Page not found.</h1>
      <p className="text-muted-foreground">
        The page you are looking for could not be found.
      </p>
      <Link replace href="/dashboard">
        <Button variant="outline">{t("back")}</Button>
      </Link>
    </div>
  );
}
