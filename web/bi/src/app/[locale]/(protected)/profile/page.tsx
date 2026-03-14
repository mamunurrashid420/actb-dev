import { ProfileView } from "@/components/profile/profile-view";
import { requireUserAbilityContext } from "@/lib/permissions/require-user-ability";

export default async function ProfilePage() {
  const { authContext } = await requireUserAbilityContext();

  return <ProfileView auth={authContext} profile={authContext.profile} />;
}
