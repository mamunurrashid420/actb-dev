import { z } from "zod";

export const createTenantSchema = z.object({
  name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(100, "Name must be less than 100 characters"),
  description: z
    .string()
    .max(500, "Description must be less than 500 characters")
    .optional(),
  status: z.enum(["active", "inactive"]).optional(),
  branding: z
    .object({
      logo_url: z.string().url().optional(),
      primary_color: z
        .string()
        .regex(/^#[0-9A-Fa-f]{6}$/, "Must be a valid hex color")
        .optional(),
      secondary_color: z
        .string()
        .regex(/^#[0-9A-Fa-f]{6}$/, "Must be a valid hex color")
        .optional(),
      theme: z.enum(["light", "dark", "auto"]).optional(),
    })
    .optional(),
});

export const updateTenantSchema = z.object({
  name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(100, "Name must be less than 100 characters")
    .optional(),
  description: z
    .string()
    .max(500, "Description must be less than 500 characters")
    .nullable()
    .optional(),
  status: z.enum(["active", "inactive"]).optional(),
  branding: z
    .object({
      logo_url: z.string().url().optional(),
      primary_color: z
        .string()
        .regex(/^#[0-9A-Fa-f]{6}$/, "Must be a valid hex color")
        .optional(),
      secondary_color: z
        .string()
        .regex(/^#[0-9A-Fa-f]{6}$/, "Must be a valid hex color")
        .optional(),
      theme: z.enum(["light", "dark", "auto"]).optional(),
    })
    .optional(),
  context_metadata: z.record(z.any()).optional(),
});

export const tenantStatusSchema = z.object({
  status: z.enum(["active", "inactive"]),
});

// Database connection schemas
export const createConnectionSchema = z.object({
  tenant_id: z.string().uuid("Invalid tenant ID"),
  name: z
    .string()
    .min(1, "Name is required")
    .max(100, "Name must be less than 100 characters"),
  type: z.enum(["postgres", "mysql", "bigquery"]),
  connection_config: z.object({
    // PostgreSQL
    host: z.string().optional(),
    port: z.number().int().min(1).max(65535).optional(),
    database: z.string().optional(),
    username: z.string().optional(),
    password: z.string().optional(),
    ssl: z.boolean().optional(),

    // MySQL
    hostname: z.string().optional(),

    // BigQuery
    project_id: z.string().optional(),
    dataset_id: z.string().optional(),
    key_file_path: z.string().optional(),
    credentials_json: z.string().optional(),
  }),
});

export const updateConnectionSchema = z.object({
  name: z
    .string()
    .min(1, "Name is required")
    .max(100, "Name must be less than 100 characters")
    .optional(),
  connection_config: z
    .object({
      host: z.string().optional(),
      port: z.number().int().min(1).max(65535).optional(),
      database: z.string().optional(),
      username: z.string().optional(),
      password: z.string().optional(),
      ssl: z.boolean().optional(),
      hostname: z.string().optional(),
      project_id: z.string().optional(),
      dataset_id: z.string().optional(),
      key_file_path: z.string().optional(),
      credentials_json: z.string().optional(),
    })
    .optional(),
  is_active: z.boolean().optional(),
});

export const testConnectionSchema = z.object({
  tenant_id: z.string().uuid("Invalid tenant ID"),
  type: z.enum(["postgres", "mysql", "bigquery"]),
  connection_config: z.record(z.any()),
});

// Asset upload schemas
export const uploadAssetSchema = z.object({
  tenant_id: z.string().uuid("Invalid tenant ID"),
  asset_type: z.enum(["logo", "markdown"]),
  file: z.any(), // Will be validated in the route handler
  file_name: z.string().optional(),
});

export const updateAssetSchema = z.object({
  file_name: z.string().optional(),
  // Add other updatable fields as needed
});

export type CreateTenantInput = z.infer<typeof createTenantSchema>;
export type UpdateTenantInput = z.infer<typeof updateTenantSchema>;
export type TenantStatusInput = z.infer<typeof tenantStatusSchema>;
export type CreateConnectionInput = z.infer<typeof createConnectionSchema>;
export type UpdateConnectionInput = z.infer<typeof updateConnectionSchema>;
export type TestConnectionInput = z.infer<typeof testConnectionSchema>;
export type UploadAssetInput = z.infer<typeof uploadAssetSchema>;
export type UpdateAssetInput = z.infer<typeof updateAssetSchema>;
