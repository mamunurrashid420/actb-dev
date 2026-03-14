# Main branch: merge only with review (team lead can bypass)

**Goal:** Team lead ছাড়া কেউ main branch-এ review ছাড়া merge করতে পারবে না। Team lead চাইলে review ছাড়াই merge করতে পারবেন।

This is configured in **GitHub repo Settings**, not in code. A repo admin must do this once.

---

## Steps (repo admin / team lead)

1. **Open the repo on GitHub** → **Settings** → **Branches**.
2. Under **Branch protection rules**, click **Add rule** (or edit the existing rule for `main`).
3. Set:
   - **Branch name pattern:** `main`
   - **Require a pull request before merging:** ✅
   - **Required approvals:** `1` (or more if you want)
   - **Allow specified actors to bypass required pull requests:** ✅  
     → Add only the **team lead** (person or team). They can merge without opening a PR or without waiting for approval.
   - (Optional) **Require status checks to pass before merging:** ✅  
     → Add **Code Review** (or the name of your CI workflow) so PRs must pass lint/test before merge.
4. **Create** / **Save** the rule.

Result:

- **Team lead:** Can push to `main` or merge without review (bypass).
- **Everyone else:** Must open a PR and get at least one approval (and pass CI if you enabled status checks) before merging to `main`.

---

## Optional: same for `develop`

Repeat the same rule for branch name pattern `develop` if you want the same policy there.

---

## Reference

- [GitHub: Managing branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/managing-a-branch-protection-rule)
