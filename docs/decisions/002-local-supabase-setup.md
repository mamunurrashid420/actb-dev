# Decision 002: Local Supabase — Docker vs Cloud Dev Project

**Context:** Resolve GitHub issue #2. Choose how ActBI developers run Supabase for local dev: local Docker stack vs a shared cloud dev project.

## Option A: Local Docker (`supabase start`)

**Pros:**
- Offline-capable; no dependency on cloud availability.
- Each developer has an isolated DB; no shared state or accidental wipes.
- Fast iteration: `supabase db reset` applies migrations + seed in seconds.
- Matches production topology (Postgres, Auth, Storage, Realtime) on one machine.
- No cloud cost for dev; only Docker resources.

**Cons:**
- Requires Docker (and ~2–4 GB RAM) on each machine.
- Local only; no “shared” dev DB for pairing or demos unless exposed manually.

## Option B: Shared Cloud Dev Project

**Pros:**
- No Docker required; only connection details and env vars.
- Single shared DB for cross-dev pairing or shared demos.
- Closer to production network/auth path.

**Cons:**
- Shared state: one developer’s reset or migration affects everyone.
- Requires network; no offline dev.
- Possible cost and need to manage project lifecycle and credentials.

## Recommendation

**Use Option A: Local Docker.**

- ActBI already has `service/supabase/` with `config.toml`, migrations, and seed. Local workflow is one command: `just db-start` / `supabase start`, then `just db-reset` / `supabase db reset`.
- Isolated DBs avoid flaky tests and accidental data loss from shared state.
- No cloud cost or credential sharing; onboarding is “install Docker + Supabase CLI, then start.”

## Decision

We will use **local Docker** for Supabase development. Implementation:

- **Config:** `service/supabase/config.toml` (already present; seed path `./seed.sql`).
- **Workflow:** From repo root `just db-start`, `just db-reset`, `just db-stop`; or from `service/supabase`: `supabase start`, `supabase db reset`, `supabase stop`.
- **Seed:** Two tenants with RLS-correct rows (see `service/supabase/seed.sql` and `docs/supabase-rls-policies-map.md`).
- **Migrations:** `supabase db diff`, `supabase migration new`, `supabase db reset` — see `docs/supabase-migrations-testing.md`.

This decision closes GitHub issue #2.
