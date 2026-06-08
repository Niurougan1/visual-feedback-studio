---
name: visual-feedback-studio
description: Use this skill when the user wants browser-based visual review for a local page or frontend app, wants to collect page feedback, or asks an agent to preview, apply, or verify Visual Feedback Studio feedback. This public skill describes the local-first browser feedback workflow and the public extension/scripts included in this repository.
---

# Visual Feedback Studio

Visual Feedback Studio is a local-first browser visual review workflow. It captures reviewer feedback from a running page and saves structured project-local feedback that an AI coding agent can inspect before making source edits.

## Public Workflow

1. Run setup for the project you want to review.
2. Load the Chrome extension from `chrome-extension/`.
3. Open a page you are allowed to review.
4. Capture text, style, or annotation feedback.
5. Save feedback to the project-local feedback file.
6. Use `scripts/vfs.py plan` to preview what can be safely resolved.
7. Apply only source-proven edits and verify the result.

## Commands

```bash
python3 scripts/setup.py /path/to/project --channel beta
python3 scripts/vfs.py plan /path/to/project
python3 scripts/vfs.py apply /path/to/project --verify
python3 scripts/vfs.py verify /path/to/project
```

## Safety Rules

- Use the tool only on pages and projects where review capture is permitted.
- Treat ambiguous source matches as manual review work.
- Keep runtime feedback files out of Git.
- Do not paste credentials, customer data, or sensitive private context into public issues.

## Public Boundary

This public repository includes the browser extension, local workflow scripts, public documentation, and a basic example. Internal planning, private release operations, commercial roadmap, submission drafts, and sensitive review materials are maintained separately.
