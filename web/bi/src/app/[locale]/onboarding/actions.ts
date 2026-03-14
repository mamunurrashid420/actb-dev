"use server";

import { z } from "zod";

import { apiServerRequest } from "@/lib/api-server";
import { getAuthContext } from "@/lib/auth/actions";

const OnboardingSchema = z.object({
  firstName: z.string().trim().min(1),
  lastName: z.string().trim().min(1),
  companyEmail: z.string().email(),
  organization: z.string().trim().min(1),
  description: z.string().trim().max(2000).optional(),
  tenantId: z.string().uuid().optional(),
});

export async function completeOnboarding(input: unknown) {
  const parsed = OnboardingSchema.safeParse(input);
  if (!parsed.success) {
    return { error: "Invalid input" };
  }

  const auth = await getAuthContext();
  if (!auth) {
    return { error: "Not authenticated" };
  }

  const { firstName, lastName, companyEmail, organization, description, tenantId } =
    parsed.data;
  const fullName = `${firstName} ${lastName}`.trim();

  try {
    await apiServerRequest("PUT", "/users/me/profile", {
      first_name: firstName,
      last_name: lastName,
      full_name: fullName,
      company_email: companyEmail,
      notes: description
        ? `${description}\nOrg: ${organization}`
        : `Org: ${organization}`,
      email: auth.email,
    });

    if (tenantId) {
      await apiServerRequest("PUT", `/tenants/${tenantId}/members/me`, {
        status: "active",
      });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Update failed";
    return { error: message };
  }

  // We don’t update tenant metadata here because RLS restricts it to admins.
  return { success: true } as const;
}
