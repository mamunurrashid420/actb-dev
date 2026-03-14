import { redirect } from "next/navigation";

export default function AdminOnboardingRedirect() {
  redirect("/admin/tenants");
}
