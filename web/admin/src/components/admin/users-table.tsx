"use client";

import { useEffect, useMemo, useState } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { deleteUser, resendInvite } from "@/lib/actions/admin-actions";
import { EditUserDialog } from "./edit-user-dialog";
import { InviteUserDialog } from "./invite-user-dialog";

export type UserRow = {
  id: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
  is_app_admin?: boolean | null;
  status: string | null;
  tenant_id: string | null;
  role?: "superadmin" | "admin" | "creator" | "viewer" | null;
  invited_at?: string | null;
  accepted_at?: string | null;
};

export type TenantRow = {
  id: string;
  name: string;
};

type Props = {
  users: UserRow[];
  tenants: TenantRow[];
  canInvite?: boolean;
};

export function UsersTable({ users, tenants, canInvite = false }: Props) {
  const [mounted, setMounted] = useState(false);
  const [userRows, setUserRows] = useState(users);
  const [filter, setFilter] = useState("");
  const [deletingUser, setDeletingUser] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<UserRow | null>(null);
  const [resending, setResending] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const filteredUsers = useMemo(() => {
    const term = filter.trim().toLowerCase();
    if (!term) return userRows;
    return userRows.filter((u) => {
      const hay = `${u.full_name ?? ""} ${u.email ?? ""}`.toLowerCase();
      return hay.includes(term);
    });
  }, [filter, userRows]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeletingUser(deleteTarget.id);
    try {
      await deleteUser(deleteTarget.id);
      setUserRows((prev) => prev.filter((row) => row.id !== deleteTarget.id));
      toast.success("User deleted");
      setDeleteTarget(null);
    } catch (error) {
      toast.error("Failed to delete user", {
        description: error instanceof Error ? error.message : "Unexpected error",
      });
    } finally {
      setDeletingUser(null);
    }
  };

  const handleResendInvite = async (user: UserRow) => {
    if (!user.email) return;
    setResending(user.id);
    try {
      await resendInvite({
        email: user.email,
        tenantId: user.tenant_id ?? undefined,
      });
      toast.success("Invite resent", { description: user.email });
    } catch (error) {
      toast.error("Failed to resend invite", {
        description: error instanceof Error ? error.message : "Unexpected error",
      });
    } finally {
      setResending(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
          <p className="text-muted-foreground text-sm">Manage tenant users</p>
        </div>
        <div className="flex items-center gap-2">
          {mounted && canInvite && (
            <InviteUserDialog
              tenants={tenants}
              onInvited={(user) => setUserRows((prev) => [user, ...prev])}
              disabled={!!deletingUser || !!resending}
            />
          )}
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Input
          placeholder="Search by name or email..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead className="w-[120px]">Status</TableHead>
              <TableHead className="w-[140px]">App Admin</TableHead>
              <TableHead className="w-[140px]">Role</TableHead>
              <TableHead className="w-[180px]">Tenant</TableHead>
              <TableHead className="w-[180px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredUsers.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-muted-foreground py-8 text-center"
                >
                  No users found.
                </TableCell>
              </TableRow>
            ) : (
              filteredUsers.map((u) => {
                return (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">
                      {u.full_name ?? "Unnamed"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {u.email ?? "—"}
                    </TableCell>
                    <TableCell>
                      {u.status === "active" ? (
                        <Badge variant="secondary">Active</Badge>
                      ) : u.invited_at && !u.accepted_at ? (
                        <Badge variant="outline" className="border-dashed">
                          Invited
                        </Badge>
                      ) : (
                        <Badge variant="outline">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {u.is_app_admin ? (
                        <Badge variant="secondary">Yes</Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {u.tenant_id ? (
                        <Badge variant="outline" className="capitalize">
                          {u.role ?? "viewer"}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {tenants.find((t) => t.id === u.tenant_id)?.name ?? "—"}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {mounted && (
                          <EditUserDialog
                            user={u}
                            tenants={tenants}
                            onUpdated={(userId, updates) =>
                              setUserRows((prev) =>
                                prev.map((row) =>
                                  row.id === userId ? { ...row, ...updates } : row,
                                ),
                              )
                            }
                          />
                        )}
                        {u.status !== "active" && u.invited_at && !u.accepted_at && (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={!!resending}
                            onClick={() => handleResendInvite(u)}
                            className="text-xs"
                          >
                            {resending === u.id ? "Sending..." : "Resend"}
                          </Button>
                        )}
                        {mounted && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeleteTarget(u)}
                            disabled={
                              !!deletingUser
                            }
                            className="text-destructive hover:text-destructive h-8 w-8 p-0"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation */}
      <AlertDialog
        open={Boolean(deleteTarget)}
        onOpenChange={() => setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete user?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes their account, memberships, and access. This cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={!!deletingUser}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={!!deletingUser}
              onClick={handleDelete}
            >
              {deletingUser ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
