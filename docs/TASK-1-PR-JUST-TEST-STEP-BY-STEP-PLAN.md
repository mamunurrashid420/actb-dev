# Task 1: Add “just test” on PR — Step-by-step plan

Complete this in order. Only one file to edit: `.github/workflows/code-review.yml`.

---

## Step 1 — Install “just” in CI

After **Checkout** and before **Setup pnpm**, add a step that installs the `just` command so the runner can run `just test`.

Add these lines (after the Checkout step, before Setup pnpm):

```yaml
      - name: Install just
        run: |
          curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
```

---

## Step 2 — Setup Python 3.12

Add a step to set up Python 3.12 (required for `just test-python` and `uv`):

```yaml
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
```

Put it after **Install just**, before **Setup pnpm** (or right after Install just).

---

## Step 3 — Install uv

Add a step to install `uv` (used by the justfile to run pytest in each workspace member):

```yaml
      - name: Install uv
        run: pip install uv
```

Or use the action (if you prefer):

```yaml
      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
```

Put it after **Setup Python**.

---

## Step 4 — Sync Python workspace (uv)

So that `just test-python` can run `uv run pytest` in each member, install the workspace once at repo root:

```yaml
      - name: Sync Python workspace
        run: uv sync
```

Put it after **Install uv** and after **Install** (pnpm install). So order can be: Checkout → just → Python → uv → pnpm install → **Sync Python workspace** (uv sync) → Lint → Test.

---

## Step 5 — Run “just test” instead of only pnpm test

Replace the current **Test** step:

```yaml
      # Test – runs on every PR and push to main/develop
      - name: Test
        run: pnpm -r run test --if-present
```

with:

```yaml
      # Test – full suite (Python + JS) via just
      - name: Test
        run: just test
```

So the runner will execute both `just test-python` and `just test-js` (as defined in the justfile).

---

## Step 6 — (Optional) Require this check on merge

So that PRs cannot merge until “just test” passes:

1. Go to **GitHub** → repo → **Settings** → **Branches**.
2. Edit the branch protection rule for **main** (and **develop** if you use it).
3. Under **Require status checks to pass before merging**, add the status check named **Code Review** (or the job name, e.g. **review**).
4. Save.

Then only PRs that pass the Code Review workflow (including `just test`) can be merged.

---

## Order of steps in the file (summary)

Suggested order in `code-review.yml`:

1. Checkout  
2. Install just  
3. Setup Python 3.12  
4. Install uv  
5. Setup pnpm  
6. Setup Node  
7. Install (pnpm install)  
8. Sync Python workspace (uv sync)  
9. Lint  
10. Test (`just test`)

---

## One block you can paste (steps 1–5 + updated Test)

Below is a single block that you can use to replace the **steps** section of the existing job (keep `name`, `on`, `jobs`, `review`, `runs-on` as they are). It adds just, Python, uv, uv sync, and changes Test to `just test`.

```yaml
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install just
        run: |
          curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        run: pip install uv

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"

      - name: Install
        run: pnpm install --frozen-lockfile

      - name: Sync Python workspace
        run: uv sync

      - name: Lint
        run: pnpm -r run lint --if-present

      - name: Test
        run: just test
```

---

## Done

After you save the workflow file and push, every new PR (and push to main/develop) will run **just test** (Python + JS). If any step fails, the PR check fails.
