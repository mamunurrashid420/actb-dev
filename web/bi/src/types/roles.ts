export type Role = {
  id: string;
  name: string;
  description: string | null;
  type: "app" | "tenant";
  created_at: string;
  updated_at: string;
};

export type RoleType = "app" | "tenant";

export type Permission = {
  id: string;
  name: string;
  description: string | null;
  resource: string | null;
  action: string | null;
  created_at: string;
  updated_at: string;
};
