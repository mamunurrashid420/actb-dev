-- Storage bucket and policies for tenant assets.
-- Idempotent: safe to re-run.

insert into storage.buckets (id, name, public)
values ('tenant-assets', 'tenant-assets', false)
on conflict (id) do update
set public = excluded.public;

drop policy if exists tenant_assets_storage_read on storage.objects;
drop policy if exists tenant_assets_storage_manage on storage.objects;

create policy tenant_assets_storage_read on storage.objects
  for select
  using (
    bucket_id = 'tenant-assets'
    and (
      user_has_permission(auth.uid(), 'tenant_assets.read')
      or user_has_permission(auth.uid(), 'tenants.manage')
      or exists (
        select 1 from tenant_users tu
        where tu.user_id = auth.uid()
          and tu.status = 'active'
          and tu.tenant_id::text = split_part(name, '/', 2)
      )
    )
  );

create policy tenant_assets_storage_manage on storage.objects
  for all
  using (
    bucket_id = 'tenant-assets'
    and (
      user_has_permission(auth.uid(), 'tenant_assets.manage')
      or user_has_permission(auth.uid(), 'tenants.manage')
      or exists (
        select 1 from tenant_users tu
        where tu.user_id = auth.uid()
          and tu.status = 'active'
          and tu.role = 'tenant_admin'
          and tu.tenant_id::text = split_part(name, '/', 2)
      )
    )
  )
  with check (
    bucket_id = 'tenant-assets'
    and (
      user_has_permission(auth.uid(), 'tenant_assets.manage')
      or user_has_permission(auth.uid(), 'tenants.manage')
      or exists (
        select 1 from tenant_users tu
        where tu.user_id = auth.uid()
          and tu.status = 'active'
          and tu.role = 'tenant_admin'
          and tu.tenant_id::text = split_part(name, '/', 2)
      )
    )
  );
