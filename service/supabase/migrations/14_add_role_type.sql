-- Add role type column to distinguish application and tenant roles
-- Idempotent: safe to re-run

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

alter table roles
  add column if not exists type text not null default 'app';

update roles
  set type = coalesce(type, 'app');

alter table roles
  alter column type set default 'app';

alter table roles
  drop constraint if exists chk_roles_type;

alter table roles
  add constraint chk_roles_type check (type in ('app', 'tenant'));
