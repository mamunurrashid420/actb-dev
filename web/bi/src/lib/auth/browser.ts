import { AUTH_COOKIE_KEYS } from "./constants";

function getCookieValue(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : undefined;
}

export function getBrowserAccessToken(): string | undefined {
  return getCookieValue(AUTH_COOKIE_KEYS.accessToken);
}
