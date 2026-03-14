-- Tenants and membership tables + profile fields for invite flow
-- Idempotent: safe to re-run

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- Core tenant entity
create table if not exists tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  metadata jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_tenants_name on tenants (lower(name));
create index if not exists idx_tenants_created_at on tenants (created_at desc);

-- Memberships (user ↔ tenant) with simple role + status
create table if not exists tenant_users (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member',
  status text not null default 'invited' check (status in ('invited','active','disabled')),
  invited_at timestamptz default now(),
  accepted_at timestamptz,
  created_at timestamptz default now(),
  unique (tenant_id, user_id)
);

create index if not exists idx_tenant_users_user on tenant_users(user_id);
create index if not exists idx_tenant_users_tenant on tenant_users(tenant_id);

-- Capture invite-profile details
alter table user_profiles
  add column if not exists first_name text,
  add column if not exists last_name text,
  add column if not exists company_email text,
  add column if not exists notes text;

-- RLS
alter table tenants enable row level security;
alter table tenant_users enable row level security;

drop policy if exists tenants_read_members on tenants;
drop policy if exists tenants_manage_admin on tenants;

create policy tenants_read_members on tenants
  for select
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenants.id
        and tu.user_id = auth.uid()
    )
    or user_has_permission(auth.uid(), 'users.read')
    or user_has_permission(auth.uid(), 'users.manage_roles')
  );

create policy tenants_manage_admin on tenants
  for all
  using (user_has_permission(auth.uid(), 'users.manage_roles'))
  with check (user_has_permission(auth.uid(), 'users.manage_roles'));

drop policy if exists tenant_users_read_self on tenant_users;
drop policy if exists tenant_users_manage_admin on tenant_users;
drop policy if exists tenant_users_self_update_status on tenant_users;

create policy tenant_users_read_self on tenant_users
  for select
  using (
    user_id = auth.uid()
    or user_has_permission(auth.uid(), 'users.read')
    or user_has_permission(auth.uid(), 'users.manage_roles')
  );

create policy tenant_users_manage_admin on tenant_users
  for all
  using (user_has_permission(auth.uid(), 'users.manage_roles'))
  with check (user_has_permission(auth.uid(), 'users.manage_roles'));

create policy tenant_users_self_update_status on tenant_users
  for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());
