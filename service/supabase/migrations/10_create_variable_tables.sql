-- Enable required extension for UUID generation
create extension if not exists pgcrypto;

-- Create enum type for variable type
do $$ begin
  if not exists (select 1 from pg_type typ join pg_namespace nsp on nsp.oid = typ.typnamespace where nsp.nspname = 'public' and typ.typname = 'variable_type') then
    create type public.variable_type as enum ('text', 'enum', 'boolean', 'number', 'JSON', 'multiline');
  end if;
end $$;

-- Create variables table
create table if not exists public.variables (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  type public.variable_type not null,
  default_value jsonb not null,
  description text not null,
  tags text[] null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Update updated_at on row updates
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists variables_set_updated_at on public.variables;
create trigger variables_set_updated_at
before update on public.variables
for each row
execute function public.set_updated_at();

-- Optional: basic index to speed up name lookups
create index if not exists variables_name_idx on public.variables using btree (name);

-- Enable RLS; service role can bypass in server-side operations
alter table public.variables enable row level security;


