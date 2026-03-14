-- Bootstrap user_has_permission before RLS policies reference it.
-- This is replaced with the full implementation in later migrations.

create or replace function user_has_permission(p_user_id uuid, p_permission text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select false;
$$;
