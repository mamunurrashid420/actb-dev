-- Add updated_at to tenant_users for better auditing of membership changes.

alter table tenant_users
  add column if not exists updated_at timestamptz default now();

-- Backfill existing rows to avoid nulls.
update tenant_users
set updated_at = coalesce(updated_at, greatest(created_at, invited_at, accepted_at, now()))
where updated_at is null;
