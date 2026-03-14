export type TenantConnection = {
  id: string;
  tenant_id: string;
  name: string;
  type: "postgres" | "mysql";
  is_active: boolean;
  config: Record<string, unknown>;
  last_test_status: string | null;
  last_tested_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};
