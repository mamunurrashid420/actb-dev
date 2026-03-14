"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  Database,
  FileText,
  Pencil,
  Plus,
  TestTube,
  Upload,
  Users,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { MarkdownRenderer } from "@/components/chat/chat-markdown";
import {
  getTenant,
  testExistingConnection,
  uploadTenantAsset,
} from "@/lib/actions/admin-actions";
import { TenantFormDialog } from "./tenant-form-dialog";
import { TenantConnectionsDialog } from "./tenant-connections-dialog";

type TenantDetails = {
  id: string;
  name: string | null;
  description: string | null;
  status: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type TenantAsset = {
  id: string;
  asset_type: "logo" | "markdown";
  file_name: string | null;
  file_size: number | null;
  signed_url?: string | null;
  content?: string | null;
};

type TenantConnection = {
  id: string;
  name: string;
  type: "postgres" | "mysql" | "bigquery";
  last_test_status: string | null;
  last_tested_at: string | null;
};

type TenantMember = {
  user_id: string;
  role: string;
  status: string;
  user?: { email: string; full_name: string | null } | null;
};

interface Props {
  tenantId: string;
}

export function TenantViewPage({ tenantId }: Props) {
  const router = useRouter();
  const [tenant, setTenant] = useState<TenantDetails | null>(null);
  const [assets, setAssets] = useState<TenantAsset[]>([]);
  const [connections, setConnections] = useState<TenantConnection[]>([]);
  const [members, setMembers] = useState<TenantMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [markdownModal, setMarkdownModal] = useState<string | null>(null);
  const [connectionsOpen, setConnectionsOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const tenantRes = await getTenant(tenantId, true);
      setTenant(tenantRes.tenant);
      setAssets(tenantRes.tenant.assets || []);
      setConnections(tenantRes.tenant.connections || []);
      setMembers(tenantRes.tenant.members || []);
    } catch (e) {
      console.error(e);
      toast.error("Failed to load tenant");
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const logoAsset = assets.find((a) => a.asset_type === "logo");
  const markdownAsset = assets.find((a) => a.asset_type === "markdown");

  const handleTestConnection = async (conn: TenantConnection) => {
    setTestingId(conn.id);
    try {
      await testExistingConnection(conn.id);
      toast.success("Connection test passed");
      await loadData();
    } catch {
      toast.error("Test failed");
    } finally {
      setTestingId(null);
    }
  };

  const handleDocUpload = async (file: File) => {
    if (file.size > 512 * 1024) {
      toast.error("File too large (max 512KB)");
      return;
    }
    setUploadingDoc(true);
    try {
      const formData = new FormData();
      formData.append("asset_type", "markdown");
      formData.append("file", file);
      formData.append("file_name", file.name);
      await uploadTenantAsset(tenantId, formData);
      toast.success("Document uploaded");
      loadData();
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploadingDoc(false);
    }
  };

  const formatRelative = (d: string | null | undefined) => {
    if (!d) return "—";
    try {
      return formatDistanceToNow(new Date(d), { addSuffix: true });
    } catch {
      return "—";
    }
  };

  const getTypeLabel = (t: string) =>
    t === "postgres"
      ? "PostgreSQL"
      : t === "mysql"
        ? "MySQL"
        : t === "bigquery"
          ? "BigQuery"
          : t;

  if (loading)
    return (
      <div className="text-muted-foreground flex min-h-[400px] items-center justify-center">
        Loading...
      </div>
    );
  if (!tenant)
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">Tenant not found</p>
        <Button variant="outline" onClick={() => router.push("/admin/tenants")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      </div>
    );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/admin/tenants")}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          {logoAsset?.signed_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={logoAsset.signed_url}
              alt="Logo"
              className="h-12 w-12 rounded-lg border object-contain"
            />
          ) : (
            <div className="bg-muted flex h-12 w-12 items-center justify-center rounded-lg border">
              <Building2 className="text-muted-foreground h-6 w-6" />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-semibold">{tenant.name || "Untitled"}</h1>
            {tenant.description && (
              <p className="text-muted-foreground text-sm">{tenant.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={tenant.status === "inactive" ? "outline" : "secondary"}
            className="capitalize"
          >
            {tenant.status || "active"}
          </Badge>
          <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex gap-8 text-sm">
        <div>
          <span className="text-muted-foreground">Members:</span>{" "}
          <span className="font-medium">{members.length}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Connections:</span>{" "}
          <span className="font-medium">{connections.length}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Created:</span>{" "}
          <span className="font-medium">{formatRelative(tenant.created_at)}</span>
        </div>
      </div>

      <Separator />

      {/* Documentation */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-medium">
            <FileText className="h-4 w-4" />
            Documentation
          </h2>
          <div className="relative">
            <input
              type="file"
              accept=".md,.txt"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleDocUpload(f);
                e.target.value = "";
              }}
              disabled={uploadingDoc}
              className="absolute inset-0 cursor-pointer opacity-0"
            />
            <Button variant="outline" size="sm" disabled={uploadingDoc}>
              <Upload className="mr-2 h-4 w-4" />
              {uploadingDoc ? "Uploading..." : markdownAsset ? "Replace" : "Upload"}
            </Button>
          </div>
        </div>
        {markdownAsset ? (
          <Button
            variant="ghost"
            className="h-auto justify-start px-0 text-left"
            onClick={() => setMarkdownModal(markdownAsset.content || "")}
          >
            <FileText className="text-muted-foreground mr-2 h-4 w-4" />
            <span>{markdownAsset.file_name}</span>
          </Button>
        ) : (
          <p className="text-muted-foreground text-sm">No documentation uploaded</p>
        )}
      </section>

      <Separator />

      {/* Database Connections */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-medium">
            <Database className="h-4 w-4" />
            Database Connections
          </h2>
          <Button variant="outline" size="sm" onClick={() => setConnectionsOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add
          </Button>
        </div>
        {connections.length === 0 ? (
          <p className="text-muted-foreground text-sm">No connections configured</p>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead className="w-[100px]">Type</TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                  <TableHead className="w-[80px] text-center">Test</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {connections.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.name}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {getTypeLabel(c.type)}
                    </TableCell>
                    <TableCell>
                      {c.last_test_status === "success" ? (
                        <Badge variant="secondary" className="gap-1">
                          <CheckCircle2 className="h-3 w-3" />
                          OK
                        </Badge>
                      ) : c.last_test_status === "error" ? (
                        <Badge variant="destructive" className="gap-1">
                          <XCircle className="h-3 w-3" />
                          Failed
                        </Badge>
                      ) : (
                        <Badge variant="outline">Untested</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                        onClick={() => handleTestConnection(c)}
                        disabled={testingId === c.id}
                      >
                        <TestTube
                          className={`h-4 w-4 ${testingId === c.id ? "animate-pulse" : ""}`}
                        />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <Separator />

      {/* Members */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-medium">
            <Users className="h-4 w-4" />
            Members
          </h2>
        </div>
        {members.length === 0 ? (
          <p className="text-muted-foreground text-sm">No members assigned</p>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead className="w-[120px]">Role</TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((m) => (
                  <TableRow key={m.user_id}>
                    <TableCell>
                      <div>{m.user?.full_name || "—"}</div>
                      <div className="text-muted-foreground text-xs">
                        {m.user?.email}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {m.role.replace("tenant_", "")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={m.status === "active" ? "secondary" : "outline"}
                        className="capitalize"
                      >
                        {m.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      {/* Dialogs */}
      <TenantConnectionsDialog
        tenant={tenant}
        open={connectionsOpen}
        onOpenChange={(open) => {
          setConnectionsOpen(open);
          if (!open) {
            void loadData();
          }
        }}
      />

      {editOpen && (
        <TenantFormDialog
          tenant={tenant}
          onSuccess={() => {
            setEditOpen(false);
            loadData();
          }}
          trigger={null}
        />
      )}

      <Dialog open={Boolean(markdownModal)} onOpenChange={() => setMarkdownModal(null)}>
        <DialogContent className="max-h-[85vh] sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>Documentation</DialogTitle>
          </DialogHeader>
          <ScrollArea className="h-[60vh] pr-4">
            <MarkdownRenderer markdown={markdownModal} />
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
}
