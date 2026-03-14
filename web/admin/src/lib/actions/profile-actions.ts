"use server";

import { apiServerRequest } from "@/lib/api-server";
import type { UserProfile } from "@/types/profile";

export async function updateMyProfile(payload: Partial<UserProfile>) {
  return await apiServerRequest<UserProfile>("PUT", "/users/me/profile", payload);
}
