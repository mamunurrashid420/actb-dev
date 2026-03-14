"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Lock } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { acceptInvite } from "./actions";

export default function AcceptInvitePage() {
  const router = useRouter();
  const params = useParams();
  const locale =
    typeof params?.locale === "string" ? params.locale : "en";

  const [hashParams, setHashParams] = useState<{
    accessToken: string;
    refreshToken: string;
    tokenType?: string;
    expiresIn?: number;
  } | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Parse invite tokens from URL hash and establish the invited session.
  useEffect(() => {
    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : "";
    const params = new URLSearchParams(hash);
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const tokenType = params.get("token_type") ?? undefined;
    const expiresIn = params.get("expires_in");

    if (!accessToken || !refreshToken) {
      setError("Invite link is missing or expired. Please request a new invite.");
      return;
    }

    setHashParams({
      accessToken,
      refreshToken,
      tokenType,
      expiresIn: expiresIn ? Number(expiresIn) : undefined,
    });
    setSessionReady(true);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionReady || !hashParams) return;

    if (!password || password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    setLoading(true);
    const result = await acceptInvite({
      accessToken: hashParams.accessToken,
      refreshToken: hashParams.refreshToken,
      tokenType: hashParams.tokenType,
      expiresIn: hashParams.expiresIn,
      password,
    });
    setLoading(false);

    if ("error" in result) {
      toast.error("Could not set password", { description: result.error });
      return;
    }

    toast.success("Password set. Continue to onboarding.");
    router.replace(`/${locale}/onboarding`);
  };

  return (
    <div className="mx-auto w-full max-w-[562px]">
      <Card className="border-border shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl">
            <Lock className="h-5 w-5" />
            Set your password
          </CardTitle>
          <CardDescription>
            Accept your invite by creating a password, then finish onboarding on the
            next step.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <p className="text-destructive text-sm">{error}</p>
          ) : !sessionReady ? (
            <p className="text-muted-foreground text-sm">Validating your invite...</p>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="password">New password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  required
                  minLength={8}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
              <Button
                type="submit"
                className="w-full"
                disabled={!sessionReady || loading}
              >
                {loading ? "Setting password..." : "Continue"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
