import { ProfileView } from "@/components/profile/profile-view";
import { requireSuperadmin } from "@/lib/auth/require-superadmin";
import { apiServerRequest } from "@/lib/api-server";
import type { UserProfile } from "@/types/profile";

export default async function ProfilePage() {
  const authContext = await requireSuperadmin();
  const profile = await apiServerRequest<UserProfile>("GET", "/users/me/profile");

  return (
    <ProfileView
      user={{ id: authContext.id, email: authContext.email }}
      profile={profile}
      isAppAdmin={Boolean(authContext.claims?.["is_app_admin"])}
    />
  );
}
