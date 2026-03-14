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
   - **Require status checks to pass before merging:** ✅  
     → **Search for status check:** টাইপ করুন `review` অথবা `Code Review`। ড্রপডাউন থেকে **review** সিলেক্ট করুন (এটাই আমাদের workflow-এর job নাম; এটা পাস না হলে PR merge ব্লক থাকবে)।  
     → একইভাবে develop এর জন্যও rule এ **review** রিকোয়ার করুন।
4. **Create** / **Save** the rule.

Result:

- **Team lead:** Can push to `main` or merge without review (bypass).
- **Everyone else:** Must open a PR and get at least one approval (and pass CI if you enabled status checks) before merging to `main`.

---

## Optional: same for `develop`

Repeat the same rule for branch name pattern `develop` if you want the same policy there.

---

## টেস্ট ফেইল করলে PR merge বন্ধ করতে (step-by-step)

**লক্ষ্য:** `just test` (অথবা Lint) ফেইল করলে PR merge করা যাবে না।

1. **GitHub এ repo খুলুন** → উপরে **Settings**।
2. বাম পাশে **Branches** ক্লিক করুন → **Branch protection rules**।
3. **Add rule** চাপুন (অথবা `main` / `develop` এর existing rule **Edit** করুন)।
4. **Branch name pattern:** `main` লিখুন (অথবা `develop` আলাদা rule এ)।
5. নিচে স্ক্রল করে **Require status checks to pass before merging** চেকবক্স টিক দিন।
6. **Search for status checks** বক্সে ক্লিক করে লিখুন: `review`।  
   - লিস্টে **review** (অথবা "Code Review / review") সিলেক্ট করুন।  
   - এটাই আমাদের workflow-এর job; এটা পাস না হলে merge বাটন নিষ্ক্রিয় থাকবে।
7. **Create** বা **Save** চাপুন।

একইভাবে `develop` এর জন্যও একটা rule এ **review** রিকোয়ার করলে develop-এ merge-ও টেস্ট পাসের পরই হবে।

---

## Reference

- [GitHub: Managing branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/managing-a-branch-protection-rule)
