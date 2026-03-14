# Local Supabase Setup — Full Guide for New Developers

This guide gets you from zero to a running local Supabase with a seeded database. Follow the steps in order.

---

## What you will have when done

- **Local Supabase** running in Docker (Postgres, Auth, API, Storage, Studio).
- **Seeded database** with 2 tenants (Acme, Beta Corp), test users, dashboards, and conversations.
- **Supabase Studio** in your browser to view and query data.

---

## Step 1 — Install Docker Desktop

Supabase runs in Docker. You need Docker Desktop installed and running.

### Windows

1. Download: **[Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)**  
   - Use the stable version (e.g. "Docker Desktop Installer.exe").
2. Run the installer. If asked, enable **WSL 2** and follow the prompts.
3. Restart your PC if the installer asks.
4. Open **Docker Desktop** from the Start menu. Wait until it shows **Docker Desktop is running** (green).
5. Check in PowerShell:
   ```powershell
   docker --version
   ```
   You should see something like `Docker version 24.x.x`.

### macOS

1. Download: **[Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)** (Apple Silicon or Intel as needed).
2. Open the downloaded `.dmg`, drag Docker to Applications, then open Docker.
3. Wait until the menu bar shows Docker is running.
4. Check in Terminal:
   ```bash
   docker --version
   ```

### Linux

Install Docker Engine for your distro:  
**[Install Docker Engine](https://docs.docker.com/engine/install/)**  
Then start the service and ensure your user can run `docker` (e.g. add to `docker` group).

---

## Step 2 — Install Supabase CLI

The Supabase CLI starts and manages the local Supabase stack. **Do not** use `npm install -g supabase` — it is no longer supported.

### Windows (PowerShell)

1. **Install Scoop** (if you don’t have it). In PowerShell (run as normal user, not Admin):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
   Type `Y` and Enter if prompted.

   Then:
   ```powershell
   irm get.scoop.sh | iex
   ```

2. **Install Supabase CLI:**
   ```powershell
   scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
   scoop install supabase
   ```

3. **Verify:**
   ```powershell
   supabase --version
   ```
   You should see a version number (e.g. `2.75.0`).

### macOS / Linux

Use **Homebrew**:

```bash
brew install supabase/tap/supabase
supabase --version
```

---

## Step 3 — Get the ActBI repository

If you don’t have the repo yet:

```bash
git clone https://github.com/actbi-ai/actbi.git
cd actbi
```

(Use SSH or your org’s URL if required.)

All Supabase config and migrations live under **`service/supabase/`**.

---

## Step 4 — Start local Supabase

1. **Ensure Docker Desktop is running** (Step 1).  
   On Windows/macOS you should see the Docker icon in the system tray/menu bar.

2. **Open a terminal** (PowerShell on Windows, Terminal on Mac/Linux).

3. **Go to the Supabase folder:**
   ```bash
   cd service/supabase
   ```
   (From the repo root, so full path is `actbi/service/supabase`.)

4. **Start Supabase:**
   ```bash
   supabase start
   ```

   The first time this runs, it will download Docker images (a few minutes). Later runs are faster.

5. **When it finishes**, the terminal will show something like:

   ```
   Started supabase local development setup.

           API URL: http://127.0.0.1:54321
       GraphQL URL: http://127.0.0.1:54321/graphql/v1
            DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
        Studio URL: http://127.0.0.1:54323
     ...
   ```

   **Note these URLs** (especially Studio URL for the next step).

---

## Step 5 — Apply migrations and seed data

With Supabase still running (from Step 4), in the **same** terminal (still in `service/supabase`):

```bash
supabase db reset
```

This will:

- Reset the local database.
- Run all migrations in `service/supabase/migrations/`.
- Run the seed script `service/supabase/seed.sql` (2 tenants, users, dashboards, conversations).

When it finishes without errors, your local database is **seeded and ready**.

---

## Step 6 — Verify in Supabase Studio

1. Open your browser and go to: **http://127.0.0.1:54323**  
   (Use the Studio URL from Step 4 if different.)

2. You should see **Supabase Studio** (local).

3. In the left sidebar, open **Table Editor**.

4. Check:
   - **`tenants`** — 2 rows (e.g. Acme, Beta Corp).
   - **`dashboards`** — 2 rows.
   - **`conversations`** — 2 rows.

If you see this data, your local Supabase setup is working.

---

## Daily workflow (after first-time setup)

Once Docker and Supabase CLI are installed:

```bash
# From repo root, or from service/supabase
cd service/supabase

# Start Supabase (Docker must be running)
supabase start

# If you pulled new migrations or changed seed, reset DB
supabase db reset

# When you're done working
supabase stop
```

Optional: from repo root you can use **just** if installed:

```bash
just db-start    # same as: cd service/supabase && supabase start
just db-reset    # same as: cd service/supabase && supabase db reset
just db-stop     # same as: cd service/supabase && supabase stop
```

---

## Connecting your app to local Supabase

Use the URLs printed when you run `supabase start`:

- **API URL:** `http://127.0.0.1:54321`  
- **Anon key:** Shown in the `supabase start` output (or in Studio: Project Settings → API).

Put these in your app’s `.env` (or env config), for example:

```env
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=<paste the anon key from supabase start output>
```

Restart your app so it uses the local Supabase.

---

## Seed users (for login testing)

Seed creates these users (password for all: **Passw0rd!**):

| Email               | Role        |
|---------------------|------------|
| root@actbi.ai       | Root Admin |
| superadmin@actbi.ai | Super Admin |
| admin@actbi.ai      | Admin      |
| creator@actbi.ai    | Creator    |
| viewer@actbi.ai     | Viewer     |

Use these in your app’s login or in Studio (Auth) to test.

---

## Troubleshooting

### "Docker is not running"

- Start **Docker Desktop** and wait until it is fully up (green / “running”).
- Then run `supabase start` again.

### "supabase: command not found" (or not recognized)

- **Windows:** Ensure you installed Supabase via Scoop (Step 2). Close and reopen PowerShell after install.
- **Mac/Linux:** Ensure `brew` added Supabase to PATH; try opening a new terminal.

### "port is already allocated" or "address already in use"

- Another process is using the same port (e.g. 54321, 54322, 54323).
- Stop other Supabase or Postgres instances: `supabase stop` from `service/supabase`, or stop other containers using those ports.
- You can change ports in `service/supabase/config.toml` if needed (advanced).

### "supabase db reset" fails or seed errors

- Ensure you are in `service/supabase` when running `supabase db reset`.
- Check the error message; it often points to a specific migration or seed line. Share the full error if you need help.
- Ensure no other Postgres is conflicting on port 54322.

### Studio page does not load (http://127.0.0.1:54323)

- Confirm Supabase is still running: run `supabase status` from `service/supabase`.
- If status is OK, try a different browser or clear cache. Ensure you use `127.0.0.1`, not `localhost`, if your system treats them differently.

---

## Summary checklist (new developer)

- [ ] Docker Desktop installed and **running**
- [ ] Supabase CLI installed (`supabase --version` works)
- [ ] Repo cloned; in terminal: `cd actbi/service/supabase`
- [ ] `supabase start` — finishes with API and Studio URLs
- [ ] `supabase db reset` — finishes without errors
- [ ] Browser: http://127.0.0.1:54323 → Table Editor → `tenants` has 2 rows

When all are done, you are ready to work with local Supabase.

---

## More documentation

- **What runs locally vs cloud:** [supabase-local-vs-cloud.md](supabase-local-vs-cloud.md)
- **RLS and tables:** [supabase-rls-policies-map.md](supabase-rls-policies-map.md)
- **Migrations and testing:** [supabase-migrations-testing.md](supabase-migrations-testing.md)
- **Database schema and usage:** [service/supabase/README.md](../service/supabase/README.md)
