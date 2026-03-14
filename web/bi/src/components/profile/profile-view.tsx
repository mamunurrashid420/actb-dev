"use client";

import { useState, useTransition } from "react";
import type React from "react";

import { Shield, Mail, Briefcase } from "lucide-react";

import { usersApi } from "@/lib/api-client";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import type { AuthContext, UserProfile } from "@/types/auth";

type ProfileViewProps = {
  auth: AuthContext;
  profile: UserProfile | null;
};

type EditableProfileFields = Pick<
  UserProfile,
  "full_name" | "avatar_url" | "department" | "position" | "phone"
>;

export function ProfileView({ auth, profile }: ProfileViewProps) {
  const [formState, setFormState] = useState<EditableProfileFields>({
    full_name: profile?.full_name ?? "",
    avatar_url: profile?.avatar_url ?? "",
    department: profile?.department ?? "",
    position: profile?.position ?? "",
    phone: profile?.phone ?? "",
  });
  const [saving, startSaving] = useTransition();
  const canEditProfile = true;

  const initials = (profile?.full_name ?? auth.email ?? "User")
    .slice(0, 2)
    .toUpperCase();

  const handleSubmit = () => {
    startSaving(async () => {
      try {
        await usersApi.put<UserProfile, Partial<EditableProfileFields>>(
          {
            full_name: formState.full_name || null,
            avatar_url: formState.avatar_url || null,
            department: formState.department || null,
            position: formState.position || null,
            phone: formState.phone || null,
          },
          "/me/profile",
        );
        toast.success("Profile updated");
      } catch (error) {
        const message = error instanceof Error ? error.message : "Update failed";
        toast.error("Update failed", { description: message });
        return;
      }
    });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-4">
        <Avatar className="h-12 w-12">
          <AvatarImage
            src={formState.avatar_url || undefined}
            alt={formState.full_name || auth.email || ""}
          />
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        <div>
          <CardTitle className="text-xl">
            {formState.full_name || "Unnamed User"}
          </CardTitle>
          <CardDescription className="flex items-center gap-2">
            <Badge variant="outline" className="flex gap-1 text-xs">
              <Shield className="h-3 w-3" />
              {String(auth.claims?.role ?? "user")}
            </Badge>
            <span className="text-muted-foreground text-xs">{auth.email}</span>
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <InfoInput
            id="full_name"
            label="Full Name"
            value={formState.full_name ?? ""}
            disabled={!canEditProfile || saving}
            onChange={(value) =>
              setFormState((prev) => ({ ...prev, full_name: value }))
            }
          />
          <InfoInput
            id="department"
            label="Department"
            value={formState.department ?? ""}
            disabled={!canEditProfile || saving}
            onChange={(value) =>
              setFormState((prev) => ({ ...prev, department: value }))
            }
          />
          <InfoInput
            id="position"
            label="Position"
            value={formState.position ?? ""}
            disabled={!canEditProfile || saving}
            onChange={(value) => setFormState((prev) => ({ ...prev, position: value }))}
          />
          <InfoInput
            id="phone"
            label="Phone"
            value={formState.phone ?? ""}
            disabled={!canEditProfile || saving}
            onChange={(value) => setFormState((prev) => ({ ...prev, phone: value }))}
          />
          <InfoInput
            id="avatar_url"
            label="Avatar URL"
            value={formState.avatar_url ?? ""}
            disabled={!canEditProfile || saving}
            onChange={(value) =>
              setFormState((prev) => ({ ...prev, avatar_url: value }))
            }
            className="md:col-span-2"
          />
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          <InfoRow
            icon={<Mail className="text-muted-foreground h-4 w-4" />}
            label="Email"
            value={auth.email ?? "—"}
          />
          <InfoRow
            icon={<Briefcase className="text-muted-foreground h-4 w-4" />}
            label="Role"
            value={String(auth.claims?.role ?? "user")}
          />
        </div>
        <Button onClick={handleSubmit} disabled={!canEditProfile || saving}>
          {saving ? "Saving..." : "Update profile"}
        </Button>
        <p className="text-muted-foreground text-xs">
          Editing is allowed only if your role has update permissions; enforced by the
          backend RBAC rules.
        </p>
      </CardContent>
    </Card>
  );
}

function InfoRow({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 rounded-md border p-3">
      {icon}
      <div className="space-y-1">
        <p className="text-muted-foreground text-xs font-medium uppercase">{label}</p>
        <p className="text-sm leading-tight">{value}</p>
      </div>
    </div>
  );
}

function InfoInput({
  id,
  label,
  value,
  onChange,
  disabled,
  className,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
  className?: string;
}) {
  return (
    <div className={className ? `space-y-2 ${className}` : "space-y-2"}>
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        autoComplete="off"
      />
    </div>
  );
}
