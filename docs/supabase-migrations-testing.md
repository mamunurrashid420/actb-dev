# Supabase: Migrations & Testing Workflow

**Purpose:** How to change schema, add migrations, and how to split tests (RLS vs unit tests). Project 1 deliverable.

## Migration workflow

### Apply migrations locally

```bash
# From repo root
just db-reset

# Or from service/supabase
cd service/supabase
supabase start   # if not already running
supabase db reset
```

`db reset` drops the local DB, reapplies all migrations in order, then runs `seed.sql`.

### Create a new migration after schema change

1. Change the DB (e.g. via Studio or a one-off SQL file).
2. Generate a diff and create a migration file:

   ```bash
   cd service/supabase
   supabase db diff -f describe_your_change
   ```

   This creates a new file under `migrations/` with a timestamp.

3. (Optional) Edit the generated SQL to remove noise or split into logical steps.
4. Apply and verify:

   ```bash
   supabase db reset
   ```

### Create an empty migration (manual SQL)

```bash
cd service/supabase
supabase migration new add_my_feature
# Edit the new file in migrations/
supabase db reset
```

## Testing split: what to mock, what needs real Postgres

### RLS, triggers, SECURITY DEFINER functions

- **Must run against real Postgres.** Row Level Security, triggers, and `SECURITY DEFINER` functions are enforced inside the database. Mocking the Supabase client in app code does **not** exercise these.
- **How to test:** Use local Supabase (`supabase start` + `supabase db reset`) and run integration tests that hit the real DB with real (or seeded) data. Optionally use a test schema or a separate test DB if you add that later.

### Agent / tool logic that does not depend on DB shape

- **Can be unit tested with a mocked client.** For logic that only uses the Supabase client as an dependency (e.g. “call this method, then transform the result”), inject a fake client so tests are fast and don’t need Postgres.
- **Do not** rely on these unit tests to verify RLS or data isolation; use the integration tests above for that.

### Summary

| What you test | Use real Postgres? | How |
|---------------|--------------------|-----|
| RLS policies, tenant isolation | Yes | Local Supabase + integration tests + seed data |
| Triggers, SECURITY DEFINER | Yes | Same |
| Agent/tool logic (no RLS in scope) | No | Unit tests with mocked Supabase client (e.g. dependency injection) |

Seed data in `service/supabase/seed.sql` provides two tenants and RLS-correct rows so that integration tests can assert tenant isolation (e.g. user in Tenant A cannot see Tenant B’s dashboards/conversations).
