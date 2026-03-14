"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { listTenants } from "@/lib/actions/admin-actions";
import { TenantTable } from "./tenant-table";

type TenantSummary = {
  id: string;
  name: string | null;
  description: string | null;
  status: string | null;
  logo_url: string | null;
  document_name: string | null;
  member_count?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export function TenantAdminPanel() {
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [loadingTenants, setLoadingTenants] = useState(false);

  const loadTenants = useCallback(async () => {
    setLoadingTenants(true);
    try {
      const data = await listTenants({ limit: 200 });
      setTenants((data.tenants ?? []) as TenantSummary[]);
    } catch {
      toast.error("Unable to load tenants");
    } finally {
      setLoadingTenants(false);
    }
  }, []);

  useEffect(() => {
    void loadTenants();
  }, [loadTenants]);

  return (
    <TenantTable tenants={tenants} loading={loadingTenants} onRefresh={loadTenants} />
  );
}
