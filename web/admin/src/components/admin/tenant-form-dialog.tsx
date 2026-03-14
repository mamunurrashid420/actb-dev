"use client";

import { useState, useEffect } from "react";
import { Plus, Pencil } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FileUpload } from "@/components/ui/file-upload";
import {
  createTenant,
  updateTenant,
  uploadTenantAsset,
  listTenantAssets,
} from "@/lib/actions/admin-actions";

type TenantSummary = {
  id: string;
  name: string | null;
  description: string | null;
  status: string | null;
  member_count?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type TenantFormState = {
  name: string;
  description: string;
  status: "active" | "inactive";
};

interface TenantFormDialogProps {
  tenant?: TenantSummary | null;
  onSuccess: () => void;
  trigger?: React.ReactNode | null;
}

export function TenantFormDialog({
  tenant,
  onSuccess,
  trigger,
}: TenantFormDialogProps) {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<TenantFormState>({
    name: "",
    description: "",
    status: "active",
  });
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [markdownFile, setMarkdownFile] = useState<File | null>(null);
  const [existingLogoName, setExistingLogoName] = useState<string | null>(null);
  const [existingMarkdownName, setExistingMarkdownName] = useState<string | null>(null);

  const isEdit = Boolean(tenant);

  // Open dialog when tenant prop changes (for programmatic opening)
  useEffect(() => {
    if (tenant && !trigger) {
      setOpen(true);
    }
  }, [tenant, trigger]);

  useEffect(() => {
    if (tenant) {
      setForm({
        name: tenant.name ?? "",
        description: tenant.description ?? "",
        status: tenant.status === "inactive" ? "inactive" : "active",
      });
    } else {
      setForm({ name: "", description: "", status: "active" });
    }
    setLogoFile(null);
    setMarkdownFile(null);
    setExistingLogoName(null);
    setExistingMarkdownName(null);
  }, [tenant, open]);

  useEffect(() => {
    if (!open || !tenant) return;
    let active = true;
    (async () => {
      try {
        const data = await listTenantAssets(tenant.id, false);
        if (!active) return;
        const logoAsset = data.assets?.find((a) => a.asset_type === "logo");
        const markdownAsset = data.assets?.find((a) => a.asset_type === "markdown");
        setExistingLogoName(logoAsset?.file_name ?? null);
        setExistingMarkdownName(markdownAsset?.file_name ?? null);
      } catch {
        if (!active) return;
        setExistingLogoName(null);
        setExistingMarkdownName(null);
      }
    })();
    return () => {
      active = false;
    };
  }, [open, tenant]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const nameValue = form.name.trim();
    if (nameValue.length < 2) {
      toast.error("Tenant name must be at least 2 characters.");
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        name: nameValue,
        description: form.description.trim() || undefined,
        status: form.status,
      };

      const { tenant: savedTenant } = isEdit
        ? await updateTenant(tenant!.id, payload)
        : await createTenant(payload);
      const tenantId = savedTenant?.id || tenant?.id;

      // Handle file uploads for both create and edit
      const uploadErrors: string[] = [];

      if (logoFile && tenantId) {
        try {
          const formData = new FormData();
          formData.append("asset_type", "logo");
          formData.append("file", logoFile);
          formData.append("file_name", logoFile.name);
          await uploadTenantAsset(tenantId, formData);
        } catch (error) {
          uploadErrors.push(
            error instanceof Error ? error.message : "Logo upload failed",
          );
        }
      }

      if (markdownFile && tenantId) {
        try {
          const formData = new FormData();
          formData.append("asset_type", "markdown");
          formData.append("file", markdownFile);
          formData.append("file_name", markdownFile.name);
          await uploadTenantAsset(tenantId, formData);
        } catch (error) {
          uploadErrors.push(
            error instanceof Error ? error.message : "Document upload failed",
          );
        }
      }

      if (uploadErrors.length > 0) {
        toast.error(
          `Tenant ${isEdit ? "updated" : "created"}, but some files failed to upload`,
          {
            description: uploadErrors.join(" "),
          },
        );
      } else {
        toast.success(`Tenant ${isEdit ? "updated" : "created"} successfully`);
      }

      setOpen(false);
      onSuccess();
    } catch (error) {
      console.error(error);
      toast.error(`Failed to ${isEdit ? "update" : "create"} tenant`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const defaultTrigger = isEdit ? (
    <Button variant="outline" size="sm">
      <Pencil className="mr-2 h-4 w-4" />
      Edit
    </Button>
  ) : (
    <Button>
      <Plus className="mr-2 h-4 w-4" />
      Create Tenant
    </Button>
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {trigger && <DialogTrigger asChild>{trigger || defaultTrigger}</DialogTrigger>}
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Tenant" : "Create Tenant"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update tenant information and upload new assets."
              : "Add a new tenant with logo and documentation."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Acme Corp"
                required
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="status">Status</Label>
              <Select
                value={form.status}
                onValueChange={(value) =>
                  setForm((prev) => ({
                    ...prev,
                    status: value as "active" | "inactive",
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={form.description}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, description: e.target.value }))
                }
                placeholder="Brief description of the tenant..."
                rows={3}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>Logo</Label>
                <FileUpload
                  accept=".png,.jpg,.jpeg,.webp,.svg"
                  maxSize={2 * 1024 * 1024} // 2MB
                  onFileSelect={setLogoFile}
                  value={logoFile}
                  placeholder="Drop logo here or click to upload"
                  disabled={isSubmitting}
                />
                {!logoFile && existingLogoName ? (
                  <p className="text-muted-foreground text-xs">
                    Current: {existingLogoName}
                  </p>
                ) : null}
                <p className="text-muted-foreground text-xs">
                  PNG, JPG, WEBP, or SVG. Max 2MB.
                </p>
              </div>

              <div className="grid gap-2">
                <Label>Documentation</Label>
                <FileUpload
                  accept=".md,.txt"
                  maxSize={512 * 1024} // 512KB
                  onFileSelect={setMarkdownFile}
                  value={markdownFile}
                  placeholder="Drop document here or click to upload"
                  disabled={isSubmitting}
                />
                {!markdownFile && existingMarkdownName ? (
                  <p className="text-muted-foreground text-xs">
                    Current: {existingMarkdownName}
                  </p>
                ) : null}
                <p className="text-muted-foreground text-xs">
                  Markdown or text file. Max 512KB.
                </p>
              </div>
            </div>
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
            <Button
              type="submit"
              disabled={isSubmitting || form.name.trim().length < 2}
            >
              {isSubmitting
                ? `${isEdit ? "Updating" : "Creating"}...`
                : `${isEdit ? "Update" : "Create"} Tenant`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
