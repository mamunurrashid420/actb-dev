"use client";

import { useEffect, useState } from "react";

import { LockKeyhole, Mail, Plus, UserPlus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import { createUser, inviteUser } from "@/lib/actions/admin-actions";

import type { TenantRow, UserRow } from "./users-table";

type InviteResponse = {
  userId: string;
  email: string;
  fullName: string;
  tenantId: string | null;
  status: string;
};

type Props = {
  tenants: TenantRow[];
  disabled?: boolean;
  onInvited?: (user: UserRow) => void;
};

export function InviteUserDialog({ tenants, disabled, onInvited }: Props) {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mode, setMode] = useState<"invite" | "create">("invite");
  const hasTenants = tenants.length > 0;
  const [form, setForm] = useState({
    email: "",
    fullName: "",
    password: "",
    tenantId: tenants[0]?.id ?? "",
    role: "viewer" as "superadmin" | "admin" | "creator" | "viewer",
  });

  useEffect(() => {
    setForm((prev) => ({
      ...prev,
      tenantId: tenants.find((t) => t.id === prev.tenantId)?.id ?? tenants[0]?.id ?? "",
    }));
  }, [tenants]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.tenantId || !hasTenants) {
      toast.error("Please select a tenant");
      return;
    }
    setIsSubmitting(true);

    let data: InviteResponse;
    try {
      if (mode === "invite") {
        data = await inviteUser({
          email: form.email.trim(),
          tenantId: form.tenantId,
          role: form.role,
        });
      } else {
        data = await createUser({
          email: form.email.trim(),
          password: form.password,
          fullName: form.fullName.trim() || undefined,
          tenantId: form.tenantId,
          role: form.role,
        });
      }
    } catch (error) {
      toast.error(
        mode === "invite" ? "Failed to send invite" : "Failed to create user",
        {
          description: error instanceof Error ? error.message : "Unexpected error",
        },
      );
      setIsSubmitting(false);
      return;
    }
    toast.success(mode === "invite" ? "Invite sent" : "User created", {
      description:
        mode === "invite"
          ? `${data.email} can now finish signup via email.`
          : `${data.email} was created successfully.`,
    });
    setIsSubmitting(false);
    setOpen(false);
    setForm({
      email: "",
      fullName: "",
      password: "",
      tenantId: form.tenantId,
      role: form.role,
    });

    onInvited?.({
      id: data.userId,
      email: data.email,
      full_name: data.fullName,
      avatar_url: null,
      status: mode === "invite" ? "inactive" : "active",
      tenant_id: data.tenantId,
      role: form.role,
      invited_at: mode === "invite" ? new Date().toISOString() : null,
      accepted_at: mode === "invite" ? null : new Date().toISOString(),
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" onClick={() => setOpen(true)} disabled={disabled}>
          <Plus className="mr-2 h-4 w-4" />
          Add user
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {mode === "invite" ? "Invite a user" : "Create a user"}
          </DialogTitle>
          <DialogDescription>
            {mode === "invite"
              ? "Send an invite email. The user sets their password."
              : "Create the account now with a password you set."}
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-2">
            <Button
              type="button"
              variant={mode === "invite" ? "default" : "outline"}
              className="gap-2"
              onClick={() => setMode("invite")}
              disabled={isSubmitting}
            >
              <Mail className="h-4 w-4" />
              Invite via email
            </Button>
            <Button
              type="button"
              variant={mode === "create" ? "default" : "outline"}
              className="gap-2"
              onClick={() => setMode("create")}
              disabled={isSubmitting}
            >
              <UserPlus className="h-4 w-4" />
              Create now
            </Button>
          </div>

          <div className="space-y-1">
            <Label htmlFor="email">Work email</Label>
            <Input
              id="email"
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
            />
          </div>

          {mode === "create" && (
            <>
              <div className="space-y-1">
                <Label htmlFor="fullName">Full name</Label>
                <Input
                  id="fullName"
                  type="text"
                  value={form.fullName}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, fullName: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  minLength={6}
                  value={form.password}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, password: e.target.value }))
                  }
                  placeholder="Set a temporary password"
                />
              </div>
            </>
          )}

          <div className="space-y-1">
            <Label htmlFor="tenant">Tenant</Label>
            <Select
              value={form.tenantId}
              onValueChange={(val) => setForm((prev) => ({ ...prev, tenantId: val }))}
              disabled={!hasTenants}
            >
              <SelectTrigger id="tenant">
                <SelectValue
                  placeholder={hasTenants ? "Select tenant" : "No tenants available"}
                />
              </SelectTrigger>
              <SelectContent>
                {tenants.map((tenant) => (
                  <SelectItem key={tenant.id} value={tenant.id}>
                    {tenant.name}
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
              disabled={!hasTenants}
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
          </div>

          <DialogFooter className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:space-y-0">
            <div className="text-muted-foreground flex items-center gap-2 text-xs">
              {mode === "invite" ? (
                <>
                  <Mail className="h-4 w-4" />
                  The system sends the invite email; the user sets their password
                  securely.
                </>
              ) : (
                <>
                  <LockKeyhole className="h-4 w-4" />
                  You set the initial password; user can change it after logging in.
                </>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpen(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting || !hasTenants}>
                {isSubmitting
                  ? "Submitting..."
                  : mode === "invite"
                    ? "Send invite"
                    : "Create user"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
