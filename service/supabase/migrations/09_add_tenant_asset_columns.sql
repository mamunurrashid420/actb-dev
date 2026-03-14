-- Add logo_url and document_name columns to tenants table for performance optimization
-- This eliminates the need for separate asset API calls when displaying tenant table
-- Idempotent: safe to re-run

-- Add columns to tenants table
alter table tenants
  add column if not exists logo_url text,
  add column if not exists document_name text;

-- Create indexes for the new columns
create index if not exists idx_tenants_logo_url on tenants (logo_url) where logo_url is not null;
create index if not exists idx_tenants_document_name on tenants (document_name) where document_name is not null;

-- Function to update tenant asset columns when assets are modified
create or replace function sync_tenant_asset_columns()
returns trigger
language plpgsql
security definer
as $$
begin
  if TG_OP = 'INSERT' or TG_OP = 'UPDATE' then
    if NEW.asset_type = 'logo' then
      update tenants 
      set logo_url = NEW.storage_path, updated_at = now()
      where id = NEW.tenant_id;
    elsif NEW.asset_type = 'markdown' then
      update tenants 
      set document_name = NEW.file_name, updated_at = now()
      where id = NEW.tenant_id;
    end if;
    return NEW;
  elsif TG_OP = 'DELETE' then
    if OLD.asset_type = 'logo' then
      update tenants 
      set logo_url = null, updated_at = now()
      where id = OLD.tenant_id;
    elsif OLD.asset_type = 'markdown' then
      update tenants 
      set document_name = null, updated_at = now()
      where id = OLD.tenant_id;
    end if;
    return OLD;
  end if;
  return null;
end;
$$;

-- Create trigger to sync asset columns
drop trigger if exists sync_tenant_asset_columns_trigger on tenant_assets;
create trigger sync_tenant_asset_columns_trigger
  after insert or update or delete on tenant_assets
  for each row
  execute function sync_tenant_asset_columns();

-- Backfill existing data
update tenants t
set 
  logo_url = (
    select storage_path 
    from tenant_assets ta 
    where ta.tenant_id = t.id and ta.asset_type = 'logo'
    limit 1
  ),
  document_name = (
    select file_name 
    from tenant_assets ta 
    where ta.tenant_id = t.id and ta.asset_type = 'markdown'
    limit 1
  );

-- Grant execute permission on the function
grant execute on function sync_tenant_asset_columns() to authenticated, service_role;
