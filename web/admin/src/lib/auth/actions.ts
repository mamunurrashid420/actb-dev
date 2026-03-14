"use server";

import { redirect } from "next/navigation";

import { API_BASE_URL } from "@/lib/auth/constants";
import { apiServerRequest, type APIError } from "@/lib/api-server";
import { clearAuthCookies, setAuthCookies } from "@/lib/auth/session";

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number | null;
  user?: Record<string, unknown> | null;
};

export type SignInResult = { success: true } | { error: string };

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

  return { success: true } as const;
}

export async function signOut() {
  await clearAuthCookies();
  redirect("/auth/login");
}

export async function getAuthContext<T>(): Promise<T | null> {
  try {
    return await apiServerRequest<T>("GET", "/auth/me");
  } catch (error) {
    const apiError = error as APIError;
    if (apiError?.status === 401) {
      return null;
    }
    throw error;
  }
}
