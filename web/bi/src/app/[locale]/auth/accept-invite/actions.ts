"use server";

import { API_BASE_URL } from "@/lib/auth/constants";
import { setAuthCookies } from "@/lib/auth/session";

export async function acceptInvite(params: {
  accessToken: string;
  refreshToken?: string | null;
  tokenType?: string | null;
  expiresIn?: number | null;
  password: string;
}) {
  const response = await fetch(`${API_BASE_URL}/auth/set-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${params.accessToken}`,
    },
    body: JSON.stringify({ password: params.password }),
    cache: "no-store",
  });

  if (!response.ok) {
    let message = "Failed to set password";
    try {
      const data = await response.json();
      message = data.detail || data.error || message;
    } catch {
      // ignore
    }
    return { error: message };
  }

  await setAuthCookies({
    accessToken: params.accessToken,
    refreshToken: params.refreshToken ?? undefined,
    tokenType: params.tokenType ?? "bearer",
    expiresIn: params.expiresIn ?? undefined,
    remember: true,
  });

  return { success: true } as const;
}
