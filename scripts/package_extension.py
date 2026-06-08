#!/usr/bin/env python3
"""Package the Visual Feedback Studio Chrome extension beta zip."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "chrome-extension"
DEFAULT_OUTPUT = ROOT / "dist" / "visual-feedback-studio-v4.0.0-beta-extension.zip"
VERSION = "4.0.0-beta"
EXCLUDED_NAMES = {
    ".git",
    ".DS_Store",
    "examples",
    "node_modules",
    ".visual_feedback_studio.json",
    ".design_feedback.json",
    ".visual_feedback_studio_tokens.json",
    ".visual_feedback_studio_preview.json",
    ".visual_feedback_studio_verify.json",
    ".visual_feedback_studio_snapshots",
    ".visual_feedback_studio_artifacts",
    ".visual_feedback_studio_receiver.json",
    ".visual_feedback_studio_receiver.log",
    "manifest.dev.json",
    "advanced-demo",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extension-dir", default=str(EXTENSION), help="Extension directory to package")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output zip path")
    return parser.parse_args()


def is_excluded(path: Path) -> bool:
    if any(part in EXCLUDED_NAMES for part in path.parts):
        return True
    return any(part.startswith("._") for part in path.parts)


def manifest_payload(extension_dir: Path) -> dict[str, Any]:
    manifest = extension_dir / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("manifest_version") != 3:
        raise RuntimeError("manifest_version must be 3")
    if payload.get("version") != "4.0.0":
        raise RuntimeError("manifest version must be 4.0.0 for v4.0.0-beta")
    description = str(payload.get("description") or "").lower()
    version_name = str(payload.get("version_name") or "").lower()
    if "beta" not in description and "beta" not in version_name:
        raise RuntimeError("manifest description or version_name must indicate beta channel")
    if payload.get("host_permissions"):
        raise RuntimeError("store package manifest must not request default host_permissions")
    optional_hosts = payload.get("optional_host_permissions") or []
    if "http://*/*" not in optional_hosts or "https://*/*" not in optional_hosts or "file:///*" not in optional_hosts:
        raise RuntimeError("store package manifest must use optional host permissions for http, https, and file URLs")
    return payload


def package(extension_dir: Path, output: Path) -> dict[str, Any]:
    extension_dir = extension_dir.expanduser().resolve()
    output = output.expanduser().resolve()
    if not extension_dir.exists() or not extension_dir.is_dir():
        raise RuntimeError(f"extension directory not found: {extension_dir}")
    manifest = manifest_payload(extension_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    entries: list[str] = []
    skipped: list[str] = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(extension_dir.rglob("*")):
            rel = path.relative_to(extension_dir)
            if is_excluded(rel) or not path.is_file():
                if path.name.startswith("._") or path.name in EXCLUDED_NAMES:
                    skipped.append(str(rel))
                continue
            archive.write(path, rel.as_posix())
            entries.append(rel.as_posix())
    apple_double_sidecar = output.with_name(f"._{output.name}")
    if apple_double_sidecar.exists():
        apple_double_sidecar.unlink()
    return {
        "ok": True,
        "version": VERSION,
        "manifest_version": manifest.get("version"),
        "channel": "beta",
        "permission_model": "store-safe optional host permissions",
        "extension_dir": str(extension_dir),
        "output": str(output),
        "entry_count": len(entries),
        "entries": entries,
        "skipped": skipped,
    }


def main() -> int:
    args = parse_args()
    try:
        payload = package(Path(args.extension_dir), Path(args.output))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
