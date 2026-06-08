"""Best-effort source path resolution for Visual Feedback Studio feedback items."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse


def source_loc_file(source_loc: Any) -> str:
    if isinstance(source_loc, dict):
        return str(source_loc.get("file") or "").strip()
    value = str(source_loc or "").strip()
    if not value:
        return ""
    match = re.match(r"^(.+?):\d+(?::\d+)?$", value)
    return match.group(1) if match else value


def source_loc_files(item: dict[str, Any]) -> list[str]:
    files: list[str] = []

    def add(source_loc: Any) -> None:
        file_value = source_loc_file(source_loc)
        if file_value and file_value not in files:
            files.append(file_value)

    anchors = item.get("source_anchors") if isinstance(item.get("source_anchors"), dict) else {}
    add(anchors.get("sourceLoc"))

    hint = item.get("source_hint") if isinstance(item.get("source_hint"), dict) else {}
    hint_anchors = hint.get("anchors") if isinstance(hint.get("anchors"), dict) else {}
    add(hint_anchors.get("sourceLoc"))

    chain = hint.get("component_chain") if isinstance(hint.get("component_chain"), list) else []
    for component in chain:
        if isinstance(component, dict):
            add(component.get("sourceLoc"))

    return files


def path_candidates(file_value: str, root: Path) -> list[Path]:
    clean = str(file_value or "").strip()
    if not clean:
        return []
    clean = clean.split("?", 1)[0].split("#", 1)[0]
    parsed = urlparse(clean)
    if parsed.scheme == "file":
        clean = unquote(parsed.path)
    elif clean.startswith("/@fs/"):
        clean = clean[len("/@fs/") - 1:]
    path = Path(unquote(clean)).expanduser()
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
        if not path.exists():
            candidates.append(root / clean.lstrip("/"))
    else:
        candidates.append(root / path)
    return candidates


def first_existing_file(candidates: list[Path]) -> Optional[Path]:
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def is_inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def fallback_path(value: Any) -> Optional[Path]:
    if not value:
        return None
    return Path(str(value)).expanduser()


def resolve_edit_source_path(item: dict[str, Any], root: Path, fallback: Any = None) -> tuple[Optional[Path], str]:
    explicit = item.get("source_path") or item.get("resolved_source_path")
    if explicit:
        path = first_existing_file([Path(str(explicit)).expanduser()])
        if path:
            return path, str(item.get("source_resolution") or "item_source_path")

    for file_value in source_loc_files(item):
        path = first_existing_file(path_candidates(file_value, root))
        if path:
            return path, "sourceLoc"

    fallback = fallback_path(fallback)
    if fallback:
        if fallback.exists() and fallback.is_file():
            return fallback.resolve(), "selected_source_path"
        return fallback, "selected_source_path_missing"

    if source_loc_files(item):
        return None, "sourceLoc did not resolve to an existing file"
    return None, "selected feedback session does not resolve to a local file"
