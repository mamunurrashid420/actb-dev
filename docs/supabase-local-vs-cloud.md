# Supabase: Local (Docker) vs Cloud — Research

**Purpose:** Document what runs when you use `supabase start` locally vs a hosted Supabase project (cloud). Used for Project 1 (Local Supabase Setup) and GitHub issue #2.

## Local: What spins up with `supabase start`

When you run `supabase start` from `service/supabase/`, the CLI starts these services via Docker:

| Service | Port (default) | Description |
|---------|----------------|-------------|
| **PostgreSQL** | 54322 | Main database (same as cloud). |
| **API (Kong)** | 54321 | REST + PostgREST, Auth, Storage API gateway. |
| **Studio** | 54323 | Web UI for DB, Auth, Storage, SQL. |
| **Auth (GoTrue)** | (via API) | Email/password, JWT, sessions. |
| **Realtime** | (via API) | Realtime subscriptions. |
| **Storage** | (via API) | S3-compatible object storage. |
| **Inbucket** | 54324 | Local email testing (catches auth emails). |
| **Edge Runtime** | 8083 (inspector) | Deno-based Edge Functions. |
| **Analytics** | 54327 | Optional analytics backend (postgres). |

**Config:** `service/supabase/config.toml` (project_id, ports, auth, db seed path, etc.).

## Cloud: Hosted Supabase project

| Capability | Local (Docker) | Cloud |
|------------|----------------|--------|
| Postgres | ✅ Same | ✅ Same |
| Auth (GoTrue) | ✅ | ✅ |
| REST API (PostgREST) | ✅ | ✅ |
| Realtime | ✅ | ✅ |
| Storage | ✅ | ✅ |
| Studio | ✅ (local URLs) | ✅ (project URL) |
| Edge Functions | ✅ (Deno, local) | ✅ (global deploy) |
| Email (SMTP) | Inbucket only (no real send) | Real SMTP / provider |
| Backups / PITR | ❌ | ✅ (plan-dependent) |
| Branching / Preview DBs | ❌ | ✅ (team/plan) |
| Network / scaling | Single machine | Managed infra |

**Summary:** For ActBI dev, local gives the same core surface (DB, Auth, API, Storage, RLS). Differences: no real email delivery (Inbucket), no cloud backups or branching.
