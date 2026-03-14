"use server";

import { extname } from "node:path";

import { z } from "zod";

import { API_BASE_URL } from "@/lib/auth/constants";
import { getAccessToken } from "@/lib/auth/session";
import { requireSuperadmin } from "@/lib/auth/require-superadmin";
import { apiServerRequest } from "@/lib/api-server";
import {
  createConnectionSchema,
  createTenantSchema,
  tenantStatusSchema,
  testConnectionSchema,
  updateConnectionSchema,
  updateTenantSchema,
  uploadAssetSchema,
} from "@/lib/validations/tenant";

const MAX_LOGO_BYTES = 2 * 1024 * 1024;
const MAX_MARKDOWN_BYTES = 512 * 1024;

const LOGO_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/svg+xml",
]);
const MARKDOWN_MIME_TYPES = new Set(["text/markdown", "text/plain"]);

const sanitizeFileName = (name: string) => name.replace(/[^\w.-]+/g, "_");

export async function listTenants(options?: {
  page?: number;
  limit?: number;
  search?: string;
  status?: string | null;
}) {
  await requireSuperadmin();
  const params = new URLSearchParams();
  params.set("page", String(options?.page ?? 1));
  params.set("limit", String(options?.limit ?? 50));
  if (options?.search) params.set("search", options.search);
  if (options?.status) params.set("status_value", options.status);
  return await apiServerRequest<{
    tenants: unknown[];
    pagination: { page: number; limit: number; total: number; totalPages: number };
  }>("GET", `/admin/tenants?${params.toString()}`);
}

export async function createTenant(payload: z.infer<typeof createTenantSchema>) {
  await requireSuperadmin();
  const validated = createTenantSchema.parse(payload);
  return await apiServerRequest<{
    tenant: {
      id: string;
      name: string;
      description: string | null;
      status: string;
      branding?: Record<string, unknown> | null;
      created_at?: string | null;
      updated_at?: string | null;
    };
  }>("POST", "/admin/tenants", validated);
}

export async function updateTenant(
  tenantId: string,
  payload: z.infer<typeof updateTenantSchema>,
) {
  await requireSuperadmin();
  const validated = updateTenantSchema.parse(payload);
  return await apiServerRequest<{
    tenant: {
      id: string;
      name: string;
      description: string | null;
      status: string;
      branding?: Record<string, unknown> | null;
      created_at?: string | null;
      updated_at?: string | null;
    };
  }>("PUT", `/admin/tenants/${tenantId}`, validated);
}

export async function updateTenantStatus(
  tenantId: string,
  payload: z.infer<typeof tenantStatusSchema>,
) {
  await requireSuperadmin();
  const validated = tenantStatusSchema.parse(payload);
  return await apiServerRequest("PUT", `/admin/tenants/${tenantId}/status`, validated);
}

export async function deleteTenant(tenantId: string) {
  await requireSuperadmin();
  return await apiServerRequest("DELETE", `/admin/tenants/${tenantId}`);
}

export async function getTenant(tenantId: string, includeAssetsContent = false) {
  await requireSuperadmin();
  const params = new URLSearchParams();
  if (includeAssetsContent) params.set("include_assets_content", "true");
  const query = params.toString();
  return await apiServerRequest<{
    tenant: {
      id: string;
      name: string | null;
      description: string | null;
      status: string | null;
      branding?: Record<string, unknown> | null;
      context_metadata?: Record<string, unknown> | null;
      logo_url?: string | null;
      document_name?: string | null;
      created_at?: string | null;
      updated_at?: string | null;
      member_count?: number | null;
      active_members?: number | null;
      admins?: Array<{ user_id: string; role: string; status: string }>;
      assets?: Array<{
        id: string;
        asset_type: "logo" | "markdown";
        storage_path?: string | null;
        file_name: string | null;
        file_size: number | null;
        content_type: string | null;
        created_at?: string | null;
        signed_url?: string | null;
        content?: string | null;
      }>;
      connections?: Array<{
        id: string;
        name: string;
        type: "postgres" | "mysql" | "bigquery";
        is_active: boolean;
        last_test_status: string | null;
        last_tested_at: string | null;
        created_at?: string | null;
      }>;
      members?: Array<{
        user_id: string;
        role: string;
        status: string;
        invited_at?: string | null;
        accepted_at?: string | null;
        user?: { email: string; full_name: string | null } | null;
      }>;
    };
  }>("GET", `/admin/tenants/${tenantId}${query ? `?${query}` : ""}`);
}

export async function listTenantAssets(tenantId: string, includeContent = false) {
  await requireSuperadmin();
  const params = new URLSearchParams();
  if (includeContent) params.set("include_content", "true");
  const query = params.toString();
  return await apiServerRequest<{
    assets: Array<{
      id: string;
      asset_type: "logo" | "markdown";
      storage_path?: string | null;
      file_name: string | null;
      file_size: number | null;
      content_type: string | null;
      created_at?: string | null;
      signed_url?: string | null;
      content?: string | null;
    }>;
  }>(
    "GET",
    `/admin/tenants/${tenantId}/assets${query ? `?${query}` : ""}`,
  );
}

export async function uploadTenantAsset(tenantId: string, formData: FormData) {
  await requireSuperadmin();
  const assetTypeRaw = formData.get("asset_type");
  const file = formData.get("file");
  const fileNameOverride = formData.get("file_name");

  const assetType = typeof assetTypeRaw === "string" ? assetTypeRaw : "";
  const fileName =
    typeof fileNameOverride === "string" && fileNameOverride.trim() !== ""
      ? fileNameOverride.trim()
      : file instanceof File
        ? file.name
        : "";

  const parsed = uploadAssetSchema.safeParse({
    tenant_id: tenantId,
    asset_type: assetType,
    file,
    file_name: fileName,
  });

  if (!parsed.success) {
    throw new Error("Invalid input");
  }

  if (!(file instanceof File)) {
    throw new Error("File is required");
  }

  const contentType = file.type || "application/octet-stream";
  const sanitizedFileName = sanitizeFileName(fileName || "upload");

  if (assetType === "logo") {
    if (!LOGO_MIME_TYPES.has(contentType)) {
      throw new Error("Logo must be a PNG, JPEG, WEBP, or SVG image.");
    }
    if (file.size > MAX_LOGO_BYTES) {
      throw new Error("Logo must be 2MB or smaller.");
    }
  } else if (assetType === "markdown") {
    if (file.size > MAX_MARKDOWN_BYTES) {
      throw new Error("Markdown file must be 512KB or smaller.");
    }
    const ext = extname(sanitizedFileName).toLowerCase();
    if (ext && ext !== ".md") {
      throw new Error("Markdown file must use .md extension.");
    }
    if (contentType && !MARKDOWN_MIME_TYPES.has(contentType) && ext !== ".md") {
      throw new Error("Markdown file must be plain text or markdown.");
    }
  }

  const token = await getAccessToken();
  const response = await fetch(`${API_BASE_URL}/admin/tenants/${tenantId}/assets`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
    cache: "no-store",
  });

  if (!response.ok) {
    let message = "Upload failed";
    try {
      const data = await response.json();
      message = data.detail || data.error || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return await response.json();
}

export async function listTenantConnections(tenantId: string) {
  await requireSuperadmin();
  return await apiServerRequest<{
    connections: Array<{
      id: string;
      name: string;
      type: "postgres" | "mysql" | "bigquery";
      is_active: boolean;
      last_test_status: string | null;
      last_tested_at: string | null;
      created_at: string | null;
    }>;
  }>("GET", `/admin/tenants/${tenantId}/connections`);
}

export async function listTenantMembers(tenantId: string) {
  await requireSuperadmin();
  return await apiServerRequest<{
    members: Array<{
      user_id: string;
      role: string;
      status: string;
      invited_at?: string | null;
      accepted_at?: string | null;
      user?: { email: string; full_name: string | null } | null;
    }>;
  }>("GET", `/admin/tenants/${tenantId}/members`);
}

export async function testConnectionConfig(payload: z.infer<typeof testConnectionSchema>) {
  await requireSuperadmin();
  const validated = testConnectionSchema.parse(payload);
  return await apiServerRequest("POST", "/admin/connections/test", validated);
}

export async function createConnection(payload: z.infer<typeof createConnectionSchema>) {
  await requireSuperadmin();
  const validated = createConnectionSchema.parse(payload);
  return await apiServerRequest("POST", "/admin/connections", validated);
}

export async function updateConnection(
  connectionId: string,
  payload: z.infer<typeof updateConnectionSchema>,
) {
  await requireSuperadmin();
  const parsed = updateConnectionSchema.parse(payload);
  return await apiServerRequest("PUT", `/admin/connections/${connectionId}`, parsed);
}

export async function deleteConnection(connectionId: string) {
  await requireSuperadmin();
  return await apiServerRequest("DELETE", `/admin/connections/${connectionId}`);
}

export async function testExistingConnection(connectionId: string) {
  await requireSuperadmin();
  return await apiServerRequest("POST", `/admin/connections/${connectionId}/test`);
}

const UserRoleSchema = z.enum(["superadmin", "admin", "creator", "viewer"]);

const InviteUserSchema = z.object({
  email: z.string().email(),
  tenantId: z.string().uuid().optional(),
  role: UserRoleSchema.optional(),
});

type InviteUserResponse = {
  userId: string;
  email: string;
  fullName: string;
  tenantId: string | null;
  status: string;
};

export async function inviteUser(payload: z.infer<typeof InviteUserSchema>) {
  await requireSuperadmin();
  const { email, tenantId, role } = InviteUserSchema.parse(payload);
  return await apiServerRequest<InviteUserResponse>("POST", "/admin/users/invite", {
    email,
    tenant_id: tenantId,
    role,
  });
}

const CreateUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  fullName: z.string().trim().max(200).optional(),
  tenantId: z.string().uuid().optional(),
  role: UserRoleSchema.optional(),
});

export async function createUser(payload: z.infer<typeof CreateUserSchema>) {
  await requireSuperadmin();
  const { email, password, fullName, tenantId, role } = CreateUserSchema.parse(payload);
  return await apiServerRequest<InviteUserResponse>("POST", "/admin/users", {
    email,
    password,
    full_name: fullName,
    tenant_id: tenantId,
    role,
  });
}

const ResendInviteSchema = z.object({
  email: z.string().email(),
  tenantId: z.string().uuid().optional(),
});

export async function resendInvite(payload: z.infer<typeof ResendInviteSchema>) {
  await requireSuperadmin();
  const { email, tenantId } = ResendInviteSchema.parse(payload);
  return await apiServerRequest("POST", "/admin/users/resend-invite", {
    email,
    tenant_id: tenantId,
  });
}

const UpdateUserSchema = z.object({
  userId: z.string().uuid(),
  fullName: z.string().trim().optional(),
  tenantId: z.string().uuid().optional(),
  role: UserRoleSchema.optional(),
});

export async function updateUser(payload: z.infer<typeof UpdateUserSchema>) {
  await requireSuperadmin();
  const { userId, fullName, tenantId, role } = UpdateUserSchema.parse(payload);
  return await apiServerRequest("PUT", `/admin/users/${userId}`, {
    full_name: fullName,
    tenant_id: tenantId,
    role,
  });
}

export async function deleteUser(userId: string) {
  await requireSuperadmin();
  return await apiServerRequest("DELETE", `/admin/users/${userId}`);
}
