export type Tenant = {
  id: string;
  name: string;
  description: string | null;
  status: "active" | "inactive";
  logo_url?: string | null;
  document_name?: string | null;
  logo_signed_url?: string | null;
  document_signed_url?: string | null;
  created_at: string;
  updated_at: string;
};

export type TenantMember = {
  id: string;
  tenant_id: string;
  user_id: string;
  role: string;
  status: "invited" | "active" | "disabled";
  invited_at: string | null;
  accepted_at: string | null;
  created_at: string;
  email?: string | null;
  full_name?: string | null;
  avatar_url?: string | null;
};

export type TenantRole = {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  created_at: string;
  updated_at: string;
};
