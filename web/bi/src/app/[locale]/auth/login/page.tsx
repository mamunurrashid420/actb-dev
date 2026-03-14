"use client";

import { useEffect, useState } from "react";

import { CircleHelp, LogIn } from "lucide-react";
import { useTranslations } from "next-intl";
import { useParams } from "next/navigation";

import { LoginForm, type LoginPrefill } from "@/components/auth/login-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

const DEMO_ACCOUNTS: Array<{
  label: string;
  email: string;
  password: string;
  note?: string;
}> = [
  {
    label: "Global App Admin",
    email: "root@actbi.ai",
    password: "Passw0rd!",
  },
  {
    label: "Tenant Superadmin",
    email: "superadmin@actbi.ai",
    password: "Passw0rd!",
  },
  {
    label: "Tenant Admin",
    email: "admin@actbi.ai",
    password: "Passw0rd!",
  },
  {
    label: "Tenant Creator",
    email: "creator@actbi.ai",
    password: "Passw0rd!",
  },
  {
    label: "Tenant Viewer",
    email: "viewer@actbi.ai",
    password: "Passw0rd!",
  },
];

export default function LoginV2() {
  const t = useTranslations("auth");
  const params = useParams();
  const locale = typeof params?.locale === "string" ? params.locale : "en";
  const [prefill, setPrefill] = useState<LoginPrefill | undefined>(undefined);

  // Preserve invite hash flow by forwarding to accept-invite page.
  useEffect(() => {
    const hash = window.location.hash;
    if (!hash || hash === "#") return;
    window.location.href = `/${locale}/auth/accept-invite${hash}`;
  }, [locale]);

  return (
    <div className="relative mx-auto w-full max-w-[562px] rounded-[4px] border border-[var(--border,#e5e5e5)] bg-[var(--background-chart,#ffffff)] p-8 shadow-sm md:p-12">
      <div className="absolute right-4 top-4 z-10">
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="hover:bg-muted bg-background/80"
              aria-label="Demo accounts"
            >
              <CircleHelp className="h-6 w-6" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64 space-y-3" align="end">
            <div>
              <p className="text-sm font-medium">{t("demoAccounts")}</p>
              <p className="text-muted-foreground text-xs">{t("demoAccountsDesc")}</p>
            </div>
            <div className="space-y-2">
              {DEMO_ACCOUNTS.map((account) => (
                <div
                  key={account.label}
                  className="shadow-xs flex items-center justify-between rounded-md border p-2 text-sm"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{account.label}</span>
                      <Badge variant="secondary" className="text-[10px]">
                        {t("demo")}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground text-xs">{account.email}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="gap-1"
                    onClick={() => setPrefill(account)}
                  >
                    <LogIn className="h-3.5 w-3.5" />
                    Quick login
                  </Button>
                </div>
              ))}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      <div className="space-y-1 pb-6">
        <h1 className="text-card-foreground text-[36px] leading-[1.3] font-medium tracking-[-0.04em]">
          {t("loginTitle")}
        </h1>
        <p className="text-muted-foreground text-sm">{t("loginSubtitle")}</p>
      </div>

      <LoginForm prefill={prefill} />
    </div>
  );
}
