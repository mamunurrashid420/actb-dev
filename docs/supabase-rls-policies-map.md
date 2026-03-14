# ActBI RLS Policies Map

**Purpose:** Which tables have RLS and what to exercise in dev. Used for Project 1 seed data and testing.

## Tables with RLS (service/supabase migrations)

| Table | Migration | Policies (summary) | Dev test focus |
|-------|-----------|--------------------|----------------|
| **tenants** | 04, 15 | Select: tenant member or app permission; Update/Delete: tenant superadmin | Only see tenants where user is in `tenant_users`. |
| **tenant_users** | 04, 15 | Select: self or admin; Insert/Update/Delete: tenant admin | Tenant admin can manage members. |
| **dashboards** | 15 | Select: owner, superadmin, creator, or tenant member if shared; Insert: owner + creator; Update: owner/superadmin/creator | Tenant isolation; creator can create. |
| **conversations** | 01, 15 | Same pattern as dashboards (owner, tenant, share_tenant_role) | Tenant isolation; creator can create. |
| **reports** | 15 | Same pattern (tenant member, owner, superadmin, creator) | Tenant isolation. |
| **tenant_database_connections** | 15 | Select: tenant member; Manage: tenant superadmin | Only superadmin per tenant. |
| **tenant_assets** | 15 | Select: tenant member; Manage: tenant superadmin | Only superadmin per tenant. |
| **storage.objects** (tenant-assets) | 15 | Read/Manage: path = `tenant_id/...` and user in that tenant | Tenant-scoped storage. |
| **user_profiles** | 15 | Self + tenant admin read | Profile visibility. |
| **messages** | 01 | Via conversation (own or shared) | Through conversation RLS. |

## Helper functions (used by RLS)

- `is_superadmin(user_id, tenant_id)` — tenant_users.role = 'superadmin'
- `is_tenant_admin(user_id, tenant_id)` — role in ('admin', 'superadmin')
- `is_tenant_creator(user_id, tenant_id)` — role = 'creator'
- `user_has_permission(uid, permission)` — app-level permissions (e.g. users.read, tenants.manage)

## Seed data to exercise RLS

- **Two tenants** with different `tenant_id`s.
- **tenant_users:** Same user in one tenant only; different users as admin/creator/viewer so policies apply.
- **dashboards / conversations:** At least one row per tenant with correct `tenant_id` and `owner_user_id` (user_profiles.id), so that:
  - Logged in as Tenant A member: see only Tenant A’s dashboards/conversations.
  - Logged in as Tenant B member: see only Tenant B’s.

See `service/supabase/seed.sql` for the concrete seed (two tenants, members, dashboards, conversations).
