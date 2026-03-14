"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Building2,
  Database,
  Eye,
  FileText,
  Pencil,
  Plus,
  RefreshCcw,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MarkdownRenderer } from "@/components/chat/chat-markdown";
import {
  deleteTenant as deleteTenantAction,
  listTenantAssets,
  uploadTenantAsset,
} from "@/lib/actions/admin-actions";
import { TenantFormDialog } from "./tenant-form-dialog";
import { TenantConnectionsDialog } from "./tenant-connections-dialog";

type TenantSummary = {
  id: string;
  name: string | null;
  description: string | null;
  status: string | null;
  logo_url: string | null;
  document_name: string | null;
  member_count?: number | null;
  connection_count?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

interface TenantTableProps {
  tenants: TenantSummary[];
  loading: boolean;
  onRefresh: () => void;
}

export function TenantTable({ tenants, loading, onRefresh }: TenantTableProps) {
  const router = useRouter();
  const [tenantRows, setTenantRows] = useState(tenants);
  const [tenantToDelete, setTenantToDelete] = useState<TenantSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [logoSignedUrls, setLogoSignedUrls] = useState<Record<string, string>>({});
  const [markdownModal, setMarkdownModal] = useState<{
    tenant: TenantSummary;
    content: string;
  } | null>(null);
  const [loadingMarkdown, setLoadingMarkdown] = useState<string | null>(null);
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);
  const [editingTenant, setEditingTenant] = useState<TenantSummary | null>(null);
  const [connectionsTenant, setConnectionsTenant] = useState<TenantSummary | null>(
    null,
  );

  // Sync with props when they change
  useEffect(() => {
    setTenantRows(tenants);
  }, [tenants]);

  // Load logo URLs for all tenants that have logos
  useEffect(() => {
    const loadLogos = async () => {
      const tenantsWithLogos = tenantRows.filter(
        (t) => t.logo_url && !logoSignedUrls[t.id],
      );
      for (const tenant of tenantsWithLogos) {
        try {
          const data = await listTenantAssets(tenant.id, false);
          const logoAsset = data.assets?.find(
            (a) => a.asset_type === "logo",
          );
          if (logoAsset?.signed_url) {
            setLogoSignedUrls((prev) => ({
              ...prev,
              [tenant.id]: logoAsset.signed_url as string,
            }));
          }
        } catch (error) {
          console.error("Failed to load logo URL:", error);
        }
      }
    };
    if (tenantRows.length > 0) {
      loadLogos();
    }
  }, [tenantRows, logoSignedUrls]);

  const uploadAsset = async (
    tenantId: string,
    assetType: "logo" | "markdown",
    file: File,
  ) => {
    const formData = new FormData();
    formData.append("asset_type", assetType);
    formData.append("file", file);
    formData.append("file_name", file.name);
    return uploadTenantAsset(tenantId, formData);
  };

  const handleDocumentUpload = async (tenantId: string, file: File) => {
    setUploadingDoc(tenantId);
    try {
      await uploadAsset(tenantId, "markdown", file);
      toast.success("Document uploaded");
      onRefresh();
    } catch (error) {
      toast.error("Upload failed", {
        description: error instanceof Error ? error.message : "Error",
      });
    } finally {
      setUploadingDoc(null);
    }
  };

  const handleViewMarkdown = async (tenant: TenantSummary) => {
    setLoadingMarkdown(tenant.id);
    try {
      const data = await listTenantAssets(tenant.id, true);
      const markdownAsset = data.assets?.find(
        (a) => a.asset_type === "markdown",
      );
      if (markdownAsset?.content) {
        setMarkdownModal({ tenant, content: markdownAsset.content });
      } else {
        toast.error("No content available");
      }
    } catch {
      toast.error("Failed to load document");
    } finally {
      setLoadingMarkdown(null);
    }
  };

  const handleDelete = async () => {
    if (!tenantToDelete) return;
    setDeleting(true);
    try {
      await deleteTenantAction(tenantToDelete.id);
      toast.success("Tenant deleted");
      onRefresh();
    } catch (error) {
      toast.error("Delete failed", {
        description: error instanceof Error ? error.message : "Error",
      });
    } finally {
      setDeleting(false);
      setTenantToDelete(null);
    }
  };

  const handleConnectionCountChange = useCallback((tenantId: string, count: number) => {
    setTenantRows((prev) =>
      prev.map((t) => (t.id === tenantId ? { ...t, connection_count: count } : t)),
    );
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tenants</h1>
          <p className="text-muted-foreground text-sm">Manage tenant organizations</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <TenantFormDialog
            onSuccess={onRefresh}
            trigger={
              <Button size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Tenant
              </Button>
            }
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[60px]">Logo</TableHead>
              <TableHead>Tenant</TableHead>
              <TableHead className="w-[100px]">Status</TableHead>
              <TableHead className="w-[100px]">Members</TableHead>
              <TableHead className="w-[100px]">Connections</TableHead>
              <TableHead className="w-[140px]">Document</TableHead>
              <TableHead className="w-[100px] text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-muted-foreground py-8 text-center"
                >
                  Loading tenants...
                </TableCell>
              </TableRow>
            ) : tenantRows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-muted-foreground py-8 text-center"
                >
                  No tenants found. Create your first tenant to get started.
                </TableCell>
              </TableRow>
            ) : (
              tenantRows.map((tenant) => (
                <TableRow key={tenant.id}>
                  <TableCell>
                    <div className="flex items-center justify-center">
                      {tenant.logo_url && logoSignedUrls[tenant.id] ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={logoSignedUrls[tenant.id]}
                          alt={`${tenant.name} logo`}
                          className="h-8 w-8 rounded border object-contain"
                        />
                      ) : (
                        <div className="bg-muted flex h-8 w-8 items-center justify-center rounded border">
                          <Building2 className="text-muted-foreground h-4 w-4" />
                        </div>
                      )}
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="space-y-1">
                      <div className="font-medium">
                        {tenant.name || "Untitled Tenant"}
                      </div>
                      {tenant.description && (
                        <div className="text-muted-foreground line-clamp-1 text-sm">
                          {tenant.description}
                        </div>
                      )}
                    </div>
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant={tenant.status === "inactive" ? "outline" : "secondary"}
                      className="capitalize"
                    >
                      {tenant.status || "active"}
                    </Badge>
                  </TableCell>

                  <TableCell className="text-center">
                    <span className="font-medium">{tenant.member_count || 0}</span>
                  </TableCell>

                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConnectionsTenant(tenant)}
                      className="h-8 gap-1 px-2"
                    >
                      {(tenant.connection_count ?? 0) > 0 ? (
                        <>
                          <Database className="h-3.5 w-3.5" />
                          <span className="font-medium">{tenant.connection_count}</span>
                        </>
                      ) : (
                        <Plus className="h-4 w-4" />
                      )}
                    </Button>
                  </TableCell>

                  <TableCell>
                    {tenant.document_name ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewMarkdown(tenant)}
                        disabled={loadingMarkdown === tenant.id}
                        className="h-8 max-w-[120px] truncate px-2 text-xs"
                      >
                        {loadingMarkdown === tenant.id ? (
                          <span className="animate-pulse">Loading...</span>
                        ) : (
                          <>
                            <FileText className="mr-1 h-3 w-3 flex-shrink-0" />
                            <span className="truncate">{tenant.document_name}</span>
                          </>
                        )}
                      </Button>
                    ) : (
                      <div className="relative">
                        <input
                          type="file"
                          accept=".md,.txt"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file && file.size <= 512 * 1024) {
                              handleDocumentUpload(tenant.id, file);
                            } else if (file) {
                              toast.error("File too large. Max 512KB.");
                            }
                            e.target.value = "";
                          }}
                          disabled={uploadingDoc === tenant.id}
                          className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={uploadingDoc === tenant.id}
                          className="h-8 px-2 text-xs"
                        >
                          <Upload className="mr-1 h-3 w-3" />
                          {uploadingDoc === tenant.id ? "..." : "Upload"}
                        </Button>
                      </div>
                    )}
                  </TableCell>

                  <TableCell>
                    <div className="flex items-center justify-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => router.push(`/admin/tenants/${tenant.id}`)}
                        className="h-8 w-8 p-0"
                        title="View details"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditingTenant(tenant)}
                        className="h-8 w-8 p-0"
                        title="Edit tenant"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setTenantToDelete(tenant)}
                        className="text-destructive hover:text-destructive h-8 w-8 p-0"
                        title="Delete tenant"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Edit Tenant Dialog */}
      {editingTenant && (
        <TenantFormDialog
          tenant={editingTenant}
          onSuccess={() => {
            setEditingTenant(null);
            onRefresh();
          }}
          trigger={null}
        />
      )}

      {/* Connections Dialog */}
      <TenantConnectionsDialog
        tenant={connectionsTenant}
        open={Boolean(connectionsTenant)}
        onOpenChange={(open) => !open && setConnectionsTenant(null)}
        onConnectionCountChange={(count) =>
          connectionsTenant && handleConnectionCountChange(connectionsTenant.id, count)
        }
      />

      {/* Markdown Viewer Modal */}
      <Dialog open={Boolean(markdownModal)} onOpenChange={() => setMarkdownModal(null)}>
        <DialogContent className="max-h-[85vh] sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>{markdownModal?.tenant.name} - Documentation</DialogTitle>
          </DialogHeader>
          <ScrollArea className="h-[60vh] pr-4">
            <div className="p-4">
              <MarkdownRenderer markdown={markdownModal?.content} />
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={Boolean(tenantToDelete)}
        onOpenChange={() => setTenantToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Tenant</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;
              {tenantToDelete?.name || "this tenant"}&quot;? This action cannot be undone
              and will remove all associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
