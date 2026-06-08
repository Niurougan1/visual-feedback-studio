<p align="center">
  <img src="./Logo.svg" width="88" alt="Visual Feedback Studio logo" />
</p>

<h1 align="center">Visual Feedback Studio</h1>

<p align="center">
  <strong>Browser feedback in. Source-ready edits out.</strong>
</p>

<p align="center">
  <code>local-first</code> · <code>Chrome MV3</code> · <code>Codex / Claude</code> · <code>visual review workflow</code>
</p>

<p align="center">
  <a href="./README.zh-CN.md">简体中文</a>
</p>

---

Visual Feedback Studio is a local-first browser visual review workflow. It lets a reviewer mark copy, style, and annotation feedback directly on a running page, then saves structured feedback that an AI-assisted development workflow can preview, apply, and verify against source files.

This public repository contains the browser extension, local workflow scripts, agent integration metadata, a basic example, and public documentation.

Internal planning, private release operations, commercial roadmap, submission drafts, design strategy, and sensitive review materials are maintained separately.

## Why

Visual review gets slow when feedback has to travel through screenshots, chat threads, issue prose, and memory. Visual Feedback Studio shortens that loop:

```text
Open page -> mark feedback -> save structured JSON -> preview source edits -> apply -> verify
```

The workflow is intentionally conservative: text edits are automated only when the source target can be proven; style edits are treated as structured source-aware suggestions unless the target can be safely resolved.

## Repository Contents

| Path | Purpose |
| --- | --- |
| `chrome-extension/` | Chrome Manifest V3 extension source. |
| `scripts/` | Local receiver, planning, apply, verify, packaging, and setup helpers. |
| `agents/` | Agent integration metadata for Codex and Claude-style workflows. |
| `docs/` | Public install, privacy, permissions, architecture, roadmap, and security notes. |
| `examples/basic-static-preview/` | Small static page for trying the browser feedback loop. |

## Quick Start

1. Run setup for a local project:

```bash
python3 scripts/setup.py /path/to/your-project --channel beta
```

2. Load the Chrome extension:

```text
chrome://extensions/ -> Developer mode -> Load unpacked
```

Choose this repository's `chrome-extension/` directory.

3. Open a page you are allowed to review, activate Visual Feedback Studio, capture feedback, and save.

4. Preview what the workflow can safely resolve:

```bash
python3 scripts/vfs.py plan /path/to/your-project
```

See [Install / Access](./docs/install.md) for more context.

## Privacy Model

The default workflow is local-first. Feedback, preview state, and verification artifacts are intended to stay in the reviewed project unless you explicitly configure a hosted or team workflow.

See [Privacy](./docs/privacy.md) and [Permissions](./docs/permissions.md).

## Status

This repository is a public project distribution. Some planning documents, private release processes, advanced internal experiments, and commercial materials are intentionally not published here.

## License

Copyright © 2026 Visual Feedback Studio. All rights reserved.

No open-source license is granted unless a future release adds an explicit license file.
