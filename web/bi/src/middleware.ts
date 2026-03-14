import { NextResponse, type NextRequest } from "next/server";

import createIntlMiddleware from "next-intl/middleware";

import { AUTH_COOKIE_KEYS } from "@/lib/auth/constants";
import { routing } from "@/i18n/routing";

const intlMiddleware = createIntlMiddleware(routing);

function getJwtExpSeconds(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) {
      return null;
    }
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded));
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}

function isTokenExpired(token: string | undefined, expiresAt?: string): boolean {
  if (!token) {
    return false;
  }
  if (expiresAt) {
    const parsed = Date.parse(expiresAt);
    if (!Number.isNaN(parsed)) {
      return Date.now() > parsed;
    }
  }
  const expSeconds = getJwtExpSeconds(token);
  if (expSeconds) {
    return Date.now() / 1000 >= expSeconds;
  }
  return false;
}

function clearAuthCookies(response: NextResponse) {
  Object.values(AUTH_COOKIE_KEYS).forEach((key) => response.cookies.delete(key));
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Skip i18n for API routes and static files
  if (
    pathname.startsWith("/api") ||
    pathname.startsWith("/_next") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // IMPORTANT: Skip middleware redirect for accept-invite paths
  // URL hash fragments (containing auth tokens) are lost during server-side redirects
  // The accept-invite page handles locale detection client-side
  const pathWithoutLocaleCheck = pathname.replace(/^\/[a-z]{2}(?=\/|$)/, "") || "/";
  if (
    pathWithoutLocaleCheck === "/auth/accept-invite" ||
    pathname === "/auth/accept-invite"
  ) {
    // If already has locale prefix, just pass through
    if (pathname.match(/^\/[a-z]{2}\/auth\/accept-invite/)) {
      return NextResponse.next();
    }
    // If no locale, rewrite (not redirect) to default locale path to preserve hash
    const defaultLocale = routing.defaultLocale;
    const url = req.nextUrl.clone();
    url.pathname = `/${defaultLocale}/auth/accept-invite`;
    return NextResponse.rewrite(url);
  }

  // Run i18n middleware first
  const intlResponse = intlMiddleware(req);

  // Extract locale from the pathname or use default
  const pathnameLocale = routing.locales.find(
    (locale) => pathname.startsWith(`/${locale}/`) || pathname === `/${locale}`,
  );
  const locale = pathnameLocale || routing.defaultLocale;

  const response = intlResponse;
  const accessToken = req.cookies.get(AUTH_COOKIE_KEYS.accessToken)?.value;
  const expiresAt = req.cookies.get(AUTH_COOKIE_KEYS.expiresAt)?.value;
  const tokenExpired = isTokenExpired(accessToken, expiresAt);
  const shouldLogout = req.nextUrl.searchParams.get("logout") === "1";
  const isLoggedIn = Boolean(accessToken) && !tokenExpired && !shouldLogout;

  // Remove locale prefix for path checking
  const pathWithoutLocale = pathnameLocale
    ? pathname.replace(`/${pathnameLocale}`, "") || "/"
    : pathname;

  if (tokenExpired || shouldLogout) {
    clearAuthCookies(response);
  }

  if (
    !isLoggedIn &&
    !pathWithoutLocale.startsWith("/auth") &&
    !pathWithoutLocale.startsWith("/unauthorized")
  ) {
    const redirectUrl = new URL(`/${locale}/auth/login`, req.url);
    if (shouldLogout) {
      redirectUrl.searchParams.set("logout", "1");
    }
    const redirectResponse = NextResponse.redirect(redirectUrl);
    if (tokenExpired || shouldLogout) {
      clearAuthCookies(redirectResponse);
    }
    return redirectResponse;
  }

  if (isLoggedIn && pathWithoutLocale.startsWith("/auth")) {
    return NextResponse.redirect(new URL(`/${locale}/dashboard`, req.url));
  }

  return response;
}

export const config = {
  matcher: ["/((?!api|_next|.*\\..*).*)"],
  runtime: "nodejs",
};
