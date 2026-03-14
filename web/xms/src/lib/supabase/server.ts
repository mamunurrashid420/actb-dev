import { createClient as createAdminClient, createClient } from "@supabase/supabase-js";
import type { SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseEnv } from "./env";

let serverClient: SupabaseClient | undefined;
let adminClient: SupabaseClient | undefined;

export function getServerSupabase(): SupabaseClient {
  if (serverClient) return serverClient;
  const { NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY } = getSupabaseEnv();

  serverClient = createClient(NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY);

  return serverClient;
}

export function getAdminSupabase(): SupabaseClient {
  if (adminClient) return adminClient;

  const { NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY } = getSupabaseEnv();
  if (!SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is required for admin client");
  }

  // Note: using createClient from @supabase/supabase-js would also work, but keep single import source
  adminClient = createAdminClient(NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
  return adminClient;
}
