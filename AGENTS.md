# Repository Instructions

## Read First: Repository Priority Map

This project is split across three GitHub repositories. Treat this section as the authoritative map; do not ask the user to paste these URLs again.

| Priority | Repo | Role | Use it when the user says |
| --- | --- | --- | --- |
| 1 | `Niurougan1/visual-feedback-studio-private` | Private main development repository. This is the source of truth for core implementation, internal plans, strategy, reviews, submissions, experiments, and sensitive product direction. | "新仓库", "私有仓", "主仓", "核心仓", "开发仓", "真实仓", "private repo" |
| 2 | `Niurougan1/visual-feedback-studio` | Public repository. This is the public-safe runnable project/code/docs surface. It can contain normal usable project code and public docs, but must not contain internal methodology, private planning, sensitive roadmap, reviews, submissions, or landing source snapshots. | "旧仓库", "公开仓", "老仓库", "public repo", "GitHub 公开页" |
| 3 | `Niurougan1/visual-feedback-studio-landing` | Dedicated landing-page repository. This is the canonical source for the public marketing/landing page and its copyable setup command. | "落地页", "官网", "landing", "首页", "营销页" |

Operational rules:

- Core product/code/internal docs belong in the private repo first.
- Public-safe code/docs/install command belong in this public repo.
- Landing page UI/copy/CTA command belongs in the landing repo, not this public repo.
- Do not add `docs/plans/`, `docs/strategy/`, `docs/reviews/`, `docs/submissions/`, `docs/landing/`, `vercel-web-upload/`, private roadmap, internal methodology, release submissions, or sensitive review material to this public repo.
- The public one-line install command is:

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | bash
```

If port `3456` is occupied, use:

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | VFS_PORT=3463 bash
```

## Public Sync Push Workflow

Use this workflow when the user asks to update the old/public repo, sync public-safe code/docs, or keep the public install command aligned.

1. Keep this repo public-safe:
   - Allowed: runnable public code, Chrome extension source, local workflow scripts, public docs, examples, agent metadata, public install command.
   - Forbidden: internal methodology, private planning, sensitive roadmap, reviews, submissions, landing source snapshots, private strategy material.

2. Before committing:

```bash
git status --short --branch
git fetch origin
git rebase origin/main
python3 scripts/self_check.py --strict-package
git ls-tree -r --name-only HEAD docs
```

The docs tree must not include `docs/plans/`, `docs/strategy/`, `docs/reviews/`, `docs/submissions/`, or `docs/landing/`.

3. If the public install command or `scripts/install.sh` changes:
   - Confirm `README.md`, `README.en.md`, `docs/install.md`, and `docs/install.en.md` use the same one-line command.
   - Push this public repo before updating the landing repo.
   - After push, test the raw install script with a temporary `HOME`, `VFS_INSTALL_DIR`, `VFS_PROJECT_ROOT`, and non-default `VFS_PORT`, then stop the temporary receiver.

4. Push and verify:

```bash
git push origin main
git ls-remote --heads origin main
```

If push is rejected because the remote is ahead, fetch and rebase, then retry. Do not force push unless the user explicitly asks to restore the public boundary; if required, use `--force-with-lease`.

## Public Boundary

This repository is allowed to contain normal runnable project code, the Chrome extension, local workflow scripts, examples, agent metadata, and public documentation. Keep public docs Chinese-first with English companions where applicable.

This repository is not the source of truth for private planning or the landing page.
