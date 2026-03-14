"use client";

import { useEffect, useState } from "react";

import { Pencil } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { TenantRow, UserRow } from "./users-table";
import { updateUser } from "@/lib/actions/admin-actions";

type Props = {
  user: UserRow;
  tenants: TenantRow[];
  onUpdated: (userId: string, updates: Partial<UserRow>) => void;
};

export function EditUserDialog({ user, tenants, onUpdated }: Props) {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState({
    full_name: user.full_name ?? "",
    tenant_id: user.tenant_id ?? "",
    role: user.role ?? "viewer",
  });

  // Reset form when user changes or dialog opens
  useEffect(() => {
    if (open) {
      setForm({
        full_name: user.full_name ?? "",
        tenant_id: user.tenant_id ?? "",
        role: user.role ?? "viewer",
      });
    }
  }, [open, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await updateUser({
        userId: user.id,
        fullName: form.full_name.trim() || undefined,
        tenantId: form.tenant_id || undefined,
        role: form.tenant_id ? (form.role as "superadmin" | "admin" | "creator" | "viewer") : undefined,
      });
    } catch (error) {
      toast.error("Failed to update user", {
        description: error instanceof Error ? error.message : "Unexpected error",
      });
      setIsSubmitting(false);
      return;
    }

    onUpdated(user.id, {
      full_name: form.full_name,
      tenant_id: form.tenant_id,
      role: form.tenant_id ? form.role : null,
    });
    toast.success("User updated");
    setIsSubmitting(false);
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Edit user">
          <Pencil className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit user</DialogTitle>
        </DialogHeader>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1">
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={user.email ?? ""} disabled className="bg-muted" />
          </div>

          <div className="space-y-1">
            <Label htmlFor="fullName">Full name</Label>
            <Input
              id="fullName"
              value={form.full_name}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, full_name: e.target.value }))
              }
              placeholder="Full name"
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="tenant">Tenant</Label>
            <Select
              value={form.tenant_id || "none"}
              onValueChange={(val) =>
                setForm((prev) => ({
                  ...prev,
                  tenant_id: val === "none" ? "" : val,
                }))
              }
            >
              <SelectTrigger id="tenant">
                <SelectValue placeholder="Select tenant" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No tenant</SelectItem>
                {tenants.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label htmlFor="role">Role</Label>
            <Select
              value={form.role}
              onValueChange={(val) =>
                setForm((prev) => ({
                  ...prev,
                  role: val as "superadmin" | "admin" | "creator" | "viewer",
                }))
              }
              disabled={!form.tenant_id}
            >
              <SelectTrigger id="role">
                <SelectValue placeholder="Select role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="superadmin">SuperAdmin</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="creator">Creator</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
            {!form.tenant_id ? (
              <p className="text-muted-foreground text-xs">
                Assign a tenant to set a role.
              </p>
            ) : null}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
