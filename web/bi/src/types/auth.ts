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

export type UserProfile = {
  id: string;
  email: string | null;
  full_name: string | null;
  first_name: string | null;
  last_name: string | null;
  company_email: string | null;
  notes: string | null;
  role_id: string | null;
  avatar_url: string | null;
  department: string | null;
  position: string | null;
  phone: string | null;
  is_superadmin: boolean | null;
  created_at: string;
  updated_at: string;
};
