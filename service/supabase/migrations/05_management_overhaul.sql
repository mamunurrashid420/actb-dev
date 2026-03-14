-- Management overhaul: RBAC helpers, superadmin controls, and safer cascades.

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- Add superadmin flag to profiles.
alter table user_profiles
  add column if not exists is_superadmin boolean default false;

-- Ensure superadmin role exists.
insert into roles (name, description)
values ('superadmin', 'Bypasses RLS and has full system control')
on conflict (name) do update set description = excluded.description;

-- Keep existing superadmin profiles flagged.
update user_profiles up
set is_superadmin = true
from roles r
where up.role_id = r.id
  and r.name = 'superadmin';

-- Refresh users view to expose is_superadmin for callers that prefer the view.
drop view if exists users cascade;
create view users as
select
  up.id,
  up.email,
  up.full_name,
  up.avatar_url,
  coalesce(r.name, 'viewer') as role,
  up.is_superadmin,
  up.created_at,
  up.updated_at
from user_profiles up
left join roles r on r.id = up.role_id;

-- Helper: check if a user is superadmin.
create or replace function is_superadmin(p_user_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(
    (select is_superadmin from user_profiles where id = p_user_id),
    false
  );
$$;

-- Permission lookup with superadmin/service-role bypass.
create or replace function user_has_permission(p_user_id uuid, p_permission text)
returns boolean
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  caller_role text := current_setting('request.jwt.claim.role', true);
begin
  if p_user_id is null or p_permission is null then
    return false;
  end if;

  if caller_role = 'service_role' then
    return true;
  end if;

  if is_superadmin(p_user_id) then
    return true;
  end if;

  return exists (
    select 1
    from user_profiles up
    join role_permissions rp on rp.role_id = up.role_id
    join permissions p on p.id = rp.permission_id
    where up.id = p_user_id
      and lower(p.name) = lower(p_permission)
  );
end;
$$;

-- Return all permissions for a user (superadmins get everything).
drop function if exists get_user_permissions(uuid);
create or replace function get_user_permissions(p_user_id uuid)
returns table(permission_name text)
language sql
stable
security definer
set search_path = public
as $$
  select p.name as permission_name
  from permissions p
  where is_superadmin(p_user_id)

  union

  select distinct perm.name as permission_name
  from user_profiles up
  join role_permissions rp on rp.role_id = up.role_id
  join permissions perm on perm.id = rp.permission_id
  where up.id = p_user_id;
$$;

-- RPC to assign roles; limited to superadmins or role managers.
create or replace function assign_user_role(user_email text, role_name text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  caller uuid := auth.uid();
  caller_role text := current_setting('request.jwt.claim.role', true);
  target_user uuid;
  target_role uuid;
begin
  if caller is null and caller_role <> 'service_role' then
    raise exception 'Not authenticated';
  end if;

  if caller_role <> 'service_role' then
    if not is_superadmin(caller) and not user_has_permission(caller, 'users.manage_roles') then
      raise exception 'Insufficient privileges';
    end if;

    if lower(role_name) = 'superadmin' and not is_superadmin(caller) then
      raise exception 'Only superadmins can assign the superadmin role';
    end if;
  end if;

  select id into target_user from auth.users where lower(email) = lower(user_email) limit 1;
  if target_user is null then
    raise exception 'User not found';
  end if;

  select id into target_role from roles where lower(name) = lower(role_name) limit 1;
  if target_role is null then
    raise exception 'Role not found';
  end if;

  insert into user_profiles (id, email, role_id, is_superadmin, updated_at)
  values (target_user, user_email, target_role, lower(role_name) = 'superadmin', now())
  on conflict (id) do update
    set role_id = excluded.role_id,
        is_superadmin = excluded.is_superadmin,
        updated_at = now(),
        email = coalesce(user_profiles.email, excluded.email);
end;
$$;

grant execute on function is_superadmin(uuid) to authenticated, service_role;
grant execute on function user_has_permission(uuid, text) to authenticated, service_role;
grant execute on function get_user_permissions(uuid) to authenticated, service_role;
grant execute on function assign_user_role(text, text) to authenticated, service_role;

-- Give superadmin every permission record.
with
  sa as (select id from roles where name = 'superadmin'),
  perms as (select id from permissions)
insert into role_permissions (role_id, permission_id)
select sa.id, p.id from sa cross join perms p
on conflict (role_id, permission_id) do nothing;

-- Make conversation deletion cascade when a user is removed.
alter table conversations drop constraint if exists conversations_user_id_fkey;
alter table conversations
  add constraint conversations_user_id_fkey
  foreign key (user_id) references auth.users(id) on delete cascade;

-- Superadmin override policies for conversations/messages.
drop policy if exists conversations_superadmin_all on conversations;
create policy conversations_superadmin_all on conversations
  for all to authenticated
  using (is_superadmin(auth.uid()))
  with check (is_superadmin(auth.uid()));

drop policy if exists messages_superadmin_all on messages;
create policy messages_superadmin_all on messages
  for all to authenticated
  using (is_superadmin(auth.uid()))
  with check (is_superadmin(auth.uid()));
