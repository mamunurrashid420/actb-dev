"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import Image from "next/image";

import { CircleHelp, LogIn } from "lucide-react";

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
  const router = useRouter();
  const [prefill, setPrefill] = useState<LoginPrefill | undefined>(undefined);

  // If an invite hash is present, hand off to dedicated accept page so user can set password.
  useEffect(() => {
    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : "";
    if (!hash) return;
    router.replace(`/auth/accept-invite#${hash}`);
  }, [router]);

  return (
    <div className="relative mx-auto flex w-full max-w-md flex-col justify-center space-y-8">
      <div className="fixed right-4 top-4 z-50">
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="hover:bg-muted bg-background/80 backdrop-blur supports-[backdrop-filter]:backdrop-blur-md"
              aria-label="Demo accounts"
            >
              <CircleHelp className="h-7 w-7" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64 space-y-3" align="end">
            <div>
              <p className="text-sm font-medium">Quick demo login</p>
              <p className="text-muted-foreground text-xs">
                Pick a role to auto-fill and auto-submit credentials.
              </p>
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
                        demo
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

      <div className="space-y-2 text-center">
        <Image
          src="/Logo/actbi-logo-w-text.png"
          alt="Actbi logo"
          width={150}
          height={60}
          className="mx-auto"
          priority
        />
        <h1 className="text-3xl font-medium">Login to your account</h1>
        <p className="text-muted-foreground text-sm">
          Please enter your details to login.
        </p>
      </div>
      <div className="space-y-4">
        <LoginForm prefill={prefill} />
      </div>
    </div>
  );
}
