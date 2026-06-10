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

## Public Boundary

This repository is allowed to contain normal runnable project code, the Chrome extension, local workflow scripts, examples, agent metadata, and public documentation. Keep public docs Chinese-first with English companions where applicable.

This repository is not the source of truth for private planning or the landing page.
