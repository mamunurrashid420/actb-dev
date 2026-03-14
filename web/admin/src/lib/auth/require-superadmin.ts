import { redirect } from "next/navigation";
import { NextResponse } from "next/server";

import { getAuthContext } from "@/lib/auth/actions";
import type { AuthContext } from "@/types/auth";

const isSuperadmin = (authContext: AuthContext) =>
  Boolean(
    authContext?.claims &&
      (authContext.claims["is_app_admin"] === true ||
        authContext.claims["role"] === "app_admin"),
  );

export async function requireSuperadmin(): Promise<AuthContext> {
  const authContext = await getAuthContext<AuthContext>();
  if (!authContext) {
    redirect("/auth/login");
  }
  if (!isSuperadmin(authContext)) {
    redirect("/unauthorized");
  }
  return authContext;
}

export async function requireSuperadminApi(): Promise<{
  authContext: AuthContext;
  error: NextResponse | null;
}> {
  const authContext = await getAuthContext<AuthContext>();
  if (!authContext) {
    return {
      authContext: null as never,
      error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }),
    };
  }
  if (!isSuperadmin(authContext)) {
    return {
      authContext: null as never,
      error: NextResponse.json({ error: "Forbidden" }, { status: 403 }),
    };
  }
  return { authContext, error: null };
}
