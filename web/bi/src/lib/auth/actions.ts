"use server";

import { redirect } from "next/navigation";

import { API_BASE_URL } from "@/lib/auth/constants";
import { apiServerRequest, type APIError } from "@/lib/api-server";
import { clearAuthCookies, setAuthCookies } from "@/lib/auth/session";
import type { AuthContext } from "@/types/auth";

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number | null;
  user?: Record<string, unknown> | null;
};

export type SignInResult =
  | { success: true; authContext?: AuthContext }
  | { error: string };

export async function signInWithEmailAndPassword(formData: {
  email: string;
  password: string;
  remember?: boolean;
}): Promise<SignInResult> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: formData.email,
      password: formData.password,
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    let message = "Login failed";
    try {
      const data = await response.json();
      message = data.detail || data.error || message;
    } catch {
      // ignore
    }
    return { error: message };
  }

  const data = (await response.json()) as LoginResponse;
  await setAuthCookies({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    tokenType: data.token_type,
    expiresIn: data.expires_in,
    remember: formData.remember,
  });

  let authContext: AuthContext | undefined;
  try {
    const contextResponse = await fetch(`${API_BASE_URL}/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${data.access_token}`,
      },
      cache: "no-store",
    });
    if (contextResponse.ok) {
      authContext = (await contextResponse.json()) as AuthContext;
    }
  } catch {
    // Ignore lookup errors; caller can fallback to default navigation.
  }

  return { success: true, authContext } as const;
}

export async function signOut() {
  await clearAuthCookies();
  redirect("/auth/login");
}

export async function getAuthContext(): Promise<AuthContext | null> {
  try {
    return await apiServerRequest<AuthContext>("GET", "/auth/me");
  } catch (error) {
    const apiError = error as APIError;
    if (apiError?.status === 401) {
      return null;
    }
    throw error;
  }
}
