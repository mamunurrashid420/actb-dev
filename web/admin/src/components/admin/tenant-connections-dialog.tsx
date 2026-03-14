"use client";

import { useCallback, useEffect, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import {
  CheckCircle2,
  Database,
  Pencil,
  Plus,
  TestTube,
  Trash2,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
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
  createConnection,
  deleteConnection,
  listTenantConnections,
  testConnectionConfig,
  testExistingConnection,
  updateConnection,
} from "@/lib/actions/admin-actions";
import type { CreateConnectionInput, UpdateConnectionInput } from "@/lib/validations/tenant";

type TenantSummary = { id: string; name: string | null };

type TenantConnection = {
  id: string;
  name: string;
  type: "postgres" | "mysql" | "bigquery";
  is_active: boolean;
  last_test_status: string | null;
  last_tested_at: string | null;
  created_at: string | null;
};

type ConnectionForm = {
  name: string;
  type: "postgres" | "mysql" | "bigquery";
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
  project_id: string;
  dataset_id: string;
  credentials_json: string;
};

interface Props {
  tenant: TenantSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnectionCountChange?: (count: number) => void;
}

const emptyForm = (): ConnectionForm => ({
  name: "",
  type: "postgres",
  host: "",
  port: "",
  database: "",
  username: "",
  password: "",
  ssl: false,
  project_id: "",
  dataset_id: "",
  credentials_json: "",
});

export function TenantConnectionsDialog({
  tenant,
  open,
  onOpenChange,
  onConnectionCountChange,
}: Props) {
  const [connections, setConnections] = useState<TenantConnection[]>([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<"list" | "form">("list");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<ConnectionForm>(emptyForm());
  const [testing, setTesting] = useState(false);
  const [testStatus, setTestStatus] = useState<{ ok: boolean; message: string } | null>(
    null,
  );
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TenantConnection | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);

  const loadConnections = useCallback(async () => {
    if (!tenant) return;
    setLoading(true);
    try {
      const data = await listTenantConnections(tenant.id);
      const conns = data.connections || [];
      setConnections(conns);
      setView(conns.length === 0 ? "form" : "list");
      onConnectionCountChange?.(conns.length);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [onConnectionCountChange, tenant]);

  useEffect(() => {
    if (open && tenant) {
      setEditingId(null);
      setForm(emptyForm());
      setTestStatus(null);
      void loadConnections();
    }
  }, [loadConnections, open, tenant]);

  const buildConfig = () => {
    const config: Record<string, unknown> = {};
    if (form.type === "postgres" || form.type === "mysql") {
      if (form.host) config.host = form.host.trim();
      if (form.port) config.port = Number(form.port);
      if (form.database) config.database = form.database.trim();
      if (form.username) config.username = form.username.trim();
      if (form.password) config.password = form.password;
      if (form.ssl) config.ssl = true;
    } else if (form.type === "bigquery") {
      if (form.project_id) config.project_id = form.project_id.trim();
      if (form.dataset_id) config.dataset_id = form.dataset_id.trim();
      if (form.credentials_json) config.credentials_json = form.credentials_json.trim();
    }
    return config;
  };

  const handleTest = async () => {
    if (!tenant) return;
    setTesting(true);
    setTestStatus(null);
    try {
      await testConnectionConfig({
        tenant_id: tenant.id,
        type: form.type,
        connection_config: buildConfig(),
      });
      setTestStatus(
        { ok: true, message: "Connection successful" },
      );
    } catch (error) {
      setTestStatus({
        ok: false,
        message: error instanceof Error ? error.message : "Connection failed",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!tenant || !form.name.trim()) return;
    setSaving(true);
    try {
      if (editingId) {
        const payload: UpdateConnectionInput = {
          name: form.name.trim(),
          connection_config: buildConfig(),
        };
        await updateConnection(editingId, payload);
      } else {
        const payload: CreateConnectionInput = {
          tenant_id: tenant.id,
          type: form.type,
          name: form.name.trim(),
          connection_config: buildConfig(),
        };
        await createConnection(payload);
      }
      toast.success(editingId ? "Connection updated" : "Connection created");
      setView("list");
      setEditingId(null);
      setForm(emptyForm());
      setTestStatus(null);
      await loadConnections();
    } catch (e) {
      toast.error("Failed to save", {
        description: e instanceof Error ? e.message : "Error",
      });
    } finally {
      setSaving(false);
    }
  };

  // connection count is reported after loadConnections to avoid loops

  const handleTestExisting = async (conn: TenantConnection) => {
    setTestingId(conn.id);
    try {
      await testExistingConnection(conn.id);
      toast.success("Connection test passed");
      await loadConnections();
    } catch {
      toast.error("Test failed");
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteConnection(deleteTarget.id);
      toast.success("Connection deleted");
      setDeleteTarget(null);
      await loadConnections();
    } catch {
      toast.error("Failed to delete");
    } finally {
      setDeleting(false);
    }
  };

  const startEdit = (c: TenantConnection) => {
    setEditingId(c.id);
    setForm({ ...emptyForm(), name: c.name, type: c.type });
    setTestStatus(null);
    setView("form");
  };
  const startAdd = () => {
    setEditingId(null);
    setForm(emptyForm());
    setTestStatus(null);
    setView("form");
  };
  const formatRelative = (d: string | null) => {
    if (!d) return "Never";
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
  const hasConfig = Object.keys(buildConfig()).length > 0;
  const canSave = form.name.trim() && (editingId || testStatus?.ok || hasConfig);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              {tenant?.name} - Connections
            </DialogTitle>
          </DialogHeader>

          {view === "list" ? (
            <div className="space-y-4">
              <div className="flex justify-end">
                <Button size="sm" onClick={startAdd}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Connection
                </Button>
              </div>
              {loading ? (
                <div className="text-muted-foreground py-8 text-center text-sm">
                  Loading...
                </div>
              ) : connections.length === 0 ? (
                <div className="text-muted-foreground py-12 text-center">
                  <Database className="mx-auto mb-3 h-10 w-10 opacity-50" />
                  <p>No connections yet</p>
                </div>
              ) : (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead className="w-[100px]">Type</TableHead>
                        <TableHead className="w-[100px]">Status</TableHead>
                        <TableHead className="w-[120px]">Tested</TableHead>
                        <TableHead className="w-[120px] text-center">Actions</TableHead>
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
                          <TableCell className="text-muted-foreground text-sm">
                            {formatRelative(c.last_tested_at)}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center justify-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => handleTestExisting(c)}
                                disabled={testingId === c.id}
                                title="Test"
                              >
                                <TestTube
                                  className={`h-4 w-4 ${testingId === c.id ? "animate-pulse" : ""}`}
                                />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => startEdit(c)}
                                title="Edit"
                              >
                                <Pencil className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive h-8 w-8 p-0"
                                onClick={() => setDeleteTarget(c)}
                                title="Delete"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">
                  {editingId ? "Edit Connection" : "New Connection"}
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    connections.length > 0 ? setView("list") : onOpenChange(false)
                  }
                >
                  {connections.length > 0 ? "Cancel" : "Close"}
                </Button>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1">
                  <Label>Name</Label>
                  <Input
                    value={form.name}
                    onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                    placeholder="My Database"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Type</Label>
                  {editingId ? (
                    <Input value={getTypeLabel(form.type)} disabled />
                  ) : (
                    <Select
                      value={form.type}
                      onValueChange={(v) =>
                        setForm((p) => ({ ...p, type: v as ConnectionForm["type"] }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="postgres">PostgreSQL</SelectItem>
                        <SelectItem value="mysql">MySQL</SelectItem>
                        <SelectItem value="bigquery">BigQuery</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>
              {(form.type === "postgres" || form.type === "mysql") && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1">
                    <Label>Host</Label>
                    <Input
                      value={form.host}
                      onChange={(e) => setForm((p) => ({ ...p, host: e.target.value }))}
                      placeholder="localhost"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Port</Label>
                    <Input
                      value={form.port}
                      onChange={(e) => setForm((p) => ({ ...p, port: e.target.value }))}
                      placeholder={form.type === "postgres" ? "5432" : "3306"}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Database</Label>
                    <Input
                      value={form.database}
                      onChange={(e) =>
                        setForm((p) => ({ ...p, database: e.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Username</Label>
                    <Input
                      value={form.username}
                      onChange={(e) =>
                        setForm((p) => ({ ...p, username: e.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Password</Label>
                    <Input
                      type="password"
                      value={form.password}
                      onChange={(e) =>
                        setForm((p) => ({ ...p, password: e.target.value }))
                      }
                    />
                  </div>
                  <div className="flex items-center gap-2 pt-6">
                    <Switch
                      checked={form.ssl}
                      onCheckedChange={(c) => setForm((p) => ({ ...p, ssl: c }))}
                    />
                    <span className="text-sm">SSL</span>
                  </div>
                </div>
              )}
              {form.type === "bigquery" && (
                <div className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1">
                      <Label>Project ID</Label>
                      <Input
                        value={form.project_id}
                        onChange={(e) =>
                          setForm((p) => ({ ...p, project_id: e.target.value }))
                        }
                      />
                    </div>
                    <div className="space-y-1">
                      <Label>Dataset ID</Label>
                      <Input
                        value={form.dataset_id}
                        onChange={(e) =>
                          setForm((p) => ({ ...p, dataset_id: e.target.value }))
                        }
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label>Service Account JSON</Label>
                    <Textarea
                      value={form.credentials_json}
                      onChange={(e) =>
                        setForm((p) => ({ ...p, credentials_json: e.target.value }))
                      }
                      rows={5}
                    />
                  </div>
                </div>
              )}
              {testStatus && (
                <div
                  className={`rounded-md border px-3 py-2 text-sm ${testStatus.ok ? "border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400" : "border-destructive/30 bg-destructive/10 text-destructive"}`}
                >
                  {testStatus.message}
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={handleTest}
                  disabled={testing || !hasConfig}
                >
                  {testing ? "Testing..." : "Test"}
                </Button>
                <Button onClick={handleSave} disabled={!canSave || saving}>
                  {saving ? "Saving..." : editingId ? "Update" : "Create"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      <AlertDialog
        open={Boolean(deleteTarget)}
        onOpenChange={() => setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Connection</AlertDialogTitle>
            <AlertDialogDescription>
              Delete &quot;{deleteTarget?.name}&quot;? This cannot be undone.
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
    </>
  );
}
