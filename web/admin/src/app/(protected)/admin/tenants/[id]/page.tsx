import { TenantViewPage } from "@/components/admin/tenant-view-page";
import { requireSuperadmin } from "@/lib/auth/require-superadmin";

export default async function TenantDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  await requireSuperadmin();
  const { id } = await params;
  return <TenantViewPage tenantId={id} />;
}
