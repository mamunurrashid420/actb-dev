# Project 2 — Mar 10–14: Docker Image — Detailed Plan

**Goal:** One lean, cloud-agnostic Dagster Docker image (webserver + daemon + pipeline code). No dbt. All config via env vars; same image runs locally and in GCP.  
**Duration:** ~5h  
**Location:** Plan says `apps/pipelines/`; repo has `pipelines/` at root — use **`pipelines/`** (or create `apps/pipelines/` and symlink/copy if client prefers that path).

---

## Before you start

1. **Repo:** Ensure you're on the right branch (e.g. `main` or a feature branch for Project 2).
2. **Local:** Docker Desktop running; you can build and run the image locally.
3. **Dependencies:** Pipelines use `pipelines/pyproject.toml` (dagster, dagster-webserver, dagster-daemon, etc.). Monorepo may use `uv` from repo root — confirm how to install deps for the Docker build (e.g. `uv sync` from root with `--package pipelines` or build from `pipelines/` with its own `pyproject.toml`).

---

## D1-01 — Multi-stage Dockerfile (~1.5h)

**What to do:**

1. **Create** `pipelines/Dockerfile` (or `apps/pipelines/Dockerfile` if you add that folder).
2. **Base image:** `python:3.12-slim`.
3. **Stages:**
   - **Builder:**
     - Install system deps if needed (e.g. for building wheels).
     - Copy repo context needed for pipelines (e.g. `pipelines/`, `lib/` for shared-io, shared-data).
     - Install Python deps: dagster, dagster-webserver, dagster-daemon, and all pipeline deps from `pipelines/pyproject.toml`. Use a single layer (e.g. `uv sync` or `pip install` from a lockfile) so the image is reproducible.
   - **Runtime:**
     - Copy from builder only what’s needed to run: Python env (or venv), `pipelines` package/code, shared libs. No dev tools or build artifacts.
     - Set `DAGSTER_HOME` (e.g. `/opt/dagster_home` or `/app/dagster_home`).
     - Default command: run webserver (or daemon) as specified later; entrypoint can be overridden.
4. **Result:** `docker build -t pipelines:<tag> .` from the build context (repo root or `pipelines/`) produces a runnable image.

**Deliverable:** `pipelines/Dockerfile` (or `apps/pipelines/Dockerfile`).

---

## D1-02 — Env var abstraction (~1h)

**What to do:**

1. **Define** these env vars (document in `pipelines/.env.example` and/or a short doc):
   - `DAGSTER_STORAGE_TYPE` — `gcs` | `s3` | `azure` (for pipeline/run storage; may map to Dagster instance storage or your own abstraction).
   - `DAGSTER_STORAGE_BUCKET` — bucket name (e.g. `actbi-pipeline-artifacts-dev` for GCS).
   - `OLAP_HOST` — OLAP service host (if pipelines need it).
   - `QDRANT_HOST` — Qdrant host (if pipelines need it).
   - `SUPABASE_URL` — Supabase project URL (if pipelines need it).
2. **Use them in code/config:** Where pipeline code or Dagster config reads storage/OLAP/Qdrant/Supabase, read from env (no hardcoded URLs). If nothing in pipelines currently uses OLAP/Qdrant/Supabase, add the vars to `.env.example` and a one-line comment in code so future use is consistent.
3. **Confirm:** Run the same image with two different `.env` sets (e.g. local vs dev) and confirm it boots without code changes (e.g. webserver and daemon start; only config/behavior differs).

**Deliverable:** Env vars documented; code/config use env vars; quick note that image was tested with two env sets.

---

## D1-03 — Dagster storage backend for GCS (~1h)

**What to do:**

1. **Create/update** `dagster.yaml` so Dagster uses GCS for instance storage:
   - **run_storage**
   - **event_log_storage**
   - **schedule_storage**  
   All should point at the same GCS bucket: `actbi-pipeline-artifacts-dev` (or the value of `DAGSTER_STORAGE_BUCKET`).
2. **How:** Dagster supports GCS via config (e.g. `dagster.yaml` with `module: dagster_gcp` or built-in schema). Use env var for bucket name so the same yaml works in different envs (e.g. `env: DAGSTER_STORAGE_BUCKET`).
3. **Where:** Either:
   - Ship `dagster.yaml` in the image (e.g. under `DAGSTER_HOME`), or
   - Mount it at runtime. Prefer generating or copying it in the image from a template so the image stays self-contained; bucket name from env.
4. **Credentials:** In GCP, use workload identity or service account key; locally, use a key file or ADC. Document in `.env.example` (e.g. `GOOGLE_APPLICATION_CREDENTIALS` or GCP project ID).

**Deliverable:** `dagster.yaml` (or template) for GCS run/event_log/schedule storage; bucket from env; doc or comments for credentials.

---

## D1-04 — Validate image locally (~1.5h)

**What to do:**

1. **Build:**  
   `docker build -t pipelines:latest -f pipelines/Dockerfile .`  
   (or from `pipelines/` if Dockerfile is there and context is correct.)
2. **Create** `.env.local` (git-ignored) with dev values:  
   `DAGSTER_STORAGE_TYPE`, `DAGSTER_STORAGE_BUCKET`, `OLAP_HOST`, `QDRANT_HOST`, `SUPABASE_URL`, and any GCS credentials (e.g. `GOOGLE_APPLICATION_CREDENTIALS`).
3. **Run webserver:**  
   `docker run --env-file .env.local -p 3000:3000 pipelines:latest`  
   (or whatever command starts the Dagster webserver on port 3000). Confirm the webserver starts and is reachable at `http://localhost:3000`.
4. **Run daemon:**  
   In another container (or same with a different command), run the Dagster daemon with the same env. Confirm it starts without errors (no need to run a full pipeline yet).
5. **Optional:** Run with a second env file (e.g. different bucket or local storage) and confirm the image still boots.

**Deliverable:** Short validation note: build command, run commands, and that webserver (port 3000) and daemon start successfully.

---

## Image tagging (per client)

- Use **`<service>:<git-sha>`** for traceability (e.g. `pipelines:abc1234`).
- Use **`<service>:latest`** for local/dev convenience.
- Align with the FastAPI image pattern in `deploy-api.yml` if that file exists (e.g. same tag format).

---

## Checklist (what to do, in order)

| Step | Task | Est. | Done |
|------|------|------|------|
| 1 | Create multi-stage Dockerfile in `pipelines/` (builder + runtime, python:3.12-slim) | 1.5h | |
| 2 | Add env var abstraction (DAGSTER_STORAGE_*, OLAP_HOST, QDRANT_HOST, SUPABASE_URL); document; use in code/config | 1h | |
| 3 | Add dagster.yaml for GCS (run/event_log/schedule storage → actbi-pipeline-artifacts-dev or env) | 1h | |
| 4 | Build image, run with .env.local; confirm webserver on 3000 and daemon starts | 1.5h | |
| 5 | Tag image as `<service>:<git-sha>` and `latest` | — | |

---

## Files you will add or touch

- `pipelines/Dockerfile` (new)
- `pipelines/dagster.yaml` or `pipelines/dagster.yaml.template` (new or replace existing in .dagster-dev)
- `pipelines/.env.example` (update with new vars)
- Optional: `pipelines/README.md` or `docs/pipelines-docker.md` (build/run and env vars)
- `.env.local` (local only, git-ignored) for validation

---

## Notes

- **No dbt** in this image (per goal).
- **Monorepo:** Docker build context may need to include `lib/` (shared-io, shared-data) if pipelines depend on them; ensure `COPY` and install steps in the Dockerfile match your repo layout.
- **GCS bucket:** If `actbi-pipeline-artifacts-dev` does not exist yet, create it in GCP or document that it must exist before using GCS storage.

This plan is the detailed “what to do” for Mar 10–14; no new files are generated beyond what’s listed above.
