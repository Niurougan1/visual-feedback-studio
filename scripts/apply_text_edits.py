#!/usr/bin/env python3
"""Apply reliable Visual Feedback Studio text edits by exact unique text replacement."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from apply_policy import evaluate_text_edit, replace_text_by_policy, text_edit_sequence_conflicts
from source_resolution import resolve_edit_source_path


SCRIPT_DIR = Path(__file__).resolve().parent
INSPECTOR = SCRIPT_DIR / "feedback_inspector.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to inspect")
    parser.add_argument("--feedback-file", help="Explicit feedback JSON file")
    parser.add_argument("--source-url", help="Prefer sessions matching this source URL or file path")
    parser.add_argument("--dry-run", action="store_true", help="Report edits without writing files")
    parser.add_argument("--allow-outside-root", action="store_true", help="Allow applying edits to a source file outside project_root")
    parser.add_argument("--no-snapshot", action="store_true", help="Do not create a rollback snapshot before writing source files")
    parser.add_argument("--snapshot-dir", help="Rollback snapshot directory; defaults to <project_root>/.visual_feedback_studio_snapshots")
    return parser.parse_args()


def run_inspector(args: argparse.Namespace) -> dict[str, Any]:
    cmd = [sys.executable, str(INSPECTOR), args.project_root]
    if args.feedback_file:
        cmd.extend(["--feedback-file", args.feedback_file])
    if args.source_url:
        cmd.extend(["--source-url", args.source_url])
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"inspector did not return JSON: {error}") from error
    if proc.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or proc.stderr or "inspector failed")
    return payload


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def snapshot_dir(root: Path, explicit: str = "") -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_absolute() else (root / path)
    return root / ".visual_feedback_studio_snapshots"


def write_rollback_snapshot(
    root: Path,
    changes: list[tuple[Path, str, str]],
    feedback_file: Any,
    snapshot_root: Path,
) -> dict[str, Any]:
    if not changes:
        return {}
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_root.mkdir(parents=True, exist_ok=True)
    path = snapshot_root / f"apply-{timestamp}-{os.getpid()}.json"
    entries: list[dict[str, Any]] = []
    for source_path, before, after in changes:
        try:
            relative = str(source_path.resolve().relative_to(root.resolve()))
        except ValueError:
            relative = ""
        entries.append({
            "path": str(source_path.resolve()),
            "relative_path": relative,
            "encoding": "utf-8",
            "sha256_before": sha256_text(before),
            "sha256_after": sha256_text(after),
            "before_text": before,
        })
    payload = {
        "ok": True,
        "version": "4.0-beta",
        "schema": "visual_feedback_studio.rollback_snapshot.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root.resolve()),
        "feedback_file": str(feedback_file or ""),
        "entry_count": len(entries),
        "entries": entries,
    }
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))
    return {
        "snapshot_file": str(path),
        "entry_count": len(entries),
        "created_at": payload["created_at"],
        "rollback_command": " ".join(shlex.quote(part) for part in [
            sys.executable,
            str(SCRIPT_DIR / "rollback_snapshot.py"),
            str(root.resolve()),
            "--snapshot",
            str(path),
        ]),
    }


def skipped_lifecycle(reason: str) -> str:
    reason = str(reason or "")
    if "confidence is not high" in reason or "sequence-dependent" in reason:
        return "needs_review"
    return "unresolved"


def apply_edits(
    summary: dict[str, Any],
    root: Path,
    dry_run: bool,
    allow_outside_root: bool,
    create_snapshot: bool = True,
    snapshot_root: Optional[Path] = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    source_path = summary.get("selected_source_path")
    edits = [edit for edit in summary.get("merged", {}).get("text_edits", []) if isinstance(edit, dict)]
    style_cmd = [sys.executable, str(SCRIPT_DIR / "suggest_style_edits.py"), str(root)]
    if summary.get("feedback_file"):
        style_cmd.extend(["--feedback-file", str(summary.get("feedback_file"))])
    result: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "feedback_file": summary.get("feedback_file"),
        "source_path": source_path,
        "applied": [],
        "skipped": [],
        "style_edits": summary.get("merged", {}).get("style_edits", []),
        "annotations": summary.get("merged", {}).get("annotations", []),
        "unresolved_changes": summary.get("merged", {}).get("unresolved_changes", []),
        "style_suggestions_command": " ".join(shlex.quote(part) for part in style_cmd),
    }

    original_by_path: dict[Path, str] = {}
    updated_by_path: dict[Path, str] = {}

    sequence_conflicts = text_edit_sequence_conflicts([edit for edit in edits if isinstance(edit, dict)])

    for index, edit in enumerate(edits):
        path, source_resolution = resolve_edit_source_path(edit, root, source_path)
        if not path:
            skipped = dict(edit)
            skipped["reason"] = source_resolution
            skipped["lifecycle_status"] = skipped_lifecycle(source_resolution)
            skipped["match_count"] = 0
            result["skipped"].append(skipped)
            continue
        if not path.exists() or not path.is_file():
            skipped = dict(edit)
            skipped["reason"] = f"source file does not exist: {path}"
            skipped["lifecycle_status"] = "unresolved"
            skipped["source_path"] = str(path)
            skipped["source_resolution"] = source_resolution
            skipped["match_count"] = 0
            result["skipped"].append(skipped)
            continue
        if not allow_outside_root and not is_inside_root(path, root):
            skipped = dict(edit)
            skipped["reason"] = f"source file is outside project root: {path}"
            skipped["lifecycle_status"] = "unresolved"
            skipped["source_path"] = str(path)
            skipped["source_resolution"] = source_resolution
            skipped["match_count"] = 0
            result["skipped"].append(skipped)
            continue
        if path not in updated_by_path:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped = dict(edit)
                skipped["reason"] = f"source file is not utf-8 text: {path}"
                skipped["lifecycle_status"] = "unresolved"
                skipped["source_path"] = str(path)
                skipped["source_resolution"] = source_resolution
                skipped["match_count"] = 0
                result["skipped"].append(skipped)
                continue
            original_by_path[path] = text
            updated_by_path[path] = text

        original = str(edit.get("original") or "")
        modified = str(edit.get("modified") or "")
        selector = str(edit.get("selector") or "")
        updated = updated_by_path[path]
        policy = evaluate_text_edit(edit, updated, "", path, root, sequence_conflicts.get(index, ""))
        reason = str(policy["reason"] or "")
        if policy["status"] == "auto_applicable":
            updated = replace_text_by_policy(updated, original, modified, policy["target"])
            updated_by_path[path] = updated
            result["applied"].append({
                "selector": selector,
                "status": "applied",
                "lifecycle_status": "planned" if dry_run else "applied",
                "original": original,
                "modified": modified,
                "locate_confidence": edit.get("locate_confidence") or "low",
                "source_path": str(path),
                "source_resolution": source_resolution,
                "match_count": policy["match_count"],
                "apply_target": policy["target"],
                "reason": reason,
            })
        else:
            skipped = dict(edit)
            skipped["reason"] = reason
            skipped["lifecycle_status"] = policy["lifecycle_status"]
            skipped["match_count"] = policy["match_count"]
            skipped["next_steps"] = policy["next_steps"]
            skipped["source_path"] = str(path)
            skipped["source_resolution"] = source_resolution
            result["skipped"].append(skipped)

    changed_paths: list[str] = []
    snapshot: dict[str, Any] = {}
    if not dry_run:
        changes = [
            (path, original_by_path[path], updated)
            for path, updated in updated_by_path.items()
            if updated != original_by_path[path]
        ]
        if create_snapshot and changes:
            snapshot = write_rollback_snapshot(root, changes, summary.get("feedback_file"), snapshot_root or snapshot_dir(root))
        for path, updated in updated_by_path.items():
            if updated != original_by_path[path]:
                atomic_write_text(path, updated)
                changed_paths.append(str(path))
    result["changed_paths"] = changed_paths
    if snapshot:
        result["snapshot"] = snapshot
        result["snapshot_file"] = snapshot["snapshot_file"]
        result["rollback_command"] = snapshot["rollback_command"]

    return result


def main() -> int:
    args = parse_args()
    try:
        summary = run_inspector(args)
        root = Path(args.project_root).expanduser().resolve()
        result = apply_edits(
            summary,
            root,
            args.dry_run,
            args.allow_outside_root,
            create_snapshot=not args.no_snapshot,
            snapshot_root=snapshot_dir(root, args.snapshot_dir or ""),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 2
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
