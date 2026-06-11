# Repository Instructions

## Repository Scope

This repository is the public-safe runnable project surface for Visual Feedback Studio. Keep all instructions, docs, scripts, examples, and metadata suitable for public readers.

Operational rules:

- Public-safe code, docs, examples, extension source, workflow scripts, and install guidance belong here.
- Do not add unpublished planning, roadmap material, release submissions, design strategy, sensitive reviews, marketing source snapshots, or non-public references.
- Do not add `docs/plans/`, `docs/strategy/`, `docs/reviews/`, `docs/submissions/`, `docs/landing/`, or `vercel-web-upload/`.

## Before Committing

- Run `python3 scripts/self_check.py --strict-package` for code, docs, package, install, or extension changes.
- Keep public install command changes consistent across README, SKILL, docs, and scripts when those files are touched.
- Confirm the docs tree does not include forbidden unpublished or marketing-source directories.

## Public Boundary

Allowed content includes runnable public code, the Chrome extension, local workflow scripts, examples, agent metadata, and public documentation. Keep public docs Chinese-first with English companions where applicable.
