# Install / Access

[简体中文](./install.md)

Visual Feedback Studio can be loaded locally as a Chrome Manifest V3 extension and used with the local workflow scripts in this repository.

## One-line Install

Run this from the local project you want to review:

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | bash
```

This checks `python3`, `git`, and `node`, pulls or updates the public repository, installs the local workflow, starts the receiver, and prints the Chrome extension path. Progress lines are prefixed with `[vfs]`.

If setup fails, read these final JSON fields:

- `error`: failure type.
- `next_step`: what to do next.
- `receiver.log_tail`: the end of the receiver startup log, including port conflicts or local permission blocks.

If port `3456` is already used by another local receiver, choose another port:

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | VFS_PORT=3463 bash
```

If the repository is already installed and you only want to reuse/update the receiver:

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | VFS_INSTALL_MODE=none VFS_PORT=3463 bash
```

If a remote preview URL must write to the local receiver, explicitly allow one origin:

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | VFS_ALLOWED_ORIGIN=https://your-preview-origin VFS_PORT=3463 bash
```

If you have already cloned this repository, you can also run setup directly:

```bash
python3 scripts/setup.py /path/to/your-project --channel beta
```

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
