export const AUTH_COOKIE_KEYS = {
  accessToken: "actbi_access_token",
  refreshToken: "actbi_refresh_token",
  tokenType: "actbi_token_type",
  expiresAt: "actbi_expires_at",
} as const;

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
