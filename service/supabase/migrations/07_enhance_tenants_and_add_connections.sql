-- Enhance tenants table and add database connections & assets
-- Idempotent: safe to re-run

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- Enhance tenants table
alter table tenants
  add column if not exists status text not null default 'active' check (status in ('active', 'inactive')),
  add column if not exists branding jsonb default '{}',
  add column if not exists context_metadata jsonb default '{}';

-- Create indexes for new columns
create index if not exists idx_tenants_status on tenants (status);
create index if not exists idx_tenants_branding on tenants using gin (branding);

-- Database connections table
create table if not exists tenant_database_connections (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  name text not null,
  type text not null check (type in ('postgres', 'mysql', 'bigquery')),
  connection_config jsonb not null,
  is_active boolean default true,
  last_test_status text,
  last_tested_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (tenant_id, name)
);

create index if not exists idx_tenant_db_connections_tenant on tenant_database_connections(tenant_id);
create index if not exists idx_tenant_db_connections_type on tenant_database_connections(type);
create index if not exists idx_tenant_db_connections_active on tenant_database_connections(is_active);
create index if not exists idx_tenant_db_connections_config on tenant_database_connections using gin (connection_config);

-- Tenant assets table
create table if not exists tenant_assets (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  asset_type text not null check (asset_type in ('logo', 'markdown')),
  storage_path text not null,
  file_name text,
  file_size bigint,
  content_type text,
  created_at timestamptz default now(),
  unique (tenant_id, asset_type)
);

create index if not exists idx_tenant_assets_tenant on tenant_assets(tenant_id);
create index if not exists idx_tenant_assets_type on tenant_assets(asset_type);
create index if not exists idx_tenant_assets_path on tenant_assets(storage_path);

-- RLS for new tables
alter table tenant_database_connections enable row level security;
alter table tenant_assets enable row level security;

-- Policies for tenant_database_connections
drop policy if exists tenant_db_connections_tenant_members on tenant_database_connections;
drop policy if exists tenant_db_connections_admin_all on tenant_database_connections;

create policy tenant_db_connections_tenant_members on tenant_database_connections
  for select
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_database_connections.tenant_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
    )
    or user_has_permission(auth.uid(), 'tenant_connections.read')
    or user_has_permission(auth.uid(), 'tenants.manage')
  );

create policy tenant_db_connections_admin_all on tenant_database_connections
  for all
  using (user_has_permission(auth.uid(), 'tenant_connections.manage') or user_has_permission(auth.uid(), 'tenants.manage'))
  with check (user_has_permission(auth.uid(), 'tenant_connections.manage') or user_has_permission(auth.uid(), 'tenants.manage'));

-- Policies for tenant_assets
drop policy if exists tenant_assets_tenant_members on tenant_assets;
drop policy if exists tenant_assets_admin_all on tenant_assets;

create policy tenant_assets_tenant_members on tenant_assets
  for select
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_assets.tenant_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
    )
    or user_has_permission(auth.uid(), 'tenant_assets.read')
    or user_has_permission(auth.uid(), 'tenants.manage')
  );

create policy tenant_assets_admin_all on tenant_assets
  for all
  using (user_has_permission(auth.uid(), 'tenant_assets.manage') or user_has_permission(auth.uid(), 'tenants.manage'))
  with check (user_has_permission(auth.uid(), 'tenant_assets.manage') or user_has_permission(auth.uid(), 'tenants.manage'));

-- Update tenants RLS to include status and new fields
drop policy if exists tenants_read_members on tenants;
drop policy if exists tenants_manage_admin on tenants;

create policy tenants_read_members on tenants
  for select
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenants.id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
    )
    or user_has_permission(auth.uid(), 'tenants.read')
    or user_has_permission(auth.uid(), 'tenants.manage')
  );

create policy tenants_manage_admin on tenants
  for all
  using (user_has_permission(auth.uid(), 'tenants.manage'))
  with check (user_has_permission(auth.uid(), 'tenants.manage'));

-- Function to encrypt connection config
create or replace function encrypt_connection_config(config jsonb)
returns jsonb
language plpgsql
security definer
as $$
begin
  return jsonb_build_object(
    'encrypted', true,
    'data', crypt(
      convert_to(config::text, 'utf8'),
      gen_salt('bf')
    )
  );
end;
$$;

-- Function to decrypt connection config
create or replace function decrypt_connection_config(encrypted_data jsonb)
returns jsonb
language plpgsql
security definer
as $$
declare
  decrypted_text text;
begin
  if encrypted_data->>'encrypted' = 'true' then
    decrypted_text := convert_from(
      decrypt(encrypted_data->>'data'::bytea, '', 'bf'),
      'utf8'
    );
    return decrypted_text::jsonb;
  else
    return encrypted_data;
  end if;
end;
$$;

-- Helper function to test database connection status
create or replace function update_connection_test_status(
  connection_id uuid,
  status text,
  details jsonb default null
)
returns void
language plpgsql
security definer
as $$
begin
  update tenant_database_connections
  set 
    last_test_status = status,
    last_tested_at = now(),
    updated_at = now(),
    connection_config = connection_config || 
      case when details is not null then jsonb_build_object('last_test_details', details) else '{}' end
  where id = connection_id;
end;
$$;

-- Grant execute permissions
grant execute on function encrypt_connection_config(jsonb) to authenticated, service_role;
grant execute on function decrypt_connection_config(jsonb) to authenticated, service_role;
grant execute on function update_connection_test_status(uuid, text, jsonb) to authenticated, service_role;

-- Add new permissions for tenant management
insert into permissions (name, description, resource, action)
values 
  ('tenants.read', 'Read tenant information', 'tenants', 'read'),
  ('tenants.create', 'Create new tenants', 'tenants', 'create'),
  ('tenants.update', 'Update tenant information', 'tenants', 'update'),
  ('tenants.delete', 'Delete tenants', 'tenants', 'delete'),
  ('tenants.manage', 'Full tenant management', 'tenants', 'manage'),
  ('tenant_connections.read', 'Read tenant database connections', 'tenant_connections', 'read'),
  ('tenant_connections.create', 'Create tenant database connections', 'tenant_connections', 'create'),
  ('tenant_connections.update', 'Update tenant database connections', 'tenant_connections', 'update'),
  ('tenant_connections.delete', 'Delete tenant database connections', 'tenant_connections', 'delete'),
  ('tenant_connections.manage', 'Full tenant connection management', 'tenant_connections', 'manage'),
  ('tenant_assets.read', 'Read tenant assets', 'tenant_assets', 'read'),
  ('tenant_assets.create', 'Create tenant assets', 'tenant_assets', 'create'),
  ('tenant_assets.update', 'Update tenant assets', 'tenant_assets', 'update'),
  ('tenant_assets.delete', 'Delete tenant assets', 'tenant_assets', 'delete'),
  ('tenant_assets.manage', 'Full tenant asset management', 'tenant_assets', 'manage')
on conflict (name) do update set 
  description = excluded.description,
  resource = excluded.resource,
  action = excluded.action;

-- Assign new permissions to existing roles
with role_perms as (
  select 
    r.id as role_id,
    p.id as permission_id
  from roles r
  cross join permissions p
  where 
    r.name = 'superadmin' and (
      p.name like 'tenants.%' or 
      p.name like 'tenant_connections.%' or 
      p.name like 'tenant_assets.%'
    )
)
insert into role_permissions (role_id, permission_id)
select role_id, permission_id from role_perms
on conflict (role_id, permission_id) do nothing;

-- Give admin most permissions (except delete)
with role_perms as (
  select 
    r.id as role_id,
    p.id as permission_id
  from roles r
  cross join permissions p
  where 
    r.name = 'admin' and (
      (p.name like 'tenants.%' and p.name not like '%delete') or 
      (p.name like 'tenant_connections.%' and p.name not like '%delete') or 
      (p.name like 'tenant_assets.%' and p.name not like '%delete')
    )
)
insert into role_permissions (role_id, permission_id)
select role_id, permission_id from role_perms
on conflict (role_id, permission_id) do nothing;

-- Give creator read and create permissions
with role_perms as (
  select 
    r.id as role_id,
    p.id as permission_id
  from roles r
  cross join permissions p
  where 
    r.name = 'creator' and (
      p.name in ('tenants.read', 'tenant_connections.read', 'tenant_connections.create', 'tenant_assets.read', 'tenant_assets.create')
    )
)
insert into role_permissions (role_id, permission_id)
select role_id, permission_id from role_perms
on conflict (role_id, permission_id) do nothing;

-- Give viewer read permissions only
with role_perms as (
  select 
    r.id as role_id,
    p.id as permission_id
  from roles r
  cross join permissions p
  where 
    r.name = 'viewer' and (
      p.name in ('tenants.read', 'tenant_connections.read', 'tenant_assets.read')
    )
)
insert into role_permissions (role_id, permission_id)
select role_id, permission_id from role_perms
on conflict (role_id, permission_id) do nothing;
