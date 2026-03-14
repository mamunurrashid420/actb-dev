export type AuthContext = {
  id: string;
  email: string | null;
  claims?: Record<string, unknown> | null;
  role?: string | null;
  is_superadmin?: boolean;
  permissions?: string[];
  tenant_roles?: Record<string, string>;
  tenant_permissions?: Record<string, string[]>;
};
