"use client";

import { useState } from "react";

import { CheckCircle2, Play, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API_BASE_URL } from "@/lib/auth/constants";

const DEMO_EMAIL = "superadmin@actbi.ai";
const DEMO_PASSWORD = "12345678";

type LogEntry = {
  id: string;
  status: "ok" | "error" | "info";
  message: string;
};

export default function ApiTestPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [sendInvite, setSendInvite] = useState(false);
  const [emailOverride, setEmailOverride] = useState("");
  const [passwordOverride, setPasswordOverride] = useState("");

  const addLog = (status: LogEntry["status"], message: string) => {
    setLogs((prev) => [
      ...prev,
      { id: `${Date.now()}-${Math.random()}`, status, message },
    ]);
  };

  const apiRequest = async (
    token: string,
    method: string,
    path: string,
    body?: unknown,
  ) => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      let detail = "Request failed";
      try {
        const data = await response.json();
        detail = data.detail || data.error || detail;
      } catch {
        // ignore
      }
      throw new Error(detail);
    }

    if (response.status === 204) {
      return null;
    }

    return response.json();
  };

  const runTests = async () => {
    setRunning(true);
    setLogs([]);

    const email = emailOverride.trim() || DEMO_EMAIL;
    const password = passwordOverride.trim() || DEMO_PASSWORD;
    const suffix = Date.now();

    let token = "";
    let tenantId = "";
    let roleId = "";
    let permissionId = "";
    let appUserId = "";
    let tenantUserId = "";

    try {
      addLog("info", "Logging in with demo credentials...");
      const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!loginResponse.ok) {
        const detail = await loginResponse.json().catch(() => ({}));
        throw new Error(detail.detail || detail.error || "Login failed");
      }

      const loginData = await loginResponse.json();
      token = loginData.access_token;
      addLog("ok", "Login success");

      const tenantName = `API Test Tenant ${suffix}`;
      const tenant = await apiRequest(token, "POST", "/tenants", {
        name: tenantName,
        description: "API test tenant",
        status: "active",
      });
      tenantId = tenant.id;
      addLog("ok", `Tenant created (${tenantName})`);

      await apiRequest(token, "PUT", `/tenants/${tenantId}`, {
        description: "Updated via API test",
        status: "active",
      });
      addLog("ok", "Tenant updated");

      await apiRequest(
        token,
        "GET",
        `/tenants?search=${encodeURIComponent(tenantName)}`,
      );
      addLog("ok", "Tenant list verified");

      const permissionName = `api_test_permission_${suffix}`;
      const permission = await apiRequest(token, "POST", "/permissions", {
        name: permissionName,
        description: "API test permission",
        resource: "api_test",
        action: "read",
      });
      permissionId = permission.id;
      addLog("ok", "Permission created");

      const roleName = `api_test_role_${suffix}`;
      const role = await apiRequest(token, "POST", "/roles", {
        name: roleName,
        description: "API test role",
      });
      roleId = role.id;
      addLog("ok", "Role created");

      await apiRequest(token, "PUT", `/roles/${roleId}/permissions`, {
        permissions: [permissionName],
      });
      addLog("ok", "Role permissions updated");

      const appUserEmail = `api-test-app+${suffix}@actbi.ai`;
      const appUser = await apiRequest(token, "POST", "/users", {
        email: appUserEmail,
        role_id: roleId,
        password: "TempPass123!",
        send_invite: false,
        tenant_assignments: [
          {
            tenant_id: tenantId,
            role: "tenant_admin",
          },
        ],
      });
      appUserId = appUser.id;
      addLog("ok", "App user created with tenant assignment");

      if (sendInvite) {
        const inviteEmail = `api-test-invite+${suffix}@actbi.ai`;
        await apiRequest(token, "POST", "/auth/invite", {
          email: inviteEmail,
          redirect_to: `${window.location.origin}/auth/accept-invite`,
        });
        addLog("ok", "Invite email sent");
      }

      const tenantUserEmail = `api-test-tenant+${suffix}@actbi.ai`;
      const tenantMember = await apiRequest(
        token,
        "POST",
        `/tenants/${tenantId}/members/invite`,
        {
          email: tenantUserEmail,
          role: "tenant_viewer",
          send_invite: sendInvite,
          password: sendInvite ? null : "TempPass123!",
          redirect_to: sendInvite
            ? `${window.location.origin}/auth/accept-invite`
            : null,
        },
      );
      tenantUserId = tenantMember.user_id;
      addLog("ok", "Tenant user created via tenant endpoint");

      await apiRequest(token, "GET", `/tenants/${tenantId}/members`);
      addLog("ok", "Tenant members listed");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Test failed";
      addLog("error", message);
    } finally {
      if (token) {
        try {
          if (tenantUserId) {
            await apiRequest(token, "DELETE", `/users/${tenantUserId}`);
            addLog("ok", "Tenant test user deleted");
          }
          if (appUserId) {
            await apiRequest(token, "DELETE", `/users/${appUserId}`);
            addLog("ok", "App test user deleted");
          }
          if (roleId) {
            await apiRequest(token, "DELETE", `/roles/${roleId}`);
            addLog("ok", "Role deleted");
          }
          if (permissionId) {
            await apiRequest(token, "DELETE", `/permissions/${permissionId}`);
            addLog("ok", "Permission deleted");
          }
          if (tenantId) {
            await apiRequest(token, "DELETE", `/tenants/${tenantId}`);
            addLog("ok", "Tenant deleted");
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : "Cleanup failed";
          addLog("error", message);
        }
      }
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">API Test Runner</h1>
        <p className="text-muted-foreground text-sm">
          Runs a full CRUD pass against tenants, roles, permissions, and users using
          demo credentials.
        </p>
      </header>

      <div className="space-y-4 rounded-md border p-4">
        <div className="space-y-2">
          <Label htmlFor="demo-email">Demo email</Label>
          <Input
            id="demo-email"
            value={emailOverride}
            placeholder={DEMO_EMAIL}
            onChange={(event) => setEmailOverride(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="demo-password">Demo password</Label>
          <Input
            id="demo-password"
            type="password"
            value={passwordOverride}
            placeholder={DEMO_PASSWORD}
            onChange={(event) => setPasswordOverride(event.target.value)}
          />
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="send-invite"
            checked={sendInvite}
            onCheckedChange={(checked) => setSendInvite(Boolean(checked))}
          />
          <Label htmlFor="send-invite" className="text-sm font-normal">
            Send invite emails during test run
          </Label>
        </div>
        <Button onClick={runTests} disabled={running}>
          <Play className="mr-2 h-4 w-4" />
          {running ? "Running..." : "Run API tests"}
        </Button>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold">Run log</h2>
        <div className="space-y-2 rounded-md border p-4 text-sm">
          {logs.length === 0 ? (
            <div className="text-muted-foreground">No runs yet.</div>
          ) : (
            logs.map((entry) => (
              <div key={entry.id} className="flex items-start gap-2">
                {entry.status === "ok" ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-500" />
                ) : entry.status === "error" ? (
                  <XCircle className="text-destructive mt-0.5 h-4 w-4" />
                ) : (
                  <span className="bg-muted mt-0.5 h-4 w-4 rounded-full" />
                )}
                <span>{entry.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
