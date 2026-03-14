# actBI Entity Sharing Permissions

**Design Document**

| | |
|---|---|
| **Author** | Architecture Team |
| **Date** | January 2026 |
| **Status** | Final |

---

## Table of Contents

1. [Overview](#1-overview)
2. [App Roles](#2-app-roles)
3. [Entity Roles](#3-entity-roles)
4. [Database Schema](#4-database-schema)
5. [RLS Policies](#5-rls-policies)
6. [API Surface](#6-api-surface)
7. [FastAPI Implementation](#7-fastapi-implementation)
8. [CASL Frontend Implementation](#8-casl-frontend-implementation)
9. [End-to-End Flows](#9-end-to-end-flows)
- [Appendix A: Search Implementation](#appendix-a-search-implementation)

---

## 1. Overview

This document defines the permissions architecture for actBI, covering app-level roles, entity-level sharing, and the enforcement strategy across the stack.

### 1.1 Design Goals

The architecture achieves the following goals:

- **No permission checks in FastAPI business logic** — backend is a passthrough
- **All data flows through Python API** — no direct Supabase calls from Next.js
- **RLS enforces all access control** — backend forwards JWT to Supabase
- **CASL provides UI gating only** — not a security boundary
- **Role-to-permissions mapping is configurable at deploy time**

### 1.2 Entity Types

Three entity types support sharing, each with separate tables:

| Entity | Table | Shares Table | Public Sharing |
|--------|-------|--------------|----------------|
| **Conversation** | `conversations` | `conversation_user_shares` | ❌ Not allowed |
| **Dashboard** | `dashboards` | `dashboard_user_shares` | ✅ View only |
| **Report** | `reports` | `report_user_shares` | ❌ Not allowed |

### 1.3 Responsibility Split

| Layer | Responsibility |
|-------|----------------|
| **Next.js + CASL** | UX guidance (what the user can try) |
| **FastAPI** | Identity propagation, passthrough to Supabase |
| **Supabase Auth** | Authentication |
| **Postgres RLS** | Authorization (source of truth) |

---

## 2. App Roles

The system defines five app roles in a strict hierarchy. Higher roles inherit all capabilities of lower roles.

### 2.1 Role Hierarchy

| Role | Hierarchy | Purpose |
|------|-----------|---------|
| **SuperAdmin** | Highest | Tenant settings, governance (manage all entities), supersedes Admin |
| **Admin** | High | Manage tenant users (invite/remove/disable) |
| **Creator** | Medium | Create and manage own conversations, dashboards, reports |
| **Viewer** | Low | View shared content only |
| **Anonymous** | Virtual | Unauthenticated public access via token (dashboards only) |

**Hierarchy rule:** `SuperAdmin > Admin > Creator > Viewer > Anonymous`

SuperAdmin inherits all Admin capabilities. Anonymous is a virtual role — not stored in the database, only used for access resolution when a public token is present.

### 2.2 Role Permissions (Configurable)

Permissions are mapped from roles at deploy time via configuration. This enables easy adjustment without database changes.

```python
# config/role_permissions.py

ROLE_PERMISSIONS = {
    "superadmin": [
        "tenant_settings.read",
        "tenant_settings.manage",
        "tenant_members.read",
        "tenant_members.manage",
        "conversations.create",
        "conversations.manage_all",
        "dashboards.create",
        "dashboards.manage_all",
        "reports.create",
        "reports.manage_all",
    ],
    "admin": [
        "tenant_members.read",
        "tenant_members.manage",
    ],
    "creator": [
        "conversations.create",
        "dashboards.create",
        "reports.create",
    ],
    "viewer": [
        # No create permissions
        # Access only via sharing
    ],
}
```

---

## 3. Entity Roles

Entity roles define what a user can do with a specific entity. These are identical across all entity types.

### 3.1 Role Definitions

| Role | View | Participate | Edit | Delete | Share |
|------|------|-------------|------|--------|-------|
| **Owner** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Editor** | ✓ | ✓ | ✓ | ✗ | ✓ |
| **Participant** | ✓ | ✓ | ✗ | ✗ | ✓ |
| **Viewer** | ✓ | ✗ | ✗ | ✗ | ✗ |

Owner is always the creator initially. Only Viewers cannot share — all other roles can share the entity with others.

### 3.2 Sharing Scopes

Users can gain access through multiple paths. The effective role is the highest across all applicable scopes.

| Scope | Allowed Roles | Applies To |
|-------|---------------|------------|
| **User** | owner, editor, participant, viewer | All entities |
| **Tenant** | editor, participant, viewer | All entities |
| **Public** | viewer only | Dashboards only |

**Effective role priority:** `Owner > Editor > Participant > Viewer > None`

If a user has both a user share (viewer) and tenant share (editor), they receive editor access.

### 3.3 Default Behavior

- New entities are **private by default** (Owner only)
- Owner can share to users or tenant
- Only dashboard owners can enable public sharing (view only)

### 3.4 Governance

| Actor | Can Manage Sharing For |
|-------|------------------------|
| **Owner** | Their own entities |
| **SuperAdmin** | Any entity in the tenant |
| **Admin** | ❌ Cannot manage sharing (user management only) |

---

## 4. Database Schema

The schema uses a hybrid approach: user shares are stored in separate tables (relational), while tenant and public settings are columns on the entity table.

### 4.1 User and Tenant Tables

```sql
-- User profiles
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    is_app_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tenants
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tenant membership
CREATE TABLE tenant_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('superadmin', 'admin', 'creator', 'viewer')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(tenant_id, user_id)
);

CREATE INDEX idx_tenant_users_tenant ON tenant_users(tenant_id);
CREATE INDEX idx_tenant_users_user ON tenant_users(user_id);
```

### 4.2 Dashboard Tables

```sql
-- Dashboards (main entity table)
CREATE TABLE dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES user_profiles(id),
    title TEXT NOT NULL,
    description TEXT,
    
    -- Tenant-wide sharing (NULL = not shared with tenant)
    share_tenant_role TEXT CHECK (share_tenant_role IN ('editor', 'participant', 'viewer')),
    
    -- Public sharing (dashboards only, always viewer role)
    share_public_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    share_public_token TEXT UNIQUE,
    share_public_expires_at TIMESTAMPTZ,
    
    -- Search
    embedding vector(1536),
    search_vector tsvector,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- User-level shares
CREATE TABLE dashboard_user_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('editor', 'participant', 'viewer')),
    created_by UUID NOT NULL REFERENCES user_profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(dashboard_id, user_id)
);

-- Indexes
CREATE INDEX idx_dashboards_tenant ON dashboards(tenant_id);
CREATE INDEX idx_dashboards_owner ON dashboards(owner_user_id);
CREATE INDEX idx_dashboards_tenant_owner ON dashboards(tenant_id, owner_user_id);
CREATE INDEX idx_dashboards_embedding ON dashboards 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_dashboards_search ON dashboards USING gin(search_vector);
CREATE INDEX idx_dashboard_user_shares_dashboard ON dashboard_user_shares(dashboard_id);
CREATE INDEX idx_dashboard_user_shares_user ON dashboard_user_shares(user_id);
```

### 4.3 Conversation and Report Tables

Conversations and reports follow the same pattern as dashboards, without public sharing columns.

```sql
-- Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES user_profiles(id),
    title TEXT NOT NULL,
    share_tenant_role TEXT CHECK (share_tenant_role IN ('editor', 'participant', 'viewer')),
    embedding vector(1536),
    search_vector tsvector,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE conversation_user_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('editor', 'participant', 'viewer')),
    created_by UUID NOT NULL REFERENCES user_profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(conversation_id, user_id)
);

-- Reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES user_profiles(id),
    title TEXT NOT NULL,
    share_tenant_role TEXT CHECK (share_tenant_role IN ('editor', 'participant', 'viewer')),
    embedding vector(1536),
    search_vector tsvector,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE report_user_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('editor', 'participant', 'viewer')),
    created_by UUID NOT NULL REFERENCES user_profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(report_id, user_id)
);
```

---

## 5. RLS Policies

Row Level Security (RLS) is the source of truth for all access control. The backend never checks permissions — it forwards the user JWT to Supabase, and RLS enforces access.

### 5.1 Helper Functions

```sql
-- Role hierarchy helper
CREATE OR REPLACE FUNCTION highest_role(role1 TEXT, role2 TEXT)
RETURNS TEXT AS $$
DECLARE
    priority TEXT[] := ARRAY['owner', 'editor', 'participant', 'viewer'];
    pos1 INT;
    pos2 INT;
BEGIN
    IF role1 IS NULL THEN RETURN role2; END IF;
    IF role2 IS NULL THEN RETURN role1; END IF;
    
    pos1 := array_position(priority, role1);
    pos2 := array_position(priority, role2);
    
    IF pos1 < pos2 THEN RETURN role1; ELSE RETURN role2; END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Check if user is SuperAdmin for a tenant
CREATE OR REPLACE FUNCTION is_superadmin(p_user_id UUID, p_tenant_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM tenant_users
        WHERE tenant_id = p_tenant_id
        AND user_id = p_user_id
        AND role = 'superadmin'
        AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 5.2 Effective Role Function

This function computes a user's effective role for a dashboard, considering ownership, user shares, and tenant shares.

```sql
CREATE OR REPLACE FUNCTION get_effective_dashboard_role(p_user_id UUID, p_dashboard_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_dashboard RECORD;
    v_user_share_role TEXT;
    v_is_tenant_member BOOLEAN;
BEGIN
    -- Get dashboard info
    SELECT owner_user_id, tenant_id, share_tenant_role
    INTO v_dashboard
    FROM dashboards
    WHERE id = p_dashboard_id;
    
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    
    -- 1. Owner check (highest priority)
    IF v_dashboard.owner_user_id = p_user_id THEN
        RETURN 'owner';
    END IF;
    
    -- 2. SuperAdmin check
    IF is_superadmin(p_user_id, v_dashboard.tenant_id) THEN
        RETURN 'owner';  -- SuperAdmin has owner-equivalent access
    END IF;
    
    -- 3. User-level share
    SELECT role INTO v_user_share_role
    FROM dashboard_user_shares
    WHERE dashboard_id = p_dashboard_id AND user_id = p_user_id;
    
    -- 4. Tenant-level share (only if user is active member)
    IF v_dashboard.share_tenant_role IS NOT NULL THEN
        SELECT EXISTS (
            SELECT 1 FROM tenant_users
            WHERE tenant_id = v_dashboard.tenant_id
            AND user_id = p_user_id
            AND status = 'active'
        ) INTO v_is_tenant_member;
        
        IF NOT v_is_tenant_member THEN
            -- User not in tenant, ignore tenant share
            RETURN v_user_share_role;  -- May be NULL
        END IF;
    ELSE
        RETURN v_user_share_role;  -- May be NULL
    END IF;
    
    -- 5. Return highest of user share and tenant share
    RETURN highest_role(v_user_share_role, v_dashboard.share_tenant_role);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 5.3 My Dashboards View

This view returns only dashboards the current user can access, with their effective role included.

```sql
CREATE OR REPLACE VIEW my_dashboards AS
SELECT 
    d.id,
    d.tenant_id,
    d.owner_user_id,
    d.title,
    d.description,
    d.share_tenant_role,
    d.share_public_enabled,
    d.created_at,
    d.updated_at,
    CASE
        WHEN d.owner_user_id = auth.uid() THEN 'owner'
        WHEN is_superadmin(auth.uid(), d.tenant_id) THEN 'owner'
        WHEN dus.role IS NOT NULL AND d.share_tenant_role IS NOT NULL THEN
            highest_role(dus.role, d.share_tenant_role)
        WHEN dus.role IS NOT NULL THEN dus.role
        WHEN d.share_tenant_role IS NOT NULL AND EXISTS (
            SELECT 1 FROM tenant_users
            WHERE tenant_id = d.tenant_id
            AND user_id = auth.uid()
            AND status = 'active'
        ) THEN d.share_tenant_role
        ELSE NULL
    END AS effective_role
FROM dashboards d
LEFT JOIN dashboard_user_shares dus 
    ON dus.dashboard_id = d.id AND dus.user_id = auth.uid()
WHERE 
    d.owner_user_id = auth.uid()
    OR is_superadmin(auth.uid(), d.tenant_id)
    OR dus.user_id IS NOT NULL
    OR (d.share_tenant_role IS NOT NULL AND EXISTS (
        SELECT 1 FROM tenant_users
        WHERE tenant_id = d.tenant_id
        AND user_id = auth.uid()
        AND status = 'active'
    ));
```

### 5.4 RLS Policies for Dashboards

```sql
-- Enable RLS
ALTER TABLE dashboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_user_shares ENABLE ROW LEVEL SECURITY;

-- SELECT: User can see dashboards they have access to
CREATE POLICY dashboards_select ON dashboards
FOR SELECT USING (
    get_effective_dashboard_role(auth.uid(), id) IS NOT NULL
);

-- INSERT: User must have dashboards.create permission (checked via tenant role)
CREATE POLICY dashboards_insert ON dashboards
FOR INSERT WITH CHECK (
    owner_user_id = auth.uid()
    AND EXISTS (
        SELECT 1 FROM tenant_users
        WHERE tenant_id = dashboards.tenant_id
        AND user_id = auth.uid()
        AND role IN ('superadmin', 'creator')
        AND status = 'active'
    )
);

-- UPDATE: User must have editor or owner role
CREATE POLICY dashboards_update ON dashboards
FOR UPDATE USING (
    get_effective_dashboard_role(auth.uid(), id) IN ('owner', 'editor')
);

-- DELETE: User must be owner (or SuperAdmin)
CREATE POLICY dashboards_delete ON dashboards
FOR DELETE USING (
    get_effective_dashboard_role(auth.uid(), id) = 'owner'
);
```

### 5.5 RLS Policies for Shares

```sql
-- SELECT: Can see shares for dashboards user has access to
CREATE POLICY dashboard_user_shares_select ON dashboard_user_shares
FOR SELECT USING (
    get_effective_dashboard_role(auth.uid(), dashboard_id) IS NOT NULL
);

-- INSERT: User must have share permission (owner, editor, or participant)
CREATE POLICY dashboard_user_shares_insert ON dashboard_user_shares
FOR INSERT WITH CHECK (
    get_effective_dashboard_role(auth.uid(), dashboard_id) IN ('owner', 'editor', 'participant')
);

-- DELETE: User must have share permission
CREATE POLICY dashboard_user_shares_delete ON dashboard_user_shares
FOR DELETE USING (
    get_effective_dashboard_role(auth.uid(), dashboard_id) IN ('owner', 'editor', 'participant')
);
```

---

## 6. API Surface

All API endpoints are passthrough — they forward requests to Supabase with the user's JWT and return results or errors directly.

### 6.1 Authentication & Permissions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenants/{tenant_id}/me/permissions` | Get current user's app role and permissions |

**Response:**

```json
{
    "app_role": "creator",
    "app_permissions": [
        "conversations.create",
        "dashboards.create",
        "reports.create"
    ]
}
```

### 6.2 Dashboard CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenants/{tenant_id}/dashboards` | List dashboards user can access |
| POST | `/tenants/{tenant_id}/dashboards` | Create a new dashboard |
| GET | `/tenants/{tenant_id}/dashboards/{id}` | Get dashboard by ID |
| PUT | `/tenants/{tenant_id}/dashboards/{id}` | Update dashboard |
| DELETE | `/tenants/{tenant_id}/dashboards/{id}` | Delete dashboard |

**List Response (includes effective_role):**

```json
[
    {
        "id": "dash_1",
        "title": "Q4 Sales",
        "owner_user_id": "user_123",
        "effective_role": "owner"
    },
    {
        "id": "dash_2",
        "title": "Marketing KPIs",
        "owner_user_id": "user_456",
        "effective_role": "editor"
    }
]
```

### 6.3 Sharing Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenants/{tenant_id}/dashboards/{id}/shares` | List all shares for a dashboard |
| POST | `/tenants/{tenant_id}/dashboards/{id}/shares` | Add a user share |
| PUT | `/tenants/{tenant_id}/dashboards/{id}/shares/{user_id}` | Update user's share role |
| DELETE | `/tenants/{tenant_id}/dashboards/{id}/shares/{user_id}` | Remove user share |
| PUT | `/tenants/{tenant_id}/dashboards/{id}/tenant-share` | Set tenant-wide share |
| DELETE | `/tenants/{tenant_id}/dashboards/{id}/tenant-share` | Remove tenant-wide share |
| POST | `/tenants/{tenant_id}/dashboards/{id}/public-link` | Enable public sharing |
| DELETE | `/tenants/{tenant_id}/dashboards/{id}/public-link` | Disable public sharing |

**Get Shares Response:**

```json
{
    "user_shares": [
        { "user_id": "user_A", "role": "editor", "created_at": "2025-01-15T10:00:00Z" },
        { "user_id": "user_B", "role": "viewer", "created_at": "2025-01-16T14:30:00Z" }
    ],
    "tenant_share": {
        "role": "participant"
    },
    "public_share": {
        "enabled": true,
        "token": "abc123xyz",
        "expires_at": null
    }
}
```

### 6.4 Public Access

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/dashboards/{token}` | Access dashboard via public link (no auth) |

Returns the dashboard in view-only mode. No authentication required.

### 6.5 Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenants/{tenant_id}/dashboards/search?q=...&mode=...` | Search dashboards |

Search modes: `keyword`, `semantic`, `hybrid`. Results include `effective_role`.

---

## 7. FastAPI Implementation

The backend is a pure passthrough — it extracts user context from the JWT, forwards requests to Supabase, and returns results or surfaces errors.

### 7.1 User Context

```python
from dataclasses import dataclass
from fastapi import Depends, Request, HTTPException

@dataclass(frozen=True)
class UserContext:
    user_id: str
    tenant_id: str | None
    auth_token: str  # Supabase JWT (opaque, untouched)

async def get_user_context(request: Request) -> UserContext:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    # Parse JWT for context (non-authoritative, just for logging/routing)
    claims = decode_jwt_without_verification(token)
    
    return UserContext(
        user_id=claims["sub"],
        tenant_id=claims.get("tenant_id"),
        auth_token=token,
    )
```

### 7.2 Supabase Client

```python
from supabase import create_client

def supabase_for_user(user_ctx: UserContext):
    """Create a Supabase client authenticated as the user."""
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(user_ctx.auth_token)
    return client
```

### 7.3 Get My Permissions

This is the one place where backend has logic — mapping role to permissions. But it's config-driven, not business logic.

```python
from config.role_permissions import ROLE_PERMISSIONS

@app.get("/tenants/{tenant_id}/me/permissions")
async def get_my_permissions(
    tenant_id: str,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    result = sb.from_("tenant_users") \
        .select("role") \
        .eq("tenant_id", tenant_id) \
        .eq("user_id", user_ctx.user_id) \
        .eq("status", "active") \
        .single() \
        .execute()
    
    if result.error:
        raise HTTPException(status_code=403, detail="Not a member of this tenant")
    
    role = result.data["role"]
    permissions = ROLE_PERMISSIONS.get(role, [])
    
    return {
        "app_role": role,
        "app_permissions": permissions
    }
```

### 7.4 List Dashboards

```python
@app.get("/tenants/{tenant_id}/dashboards")
async def list_dashboards(
    tenant_id: str,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    # Query the view that includes effective_role
    # RLS automatically filters to accessible dashboards
    result = sb.from_("my_dashboards") \
        .select("*") \
        .eq("tenant_id", tenant_id) \
        .execute()
    
    if result.error:
        raise HTTPException(status_code=500, detail=result.error.message)
    
    return result.data
```

### 7.5 Get Dashboard

```python
@app.get("/tenants/{tenant_id}/dashboards/{dashboard_id}")
async def get_dashboard(
    tenant_id: str,
    dashboard_id: str,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    result = sb.from_("my_dashboards") \
        .select("*") \
        .eq("id", dashboard_id) \
        .eq("tenant_id", tenant_id) \
        .single() \
        .execute()
    
    if result.error:
        raise HTTPException(status_code=404, detail="Dashboard not found or access denied")
    
    return result.data
```

### 7.6 Create Dashboard

```python
from pydantic import BaseModel

class DashboardCreate(BaseModel):
    title: str
    description: str | None = None

@app.post("/tenants/{tenant_id}/dashboards")
async def create_dashboard(
    tenant_id: str,
    payload: DashboardCreate,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    # RLS INSERT policy checks if user has create permission
    result = sb.from_("dashboards") \
        .insert({
            "tenant_id": tenant_id,
            "owner_user_id": user_ctx.user_id,
            "title": payload.title,
            "description": payload.description,
        }) \
        .execute()
    
    if result.error:
        raise HTTPException(status_code=403, detail=result.error.message)
    
    return result.data[0]
```

### 7.7 Update Dashboard

```python
class DashboardUpdate(BaseModel):
    title: str | None = None
    description: str | None = None

@app.put("/tenants/{tenant_id}/dashboards/{dashboard_id}")
async def update_dashboard(
    tenant_id: str,
    dashboard_id: str,
    payload: DashboardUpdate,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    # RLS UPDATE policy checks effective_role IN ('owner', 'editor')
    result = sb.from_("dashboards") \
        .update(payload.dict(exclude_none=True)) \
        .eq("id", dashboard_id) \
        .eq("tenant_id", tenant_id) \
        .execute()
    
    if result.error:
        raise HTTPException(status_code=403, detail=result.error.message)
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Dashboard not found or access denied")
    
    return result.data[0]
```

### 7.8 Delete Dashboard

```python
@app.delete("/tenants/{tenant_id}/dashboards/{dashboard_id}")
async def delete_dashboard(
    tenant_id: str,
    dashboard_id: str,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    # RLS DELETE policy checks effective_role = 'owner'
    result = sb.from_("dashboards") \
        .delete() \
        .eq("id", dashboard_id) \
        .eq("tenant_id", tenant_id) \
        .execute()
    
    if result.error:
        raise HTTPException(status_code=403, detail=result.error.message)
    
    return {"deleted": True}
```

### 7.9 Add User Share

```python
class ShareCreate(BaseModel):
    user_id: str
    role: str  # 'editor', 'participant', 'viewer'

@app.post("/tenants/{tenant_id}/dashboards/{dashboard_id}/shares")
async def create_dashboard_share(
    tenant_id: str,
    dashboard_id: str,
    payload: ShareCreate,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    # RLS INSERT policy checks effective_role IN ('owner', 'editor', 'participant')
    result = sb.from_("dashboard_user_shares") \
        .insert({
            "dashboard_id": dashboard_id,
            "user_id": payload.user_id,
            "role": payload.role,
            "created_by": user_ctx.user_id,
        }) \
        .execute()
    
    if result.error:
        raise HTTPException(status_code=403, detail=result.error.message)
    
    return result.data[0]
```

### 7.10 Set Tenant Share

```python
class TenantShareUpdate(BaseModel):
    role: str  # 'editor', 'participant', 'viewer'

@app.put("/tenants/{tenant_id}/dashboards/{dashboard_id}/tenant-share")
async def set_tenant_share(
    tenant_id: str,
    dashboard_id: str,
    payload: TenantShareUpdate,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    # RLS UPDATE policy applies
    result = sb.from_("dashboards") \
        .update({"share_tenant_role": payload.role}) \
        .eq("id", dashboard_id) \
        .eq("tenant_id", tenant_id) \
        .execute()
    
    if result.error:
        raise HTTPException(status_code=403, detail=result.error.message)
    
    return result.data[0]
```

---

## 8. CASL Frontend Implementation

CASL provides UI gating — showing/hiding buttons and routes based on permissions. It is not a security boundary; RLS enforces access.

### 8.1 Ability Definitions

```typescript
// lib/casl/abilities.ts
import { AbilityBuilder, createMongoAbility, MongoAbility } from '@casl/ability';

// Action types
type AppAction = 'create' | 'read' | 'manage';
type EntityAction = 'view' | 'participate' | 'edit' | 'delete' | 'share';

// Subject types
type AppSubject = 'Conversation' | 'Dashboard' | 'Report' | 'TenantMembers' | 'TenantSettings';
type EntitySubject = 'Conversation' | 'Dashboard' | 'Report';

export type AppAbility = MongoAbility<[AppAction, AppSubject]>;
export type EntityAbility = MongoAbility<[EntityAction, EntitySubject]>;
```

### 8.2 App-Level Ability Builder

Built once on login/tenant switch from `/me/permissions` response.

```typescript
// lib/casl/defineAppAbility.ts
import { AbilityBuilder, createMongoAbility } from '@casl/ability';
import type { AppAbility } from './abilities';

interface PermissionsResponse {
  app_role: string;
  app_permissions: string[];
}

export function defineAppAbility(permissions: PermissionsResponse): AppAbility {
  const { can, build } = new AbilityBuilder<AppAbility>(createMongoAbility);
  
  const perms = new Set(permissions.app_permissions);
  
  // Conversations
  if (perms.has('conversations.create')) {
    can('create', 'Conversation');
  }
  if (perms.has('conversations.manage_all')) {
    can('manage', 'Conversation');
  }
  
  // Dashboards
  if (perms.has('dashboards.create')) {
    can('create', 'Dashboard');
  }
  if (perms.has('dashboards.manage_all')) {
    can('manage', 'Dashboard');
  }
  
  // Reports
  if (perms.has('reports.create')) {
    can('create', 'Report');
  }
  if (perms.has('reports.manage_all')) {
    can('manage', 'Report');
  }
  
  // Tenant management
  if (perms.has('tenant_members.read')) {
    can('read', 'TenantMembers');
  }
  if (perms.has('tenant_members.manage')) {
    can('manage', 'TenantMembers');
  }
  if (perms.has('tenant_settings.read')) {
    can('read', 'TenantSettings');
  }
  if (perms.has('tenant_settings.manage')) {
    can('manage', 'TenantSettings');
  }
  
  return build();
}
```

### 8.3 Entity-Level Ability Builder

Built from `effective_role` returned with each entity.

```typescript
// lib/casl/defineEntityAbility.ts
import { AbilityBuilder, createMongoAbility } from '@casl/ability';
import type { EntityAbility } from './abilities';

type EffectiveRole = 'owner' | 'editor' | 'participant' | 'viewer' | null;

export function defineEntityAbility(
  effectiveRole: EffectiveRole,
  subject: 'Conversation' | 'Dashboard' | 'Report' = 'Dashboard'
): EntityAbility {
  const { can, build } = new AbilityBuilder<EntityAbility>(createMongoAbility);
  
  if (!effectiveRole) {
    return build();  // No access
  }
  
  // All roles can view
  can('view', subject);
  
  // Participant and above can participate and share
  if (['owner', 'editor', 'participant'].includes(effectiveRole)) {
    can('participate', subject);
    can('share', subject);
  }
  
  // Editor and above can edit
  if (['owner', 'editor'].includes(effectiveRole)) {
    can('edit', subject);
  }
  
  // Only owner can delete
  if (effectiveRole === 'owner') {
    can('delete', subject);
  }
  
  return build();
}
```

### 8.4 React Context Provider

```typescript
// contexts/AbilityContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { defineAppAbility } from '@/lib/casl/defineAppAbility';
import type { AppAbility } from '@/lib/casl/abilities';
import { api } from '@/lib/api';

interface AbilityContextType {
  appAbility: AppAbility | null;
  loading: boolean;
}

const AbilityContext = createContext<AbilityContextType>({
  appAbility: null,
  loading: true,
});

export function AbilityProvider({ 
  tenantId, 
  children 
}: { 
  tenantId: string; 
  children: React.ReactNode;
}) {
  const [appAbility, setAppAbility] = useState<AppAbility | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function loadPermissions() {
      setLoading(true);
      try {
        const permissions = await api.getMyPermissions(tenantId);
        const ability = defineAppAbility(permissions);
        setAppAbility(ability);
      } catch (error) {
        console.error('Failed to load permissions:', error);
        setAppAbility(null);
      } finally {
        setLoading(false);
      }
    }
    
    loadPermissions();
  }, [tenantId]);
  
  return (
    <AbilityContext.Provider value={{ appAbility, loading }}>
      {children}
    </AbilityContext.Provider>
  );
}

export function useAppAbility() {
  return useContext(AbilityContext);
}
```

### 8.5 Usage in Components

```typescript
// components/DashboardList.tsx
import { useAppAbility } from '@/contexts/AbilityContext';
import { defineEntityAbility } from '@/lib/casl/defineEntityAbility';

export function DashboardList({ dashboards }) {
  const { appAbility, loading } = useAppAbility();
  
  if (loading) return <Spinner />;
  
  return (
    <div>
      {/* Create button - based on app-level ability */}
      {appAbility?.can('create', 'Dashboard') && (
        <Button onClick={handleCreate}>Create Dashboard</Button>
      )}
      
      {dashboards.map(dashboard => {
        // Entity-level ability from effective_role
        const entityAbility = defineEntityAbility(dashboard.effective_role, 'Dashboard');
        
        return (
          <DashboardCard 
            key={dashboard.id}
            dashboard={dashboard}
            canEdit={entityAbility.can('edit', 'Dashboard')}
            canDelete={entityAbility.can('delete', 'Dashboard')}
            canShare={entityAbility.can('share', 'Dashboard')}
          />
        );
      })}
    </div>
  );
}
```

```typescript
// components/DashboardDetail.tsx
import { defineEntityAbility } from '@/lib/casl/defineEntityAbility';

export function DashboardDetail({ dashboard }) {
  const entityAbility = defineEntityAbility(dashboard.effective_role, 'Dashboard');
  
  async function handleDelete() {
    try {
      await api.deleteDashboard(dashboard.tenant_id, dashboard.id);
      router.push('/dashboards');
    } catch (error) {
      if (error.status === 403) {
        toast.error("You don't have permission to delete this dashboard");
      }
    }
  }
  
  return (
    <div>
      <h1>{dashboard.title}</h1>
      
      <div className="actions">
        {entityAbility.can('edit', 'Dashboard') && (
          <Button onClick={handleEdit}>Edit</Button>
        )}
        
        {entityAbility.can('share', 'Dashboard') && (
          <Button onClick={openShareModal}>Share</Button>
        )}
        
        {entityAbility.can('delete', 'Dashboard') && (
          <Button variant="danger" onClick={handleDelete}>Delete</Button>
        )}
      </div>
    </div>
  );
}
```

---

## 9. End-to-End Flows

This section shows complete flows from user action to database, demonstrating how permissions are enforced without backend logic.

### 9.1 User Logs In and Views Dashboards

1. User authenticates with Supabase Auth, receives JWT
2. Frontend calls `GET /tenants/{id}/me/permissions`
3. Backend queries `tenant_users`, returns role + permissions
4. Frontend builds `appAbility` with CASL
5. Frontend calls `GET /tenants/{id}/dashboards`
6. Backend queries `my_dashboards` view (RLS filters to accessible)
7. Each dashboard includes `effective_role`
8. Frontend renders list with appropriate buttons per dashboard

### 9.2 User Edits a Dashboard

1. User clicks Edit button (visible because `effective_role = editor`)
2. Frontend calls `PUT /tenants/{id}/dashboards/{id}`
3. Backend forwards to Supabase with user JWT
4. RLS UPDATE policy checks: `get_effective_dashboard_role() IN ('owner', 'editor')`
5. If allowed: update succeeds, backend returns updated data
6. If denied: Supabase returns error, backend returns 403

### 9.3 User Tries to Delete (Access Denied)

1. User with `effective_role = editor` tries to delete
2. Delete button is hidden (CASL check fails)
3. If they bypass UI and call DELETE endpoint directly...
4. Backend forwards to Supabase
5. RLS DELETE policy checks: `get_effective_dashboard_role() = 'owner'`
6. Policy fails (user is editor, not owner)
7. Backend returns 403 to frontend

### 9.4 User Shares a Dashboard

1. User with `effective_role = participant` opens share modal
2. Frontend calls `POST /tenants/{id}/dashboards/{id}/shares`
3. Backend inserts into `dashboard_user_shares` via Supabase
4. RLS INSERT policy checks: `get_effective_dashboard_role() IN ('owner', 'editor', 'participant')`
5. Policy passes (user is participant)
6. Share is created, new user can access the dashboard

---

## Appendix A: Search Implementation

Search uses pgvector in Supabase, enabling semantic and keyword search with RLS enforcement in a single query.

### A.1 Search Function

```sql
CREATE OR REPLACE FUNCTION search_my_dashboards(
  p_tenant_id UUID,
  p_query TEXT,
  p_query_embedding vector(1536) DEFAULT NULL,
  p_mode TEXT DEFAULT 'keyword',  -- 'keyword', 'semantic', 'hybrid'
  p_limit INT DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  title TEXT,
  description TEXT,
  effective_role TEXT,
  score REAL
) AS $$
BEGIN
  IF p_mode = 'keyword' THEN
    RETURN QUERY
    SELECT 
      d.id,
      d.title,
      d.description,
      d.effective_role,
      ts_rank(db.search_vector, plainto_tsquery('english', p_query))::REAL AS score
    FROM my_dashboards d
    JOIN dashboards db ON db.id = d.id
    WHERE 
      d.tenant_id = p_tenant_id
      AND db.search_vector @@ plainto_tsquery('english', p_query)
    ORDER BY score DESC
    LIMIT p_limit;

  ELSIF p_mode = 'semantic' THEN
    RETURN QUERY
    SELECT 
      d.id,
      d.title,
      d.description,
      d.effective_role,
      (1 - (db.embedding <=> p_query_embedding))::REAL AS score
    FROM my_dashboards d
    JOIN dashboards db ON db.id = d.id
    WHERE 
      d.tenant_id = p_tenant_id
      AND db.embedding IS NOT NULL
    ORDER BY db.embedding <=> p_query_embedding
    LIMIT p_limit;

  ELSIF p_mode = 'hybrid' THEN
    RETURN QUERY
    SELECT 
      d.id,
      d.title,
      d.description,
      d.effective_role,
      (
        COALESCE(ts_rank(db.search_vector, plainto_tsquery('english', p_query)), 0) * 0.3 +
        COALESCE(1 - (db.embedding <=> p_query_embedding), 0) * 0.7
      )::REAL AS score
    FROM my_dashboards d
    JOIN dashboards db ON db.id = d.id
    WHERE 
      d.tenant_id = p_tenant_id
      AND (
        db.search_vector @@ plainto_tsquery('english', p_query)
        OR db.embedding IS NOT NULL
      )
    ORDER BY score DESC
    LIMIT p_limit;

  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### A.2 Search API Endpoint

```python
@app.get("/tenants/{tenant_id}/dashboards/search")
async def search_dashboards(
    tenant_id: str,
    q: str,
    mode: str = "keyword",  # keyword, semantic, hybrid
    limit: int = 20,
    user_ctx: UserContext = Depends(get_user_context)
):
    sb = supabase_for_user(user_ctx)
    
    params = {
        "p_tenant_id": tenant_id,
        "p_query": q,
        "p_mode": mode,
        "p_limit": limit,
    }
    
    # Generate embedding for semantic/hybrid modes
    if mode in ("semantic", "hybrid"):
        embedding = await embedding_service.embed(q)
        params["p_query_embedding"] = embedding
    
    result = sb.rpc("search_my_dashboards", params).execute()
    
    if result.error:
        raise HTTPException(status_code=500, detail=result.error.message)
    
    return result.data
```

### A.3 Search Response

```json
[
  {
    "id": "dash_1",
    "title": "Q4 Revenue Analysis",
    "description": "Quarterly revenue breakdown by region",
    "effective_role": "editor",
    "score": 0.92
  },
  {
    "id": "dash_2",
    "title": "Annual Financial Review",
    "description": "Year-end financial summary",
    "effective_role": "viewer",
    "score": 0.87
  }
]
```

### A.4 Key Benefits

- **Single query** — search and permissions in one database call
- **RLS enforced** — `my_dashboards` view filters to accessible entities
- **No post-filtering** — results are already permission-checked
- **Transactionally consistent** — search and access in same transaction
- **Effective role included** — CASL can gate UI for each result

---

*End of Document*
