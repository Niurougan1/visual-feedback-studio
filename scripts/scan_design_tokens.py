#!/usr/bin/env python3
"""Scan project design tokens for Visual Feedback Studio."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Optional


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".next",
    ".nuxt",
    ".svelte-kit",
    "dist",
    "build",
    "coverage",
    ".cache",
    ".parcel-cache",
    "__pycache__",
}
CSS_SUFFIXES = {".css", ".scss", ".sass", ".less", ".pcss", ".postcss", ".svelte", ".astro"}
JSON_TOKEN_NAMES = {"tokens.json", "design-tokens.json", "theme.json"}
TAILWIND_NAMES = {"tailwind.config.js", "tailwind.config.cjs", "tailwind.config.mjs", "tailwind.config.ts"}
CSS_VAR_RE = re.compile(r"(?P<name>--[A-Za-z0-9_-]+)\s*:\s*(?P<value>[^;{}]+);")
TAILWIND_PAIR_RE = re.compile(r"['\"]?(?P<key>[A-Za-z0-9_-]+)['\"]?\s*:\s*['\"](?P<value>[^'\"]+)['\"]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to scan")
    parser.add_argument("--output", help="Token cache path; defaults to <project_root>/.visual_feedback_studio_tokens.json")
    parser.add_argument("--no-write", action="store_true", help="Print results without writing the token cache")
    return parser.parse_args()


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def default_output(root: Path) -> Path:
    return root / ".visual_feedback_studio_tokens.json"


def token_type(name: str, value: str = "") -> str:
    lowered = f"{name} {value}".lower()
    if any(part in lowered for part in ["color", "colour", "fg", "bg", "background", "border"]):
        return "color"
    if re.search(r"#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(|oklch\(|lab\(", value, re.I):
        return "color"
    if any(part in lowered for part in ["radius", "rounded", "corner"]):
        return "radius"
    if any(part in lowered for part in ["font", "type", "text", "leading", "line-height"]):
        return "typography"
    if any(part in lowered for part in ["shadow", "elevation"]):
        return "shadow"
    if any(part in lowered for part in ["space", "spacing", "gap", "padding", "margin", "size", "width", "height"]):
        return "spacing"
    if re.search(r"^-?\d*\.?\d+(px|rem|em|vh|vw|%)$", value.strip()):
        return "spacing"
    return "other"


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def token_payload(name: str, value: Any, typ: str, source: Path, root: Path, line: int = 0) -> dict[str, Any]:
    text_value = str(value).strip()
    return {
        "name": name,
        "value": text_value,
        "type": typ or token_type(name, text_value),
        "source": rel(source, root),
        "line": line,
        "applied_as": f"var({name})" if name.startswith("--") else text_value,
    }


def scan_css_file(path: Path, root: Path) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return tokens
    for index, line in enumerate(lines, start=1):
        for match in CSS_VAR_RE.finditer(line):
            name = match.group("name").strip()
            value = match.group("value").strip()
            tokens.append(token_payload(name, value, token_type(name, value), path, root, index))
    return tokens


def flatten_json(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        if "value" in value and len(value) <= 4:
            yield prefix, value.get("value")
            return
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from flatten_json(child, next_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from flatten_json(child, f"{prefix}.{index}" if prefix else str(index))
    else:
        yield prefix, value


def scan_json_file(path: Path, root: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    tokens: list[dict[str, Any]] = []
    for name, value in flatten_json(payload):
        if not name or isinstance(value, (dict, list)):
            continue
        text_value = str(value).strip()
        if not text_value:
            continue
        css_name = name if name.startswith("--") else "--" + name.replace(".", "-").replace("_", "-")
        tokens.append(token_payload(css_name, text_value, token_type(css_name, text_value), path, root))
    return tokens


def scan_tailwind_file(path: Path, root: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    tokens: list[dict[str, Any]] = []
    for match in TAILWIND_PAIR_RE.finditer(text):
        key = match.group("key")
        value = match.group("value").strip()
        if not value or len(value) > 120:
            continue
        typ = token_type(key, value)
        if typ == "other":
            continue
        line = text.count("\n", 0, match.start()) + 1
        name = "--tw-" + key.replace("_", "-")
        tokens.append(token_payload(name, value, typ, path, root, line))
    return tokens


def iter_candidate_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS and not name.startswith("._")]
        if is_excluded(current.relative_to(root) if current != root else Path("")):
            continue
        for filename in filenames:
            if filename.startswith("._"):
                continue
            path = current / filename
            suffix = path.suffix.lower()
            if suffix in CSS_SUFFIXES or filename in JSON_TOKEN_NAMES or filename in TAILWIND_NAMES:
                yield path


def dedupe(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for token in tokens:
        key = (str(token.get("name") or ""), str(token.get("value") or ""))
        if key[0] and key not in by_key:
            by_key[key] = token
    return sorted(by_key.values(), key=lambda item: (str(item.get("type")), str(item.get("name")), str(item.get("source"))))


def scan(root: Path) -> dict[str, Any]:
    tokens: list[dict[str, Any]] = []
    scanned: list[str] = []
    for path in iter_candidate_files(root):
        scanned.append(rel(path, root))
        if path.name in JSON_TOKEN_NAMES:
            tokens.extend(scan_json_file(path, root))
        elif path.name in TAILWIND_NAMES:
            tokens.extend(scan_tailwind_file(path, root))
        else:
            tokens.extend(scan_css_file(path, root))
    tokens = dedupe(tokens)
    by_type: dict[str, int] = {}
    for token in tokens:
        typ = str(token.get("type") or "other")
        by_type[typ] = by_type.get(typ, 0) + 1
    return {
        "ok": True,
        "version": "4.0-beta",
        "project_root": str(root),
        "token_count": len(tokens),
        "by_type": by_type,
        "scanned_files": scanned,
        "tokens": tokens,
    }


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output(root)
    payload = scan(root)
    payload["output_file"] = str(output_path)
    if not args.no_write:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
