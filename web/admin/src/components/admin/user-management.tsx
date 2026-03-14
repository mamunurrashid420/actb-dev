"use client";

import { useState } from "react";

import { UserRow, UsersTable } from "./users-table";

type Props = {
  users: UserRow[];
  tenants: Array<{ id: string; name: string }>;
};

export function AdminUserManager({ users, tenants }: Props) {
  const [tenantRows] = useState(tenants);

  return (
    <UsersTable users={users} tenants={tenantRows} canInvite={true} />
  );
}
