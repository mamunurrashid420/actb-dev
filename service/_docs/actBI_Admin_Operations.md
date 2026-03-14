# ActBI Admin Operations

**Design Document**

| | |
|---|---|
| **Author** | Architecture Team |
| **Date** | January 2026 |
| **Status** | Final |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Use Cases](#2-use-cases)
3. [Design Choices & Rationale](#3-design-choices--rationale)
4. [Architecture](#4-architecture)
5. [Database Schema](#5-database-schema)
6. [Postgres Functions](#6-postgres-functions)
7. [Next.js Implementation](#7-nextjs-implementation)
8. [Security Model](#8-security-model)
9. [SOC II Compliance](#9-soc-ii-compliance)
10. [Operational Procedures](#10-operational-procedures)

---

## 1. Overview

This document defines the architecture for ActBI internal administration — how ActBI personnel (not customers) perform cross-tenant operations like onboarding, support, and configuration.

### 1.1 The Problem

ActBI personnel need to:

- Onboard new tenants
- Add the first SuperAdmin user to a tenant
- Configure connectors
- Provide customer support
- View tenant health and usage

But we must:

- Minimize blast radius if credentials are compromised
- Maintain complete audit trail for SOC II
- Avoid "god mode" access patterns
- Keep customer-facing RLS policies clean and unchanged

### 1.2 The Solution

A dedicated admin application at `admin.pinax.ai` that:

- Is only accessible via VPN (not publicly resolvable)
- Requires Google SSO with enforced 2FA
- Uses scoped Postgres functions instead of raw table access
- Logs every action to an audit table
- Keeps admin logic completely separate from customer app

---

## 2. Use Cases

### 2.1 Tenant Onboarding

**Scenario:** A new customer signs a contract. ActBI needs to create their tenant and add their first admin user.

**Flow:**

1. ActBI admin logs into `admin.pinax.ai` via Google SSO
2. Navigates to "Create Tenant"
3. Enters tenant name (e.g., "Acme Corp")
4. System creates tenant, logs the action
5. ActBI admin adds the customer's IT admin as SuperAdmin
6. Customer receives invite, logs in, and takes over tenant management

**Why ActBI does this (not self-service):**

- Contract verification required before provisioning
- Billing setup may be needed
- Custom onboarding steps per customer tier

---

### 2.2 Adding First SuperAdmin

**Scenario:** Tenant exists but has no users yet, or customer needs a new SuperAdmin added.

**Flow:**

1. ActBI admin searches for tenant
2. Views tenant details (users, usage stats)
3. Adds new SuperAdmin by email
4. User is created (or linked if they exist) and granted SuperAdmin role
5. Action logged with who did it, when, from where

---

### 2.3 Customer Support

**Scenario:** Customer reports an issue. Support needs to see their tenant's state.

**Flow:**

1. Support engineer logs into `admin.pinax.ai`
2. Searches for customer's tenant
3. Views read-only details: users, dashboard count, recent activity
4. All views are logged for audit

**What support CANNOT do:**

- View actual dashboard/report content (privacy)
- Modify customer data
- Delete anything

---

### 2.4 Connector Configuration

**Scenario:** Customer needs a data connector set up that requires ActBI-side configuration.

**Flow:**

1. ActBI admin navigates to tenant's connector settings
2. Adds connector configuration (credentials stored encrypted)
3. Tests connection
4. Action logged

---

### 2.5 Emergency Access Revocation

**Scenario:** An ActBI admin leaves the company or their account is compromised.

**Flow:**

1. Designated admin (you) sets `is_active = FALSE` on their record
2. Immediately, all their admin access is revoked
3. No customer data was exposed because they never had direct table access

---

## 3. Design Choices & Rationale

### 3.1 Why Not Add ActBI Admins to RLS Policies?

**Option considered:**

```sql
-- Adding to every policy
CREATE POLICY dashboards_select ON dashboards
FOR SELECT USING (
    get_effective_dashboard_role(auth.uid(), id) IS NOT NULL
    OR is_actbi_admin(auth.uid())  -- Pollution
);
```

**Why we rejected it:**

| Concern | Problem |
|---------|---------|
| **Policy pollution** | Every RLS policy needs modification |
| **Blast radius** | If admin account compromised, attacker has SELECT on all tables |
| **Audit difficulty** | Hard to distinguish admin access from normal access |
| **Maintenance burden** | New tables need to remember the admin clause |
| **Separation of concerns** | Customer security model shouldn't know about ActBI internals |

---

### 3.2 Why SECURITY DEFINER Functions?

**How it works:**

```sql
CREATE FUNCTION admin_create_tenant(...)
RETURNS UUID AS $$
  -- Runs as postgres (function owner), not calling user
  -- RLS does not apply
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Why this is the right choice:**

| Benefit | Explanation |
|---------|-------------|
| **Scoped access** | Function can only do what it's written to do |
| **No RLS bypass leakage** | Service key stays server-side, never exposed |
| **Self-documenting** | Function name describes the operation |
| **Audit built-in** | Function writes to audit log atomically |
| **Testable** | Each function can be unit tested |
| **Principle of least privilege** | Admin can create tenant but can't read customer dashboards |

---

### 3.3 Why a Separate Admin App?

**Options considered:**

| Option | Pros | Cons |
|--------|------|------|
| Admin routes in main app | Single deployment | Attack surface, complexity |
| Separate app, public | Simple | Exposed to internet |
| **Separate app, VPN only** | Isolated, secure | Requires VPN |

**Why VPN-only separate app wins:**

- **Network isolation**: Not reachable from internet at all
- **DNS isolation**: `admin.pinax.ai` not publicly resolvable
- **Credential isolation**: Service role key only in admin app
- **Mental model**: Clear separation for developers
- **Compliance**: Easy to explain to auditors

---

### 3.4 Why Google SSO + 2FA?

**Requirements:**

- Strong authentication
- Centralized user management
- Audit trail of logins
- Easy revocation

**Google Workspace provides:**

- SSO via OAuth/OIDC
- Enforced 2FA at organization level
- Login audit logs
- Instant revocation by disabling Workspace account
- No password management burden

---

### 3.5 Why Not Use Supabase Service Role Directly?

**The service role key:**

```
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

This key bypasses ALL RLS. If used directly for queries:

```typescript
// DANGEROUS - gives full access
const { data } = await supabase.from('dashboards').select('*');
```

**Our approach — only use it for RPC calls:**

```typescript
// SAFE - scoped to what function allows
const { data } = await supabase.rpc('admin_create_tenant', { ... });
```

The function controls what happens, not the caller.

---

## 4. Architecture

### 4.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CORPORATE VPN                            │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  ActBI Admin (you)                      │   │
│   │                  nikos@actbi.ai                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              │ Google SSO + 2FA                 │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              admin.pinax.ai                              │   │
│   │              (internal DNS only)                         │   │
│   │                                                          │   │
│   │   ┌──────────────────────────────────────────────────┐  │   │
│   │   │           Next.js Admin App                      │  │   │
│   │   │                                                  │  │   │
│   │   │  Client Side          │  Server Side            │  │   │
│   │   │  ─────────────        │  ───────────            │  │   │
│   │   │  • React UI           │  • Server Actions       │  │   │
│   │   │  • No secrets         │  • Service Role Key     │  │   │
│   │   │                       │  • Admin verification   │  │   │
│   │   └──────────────────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
└──────────────────────────────│──────────────────────────────────┘
                               │
                               │ RPC calls only (not raw SQL)
                               │ Using service_role key
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Supabase                               │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    Postgres                             │   │
│   │                                                         │   │
│   │   SECURITY DEFINER Functions     │   Regular Tables     │   │
│   │   ───────────────────────────    │   ──────────────     │   │
│   │   • admin_create_tenant()        │   • tenants          │   │
│   │   • admin_add_tenant_superadmin()│   • tenant_users     │   │
│   │   • admin_list_tenants()         │   • dashboards       │   │
│   │   • admin_get_tenant_details()   │   • etc.             │   │
│   │                                  │                      │   │
│   │   Each function:                 │   RLS policies       │   │
│   │   • Validates admin email        │   unchanged for      │   │
│   │   • Does ONE specific thing      │   customer app       │   │
│   │   • Writes to audit log          │                      │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  admin_audit_log                        │   │
│   │                                                         │   │
│   │   Every admin action recorded:                          │   │
│   │   • Who (admin_email)                                   │   │
│   │   • What (action)                                       │   │
│   │   • When (created_at)                                   │   │
│   │   • Where (ip_address)                                  │   │
│   │   • Target (tenant_id, user_id)                         │   │
│   │   • Details (JSONB)                                     │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Request Flow

```
1. Admin connects to VPN
2. Admin navigates to admin.pinax.ai (resolves only on internal DNS)
3. Admin clicks "Sign in with Google"
4. Google authenticates with 2FA
5. Supabase Auth creates session
6. Admin clicks "Create Tenant"
7. React form submits to Server Action
8. Server Action:
   a. Verifies session exists
   b. Checks email is in actbi_admins table
   c. Calls supabase.rpc('admin_create_tenant', {...})
9. Postgres function:
   a. Re-validates admin email (defense in depth)
   b. Creates tenant
   c. Writes audit log
   d. Returns tenant ID
10. UI updates with new tenant
```

---

## 5. Database Schema

### 5.1 ActBI Admins Table

```sql
-- Table of ActBI personnel who can access the admin app
CREATE TABLE actbi_admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    granted_by TEXT NOT NULL,           -- Who added this admin
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,             -- Optional: time-limited access
    last_login_at TIMESTAMPTZ,
    notes TEXT                          -- e.g., "Support team lead"
);

-- Initial seed (run once)
INSERT INTO actbi_admins (email, display_name, granted_by, notes)
VALUES ('nikos@actbi.ai', 'Nikos Michalakis', 'system_init', 'Founder - permanent access');
```

### 5.2 Admin Audit Log

```sql
-- Immutable log of all admin actions
CREATE TABLE admin_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Who
    admin_email TEXT NOT NULL,
    
    -- What
    action TEXT NOT NULL,               -- e.g., 'create_tenant', 'add_superadmin'
    
    -- Target
    target_tenant_id UUID,
    target_user_id UUID,
    
    -- Details
    details JSONB NOT NULL DEFAULT '{}',
    
    -- Context
    ip_address TEXT,
    user_agent TEXT,
    
    -- When
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for querying audit log
CREATE INDEX idx_admin_audit_log_admin ON admin_audit_log(admin_email);
CREATE INDEX idx_admin_audit_log_tenant ON admin_audit_log(target_tenant_id);
CREATE INDEX idx_admin_audit_log_action ON admin_audit_log(action);
CREATE INDEX idx_admin_audit_log_created ON admin_audit_log(created_at DESC);

-- Prevent modifications (audit log should be append-only)
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log cannot be modified';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_immutable
BEFORE UPDATE OR DELETE ON admin_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
```

### 5.3 Why These Tables Are Not RLS-Protected

These tables use traditional access control:

- `actbi_admins`: Only readable by service role (admin app backend)
- `admin_audit_log`: Only writable by SECURITY DEFINER functions

Customer-facing app never touches these tables.

---

## 6. Postgres Functions

### 6.1 Helper: Validate Admin

```sql
-- Reusable admin validation (called by all admin functions)
CREATE OR REPLACE FUNCTION validate_actbi_admin(p_admin_email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM actbi_admins 
        WHERE email = p_admin_email 
        AND is_active = TRUE
        AND (expires_at IS NULL OR expires_at > now())
    ) THEN
        RAISE EXCEPTION 'Unauthorized: % is not an active ActBI admin', p_admin_email;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 6.2 Create Tenant

```sql
CREATE OR REPLACE FUNCTION admin_create_tenant(
    p_admin_email TEXT,
    p_tenant_name TEXT,
    p_ip_address TEXT DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_tenant_id UUID;
BEGIN
    -- Validate admin
    PERFORM validate_actbi_admin(p_admin_email);
    
    -- Validate input
    IF p_tenant_name IS NULL OR trim(p_tenant_name) = '' THEN
        RAISE EXCEPTION 'Tenant name is required';
    END IF;
    
    -- Create tenant
    INSERT INTO tenants (name)
    VALUES (trim(p_tenant_name))
    RETURNING id INTO v_tenant_id;
    
    -- Audit log
    INSERT INTO admin_audit_log (
        admin_email, 
        action, 
        target_tenant_id, 
        details, 
        ip_address,
        user_agent
    )
    VALUES (
        p_admin_email, 
        'create_tenant', 
        v_tenant_id, 
        jsonb_build_object('tenant_name', p_tenant_name),
        p_ip_address,
        p_user_agent
    );
    
    RETURN v_tenant_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 6.3 Add Tenant SuperAdmin

```sql
CREATE OR REPLACE FUNCTION admin_add_tenant_superadmin(
    p_admin_email TEXT,
    p_tenant_id UUID,
    p_user_email TEXT,
    p_user_display_name TEXT,
    p_ip_address TEXT DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Validate admin
    PERFORM validate_actbi_admin(p_admin_email);
    
    -- Validate tenant exists
    IF NOT EXISTS (SELECT 1 FROM tenants WHERE id = p_tenant_id) THEN
        RAISE EXCEPTION 'Tenant not found: %', p_tenant_id;
    END IF;
    
    -- Validate input
    IF p_user_email IS NULL OR trim(p_user_email) = '' THEN
        RAISE EXCEPTION 'User email is required';
    END IF;
    
    -- Create or get user
    INSERT INTO user_profiles (email, display_name)
    VALUES (lower(trim(p_user_email)), trim(p_user_display_name))
    ON CONFLICT (email) DO UPDATE SET 
        display_name = COALESCE(EXCLUDED.display_name, user_profiles.display_name)
    RETURNING id INTO v_user_id;
    
    -- Add as SuperAdmin (upsert to handle existing membership)
    INSERT INTO tenant_users (tenant_id, user_id, role, status)
    VALUES (p_tenant_id, v_user_id, 'superadmin', 'active')
    ON CONFLICT (tenant_id, user_id) DO UPDATE SET 
        role = 'superadmin', 
        status = 'active';
    
    -- Audit log
    INSERT INTO admin_audit_log (
        admin_email, 
        action, 
        target_tenant_id, 
        target_user_id, 
        details,
        ip_address,
        user_agent
    )
    VALUES (
        p_admin_email, 
        'add_tenant_superadmin', 
        p_tenant_id, 
        v_user_id, 
        jsonb_build_object(
            'user_email', p_user_email,
            'user_display_name', p_user_display_name
        ),
        p_ip_address,
        p_user_agent
    );
    
    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 6.4 List Tenants

```sql
CREATE OR REPLACE FUNCTION admin_list_tenants(p_admin_email TEXT)
RETURNS TABLE (
    id UUID,
    name TEXT,
    created_at TIMESTAMPTZ,
    user_count BIGINT,
    dashboard_count BIGINT,
    conversation_count BIGINT,
    report_count BIGINT
) AS $$
BEGIN
    -- Validate admin
    PERFORM validate_actbi_admin(p_admin_email);
    
    RETURN QUERY
    SELECT 
        t.id,
        t.name,
        t.created_at,
        (SELECT COUNT(*) FROM tenant_users tu WHERE tu.tenant_id = t.id AND tu.status = 'active'),
        (SELECT COUNT(*) FROM dashboards d WHERE d.tenant_id = t.id),
        (SELECT COUNT(*) FROM conversations c WHERE c.tenant_id = t.id),
        (SELECT COUNT(*) FROM reports r WHERE r.tenant_id = t.id)
    FROM tenants t
    ORDER BY t.created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 6.5 Get Tenant Details

```sql
CREATE OR REPLACE FUNCTION admin_get_tenant_details(
    p_admin_email TEXT,
    p_tenant_id UUID
)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
BEGIN
    -- Validate admin
    PERFORM validate_actbi_admin(p_admin_email);
    
    -- Validate tenant exists
    IF NOT EXISTS (SELECT 1 FROM tenants WHERE id = p_tenant_id) THEN
        RAISE EXCEPTION 'Tenant not found: %', p_tenant_id;
    END IF;
    
    -- Build result
    SELECT jsonb_build_object(
        'tenant', (
            SELECT jsonb_build_object(
                'id', t.id,
                'name', t.name,
                'created_at', t.created_at
            )
            FROM tenants t 
            WHERE t.id = p_tenant_id
        ),
        'users', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'user_id', tu.user_id,
                    'email', up.email,
                    'display_name', up.display_name,
                    'role', tu.role,
                    'status', tu.status,
                    'created_at', tu.created_at
                ) ORDER BY tu.created_at
            ), '[]'::jsonb)
            FROM tenant_users tu
            JOIN user_profiles up ON up.id = tu.user_id
            WHERE tu.tenant_id = p_tenant_id
        ),
        'stats', jsonb_build_object(
            'dashboard_count', (SELECT COUNT(*) FROM dashboards WHERE tenant_id = p_tenant_id),
            'conversation_count', (SELECT COUNT(*) FROM conversations WHERE tenant_id = p_tenant_id),
            'report_count', (SELECT COUNT(*) FROM reports WHERE tenant_id = p_tenant_id)
        )
    ) INTO v_result;
    
    -- Audit log (read actions logged too)
    INSERT INTO admin_audit_log (admin_email, action, target_tenant_id, details)
    VALUES (p_admin_email, 'view_tenant_details', p_tenant_id, '{}'::jsonb);
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 6.6 Deactivate Tenant User

```sql
CREATE OR REPLACE FUNCTION admin_deactivate_tenant_user(
    p_admin_email TEXT,
    p_tenant_id UUID,
    p_user_id UUID,
    p_reason TEXT DEFAULT NULL,
    p_ip_address TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Validate admin
    PERFORM validate_actbi_admin(p_admin_email);
    
    -- Validate tenant and user exist
    IF NOT EXISTS (
        SELECT 1 FROM tenant_users 
        WHERE tenant_id = p_tenant_id AND user_id = p_user_id
    ) THEN
        RAISE EXCEPTION 'User not found in tenant';
    END IF;
    
    -- Deactivate
    UPDATE tenant_users
    SET status = 'inactive'
    WHERE tenant_id = p_tenant_id AND user_id = p_user_id;
    
    -- Audit log
    INSERT INTO admin_audit_log (
        admin_email, 
        action, 
        target_tenant_id, 
        target_user_id, 
        details,
        ip_address
    )
    VALUES (
        p_admin_email, 
        'deactivate_tenant_user', 
        p_tenant_id, 
        p_user_id, 
        jsonb_build_object('reason', p_reason),
        p_ip_address
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 6.7 View Audit Log

```sql
CREATE OR REPLACE FUNCTION admin_view_audit_log(
    p_admin_email TEXT,
    p_tenant_id UUID DEFAULT NULL,
    p_limit INT DEFAULT 100,
    p_offset INT DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    admin_email TEXT,
    action TEXT,
    target_tenant_id UUID,
    target_user_id UUID,
    details JSONB,
    ip_address TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    -- Validate admin
    PERFORM validate_actbi_admin(p_admin_email);
    
    RETURN QUERY
    SELECT 
        al.id,
        al.admin_email,
        al.action,
        al.target_tenant_id,
        al.target_user_id,
        al.details,
        al.ip_address,
        al.created_at
    FROM admin_audit_log al
    WHERE (p_tenant_id IS NULL OR al.target_tenant_id = p_tenant_id)
    ORDER BY al.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 7. Next.js Implementation

### 7.1 Project Structure

```
admin-app/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # Redirect to /admin/tenants
│   ├── login/
│   │   └── page.tsx                # Google SSO login
│   ├── admin/
│   │   ├── layout.tsx              # Auth check wrapper
│   │   ├── tenants/
│   │   │   ├── page.tsx            # List tenants
│   │   │   └── [tenantId]/
│   │   │       └── page.tsx        # Tenant details
│   │   └── audit/
│   │       └── page.tsx            # Audit log viewer
│   └── actions/
│       └── admin.ts                # Server Actions
├── lib/
│   ├── supabase/
│   │   ├── client.ts               # Browser client (auth only)
│   │   ├── server.ts               # Server client (auth only)
│   │   └── admin.ts                # Admin client (service role)
│   └── auth/
│       └── verifyAdmin.ts          # Admin verification
├── components/
│   └── ...
└── middleware.ts                   # Auth redirect
```

### 7.2 Environment Variables

```env
# .env.local

# Public (safe to expose to browser)
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Private (server-side only, never prefix with NEXT_PUBLIC_)
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### 7.3 Supabase Clients

```typescript
// lib/supabase/client.ts
// Browser client - for auth only
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

```typescript
// lib/supabase/server.ts
// Server client - for auth only
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createServerSupabaseClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Called from Server Component
          }
        },
      },
    }
  );
}
```

```typescript
// lib/supabase/admin.ts
// Admin client - uses service role, server-side only!
import { createClient } from '@supabase/supabase-js';

export function createAdminSupabaseClient() {
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  
  if (!serviceRoleKey) {
    throw new Error(
      'SUPABASE_SERVICE_ROLE_KEY is not set. ' +
      'This should only be called server-side.'
    );
  }
  
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    serviceRoleKey,
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    }
  );
}
```

### 7.4 Admin Verification

```typescript
// lib/auth/verifyAdmin.ts
import { createServerSupabaseClient } from '@/lib/supabase/server';
import { createAdminSupabaseClient } from '@/lib/supabase/admin';

export interface ActBIAdmin {
  email: string;
  displayName: string | null;
}

export async function verifyActBIAdmin(): Promise<ActBIAdmin | null> {
  // Get current user session
  const supabase = await createServerSupabaseClient();
  const { data: { user }, error } = await supabase.auth.getUser();
  
  if (error || !user?.email) {
    return null;
  }
  
  // Verify user is in actbi_admins table
  const adminClient = createAdminSupabaseClient();
  const { data: adminRecord, error: adminError } = await adminClient
    .from('actbi_admins')
    .select('email, display_name')
    .eq('email', user.email)
    .eq('is_active', true)
    .or('expires_at.is.null,expires_at.gt.now()')
    .single();
  
  if (adminError || !adminRecord) {
    console.warn(`Unauthorized admin access attempt: ${user.email}`);
    return null;
  }
  
  // Update last login
  await adminClient
    .from('actbi_admins')
    .update({ last_login_at: new Date().toISOString() })
    .eq('email', user.email);
  
  return {
    email: adminRecord.email,
    displayName: adminRecord.display_name,
  };
}

// Helper for use in Server Actions
export async function requireActBIAdmin(): Promise<ActBIAdmin> {
  const admin = await verifyActBIAdmin();
  if (!admin) {
    throw new Error('Unauthorized: ActBI admin access required');
  }
  return admin;
}
```

### 7.5 Server Actions

```typescript
// app/actions/admin.ts
'use server';

import { requireActBIAdmin } from '@/lib/auth/verifyAdmin';
import { createAdminSupabaseClient } from '@/lib/supabase/admin';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';

// Get client context for audit logging
async function getClientContext() {
  const headersList = await headers();
  return {
    ip: headersList.get('x-forwarded-for')?.split(',')[0] || 'unknown',
    userAgent: headersList.get('user-agent') || 'unknown',
  };
}

// ─────────────────────────────────────────────────────────────────
// Tenant Operations
// ─────────────────────────────────────────────────────────────────

export async function createTenant(formData: FormData) {
  const admin = await requireActBIAdmin();
  const { ip, userAgent } = await getClientContext();
  
  const tenantName = formData.get('tenantName') as string;
  if (!tenantName?.trim()) {
    throw new Error('Tenant name is required');
  }
  
  const supabase = createAdminSupabaseClient();
  
  const { data, error } = await supabase.rpc('admin_create_tenant', {
    p_admin_email: admin.email,
    p_tenant_name: tenantName.trim(),
    p_ip_address: ip,
    p_user_agent: userAgent,
  });
  
  if (error) {
    console.error('Failed to create tenant:', error);
    throw new Error(error.message);
  }
  
  revalidatePath('/admin/tenants');
  return { tenantId: data };
}

export async function listTenants() {
  const admin = await requireActBIAdmin();
  
  const supabase = createAdminSupabaseClient();
  
  const { data, error } = await supabase.rpc('admin_list_tenants', {
    p_admin_email: admin.email,
  });
  
  if (error) {
    console.error('Failed to list tenants:', error);
    throw new Error(error.message);
  }
  
  return data;
}

export async function getTenantDetails(tenantId: string) {
  const admin = await requireActBIAdmin();
  
  const supabase = createAdminSupabaseClient();
  
  const { data, error } = await supabase.rpc('admin_get_tenant_details', {
    p_admin_email: admin.email,
    p_tenant_id: tenantId,
  });
  
  if (error) {
    console.error('Failed to get tenant details:', error);
    throw new Error(error.message);
  }
  
  return data;
}

// ─────────────────────────────────────────────────────────────────
// User Operations
// ─────────────────────────────────────────────────────────────────

export async function addTenantSuperAdmin(tenantId: string, formData: FormData) {
  const admin = await requireActBIAdmin();
  const { ip, userAgent } = await getClientContext();
  
  const userEmail = formData.get('userEmail') as string;
  const userDisplayName = formData.get('userDisplayName') as string;
  
  if (!userEmail?.trim()) {
    throw new Error('User email is required');
  }
  
  const supabase = createAdminSupabaseClient();
  
  const { data, error } = await supabase.rpc('admin_add_tenant_superadmin', {
    p_admin_email: admin.email,
    p_tenant_id: tenantId,
    p_user_email: userEmail.trim(),
    p_user_display_name: userDisplayName?.trim() || null,
    p_ip_address: ip,
    p_user_agent: userAgent,
  });
  
  if (error) {
    console.error('Failed to add superadmin:', error);
    throw new Error(error.message);
  }
  
  revalidatePath(`/admin/tenants/${tenantId}`);
  return { userId: data };
}

export async function deactivateTenantUser(
  tenantId: string, 
  userId: string, 
  reason?: string
) {
  const admin = await requireActBIAdmin();
  const { ip } = await getClientContext();
  
  const supabase = createAdminSupabaseClient();
  
  const { error } = await supabase.rpc('admin_deactivate_tenant_user', {
    p_admin_email: admin.email,
    p_tenant_id: tenantId,
    p_user_id: userId,
    p_reason: reason || null,
    p_ip_address: ip,
  });
  
  if (error) {
    console.error('Failed to deactivate user:', error);
    throw new Error(error.message);
  }
  
  revalidatePath(`/admin/tenants/${tenantId}`);
  return { success: true };
}

// ─────────────────────────────────────────────────────────────────
// Audit Log
// ─────────────────────────────────────────────────────────────────

export async function getAuditLog(tenantId?: string, limit = 100, offset = 0) {
  const admin = await requireActBIAdmin();
  
  const supabase = createAdminSupabaseClient();
  
  const { data, error } = await supabase.rpc('admin_view_audit_log', {
    p_admin_email: admin.email,
    p_tenant_id: tenantId || null,
    p_limit: limit,
    p_offset: offset,
  });
  
  if (error) {
    console.error('Failed to get audit log:', error);
    throw new Error(error.message);
  }
  
  return data;
}
```

### 7.6 Middleware

```typescript
// middleware.ts
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  // If not logged in and trying to access /admin, redirect to login
  if (!user && request.nextUrl.pathname.startsWith('/admin')) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('redirect', request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  // If logged in and on login page, redirect to admin
  if (user && request.nextUrl.pathname === '/login') {
    const url = request.nextUrl.clone();
    url.pathname = '/admin/tenants';
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: ['/admin/:path*', '/login'],
};
```

### 7.7 Page Examples

```typescript
// app/admin/tenants/page.tsx
import { listTenants, createTenant } from '@/app/actions/admin';
import { verifyActBIAdmin } from '@/lib/auth/verifyAdmin';
import { redirect } from 'next/navigation';

export default async function TenantsPage() {
  const admin = await verifyActBIAdmin();
  if (!admin) {
    redirect('/login');
  }
  
  const tenants = await listTenants();
  
  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Tenants</h1>
        <span className="text-sm text-gray-500">
          Logged in as {admin.email}
        </span>
      </div>
      
      {/* Create tenant form */}
      <form action={createTenant} className="mb-8 p-4 border rounded">
        <h2 className="text-lg font-semibold mb-4">Create New Tenant</h2>
        <div className="flex gap-4">
          <input 
            name="tenantName" 
            placeholder="Tenant name" 
            required 
            className="border px-3 py-2 rounded flex-1"
          />
          <button 
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Create Tenant
          </button>
        </div>
      </form>
      
      {/* Tenant list */}
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="text-left p-3 border">Name</th>
            <th className="text-left p-3 border">Users</th>
            <th className="text-left p-3 border">Dashboards</th>
            <th className="text-left p-3 border">Created</th>
          </tr>
        </thead>
        <tbody>
          {tenants.map((tenant: any) => (
            <tr key={tenant.id} className="hover:bg-gray-50">
              <td className="p-3 border">
                <a 
                  href={`/admin/tenants/${tenant.id}`}
                  className="text-blue-600 hover:underline"
                >
                  {tenant.name}
                </a>
              </td>
              <td className="p-3 border">{tenant.user_count}</td>
              <td className="p-3 border">{tenant.dashboard_count}</td>
              <td className="p-3 border">
                {new Date(tenant.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 8. Security Model

### 8.1 Defense in Depth

| Layer | Control |
|-------|---------|
| **Network** | VPN required, DNS not public |
| **Authentication** | Google SSO with enforced 2FA |
| **Authorization** | `actbi_admins` table check |
| **Function-level** | Each function re-validates admin |
| **Database** | SECURITY DEFINER scopes access |
| **Audit** | Every action logged immutably |

### 8.2 What an Attacker Would Need

To compromise the admin system, an attacker would need ALL of:

1. VPN access to your network
2. Valid Google Workspace credentials for an @actbi.ai account
3. 2FA device for that account
4. That account to be in the `actbi_admins` table with `is_active = TRUE`

Even then, they can only:

- Create tenants
- Add users to tenants
- View tenant metadata

They CANNOT:

- Read customer dashboards, conversations, reports
- Modify customer data
- Access raw database tables
- Bypass the scoped functions

### 8.3 Breach Response

If an admin account is compromised:

```sql
-- Immediate revocation
UPDATE actbi_admins 
SET is_active = FALSE 
WHERE email = 'compromised@actbi.ai';

-- Review what they did
SELECT * FROM admin_audit_log 
WHERE admin_email = 'compromised@actbi.ai'
ORDER BY created_at DESC;
```

---

## 9. SOC II Compliance

### 9.1 Control Mapping

| SOC II Control | How We Address It |
|----------------|-------------------|
| **CC6.1** Logical access | VPN + SSO + 2FA + actbi_admins table |
| **CC6.2** Registration/authorization | Explicit grant in actbi_admins with granted_by |
| **CC6.3** Removal of access | Set is_active = FALSE, immediate effect |
| **CC6.6** Audit logging | admin_audit_log with immutable trigger |
| **CC6.7** System component restrictions | SECURITY DEFINER functions, no raw access |
| **CC7.2** Monitoring | Audit log review capability |

### 9.2 Audit Evidence

For auditors, you can provide:

```sql
-- All admin access grants
SELECT email, display_name, granted_by, granted_at, is_active
FROM actbi_admins
ORDER BY granted_at;

-- All admin actions in a period
SELECT * FROM admin_audit_log
WHERE created_at BETWEEN '2025-01-01' AND '2025-03-31'
ORDER BY created_at;

-- Actions by specific admin
SELECT * FROM admin_audit_log
WHERE admin_email = 'nikos@actbi.ai'
ORDER BY created_at DESC;

-- Actions on specific tenant
SELECT * FROM admin_audit_log
WHERE target_tenant_id = 'uuid-here'
ORDER BY created_at DESC;
```

---

## 10. Operational Procedures

### 10.1 Adding a New ActBI Admin

```sql
-- Only you (or designated admins) should run this
INSERT INTO actbi_admins (email, display_name, granted_by, notes)
VALUES (
    'new.person@actbi.ai',
    'New Person',
    'nikos@actbi.ai',
    'Support team - added for customer onboarding'
);
```

### 10.2 Removing an ActBI Admin

```sql
-- Immediate revocation
UPDATE actbi_admins 
SET is_active = FALSE 
WHERE email = 'departing@actbi.ai';

-- Or with expiration (for contractors)
UPDATE actbi_admins 
SET expires_at = '2025-06-30 23:59:59'
WHERE email = 'contractor@actbi.ai';
```

### 10.3 Reviewing Admin Activity

```sql
-- Weekly review query
SELECT 
    admin_email,
    action,
    COUNT(*) as action_count
FROM admin_audit_log
WHERE created_at > now() - interval '7 days'
GROUP BY admin_email, action
ORDER BY admin_email, action_count DESC;
```

### 10.4 Tenant Onboarding Checklist

1. ☐ Create tenant via admin app
2. ☐ Add customer's IT admin as SuperAdmin
3. ☐ Verify they can log in
4. ☐ Document in CRM
5. ☐ Send welcome email with next steps

---

## Summary

This design provides:

- **Isolated admin access** via VPN-only separate app
- **Strong authentication** via Google SSO + 2FA
- **Scoped operations** via SECURITY DEFINER functions
- **Complete audit trail** for SOC II compliance
- **Minimal blast radius** — admin can't access customer content
- **Easy revocation** — flip is_active to FALSE

The customer-facing app and RLS policies remain completely unchanged.

---

*End of Document*
