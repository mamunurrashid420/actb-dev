-- Tenant roles and permissions management.
-- Idempotent: safe to re-run.

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- Tenant roles table
create table if not exists tenant_roles (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  name text not null,
  description text,
  is_system boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (tenant_id, name)
);

create index if not exists idx_tenant_roles_tenant on tenant_roles(tenant_id);

-- Tenant role permissions table
create table if not exists tenant_role_permissions (
  id uuid primary key default gen_random_uuid(),
  tenant_role_id uuid not null references tenant_roles(id) on delete cascade,
  permission_id uuid not null references permissions(id) on delete cascade,
  created_at timestamptz default now(),
  unique (tenant_role_id, permission_id)
);

create index if not exists idx_tenant_role_permissions_role on tenant_role_permissions(tenant_role_id);

-- Add tenant-specific permissions
insert into permissions (name, description, resource, action)
values
  ('tenant_roles.read', 'Read tenant roles', 'tenant_roles', 'read'),
  ('tenant_roles.manage', 'Manage tenant roles', 'tenant_roles', 'manage'),
  ('tenant_members.read', 'Read tenant members', 'tenant_members', 'read'),
  ('tenant_members.manage', 'Manage tenant members', 'tenant_members', 'manage'),
  ('tenant_assets.read', 'Read tenant assets', 'tenant_assets', 'read'),
  ('tenant_assets.manage', 'Manage tenant assets', 'tenant_assets', 'manage'),
  ('tenant_kb.read', 'Read tenant knowledge base', 'tenant_kb', 'read'),
  ('tenant_kb.manage', 'Manage tenant knowledge base', 'tenant_kb', 'manage')
on conflict (name) do update
set description = excluded.description,
    resource = excluded.resource,
    action = excluded.action;

-- RLS
alter table tenant_roles enable row level security;
alter table tenant_role_permissions enable row level security;

drop policy if exists tenant_roles_read on tenant_roles;
drop policy if exists tenant_roles_manage on tenant_roles;

create policy tenant_roles_read on tenant_roles
  for select
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_roles.tenant_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
    )
    or user_has_permission(auth.uid(), 'tenant_roles.read')
    or user_has_permission(auth.uid(), 'tenants.manage')
  );

create policy tenant_roles_manage on tenant_roles
  for all
  using (
    user_has_permission(auth.uid(), 'tenant_roles.manage')
    or user_has_permission(auth.uid(), 'tenants.manage')
    or exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_roles.tenant_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
        and tu.role = 'tenant_admin'
    )
  )
  with check (
    user_has_permission(auth.uid(), 'tenant_roles.manage')
    or user_has_permission(auth.uid(), 'tenants.manage')
    or exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_roles.tenant_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
        and tu.role = 'tenant_admin'
    )
  );

drop policy if exists tenant_role_permissions_read on tenant_role_permissions;
drop policy if exists tenant_role_permissions_manage on tenant_role_permissions;

create policy tenant_role_permissions_read on tenant_role_permissions
  for select
  using (
    exists (
      select 1 from tenant_roles tr
      join tenant_users tu on tu.tenant_id = tr.tenant_id
      where tr.id = tenant_role_permissions.tenant_role_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
    )
    or user_has_permission(auth.uid(), 'tenant_roles.read')
    or user_has_permission(auth.uid(), 'tenants.manage')
  );

create policy tenant_role_permissions_manage on tenant_role_permissions
  for all
  using (
    user_has_permission(auth.uid(), 'tenant_roles.manage')
    or user_has_permission(auth.uid(), 'tenants.manage')
    or exists (
      select 1 from tenant_roles tr
      join tenant_users tu on tu.tenant_id = tr.tenant_id
      where tr.id = tenant_role_permissions.tenant_role_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
        and tu.role = 'tenant_admin'
    )
  )
  with check (
    user_has_permission(auth.uid(), 'tenant_roles.manage')
    or user_has_permission(auth.uid(), 'tenants.manage')
    or exists (
      select 1 from tenant_roles tr
      join tenant_users tu on tu.tenant_id = tr.tenant_id
      where tr.id = tenant_role_permissions.tenant_role_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
        and tu.role = 'tenant_admin'
    )
  );

-- Seed default tenant roles for existing tenants
insert into tenant_roles (tenant_id, name, description, is_system)
select t.id, v.name, v.description, true
from tenants t
cross join (
  values
    ('tenant_admin', 'Tenant administrator'),
    ('tenant_editor', 'Tenant editor'),
    ('tenant_viewer', 'Tenant viewer')
) as v(name, description)
on conflict (tenant_id, name) do nothing;

-- Assign default permissions to tenant roles
with perms as (
  select id, name from permissions
),
roles as (
  select id, name from tenant_roles
)
insert into tenant_role_permissions (tenant_role_id, permission_id)
select r.id, p.id
from roles r
join perms p on (
  (r.name = 'tenant_admin' and p.name in (
    'tenant_roles.read', 'tenant_roles.manage',
    'tenant_members.read', 'tenant_members.manage',
    'tenant_assets.read', 'tenant_assets.manage',
    'tenant_kb.read', 'tenant_kb.manage',
    'tenant_connections.read', 'tenant_connections.manage'
  ))
  or (r.name = 'tenant_editor' and p.name in (
    'tenant_members.read',
    'tenant_assets.read', 'tenant_assets.manage',
    'tenant_kb.read', 'tenant_kb.manage',
    'tenant_connections.read'
  ))
  or (r.name = 'tenant_viewer' and p.name in (
    'tenant_members.read',
    'tenant_assets.read',
    'tenant_kb.read',
    'tenant_connections.read'
  ))
)
on conflict (tenant_role_id, permission_id) do nothing;
