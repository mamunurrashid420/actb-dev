import type { User } from "@supabase/supabase-js";

export type UserProfileRow = {
  id: string;
  email: string | null;
  full_name: string | null;
  role_id: string | null;
  avatar_url: string | null;
  department: string | null;
  position: string | null;
  phone: string | null;
  is_active: boolean | null;
  is_superadmin: boolean | null;
  last_login: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type UserAuthContext = {
  user: User;
  profile: UserProfileRow | null;
  permissions: string[];
  role: string;
};
