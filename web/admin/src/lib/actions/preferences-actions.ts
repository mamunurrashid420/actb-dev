"use server";

import { setValueToCookie } from "@/lib/preferences";

export async function setPreferenceCookie(key: string, value: string) {
  await setValueToCookie(key, value);
}
