import { cookies } from "next/headers";

import { AUTH_COOKIE_KEYS } from "./constants";

export type AuthTokens = {
  accessToken: string;
  refreshToken?: string | null;
  tokenType?: string | null;
  expiresIn?: number | null;
  remember?: boolean;
};

export async function getAccessToken(): Promise<string | undefined> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIE_KEYS.accessToken)?.value;
}

export async function setAuthCookies(tokens: AuthTokens): Promise<void> {
  const cookieStore = await cookies();
  const maxAge = tokens.remember ? 60 * 60 * 24 * 30 : undefined;
  const expiresAt = tokens.expiresIn
    ? new Date(Date.now() + tokens.expiresIn * 1000).toISOString()
    : undefined;

  cookieStore.set(AUTH_COOKIE_KEYS.accessToken, tokens.accessToken, {
    path: "/",
    maxAge,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
  });

  if (tokens.refreshToken) {
    cookieStore.set(AUTH_COOKIE_KEYS.refreshToken, tokens.refreshToken, {
      path: "/",
      maxAge,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
  }

  if (tokens.tokenType) {
    cookieStore.set(AUTH_COOKIE_KEYS.tokenType, tokens.tokenType, {
      path: "/",
      maxAge,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
  }

  if (expiresAt) {
    cookieStore.set(AUTH_COOKIE_KEYS.expiresAt, expiresAt, {
      path: "/",
      maxAge,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
  }
}

export async function clearAuthCookies(): Promise<void> {
  const cookieStore = await cookies();
  Object.values(AUTH_COOKIE_KEYS).forEach((key) => cookieStore.delete(key));
}
