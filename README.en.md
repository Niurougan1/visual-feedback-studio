<p align="center">
  <img src="./Logo.svg" width="88" alt="Visual Feedback Studio logo" />
</p>

<h1 align="center">Visual Feedback Studio</h1>

<p align="center">
  <strong>Capture visual feedback in the browser and bring it back to the source workflow.</strong>
</p>

<p align="center">
  <code>local-first</code> · <code>Chrome MV3</code> · <code>Codex / Claude</code> · <code>visual review</code>
</p>

<p align="center">
  <a href="./README.md">简体中文</a>
</p>

---

## Quick Start

Run setup for the project you want to review:

```bash
python3 scripts/setup.py /path/to/your-project --channel beta
```

Load the Chrome extension:

```text
chrome://extensions/ -> Developer mode -> Load unpacked
```

Choose this repository's `chrome-extension/` directory. Then open a page you are allowed to review, activate Visual Feedback Studio, capture feedback, and save.

Preview what can be safely resolved:

```bash
python3 scripts/vfs.py plan /path/to/your-project
```

See [Install / Access](./docs/install.en.md) for more.

To try the loop first, open `examples/basic-static-preview/index.html` directly or serve that directory with any static file server. For local `file://` pages, enable file URL access in the Chrome extension details page.

## What It Is

Visual Feedback Studio is a local-first workflow for frontend product review. It lets reviewers edit copy, tune styles, and leave annotations directly on a running page, then saves structured feedback that an AI-assisted development workflow can preview, apply, and verify against source files.

The goal is not to be another screenshot annotation tool. The goal is to shorten the translation step between "this feels off" and "this is the file, component, copy, or style that needs attention."

```text
Open page -> mark feedback -> save structured JSON -> preview source edits -> apply -> verify
```

## Use Cases

- Product, design, and engineering review frontend pages together.
- Reviewers want to express changes on the page instead of writing long screenshot notes.
- Codex, Claude, or another AI coding agent is part of the development loop.
- Feedback should stay local to the project by default.
- Source edits should be previewed and verified instead of guessed.

## Core Capabilities

| Capability | Description |
| --- | --- |
| In-page feedback | Capture copy, style, and annotation feedback on a real page. |
| Local structured state | Save feedback into project-local files for agent workflows. |
| Source preview | Check which feedback can be safely mapped to source before editing. |
| Conservative apply | Automate only when the target can be proven; leave ambiguous items for review. |
| Verification loop | Verify applied feedback through source and browser-visible evidence. |
| Agent handoff | Provide Codex / Claude-style workflow metadata. |

## Repository Contents

| Path | Purpose |
| --- | --- |
| `chrome-extension/` | Chrome Manifest V3 extension source. |
| `scripts/` | Local receiver, planning, apply, verify, packaging, and setup helpers. |
| `agents/` | Agent metadata for Codex / Claude-style workflows. |
| `docs/` | Public install, privacy, permissions, architecture, roadmap, and security notes. |
| `examples/basic-static-preview/` | Small static page for trying the feedback loop. |

## Design Principles

- **Local-first**: feedback, preview state, and verification artifacts stay in the reviewed project by default.
- **Preview before editing**: browser feedback is not treated as a source edit until it is planned.
- **No guessing**: ambiguous targets are left for review instead of being applied silently.
- **Project-aware**: style feedback should respect the current component, styling, and token system.
- **Agent-friendly**: AI coding agents receive structured feedback closer to source semantics than screenshots alone.

## Future Direction

The public version will continue improving:

- First-run setup and diagnostics.
- Clearer preview / apply / verify reports.
- More examples for static pages and common frontend frameworks.
- More stable feedback schemas for different agents and tools.
- Better design-system adaptation for components, variables, and tokens.
- Optional team and hosted workflows with explicit authorization and configuration.

The baseline remains the same: do not upload source or review feedback by default, and do not pretend uncertain feedback is a certain source edit.

## Public Boundary

This public repository includes the browser extension, local workflow scripts, agent metadata, a basic example, and public documentation. Internal planning, private release operations, commercial roadmap, submission drafts, design strategy, and sensitive review materials are maintained separately.

## Docs

- [Install / Access](./docs/install.en.md)
- [Privacy](./docs/privacy.en.md)
- [Permissions](./docs/permissions.en.md)
- [Architecture](./docs/architecture.en.md)
- [Public Roadmap](./docs/public-roadmap.en.md)
- [Security](./docs/security.en.md)
- [FAQ](./docs/faq.en.md)

## License

Copyright © 2026 Visual Feedback Studio. All rights reserved.

No open-source license is granted unless a future release adds an explicit license file.
