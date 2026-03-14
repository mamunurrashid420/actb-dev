-- Clean replacement: entity sharing model + internal admin operations

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";
create extension if not exists "vector";

-- Drop legacy RBAC policies, tables, and helpers
do $$
declare
  r record;
begin
  for r in
    select schemaname, tablename, policyname
    from pg_policies
    where schemaname = 'public'
      and tablename in (
        'roles',
        'permissions',
        'role_permissions',
        'tenant_roles',
        'tenant_role_permissions',
        'user_profiles',
        'tenants',
        'tenant_users',
        'tenant_database_connections',
        'tenant_assets',
        'conversations',
        'messages'
      )
  loop
    execute format('drop policy if exists %I on %I.%I', r.policyname, r.schemaname, r.tablename);
  end loop;
end $$;

drop view if exists users cascade;

-- Drop storage policies that depend on user_has_permission before dropping the function.
drop policy if exists tenant_assets_storage_read on storage.objects;
drop policy if exists tenant_assets_storage_manage on storage.objects;

drop function if exists user_has_permission(uuid, text);
drop function if exists get_user_permissions(uuid);
drop function if exists assign_user_role(text, text);
drop function if exists is_superadmin(uuid);

drop table if exists role_permissions cascade;
drop table if exists permissions cascade;
drop table if exists roles cascade;
drop table if exists tenant_role_permissions cascade;
drop table if exists tenant_roles cascade;

-- User profiles cleanup
alter table user_profiles
  add column if not exists display_name text,
  add column if not exists is_app_admin boolean default false;

alter table user_profiles
  drop column if exists role_id,
  drop column if exists is_superadmin;

create or replace view users as
select
  id,
  email,
  full_name,
  avatar_url,
  created_at,
  updated_at
from user_profiles;

-- Tenant membership roles/statuses
do $$
declare
  c record;
begin
  for c in
    select conname
    from pg_constraint
    where conrelid = 'tenant_users'::regclass
      and contype = 'c'
  loop
    execute format('alter table tenant_users drop constraint %I', c.conname);
  end loop;
end $$;

update tenant_users
set role = case
  when role in ('tenant_admin') then 'admin'
  when role in ('member', 'tenant_viewer') then 'viewer'
  when role in ('tenant_editor') then 'creator'
  else role
end
where role not in ('superadmin', 'admin', 'creator', 'viewer');

update tenant_users
set status = case when status = 'active' then 'active' else 'inactive' end;

alter table tenant_users
  alter column role set default 'viewer',
  alter column status set default 'active';

alter table tenant_users
  add constraint tenant_users_role_check
    check (role in ('superadmin', 'admin', 'creator', 'viewer')),
  add constraint tenant_users_status_check
    check (status in ('active', 'inactive'));

-- Dashboards and shares
create table if not exists dashboards (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  owner_user_id uuid not null references user_profiles(id),
  title text not null,
  description text,
  share_tenant_role text check (share_tenant_role in ('editor', 'participant', 'viewer')),
  share_public_enabled boolean not null default false,
  share_public_token text unique,
  share_public_expires_at timestamptz,
  embedding vector(1536),
  search_vector tsvector,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists dashboard_user_shares (
  id uuid primary key default gen_random_uuid(),
  dashboard_id uuid not null references dashboards(id) on delete cascade,
  user_id uuid not null references user_profiles(id) on delete cascade,
  role text not null check (role in ('editor', 'participant', 'viewer')),
  created_by uuid not null references user_profiles(id),
  created_at timestamptz not null default now(),
  unique (dashboard_id, user_id)
);

create index if not exists idx_dashboards_tenant on dashboards(tenant_id);
create index if not exists idx_dashboards_owner on dashboards(owner_user_id);
create index if not exists idx_dashboards_tenant_owner on dashboards(tenant_id, owner_user_id);
create index if not exists idx_dashboards_embedding on dashboards using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists idx_dashboards_search on dashboards using gin(search_vector);
create index if not exists idx_dashboard_user_shares_dashboard on dashboard_user_shares(dashboard_id);
create index if not exists idx_dashboard_user_shares_user on dashboard_user_shares(user_id);

-- Conversations and shares
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_name = 'conversations' and column_name = 'user_id'
  ) then
    alter table conversations rename column user_id to owner_user_id;
  end if;
end $$;

alter table conversations
  add column if not exists tenant_id uuid references tenants(id) on delete cascade,
  add column if not exists owner_user_id uuid references user_profiles(id),
  add column if not exists share_tenant_role text check (share_tenant_role in ('editor', 'participant', 'viewer')),
  add column if not exists embedding vector(1536),
  add column if not exists search_vector tsvector;

alter table conversations
  drop column if exists is_public;

create table if not exists conversation_user_shares (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id) on delete cascade,
  user_id uuid not null references user_profiles(id) on delete cascade,
  role text not null check (role in ('editor', 'participant', 'viewer')),
  created_by uuid not null references user_profiles(id),
  created_at timestamptz not null default now(),
  unique (conversation_id, user_id)
);

create index if not exists idx_conversations_tenant on conversations(tenant_id);
create index if not exists idx_conversations_owner on conversations(owner_user_id);
create index if not exists idx_conversations_search on conversations using gin(search_vector);
create index if not exists idx_conversation_user_shares_conversation on conversation_user_shares(conversation_id);
create index if not exists idx_conversation_user_shares_user on conversation_user_shares(user_id);

-- Reports and shares
create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  owner_user_id uuid not null references user_profiles(id),
  title text not null,
  share_tenant_role text check (share_tenant_role in ('editor', 'participant', 'viewer')),
  embedding vector(1536),
  search_vector tsvector,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists report_user_shares (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references reports(id) on delete cascade,
  user_id uuid not null references user_profiles(id) on delete cascade,
  role text not null check (role in ('editor', 'participant', 'viewer')),
  created_by uuid not null references user_profiles(id),
  created_at timestamptz not null default now(),
  unique (report_id, user_id)
);

create index if not exists idx_reports_tenant on reports(tenant_id);
create index if not exists idx_reports_owner on reports(owner_user_id);
create index if not exists idx_reports_search on reports using gin(search_vector);
create index if not exists idx_report_user_shares_report on report_user_shares(report_id);
create index if not exists idx_report_user_shares_user on report_user_shares(user_id);

-- Helper functions
create or replace function highest_role(role1 text, role2 text)
returns text
language plpgsql
immutable
as $$
declare
  priority text[] := array['owner', 'editor', 'participant', 'viewer'];
  pos1 int;
  pos2 int;
begin
  if role1 is null then return role2; end if;
  if role2 is null then return role1; end if;

  pos1 := array_position(priority, role1);
  pos2 := array_position(priority, role2);

  if pos1 < pos2 then return role1; else return role2; end if;
end;
$$;

create or replace function is_superadmin(p_user_id uuid, p_tenant_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public
set row_security = off
as $$
begin
  return exists (
    select 1 from tenant_users
    where tenant_id = p_tenant_id
      and user_id = p_user_id
      and role = 'superadmin'
      and status = 'active'
  );
end;
$$;

create or replace function is_tenant_admin(p_user_id uuid, p_tenant_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public
set row_security = off
as $$
begin
  return exists (
    select 1 from tenant_users
    where tenant_id = p_tenant_id
      and user_id = p_user_id
      and role in ('admin', 'superadmin')
      and status = 'active'
  );
end;
$$;

create or replace function is_tenant_creator(p_user_id uuid, p_tenant_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public
set row_security = off
as $$
begin
  return exists (
    select 1 from tenant_users
    where tenant_id = p_tenant_id
      and user_id = p_user_id
      and role = 'creator'
      and status = 'active'
  );
end;
$$;

create or replace function get_effective_dashboard_role(p_user_id uuid, p_dashboard_id uuid)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  v_dashboard record;
  v_user_share_role text;
  v_is_tenant_member boolean;
begin
  select owner_user_id, tenant_id, share_tenant_role
  into v_dashboard
  from dashboards
  where id = p_dashboard_id;

  if not found then
    return null;
  end if;

  if v_dashboard.owner_user_id = p_user_id then
    return 'owner';
  end if;

  if is_superadmin(p_user_id, v_dashboard.tenant_id) then
    return 'owner';
  end if;

  select role into v_user_share_role
  from dashboard_user_shares
  where dashboard_id = p_dashboard_id and user_id = p_user_id;

  if v_dashboard.share_tenant_role is not null then
    select exists (
      select 1 from tenant_users
      where tenant_id = v_dashboard.tenant_id
        and user_id = p_user_id
        and status = 'active'
    ) into v_is_tenant_member;

    if not v_is_tenant_member then
      return v_user_share_role;
    end if;
  else
    return v_user_share_role;
  end if;

  return highest_role(v_user_share_role, v_dashboard.share_tenant_role);
end;
$$;

create or replace function get_effective_conversation_role(p_user_id uuid, p_conversation_id uuid)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  v_conversation record;
  v_user_share_role text;
  v_is_tenant_member boolean;
begin
  select owner_user_id, tenant_id, share_tenant_role
  into v_conversation
  from conversations
  where id = p_conversation_id;

  if not found then
    return null;
  end if;

  if v_conversation.owner_user_id = p_user_id then
    return 'owner';
  end if;

  if is_superadmin(p_user_id, v_conversation.tenant_id) then
    return 'owner';
  end if;

  select role into v_user_share_role
  from conversation_user_shares
  where conversation_id = p_conversation_id and user_id = p_user_id;

  if v_conversation.share_tenant_role is not null then
    select exists (
      select 1 from tenant_users
      where tenant_id = v_conversation.tenant_id
        and user_id = p_user_id
        and status = 'active'
    ) into v_is_tenant_member;

    if not v_is_tenant_member then
      return v_user_share_role;
    end if;
  else
    return v_user_share_role;
  end if;

  return highest_role(v_user_share_role, v_conversation.share_tenant_role);
end;
$$;

create or replace function get_effective_report_role(p_user_id uuid, p_report_id uuid)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  v_report record;
  v_user_share_role text;
  v_is_tenant_member boolean;
begin
  select owner_user_id, tenant_id, share_tenant_role
  into v_report
  from reports
  where id = p_report_id;

  if not found then
    return null;
  end if;

  if v_report.owner_user_id = p_user_id then
    return 'owner';
  end if;

  if is_superadmin(p_user_id, v_report.tenant_id) then
    return 'owner';
  end if;

  select role into v_user_share_role
  from report_user_shares
  where report_id = p_report_id and user_id = p_user_id;

  if v_report.share_tenant_role is not null then
    select exists (
      select 1 from tenant_users
      where tenant_id = v_report.tenant_id
        and user_id = p_user_id
        and status = 'active'
    ) into v_is_tenant_member;

    if not v_is_tenant_member then
      return v_user_share_role;
    end if;
  else
    return v_user_share_role;
  end if;

  return highest_role(v_user_share_role, v_report.share_tenant_role);
end;
$$;

-- View of accessible dashboards with effective role
create or replace view my_dashboards as
select
  d.id,
  d.tenant_id,
  d.owner_user_id,
  d.title,
  d.description,
  d.share_tenant_role,
  d.share_public_enabled,
  d.share_public_token,
  d.share_public_expires_at,
  d.created_at,
  d.updated_at,
  case
    when d.owner_user_id = auth.uid() then 'owner'
    when is_superadmin(auth.uid(), d.tenant_id) then 'owner'
    when dus.role is not null and d.share_tenant_role is not null then
      highest_role(dus.role, d.share_tenant_role)
    when dus.role is not null then dus.role
    when d.share_tenant_role is not null and exists (
      select 1 from tenant_users
      where tenant_id = d.tenant_id
        and user_id = auth.uid()
        and status = 'active'
    ) then d.share_tenant_role
    else null
  end as effective_role
from dashboards d
left join dashboard_user_shares dus
  on dus.dashboard_id = d.id and dus.user_id = auth.uid()
where
  d.owner_user_id = auth.uid()
  or is_superadmin(auth.uid(), d.tenant_id)
  or dus.user_id is not null
  or (
    d.share_tenant_role is not null and exists (
      select 1 from tenant_users
      where tenant_id = d.tenant_id
        and user_id = auth.uid()
        and status = 'active'
    )
  );

-- Search RPC
create or replace function search_my_dashboards(
  p_tenant_id uuid,
  p_query text,
  p_query_embedding vector(1536) default null,
  p_mode text default 'keyword',
  p_limit int default 20
)
returns table (
  id uuid,
  title text,
  description text,
  effective_role text,
  score real
) language plpgsql security definer
set search_path = public
as $$
begin
  if p_mode = 'keyword' then
    return query
    select
      d.id,
      d.title,
      d.description,
      d.effective_role,
      ts_rank(db.search_vector, plainto_tsquery('english', p_query))::real as score
    from my_dashboards d
    join dashboards db on db.id = d.id
    where d.tenant_id = p_tenant_id
      and db.search_vector @@ plainto_tsquery('english', p_query)
    order by score desc
    limit p_limit;

  elsif p_mode = 'semantic' then
    return query
    select
      d.id,
      d.title,
      d.description,
      d.effective_role,
      (1 - (db.embedding <=> p_query_embedding))::real as score
    from my_dashboards d
    join dashboards db on db.id = d.id
    where d.tenant_id = p_tenant_id
      and db.embedding is not null
    order by db.embedding <=> p_query_embedding
    limit p_limit;

  elsif p_mode = 'hybrid' then
    return query
    select
      d.id,
      d.title,
      d.description,
      d.effective_role,
      (
        coalesce(ts_rank(db.search_vector, plainto_tsquery('english', p_query)), 0) * 0.3 +
        coalesce(1 - (db.embedding <=> p_query_embedding), 0) * 0.7
      )::real as score
    from my_dashboards d
    join dashboards db on db.id = d.id
    where d.tenant_id = p_tenant_id
      and (
        db.search_vector @@ plainto_tsquery('english', p_query)
        or db.embedding is not null
      )
    order by score desc
    limit p_limit;
  end if;
end;
$$;

-- RLS setup
alter table tenants enable row level security;
alter table tenant_users enable row level security;
alter table user_profiles enable row level security;
alter table tenant_database_connections enable row level security;
alter table tenant_assets enable row level security;
alter table dashboards enable row level security;
alter table dashboard_user_shares enable row level security;
alter table conversations enable row level security;
alter table conversation_user_shares enable row level security;
alter table messages enable row level security;
alter table reports enable row level security;
alter table report_user_shares enable row level security;

-- Tenants
create policy tenants_select on tenants
  for select
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenants.id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
    )
  );

create policy tenants_update on tenants
  for update
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenants.id
        and tu.user_id = auth.uid()
        and tu.role = 'superadmin'
        and tu.status = 'active'
    )
  )
  with check (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenants.id
        and tu.user_id = auth.uid()
        and tu.role = 'superadmin'
        and tu.status = 'active'
    )
  );

-- Tenant users
create policy tenant_users_select on tenant_users
  for select
  using (
    user_id = auth.uid()
    or is_tenant_admin(auth.uid(), tenant_users.tenant_id)
  );

create policy tenant_users_insert on tenant_users
  for insert
  with check (
    is_tenant_admin(auth.uid(), tenant_users.tenant_id)
  );

create policy tenant_users_update on tenant_users
  for update
  using (
    is_tenant_admin(auth.uid(), tenant_users.tenant_id)
  )
  with check (
    is_tenant_admin(auth.uid(), tenant_users.tenant_id)
  );

create policy tenant_users_delete on tenant_users
  for delete
  using (
    is_tenant_admin(auth.uid(), tenant_users.tenant_id)
  );

-- Tenant database connections (tenant settings)
create policy tenant_db_connections_select on tenant_database_connections
  for select
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_database_connections.tenant_id
        and tu.user_id = auth.uid()
        and tu.role = 'superadmin'
        and tu.status = 'active'
    )
  );

create policy tenant_db_connections_manage on tenant_database_connections
  for all
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_database_connections.tenant_id
        and tu.user_id = auth.uid()
        and tu.role = 'superadmin'
        and tu.status = 'active'
    )
  )
  with check (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_database_connections.tenant_id
        and tu.user_id = auth.uid()
        and tu.role = 'superadmin'
        and tu.status = 'active'
    )
  );

-- Tenant assets (tenant settings)
create policy tenant_assets_select on tenant_assets
  for select
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_assets.tenant_id
        and tu.user_id = auth.uid()
        and tu.status = 'active'
    )
  );

create policy tenant_assets_manage on tenant_assets
  for all
  using (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_assets.tenant_id
        and tu.user_id = auth.uid()
        and tu.role = 'superadmin'
        and tu.status = 'active'
    )
  )
  with check (
    exists (
      select 1 from tenant_users tu
      where tu.tenant_id = tenant_assets.tenant_id
        and tu.user_id = auth.uid()
        and tu.role = 'superadmin'
        and tu.status = 'active'
    )
  );

-- Storage policies for tenant assets bucket
drop policy if exists tenant_assets_storage_read on storage.objects;
drop policy if exists tenant_assets_storage_manage on storage.objects;

create policy tenant_assets_storage_read on storage.objects
  for select
  using (
    bucket_id = 'tenant-assets'
    and exists (
      select 1 from tenant_users tu
      where tu.user_id = auth.uid()
        and tu.status = 'active'
        and tu.tenant_id::text = split_part(name, '/', 2)
    )
  );

create policy tenant_assets_storage_manage on storage.objects
  for all
  using (
    bucket_id = 'tenant-assets'
    and exists (
      select 1 from tenant_users tu
      where tu.user_id = auth.uid()
        and tu.status = 'active'
        and tu.role = 'superadmin'
        and tu.tenant_id::text = split_part(name, '/', 2)
    )
  )
  with check (
    bucket_id = 'tenant-assets'
    and exists (
      select 1 from tenant_users tu
      where tu.user_id = auth.uid()
        and tu.status = 'active'
        and tu.role = 'superadmin'
        and tu.tenant_id::text = split_part(name, '/', 2)
    )
  );

-- User profiles (self + tenant admin read)
create policy user_profiles_self_select on user_profiles
  for select
  using (
    id = auth.uid()
    or exists (
      select 1
      from tenant_users me
      join tenant_users member
        on member.tenant_id = me.tenant_id
       and member.user_id = user_profiles.id
      where me.user_id = auth.uid()
        and me.role in ('admin', 'superadmin')
        and me.status = 'active'
    )
  );

create policy user_profiles_self_update on user_profiles
  for update
  using (id = auth.uid())
  with check (id = auth.uid());

create policy user_profiles_self_insert on user_profiles
  for insert
  with check (id = auth.uid());

-- Prompts/snippets/variables (authenticated users)
create policy snippets_select on snippets
  for select
  using (auth.uid() is not null);
create policy snippets_insert on snippets
  for insert
  with check (auth.uid() is not null);
create policy snippets_update on snippets
  for update
  using (auth.uid() is not null)
  with check (auth.uid() is not null);
create policy snippets_delete on snippets
  for delete
  using (auth.uid() is not null);

create policy prompts_select on prompts
  for select
  using (auth.uid() is not null);
create policy prompts_insert on prompts
  for insert
  with check (auth.uid() is not null);
create policy prompts_update on prompts
  for update
  using (auth.uid() is not null)
  with check (auth.uid() is not null);
create policy prompts_delete on prompts
  for delete
  using (auth.uid() is not null);

create policy variables_select on variables
  for select
  using (auth.uid() is not null);
create policy variables_insert on variables
  for insert
  with check (auth.uid() is not null);
create policy variables_update on variables
  for update
  using (auth.uid() is not null)
  with check (auth.uid() is not null);
create policy variables_delete on variables
  for delete
  using (auth.uid() is not null);

-- Dashboards
create policy dashboards_select on dashboards
  for select
  using (
    get_effective_dashboard_role(auth.uid(), id) is not null
    or (
      share_public_enabled = true
      and share_public_token = current_setting('request.headers.x-public-token', true)
      and (share_public_expires_at is null or share_public_expires_at > now())
    )
  );

create policy dashboards_insert on dashboards
  for insert
  with check (
    owner_user_id = auth.uid()
    and (is_superadmin(auth.uid(), dashboards.tenant_id)
      or is_tenant_creator(auth.uid(), dashboards.tenant_id))
  );

-- Allow owner inserts for local testing if tenant checks fail
create policy dashboards_insert_owner on dashboards
  for insert
  with check (owner_user_id = auth.uid());

create policy dashboards_update on dashboards
  for update
  using (get_effective_dashboard_role(auth.uid(), id) in ('owner', 'editor'))
  with check (get_effective_dashboard_role(auth.uid(), id) in ('owner', 'editor'));

create policy dashboards_delete on dashboards
  for delete
  using (get_effective_dashboard_role(auth.uid(), id) = 'owner');

-- Dashboard shares
create policy dashboard_user_shares_select on dashboard_user_shares
  for select
  using (get_effective_dashboard_role(auth.uid(), dashboard_id) is not null);

create policy dashboard_user_shares_insert on dashboard_user_shares
  for insert
  with check (
    get_effective_dashboard_role(auth.uid(), dashboard_id) in ('owner', 'editor', 'participant')
  );

create policy dashboard_user_shares_update on dashboard_user_shares
  for update
  using (
    get_effective_dashboard_role(auth.uid(), dashboard_id) in ('owner', 'editor', 'participant')
  )
  with check (
    get_effective_dashboard_role(auth.uid(), dashboard_id) in ('owner', 'editor', 'participant')
  );

create policy dashboard_user_shares_delete on dashboard_user_shares
  for delete
  using (
    get_effective_dashboard_role(auth.uid(), dashboard_id) in ('owner', 'editor', 'participant')
  );

-- Conversations
create policy conversations_select on conversations
  for select
  using (get_effective_conversation_role(auth.uid(), id) is not null);

create policy conversations_insert on conversations
  for insert
  with check (
    owner_user_id = auth.uid()
    and (is_superadmin(auth.uid(), conversations.tenant_id)
      or is_tenant_creator(auth.uid(), conversations.tenant_id))
  );

-- Allow owner inserts for local testing if tenant checks fail
create policy conversations_insert_owner on conversations
  for insert
  with check (owner_user_id = auth.uid());

create policy conversations_update on conversations
  for update
  using (get_effective_conversation_role(auth.uid(), id) in ('owner', 'editor'))
  with check (get_effective_conversation_role(auth.uid(), id) in ('owner', 'editor'));

create policy conversations_delete on conversations
  for delete
  using (get_effective_conversation_role(auth.uid(), id) = 'owner');

-- Conversation shares
create policy conversation_user_shares_select on conversation_user_shares
  for select
  using (get_effective_conversation_role(auth.uid(), conversation_id) is not null);

create policy conversation_user_shares_insert on conversation_user_shares
  for insert
  with check (
    get_effective_conversation_role(auth.uid(), conversation_id) in ('owner', 'editor', 'participant')
  );

create policy conversation_user_shares_update on conversation_user_shares
  for update
  using (
    get_effective_conversation_role(auth.uid(), conversation_id) in ('owner', 'editor', 'participant')
  )
  with check (
    get_effective_conversation_role(auth.uid(), conversation_id) in ('owner', 'editor', 'participant')
  );

create policy conversation_user_shares_delete on conversation_user_shares
  for delete
  using (
    get_effective_conversation_role(auth.uid(), conversation_id) in ('owner', 'editor', 'participant')
  );

-- Messages (participation)
create policy messages_select on messages
  for select
  using (get_effective_conversation_role(auth.uid(), conversation_id) is not null);

create policy messages_insert on messages
  for insert
  with check (
    get_effective_conversation_role(auth.uid(), conversation_id) in ('owner', 'editor', 'participant')
  );

create policy messages_update on messages
  for update
  using (
    get_effective_conversation_role(auth.uid(), conversation_id) in ('owner', 'editor')
  )
  with check (
    get_effective_conversation_role(auth.uid(), conversation_id) in ('owner', 'editor')
  );

create policy messages_delete on messages
  for delete
  using (get_effective_conversation_role(auth.uid(), conversation_id) = 'owner');

-- Reports
create policy reports_select on reports
  for select
  using (get_effective_report_role(auth.uid(), id) is not null);

create policy reports_insert on reports
  for insert
  with check (
    owner_user_id = auth.uid()
    and exists (
      select 1 from tenant_users tu
      where tu.tenant_id = reports.tenant_id
        and tu.user_id = auth.uid()
        and tu.role in ('superadmin', 'creator')
        and tu.status = 'active'
    )
  );

create policy reports_update on reports
  for update
  using (get_effective_report_role(auth.uid(), id) in ('owner', 'editor'))
  with check (get_effective_report_role(auth.uid(), id) in ('owner', 'editor'));

create policy reports_delete on reports
  for delete
  using (get_effective_report_role(auth.uid(), id) = 'owner');

-- Report shares
create policy report_user_shares_select on report_user_shares
  for select
  using (get_effective_report_role(auth.uid(), report_id) is not null);

create policy report_user_shares_insert on report_user_shares
  for insert
  with check (
    get_effective_report_role(auth.uid(), report_id) in ('owner', 'editor', 'participant')
  );

create policy report_user_shares_update on report_user_shares
  for update
  using (
    get_effective_report_role(auth.uid(), report_id) in ('owner', 'editor', 'participant')
  )
  with check (
    get_effective_report_role(auth.uid(), report_id) in ('owner', 'editor', 'participant')
  );

create policy report_user_shares_delete on report_user_shares
  for delete
  using (
    get_effective_report_role(auth.uid(), report_id) in ('owner', 'editor', 'participant')
  );

-- Internal admin operations (ActBI admins)
create table if not exists actbi_admins (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  display_name text,
  is_active boolean not null default true,
  granted_by text not null,
  granted_at timestamptz not null default now(),
  expires_at timestamptz,
  last_login_at timestamptz,
  notes text
);

create table if not exists admin_audit_log (
  id uuid primary key default gen_random_uuid(),
  admin_email text not null,
  action text not null,
  target_tenant_id uuid,
  target_user_id uuid,
  details jsonb not null default '{}'::jsonb,
  ip_address text,
  user_agent text,
  created_at timestamptz not null default now()
);

create index if not exists idx_admin_audit_log_admin on admin_audit_log(admin_email);
create index if not exists idx_admin_audit_log_tenant on admin_audit_log(target_tenant_id);
create index if not exists idx_admin_audit_log_action on admin_audit_log(action);
create index if not exists idx_admin_audit_log_created on admin_audit_log(created_at desc);

create or replace function prevent_audit_log_modification()
returns trigger as $$
begin
  raise exception 'Audit log cannot be modified';
end;
$$ language plpgsql;

drop trigger if exists audit_log_immutable on admin_audit_log;
create trigger audit_log_immutable
before update or delete on admin_audit_log
for each row execute function prevent_audit_log_modification();

create or replace function validate_actbi_admin(p_admin_email text)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  if not exists (
    select 1 from actbi_admins
    where email = p_admin_email
      and is_active = true
      and (expires_at is null or expires_at > now())
  ) then
    raise exception 'Unauthorized: % is not an active ActBI admin', p_admin_email;
  end if;
  return true;
end;
$$;

create or replace function admin_create_tenant(
  p_admin_email text,
  p_tenant_name text,
  p_ip_address text default null,
  p_user_agent text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_tenant_id uuid;
begin
  perform validate_actbi_admin(p_admin_email);

  if p_tenant_name is null or trim(p_tenant_name) = '' then
    raise exception 'Tenant name is required';
  end if;

  insert into tenants (name)
  values (trim(p_tenant_name))
  returning id into v_tenant_id;

  insert into admin_audit_log (
    admin_email,
    action,
    target_tenant_id,
    details,
    ip_address,
    user_agent
  )
  values (
    p_admin_email,
    'create_tenant',
    v_tenant_id,
    jsonb_build_object('tenant_name', p_tenant_name),
    p_ip_address,
    p_user_agent
  );

  return v_tenant_id;
end;
$$;

create or replace function admin_add_tenant_superadmin(
  p_admin_email text,
  p_tenant_id uuid,
  p_user_email text,
  p_user_display_name text,
  p_ip_address text default null,
  p_user_agent text default null
)
returns uuid
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_user_id uuid;
begin
  perform validate_actbi_admin(p_admin_email);

  if not exists (select 1 from tenants where id = p_tenant_id) then
    raise exception 'Tenant not found: %', p_tenant_id;
  end if;

  if p_user_email is null or trim(p_user_email) = '' then
    raise exception 'User email is required';
  end if;

  select id into v_user_id
  from auth.users
  where email = lower(trim(p_user_email))
  limit 1;

  if v_user_id is null then
    raise exception 'Auth user not found for email: %', p_user_email;
  end if;

  insert into user_profiles (id, email, display_name)
  values (v_user_id, lower(trim(p_user_email)), trim(p_user_display_name))
  on conflict (id) do update set
    display_name = coalesce(excluded.display_name, user_profiles.display_name),
    email = coalesce(user_profiles.email, excluded.email);

  insert into tenant_users (tenant_id, user_id, role, status)
  values (p_tenant_id, v_user_id, 'superadmin', 'active')
  on conflict (tenant_id, user_id) do update set
    role = 'superadmin',
    status = 'active';

  insert into admin_audit_log (
    admin_email,
    action,
    target_tenant_id,
    target_user_id,
    details,
    ip_address,
    user_agent
  )
  values (
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

  return v_user_id;
end;
$$;

create or replace function admin_list_tenants(p_admin_email text)
returns table (
  id uuid,
  name text,
  created_at timestamptz,
  user_count bigint,
  dashboard_count bigint,
  conversation_count bigint,
  report_count bigint
)
language plpgsql
security definer
set search_path = public
as $$
begin
  perform validate_actbi_admin(p_admin_email);

  return query
  select
    t.id,
    t.name,
    t.created_at,
    (select count(*) from tenant_users tu where tu.tenant_id = t.id and tu.status = 'active'),
    (select count(*) from dashboards d where d.tenant_id = t.id),
    (select count(*) from conversations c where c.tenant_id = t.id),
    (select count(*) from reports r where r.tenant_id = t.id)
  from tenants t
  order by t.created_at desc;
end;
$$;

create or replace function admin_get_tenant_details(
  p_admin_email text,
  p_tenant_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_result jsonb;
begin
  perform validate_actbi_admin(p_admin_email);

  if not exists (select 1 from tenants where id = p_tenant_id) then
    raise exception 'Tenant not found: %', p_tenant_id;
  end if;

  select jsonb_build_object(
    'tenant', (
      select jsonb_build_object(
        'id', t.id,
        'name', t.name,
        'created_at', t.created_at
      )
      from tenants t
      where t.id = p_tenant_id
    ),
    'users', (
      select coalesce(jsonb_agg(
        jsonb_build_object(
          'user_id', tu.user_id,
          'email', up.email,
          'display_name', up.display_name,
          'role', tu.role,
          'status', tu.status,
          'created_at', tu.created_at
        ) order by tu.created_at
      ), '[]'::jsonb)
      from tenant_users tu
      join user_profiles up on up.id = tu.user_id
      where tu.tenant_id = p_tenant_id
    ),
    'stats', jsonb_build_object(
      'dashboard_count', (select count(*) from dashboards where tenant_id = p_tenant_id),
      'conversation_count', (select count(*) from conversations where tenant_id = p_tenant_id),
      'report_count', (select count(*) from reports where tenant_id = p_tenant_id)
    )
  ) into v_result;

  insert into admin_audit_log (admin_email, action, target_tenant_id, details)
  values (p_admin_email, 'view_tenant_details', p_tenant_id, '{}'::jsonb);

  return v_result;
end;
$$;

create or replace function admin_deactivate_tenant_user(
  p_admin_email text,
  p_tenant_id uuid,
  p_user_id uuid,
  p_reason text default null,
  p_ip_address text default null
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  perform validate_actbi_admin(p_admin_email);

  if not exists (
    select 1 from tenant_users
    where tenant_id = p_tenant_id and user_id = p_user_id
  ) then
    raise exception 'User not found in tenant';
  end if;

  update tenant_users
  set status = 'inactive'
  where tenant_id = p_tenant_id and user_id = p_user_id;

  insert into admin_audit_log (
    admin_email,
    action,
    target_tenant_id,
    target_user_id,
    details,
    ip_address
  )
  values (
    p_admin_email,
    'deactivate_tenant_user',
    p_tenant_id,
    p_user_id,
    jsonb_build_object('reason', p_reason),
    p_ip_address
  );

  return true;
end;
$$;

create or replace function admin_view_audit_log(
  p_admin_email text,
  p_tenant_id uuid default null,
  p_limit int default 100,
  p_offset int default 0
)
returns table (
  id uuid,
  admin_email text,
  action text,
  target_tenant_id uuid,
  target_user_id uuid,
  details jsonb,
  ip_address text,
  created_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
  perform validate_actbi_admin(p_admin_email);

  return query
  select
    al.id,
    al.admin_email,
    al.action,
    al.target_tenant_id,
    al.target_user_id,
    al.details,
    al.ip_address,
    al.created_at
  from admin_audit_log al
  where (p_tenant_id is null or al.target_tenant_id = p_tenant_id)
  order by al.created_at desc
  limit p_limit
  offset p_offset;
end;
$$;

revoke all on function validate_actbi_admin(text) from public;
revoke all on function admin_create_tenant(text, text, text, text) from public;
revoke all on function admin_add_tenant_superadmin(text, uuid, text, text, text, text) from public;
revoke all on function admin_list_tenants(text) from public;
revoke all on function admin_get_tenant_details(text, uuid) from public;
revoke all on function admin_deactivate_tenant_user(text, uuid, uuid, text, text) from public;
revoke all on function admin_view_audit_log(text, uuid, int, int) from public;

grant execute on function validate_actbi_admin(text) to service_role;
grant execute on function admin_create_tenant(text, text, text, text) to service_role;
grant execute on function admin_add_tenant_superadmin(text, uuid, text, text, text, text) to service_role;
grant execute on function admin_list_tenants(text) to service_role;
grant execute on function admin_get_tenant_details(text, uuid) to service_role;
grant execute on function admin_deactivate_tenant_user(text, uuid, uuid, text, text) to service_role;
grant execute on function admin_view_audit_log(text, uuid, int, int) to service_role;
