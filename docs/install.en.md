# Install / Access

[简体中文](./install.md)

Visual Feedback Studio can be loaded locally as a Chrome Manifest V3 extension and used with the local workflow scripts in this repository.

## Local Setup

Run setup against the project you want to review:

```bash
python3 scripts/setup.py /path/to/your-project --channel beta
```

The setup output includes the extension path and local workflow status.

## Chrome Extension

Open Chrome extensions:

```text
chrome://extensions/
```

Enable Developer mode, choose "Load unpacked", and select this repository's `chrome-extension/` directory.

Use one unpacked Visual Feedback Studio extension at a time. If you previously loaded a packaged copy or an older local copy, remove the duplicate entry before testing.

## First Review Loop

If you only want to verify that the tool runs, open `examples/basic-static-preview/index.html` directly or serve `examples/basic-static-preview/` with any static file server.

1. Open a page you are allowed to review.
2. Click the Visual Feedback Studio extension.
3. Grant current-site access when Chrome asks.
4. Capture text, style, or annotation feedback.
5. Save feedback.
6. Preview source resolution:

```bash
python3 scripts/vfs.py plan /path/to/your-project
```

## File URLs

Chrome handles `file://` pages separately. If you review local files, open the extension details page and enable file URL access.

## Public / Private Boundary

This public repository includes the core local review loop and public documentation. Internal planning, commercial materials, private release operations, and sensitive review notes are maintained separately.
