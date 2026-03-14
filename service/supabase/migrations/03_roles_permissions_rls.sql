-- Roles, permissions, role assignments, and tightened RLS for conversations/messages/chat_messages
-- Idempotent: safe to re-run

-- Ensure required extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

----------------------------
-- Core RBAC tables
----------------------------

create table if not exists roles (
  id uuid default gen_random_uuid() primary key,
  name varchar(50) not null unique,
  description text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists permissions (
  id uuid default gen_random_uuid() primary key,
  name varchar(100) not null unique,
  description text,
  resource varchar(50),
  action varchar(50),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists role_permissions (
  id uuid default gen_random_uuid() primary key,
  role_id uuid not null references roles(id) on delete cascade,
  permission_id uuid not null references permissions(id) on delete cascade,
  created_at timestamptz default now(),
  unique (role_id, permission_id)
);

create table if not exists user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email varchar(255),
  full_name varchar(255),
  role_id uuid references roles(id),
  avatar_url text,
  department varchar(100),
  position varchar(100),
  phone varchar(20),
  is_active boolean default true,
  last_login timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Drop view first to avoid type mismatch when users is already a view
drop view if exists users cascade;
drop table if exists users cascade;

create or replace view users as
select
  up.id,
  up.email,
  up.full_name,
  up.avatar_url,
  coalesce(r.name, 'viewer') as role,
  up.created_at,
  up.updated_at
from user_profiles up
left join roles r on r.id = up.role_id;

----------------------------
-- Seed roles and permissions
----------------------------

insert into roles (name, description)
values
  ('admin', 'Full system access with user management capabilities'),
  ('creator', 'Can create and manage content, limited administrative access'),
  ('viewer', 'Read-only access to most resources')
on conflict (name) do update
set description = excluded.description;

insert into permissions (name, description, resource, action)
values
  -- Content
  ('content.create', 'Create content', 'content', 'create'),
  ('content.read', 'Read content', 'content', 'read'),
  ('content.update', 'Update content', 'content', 'update'),
  ('content.delete', 'Delete content', 'content', 'delete'),
  -- Dashboards
  ('dashboard.read', 'Read dashboards', 'dashboard', 'read'),
  ('dashboard.analytics', 'View dashboard analytics', 'dashboard', 'analytics'),
  ('dashboard.admin', 'Administer dashboards', 'dashboard', 'admin'),
  -- Reports
  ('reports.create', 'Create reports', 'reports', 'create'),
  ('reports.read', 'Read reports', 'reports', 'read'),
  -- Settings
  ('settings.read', 'Read settings', 'settings', 'read'),
  ('settings.update', 'Update settings', 'settings', 'update'),
  -- Users
  ('users.create', 'Create users', 'users', 'create'),
  ('users.read', 'Read users', 'users', 'read'),
  ('users.update', 'Update users', 'users', 'update'),
  ('users.delete', 'Delete users', 'users', 'delete'),
  ('users.manage_roles', 'Manage roles and permissions', 'users', 'manage_roles')
on conflict (name) do update
set description = excluded.description,
    resource = excluded.resource,
    action = excluded.action;

-- Admin gets everything
with
  admin_role as (select id from roles where name = 'admin'),
  perms as (select name, id from permissions)
insert into role_permissions (role_id, permission_id)
select ar.id, p.id
from admin_role ar
cross join perms p
on conflict (role_id, permission_id) do nothing;

-- Creator
with
  creator_role as (select id from roles where name = 'creator'),
  perms as (select name, id from permissions)
insert into role_permissions (role_id, permission_id)
select cr.id, p.id
from creator_role cr
join perms p on p.name in (
  'content.create', 'content.read', 'content.update', 'content.delete',
  'dashboard.read', 'dashboard.analytics',
  'reports.create', 'reports.read'
)
on conflict (role_id, permission_id) do nothing;

-- Viewer
with
  viewer_role as (select id from roles where name = 'viewer'),
  perms as (select name, id from permissions)
insert into role_permissions (role_id, permission_id)
select vr.id, p.id
from viewer_role vr
join perms p on p.name in (
  'content.read',
  'dashboard.read',
  'reports.read'
)
on conflict (role_id, permission_id) do nothing;

----------------------------
-- Schema tweaks for sharing
----------------------------

alter table conversations
  add column if not exists is_public boolean default false;

----------------------------
-- RLS policies
----------------------------

-- roles
alter table roles enable row level security;
drop policy if exists roles_select_manage on roles;
drop policy if exists roles_write_manage on roles;
create policy roles_select_manage on roles
  for select
  using (user_has_permission(auth.uid(), 'users.manage_roles') or user_has_permission(auth.uid(), 'users.read') or user_has_permission(auth.uid(), 'settings.read'));
create policy roles_write_manage on roles
  for all
  using (user_has_permission(auth.uid(), 'users.manage_roles'))
  with check (user_has_permission(auth.uid(), 'users.manage_roles'));

-- permissions
alter table permissions enable row level security;
drop policy if exists permissions_select_manage on permissions;
drop policy if exists permissions_write_manage on permissions;
create policy permissions_select_manage on permissions
  for select
  using (user_has_permission(auth.uid(), 'users.manage_roles') or user_has_permission(auth.uid(), 'users.read') or user_has_permission(auth.uid(), 'settings.read'));
create policy permissions_write_manage on permissions
  for all
  using (user_has_permission(auth.uid(), 'users.manage_roles'))
  with check (user_has_permission(auth.uid(), 'users.manage_roles'));

-- role_permissions
alter table role_permissions enable row level security;
drop policy if exists role_permissions_select_manage on role_permissions;
drop policy if exists role_permissions_write_manage on role_permissions;
create policy role_permissions_select_manage on role_permissions
  for select
  using (user_has_permission(auth.uid(), 'users.manage_roles') or user_has_permission(auth.uid(), 'users.read'));
create policy role_permissions_write_manage on role_permissions
  for all
  using (user_has_permission(auth.uid(), 'users.manage_roles'))
  with check (user_has_permission(auth.uid(), 'users.manage_roles'));

-- user_profiles
alter table user_profiles enable row level security;
drop policy if exists user_profiles_self_select on user_profiles;
drop policy if exists user_profiles_admin_select on user_profiles;
drop policy if exists user_profiles_self_update on user_profiles;
drop policy if exists user_profiles_admin_update on user_profiles;
drop policy if exists user_profiles_admin_delete on user_profiles;
drop policy if exists user_profiles_insert_self on user_profiles;
drop policy if exists user_profiles_insert_admin on user_profiles;

create policy user_profiles_self_select on user_profiles
  for select
  using (id = auth.uid());

create policy user_profiles_admin_select on user_profiles
  for select
  using (user_has_permission(auth.uid(), 'users.read') or user_has_permission(auth.uid(), 'users.manage_roles'));

create policy user_profiles_self_update on user_profiles
  for update
  using (id = auth.uid())
  with check (id = auth.uid());

create policy user_profiles_admin_update on user_profiles
  for update
  using (user_has_permission(auth.uid(), 'users.update') or user_has_permission(auth.uid(), 'users.manage_roles'))
  with check (user_has_permission(auth.uid(), 'users.update') or user_has_permission(auth.uid(), 'users.manage_roles'));

create policy user_profiles_admin_delete on user_profiles
  for delete
  using (user_has_permission(auth.uid(), 'users.delete') or user_has_permission(auth.uid(), 'users.manage_roles'));

create policy user_profiles_insert_self on user_profiles
  for insert
  with check (id = auth.uid());

create policy user_profiles_insert_admin on user_profiles
  for insert
  with check (user_has_permission(auth.uid(), 'users.create') or user_has_permission(auth.uid(), 'users.manage_roles'));

-- users view inherits user_profiles policies; no extra RLS needed.

-- conversations
alter table conversations enable row level security;
drop policy if exists "Users can view own conversations" on conversations;
drop policy if exists "Users can create own conversations" on conversations;
drop policy if exists "Users can update own conversations" on conversations;
drop policy if exists "Users can delete own conversations" on conversations;
drop policy if exists "Anonymous conversations policy" on conversations;
drop policy if exists conversations_read_owner_or_public on conversations;
drop policy if exists conversations_insert_owner on conversations;
drop policy if exists conversations_update_owner on conversations;
drop policy if exists conversations_delete_owner on conversations;

create policy conversations_read_owner_or_public on conversations
  for select
  using (auth.uid() = user_id or is_public = true);

create policy conversations_insert_owner on conversations
  for insert
  with check (auth.uid() = user_id);

create policy conversations_update_owner on conversations
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy conversations_delete_owner on conversations
  for delete
  using (auth.uid() = user_id);

-- messages
alter table messages enable row level security;
drop policy if exists "Users can view messages from own conversations" on messages;
drop policy if exists "Users can add messages to own conversations" on messages;
drop policy if exists "Users can update messages in own conversations" on messages;
drop policy if exists "Users can delete messages in own conversations" on messages;
drop policy if exists "Anonymous messages policy" on messages;
drop policy if exists messages_read_owner_or_public on messages;
drop policy if exists messages_insert_owner on messages;
drop policy if exists messages_update_owner on messages;
drop policy if exists messages_delete_owner on messages;

create policy messages_read_owner_or_public on messages
  for select
  using (
    exists (
      select 1
      from conversations c
      where c.id = messages.conversation_id
        and (c.user_id = auth.uid() or c.is_public = true)
    )
  );

create policy messages_insert_owner on messages
  for insert
  with check (
    exists (
      select 1
      from conversations c
      where c.id = messages.conversation_id
        and c.user_id = auth.uid()
    )
  );

create policy messages_update_owner on messages
  for update
  using (
    exists (
      select 1
      from conversations c
      where c.id = messages.conversation_id
        and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from conversations c
      where c.id = messages.conversation_id
        and c.user_id = auth.uid()
    )
  );

create policy messages_delete_owner on messages
  for delete
  using (
    exists (
      select 1
      from conversations c
      where c.id = messages.conversation_id
        and c.user_id = auth.uid()
    )
  );

-- chat_messages (optional table in some deployments)
do $$
begin
  if to_regclass('public.chat_messages') is not null then
    alter table chat_messages enable row level security;
    drop policy if exists chat_messages_select_self on chat_messages;
    drop policy if exists chat_messages_insert_self on chat_messages;
    drop policy if exists chat_messages_update_self on chat_messages;
    drop policy if exists chat_messages_delete_self on chat_messages;

    create policy chat_messages_select_self on chat_messages
      for select
      using (user_id = auth.uid());

    create policy chat_messages_insert_self on chat_messages
      for insert
      with check (user_id = auth.uid());

    create policy chat_messages_update_self on chat_messages
      for update
      using (user_id = auth.uid())
      with check (user_id = auth.uid());

    create policy chat_messages_delete_self on chat_messages
      for delete
      using (user_id = auth.uid());
  end if;
end $$;
