import { redirect } from "next/navigation";

import { apiServerRequest } from "@/lib/api-server";
import { getAuthContext } from "@/lib/auth/actions";
import { buildAbility, type AppAbility } from "@/lib/permissions/casl";
import type { AuthContext, UserProfile } from "@/types/auth";

export type UserAbilityContext = {
  authContext: AuthContext & { profile: UserProfile | null };
  ability: AppAbility;
  isAdmin: boolean;
};

export async function requireUserAbilityContext(): Promise<UserAbilityContext> {
  const authContext = await getAuthContext();

  if (!authContext) {
    redirect("/auth/login?logout=1");
  }

  const profile = await apiServerRequest<UserProfile | null>(
    "GET",
    "/users/me/profile",
  ).catch(() => null);

  const permissions = authContext.permissions ?? [];
  const isAdmin = Boolean(
    authContext.is_superadmin ||
      authContext.role === "admin" ||
      authContext.role === "superadmin",
  );
  const ability = buildAbility(permissions, { isAdmin });

  return {
    authContext: { ...authContext, profile },
    ability,
    isAdmin,
  };
}
