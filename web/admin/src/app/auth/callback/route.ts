import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const origin = requestUrl.origin;
  return NextResponse.redirect(
    `${origin}/auth/login?error=${encodeURIComponent(
      "OAuth is disabled for admin. Use email/password.",
    )}`,
  );
}
