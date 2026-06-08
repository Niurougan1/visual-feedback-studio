#!/usr/bin/env python3
"""Print Chrome Load unpacked instructions for Visual Feedback Studio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTENSION = ROOT / "chrome-extension"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extension-dir", default=str(DEFAULT_EXTENSION), help="Extension directory to load unpacked")
    return parser.parse_args()


def load_manifest(extension_dir: Path) -> dict[str, Any]:
    manifest = extension_dir / "manifest.json"
    if not manifest.exists():
        raise RuntimeError(f"manifest not found: {manifest}")
    return json.loads(manifest.read_text(encoding="utf-8"))


def channel(manifest: dict[str, Any]) -> str:
    text = " ".join([
        str(manifest.get("description") or ""),
        str(manifest.get("version_name") or ""),
    ]).lower()
    return "beta" if "beta" in text else "stable"


def main() -> int:
    args = parse_args()
    try:
        extension_dir = Path(args.extension_dir).expanduser().resolve()
        manifest = load_manifest(extension_dir)
        detected_channel = channel(manifest)
        payload = {
            "ok": True,
            "extension_dir": str(extension_dir),
            "manifest_version": manifest.get("manifest_version"),
            "extension_version": manifest.get("version"),
            "channel": detected_channel,
            "load_unpacked": str(extension_dir),
            "single_entry": True,
            "chrome_url": "chrome://extensions/",
            "steps": [
                "Open chrome://extensions/.",
                "Remove or disable old Visual Feedback Studio entries loaded from dist, zip extracts, or skill install copies.",
                "Enable Developer mode.",
                "Choose Load unpacked.",
                "Select load_unpacked.",
                "Enable Allow access to file URLs if reviewing file:// pages.",
            ],
        }
        if manifest.get("version") != "4.0.0" or detected_channel != "beta":
            payload["warning"] = "Expected v4.0.0 beta manifest for this branch."
        payload["permission_model"] = (
            "store-safe optional host permissions"
            if manifest.get("optional_host_permissions") and not manifest.get("host_permissions")
            else "development or legacy host permissions"
        )
        payload["file_url_note"] = "Enable Allow access to file URLs in extension details before reviewing file:// pages."
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
