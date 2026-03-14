-- Create prompts table
create table if not exists public.prompts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  tags text[] not null default '{}',
  blocks jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Trigger to update updated_at on prompts
create or replace function public.prompts_set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists prompts_set_updated_at on public.prompts;
create trigger prompts_set_updated_at
before update on public.prompts
for each row
execute function public.prompts_set_updated_at();

create index if not exists prompts_name_idx on public.prompts using btree (name);

alter table public.prompts enable row level security;


