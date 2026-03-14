"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { buildAbility, type AppAbility } from "@/lib/permissions/casl";

type AbilityContextValue = {
  ability: AppAbility;
  permissions: string[];
  role: string;
  isAdmin: boolean;
};

const AbilityContext = createContext<AbilityContextValue | null>(null);

type AbilityProviderProps = {
  permissions: string[];
  role: string;
  children: ReactNode;
};

export function AbilityProvider({ permissions, role, children }: AbilityProviderProps) {
  const normalizedPermissions = useMemo(() => permissions.slice(), [permissions]);

  const value = useMemo<AbilityContextValue>(() => {
    const isAdminRole = role === "admin" || role === "superadmin";
    return {
      ability: buildAbility(normalizedPermissions, { isAdmin: isAdminRole }),
      permissions: normalizedPermissions,
      role,
      isAdmin: isAdminRole,
    };
  }, [normalizedPermissions, role]);

  return <AbilityContext.Provider value={value}>{children}</AbilityContext.Provider>;
}

export function useAbility() {
  const context = useContext(AbilityContext);
  if (!context) {
    throw new Error("useAbility must be used within an AbilityProvider");
  }
  return context;
}
