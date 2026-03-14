import { TenantAdminPanel } from "@/components/admin/tenant-admin-panel";
import { requireSuperadmin } from "@/lib/auth/require-superadmin";

export default async function AdminTenantsPage() {
  await requireSuperadmin();

  return <TenantAdminPanel />;
}
