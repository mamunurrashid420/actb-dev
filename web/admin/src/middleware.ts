import { NextResponse, type NextRequest } from "next/server";

import { AUTH_COOKIE_KEYS } from "@/lib/auth/constants";

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const accessToken = req.cookies.get(AUTH_COOKIE_KEYS.accessToken)?.value;
  const isLoggedIn = Boolean(accessToken);

  if (!isLoggedIn && pathname.startsWith("/admin")) {
    return NextResponse.redirect(new URL("/auth/login", req.url));
  }

  if (isLoggedIn && (pathname === "/auth/login" || pathname === "/auth/register")) {
    return NextResponse.redirect(new URL("/admin/tenants", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/:path*", "/auth/login", "/auth/register"],
  runtime: "nodejs",
};
