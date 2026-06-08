#!/usr/bin/env python3
"""Restore source files from a Visual Feedback Studio rollback snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Project root")
    parser.add_argument("--snapshot", required=True, help="Snapshot JSON produced by apply_text_edits.py")
    parser.add_argument("--dry-run", action="store_true", help="Report files that would be restored without writing")
    parser.add_argument("--force", action="store_true", help="Restore even if current file content differs from the recorded post-apply hash")
    parser.add_argument("--allow-outside-root", action="store_true", help="Allow restoring paths outside project_root")
    return parser.parse_args()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def atomic_write_text(path: Path, text: str) -> None:
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def load_snapshot(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "visual_feedback_studio.rollback_snapshot.v1":
        raise RuntimeError("snapshot is not a Visual Feedback Studio rollback snapshot")
    if not isinstance(payload.get("entries"), list):
        raise RuntimeError("snapshot entries must be a list")
    return payload


def restore_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project_root).expanduser().resolve()
    snapshot_path = Path(args.snapshot).expanduser().resolve()
    snapshot = load_snapshot(snapshot_path)
    restored: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for entry in snapshot.get("entries", []):
        if not isinstance(entry, dict):
            skipped.append({"reason": "snapshot entry is not an object"})
            continue
        path = Path(str(entry.get("path") or "")).expanduser()
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        if not args.allow_outside_root and not is_inside_root(path, root):
            skipped.append({"path": str(path), "reason": "snapshot path is outside project root"})
            continue
        before = str(entry.get("before_text") or "")
        expected_after = str(entry.get("sha256_after") or "")
        if not path.exists() or not path.is_file():
            skipped.append({"path": str(path), "reason": "current file does not exist"})
            continue
        try:
            current = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append({"path": str(path), "reason": "current file is not utf-8 text"})
            continue
        current_hash = sha256_text(current)
        if expected_after and current_hash != expected_after and not args.force:
            skipped.append({
                "path": str(path),
                "reason": "current file differs from snapshot post-apply hash",
                "current_sha256": current_hash,
                "expected_sha256": expected_after,
            })
            continue
        if not args.dry_run:
            atomic_write_text(path, before)
        restored.append({
            "path": str(path),
            "status": "would_restore" if args.dry_run else "restored",
            "sha256_restored": sha256_text(before),
        })
    return {
        "ok": True,
        "dry_run": args.dry_run,
        "snapshot_file": str(snapshot_path),
        "project_root": str(root),
        "restored": restored,
        "skipped": skipped,
        "counts": {
            "restored": len(restored),
            "skipped": len(skipped),
        },
    }


def main() -> int:
    args = parse_args()
    try:
        payload = restore_snapshot(args)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("ok") else 2
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
