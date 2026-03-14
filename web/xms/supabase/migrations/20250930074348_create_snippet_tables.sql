-- Create snippets table
create table if not exists public.snippets (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  body text not null,
  tags text[] not null default '{}',
  word_count integer not null,
  used_in_prompts integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Trigger to update updated_at
create or replace function public.snippets_set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists snippets_set_updated_at on public.snippets;
create trigger snippets_set_updated_at
before update on public.snippets
for each row
execute function public.snippets_set_updated_at();

create index if not exists snippets_name_idx on public.snippets using btree (name);

alter table public.snippets enable row level security;


