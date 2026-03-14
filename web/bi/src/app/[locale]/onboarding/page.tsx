import { redirect } from "next/navigation";

import { apiServerRequest } from "@/lib/api-server";
import { getAuthContext } from "@/lib/auth/actions";
import type { UserProfile } from "@/types/auth";
import type { PaginatedResponse } from "@/types/connections";
import type { Tenant } from "@/types/tenants";

import { OnboardingForm } from "./onboarding-form";

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function OnboardingPage({ params }: Props) {
  const { locale } = await params;
  const auth = await getAuthContext();
  if (!auth) {
    redirect(`/${locale}/auth/login`);
  }

  const profile = await apiServerRequest<UserProfile | null>(
    "GET",
    "/users/me/profile",
  ).catch(() => null);
  const tenantsResponse = await apiServerRequest<PaginatedResponse<Tenant>>(
    "GET",
    "/tenants?limit=200&offset=0",
  ).catch(() => ({ items: [], total: 0, limit: 200, offset: 0 }));
  const tenants = tenantsResponse.items ?? [];
  const primaryTenant = tenants[0] ?? null;

  const firstName = profile?.first_name ?? profile?.full_name?.split(" ")?.[0] ?? "";
  const lastName =
    profile?.last_name ??
    (profile?.full_name ? profile.full_name.split(" ").slice(1).join(" ") : "");

  const defaultValues = {
    firstName,
    lastName,
    companyEmail: profile?.company_email ?? profile?.email ?? auth.email ?? "",
    organization: primaryTenant?.name ?? "",
    description: profile?.notes ?? "",
  };

  return (
    <OnboardingForm
      tenantId={primaryTenant?.id ?? null}
      defaultValues={defaultValues}
    />
  );
}
