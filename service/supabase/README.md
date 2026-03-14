# actBI Database Schema

Single source of truth for all database migrations.

**New developer?** → **[Full local Supabase setup guide (install + run)](../../docs/SUPABASE-LOCAL-SETUP-FOR-NEW-DEVELOPERS.md)** — Docker, Supabase CLI, step-by-step from zero.

## Migrations

| # | Migration | Domain | Purpose |
|---|-----------|--------|---------|
| 00 | user_has_permission_bootstrap | Core | Initial permission helper |
| 01 | conversations_and_messages | BI | Chat schema |
| 02 | add_message_metadata | BI | Message metadata |
| 03 | roles_permissions_rls | RBAC | Full RBAC with RLS |
| 04 | tenants_and_invites | Core | Multi-tenant support |
| 05 | management_overhaul | Core | Management layer |
| 06 | tenant_users_updated_at | Core | Timestamps |
| 07 | enhance_tenants_connections | Core | Data connections |
| 08 | tenant_assets_storage | Assets | Asset storage |
| 09 | add_tenant_asset_columns | Assets | Asset metadata |
| 10 | create_variable_tables | Prompts | Variables (from xms) |
| 11 | create_snippet_tables | Prompts | Snippets (from xms) |
| 12 | create_prompt_tables | Prompts | Prompts (from xms) |

## Usage

### Local Development

```bash
# From repository root
just db-start    # Start local Supabase
just db-reset    # Reset and apply all migrations
just db-stop     # Stop local Supabase

# Or manually from service directory
cd service/supabase
supabase start
supabase db reset
supabase stop
```

### Generate TypeScript Types

```bash
just db-types-ts
```

### Deploy to Staging/Production

```bash
cd service/supabase
supabase link --project-ref <project-ref>
supabase db push
```

## Schema Domains

- **Core**: tenants, tenant_users, user_profiles
- **RBAC**: roles, permissions, role_permissions
- **BI**: conversations, messages, charts, dashboards
- **Prompts**: prompts, snippets, variables
- **Assets**: tenant_assets, tenant_database_connections

## Project 1 / Issue #2 (local Supabase)

- [Local vs Cloud](../../docs/supabase-local-vs-cloud.md) — what runs with `supabase start` vs cloud
- [RLS policies map](../../docs/supabase-rls-policies-map.md) — tables and policies to exercise in dev
- [Decision: Local Docker](../../docs/decisions/002-local-supabase-setup.md) — why we use local Docker
- [Migrations & testing](../../docs/supabase-migrations-testing.md) — migration workflow and RLS vs unit-test split
