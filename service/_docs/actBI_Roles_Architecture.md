# actBI Roles & Access Architecture (App Admin + Tenant Roles)

This note summarizes how **app admin** vs **tenant roles** are represented and enforced in the current codebase.

## 1) Where roles live

### App‑level admin
- **Table:** `user_profiles`
- **Field:** `is_app_admin` (boolean)
- **Purpose:** marks global app admins (superadmin capability across tenants)

### Tenant roles
- **Table:** `tenant_users`
- **Field:** `role` (enum text: `superadmin | admin | creator | viewer`)
- **Purpose:** per‑tenant membership + permissions


## 2) Core tables

### `user_profiles`
```sql
id UUID PRIMARY KEY REFERENCES auth.users(id)
email TEXT UNIQUE
full_name / display_name
is_app_admin BOOLEAN DEFAULT FALSE
created_at / updated_at
```

### `tenant_users`
```sql
tenant_id UUID REFERENCES tenants(id)
user_id UUID REFERENCES user_profiles(id)
role TEXT CHECK (role IN ('superadmin','admin','creator','viewer'))
status TEXT CHECK (status IN ('active','inactive'))
created_at / updated_at
UNIQUE(tenant_id, user_id)
```

> **App‑admin** is global (user_profiles). **Tenant role** is per‑tenant (tenant_users).


## 3) API surface (admin)

### List users
`GET /admin/users`
- Joins `users` view + `tenant_users`
- Returns: `status`, `tenant_id`, `role`, and timestamps

### Invite / Create user
`POST /admin/users/invite`
`POST /admin/users`
- If `tenant_id` is provided, a `tenant_users` row is created
- Role is saved in `tenant_users.role` (defaults to `viewer`)

### Update user
`PUT /admin/users/{user_id}`
- Updates `user_profiles.full_name`
- Upserts `tenant_users` for given `tenant_id`
- Role is set/updated in `tenant_users.role`


## 4) Enforcement model

### RLS as source of truth
- Postgres RLS policies enforce access
- FastAPI acts as a passthrough with JWT
- UI (Next.js/CASL) is **only** a convenience layer

### App admin check
- `require_superadmin` checks:
  1. JWT claim `role == app_admin` **OR**
  2. `user_profiles.is_app_admin` via service role

### Tenant role checks
- Membership is validated in RLS policies using `tenant_users.role`
- `require_tenant_member` ensures the user is active in `tenant_users`


## 5) Role hierarchy (per design doc)

From `actBI_Entity_Sharing_Permissions.md`:

```
SuperAdmin > Admin > Creator > Viewer
```
- **SuperAdmin**: manage tenant settings + members + all entities
- **Admin**: manage tenant members
- **Creator**: create and manage own entities
- **Viewer**: read‑only access via shares


## 6) Notes / gotchas

- App‑admin is **global**, tenant role is **per‑tenant**.
- If a user has no tenant membership, they have no tenant role.
- In the admin UI, role selection only applies when a tenant is assigned.

