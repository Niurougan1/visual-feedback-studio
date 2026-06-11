# Repository Instructions

## Read First: Public Repository Boundary

This is the public-safe runnable project surface for Visual Feedback Studio. Keep all instructions, docs, scripts, examples, and metadata suitable for public readers.

Operational rules:

- Public-safe code/docs/install command belong in this public repo.
- Do not add internal planning, private roadmap, release submissions, design strategy, sensitive reviews, marketing source snapshots, or non-public repository references.
- Do not add `docs/plans/`, `docs/strategy/`, `docs/reviews/`, `docs/submissions/`, `docs/landing/`, or `vercel-web-upload/`.
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
   - After push, test the raw install script with a temporary `HOME`, `VFS_INSTALL_DIR`, `VFS_PROJECT_ROOT`, and non-default `VFS_PORT`, then stop the temporary receiver.

4. Push and verify:

```bash
git push origin main
git ls-remote --heads origin main
```

If push is rejected because the remote is ahead, fetch and rebase, then retry. Do not force push unless the user explicitly asks to restore the public boundary; if required, use `--force-with-lease`.

## Public Boundary

This repository is allowed to contain normal runnable project code, the Chrome extension, local workflow scripts, examples, agent metadata, and public documentation. Keep public docs Chinese-first with English companions where applicable.

This repository is not the source of truth for private planning or marketing page source.
