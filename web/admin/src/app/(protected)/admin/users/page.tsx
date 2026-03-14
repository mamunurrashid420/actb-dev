import { AdminUserManager } from "@/components/admin/user-management";
import type { TenantRow, UserRow } from "@/components/admin/users-table";
import { requireSuperadmin } from "@/lib/auth/require-superadmin";
import { apiServerRequest } from "@/lib/api-server";

type ApiUserRow = {
  id: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
  is_app_admin?: boolean | null;
  status: string | null;
  tenant_id: string | null;
  role?: string | null;
  invited_at?: string | null;
  accepted_at?: string | null;
};

const VALID_ROLES = ["superadmin", "admin", "creator", "viewer"] as const;
type ValidRole = (typeof VALID_ROLES)[number];

function normalizeRole(
  role: string | null | undefined,
): UserRow["role"] {
  return role && (VALID_ROLES as readonly string[]).includes(role)
    ? (role as ValidRole)
    : null;
}

export default async function AdminUsersPage() {
  await requireSuperadmin();
  const { users, tenants } = await apiServerRequest<{
    users: ApiUserRow[];
    tenants: TenantRow[];
  }>("GET", "/admin/users");

  const normalizedUsers: UserRow[] = (users ?? []).map((user) => ({
    ...user,
    role: normalizeRole(user.role),
  }));

  return (
    <AdminUserManager
      users={normalizedUsers}
      tenants={(tenants ?? []) as TenantRow[]}
    />
  );
}
