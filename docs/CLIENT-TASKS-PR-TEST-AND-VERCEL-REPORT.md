# Client tasks: PR test check + Vercel deploy only when web/bi changes — How-to report

No code changes in this doc; only how to do each task.

---

## Task 1: Add “just test” check when someone creates a new PR

### Current state
- There is already a workflow: **`.github/workflows/code-review.yml`**
- It runs on: `pull_request` and `push` to `main` and `develop`
- It currently: checks out, sets up pnpm/Node, runs `pnpm install`, **Lint**, and **Test**
- The “Test” step is: `pnpm -r run test --if-present` → only **JavaScript** tests (web packages that have a `test` script). **Python / `just test` is not run.**

### What “just test” does (from repo)
- `just test` = `test-python` + `test-js`
- **test-python:** for each workspace member with a `tests/` folder, runs `uv run pytest`
- **test-js:** `pnpm --filter './web/*' test`

So today, PRs only run JS tests. The client wants the **full** test suite (Python + JS), i.e. what `just test` does.

### How to do it

1. **In the same workflow (e.g. `.github/workflows/code-review.yml`), add a step that runs `just test` (or equivalent).**
2. **Requirements for running `just test` in CI:**
   - **just:** install `just` (e.g. `curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin` or use a GitHub Action like `extractions/setup-just`).
   - **Python + uv:** install Python 3.12 and `uv` so that `just test-python` can run (e.g. `actions/setup-python` + `astral-sh/setup-uv` or repo’s documented way).
   - **Existing step:** Node/pnpm are already there; `just test-js` (or `pnpm -r run test`) can keep using that.
3. **Options:**
   - **Option A (recommended):** Add one step that runs `just test`, after installing `just`, Python 3.12, and `uv`, and ensure the job has both Node (for pnpm) and Python/uv. So a single “Test” step becomes “run `just test`” (and remove or keep the current `pnpm -r run test`; if `just test` covers it, you can remove the duplicate).
   - **Option B:** Keep the current “Test” step as-is and add a **second** step “Test (Python)” that sets up Python/uv and runs `just test-python` (so “just test” is effectively split into two steps).
4. **Branch protection:** In GitHub repo **Settings → Branches → Branch protection** for `main` (and optionally `develop`), under “Require status checks”, add the **job name** of this workflow (e.g. “review” or “Code Review”) so that PRs must pass this check (including `just test`) before merge.

### Summary (Task 1)
- **Where:** `.github/workflows/code-review.yml`
- **What:** Add setup for `just` + Python 3.12 + `uv`, then run `just test` (or run `just test-python` and keep existing JS test step).
- **Result:** Every new PR runs the full test suite (Python + JS); failing tests fail the PR.

---

## Task 2: Fix Vercel deploying even when web/bi code is not changed

### What’s going on
- Vercel is connected to the repo and builds on (e.g.) every push to `main` or on every PR.
- So any push (e.g. changes only in `pipelines/`, `service/`, or docs) still triggers a build/deploy for the app (e.g. web/bi). The client wants: **deploy only when there are changes under `web/bi`** (or the path that actually contains the Vercel app).

### How to do it: “Ignored Build Step”

Vercel has an **“Ignored Build Step”** (or “Build Command” / “Override” that can skip the build):

- If the command **exits with 0** → Vercel **skips** the build (no deploy).
- If the command **exits with non-zero** (e.g. 1) → Vercel **runs** the build and deploys.

So we want: **skip when nothing under `web/bi` changed; build when something under `web/bi` changed.**

### Command to use

In Vercel **Project Settings → General → Build & Development Settings** (or “Ignored Build Step” / “Override” section), set the **Ignored Build Step** command to:

```bash
git diff HEAD^ HEAD --quiet -- web/bi
```

- **If there are no changes in `web/bi`:** `git diff ... --quiet` exits **0** → Vercel **skips** the build.
- **If there are changes in `web/bi`:** `git diff ... --quiet` exits **1** → Vercel **runs** the build.

Path note: Vercel usually runs from the **repo root** (or from the “Root Directory” you set). If the repo root is the project root, `web/bi` is correct. If you set “Root Directory” to e.g. `web/bi`, then this command would need to run from repo root (some setups allow a script at root); otherwise use a path relative to that root (e.g. `.` if the root is already `web/bi`).

### If the app is in a different path
Replace `web/bi` with the actual path that contains the app Vercel deploys (e.g. `web/bi` or `apps/bi`). The logic stays the same: `git diff HEAD^ HEAD --quiet -- <that-path>`.

### Summary (Task 2)
- **Where:** Vercel dashboard → Project → Settings → **Ignored Build Step** (or equivalent).
- **What:** Set the command to: `git diff HEAD^ HEAD --quiet -- web/bi` (or the correct app path).
- **Result:** Vercel only deploys when there are changes in `web/bi`; other changes no longer trigger a deploy.

---

## Quick reference

| Task | Where | Action |
|------|--------|--------|
| 1. PR “just test” check | `.github/workflows/code-review.yml` | Add just + Python/uv, run `just test` (or `just test-python` + keep JS test). Optionally require this status check on the branch protection rule. |
| 2. Vercel only when web/bi changes | Vercel Project Settings → Ignored Build Step | Set command: `git diff HEAD^ HEAD --quiet -- web/bi` (or the real app path). |

No file changes were made in the repo for this report; this document only describes how to implement the two tasks.
